#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file upgrade.py
@brief Ownership-aware V2-to-V2 AEGIS payload upgrade planning.
@details Applies the pure three-way classifier only to managed paths, resolves
         every conflict path explicitly, and preserves generated/project-owned
         bytes and dispositions.
"""

# IMPORTS

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .classify import ConflictDecision, UpgradeAction, classify_upgrade, normalize_conflict_decision
from .copier import InventoryRecord
from .gitsafety import build_recovery_plan, require_clean, require_repository, tracked_paths
from .locate import resolve_payload
from .manifest import MANIFEST_PATH, FileRecord, InstallManifest, contained_destination, file_record, load_manifest
from .ownership import Disposition
from .publication import PublicationPlan
from .runner import Runner
from .version import WIZARD_VERSION, is_payload_compatible, parse_semver


# DATA MODELS / TYPEDEFINITIONS


class UpgradeError(RuntimeError):
    """@brief Raised when an upgrade cannot produce a safe complete plan."""


class UpgradeNeedsInput(UpgradeError):
    """@brief Carries every unresolved or stale path-specific conflict key."""

    def __init__(self, keys: tuple[str, ...]) -> None:
        self.keys = keys
        super().__init__("more operator input is required: " + ", ".join(keys))


@dataclass(frozen=True, slots=True)
class UpgradeItem:
    """@brief One ownership/classifier outcome rendered before consent."""

    path: str
    action: str
    disposition: Disposition | None
    sidecar: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "action": self.action,
            "disposition": self.disposition.value if self.disposition else None,
            "sidecar": self.sidecar,
        }


@dataclass(frozen=True, slots=True)
class UpgradePlan:
    """@brief Complete upgrade decisions plus shared publication plan."""

    installed_version: str
    payload_version: str
    items: tuple[UpgradeItem, ...]
    publication: PublicationPlan

    def to_dict(self) -> dict[str, object]:
        return {
            "installed_version": self.installed_version,
            "payload_version": self.payload_version,
            "items": [item.to_dict() for item in self.items],
            "publication": self.publication.to_dict(),
        }


# HELPER FUNCTIONS


def _current_bytes(repository: Path, path: str) -> bytes | None:
    destination = contained_destination(repository, path)
    if not destination.exists():
        return None
    if not destination.is_file():
        raise UpgradeError(f"upgrade destination is not a regular file: {path}")
    try:
        return destination.read_bytes()
    except OSError as exc:
        raise UpgradeError(f"cannot read upgrade destination {path}: {exc}") from exc


def _payload_bytes(root: Path, record: InventoryRecord) -> bytes:
    try:
        data = root.joinpath(*record.path.split("/")).read_bytes()
    except OSError as exc:
        raise UpgradeError(f"cannot read payload path {record.path}: {exc}") from exc
    if len(data) != record.size or hashlib.sha256(data).hexdigest() != record.sha256:
        raise UpgradeError(f"payload changed after inventory verification: {record.path}")
    return data


def _observed_record(data: bytes | None, previous: FileRecord, disposition: Disposition) -> FileRecord:
    return file_record(data, disposition) if data is not None else FileRecord(previous.sha256, previous.size, disposition)


def _sidecar_path(repository: Path, relative: str, reserved: set[str]) -> str:
    base = f"{relative}.waegis-{WIZARD_VERSION}.new"
    candidate = base
    index = 1
    while candidate.casefold() in reserved or repository.joinpath(*candidate.split("/")).exists():
        index += 1
        candidate = f"{base}.{index}"
    reserved.add(candidate.casefold())
    return candidate


def _seeded_addition(
    repository: Path,
    payload_root: Path,
    record: InventoryRecord,
    writes: dict[str, bytes],
    files: dict[str, FileRecord],
) -> UpgradeItem:
    current = _current_bytes(repository, record.path)
    if current is None:
        data = _payload_bytes(payload_root, record)
        writes[record.path] = data
        files[record.path] = file_record(data, Disposition.SEEDED)
        return UpgradeItem(record.path, "add", Disposition.SEEDED)
    files[record.path] = file_record(current, Disposition.SEEDED)
    return UpgradeItem(record.path, "preserve-local", Disposition.SEEDED)


# EXPORTED FUNCTIONS / PUBLIC API


def plan_upgrade(
    repository: Path,
    payload: Path | None,
    answers: Mapping[str, object],
    runner: Runner,
    *,
    conflict_resolver: Callable[[str], str] | None = None,
) -> UpgradePlan:
    """@brief Build a complete ownership-aware V2-to-V2 upgrade plan."""
    root = require_repository(runner, repository)
    require_clean(runner, root)
    manifest = load_manifest(root.joinpath(*MANIFEST_PATH.split("/")))
    try:
        installed_compatible = is_payload_compatible(manifest.payload_version)
    except ValueError as exc:
        raise UpgradeError(f"installed payload version is invalid: {manifest.payload_version}") from exc
    if not installed_compatible:
        raise UpgradeError("installed payload is outside the WAEGIS 3 compatibility range")
    payload_root, payload_version, inventory = resolve_payload(payload)
    if parse_semver(payload_version)[:3] <= parse_semver(manifest.payload_version)[:3]:
        raise UpgradeError(
            f"upgrade payload {payload_version} must be newer than installed {manifest.payload_version}"
        )
    supplied_conflicts = answers.get("conflicts", {})
    if not isinstance(supplied_conflicts, Mapping):
        raise UpgradeError("conflicts answers must be a path mapping")
    payload_records = inventory.by_path
    paths = sorted(set(manifest.files) | set(payload_records), key=lambda item: item.encode("utf-8"))
    folded: dict[str, str] = {}
    for path in paths:
        previous_case = folded.setdefault(path.casefold(), path)
        if previous_case != path:
            raise UpgradeError(f"old/new payload paths collide by case: {previous_case}, {path}")
    writes: dict[str, bytes] = {}
    removals: list[str] = []
    files: dict[str, FileRecord] = {}
    items: list[UpgradeItem] = []
    missing: list[str] = []
    used_conflicts: set[str] = set()
    reserved = {path.casefold() for path in paths}
    for path in paths:
        previous = manifest.files.get(path)
        payload_record = payload_records.get(path)
        current = _current_bytes(root, path)
        current_hash = hashlib.sha256(current).hexdigest() if current is not None else None
        if previous is not None and previous.disposition is not Disposition.MANAGED:
            files[path] = _observed_record(current, previous, previous.disposition)
            items.append(UpgradeItem(path, "preserve-local", previous.disposition))
            continue
        if previous is not None and payload_record is not None and payload_record.disposition is Disposition.SEEDED:
            if current is None:
                data = _payload_bytes(payload_root, payload_record)
                writes[path] = data
                files[path] = file_record(data, Disposition.SEEDED)
                items.append(UpgradeItem(path, "add", Disposition.SEEDED))
            else:
                files[path] = file_record(current, Disposition.SEEDED)
                items.append(UpgradeItem(path, "preserve-local", Disposition.SEEDED))
            continue
        if previous is not None and payload_record is not None and payload_record.disposition is Disposition.GENERATED:
            files[path] = _observed_record(current, previous, Disposition.GENERATED)
            items.append(UpgradeItem(path, "preserve-local", Disposition.GENERATED))
            continue
        if previous is None and payload_record is not None and payload_record.disposition is Disposition.SEEDED:
            items.append(_seeded_addition(root, payload_root, payload_record, writes, files))
            continue
        if previous is None and payload_record is not None and payload_record.disposition is Disposition.GENERATED:
            if current is not None:
                files[path] = file_record(current, Disposition.KEPT_LOCAL)
            items.append(UpgradeItem(path, "preserve-local", Disposition.KEPT_LOCAL))
            continue
        baseline_hash = previous.sha256 if previous else None
        payload_hash = payload_record.sha256 if payload_record else None
        action = classify_upgrade(baseline_hash, current_hash, payload_hash, Disposition.MANAGED)
        if action in {UpgradeAction.ADD, UpgradeAction.REPLACE}:
            assert payload_record is not None
            data = _payload_bytes(payload_root, payload_record)
            writes[path] = data
            files[path] = file_record(data, Disposition.MANAGED)
            items.append(UpgradeItem(path, action.value, Disposition.MANAGED))
        elif action is UpgradeAction.REMOVE:
            removals.append(path)
            items.append(UpgradeItem(path, action.value, None))
        elif action in {UpgradeAction.UNCHANGED, UpgradeAction.CONVERGED}:
            if payload_record is not None:
                files[path] = FileRecord(payload_record.sha256, payload_record.size, Disposition.MANAGED)
            items.append(UpgradeItem(path, action.value, Disposition.MANAGED if payload_record else None))
        elif action is UpgradeAction.PRESERVE_LOCAL:
            assert previous is not None
            files[path] = _observed_record(current, previous, Disposition.KEPT_LOCAL)
            items.append(UpgradeItem(path, action.value, Disposition.KEPT_LOCAL))
        else:
            raw_decision = supplied_conflicts.get(path)
            if raw_decision is not None:
                used_conflicts.add(path)
            elif conflict_resolver is not None:
                raw_decision = conflict_resolver(path)
            if raw_decision is None:
                missing.append(f"conflicts.{path}")
                continue
            try:
                decision = normalize_conflict_decision(str(raw_decision))
            except ValueError as exc:
                raise UpgradeError(f"invalid conflict decision for {path}: {raw_decision!r}") from exc
            assert payload_record is not None
            data = _payload_bytes(payload_root, payload_record)
            if decision is ConflictDecision.TAKE_PAYLOAD:
                writes[path] = data
                files[path] = file_record(data, Disposition.MANAGED)
                items.append(UpgradeItem(path, "take-payload", Disposition.MANAGED))
            else:
                fallback = previous or FileRecord(payload_record.sha256, payload_record.size, Disposition.KEPT_LOCAL)
                files[path] = _observed_record(current, fallback, Disposition.KEPT_LOCAL)
                if decision is ConflictDecision.KEEP_LOCAL:
                    items.append(UpgradeItem(path, "keep-local", Disposition.KEPT_LOCAL))
                else:
                    sidecar = _sidecar_path(root, path, reserved)
                    writes[sidecar] = data
                    files[sidecar] = file_record(data, Disposition.SIDECAR)
                    items.append(UpgradeItem(path, "sidecar", Disposition.KEPT_LOCAL, sidecar))
    if missing:
        raise UpgradeNeedsInput(tuple(sorted(missing)))
    stale = sorted(set(supplied_conflicts) - used_conflicts, key=lambda item: item.encode("utf-8"))
    if stale:
        raise UpgradeNeedsInput(tuple(f"conflicts.{path}" for path in stale))
    maintained_existing = tuple(
        path for path, record in files.items() if record.disposition is Disposition.MANAGED and contained_destination(root, path).exists()
    )
    tracked = tracked_paths(runner, root, maintained_existing)
    outside_baseline = tuple(path for path in maintained_existing if path not in tracked)
    if outside_baseline:
        raise UpgradeError("managed upgrade destinations are outside the committed baseline: " + ", ".join(outside_baseline))
    workflow = _current_bytes(root, ".agentic/workflow.toml")
    configuration = dict(manifest.configuration)
    if workflow is not None:
        configuration["workflow_sha256"] = hashlib.sha256(workflow).hexdigest()
    updated_manifest = InstallManifest(
        payload_version,
        inventory.digest,
        datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        f"waegis {WIZARD_VERSION}",
        "upgrade",
        files,
        configuration,
    )
    recovery = build_recovery_plan(runner, root, (*writes, *removals, MANIFEST_PATH))
    publication = PublicationPlan("upgrade", root, writes, tuple(removals), recovery, updated_manifest)
    return UpgradePlan(manifest.payload_version, payload_version, tuple(items), publication)


# END OF FILE
