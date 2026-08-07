#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_execution_outcomes.py
@brief Public CLI contracts for explicit execution outcomes.
@details Covers WP4's distinct nothing-ran result without relabeling disabled
         policy, audit, bypass, pass, or failure states.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import subprocess

import pytest

import aegis.check_execution as check_execution_module
import aegis.gates as gates_module
import aegis.store as store_module
from aegis.cli import main
from aegis.config import load_config
from aegis.gates import run_gates_with_outcome
from aegis.models import Check, StageRecord
from aegis.store import init_graph, journal_path, load_graph, save_graph
from aegis.verification import run_verification

# TESTS


def test_verify_gates_with_only_disabled_groups_reports_nothing_ran(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Enforce WP4's explicit-gate nothing-ran outcome.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "fix", "--json"])
    run_id = json.loads(capsys.readouterr().out)["run_id"]

    with pytest.raises(SystemExit) as raised:
        main(["verify", "gates", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert raised.value.code != 0
    assert payload["execution_status"] == "nothing-ran"
    assert payload["executed_count"] == 0
    assert "disabled" in payload["reason"]
    assert load_graph(tmp_path, run_id).evidence == []
    event = json.loads(
        journal_path(tmp_path, run_id).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert event["event"] == "gate.execution.nothing-ran"
    assert event["data"]["executed_count"] == 0


def test_verify_gates_selected_disabled_group_reports_plain_nothing_ran(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Enforce WP4 for an explicit disabled single-gate selection.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "fix", "--json"])
    capsys.readouterr()

    with pytest.raises(SystemExit) as raised:
        main(["verify", "gates", "test"])
    plain = capsys.readouterr().out

    assert raised.value.code == 1
    assert "NOTHING RAN:" in plain
    assert "selected gate is disabled" in plain
    assert "execution_status: nothing-ran" in plain
    assert "executed_count: 0" in plain


@pytest.mark.parametrize(
    ("returncode", "execution_status", "exit_code"),
    [(0, "pass", 0), (7, "fail", 7)],
)
def test_verify_gates_reports_executed_pass_or_fail(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    returncode: int,
    execution_status: str,
    exit_code: int,
) -> None:
    """
    @brief Keep a launched passing or failing gate distinct from nothing-ran.
    @param[in] tmp_path Configured temporary repository.
    @param[in] replace_workflow_toml Shared workflow editor.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @param[in] returncode Scripted command result.
    @param[in] execution_status Expected explicit execution state.
    @param[in] exit_code Expected CLI exit code.
    @return None.
    """
    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\nmode = "enforce"\ncommands = ["test-command"]',
    )
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "fix", "--json"])
    capsys.readouterr()
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda _root, command, _timeout: subprocess.CompletedProcess(
            command, returncode, "output", ""
        ),
    )

    if exit_code:
        with pytest.raises(SystemExit) as raised:
            main(["verify", "gates", "test", "--json"])
        assert raised.value.code == exit_code
    else:
        main(["verify", "gates", "test", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["execution_status"] == execution_status
    assert payload["executed_count"] == 1
    assert "reason" not in payload


def test_verify_run_keeps_disabled_gates_not_enforced_not_nothing_ran(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Preserve ordinary verification's disabled-policy audit semantics.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "fix", "--json"])
    run_id = json.loads(capsys.readouterr().out)["run_id"]

    with pytest.raises(SystemExit):
        main(["verify", "run", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert "execution_status" not in payload
    assert {
        item["status"]
        for item in payload["verification"]["gates"].values()
    } == {"not-enforced"}
    events = [
        json.loads(line)["event"]
        for line in journal_path(tmp_path, run_id).read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert "gate.execution.nothing-ran" not in events


def test_run_verification_does_not_journal_an_explicit_gate_outcome(
    tmp_path: Path,
) -> None:
    """
    @brief Preserve aggregate gate journal semantics through the public API.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    graph = init_graph(tmp_path, "fix", "Aggregate verification outcome")

    summary, _exit_code = run_verification(tmp_path, graph, load_config(tmp_path))

    assert {
        item["status"] for item in summary["gates"].values()
    } == {"not-enforced"}
    events = [
        json.loads(line)["event"]
        for line in journal_path(tmp_path, graph.run_id).read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert "gate.execution.nothing-ran" not in events


def test_managed_check_run_with_empty_set_reports_nothing_ran(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Enforce WP4 when a managed check execution resolves no commands.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    graph = init_graph(tmp_path, "fix", "Empty managed execution")
    graph.stage = "implementation"
    graph.stage_records["implementation"] = StageRecord(
        stage="implementation",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="managed",
    )
    save_graph(tmp_path, graph)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as raised:
        main(["check", "run", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert raised.value.code == 1
    assert payload["execution_status"] == "nothing-ran"
    assert payload["executed_count"] == 0
    assert payload["evidence"] == []
    persisted = load_graph(tmp_path, graph.run_id)
    assert persisted.evidence == []
    event = json.loads(
        journal_path(tmp_path, graph.run_id).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert event["event"] == "check.execution.nothing-ran"


def test_managed_check_run_reports_pass_or_fail_not_nothing_ran(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Keep executed managed observations distinct from an empty request.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    graph = init_graph(tmp_path, "fix", "Managed execution outcomes")
    graph.stage = "implementation"
    graph.checks = [
        Check(
            id="CHK-001",
            level="unit",
            cites_spec=[],
            command="check-command",
            path="tests/test_example.py",
        )
    ]
    graph.stage_records["implementation"] = StageRecord(
        stage="implementation",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="managed",
    )
    save_graph(tmp_path, graph)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        check_execution_module,
        "_run_command",
        lambda _root, command, _timeout: subprocess.CompletedProcess(
            command, 1, "", "failure"
        ),
    )

    main(["check", "run", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["execution_status"] == "fail"
    assert payload["executed_count"] == 1
    assert payload["evidence"][0]["result"] == "fail"


def test_nothing_ran_journal_failure_preserves_graph_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Preserve no-pass-evidence behavior when outcome journaling fails.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    """
    graph = init_graph(tmp_path, "fix", "Outcome publication failure")
    graph_before = (tmp_path / ".agentic" / "runs" / graph.run_id / "graph.json").read_bytes()
    original_write = store_module.atomic_write_bytes
    target_journal = journal_path(tmp_path, graph.run_id)
    journal_before = target_journal.read_bytes()

    def fail_only_outcome_journal(target: Path, content: bytes) -> None:
        """@brief Fail the outcome journal replacement after graph save."""
        if target == target_journal:
            raise OSError("journal failure")
        original_write(target, content)

    monkeypatch.setattr(store_module, "atomic_write_bytes", fail_only_outcome_journal)

    with pytest.raises(OSError, match="journal failure"):
        run_gates_with_outcome(tmp_path, graph.run_id, load_config(tmp_path))

    assert (tmp_path / ".agentic" / "runs" / graph.run_id / "graph.json").read_bytes() == graph_before
    assert target_journal.read_bytes() == journal_before


# END OF FILE
