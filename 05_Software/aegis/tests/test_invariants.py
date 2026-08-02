#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_invariants.py
@brief Workflow support module for test_invariants.
@details Covers expected workflow behavior through focused pytest checks.
"""

# IMPORTS

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess

from aegis.check_execution import _update_check_states
from aegis.config import RuleSetPolicy, WorkflowConfig, load_config
from aegis.invariants import _clean_secrets, _no_regression, _red_before_green
from aegis.models import Check, Evidence
from aegis.store import init_graph


# LOCAL HELPERS


def init_repo_with_commit(tmp_path: Path) -> None:
    """
    @brief      Initialize a Git repo with one committed file.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True)


def secret_config(repo_root: Path) -> WorkflowConfig:
    """
    @brief      Build a WorkflowConfig with one secret-like regex configured.
    @param[in]  repo_root Repository containing the complete workflow config.
    @return     Valid workflow configuration with secret enforcement enabled.
    @exception  None
    """
    return replace(
        load_config(repo_root),
        secrets=RuleSetPolicy(mode="enforce", patterns=(r"sk-[A-Za-z0-9_-]{20,}",)),
    )


# TESTS


def test_clean_secrets_detects_staged_file(tmp_path: Path) -> None:
    """
    @brief      A secret in a staged-but-uncommitted file fails INV-7.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18): the
                previous `git diff` (unstaged only) never showed a file that
                had already been `git add`-ed, so a secret committed via
                `git add` then left staged would silently pass INV-7.
    @exception  None
    """
    init_repo_with_commit(tmp_path)
    (tmp_path / "config.py").write_text("TOKEN = 'sk-abcdefghijklmnopqrstuvwx'\n", encoding="utf-8")
    subprocess.run(["git", "add", "config.py"], cwd=tmp_path, check=True, capture_output=True)

    result = _clean_secrets(tmp_path, secret_config(tmp_path))

    assert result.holds is False


def test_clean_secrets_detects_untracked_file(tmp_path: Path) -> None:
    """
    @brief      A secret in a brand-new untracked file fails INV-7.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18): a
                newly created file has no committed history to diff against,
                so it never appeared in a plain `git diff` at all; the fix
                reads untracked file content directly via `git ls-files
                --others --exclude-standard`.
    @exception  None
    """
    init_repo_with_commit(tmp_path)
    (tmp_path / "new_file.py").write_text("TOKEN = 'sk-abcdefghijklmnopqrstuvwx'\n", encoding="utf-8")

    result = _clean_secrets(tmp_path, secret_config(tmp_path))

    assert result.holds is False


def test_clean_secrets_passes_for_untracked_file_without_secret(tmp_path: Path) -> None:
    """
    @brief      A clean untracked file does not trip INV-7.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    init_repo_with_commit(tmp_path)
    (tmp_path / "notes.md").write_text("Nothing sensitive here.\n", encoding="utf-8")

    result = _clean_secrets(tmp_path, secret_config(tmp_path))

    assert result.holds is True


def test_green_rerun_retires_failed_attempts_for_inv4_and_inv3(
    tmp_path: Path,
) -> None:
    """
    @brief      A genuine pass after failed attempts satisfies INV-4 and INV-3.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    End-to-end over the shared state-update rule: a check-stage red
                witness, a failed implementation attempt, then a genuine pass.
                The failed attempt is retired so INV-4 no longer reports a live
                regression, while the check-stage red stays active so INV-3's
                red-before-green link survives.
    """
    graph = init_graph(tmp_path, "fix", "Reconcile check evidence")
    graph.checks = [
        Check(id="CHK-001", level="unit", cites_spec=[], command="pytest -q")
    ]
    graph.evidence = [
        Evidence(
            id="E-0001",
            kind="test-run",
            result="fail",
            summary="red witness",
            stage="check",
            check_id="CHK-001",
            exit_status=1,
        ),
        Evidence(
            id="E-0002",
            kind="test-run",
            result="fail",
            summary="launcher denied",
            stage="implementation",
            check_id="CHK-001",
            exit_status=127,
        ),
    ]
    fresh_pass = Evidence(
        id="E-0003",
        kind="test-run",
        result="pass",
        summary="observed pass",
        stage="implementation",
        check_id="CHK-001",
        exit_status=0,
    )
    graph.evidence.append(fresh_pass)

    _update_check_states(graph, [fresh_pass])

    config = load_config(tmp_path)
    assert _no_regression(graph, config).holds is True
    assert _red_before_green(graph).holds is True
    assert graph.checks[0].red_evidence == "E-0001"
    assert graph.checks[0].green_evidence == "E-0003"


def test_regressed_check_still_fails_inv4(tmp_path: Path) -> None:
    """
    @brief      A rerun failure after a pass keeps INV-4 honestly failing.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    """
    graph = init_graph(tmp_path, "fix", "Expose a genuine regression")
    graph.checks = [
        Check(id="CHK-001", level="unit", cites_spec=[], command="pytest -q")
    ]
    graph.evidence = [
        Evidence(
            id="E-0001",
            kind="test-run",
            result="pass",
            summary="previously green",
            stage="implementation",
            check_id="CHK-001",
            exit_status=0,
        ),
    ]
    regression = Evidence(
        id="E-0002",
        kind="test-run",
        result="fail",
        summary="assertion failed",
        stage="implementation",
        check_id="CHK-001",
        exit_status=1,
    )
    graph.evidence.append(regression)

    _update_check_states(graph, [regression])

    config = load_config(tmp_path)
    assert _no_regression(graph, config).holds is False
    assert graph.checks[0].state == "red"


# END OF FILE
