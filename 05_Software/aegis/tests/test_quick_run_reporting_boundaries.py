#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_quick_run_reporting_boundaries.py
@brief Regression tests for honest quick-run reporting boundaries.
@details Proves absent requirement-stage storage is not loaded and that a
         bypass is reported only after human intake closure commits the route.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from aegis.cli import main
from aegis.config import WorkflowConfig, load_config
from aegis.report import render_report
from aegis.store import load_graph
from aegis.verification import run_verification

# CONSTANTS

QUICK_BYPASSED_STAGES = ["alignment", "requirement", "design", "check"]
NOT_APPLICABLE_INVARIANTS = ("INV-1", "INV-2", "INV-3", "INV-8", "INV-10")

# LOCAL HELPERS


def _invoke_json(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> dict[str, object]:
    """
    @brief Invoke one successful CLI command and parse its JSON response.
    @param[in] capsys Pytest capture fixture.
    @param[in] arguments Command arguments without the global JSON flag.
    @return Parsed stable response envelope.
    """
    main([*arguments, "--json"])
    return json.loads(capsys.readouterr().out)


def _replace(path: Path, replacements: dict[str, str]) -> None:
    """
    @brief Apply exact substitutions to one generated workflow form.
    @param[in] path Generated form path.
    @param[in] replacements Expected old fragments and replacements.
    @return None.
    """
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert text.count(old) == 1, (path, old)
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")


def _journal(repo_root: Path, run_id: str) -> list[dict[str, object]]:
    """
    @brief Read one run journal as parsed JSON Lines.
    @param[in] repo_root Temporary repository root.
    @param[in] run_id Run whose journal is inspected.
    @return Parsed journal entries in append order.
    """
    path = repo_root / ".agentic" / "runs" / run_id / "journal.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _initialize_git_repository(repo_root: Path) -> None:
    """
    @brief Create a committed baseline for real working-tree verification.
    @param[in] repo_root Temporary repository root.
    @return None.
    """
    source = repo_root / "src" / "state.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("STATE = 'baseline'\n", encoding="utf-8", newline="\n")
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=AEGIS Tests",
            "-c",
            "user.email=aegis-tests@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "baseline",
        ],
        cwd=repo_root,
        check=True,
    )


def _configure_failing_test_gate(repo_root: Path) -> WorkflowConfig:
    """
    @brief Enable one deterministic enforced gate that exits with status seven.
    @param[in] repo_root Temporary repository root.
    @return Reloaded workflow configuration.
    """
    path = repo_root / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    executable = Path(sys.executable).as_posix()
    command = f'"{executable}" -c "import sys; sys.exit(7)"'
    old = '[gates.test]\nmode = "disabled"\ncommands = []'
    new = f'[gates.test]\nmode = "enforce"\ncommands = [{command!r}]'
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return load_config(repo_root)


