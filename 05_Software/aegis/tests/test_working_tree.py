#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_working_tree.py
@brief Deterministic working-tree review tests for AEGIS 2.
@details Covers untracked reporting, configured blockers, Unicode paths,
         adoption source protection, and fail-closed Git diagnostics.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 2.0.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import subprocess

import pytest

from aegis.config import load_config
from aegis.models import Graph, Intent
from aegis.working_tree import audit_working_tree

# TESTS


def test_audit_reports_untracked_file_without_blocking(tmp_path: Path) -> None:
    """@brief Treat ordinary untracked files as review input, not failure."""
    _init_repo(tmp_path)
    (tmp_path / "meeting-notes.md").write_text("Notes.\n", encoding="utf-8")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert report["blocking_findings"] == []
    assert report["untracked"] == [{"status": "??", "path": "meeting-notes.md"}]


def test_audit_matches_configured_blocker_and_unicode_path(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Match blocked globs after Git path decoding."""
    replace_workflow_toml(
        '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
        '[guardrails.working_tree]\nmode = "restricted"\n'
        'blocked_patterns = ["generated/**"]',
    )
    _init_repo(tmp_path)
    path = tmp_path / "generated" / "café.txt"
    path.parent.mkdir()
    path.write_text("Generated.\n", encoding="utf-8")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert report["blocking_findings"][0]["code"] == "blocked-pattern"
    assert report["blocking_findings"][0]["path"] == "generated/café.txt"


def test_adoption_source_change_is_blocked(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Keep adoption delivery from silently changing application code."""
    replace_workflow_toml(
        '[adoption.source_changes]\nmode = "unrestricted"',
        '[adoption.source_changes]\nmode = "blocked"',
    )
    _init_repo(tmp_path)
    source = tmp_path / "src" / "app.py"
    source.parent.mkdir()
    source.write_text("print('changed')\n", encoding="utf-8")
    graph = Graph(
        run_id="adoption-20260729T120000Z-abcdef12",
        stage="adoption-delivery",
        intent=Intent(id="I-1", kind="adoption", statement="Adopt repository"),
    )

    report = audit_working_tree(tmp_path, load_config(tmp_path), graph)

    assert any(
        finding["code"] == "ADOPTION-SOURCE-CHANGE"
        for finding in report["blocking_findings"]
    )


def test_non_repository_fails_closed(tmp_path: Path) -> None:
    """@brief Report unavailable Git state as a blocking finding."""
    report = audit_working_tree(tmp_path, load_config(tmp_path))
    assert report["blocking_findings"][0]["code"] == "git-status-unavailable"


def test_missing_git_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Convert a missing executable into deterministic review failure."""
    def unavailable(*args: object, **kwargs: object) -> None:
        """@brief Simulate a host without Git."""
        raise FileNotFoundError("git missing")

    monkeypatch.setattr(subprocess, "run", unavailable)
    report = audit_working_tree(tmp_path, load_config(tmp_path))
    assert report["blocking_findings"][0]["code"] == "git-status-unavailable"


def _init_repo(repo_root: Path) -> None:
    """@brief Initialize and commit the generated schema-3 policy."""
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", ".agentic/workflow.toml"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "workflow config"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


# END OF FILE
