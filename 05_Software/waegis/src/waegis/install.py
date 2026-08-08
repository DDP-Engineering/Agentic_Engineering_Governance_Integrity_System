#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file install.py
@brief Shared WAEGIS 3 ``new`` and ``adopt`` plan/apply flow.
@details Computes every byte, conflict, ownership disposition, and recovery path
         before consent; publishes atomically; validates the real copied AEGIS
         wrapper; and writes manifest schema 2 last.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping, TextIO

from .answers import configuration_answers
from .classify import ConflictDecision, normalize_conflict_decision
from .copier import PayloadInventory
from .gitsafety import (
    RecoveryPlan,
    acquire_lock,
    build_recovery_plan,
    execute_recovery,
    require_clean,
    require_planned_head,
    require_repository,
    tracked_paths,
)
from .gitops import initialize_repository
from .manifest import (
    MANIFEST_PATH,
    InstallManifest,
    contained_destination,
    detect_manifest_version,
    file_record,
    serialize_manifest,
)
from .ownership import Disposition
from .publication import validate_aegis
from .runner import Runner
from .runtime import register_runtime
from .version import WIZARD_VERSION
from .workflow_toml import generate_workflow


# CONSTANTS

# DATA MODELS / TYPEDEFINITIONS


class InstallError(RuntimeError):
    """@brief Raised when install planning, validation, or recovery fails."""


class NeedsInput(InstallError):
    """@brief Carries every missing answer/conflict/consent key."""

    def __init__(self, keys: tuple[str, ...]) -> None:
        self.keys = keys
        super().__init__("more operator input is required: " + ", ".join(keys))


@dataclass(frozen=True, slots=True)
class FileOperation:
    """@brief One planned destination and its final bytes/authority."""

    path: str
    action: str
    disposition: Disposition
    data: bytes
    source_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "action": self.action,
            "disposition": self.disposition.value,
            "size": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "source_path": self.source_path,
        }


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """@brief Complete immutable install plan rendered before consent."""

    mode: str
    target: Path
    payload_version: str
    payload_digest: str
    answers: Mapping[str, object]
    provenance: Mapping[str, str]
    operations: tuple[FileOperation, ...]
    recovery: RecoveryPlan | None
    migrates_v1: bool

    @property
    def write_operations(self) -> tuple[FileOperation, ...]:
        return tuple(operation for operation in self.operations if operation.action in {"write", "sidecar"})

    def to_dict(self) -> dict[str, object]:
        recovery: object = self.recovery.to_dict() if self.recovery else {
            "kind": "delete-created-target",
            "path": str(self.target),
        }
        return {
            "mode": self.mode,
            "target": str(self.target),
            "payload_version": self.payload_version,
            "payload_digest": self.payload_digest,
            "migrates_v1": self.migrates_v1,
            "answers": dict(sorted(configuration_answers(self.answers).items())),
            "provenance": dict(sorted(self.provenance.items())),
            "operations": [operation.to_dict() for operation in self.operations],
            "recovery": recovery,
        }


# HELPER FUNCTIONS


def _read_payload_bytes(root: Path, relative: str, expected_hash: str, expected_size: int) -> bytes:
    source = root.joinpath(*relative.split("/"))
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise InstallError(f"cannot read payload member {relative}: {exc}") from exc
    if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected_hash:
        raise InstallError(f"payload member changed after inventory verification: {relative}")
    return data


def _sidecar_path(target: Path, relative: str, reserved: set[str]) -> str:
    base = f"{relative}.waegis-{WIZARD_VERSION}.new"
    candidate = base
    index = 1
    while candidate.casefold() in reserved or target.joinpath(*candidate.split("/")).exists():
        index += 1
        candidate = f"{base}.{index}"
    reserved.add(candidate.casefold())
    return candidate


def _recovery_record(plan: InstallPlan) -> dict[str, object]:
    if plan.recovery:
        return plan.recovery.to_dict()
    return {"kind": "delete-created-target", "path": str(plan.target)}


def _emit_recovery(plan: InstallPlan, stream: TextIO, *, as_json: bool) -> None:
    record = _recovery_record(plan)
    if as_json:
        stream.write(json.dumps({"waegis_recovery": record}, sort_keys=True) + "\n")
    else:
        stream.write("Recovery plan (emitted before mutation):\n")
        if plan.recovery:
            for command in plan.recovery.rendered():
                stream.write(f"  {command}\n")
        else:
            stream.write(f"  delete the WAEGIS-created directory: {plan.target}\n")
    stream.flush()


def _manifest_for(plan: InstallPlan) -> InstallManifest:
    records = {
        operation.path: file_record(operation.data, operation.disposition)
        for operation in plan.operations
    }
    workflow = records.get(".agentic/workflow.toml")
    configuration = {
        "answers": configuration_answers(plan.answers),
        "generator_version": WIZARD_VERSION,
        "workflow_sha256": workflow.sha256 if workflow else None,
    }
    return InstallManifest(
        payload_version=plan.payload_version,
        payload_digest=plan.payload_digest,
        installed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        installed_by=f"waegis {WIZARD_VERSION}",
        mode=plan.mode,
        files=records,
        configuration=configuration,
    )


