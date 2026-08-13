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
@brief   Implement the filesystem-backed AEGIS workspace port.
@details Centralizes path safety, codecs, Git observation, and transactions.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any

from aegis.domain.execution import CancellationToken, ExecutionRequest, ExecutionResult
from aegis.domain.values import RepositoryPath, ValueValidationError
from aegis.infrastructure.codecs import (
    ArtifactDecodeError,
    decode_general_text,
    parse_markdown_document,
    parse_project_config,
    render_markdown_document,
    render_requirement,
)
from aegis.infrastructure.payload import load_payload_manifest, verify_payload
from aegis.infrastructure.process import execute_process
from aegis.infrastructure.transactions import (
    FileMutation,
    RecoveryError,
    RevisionConflict,
    TransactionStore,
    revision_of,
)
from aegis.ports.workspace import RepositoryMutation, WorkspaceError


class FileWorkspace:
    """@brief Provide safe repository artifact access through concrete adapters."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._transactions = TransactionStore(self.root)
        config_path = self.root / ".agentic" / "config.toml"
        try:
            self.config = parse_project_config(
                config_path.read_bytes(), path=".agentic/config.toml"
            )
        except (OSError, ArtifactDecodeError) as error:
            raise WorkspaceError(
                "malformed_state", str(error), path=".agentic/config.toml"
            ) from error

    def _path(self, path: str) -> Path:
        try:
            canonical = RepositoryPath(path)
            target = self.root.joinpath(*str(canonical).split("/"))
            probe = target if target.exists() else target.parent
            probe.resolve().relative_to(self.root)
            return target
        except (ValueValidationError, ValueError) as error:
            raise WorkspaceError(
                "repository_error", "Repository path is unsafe.", path=path
            ) from error

    def read_bytes(self, path: str) -> bytes:
        self._transactions.recover()
        target = self._path(path)
        try:
            if not target.is_file():
                raise FileNotFoundError
            return target.read_bytes()
        except OSError as error:
            raise WorkspaceError(
                "not_found", "Repository artifact was not found.", path=path
            ) from error

    def read_optional(self, path: str) -> bytes | None:
        target = self._path(path)
        if not target.exists():
            return None
        return self.read_bytes(path)

    def read_text(self, path: str) -> str:
        """@brief Read one repository text artifact through the general codec."""
        try:
            return decode_general_text(self.read_bytes(path), path=path)
        except ArtifactDecodeError as error:
            raise WorkspaceError(error.code, error.summary, path=path) from error

    def revision(self, path: str) -> str | None:
        content = self.read_optional(path)
        return None if content is None else revision_of(content)

    def path_exists(self, path: str, *, directory: bool = False) -> bool:
        """@brief Test a safe repository path without conflating emptiness."""
        self._transactions.recover()
        target = self._path(path)
        return target.is_dir() if directory else target.exists()

    def list_files(self, root: str, *, suffix: str | None = None) -> tuple[str, ...]:
        directory = self._path(root)
        if not directory.exists():
            return ()
        files = []
        for path in directory.rglob("*"):
            relative = path.relative_to(self.root).as_posix()
            if path.is_file() and (suffix is None or relative.endswith(suffix)):
                files.append(relative)
        return tuple(sorted(files))

    def git_visible_files(self, root: str) -> tuple[str, ...]:
        """@brief List safe existing tracked and unignored files below one root."""
        canonical_root = str(RepositoryPath(root))
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.root),
                    "ls-files",
                    "-z",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "--",
                    canonical_root,
                ],
                capture_output=True,
                check=True,
                shell=False,
            )
            paths = result.stdout.decode("utf-8", "strict").split("\0")
        except (OSError, UnicodeError, subprocess.CalledProcessError):
            return self.list_files(root)

        files = set()
        for path in paths:
            if not path:
                continue
            try:
                canonical = str(RepositoryPath(path))
                target = self._path(canonical)
            except (ValueValidationError, WorkspaceError):
                continue
            if target.is_file():
                files.add(canonical)
        return tuple(sorted(files))

    def publish(
        self,
        mutations: tuple[RepositoryMutation, ...],
        *,
        expected_revisions: dict[str, str | None] | None = None,
    ) -> dict[str, str | None]:
        try:
            return self._transactions.publish(
                tuple(
                    FileMutation(RepositoryPath(item.path), item.content)
                    for item in mutations
                ),
                expected_revisions=expected_revisions,
            )
        except RevisionConflict as error:
            raise WorkspaceError("state_conflict", str(error)) from error
        except RecoveryError as error:
            raise WorkspaceError("publication_failed", str(error)) from error

    def load_document(self, path: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        content = self.read_bytes(path)
        try:
            metadata, state, _ = parse_markdown_document(content, path=path)
            return metadata, state, revision_of(content)
        except ArtifactDecodeError as error:
            raise WorkspaceError(error.code, error.summary, path=path) from error

    def render_document(
        self, metadata: dict[str, Any], state: dict[str, Any], *, kind: str
    ) -> bytes:
        return render_markdown_document(metadata, state, kind=kind)

    def load_toml(self, path: str) -> tuple[dict[str, Any], str]:
        """@brief Load one exact UTF-8 TOML artifact and its revision."""
        content = self.read_bytes(path)
        try:
            return tomllib.loads(content.decode("utf-8-sig")), revision_of(content)
        except (UnicodeError, tomllib.TOMLDecodeError) as error:
            raise WorkspaceError(
                "malformed_state", "TOML artifact is malformed.", path=path
            ) from error

    def render_requirement(self, data: dict[str, Any]) -> bytes:
        """@brief Render one current Requirement through its schema codec."""
        return render_requirement(data)

    def load_instruction(self, stage: str) -> dict[str, Any]:
        path = f".agentic/aegis/workflows/{stage}.toml"
        try:
            data = tomllib.loads(self.read_bytes(path).decode("utf-8"))
            if data.get("schema") != 1 or data.get("stage") != stage:
                raise ValueError
            findings = data.get("common_findings", [])
            actions = data.get("recovery_actions", [])
            if (
                not isinstance(findings, list)
                or len(findings) > 4
                or any(
                    not isinstance(item, str) or not item or len(item) > 240
                    for item in findings
                )
                or not isinstance(actions, list)
                or len(actions) > 4
                or any(
                    not isinstance(item, dict)
                    or set(item) != {"condition", "operation", "guidance"}
                    or any(
                        not isinstance(item[key], str)
                        or not item[key]
                        or len(item[key]) > 240
                        for key in item
                    )
                    for item in actions
                )
            ):
                raise ValueError
            data["common_findings"] = findings
            data["recovery_actions"] = actions
            return data
        except (UnicodeError, tomllib.TOMLDecodeError, ValueError, KeyError) as error:
            raise WorkspaceError(
                "malformed_state", "Workflow resource is malformed.", path=path
            ) from error

    def git_snapshot(self) -> dict[str, Any]:
        def run(
            *arguments: str, check: bool = True
        ) -> subprocess.CompletedProcess[bytes]:
            return subprocess.run(
                ["git", "-C", str(self.root), *arguments],
                capture_output=True,
                check=check,
                shell=False,
            )

        try:
            branch_result = run(
                "symbolic-ref", "--quiet", "--short", "HEAD", check=False
            )
            branch = (
                branch_result.stdout.decode("utf-8", "strict").strip() or "detached"
            )
            head_result = run("rev-parse", "--verify", "HEAD", check=False)
            head = (
                head_result.stdout.decode("ascii", "strict").strip()
                if head_result.returncode == 0
                else "unborn"
            )
            status = run(
                "status", "--porcelain=v2", "-z", "--untracked-files=all"
            ).stdout
            raw_entries = [entry for entry in status.split(b"\0") if entry]
            entries = [
                entry.decode("utf-8", "surrogateescape") for entry in raw_entries
            ]
            classifications: dict[str, list[Any]] = {
                "staged": [],
                "unstaged": [],
                "untracked": [],
                "renamed": [],
                "deleted": [],
            }
            index = 0
            while index < len(entries):
                entry = entries[index]
                if entry.startswith("? "):
                    classifications["untracked"].append(entry[2:])
                    index += 1
                    continue
                if entry.startswith("1 "):
                    parts = entry.split(" ", 8)
                    xy, path, original = parts[1], parts[8], None
                elif entry.startswith("2 "):
                    parts = entry.split(" ", 9)
                    xy, path = parts[1], parts[9]
                    original = entries[index + 1] if index + 1 < len(entries) else ""
                    index += 1
                elif entry.startswith("u "):
                    parts = entry.split(" ", 10)
                    xy, path, original = parts[1], parts[10], None
                else:
                    index += 1
                    continue
                staged, unstaged = xy[0], xy[1]
                if staged != ".":
                    classifications["staged"].append({"path": path, "status": staged})
                if unstaged != ".":
                    classifications["unstaged"].append(
                        {"path": path, "status": unstaged}
                    )
                if original is not None:
                    area = "staged" if staged in {"R", "C"} else "unstaged"
                    classifications["renamed"].append(
                        {"from": original, "to": path, "area": area}
                    )
                if staged == "D":
                    classifications["deleted"].append({"path": path, "area": "staged"})
                if unstaged == "D":
                    classifications["deleted"].append(
                        {"path": path, "area": "unstaged"}
                    )
                index += 1
            index_result = run("rev-parse", "--git-path", "index")
            index_path = Path(index_result.stdout.decode("utf-8", "strict").strip())
            if not index_path.is_absolute():
                index_path = self.root / index_path
            index_revision = (
                revision_of(index_path.read_bytes()) if index_path.is_file() else None
            )
            working_files = {}
            for path in self.root.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(self.root).as_posix()
                if relative.startswith(".git/") or relative.startswith(
                    ".agentic/.runtime/"
                ):
                    continue
                working_files[relative] = revision_of(path.read_bytes())
            return {
                "branch": branch,
                "head": head,
                "entries": entries,
                "classifications": classifications,
                "index_revision": index_revision,
                "working_files": working_files,
            }
        except (OSError, UnicodeError, subprocess.CalledProcessError) as error:
            raise WorkspaceError(
                "repository_error", "Read-only Git inspection failed."
            ) from error

    def payload_findings(self) -> tuple[dict[str, Any], ...]:
        """@brief Return bounded exact-byte payload ownership findings."""
        manifest_path = self.root / ".agentic" / "aegis" / "manifest.toml"
        try:
            manifest = load_payload_manifest(manifest_path)
            return tuple(
                {
                    "label": f"F{index}",
                    "code": finding.code,
                    "severity": "warning",
                    "summary": finding.summary,
                    "disposition": "open",
                    "artifact": f".agentic/aegis/{finding.path}",
                }
                for index, finding in enumerate(
                    verify_payload(manifest_path.parent, manifest), start=1
                )
            )
        except ArtifactDecodeError as error:
            raise WorkspaceError(
                "malformed_state", error.summary, path=error.path
            ) from error

    def execute_command(
        self,
        category: str,
        name: str,
        *,
        additional_arguments: tuple[str, ...] = (),
        cancellation: CancellationToken | None = None,
    ) -> tuple[Any, ExecutionResult]:
        """@brief Execute one exact named configuration entry."""
        key = f"{category}.{name}"
        command = self.config.commands.get(key)
        if command is None:
            raise WorkspaceError(
                "not_found", "Configured validation command does not exist."
            )
        cwd = (
            self.root
            if str(command.working_directory) == "."
            else self._path(str(command.working_directory))
        )
        if not cwd.is_dir():
            raise WorkspaceError(
                "repository_error",
                "Configured working directory is unavailable.",
                path=str(command.working_directory),
            )
        result = execute_process(
            ExecutionRequest(
                command.command + additional_arguments,
                cwd,
                command.timeout_seconds,
            ),
            cancellation=cancellation,
        )
        return command, result

    def _external_path(self, path: str) -> Path:
        candidate = Path(path)
        return (
            candidate.resolve()
            if candidate.is_absolute()
            else (self.root / candidate).resolve()
        )

    def read_external_text(self, path: str) -> str:
        candidate = self._external_path(path)
        try:
            return decode_general_text(candidate.read_bytes(), path=str(candidate))
        except OSError as error:
            raise WorkspaceError(
                "not_found", "Input file was not found.", path=str(candidate)
            ) from error
        except ArtifactDecodeError as error:
            raise WorkspaceError(
                "invalid_input", error.summary, path=error.path
            ) from error

    def read_external_bytes(self, path: str) -> bytes:
        candidate = self._external_path(path)
        try:
            if not candidate.is_file():
                raise FileNotFoundError
            return candidate.read_bytes()
        except OSError as error:
            raise WorkspaceError(
                "not_found", "Input file was not found.", path=str(candidate)
            ) from error


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
