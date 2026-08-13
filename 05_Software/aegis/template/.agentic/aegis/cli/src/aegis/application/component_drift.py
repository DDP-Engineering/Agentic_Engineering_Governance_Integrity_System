#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    component_drift.py
@brief   Capture and compare exact-byte Component member digest baselines.
@details Keeps declared-member drift semantics deterministic and read-only.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from aegis.ports.workspace import Workspace, WorkspaceError


def capture_file_digests(
    workspace: Workspace, file_paths: list[str]
) -> dict[str, str]:
    """
    @brief Capture SHA-256 digests for safely readable declared members.
    @param[in] workspace Repository reader used without mutation.
    @param[in] file_paths Declared repository-relative member paths.
    @return Deterministically ordered path-to-digest baselines.
    """
    digests: dict[str, str] = {}
    for path in sorted(set(file_paths)):
        try:
            content = workspace.read_optional(path)
        except WorkspaceError:
            continue
        if content is not None:
            digests[path] = sha256(content).hexdigest()
    return digests


def compare_file_digests(
    workspace: Workspace,
    file_paths: list[str],
    recorded: Any,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """
    @brief Compare readable declared members with one recorded baseline.
    @param[in] workspace Repository reader used without mutation.
    @param[in] file_paths Declared repository-relative member paths.
    @param[in] recorded Persisted path-to-digest baseline, possibly absent.
    @return Changed paths followed by readable paths without a baseline.
    """
    baselines = recorded if isinstance(recorded, dict) else {}
    changed: list[str] = []
    unreviewed: list[str] = []
    current = capture_file_digests(workspace, file_paths)
    for path, digest in current.items():
        baseline = baselines.get(path)
        if not isinstance(baseline, str) or not baseline:
            unreviewed.append(path)
        elif baseline != digest:
            changed.append(path)
    return tuple(changed), tuple(unreviewed)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
