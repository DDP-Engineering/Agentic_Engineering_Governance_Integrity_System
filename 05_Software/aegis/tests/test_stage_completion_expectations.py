#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_stage_completion_expectations.py
@brief   Verify truthful advisory expectation evaluation at Stage completion.
@details Covers CP-STAGE-004, PR-POSTURE-002, PR-RED, PR-STATE, FS-STAGE-015,
         AC-RUN-001/002, AC-RED-001/002, AC-PROTO-005, and AC-ZONE-001.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from aegis.infrastructure.codecs import parse_markdown_document
from aegis.infrastructure.workspace import FileWorkspace
from aegis.ports.workspace import WorkspaceError

from tests.test_execution_integrity import advance_to, configure_commands
from tests.test_run_stage_workflow import create_run, installed_repository, invoke

FULL_SECTION_EXPECTATIONS = {
    "intake": {
        "intake_inputs_unrecorded",
        "intake_configured_project_paths_unrecorded",
        "intake_relevant_project_knowledge_unrecorded",
        "intake_restated_ask_unrecorded",
        "intake_initially_affected_repository_area_unrecorded",
        "intake_facts_and_uncertainties_unrecorded",
        "intake_outputs_and_handoff_unrecorded",
    },
    "alignment": {
        "alignment_inputs_from_intake_unrecorded",
        "alignment_proposed_scope_unrecorded",
        "alignment_developer_corrections_unrecorded",
        "alignment_agreed_scope_unrecorded",
        "alignment_outputs_and_handoff_unrecorded",
        "alignment_approval_unrecorded",
    },
    "requirement": {
        "requirement_inputs_from_alignment_unrecorded",
        "requirement_requirement_artifact_changes_unrecorded",
        "requirement_traceability_unrecorded",
        "requirement_risk_based_test_depth_decision_unrecorded",
        "requirement_gaps_and_uncertainties_unrecorded",
        "requirement_outputs_and_handoff_unrecorded",
        "requirement_approval_unrecorded",
    },
    "design": {
        "design_inputs_unrecorded",
        "design_proposed_solution_unrecorded",
        "design_requirement_coverage_unrecorded",
        "design_interfaces_data_and_failure_behavior_unrecorded",
        "design_alternatives_and_risks_unrecorded",
        "design_outputs_and_handoff_unrecorded",
        "design_approval_unrecorded",
    },
    "check": {
        "check_inputs_unrecorded",
        "check_test_work_unrecorded",
        "check_recorded_red_evidence_unrecorded",
        "check_test_fingerprints_at_red_unrecorded",
        "check_red_before_green_decision_unrecorded",
        "check_outputs_and_handoff_unrecorded",
    },
    "implementation": {
        "implementation_inputs_unrecorded",
        "implementation_implementation_changes_unrecorded",
        "implementation_test_integrity_comparison_unrecorded",
        "implementation_implementation_evidence_unrecorded",
        "implementation_component_documentation_review_unrecorded",
        "implementation_outputs_and_handoff_unrecorded",
    },
    "validation": {
        "validation_inputs_unrecorded",
        "validation_impacted_test_selection_unrecorded",
        "validation_automated_validation_evidence_unrecorded",
        "validation_manual_validation_evidence_unrecorded",
        "validation_test_integrity_conclusion_unrecorded",
        "validation_outputs_and_handoff_unrecorded",
    },
    "delivery": {
        "delivery_project_artifact_changes_unrecorded",
        "delivery_implementation_changes_unrecorded",
        "delivery_test_integrity_unrecorded",
        "delivery_component_drift_review_unrecorded",
        "delivery_delivery_decision_unrecorded",
    },
}


def _stage_path(repo: Path, run_id: str, stage: str) -> Path:
    """@return Canonical path for one Stage in a synthetic Run."""
    sequence = list(FULL_SECTION_EXPECTATIONS).index(stage) + 1
    return repo / ".agentic" / "runs" / run_id / f"{sequence:02d}-{stage}.md"


def _stage_document(
    repo: Path, run_id: str, stage: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """@return Parsed metadata and state for one durable Stage."""
    path = _stage_path(repo, run_id, stage)
    metadata, state, _ = parse_markdown_document(path.read_bytes(), path=str(path))
    return metadata, state


def _prepare_delivery(repo: Path) -> None:
    """@brief Satisfy only the preserved hard Delivery completion preconditions."""
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": "terminal_result", "content": "achieved", "actor": "agent"},
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "approved",
                "actor": "agent",
                "target": "delivery",
                "reason": "The terminal record is truthful.",
            },
        )[0]
        == 0
    )


