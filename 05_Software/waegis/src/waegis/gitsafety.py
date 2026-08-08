#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file gitsafety.py
@brief Clean-tree preconditions, exact recovery plans, and one repository lock.
@details Uses Git as the existing-repository recovery baseline. No bypass,
         history mutation, persistent operation state, or age-only lock break
         exists.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import shlex
import socket
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .gitops import GitError, require_git_success, run_git
from .manifest import canonical_path
from .runner import Runner


# DATA MODELS / TYPEDEFINITIONS


class SafetyError(RuntimeError):
    """@brief Raised when mutation preconditions or exact recovery fail."""


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """@brief Exact tracked/new path recovery commands computed before consent."""

    repository: Path
    head: str
    tracked: tuple[str, ...]
    new: tuple[str, ...]

    def commands(self) -> tuple[tuple[str, ...], ...]:
        """@brief Return path-scoped Git commands with explicit path separators."""
        prefix = ("git", "-C", str(self.repository))
        commands: list[tuple[str, ...]] = []
        if self.tracked:
            commands.append((*prefix, "restore", "--source=HEAD", "--staged", "--worktree", "--", *self.tracked))
        if self.new:
            commands.append((*prefix, "clean", "-fdx", "--", *self.new))
        return tuple(commands)

    def rendered(self) -> tuple[str, ...]:
        """@brief Render commands for operator-visible recovery evidence."""
        if os.name == "nt":
            return tuple(subprocess.list2cmdline(command) for command in self.commands())
        return tuple(shlex.join(command) for command in self.commands())

    def to_dict(self) -> dict[str, object]:
        """@brief Convert the recovery plan to the JSON stderr record."""
        return {
            "kind": "git-path-recovery",
            "repository": str(self.repository),
            "head": self.head,
            "tracked": list(self.tracked),
            "new": list(self.new),
            "commands": list(self.rendered()),
        }


@dataclass(slots=True)
class RepoLock:
    """@brief One O_EXCL lock with visible owner metadata and token-safe release."""

    path: Path
    token: str
    metadata: dict[str, object]
    _held: bool = True

    def release(self) -> None:
        """@brief Remove this invocation's lock without deleting a replacement."""
        if not self._held:
            return
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            self._held = False
            return
        if isinstance(current, dict) and current.get("token") == self.token:
            self.path.unlink(missing_ok=True)
        self._held = False

    def __enter__(self) -> RepoLock:
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        self.release()


# HELPER FUNCTIONS


