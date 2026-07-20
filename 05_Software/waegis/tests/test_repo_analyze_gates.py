#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repo_analyze_gates.py
@brief Tests for gate-command candidate extraction with provenance (T5.1 §9).
@details Every extracted candidate must name its source file and locator, must
         never be executed, and a shell-syntax line that ``shlex`` cannot
         safely split must become a "manual review required" candidate rather
         than a wrong argv. Offline: the walk-fallback runner is used so no git
         is invoked; candidate extraction reads marker files from disk.
@author Eng. Dan Dumitru Pasare
@date 2026-07-14
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

from waegis.repo import analyze
from waegis.probes.runner import CommandResult

# LOCAL HELPERS


class _NoGitRunner:
    """
    @brief Fake :class:`CommandRunner` forcing the walk inventory fallback.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    def run(self, argv, *, timeout: float = 5.0, cwd=None) -> CommandResult:
        """
        @brief      Always report "not found".
        @param[in]  argv Ignored.
        @param[in]  timeout Ignored.
        @param[in]  cwd Ignored.
        @return     A not-found :class:`CommandResult`.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return CommandResult(found=False, exit_code=None, stdout="", stderr="")


def _write(repo: Path, rel_path: str, content: str) -> None:
    """
    @brief      Write a fixture file, creating parent directories.
    @param[in]  repo Repository root.
    @param[in]  rel_path Repo-relative path.
    @param[in]  content File content.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _analyze(repo: Path) -> analyze.RepoAnalysis:
    """
    @brief      Run the full analysis over a repo via the walk fallback.
    @param[in]  repo Repository root.
    @return     The analysis result.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return analyze.analyze_repo(repo, runner=_NoGitRunner())


# TESTS

# --- Makefile -----------------------------------------------------------------


def test_makefile_test_and_lint_targets_both_extracted(tmp_path: Path) -> None:
    """
    @brief      A Makefile with ``test:`` and ``lint:`` targets yields both
                candidates as ``make <target>`` with target provenance.
    @return     None
    @exception  AssertionError If either candidate is missing or misattributed.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(tmp_path, "Makefile", "test:\n\tpytest -q\n\nlint:\n\truff check .\n")

    result = _analyze(tmp_path)

    test = next(c for c in result.gate_test_cmds if c.source_file == "Makefile")
    lint = next(c for c in result.gate_lint_cmds if c.source_file == "Makefile")
    assert test.argv == ("make", "test")
    assert test.source_detail == "target 'test'"
    assert lint.argv == ("make", "lint")
    assert lint.source_detail == "target 'lint'"


def test_makefile_assignment_is_not_a_target(tmp_path: Path) -> None:
    """
    @brief      A ``test := ...`` variable assignment is not mistaken for a
                ``test:`` target.
    @return     None
    @exception  AssertionError If a candidate is spuriously extracted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(tmp_path, "Makefile", "test := pytest\n")

    result = _analyze(tmp_path)

    assert not any(c.source_file == "Makefile" for c in result.gate_test_cmds)


# --- CI files -----------------------------------------------------------------


def test_github_workflow_run_line_extracted_with_provenance(tmp_path: Path) -> None:
    """
    @brief      A GitHub-workflow ``run: pytest -q`` line becomes a test
                candidate split to argv, tagged with the workflow file and
                line number.
    @return     None
    @exception  AssertionError If the candidate or provenance is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(
        tmp_path,
        ".github/workflows/ci.yml",
        "jobs:\n  test:\n    steps:\n      - run: pytest -q\n",
    )

    result = _analyze(tmp_path)

    candidate = next(c for c in result.gate_test_cmds if c.source_file == ".github/workflows/ci.yml")
    assert candidate.argv == ("pytest", "-q")
    assert candidate.needs_review is False
    assert candidate.source_detail.startswith("run: line")


def test_shell_syntax_ci_line_becomes_manual_review(tmp_path: Path) -> None:
    """
    @brief      A ``run:`` line with shell chaining that shlex cannot safely
                split becomes a manual-review candidate (argv=None), never a
                wrong argv.
    @return     None
    @exception  AssertionError If a wrong argv was produced.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(
        tmp_path,
        ".github/workflows/ci.yml",
        "jobs:\n  x:\n    steps:\n      - run: pytest -q && echo done\n",
    )

    result = _analyze(tmp_path)

    candidate = next(c for c in result.gate_test_cmds if c.source_file == ".github/workflows/ci.yml")
    assert candidate.argv is None
    assert candidate.needs_review is True
    assert "&&" in candidate.raw


