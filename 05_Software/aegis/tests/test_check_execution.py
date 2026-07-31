#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_check_execution.py
@brief Behavioral tests for external deterministic check evidence.
@details Covers canonical field storage, complete-document validation,
         preparation preconditions, mutation isolation, form retention, and
         managed-execution stale-state rejection.
@author Eng. Dan Dumitru Pasare
@date 2026-07-30
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

import aegis.check_execution as check_execution_module
from aegis.check_execution import (
    prepare_check_evidence,
    record_check_evidence,
    run_checks,
)
from aegis.models import Check, Evidence, Graph, StageRecord
from aegis.stage_forms import StageOperationError
from aegis.store import (
    GraphConflictError,
    graph_path,
    init_graph,
    journal_path,
    load_graph,
    save_graph,
)

# TESTS


@pytest.mark.parametrize(
    ("stage", "raw_result", "exit_status", "expected_state"),
    [
        ("implementation", " pass ", 0, "green"),
        ("check", " fail ", 1, "red"),
    ],
)
def test_external_result_fields_are_stored_canonically(
    tmp_path: Path,
    stage: str,
    raw_result: str,
    exit_status: int,
    expected_state: str,
) -> None:
    """
    @brief Store the same normalized result, summary, and output path validated.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(tmp_path, stage=stage, check_count=1)
    form = prepare_check_evidence(tmp_path, graph)
    _replace_once(form, 'result = ""', f'result = "{raw_result}"')
    _replace_once(form, "exit_status = 0", f"exit_status = {exit_status}")
    _replace_once(form, 'summary = ""', 'summary = "  observed outcome  "')
    _replace_once(form, 'output_log = ""', 'output_log = "  logs/check.log  "')

    imported = record_check_evidence(tmp_path, graph)

    assert [item.id for item in imported] == ["E-0001"]
    assert imported[0].result == raw_result.strip()
    assert imported[0].summary == "observed outcome"
    assert imported[0].output_log == "logs/check.log"
    assert graph.checks[0].state == expected_state
    persisted = load_graph(tmp_path, graph.run_id)
    assert persisted.evidence[0].result == raw_result.strip()
    assert persisted.checks[0].state == expected_state
    assert not form.exists()


def test_record_rejects_graph_without_imported_checks(tmp_path: Path) -> None:
    """
    @brief Reject an empty imported-check set as a typed stage failure.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(tmp_path, check_count=0)

    with pytest.raises(
        StageOperationError,
        match="no imported checks are available",
    ):
        record_check_evidence(tmp_path, graph)

    assert graph.evidence == []


def test_external_evidence_rejects_unsupported_stage(tmp_path: Path) -> None:
    """
    @brief Apply the same supported-stage constraint to prepare and record.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(tmp_path, stage="validation", check_count=1)

    for operation in (prepare_check_evidence, record_check_evidence):
        with pytest.raises(
            StageOperationError,
            match="valid only during check or implementation",
        ):
            operation(tmp_path, graph)


def test_external_evidence_rejects_wrong_captured_mode(tmp_path: Path) -> None:
    """
    @brief Require the active prepared stage to capture external execution.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(
        tmp_path,
        mode="managed",
        check_count=1,
    )

    for operation in (prepare_check_evidence, record_check_evidence):
        with pytest.raises(StageOperationError, match="mode is managed"):
            operation(tmp_path, graph)


@pytest.mark.parametrize(
    "invalid_case",
    [
        "empty-results",
        "duplicate-check",
        "missing-check",
        "unknown-check",
        "command-mismatch",
        "inconsistent-exit-status",
        "malformed-row",
        "missing-top-level-key",
        "unknown-top-level-key",
        "missing-row-key",
        "unknown-row-key",
    ],
)
def test_invalid_external_document_does_not_mutate_state(
    tmp_path: Path,
    invalid_case: str,
) -> None:
    """
    @brief Validate the complete form before any graph, journal, or form change.
    @param[in] tmp_path Temporary repository root.
    @param[in] invalid_case Invalid evidence-document transformation.
    @return None.
    """
    graph = _external_graph(tmp_path, check_count=2)
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result="pass", exit_status=0)
    _make_invalid(form, graph, invalid_case)
    graph_before = graph.to_dict()
    graph_bytes = graph_path(tmp_path, graph.run_id).read_bytes()
    journal_bytes = journal_path(tmp_path, graph.run_id).read_bytes()
    form_bytes = form.read_bytes()

    with pytest.raises(StageOperationError):
        record_check_evidence(tmp_path, graph)

    assert graph.to_dict() == graph_before
    assert graph_path(tmp_path, graph.run_id).read_bytes() == graph_bytes
    assert journal_path(tmp_path, graph.run_id).read_bytes() == journal_bytes
    assert form.read_bytes() == form_bytes


