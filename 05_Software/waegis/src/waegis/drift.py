#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file drift.py
@brief Read-only installed-file drift inspection shared by analyze/check/repair.
@details Manifest paths remain untrusted until containment checks pass. Every
         finding retains its ownership disposition so maintenance authority is
         never inferred from drift alone.
"""

# IMPORTS

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .manifest import InstallManifest, contained_destination
from .ownership import Disposition


# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True, slots=True)
class DriftRecord:
    """@brief One installed path's current state against its receipt."""

    path: str
    state: str
    disposition: Disposition
    expected_sha256: str
    actual_sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "state": self.state,
            "disposition": self.disposition.value,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
        }


# EXPORTED FUNCTIONS / PUBLIC API


def inspect_drift(repository: Path, manifest: InstallManifest) -> tuple[DriftRecord, ...]:
    """@brief Compare all manifest receipts with current regular-file bytes."""
    records: list[DriftRecord] = []
    for path, expected in sorted(manifest.files.items()):
        try:
            destination = contained_destination(repository, path)
        except ValueError:
            records.append(DriftRecord(path, "unsafe", expected.disposition, expected.sha256))
            continue
        if not destination.exists():
            records.append(DriftRecord(path, "missing", expected.disposition, expected.sha256))
            continue
        if not destination.is_file():
            records.append(DriftRecord(path, "not-file", expected.disposition, expected.sha256))
            continue
        try:
            data = destination.read_bytes()
        except OSError:
            records.append(DriftRecord(path, "unreadable", expected.disposition, expected.sha256))
            continue
        actual = hashlib.sha256(data).hexdigest()
        state = "clean" if len(data) == expected.size and actual == expected.sha256 else "modified"
        records.append(DriftRecord(path, state, expected.disposition, expected.sha256, actual))
    return tuple(records)


def ownership_counts(manifest: InstallManifest) -> Mapping[str, int]:
    """@brief Count every manifest disposition for a stable health summary."""
    return {
        disposition.value: sum(record.disposition is disposition for record in manifest.files.values())
        for disposition in Disposition
    }


# END OF FILE
