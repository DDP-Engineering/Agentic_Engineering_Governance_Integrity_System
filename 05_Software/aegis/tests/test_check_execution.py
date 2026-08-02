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
         preparation preconditions, mutation isolation, form retention,
         waiver-excused partial submissions, and managed-execution stale-state
         rejection.
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

import aegis.check_execution as check_execution_module
import aegis.stage_forms as stage_forms_module
from aegis.check_execution import (
    prepare_check_evidence,
    record_check_evidence,
    run_checks,
)
from aegis.models import Check, Evidence, Graph, StageRecord
from aegis.stage_forms import StageOperationError, stage_blocker_details
from aegis.store import (
    GraphConflictError,
    add_waiver,
    graph_path,
    init_graph,
    journal_path,
    load_graph,
    relink_check_evidence,
    save_graph,
)
from aegis.waivers import Blocker

# CONSTANTS

COMPLETENESS_ERROR = (
    "result collection must contain every imported check exactly once"
)
STAGE_EXPECTATIONS = (("check", "fail", 1), ("implementation", "pass", 0))

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


@pytest.mark.parametrize(
    ("stage", "expected", "exit_status"),
    STAGE_EXPECTATIONS,
)
def test_waived_check_is_excused_from_the_evidence_document(
    tmp_path: Path,
    stage: str,
    expected: str,
    exit_status: int,
) -> None:
    """
    @brief Record real evidence for the checks that have it while one is waived.
    @param[in] tmp_path Temporary repository root.
    @param[in] stage Active stage under test.
    @param[in] expected Uniform result required of every present row.
    @param[in] exit_status Process status consistent with that result.
    @return None.
    """
    graph = _external_graph(tmp_path, stage=stage, check_count=2)
    _waive(tmp_path, graph, "CHK-001")

    form = prepare_check_evidence(tmp_path, graph)
    assert _row_check_ids(form) == ["CHK-002"]
    _complete_results(form, result=expected, exit_status=exit_status)
    imported = record_check_evidence(tmp_path, graph)

    assert [item.check_id for item in imported] == ["CHK-002"]
    persisted = load_graph(tmp_path, graph.run_id)
    assert [item.check_id for item in persisted.evidence] == ["CHK-002"]
    assert persisted.checks[0].state == "unknown"
    assert persisted.checks[1].state == ("red" if expected == "fail" else "green")


@pytest.mark.parametrize(
    ("stage", "expected", "exit_status"),
    STAGE_EXPECTATIONS,
)
def test_unwaived_check_still_cannot_be_omitted(
    tmp_path: Path,
    stage: str,
    expected: str,
    exit_status: int,
) -> None:
    """
    @brief Keep every check without an active waiver mandatory in the document.
    @param[in] tmp_path Temporary repository root.
    @param[in] stage Active stage under test.
    @param[in] expected Uniform result required of every present row.
    @param[in] exit_status Process status consistent with that result.
    @return None.
    """
    graph = _external_graph(tmp_path, stage=stage, check_count=3)
    _waive(tmp_path, graph, "CHK-001")
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result=expected, exit_status=exit_status)
    _drop_row(form, "CHK-002")

    with pytest.raises(StageOperationError, match=COMPLETENESS_ERROR):
        record_check_evidence(tmp_path, graph)

    assert load_graph(tmp_path, graph.run_id).evidence == []


@pytest.mark.parametrize(
    ("stage", "expected", "exit_status"),
    STAGE_EXPECTATIONS,
)
def test_stale_waiver_does_not_excuse_its_check(
    tmp_path: Path,
    stage: str,
    expected: str,
    exit_status: int,
) -> None:
    """
    @brief Restore the mandatory row once approved state no longer matches.
    @param[in] tmp_path Temporary repository root.
    @param[in] stage Active stage under test.
    @param[in] expected Uniform result required of every present row.
    @param[in] exit_status Process status consistent with that result.
    @return None.
    """
    graph = _external_graph(tmp_path, stage=stage, check_count=2)
    _waive(tmp_path, graph, "CHK-001")
    if stage == "check":
        graph.checks[0].concerns = ["state advanced after approval"]
    else:
        graph.stage_records[stage].revision += 1
    save_graph(tmp_path, graph)

    form = prepare_check_evidence(tmp_path, graph)

    assert _row_check_ids(form) == ["CHK-001", "CHK-002"]
    assert len(load_graph(tmp_path, graph.run_id).waivers) == 1
    _complete_results(form, result=expected, exit_status=exit_status)
    _drop_row(form, "CHK-001")
    with pytest.raises(StageOperationError, match=COMPLETENESS_ERROR):
        record_check_evidence(tmp_path, graph)


