#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Inspect archive paths, exact inventory, digests, and runtime declarations."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import PurePosixPath
from typing import Any


class InspectionError(ValueError):
    """Report an archive that is unsafe, inconsistent, or non-exact."""


def _safe(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
    )


def inspect_archive(path) -> dict[str, Any]:
    """Verify an archive entirely before any caller extracts it."""
    try:
        with zipfile.ZipFile(path) as bundle:
            names = [entry.filename for entry in bundle.infolist()]
            if len(names) != len(set(names)) or not all(_safe(name) for name in names):
                raise InspectionError("Archive contains an unsafe or duplicate path")
            if "ARCHIVE_INVENTORY.json" not in names:
                raise InspectionError("Archive inventory is missing")
            try:
                inventory = json.loads(
                    bundle.read("ARCHIVE_INVENTORY.json").decode("utf-8")
                )
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise InspectionError("Archive inventory is invalid") from exc
            declared = {entry["path"]: entry for entry in inventory.get("files", [])}
            actual = set(names) - {"ARCHIVE_INVENTORY.json"}
            if actual != set(declared):
                raise InspectionError(
                    "Archive inventory does not match archive members"
                )
            for name, entry in declared.items():
                content = bundle.read(name)
                if len(content) != entry.get("size") or hashlib.sha256(
                    content
                ).hexdigest() != entry.get("sha256"):
                    raise InspectionError(f"Archive inventory digest mismatch: {name}")
            lowered = {name.lower() for name in names}
            if any(name.endswith("pyvenv.cfg") for name in lowered):
                raise InspectionError(
                    "Archive contains a persistent virtual-environment marker"
                )
            bundled = bool(inventory.get("with_dependencies"))
            runtime_members = [
                name
                for name in names
                if name.startswith("runtime/")
                or name.startswith(".agentic/aegis/runtime/")
            ]
            if not bundled and runtime_members:
                raise InspectionError(
                    "External-runtime archive unexpectedly contains runtime files"
                )
            if bundled and not inventory.get("runtime_inputs"):
                raise InspectionError("Bundled archive has no locked runtime inputs")
            return {
                "product": inventory.get("product"),
                "platform": inventory.get("platform"),
                "with_dependencies": bundled,
                "file_count": len(declared),
            }
    except zipfile.BadZipFile as exc:
        raise InspectionError("Archive is not a valid ZIP file") from exc