def _parse_porcelain_z(value: str) -> tuple[str, ...]:
    fields = value.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise SafetyError("git status returned an unrecognized porcelain record")
        status = record[:2]
        path = record[3:].replace("\\", "/")
        paths.add(path)
        if "R" in status or "C" in status:
            if index >= len(fields) or not fields[index]:
                raise SafetyError("git status returned an incomplete rename/copy record")
            paths.add(fields[index].replace("\\", "/"))
            index += 1
    return tuple(sorted(paths, key=lambda item: item.encode("utf-8")))


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_lock(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SafetyError(f"lock metadata is invalid at {path}; preserve and inspect it") from exc
    required = {"schema_version", "pid", "host", "command", "repository", "started_at", "token"}
    if not isinstance(value, dict) or set(value) != required:
        raise SafetyError(f"lock metadata is invalid at {path}; preserve and inspect it")
    return value


# EXPORTED FUNCTIONS / PUBLIC API


def require_repository(runner: Runner, repository: Path) -> Path:
    """
    @brief Require an existing Git root with a valid committed HEAD.
    @param[in] runner Git subprocess runner.
    @param[in] repository Candidate root.
    @return Resolved exact repository root.
    @exception SafetyError If the target is not the root of a committed repository.
    """
    try:
        root = repository.resolve(strict=True)
    except OSError as exc:
        raise SafetyError(f"repository does not exist: {repository}") from exc
    top = run_git(runner, root, ("rev-parse", "--show-toplevel"))
    try:
        require_git_success(top, "rev-parse --show-toplevel")
    except GitError as exc:
        raise SafetyError(str(exc)) from exc
    reported = Path(top.stdout.strip()).resolve()
    if reported != root:
        raise SafetyError(f"target must be the Git repository root: {reported}")
    head = run_git(runner, root, ("rev-parse", "--verify", "HEAD"))
    if head.returncode != 0:
        raise SafetyError("repository requires an initial commit before this command")
    return root


def dirty_paths(runner: Runner, repository: Path) -> tuple[str, ...]:
    """@brief Return every staged, unstaged, renamed, and untracked path."""
    result = run_git(runner, repository, ("status", "--porcelain=v1", "-z", "--untracked-files=all"))
    try:
        require_git_success(result, "status")
    except GitError as exc:
        raise SafetyError(str(exc)) from exc
    return _parse_porcelain_z(result.stdout)


def require_clean(runner: Runner, repository: Path) -> None:
    """@brief Enforce the absolute clean committed-tree mutation precondition."""
    paths = dirty_paths(runner, repository)
    if paths:
        rendered = "\n  ".join(paths)
        raise SafetyError(f"repository is not clean; commit or stash these paths:\n  {rendered}")


def head_oid(runner: Runner, repository: Path) -> str:
    """@brief Read the exact committed baseline used by a mutation plan."""
    result = run_git(runner, repository, ("rev-parse", "--verify", "HEAD"))
    try:
        require_git_success(result, "rev-parse --verify HEAD")
    except GitError as exc:
        raise SafetyError(str(exc)) from exc
    value = result.stdout.strip().casefold()
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise SafetyError("git returned an invalid HEAD object ID")
    return value


def require_planned_head(runner: Runner, plan: RecoveryPlan) -> None:
    """@brief Refuse a plan if its committed baseline changed before apply."""
    current = head_oid(runner, plan.repository)
    if current != plan.head:
        raise SafetyError(f"repository HEAD changed after planning: expected {plan.head}, found {current}; rerun the command")


def tracked_paths(runner: Runner, repository: Path, paths: Iterable[str]) -> frozenset[str]:
    """@brief Return the subset of canonical paths tracked by the index."""
    requested = tuple(sorted({canonical_path(path) for path in paths}, key=lambda item: item.encode("utf-8")))
    if not requested:
        return frozenset()
    result = run_git(runner, repository, ("ls-files", "-z", "--", *requested))
    try:
        require_git_success(result, "ls-files")
    except GitError as exc:
        raise SafetyError(str(exc)) from exc
    return frozenset(path.replace("\\", "/") for path in result.stdout.split("\0") if path)


def build_recovery_plan(runner: Runner, repository: Path, write_paths: Iterable[str]) -> RecoveryPlan:
    """
    @brief Classify the complete precomputed write set into exact Git recovery.
    @param[in] runner Git subprocess runner.
    @param[in] repository Clean repository root.
    @param[in] write_paths Complete canonical destinations, including manifest.
    @return Deterministic recovery plan.
    """
    paths = tuple(sorted({canonical_path(path) for path in write_paths}, key=lambda item: item.encode("utf-8")))
    tracked = tracked_paths(runner, repository, paths)
    existing_untracked = [path for path in paths if (repository.joinpath(*path.split("/"))).exists() and path not in tracked]
    if existing_untracked:
        raise SafetyError(
            "managed destinations exist but are not tracked; preserve or remove them before adoption: "
            + ", ".join(existing_untracked)
        )
    return RecoveryPlan(
        repository,
        head_oid(runner, repository),
        tuple(path for path in paths if path in tracked),
        tuple(path for path in paths if path not in tracked),
    )


def execute_recovery(runner: Runner, plan: RecoveryPlan) -> None:
    """@brief Execute the exact preprinted recovery commands in order."""
    for command in plan.commands():
        result = runner.run(command, cwd=plan.repository, timeout=60)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
            raise SafetyError(f"recovery command failed: {detail}")


def lock_path(runner: Runner, repository: Path) -> Path:
    """@brief Resolve the one lock inside the actual Git directory/worktree."""
    result = run_git(runner, repository, ("rev-parse", "--git-path", "waegis-v3.lock"))
    try:
        require_git_success(result, "rev-parse --git-path")
    except GitError as exc:
        raise SafetyError(str(exc)) from exc
    candidate = Path(result.stdout.strip())
    return candidate.resolve() if candidate.is_absolute() else (repository / candidate).resolve()


def acquire_lock(
    runner: Runner,
    repository: Path,
    command: str,
    *,
    break_lock: bool = False,
) -> RepoLock:
    """
    @brief Acquire the one repository lock, optionally breaking a proven dead owner.
    @param[in] runner Git subprocess runner.
    @param[in] repository Repository root.
    @param[in] command Mutating WAEGIS command.
    @param[in] break_lock Explicit operator dead-owner instruction.
    @return Held token-safe lock.
    @exception SafetyError If a live, foreign, or invalid lock exists.
    """
    path = lock_path(runner, repository)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        current = _read_lock(path)
        same_host = current["host"] == socket.gethostname()
        pid = current["pid"]
        dead = same_host and isinstance(pid, int) and not isinstance(pid, bool) and not _pid_alive(pid)
        if not break_lock:
            raise SafetyError(f"WAEGIS lock already exists at {path}; use --break-lock only after confirming its owner is dead")
        if not dead:
            raise SafetyError(f"WAEGIS lock owner is live or cannot be proven dead: {current}")
        path.unlink()
    token = uuid.uuid4().hex
    metadata: dict[str, object] = {
        "schema_version": 1,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "command": command,
        "repository": str(repository.resolve()),
        "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "token": token,
    }
    encoded = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise SafetyError(f"another WAEGIS process acquired the lock at {path}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return RepoLock(path, token, metadata)


# END OF FILE
