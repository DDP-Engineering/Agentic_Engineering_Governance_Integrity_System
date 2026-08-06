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


def test_renaming_a_protected_file_is_still_a_protected_path_finding(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      A rename out of a protected location does not evade the guard.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  replace_workflow_toml Shared policy-fragment fixture.
    @return     None.
    @details    Regression test (B2, 2026-08-04): the protected-path and
                blocked-pattern checks tested the bare `entry["path"]`, which
                for an `R`/`C` porcelain entry is the *destination*. Three lines
                above, the adoption-source check already used `_entry_paths`,
                which returns Git's `previous_path` too - so the asymmetry was
                an oversight in a function whose docstring says it has to fail
                closed. `git mv config/secrets.yaml …` moved a protected file
                out of its protected location and produced no finding at all.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
        '[guardrails.protected_paths]\nmode = "enforce"\n'
        'patterns = ["config/secrets.yaml"]\noperations = ["write"]',
    )
    _init_repo(tmp_path)
    protected = tmp_path / "config" / "secrets.yaml"
    protected.parent.mkdir()
    protected.write_text("token: value\n", encoding="utf-8")
    _git(tmp_path, "add", "config/secrets.yaml")
    _commit(tmp_path, "add protected file")
    _git(tmp_path, "mv", "config/secrets.yaml", "config/legacy-secrets.yaml")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert [
        finding["path"]
        for finding in report["blocking_findings"]
        if finding["code"] == "protected-path"
    ] == ["config/secrets.yaml"]


def test_blocked_pattern_also_matches_a_rename_source(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      The blocked-pattern check reads both paths of a rename too.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  replace_workflow_toml Shared policy-fragment fixture.
    @return     None.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
        '[guardrails.working_tree]\nmode = "restricted"\n'
        'blocked_patterns = ["generated/**"]',
    )
    _init_repo(tmp_path)
    generated = tmp_path / "generated" / "bundle.js"
    generated.parent.mkdir()
    generated.write_text("// bundle\n", encoding="utf-8")
    _git(tmp_path, "add", "generated/bundle.js")
    _commit(tmp_path, "add generated file")
    _git(tmp_path, "mv", "generated/bundle.js", "dist-bundle.js")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert [
        finding["path"]
        for finding in report["blocking_findings"]
        if finding["code"] == "blocked-pattern"
    ] == ["generated/bundle.js"]


@pytest.mark.skipif(
    os.name == "nt",
    reason="A backslash is not a legal filename character on Windows.",
)
def test_backslash_in_a_posix_filename_is_not_translated(tmp_path: Path) -> None:
    """
    @brief      A literal backslash in a filename survives status decoding.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Regression test (B7, 2026-08-04): `_unquote_git_path(...)
                .replace("\\\\", "/")` ran *after* unquoting. Git emits `/` as
                its separator on every platform, so the replacement could only
                ever fire on a backslash the unquoting had just correctly
                recovered - turning `data\\report.csv` into the non-existent
                `data/report.csv`, against which no protected pattern could
                match and the secret scan read nothing.
    @exception  None
    """
    _init_repo(tmp_path)
    (tmp_path / "data\\report.csv").write_text("value\n", encoding="utf-8")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert report["untracked"] == [{"status": "??", "path": "data\\report.csv"}]


def _git(repo_root: Path, *arguments: str) -> None:
    """@brief Run one Git command in the fixture repository."""
    subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


def _commit(repo_root: Path, message: str) -> None:
    """@brief Commit the index with a deterministic identity."""
    subprocess.run(
        ["git", "commit", "-m", message],
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