def test_gitlab_script_list_items_extracted(tmp_path: Path) -> None:
    """
    @brief      GitLab ``script:`` list items are extracted with .gitlab-ci.yml
                provenance; a lint item classifies to the lint gate.
    @return     None
    @exception  AssertionError If either item is missing or misclassified.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(
        tmp_path,
        ".gitlab-ci.yml",
        "unit:\n  script:\n    - pytest -q\n    - ruff check .\n",
    )

    result = _analyze(tmp_path)

    test = next(c for c in result.gate_test_cmds if c.source_file == ".gitlab-ci.yml")
    lint = next(c for c in result.gate_lint_cmds if c.source_file == ".gitlab-ci.yml")
    assert test.argv == ("pytest", "-q")
    assert lint.argv == ("ruff", "check", ".")


def test_ci_install_line_is_dropped_not_classified(tmp_path: Path) -> None:
    """
    @brief      A CI ``run:`` line matching neither test nor lint keywords
                (an install step) is dropped, not surfaced as a candidate.
    @return     None
    @exception  AssertionError If the install line leaked into any gate.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(
        tmp_path,
        ".github/workflows/ci.yml",
        "jobs:\n  x:\n    steps:\n      - run: pip install -e .\n",
    )

    result = _analyze(tmp_path)

    assert not any(c.source_file == ".github/workflows/ci.yml" for c in result.gate_test_cmds)
    assert not any(c.source_file == ".github/workflows/ci.yml" for c in result.gate_lint_cmds)


def test_github_block_scalar_run_is_skipped(tmp_path: Path) -> None:
    """
    @brief      A block-scalar ``run: |`` header carries no inline command and
                is skipped (documented scope limit).
    @return     None
    @exception  AssertionError If a spurious candidate was extracted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(
        tmp_path,
        ".github/workflows/ci.yml",
        "jobs:\n  x:\n    steps:\n      - run: |\n          pytest -q\n",
    )

    result = _analyze(tmp_path)

    assert not any(c.source_file == ".github/workflows/ci.yml" for c in result.gate_test_cmds)


# --- package.json placeholder -------------------------------------------------


def test_npm_placeholder_test_script_is_skipped(tmp_path: Path) -> None:
    """
    @brief      npm's default "no test specified" placeholder script is not
                emitted as a gate candidate.
    @return     None
    @exception  AssertionError If the placeholder produced a candidate.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(
        tmp_path,
        "package.json",
        '{"scripts": {"test": "echo \\"Error: no test specified\\" && exit 1"}}',
    )

    result = _analyze(tmp_path)

    assert not any(c.source_file == "package.json" for c in result.gate_test_cmds)


def test_every_gate_candidate_names_its_source_file(tmp_path: Path) -> None:
    """
    @brief      Across mixed sources, every extracted candidate carries a
                non-empty source_file and source_detail (provenance guarantee).
    @return     None
    @exception  AssertionError If any candidate lacks provenance.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write(tmp_path, "package.json", '{"scripts": {"test": "jest", "lint": "eslint ."}}')
    _write(tmp_path, "pyproject.toml", "[tool.pytest.ini_options]\n[tool.ruff]\n")
    _write(tmp_path, "Makefile", "test:\n\tpytest\nlint:\n\truff check .\n")

    result = _analyze(tmp_path)

    candidates = result.gate_test_cmds + result.gate_lint_cmds
    assert candidates
    for candidate in candidates:
        assert candidate.source_file
        assert candidate.source_detail


# END OF FILE
