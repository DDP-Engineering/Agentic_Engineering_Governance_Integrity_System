#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_git_safety.py
@brief Integration tests for clean-tree recovery and lock contracts.
@details Uses disposable local repositories and executes emitted commands
         verbatim; no network or history mutation occurs in WAEGIS code.
"""

import json
import socket
import subprocess
from pathlib import Path

import pytest

from waegis.gitsafety import (
    SafetyError,
    acquire_lock,
    build_recovery_plan,
    dirty_paths,
    execute_recovery,
    lock_path,
    require_clean,
    require_repository,
)
from waegis.runner import CommandRunner


RUNNER = CommandRunner()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("git", "-C", str(repo), *args), text=True, capture_output=True, check=True)


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "WAEGIS Tests")
    (repo / "tracked.txt").write_text("before\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "baseline")
    return repo


def test_repository_requires_exact_root_and_committed_head(tmp_path: Path) -> None:
    """@brief R3 refuses non-roots and repositories without a recovery HEAD."""
    repo = _repository(tmp_path)
    assert require_repository(RUNNER, repo) == repo.resolve()
    nested = repo / "nested"
    nested.mkdir()
    with pytest.raises(SafetyError, match="repository root"):
        require_repository(RUNNER, nested)
    empty = tmp_path / "empty"
    empty.mkdir()
    _git(empty, "init")
    with pytest.raises(SafetyError, match="initial commit"):
        require_repository(RUNNER, empty)


def test_dirty_report_includes_staged_unstaged_untracked_and_renamed(tmp_path: Path) -> None:
    """@brief R3 lists every dirty path and provides no bypass."""
    repo = _repository(tmp_path)
    (repo / "tracked.txt").write_text("unstaged\n", encoding="utf-8")
    (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    paths = dirty_paths(RUNNER, repo)
    assert set(paths) == {"staged.txt", "tracked.txt", "untracked.txt"}
    with pytest.raises(SafetyError, match="commit or stash"):
        require_clean(RUNNER, repo)


def test_exact_recovery_restores_tracked_and_removes_only_planned_new_files(tmp_path: Path) -> None:
    """@brief R3 emitted Git commands restore one complete precomputed write set."""
    repo = _repository(tmp_path)
    plan = build_recovery_plan(RUNNER, repo, ["tracked.txt", ".agentic/new.txt"])
    assert plan.tracked == ("tracked.txt",)
    assert plan.new == (".agentic/new.txt",)
    assert all(" -- " in rendered for rendered in plan.rendered())
    (repo / "tracked.txt").write_text("after\n", encoding="utf-8")
    (repo / ".agentic").mkdir()
    (repo / ".agentic" / "new.txt").write_text("new\n", encoding="utf-8")
    ignored = repo / "unrelated.ignored"
    ignored.write_text("keep\n", encoding="utf-8")
    execute_recovery(RUNNER, plan)
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "before\n"
    assert not (repo / ".agentic" / "new.txt").exists()
    assert ignored.read_text(encoding="utf-8") == "keep\n"


def test_existing_ignored_destination_is_refused_before_mutation(tmp_path: Path) -> None:
    """@brief R3 does not misclassify a pre-existing ignored file as recoverable new state."""
    repo = _repository(tmp_path)
    (repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore")
    (repo / "ignored.txt").write_text("local\n", encoding="utf-8")
    require_clean(RUNNER, repo)
    with pytest.raises(SafetyError, match="not tracked"):
        build_recovery_plan(RUNNER, repo, ["ignored.txt"])


def test_lock_requires_explicit_proven_dead_owner_and_token_safe_release(tmp_path: Path) -> None:
    """@brief R3 time alone never breaks a lock and live owners remain protected."""
    repo = _repository(tmp_path)
    first = acquire_lock(RUNNER, repo, "adopt")
    with pytest.raises(SafetyError, match="--break-lock"):
        acquire_lock(RUNNER, repo, "repair")
    with pytest.raises(SafetyError, match="live or cannot"):
        acquire_lock(RUNNER, repo, "repair", break_lock=True)
    replacement = dict(first.metadata)
    replacement["token"] = "replacement"
    first.path.write_text(json.dumps(replacement), encoding="utf-8")
    first.release()
    assert first.path.exists()


def test_dead_owner_lock_can_be_broken_explicitly(tmp_path: Path) -> None:
    """@brief A same-host dead PID is the only automatic proof accepted."""
    repo = _repository(tmp_path)
    path = lock_path(RUNNER, repo)
    metadata = {
        "schema_version": 1,
        "pid": 2_000_000_000,
        "host": socket.gethostname(),
        "command": "adopt",
        "repository": str(repo.resolve()),
        "started_at": "2000-01-01T00:00:00Z",
        "token": "dead",
    }
    path.write_text(json.dumps(metadata), encoding="utf-8")
    lock = acquire_lock(RUNNER, repo, "repair", break_lock=True)
    assert lock.metadata["token"] != "dead"
    lock.release()
    assert not path.exists()


def test_invalid_lock_metadata_is_preserved(tmp_path: Path) -> None:
    """@brief Invalid evidence fails closed even with explicit break intent."""
    repo = _repository(tmp_path)
    path = lock_path(RUNNER, repo)
    path.write_text("invalid", encoding="utf-8")
    with pytest.raises(SafetyError, match="preserve and inspect"):
        acquire_lock(RUNNER, repo, "repair", break_lock=True)
    assert path.read_text(encoding="utf-8") == "invalid"


# END OF FILE