# EXPORTED FUNCTIONS / PUBLIC API


def plan_install(
    mode: str,
    target: Path,
    payload_root: Path,
    payload_version: str,
    inventory: PayloadInventory,
    answers: Mapping[str, object],
    runner: Runner,
    *,
    provenance: Mapping[str, str] | None = None,
    conflict_resolver: Callable[[str], str] | None = None,
) -> InstallPlan:
    """
    @brief Compute every install byte, conflict, disposition, and recovery path.
    @param[in] mode ``new`` or ``adopt``.
    @param[in] target Target path.
    @param[in] payload_root Verified payload directory.
    @param[in] payload_version Compatible payload version.
    @param[in] inventory Closed payload inventory.
    @param[in] answers Normalized interview/operation answers.
    @param[in] runner Injectable Git runner.
    @param[in] conflict_resolver Optional live path-specific decision callback.
    @return Complete immutable pre-consent plan.
    """
    if mode not in {"new", "adopt"}:
        raise InstallError(f"unsupported install mode: {mode}")
    resolved_target = target.resolve() if target.exists() else target.absolute()
    if mode == "new":
        if target.exists():
            raise InstallError("new target must not exist; remove an empty directory or use adopt")
        try:
            parent = target.parent.resolve(strict=True)
        except OSError as exc:
            raise InstallError(f"new target parent does not exist: {target.parent}") from exc
        if not parent.is_dir():
            raise InstallError(f"new target parent is not a directory: {parent}")
        resolved_target = parent / target.name
        repository = None
        migrates_v1 = False
    else:
        repository = require_repository(runner, target)
        require_clean(runner, repository)
        resolved_target = repository
        manifest_path = repository.joinpath(*MANIFEST_PATH.split("/"))
        detected = detect_manifest_version(manifest_path)
        if manifest_path.exists() and detected is None:
            raise InstallError("existing install manifest is invalid; preserve it and review before adoption")
        if detected == 2:
            raise InstallError("repository already has a WAEGIS 3 manifest; use check or upgrade")
        migrates_v1 = detected is not None
        if migrates_v1 and answers.get("migration_v1") is not True:
            raise NeedsInput(("migration_v1",))
    workflow_record = inventory.by_path.get(".agentic/workflow.toml")
    if workflow_record is None:
        raise InstallError("payload inventory lacks .agentic/workflow.toml")
    base_workflow = _read_payload_bytes(
        payload_root,
        workflow_record.path,
        workflow_record.sha256,
        workflow_record.size,
    ).decode("utf-8")
    workflow_data = generate_workflow(base_workflow, answers).encode("utf-8")
    supplied_conflicts = answers.get("conflicts", {})
    if not isinstance(supplied_conflicts, Mapping):
        raise InstallError("conflicts answers must be a path mapping")
    operations: list[FileOperation] = []
    reserved = {record.path.casefold() for record in inventory.records}
    missing: list[str] = []
    used_conflicts: set[str] = set()
    for record in inventory.records:
        data = workflow_data if record.path == ".agentic/workflow.toml" else _read_payload_bytes(
            payload_root,
            record.path,
            record.sha256,
            record.size,
        )
        if repository is None:
            operations.append(FileOperation(record.path, "write", record.disposition, data))
            continue
        destination = contained_destination(repository, record.path)
        if not destination.exists():
            operations.append(FileOperation(record.path, "write", record.disposition, data))
            continue
        try:
            current = destination.read_bytes()
        except OSError as exc:
            raise InstallError(f"cannot read existing destination {record.path}: {exc}") from exc
        if current == data:
            operations.append(FileOperation(record.path, "unchanged", record.disposition, current))
            continue
        raw_decision = supplied_conflicts.get(record.path)
        if raw_decision is not None:
            used_conflicts.add(record.path)
        if raw_decision is None and conflict_resolver is not None:
            raw_decision = conflict_resolver(record.path)
        if raw_decision is None:
            missing.append(f"conflicts.{record.path}")
            continue
        try:
            decision = normalize_conflict_decision(str(raw_decision))
        except ValueError as exc:
            raise InstallError(f"invalid conflict decision for {record.path}: {raw_decision!r}") from exc
        if decision is ConflictDecision.KEEP_LOCAL:
            operations.append(FileOperation(record.path, "keep-local", Disposition.KEPT_LOCAL, current))
        elif decision is ConflictDecision.TAKE_PAYLOAD:
            operations.append(FileOperation(record.path, "write", record.disposition, data))
        else:
            operations.append(FileOperation(record.path, "keep-local", Disposition.KEPT_LOCAL, current))
            sidecar = _sidecar_path(repository, record.path, reserved)
            operations.append(FileOperation(sidecar, "sidecar", Disposition.SIDECAR, data, source_path=record.path))
    if missing:
        raise NeedsInput(tuple(sorted(missing)))
    stale_conflicts = sorted(set(supplied_conflicts) - used_conflicts, key=lambda item: item.encode("utf-8"))
    if stale_conflicts:
        raise NeedsInput(tuple(f"conflicts.{path}" for path in stale_conflicts))
    operations.sort(key=lambda operation: operation.path.encode("utf-8"))
    if repository:
        maintained_existing = tuple(
            operation.path
            for operation in operations
            if operation.action == "unchanged"
            and operation.disposition in {Disposition.MANAGED, Disposition.GENERATED}
        )
        tracked_maintained = tracked_paths(runner, repository, maintained_existing)
        untracked_maintained = tuple(path for path in maintained_existing if path not in tracked_maintained)
        if untracked_maintained:
            raise InstallError(
                "managed destinations exist outside the committed baseline; preserve or remove them before adoption: "
                + ", ".join(untracked_maintained)
            )
    write_paths = [operation.path for operation in operations if operation.action in {"write", "sidecar"}]
    write_paths.append(MANIFEST_PATH)
    recovery = build_recovery_plan(runner, repository, write_paths) if repository else None
    return InstallPlan(
        mode,
        resolved_target,
        payload_version,
        inventory.digest,
        dict(answers),
        dict(provenance or {}),
        tuple(operations),
        recovery,
        migrates_v1,
    )


