#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    workspace.py
@brief   Define the repository workspace port used by application operations.
@details Keeps filesystem, Git, codec, and transaction adapters outside use cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from aegis.domain.configuration import ProjectConfig
from aegis.domain.execution import CancellationToken, ExecutionResult


class WorkspaceError(RuntimeError):
    """@brief Carry one structured repository or state failure."""

    def __init__(self, code: str, summary: str, *, path: str | None = None) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.path = path


@dataclass(frozen=True, slots=True)
class RepositoryMutation:
    """@brief Describe one repository-relative create, update, or deletion."""

    path: str
    content: bytes | None


class Workspace(Protocol):
    """@brief Expose bounded artifact and observation capabilities."""

    root: Path
    config: ProjectConfig

    def read_bytes(self, path: str) -> bytes: ...
    def read_optional(self, path: str) -> bytes | None: ...
    def read_text(self, path: str) -> str: ...
    def revision(self, path: str) -> str | None: ...
    def path_exists(
        self, path: str, *, directory: bool = False, recover: bool = True
    ) -> bool: ...
    def pending_recovery_paths(
        self, *, limit: int
    ) -> tuple[tuple[str, ...], int]: ...
    def list_files(
        self, root: str, *, suffix: str | None = None
    ) -> tuple[str, ...]: ...
    def git_visible_files(self, root: str) -> tuple[str, ...]: ...
    def publish(
        self,
        mutations: tuple[RepositoryMutation, ...],
        *,
        expected_revisions: dict[str, str | None] | None = None,
    ) -> dict[str, str | None]: ...
    def load_document(
        self, path: str
    ) -> tuple[dict[str, Any], dict[str, Any], str]: ...
    def render_document(
        self, metadata: dict[str, Any], state: dict[str, Any], *, kind: str
    ) -> bytes: ...
    def load_toml(self, path: str) -> tuple[dict[str, Any], str]: ...
    def render_requirement(self, data: dict[str, Any]) -> bytes: ...
    def load_instruction(self, stage: str) -> dict[str, Any]: ...
    def git_snapshot(self) -> dict[str, Any]: ...
    def payload_findings(self) -> tuple[dict[str, Any], ...]: ...
    def execute_command(
        self,
        category: str,
        name: str,
        *,
        additional_arguments: tuple[str, ...] = (),
        cancellation: CancellationToken | None = None,
    ) -> tuple[Any, ExecutionResult]: ...
    def read_external_text(self, path: str) -> str: ...
    def read_external_bytes(self, path: str) -> bytes: ...


class WorkspaceFactory(Protocol):
    """@brief Construct one concrete workspace for an installed repository."""

    def __call__(self, root: Path) -> Workspace: ...


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