@pytest.mark.parametrize("stage", tuple(FULL_SECTION_EXPECTATIONS))
def test_full_profile_evaluates_every_stage_section_expectation(
    tmp_path: Path, stage: str
) -> None:
    """@brief Every full-profile Stage reports each still-unrecorded section."""
    repo = installed_repository(tmp_path)
    create_run(repo, profile="full")
    if stage == "delivery":
        advance_to(repo, "validation")
        _prepare_delivery(repo)
    else:
        advance_to(repo, stage)

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    assert completed["data"]["status"] == "completed"
    section_codes = {
        finding["code"]
        for finding in completed["findings"]
        if finding["code"].endswith("_unrecorded")
    }
    assert section_codes == FULL_SECTION_EXPECTATIONS[stage]


def test_short_profile_omits_design_but_retains_check_expectations(
    tmp_path: Path,
) -> None:
    """@brief Short omits only Design and keeps truthful Check evaluation."""
    repo = installed_repository(tmp_path)
    created = create_run(repo, profile="short")
    advance_to(repo, "check")

    design = invoke(repo, "stage-show", None, "--stage", "design")[1]
    completed = invoke(repo, "stage-complete")[1]

    assert design["data"]["status"] == "omitted"
    assert "check_red_witness_missing" in {
        finding["code"] for finding in completed["findings"]
    }
    assert not any(
        finding["code"].startswith("design_") for finding in completed["findings"]
    )
    design_metadata, design_state = _stage_document(repo, created["run_id"], "design")
    assert design_metadata["status"] == "omitted"
    assert design_state["findings"] == []


def test_empty_intake_findings_close_atomically_and_match_durable_state(
    tmp_path: Path,
) -> None:
    """@brief Advisory findings and completion publish as one truthful result."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    assert completed["data"]["status"] == "completed"
    assert {
        finding["code"] for finding in completed["findings"]
    } == FULL_SECTION_EXPECTATIONS["intake"]
    metadata, state = _stage_document(repo, created["run_id"], "intake")
    assert metadata["status"] == "completed"
    assert [finding["code"] for finding in state["findings"]] == [
        finding["code"] for finding in completed["findings"]
    ]
    run_bytes = (repo / ".agentic" / "runs" / created["run_id"] / "run.md").read_bytes()
    assert b"| Intake | completed | Recorded |" in run_bytes


def test_completion_publication_failure_preserves_exact_stage_and_run_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Failed atomic publication exposes neither findings nor completion."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    stage_path = _stage_path(repo, created["run_id"], "intake")
    run_path = repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    before = (stage_path.read_bytes(), run_path.read_bytes())

    def refuse_publication(*_: Any, **__: Any) -> dict[str, str | None]:
        raise WorkspaceError("publication_failed", "Injected publication failure.")

    monkeypatch.setattr(FileWorkspace, "publish", refuse_publication)

    exit_code, failed = invoke(repo, "stage-complete")

    assert exit_code == 6, failed
    assert failed["error"]["code"] == "publication_failed"
    assert (stage_path.read_bytes(), run_path.read_bytes()) == before


def test_check_passing_execution_without_prior_red_is_reported(tmp_path: Path) -> None:
    """@brief An unexpected pre-implementation pass is not a red witness."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    create_run(repo)
    advance_to(repo, "check")
    assert (
        invoke(repo, "execution-run", None, "--category", "tests", "--name", "pass")[0]
        == 0
    )

    completed = invoke(repo, "stage-complete")[1]

    assert "check_red_witness_unexpected_pass" in {
        finding["code"] for finding in completed["findings"]
    }
    assert "check_red_witness_missing" not in {
        finding["code"] for finding in completed["findings"]
    }


def test_check_without_test_execution_reports_missing_red(tmp_path: Path) -> None:
    """@brief Absence of actual red evidence remains visible without blocking."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    advance_to(repo, "check")

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    finding = next(
        item
        for item in completed["findings"]
        if item["code"] == "check_red_witness_missing"
    )
    assert finding["disposition"] == "open"


def test_check_valid_red_witness_remains_immutable_and_satisfies_expectation(
    tmp_path: Path,
) -> None:
    """@brief Actual failing test evidence with fingerprints remains the witness."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    created = create_run(repo)
    advance_to(repo, "check")
    assert (
        invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")[1][
            "outcome"
        ]
        == "failed"
    )
    _, before = _stage_document(repo, created["run_id"], "check")
    witness = before["evidence"][-1]

    completed = invoke(repo, "stage-complete")[1]

    assert not {finding["code"] for finding in completed["findings"]} & {
        "check_red_witness_missing",
        "check_red_witness_unexpected_pass",
        "check_red_witness_not_prior",
    }
    _, after = _stage_document(repo, created["run_id"], "check")
    assert after["evidence"][-1] == witness