@pytest.mark.parametrize(
    ("stage", "expected", "exit_status"),
    STAGE_EXPECTATIONS,
)
def test_every_check_is_required_without_any_waiver(
    tmp_path: Path,
    stage: str,
    expected: str,
    exit_status: int,
) -> None:
    """
    @brief Preserve complete-document behavior for runs that hold no waivers.
    @param[in] tmp_path Temporary repository root.
    @param[in] stage Active stage under test.
    @param[in] expected Uniform result required of every present row.
    @param[in] exit_status Process status consistent with that result.
    @return None.
    """
    graph = _external_graph(tmp_path, stage=stage, check_count=2)

    form = prepare_check_evidence(tmp_path, graph)
    assert _row_check_ids(form) == ["CHK-001", "CHK-002"]
    _complete_results(form, result=expected, exit_status=exit_status)
    imported = record_check_evidence(tmp_path, graph)

    assert [item.check_id for item in imported] == ["CHK-001", "CHK-002"]


@pytest.mark.parametrize(
    ("stage", "expected", "exit_status"),
    STAGE_EXPECTATIONS,
)
def test_excused_check_may_not_carry_a_recorded_result(
    tmp_path: Path,
    stage: str,
    expected: str,
    exit_status: int,
) -> None:
    """
    @brief Refuse an observation submitted under an active approval instead.
    @param[in] tmp_path Temporary repository root.
    @param[in] stage Active stage under test.
    @param[in] expected Uniform result required of every present row.
    @param[in] exit_status Process status consistent with that result.
    @return None.
    """
    graph = _external_graph(tmp_path, stage=stage, check_count=2)
    _waive(tmp_path, graph, "CHK-001")
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result=expected, exit_status=exit_status)
    _replace_once(form, 'check_id = "CHK-002"', 'check_id = "CHK-001"')
    _replace_once(form, "tests/test_2.py", "tests/test_1.py")

    with pytest.raises(
        StageOperationError,
        match="CHK-001 is covered by an active waiver",
    ):
        record_check_evidence(tmp_path, graph)

    assert load_graph(tmp_path, graph.run_id).evidence == []


@pytest.mark.parametrize(("stage", "expected", "exit_status"), STAGE_EXPECTATIONS)
def test_fully_waived_check_set_requires_no_external_document(
    tmp_path: Path,
    stage: str,
    expected: str,
    exit_status: int,
) -> None:
    """
    @brief Report an honest precondition instead of an empty evidence document.
    @param[in] tmp_path Temporary repository root.
    @param[in] stage Active stage under test.
    @param[in] expected Unused uniform result for the shared stage table.
    @param[in] exit_status Unused process status for the shared stage table.
    @return None.
    """
    graph = _external_graph(tmp_path, stage=stage, check_count=1)
    _waive(tmp_path, graph, "CHK-001")

    for operation in (prepare_check_evidence, record_check_evidence):
        with pytest.raises(
            StageOperationError,
            match="every imported check is covered by an active waiver",
        ):
            operation(tmp_path, graph)


