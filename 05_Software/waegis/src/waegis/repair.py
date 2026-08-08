#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file repair.py
@brief Managed-file-only AEGIS repair planning.
@details Requires the exact installed payload identity, never regenerates
         workflow configuration, and preserves every project-owned disposition.
"""

# IMPORTS

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .drift import inspect_drift
from .gitsafety import build_recovery_plan, require_clean, require_repository
from .locate import resolve_payload
from .manifest import MANIFEST_PATH, InstallManifest, load_manifest
from .ownership import Disposition
from .publication import PublicationPlan
from .runner import Runner
from .version import WIZARD_VERSION
from .workflow_toml import WorkflowError, workflow_answers


# DATA MODELS / TYPEDEFINITIONS


class RepairError(RuntimeError):
    """@brief Raised when managed-only repair authority cannot be proven."""


# EXPORTED FUNCTIONS / PUBLIC API


def plan_repair(
    repository: Path,
    payload: Path | None,
    runner: Runner,
) -> tuple[PublicationPlan | None, tuple[dict[str, object], ...]]:
    """@brief Plan restoration of only missing or modified managed files."""
    root = require_repository(runner, repository)
    require_clean(runner, root)
    manifest = load_manifest(root.joinpath(*MANIFEST_PATH.split("/")))
    payload_root, payload_version, inventory = resolve_payload(payload)
    if payload_version != manifest.payload_version or inventory.digest != manifest.payload_digest:
        if payload_version == manifest.payload_version:
            raise RepairError("available payload is a different same-version rebuild; use waegis adopt to re-adopt it")
        raise RepairError("available payload is not the installed payload identity; use waegis upgrade")
    drift = inspect_drift(root, manifest)
    configuration_drift = [
        record for record in drift if record.disposition is Disposition.GENERATED and record.state != "clean"
    ]
    workflow_path = root / ".agentic" / "workflow.toml"
    try:
        workflow_answers(workflow_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, WorkflowError) as exc:
        raise RepairError(f"workflow configuration needs waegis configure, not repair: {exc}") from exc
    if configuration_drift:
        raise RepairError("generated workflow configuration has drift; run waegis configure")
    writes: dict[str, bytes] = {}
    for record in drift:
        if record.state == "clean" or record.disposition is not Disposition.MANAGED:
            continue
        if record.state in {"unsafe", "not-file", "unreadable"}:
            raise RepairError(f"managed path cannot be repaired safely in its current state: {record.path} ({record.state})")
        payload_record = inventory.by_path.get(record.path)
        manifest_record = manifest.files[record.path]
        if (
            payload_record is None
            or payload_record.sha256 != manifest_record.sha256
            or payload_record.size != manifest_record.size
        ):
            raise RepairError(f"installed baseline bytes are unavailable for managed path: {record.path}")
        source = payload_root.joinpath(*record.path.split("/"))
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise RepairError(f"cannot read repair payload path {record.path}: {exc}") from exc
        if len(data) != payload_record.size or hashlib.sha256(data).hexdigest() != payload_record.sha256:
            raise RepairError(f"repair payload changed after inventory verification: {record.path}")
        writes[record.path] = data
    report = tuple(record.to_dict() for record in drift if record.state != "clean")
    if not writes:
        return None, report
    updated = InstallManifest(
        manifest.payload_version,
        manifest.payload_digest,
        datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        f"waegis {WIZARD_VERSION}",
        "repair",
        dict(manifest.files),
        dict(manifest.configuration),
    )
    recovery = build_recovery_plan(runner, root, (*writes, MANIFEST_PATH))
    return PublicationPlan("repair", root, writes, (), recovery, updated), report


# END OF FILE
