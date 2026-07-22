#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_root_discovery.py
@brief Upward workflow-root discovery tests for `repo_root_from`.
@details Regression suite for the cwd-trust defect: invoking the CLI from a
         repository subdirectory used to treat that subdirectory as the
         workflow root, so `status` reported "No active agentic run" and
         `start` silently scaffolded a nested `src/.agentic/` beside the real
         install. `repo_root_from` now walks upward: the nearest ancestor
         containing an `.agentic` directory wins, then the nearest ancestor
         containing `.git`, then the candidate itself (legacy greenfield
         behavior).
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.store import repo_root_from


# HELPER FUNCTIONS


def _walk_is_contaminated(path: Path) -> bool:
    """
    @brief      Detect `.agentic`/`.git` markers in the ancestors of a test path.
    @param[in]  path Directory whose ancestors are inspected.
    @return     True when any ancestor carries a discovery marker.
    @details    The no-marker fallback tests assert that discovery returns the
                candidate itself. On a machine where an ancestor of the pytest
                temp directory is itself a git repository (for example a
                version-controlled home directory), the upward walk would
                legitimately resolve there instead, so those tests skip rather
                than report a false failure.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    return any(
        (directory / ".agentic").is_dir() or (directory / ".git").exists()
        for directory in path.parents
    )


# TESTS


def test_discovers_agentic_root_from_subdirectory(tmp_path: Path) -> None:
    """
    @brief      A repo subdirectory resolves to the ancestor holding `.agentic`.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    root = tmp_path / "project"
    (root / ".agentic").mkdir(parents=True)
    subdirectory = root / "src" / "pkg"
    subdirectory.mkdir(parents=True)

    assert repo_root_from(subdirectory) == root.resolve()


def test_falls_back_to_git_directory_root(tmp_path: Path) -> None:
    """
    @brief      Without `.agentic`, the nearest `.git` directory names the root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    subdirectory = root / "src"
    subdirectory.mkdir()

    assert repo_root_from(subdirectory) == root.resolve()


def test_falls_back_to_git_file_root(tmp_path: Path) -> None:
    """
    @brief      A `.git` file (linked worktree layout) also marks the root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    root = tmp_path / "worktree"
    root.mkdir()
    (root / ".git").write_text("gitdir: ../main/.git/worktrees/wt\n", encoding="utf-8")
    subdirectory = root / "src"
    subdirectory.mkdir()

    assert repo_root_from(subdirectory) == root.resolve()


def test_nearest_agentic_wins_over_outer_agentic(tmp_path: Path) -> None:
    """
    @brief      A nested governed project resolves to its own `.agentic` root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    outer = tmp_path / "outer"
    (outer / ".agentic").mkdir(parents=True)
    inner = outer / "inner"
    (inner / ".agentic").mkdir(parents=True)
    subdirectory = inner / "sub"
    subdirectory.mkdir()

    assert repo_root_from(subdirectory) == inner.resolve()


def test_agentic_beats_a_nearer_git_marker(tmp_path: Path) -> None:
    """
    @brief      A governed root wins over a closer vendored `.git` checkout.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    A single nearest-marker rule would resolve into the vendored
                repository and reintroduce the nested-scaffold defect there;
                the `.agentic` pass therefore runs to completion first.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    root = tmp_path / "project"
    (root / ".agentic").mkdir(parents=True)
    vendored = root / "vendor" / "lib"
    (vendored / ".git").mkdir(parents=True)
    subdirectory = vendored / "src"
    subdirectory.mkdir()

    assert repo_root_from(subdirectory) == root.resolve()


def test_heals_when_invoked_from_inside_agentic(tmp_path: Path) -> None:
    """
    @brief      A cwd inside `.agentic` resolves upward to the project root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Before upward discovery this case was a hard `SystemExit`
                (0.3.0 guard); discovery now heals it to the correct root, and
                the guard remains only as a safety net for paths that do not
                exist on disk.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    root = tmp_path / "project"
    nested = root / ".agentic" / "cli" / "src"
    nested.mkdir(parents=True)

    assert repo_root_from(nested) == root.resolve()
    assert repo_root_from(root / ".agentic") == root.resolve()


def test_without_markers_falls_back_to_candidate(tmp_path: Path) -> None:
    """
    @brief      With no marker anywhere upward, the candidate itself is the root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Preserves the greenfield behavior: `aegis start` in a brand-new
                folder still scaffolds `.agentic/` right there.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    if _walk_is_contaminated(tmp_path):
        pytest.skip("an ancestor of the pytest temp directory carries a repo marker")
    candidate = tmp_path / "fresh"
    candidate.mkdir()

    assert repo_root_from(candidate) == candidate.resolve()


def test_start_from_subdirectory_creates_run_at_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    unrestricted_workflow_toml: str,
) -> None:
    """
    @brief      `aegis start` run from a subdirectory writes under the real root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    End-to-end regression for the observed defect: previously this
                exact sequence created a second `src/.agentic/` silently.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    root = tmp_path / "project"
    (root / ".agentic").mkdir(parents=True)
    (root / ".agentic" / "workflow.toml").write_text(
        unrestricted_workflow_toml,
        encoding="utf-8",
        newline="\n",
    )
    subdirectory = root / "src"
    subdirectory.mkdir()
    monkeypatch.chdir(subdirectory)

    main(["start", "--kind", "fix", "--statement", "root discovery regression"])

    payload = json.loads(capsys.readouterr().out)
    assert (root / ".agentic" / "runs" / payload["run_id"] / "graph.json").is_file()
    assert not (subdirectory / ".agentic").exists()


def test_status_from_subdirectory_finds_active_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    unrestricted_workflow_toml: str,
) -> None:
    """
    @brief      `aegis status` from a subdirectory reports the root's active run.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @param[in]  capsys Pytest capture fixture.
    @param[in]  unrestricted_workflow_toml Complete strict workflow config.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    root = tmp_path / "project"
    (root / ".agentic").mkdir(parents=True)
    (root / ".agentic" / "workflow.toml").write_text(
        unrestricted_workflow_toml,
        encoding="utf-8",
        newline="\n",
    )
    subdirectory = root / "src"
    subdirectory.mkdir()
    monkeypatch.chdir(root)
    main(["start", "--kind", "fix", "--statement", "root discovery regression"])
    started = json.loads(capsys.readouterr().out)

    monkeypatch.chdir(subdirectory)
    main(["status"])

    reported = json.loads(capsys.readouterr().out)
    assert reported["run_id"] == started["run_id"]


# END OF FILE