def test_reapplying_unchanged_checks_preserves_evidence_links(
    tmp_path: Path,
) -> None:
    """
    @brief Keep red/green links and state through a same-definition reapply.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(tmp_path, stage="check", check_count=2)
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result="fail", exit_status=1)
    record_check_evidence(tmp_path, graph)
    linked = [(check.state, check.red_evidence) for check in graph.checks]
    assert linked == [("red", "E-0001"), ("red", "E-0002")]

    directory = _write_check_forms(tmp_path, graph)
    stage_forms_module._apply_checks(
        graph, directory, graph.stage_records["check"]
    )

    assert [
        (check.state, check.red_evidence) for check in graph.checks
    ] == linked


def test_reapplying_a_changed_command_resets_only_that_check(
    tmp_path: Path,
) -> None:
    """
    @brief Reset evidence links only for a check whose command changed.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(tmp_path, stage="check", check_count=2)
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result="fail", exit_status=1)
    record_check_evidence(tmp_path, graph)

    directory = _write_check_forms(
        tmp_path,
        graph,
        commands={"CHK-001": "python -m pytest tests/test_other.py"},
    )
    stage_forms_module._apply_checks(
        graph, directory, graph.stage_records["check"]
    )

    changed, kept = graph.checks
    assert (changed.state, changed.red_evidence) == ("unknown", None)
    assert (kept.state, kept.red_evidence) == ("red", "E-0002")


def test_managed_green_rerun_supersedes_prior_failed_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Retire an implementation-stage failed attempt on a genuine rerun pass.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    """
    graph = _external_graph(
        tmp_path, stage="implementation", mode="managed", check_count=1
    )
    _seed_evidence(
        graph,
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
    )
    save_graph(tmp_path, graph)
    monkeypatch.setattr(
        check_execution_module,
        "_run_command",
        lambda _root, command, _timeout: subprocess.CompletedProcess(
            command, 0, "ok", ""
        ),
    )

    imported = run_checks(tmp_path, graph)

    assert [item.result for item in imported] == ["pass"]
    persisted = load_graph(tmp_path, graph.run_id)
    by_id = {item.id: item for item in persisted.evidence}
    assert by_id["E-0002"].status == "superseded"
    assert by_id["E-0002"].superseded_by == imported[0].id
    assert by_id["E-0001"].status == "active"
    check = persisted.checks[0]
    assert check.state == "green"
    assert check.green_evidence == imported[0].id
    assert check.red_evidence == "E-0001"


def test_external_green_rerun_supersedes_prior_failed_attempt(
    tmp_path: Path,
) -> None:
    """
    @brief Apply the same supersede rule through the external record path.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    graph = _external_graph(tmp_path, stage="implementation", check_count=1)
    _seed_evidence(
        graph,
        Evidence(
            id="E-0001",
            kind="test-run",
            result="fail",
            summary="launcher denied",
            stage="implementation",
            check_id="CHK-001",
            exit_status=127,
        ),
    )
    save_graph(tmp_path, graph)
    form = prepare_check_evidence(tmp_path, graph)
    _complete_results(form, result="pass", exit_status=0)

    imported = record_check_evidence(tmp_path, graph)

    persisted = load_graph(tmp_path, graph.run_id)
    by_id = {item.id: item for item in persisted.evidence}
    assert by_id["E-0001"].status == "superseded"
    assert by_id["E-0001"].superseded_by == imported[0].id
    check = persisted.checks[0]
    assert check.state == "green"
    assert check.red_evidence is None