def test_check_valid_red_exception_is_visible_and_never_passed(tmp_path: Path) -> None:
    """@brief Complete approved non-applicability is represented truthfully."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    advance_to(repo, "check")
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "exception_approved",
                "actor": "agent",
                "target": "red_before_green",
                "reason": "The change affects documentation rendering only.",
                "alternative_confirmation": "Inspect the rendered document.",
            },
        )[0]
        == 0
    )

    completed = invoke(repo, "stage-complete")[1]

    finding = next(
        item
        for item in completed["findings"]
        if item["code"] == "check_red_exception_approved"
    )
    assert finding["disposition"] == "not_applicable"
    assert finding["severity"] == "info"
    assert finding.get("outcome") != "passed"


def test_implementation_without_green_test_evidence_is_advisory(tmp_path: Path) -> None:
    """@brief Missing post-implementation green remains visible and non-blocking."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    advance_to(repo, "implementation")

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    assert "implementation_green_evidence_missing" in {
        finding["code"] for finding in completed["findings"]
    }


def test_validation_reports_each_configured_command_without_recorded_evidence(
    tmp_path: Path,
) -> None:
    """@brief Applicable configured commands are evaluated from durable evidence."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    create_run(repo)
    advance_to(repo, "validation")

    completed = invoke(repo, "stage-complete")[1]

    missing = [
        finding
        for finding in completed["findings"]
        if finding["code"] == "validation_command_evidence_missing"
    ]
    assert {finding["summary"].split()[0] for finding in missing} == {
        "tests.fail",
        "tests.large",
        "tests.missing",
        "tests.pass",
        "tests.red",
        "tests.select",
        "tests.slow",
    }


def test_completion_does_not_launch_configured_commands_or_mutate_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Completion only evaluates state and keeps Git content unchanged."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    create_run(repo)
    advance_to(repo, "check")
    before_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
    ).stdout
    index_path = repo / ".git" / "index"
    before_index = index_path.read_bytes() if index_path.exists() else None

    def reject_execution(*_: Any, **__: Any) -> Any:
        raise AssertionError("stage.complete launched a configured command")

    monkeypatch.setattr(FileWorkspace, "execute_command", reject_execution)

    assert invoke(repo, "stage-complete")[0] == 0

    after_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
    ).stdout
    after_index = index_path.read_bytes() if index_path.exists() else None
    assert (after_head, after_index) == (before_head, before_index)


def test_revisit_and_recomplete_preserve_finding_labels_evidence_and_history(
    tmp_path: Path,
) -> None:
    """@brief Later completion appends history without overwriting earlier truth."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    assert invoke(repo, "stage-complete")[0] == 0
    _, first = _stage_document(repo, created["run_id"], "intake")
    original_findings = list(first["findings"])
    assert (
        invoke(
            repo,
            "stage-revisit",
            {"actor": "agent", "reason": "Record newly discovered context."},
            "intake",
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "evidence-add",
            {
                "kind": "manual",
                "actor": "agent",
                "procedure": "Inspect the Run history.",
                "expected": "Earlier completion remains visible.",
                "actual": "Earlier completion remains visible.",
            },
        )[0]
        == 0
    )

    assert invoke(repo, "stage-complete")[0] == 0

    _, later = _stage_document(repo, created["run_id"], "intake")
    assert later["findings"][: len(original_findings)] == original_findings
    labels = [finding["label"] for finding in later["findings"]]
    assert len(labels) == len(set(labels))
    assert later["evidence"][0]["actual"] == "Earlier completion remains visible."
    assert [event["event"] for event in later["events"]].count("stage_completed") == 2


def test_stale_completion_revision_rejects_before_evaluation_and_preserves_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Stale machine authority prevents evaluation and publication."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    shown = invoke(repo, "stage-show")[1]
    stale = shown["revision"]
    assert (
        invoke(
            repo,
            "stage-set-section",
            {
                "section": "restated_ask",
                "content": "Preserve stale-call bytes.",
                "actor": "agent",
            },
        )[0]
        == 0
    )
    stage_path = _stage_path(repo, created["run_id"], "intake")
    run_path = repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    before = (stage_path.read_bytes(), run_path.read_bytes())

    def reject_git_observation(*_: Any, **__: Any) -> Any:
        raise AssertionError("stale completion evaluated repository state")

    monkeypatch.setattr(FileWorkspace, "git_snapshot", reject_git_observation)

    exit_code, rejected = invoke(repo, "stage-complete", expected_revision=stale)

    assert exit_code == 4, rejected
    assert rejected["error"]["code"] == "state_conflict"
    assert (stage_path.read_bytes(), run_path.read_bytes()) == before