def apply_install(
    plan: InstallPlan,
    runner: Runner,
    recovery_stream: TextIO,
    *,
    as_json: bool,
    break_lock: bool = False,
) -> InstallManifest:
    """
    @brief Apply a consented install plan and publish its manifest last.
    @param[in] plan Complete immutable plan.
    @param[in] runner Injectable subprocess runner.
    @param[in] recovery_stream Flushed pre-mutation recovery output.
    @param[in] as_json Emit a structured recovery line when true.
    @param[in] break_lock Explicit dead-owner instruction.
    @return Published manifest.
    @exception InstallError If apply, validation, or rollback fails.
    """
    created_target = plan.mode == "new"
    target_created = False
    recovery_emitted = False
    lock = None
    stage_root: Path | None = None
    manifest = _manifest_for(plan)
    try:
        if created_target:
            if plan.target.exists():
                raise InstallError("new target already exists; rerun planning or use adopt")
            _emit_recovery(plan, recovery_stream, as_json=as_json)
            recovery_emitted = True
            plan.target.mkdir(parents=False)
            target_created = True
            initialize_repository(runner, plan.target)
        else:
            require_clean(runner, plan.target)
        lock = acquire_lock(runner, plan.target, plan.mode, break_lock=break_lock)
        if not created_target:
            require_clean(runner, plan.target)
            assert plan.recovery is not None
            require_planned_head(runner, plan.recovery)
            _emit_recovery(plan, recovery_stream, as_json=as_json)
            recovery_emitted = True
        register_runtime(runner)
        stage_root = Path(tempfile.mkdtemp(prefix=".waegis-stage-", dir=plan.target.parent))
        for operation in plan.write_operations:
            staged = stage_root.joinpath(*operation.path.split("/"))
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(operation.data)
        staged_manifest = stage_root.joinpath(*MANIFEST_PATH.split("/"))
        staged_manifest.parent.mkdir(parents=True, exist_ok=True)
        staged_manifest.write_bytes(serialize_manifest(manifest))
        for operation in plan.write_operations:
            destination = contained_destination(plan.target, operation.path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage_root.joinpath(*operation.path.split("/")), destination)
        validate_aegis(plan.target, runner)
        manifest_destination = contained_destination(plan.target, MANIFEST_PATH)
        manifest_destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_manifest, manifest_destination)
        return manifest
    except BaseException as exc:
        rollback_error: Exception | None = None
        try:
            if created_target:
                if target_created and plan.target.exists():
                    shutil.rmtree(plan.target)
            elif plan.recovery:
                execute_recovery(runner, plan.recovery)
        except Exception as rollback_exc:  # pragma: no cover - separately fault-injected
            rollback_error = rollback_exc
        if isinstance(exc, KeyboardInterrupt):
            if rollback_error:
                raise InstallError(f"interrupted; automatic recovery failed: {rollback_error}") from exc
            raise
        detail = str(exc)
        if not recovery_emitted:
            detail = f"failed before recovery evidence or repository mutation: {detail}"
        if rollback_error:
            detail += f"; automatic recovery failed: {rollback_error}"
        raise InstallError(detail) from exc
    finally:
        if lock is not None:
            lock.release()
        if stage_root is not None:
            shutil.rmtree(stage_root, ignore_errors=True)


# END OF FILE