def _close_quick_intake(
    repo_root: Path,
    capsys: pytest.CaptureFixture[str],
    artifact: str,
) -> dict[str, object]:
    """
    @brief Human-close the prepared intake form for one selected quick run.
    @param[in] repo_root Temporary repository root.
    @param[in] capsys Pytest capture fixture.
    @param[in] artifact Repository-relative intake form path.
    @return Stage-close response positioned at implementation.
    """
    _replace(
        repo_root / artifact,
        {
            'statement = ""': 'statement = "Repair a bounded defect"',
            'summary = ""': 'summary = "Quick intake approved"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    closed = _invoke_json(capsys, ["stage", "close"])
    assert closed["stage"] == "implementation"
    return closed


def _invariant_map(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    """
    @brief Index serialized verification invariants by stable identifier.
    @param[in] summary Validation summary returned by verification.
    @return Mapping from invariant ID to its serialized result.
    """
    invariants = summary["invariants"]
    assert isinstance(invariants, list)
    return {
        str(item["id"]): item
        for item in invariants
        if isinstance(item, dict)
    }


# TESTS


def test_quick_verification_skips_malformed_requirement_storage_but_runs_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Keep absent-stage state N/A while gates and reporting remain real.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    _initialize_git_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    started = _invoke_json(capsys, ["run", "start", "fix", "--quick"])
    run_id = str(started["run_id"])
    _close_quick_intake(tmp_path, capsys, str(started["artifact"]))

    malformed = (
        tmp_path
        / ".agentic"
        / "requirements"
        / "functional"
        / "malformed.toml"
    )
    malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_text("not = [valid\n", encoding="utf-8", newline="\n")
    config = _configure_failing_test_gate(tmp_path)

    summary, code = run_verification(
        tmp_path,
        load_graph(tmp_path, run_id),
        config,
    )

    assert code == 1
    gates = summary["gates"]
    assert isinstance(gates, dict)
    assert gates["test"]["status"] == "failed"
    invariants = _invariant_map(summary)
    for invariant_id in NOT_APPLICABLE_INVARIANTS:
        assert invariants[invariant_id]["status"] == "not-applicable"
        assert invariants[invariant_id]["holds"] is None
    assert invariants["INV-4"]["holds"] is False
    assert summary["traceability"] == [
        {
            "status": "not-applicable",
            "message": "Not applicable - quick run.",
        }
    ]
    assert summary["coverage"] == summary["traceability"]
    impact_rows = summary["impact"]
    assert isinstance(impact_rows, list)
    assert all(
        row["uncovered"] is None
        and row["coverage_status"] == "not-applicable"
        for row in impact_rows
    )
    assert isinstance(summary["working_tree"], dict)

    report = render_report(
        tmp_path,
        load_graph(tmp_path, run_id),
        config,
    )
    assert "- Quick run - stages bypassed: " in report
    requirements_section = report.split("## Requirements", maxsplit=1)[1]
    requirements_section = requirements_section.split(
        "## Solution Design", maxsplit=1
    )[0]
    assert "NOT APPLICABLE: Not applicable - quick run." in requirements_section
    assert "- `INV-4` FAIL" in report


def test_bypass_reporting_begins_only_after_human_intake_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Align status, summary, report, and journal bypass timing.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    _initialize_git_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    started = _invoke_json(capsys, ["run", "start", "fix", "--quick"])
    run_id = str(started["run_id"])
    config = load_config(tmp_path)

    status_before = _invoke_json(capsys, ["run", "status"])
    assert status_before["run_profile"] == "quick"
    assert "bypass_status" not in status_before
    assert "bypassed_stages" not in status_before
    assert not any(
        item["event"] == "run.stages_bypassed"
        for item in _journal(tmp_path, run_id)
    )

    summary_before, _code_before = run_verification(
        tmp_path,
        load_graph(tmp_path, run_id),
        config,
    )
    assert summary_before["run_profile"] == "quick"
    assert "bypass_status" not in summary_before
    assert "bypassed_stages" not in summary_before
    report_before = render_report(
        tmp_path,
        load_graph(tmp_path, run_id),
        config,
    )
    assert "Quick run - stages bypassed" not in report_before

    closed = _close_quick_intake(
        tmp_path,
        capsys,
        str(started["artifact"]),
    )
    assert closed["bypass_status"] == "bypassed"
    assert closed["bypassed_stages"] == QUICK_BYPASSED_STAGES
    status_after = _invoke_json(capsys, ["run", "status"])
    assert status_after["bypass_status"] == "bypassed"
    assert status_after["bypassed_stages"] == QUICK_BYPASSED_STAGES
    bypass_events = [
        item
        for item in _journal(tmp_path, run_id)
        if item["event"] == "run.stages_bypassed"
    ]
    assert len(bypass_events) == 1

    summary_after, _code_after = run_verification(
        tmp_path,
        load_graph(tmp_path, run_id),
        config,
    )
    assert summary_after["bypass_status"] == "bypassed"
    assert summary_after["bypassed_stages"] == QUICK_BYPASSED_STAGES
    report_after = render_report(
        tmp_path,
        load_graph(tmp_path, run_id),
        config,
    )
    assert (
        "Quick run - stages bypassed: alignment, requirement, design, check"
        in report_after
    )


# END OF FILE