def test_regressed_check_keeps_its_prior_pass_visible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Keep an older pass active when a rerun fails, exposing the regression.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    """
    graph = _external_graph(
        tmp_path, stage="implementation", mode="managed", check_count=1
    )
    _seed_evidence(
        graph,
        Evidence(
            id="E-0001",
            kind="test-run",
            result="pass",
            summary="previously green",
            stage="implementation",
            check_id="CHK-001",
            exit_status=0,
        ),
    )
    save_graph(tmp_path, graph)
    monkeypatch.setattr(
        check_execution_module,
        "_run_command",
        lambda _root, command, _timeout: subprocess.CompletedProcess(
            command, 1, "", "assertion failed"
        ),
    )

    imported = run_checks(tmp_path, graph)

    persisted = load_graph(tmp_path, graph.run_id)
    by_id = {item.id: item for item in persisted.evidence}
    assert by_id["E-0001"].status == "active"
    check = persisted.checks[0]
    assert check.state == "red"
    assert check.red_evidence == imported[0].id
    assert check.green_evidence == "E-0001"


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


def _seed_evidence(graph: Graph, *records: Evidence) -> None:
    """
    @brief Append pre-existing evidence and relink check state from it.
    @param[in,out] graph Active graph receiving the seeded records.
    @param[in] records Evidence records considered already recorded.
    @return None.
    """
    graph.evidence.extend(records)
    relink_check_evidence(graph)


def _write_check_forms(
    repo_root: Path,
    graph: Graph,
    commands: dict[str, str] | None = None,
) -> Path:
    """
    @brief Write one importable check form per imported check.
    @param[in] repo_root Temporary repository root.
    @param[in] graph Active graph whose check collection is re-expressed.
    @param[in] commands Optional per-check command overrides.
    @return Directory containing the generated check forms.
    """
    record = graph.stage_records[graph.stage]
    directory = repo_root / f".agentic/runs/{graph.run_id}/stages/{graph.stage}"
    directory.mkdir(parents=True, exist_ok=True)
    for index, check in enumerate(graph.checks, start=1):
        command = (commands or {}).get(check.id, check.command)
        (directory / f"check-{index:03d}.toml").write_text(
            "\n".join(
                [
                    "schema_version = 3",
                    f'run_id = "{graph.run_id}"',
                    f'stage = "{graph.stage}"',
                    f"revision = {record.revision}",
                    f'id = "{check.id}"',
                    'level = "unit"',
                    'cites_requirement = ["REQ-TEST"]',
                    "cites_spec = []",
                    f'command = "{command}"',
                    f'path = "{check.path}"',
                    "contract_variants = []",
                    "concerns = []",
                    "parity_targets = []",
                ]
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return directory


def _stage_blocker(repo_root: Path, graph: Graph, check_id: str) -> Blocker:
    """
    @brief Return the exact CLI waiver target this stage's evidence answers.
    @param[in] repo_root Temporary repository root.
    @param[in] graph Active graph in an applied stage.
    @param[in] check_id Immutable check identity.
    @return The blocker `aegis waive add` would accept for that check.
    """
    wanted = (
        f"red-before-green:{check_id}"
        if graph.stage == "check"
        else f"stage:implementation:{check_id}:green-evidence"
    )
    return next(
        item
        for item in stage_blocker_details(repo_root, graph)
        if item.id == wanted
    )


def _waive(repo_root: Path, graph: Graph, check_id: str) -> None:
    """
    @brief Approve one check's stage evidence blocker for exact current state.
    @param[in] repo_root Temporary repository root.
    @param[in,out] graph Active graph receiving the run-local waiver.
    @param[in] check_id Immutable check identity.
    @return None.
    """
    blocker = _stage_blocker(repo_root, graph, check_id)
    add_waiver(
        repo_root,
        graph,
        blocker.id,
        "A human accepted this unobtainable observation.",
        blocker.state_digests,
    )


def _row_check_ids(path: Path) -> list[str]:
    """
    @brief Read the immutable check identities present in a generated form.
    @param[in] path Evidence form path.
    @return Check IDs in document order.
    """
    return [
        line.removeprefix("check_id = ").strip('"')
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("check_id = ")
    ]


def _drop_row(path: Path, check_id: str) -> None:
    """
    @brief Remove exactly one completed result row from a form.
    @param[in] path Evidence form path.
    @param[in] check_id Immutable identity of the row to omit.
    @return None.
    """
    header, *rows = path.read_text(encoding="utf-8").split("\n[[result]]")
    kept = [row for row in rows if f'check_id = "{check_id}"' not in row]
    if len(kept) != len(rows) - 1:
        raise AssertionError(f"expected exactly one row for {check_id}")
    path.write_text(
        header + "\n[[result]]".join(["", *kept]),
        encoding="utf-8",
        newline="\n",
    )


def _replace_once(path: Path, old: str, new: str) -> None:
    """
    @brief Replace one required unique form fragment.
    @param[in] path Form path.
    @param[in] old Expected fragment.
    @param[in] new Replacement fragment.
    @return None.
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