def test_success_uses_monotonic_id_and_versioned_form_retention(
    tmp_path: Path,
) -> None:
    """
    @brief Preserve evidence-ID allocation and captured versioned retention.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(
        tmp_path,
        check_count=1,
        retention="versioned",
    )
    graph.evidence.append(
        Evidence(
            id="E-0007",
            kind="note",
            result="info",
            summary="Prior evidence",
            stage="design",
        )
    )
    save_graph(tmp_path, graph)
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result="pass", exit_status=0)

    imported = record_check_evidence(tmp_path, graph)

    assert [item.id for item in imported] == ["E-0008"]
    assert form.is_file()
    revision = form.parent / "revisions" / "check-evidence-E-0008"
    assert (revision / "evidence.toml").read_bytes() == form.read_bytes()
    assert (revision / "digest.json").is_file()


def test_form_is_not_retired_when_journal_persistence_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Retire a validated form only after graph and journal persistence.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(tmp_path, check_count=1)
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result="pass", exit_status=0)

    def fail_journal(*args: object, **kwargs: object) -> None:
        """@brief Inject a durable-journal publication failure."""
        raise OSError("journal unavailable")

    monkeypatch.setattr(
        check_execution_module,
        "append_journal",
        fail_journal,
    )

    with pytest.raises(OSError, match="journal unavailable"):
        record_check_evidence(tmp_path, graph)

    assert form.is_file()


def test_managed_results_reject_changed_checks_before_recording(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Reject Phase C when check definitions change during execution.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @version 0.1.0
    """
    graph = _external_graph(
        tmp_path,
        stage="implementation",
        mode="managed",
        check_count=1,
    )

    def change_check_while_running(
        _repo_root: Path,
        command: str,
        _timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        """
        @brief Simulate a concurrent check-definition mutation in Phase B.
        @version 0.1.0
        """
        current = load_graph(tmp_path, graph.run_id)
        current.checks[0].command = "python -m pytest tests/replacement.py"
        save_graph(tmp_path, current)
        return subprocess.CompletedProcess(command, 0, "passed", "")

    monkeypatch.setattr(
        check_execution_module,
        "_run_command",
        change_check_while_running,
    )

    with pytest.raises(GraphConflictError) as raised:
        run_checks(tmp_path, graph)

    assert raised.value.code == "GRAPH-STALE-UPDATE"
    persisted = load_graph(tmp_path, graph.run_id)
    assert persisted.evidence == []
    assert persisted.checks[0].state == "unknown"
    assert not (
        tmp_path
        / ".agentic"
        / "runs"
        / graph.run_id
        / "evidence"
        / "logs"
    ).exists()
    assert '"event": "check.output"' not in journal_path(
        tmp_path,
        graph.run_id,
    ).read_text(encoding="utf-8")


# LOCAL HELPERS


def _external_graph(
    repo_root: Path,
    *,
    stage: str = "implementation",
    mode: str = "external",
    check_count: int,
    retention: str = "discard",
) -> Graph:
    """
    @brief Create and persist one active graph configured for evidence tests.
    @param[in] repo_root Temporary repository root.
    @param[in] stage Active stage.
    @param[in] mode Captured execution mode.
    @param[in] check_count Number of imported checks.
    @param[in] retention Captured evidence-form retention.
    @return Persisted graph.
    @version 0.1.0
    """
    graph = init_graph(repo_root, "fix", "Exercise external evidence")
    graph.stage = stage  # type: ignore[assignment]
    graph.checks = [
        Check(
            id=f"CHK-{index:03d}",
            level="unit",
            cites_spec=[],
            command=f"python -m pytest tests/test_{index}.py",
            path=f"tests/test_{index}.py",
        )
        for index in range(1, check_count + 1)
    ]
    graph.stage_records[stage] = StageRecord(
        stage=stage,  # type: ignore[arg-type]
        revision=1,
        status="applied",
        retention=retention,  # type: ignore[arg-type]
        check_execution=mode,  # type: ignore[arg-type]
        artifact=f".agentic/runs/{graph.run_id}/stages/{stage}/stage.toml",
    )
    save_graph(repo_root, graph)
    return graph


def _replace_once(path: Path, old: str, new: str) -> None:
    """
    @brief Replace one required unique form fragment.
    @param[in] path Form path.
    @param[in] old Expected fragment.
    @param[in] new Replacement fragment.
    @return None.
    @version 0.1.0
    """
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(f"expected one occurrence of {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def _complete_results(path: Path, *, result: str, exit_status: int) -> None:
    """
    @brief Complete every generated result row with valid evidence.
    @param[in] path Evidence form path.
    @param[in] result Expected result.
    @param[in] exit_status Matching process status.
    @return None.
    @version 0.1.0
    """
    text = path.read_text(encoding="utf-8")
    text = text.replace('result = ""', f'result = "{result}"')
    text = text.replace("exit_status = 0", f"exit_status = {exit_status}")
    text = text.replace('summary = ""', 'summary = "Observed expected outcome"')
    path.write_text(text, encoding="utf-8", newline="\n")


def _make_invalid(path: Path, graph: Graph, invalid_case: str) -> None:
    """
    @brief Apply one malformed-document transformation.
    @param[in] path Evidence form path.
    @param[in] graph Active graph supplying immutable identities.
    @param[in] invalid_case Transformation name.
    @return None.
    @version 0.1.0
    """
    text = path.read_text(encoding="utf-8")
    header, *rows = text.split("\n[[result]]")
    if invalid_case == "empty-results":
        text = header + "\nresult = []\n"
    elif invalid_case == "duplicate-check":
        rows[1] = rows[1].replace(graph.checks[1].id, graph.checks[0].id)
        text = header + "\n[[result]]".join(["", *rows])
    elif invalid_case == "missing-check":
        text = header + "\n[[result]]" + rows[0]
    elif invalid_case == "unknown-check":
        rows[1] = rows[1].replace(graph.checks[1].id, "CHK-UNKNOWN")
        text = header + "\n[[result]]".join(["", *rows])
    elif invalid_case == "command-mismatch":
        rows[0] = rows[0].replace(graph.checks[0].command or "", "other command")
        text = header + "\n[[result]]".join(["", *rows])
    elif invalid_case == "inconsistent-exit-status":
        rows[0] = rows[0].replace("exit_status = 0", "exit_status = 1")
        text = header + "\n[[result]]".join(["", *rows])
    elif invalid_case == "malformed-row":
        text = header + '\nresult = ["not-a-table"]\n'
    elif invalid_case == "missing-top-level-key":
        header = header.replace('expected_result = "pass"\n', "")
        text = header + "\n[[result]]".join(["", *rows])
    elif invalid_case == "unknown-top-level-key":
        header += '\nunknown = "value"'
        text = header + "\n[[result]]".join(["", *rows])
    elif invalid_case == "missing-row-key":
        rows[0] = rows[0].replace('output_log = ""\n', "")
        text = header + "\n[[result]]".join(["", *rows])
    elif invalid_case == "unknown-row-key":
        rows[0] = rows[0].replace(
            'output_log = ""',
            'output_log = ""\nunknown = "value"',
        )
        text = header + "\n[[result]]".join(["", *rows])
    else:  # pragma: no cover - protects the parameter table itself
        raise AssertionError(f"unknown invalid case: {invalid_case}")
    path.write_text(text, encoding="utf-8", newline="\n")


# END OF FILE
