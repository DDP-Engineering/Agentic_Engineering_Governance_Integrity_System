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
         PR-REPORT-001, PR-DELIVERY-004, AC-RUN-001/002, AC-RED-001/002,
         AC-PROTO-005, and AC-ZONE-001.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from aegis.infrastructure.codecs import parse_markdown_document
from aegis.infrastructure.workspace import FileWorkspace
from aegis.ports.workspace import WorkspaceError

from tests.test_execution_integrity import advance_to, configure_commands
from tests.test_project_knowledge_trace import requirement_data
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


def _set_delivery_section(repo: Path, section: str, content: str) -> None:
    """@brief Replace one author-writable Delivery section."""
    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": section, "content": content, "actor": "agent"},
        )[0]
        == 0
    )


def _recorded_categories(repo: Path, run_id: str) -> dict[str, Any]:
    """@return Decoded deterministic categories from Delivery recorded_state."""
    _, delivery_state = _stage_document(repo, run_id, "delivery")
    categories = {}
    for line in delivery_state["sections"]["recorded_state"].splitlines():
        name, value = line.removeprefix("- ").split(": ", maxsplit=1)
        categories[name] = json.loads(value)
    return categories


def test_delivery_records_derived_state(tmp_path: Path) -> None:
    """@brief Delivery records six truthful skips beside contradictory prose."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    assert invoke(repo, "stage-complete")[0] == 0
    skip_reasons = {
        stage: f"Recorded reason for skipping {stage}."
        for stage in (
            "alignment",
            "requirement",
            "design",
            "check",
            "implementation",
            "validation",
        )
    }
    for stage, reason in skip_reasons.items():
        assert invoke(repo, "stage-start", None, stage)[0] == 0
        assert (
            invoke(
                repo,
                "stage-skip",
                {"actor": "agent", "reason": reason},
            )[0]
            == 0
        )
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    author_sections = {
        "skips_waivers_and_omitted_stages": (
            "No Stage was skipped, waived, or omitted."
        ),
        "evidence_summary": "All automated tests passed.",
        "test_integrity": "No test was changed between red and green.",
    }
    for section, content in author_sections.items():
        _set_delivery_section(repo, section, content)
    _set_delivery_section(repo, "terminal_result", "achieved")
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "approved",
                "actor": "agent",
                "target": "delivery",
                "reason": "Approve the author-written Delivery assessment.",
            },
        )[0]
        == 0
    )

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    _, delivery_state = _stage_document(repo, created["run_id"], "delivery")
    assert {
        section: delivery_state["sections"][section] for section in author_sections
    } == author_sections
    recorded_state = delivery_state["sections"]["recorded_state"]
    for stage, reason in skip_reasons.items():
        assert f'"stage":"{stage}"' in recorded_state
        assert f'"reason":"{reason}"' in recorded_state
    assert "- waiver_escapes: []" in recorded_state
    assert "- non_passing_executions: []" in recorded_state
    assert "- changed_tests: []" in recorded_state
    assert _recorded_categories(repo, created["run_id"])["red_before_green"] == {
        "approved_exception": False,
        "check_skipped": True,
        "conclusion": "not_established",
        "later_executed_green": False,
        "recorded_witness": False,
        "valid_witness": False,
    }
    delivery_bytes = _stage_path(repo, created["run_id"], "delivery").read_bytes()
    assert b"## Recorded State\n" in delivery_bytes


def test_delivery_recorded_state_is_not_writable(tmp_path: Path) -> None:
    """@brief The derived Delivery section stays outside caller authority."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    advance_to(repo, "validation")
    _prepare_delivery(repo)

    exit_code, rejected = invoke(
        repo,
        "stage-set-section",
        {
            "section": "recorded_state",
            "content": "Caller-supplied state.",
            "actor": "agent",
        },
    )

    assert exit_code == 2, rejected
    assert rejected["error"]["code"] == "invalid_input"
    assert "recorded_state" not in rejected["error"]["details"]["allowed"]


def test_recorded_state_reports_open_findings(tmp_path: Path) -> None:
    """@brief Delivery truthfully aggregates only open findings from every Stage."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    assert (
        invoke(
            repo,
            "finding-add",
            {
                "severity": "critical",
                "observation": "The Intake risk remains open.",
                "consequence": "Delivery must retain its visibility.",
            },
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "finding-add",
            {
                "severity": "info",
                "observation": "This Intake note is resolved.",
                "consequence": "It must not appear in the open aggregate.",
            },
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "finding-set-disposition",
            {
                "disposition": "resolved",
                "actor": "agent",
                "reason": "The note was confirmed before Delivery.",
            },
            "--finding",
            "F2",
        )[0]
        == 0
    )
    advance_to(repo, "validation")
    assert (
        invoke(
            repo,
            "finding-add",
            {
                "severity": "error",
                "observation": "The Validation risk remains open.",
                "consequence": "Delivery must retain its visibility.",
            },
        )[0]
        == 0
    )
    _prepare_delivery(repo)
    denial = "No findings remain open."
    _set_delivery_section(repo, "findings_and_residual_risk", denial)

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    stage_names = list(FULL_SECTION_EXPECTATIONS)
    open_findings = []
    for stage in stage_names:
        _, state = _stage_document(repo, created["run_id"], stage)
        open_findings.extend(
            (stage, finding)
            for finding in state["findings"]
            if finding.get("disposition") == "open"
        )
    _, delivery_state = _stage_document(repo, created["run_id"], "delivery")
    assert delivery_state["sections"]["findings_and_residual_risk"] == denial
    assert any(
        finding.get("code", "").startswith("delivery_")
        and finding.get("disposition") == "open"
        for finding in delivery_state["findings"]
    )
    counts_by_severity: dict[str, int] = {}
    for _, finding in open_findings:
        severity = finding["severity"]
        counts_by_severity[severity] = counts_by_severity.get(severity, 0) + 1
    recorded_categories = {}
    for line in delivery_state["sections"]["recorded_state"].splitlines():
        name, value = line.removeprefix("- ").split(": ", maxsplit=1)
        recorded_categories[name] = json.loads(value)
    assert recorded_categories["open_findings"] == {
        "total": len(open_findings),
        "by_severity": dict(sorted(counts_by_severity.items())),
        "stages": sorted({stage for stage, _ in open_findings}),
    }
    assert recorded_categories["open_findings"]["by_severity"]["critical"] == 1
    assert recorded_categories["open_findings"]["by_severity"]["error"] == 1
    assert "info" not in recorded_categories["open_findings"]["by_severity"]
    assert "delivery" in recorded_categories["open_findings"]["stages"]


def test_delivery_recorded_state_covers_structured_integrity_facts(
    tmp_path: Path,
) -> None:
    """@brief The fixed record covers every structured integrity category."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    created = create_run(repo, profile="short")
    advance_to(repo, "check")
    assert (
        invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")
        [1]["outcome"]
        == "failed"
    )
    waiver_reason = "The failing execution is accepted for this focused record."
    waiver_exit, waiver = invoke(
        repo,
        "finding-waive",
        {"actor": "agent", "reason": waiver_reason},
        "--finding",
        "F1",
    )
    assert waiver_exit == 0, json.dumps(waiver, indent=2)
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "exception_approved",
                "actor": "agent",
                "target": "red_before_green",
                "reason": "An explicit exception is also recorded.",
                "alternative_confirmation": "Inspect the durable evidence.",
            },
        )[0]
        == 0
    )
    red_test.write_text("print('passed')\n", encoding="utf-8")
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    assert (
        invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")
        [1]["outcome"]
        == "passed"
    )
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "validation")[0] == 0
    _prepare_delivery(repo)

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    _, delivery_state = _stage_document(repo, created["run_id"], "delivery")
    open_findings = []
    for stage in FULL_SECTION_EXPECTATIONS:
        _, durable_state = _stage_document(repo, created["run_id"], stage)
        open_findings.extend(
            (stage, finding)
            for finding in durable_state["findings"]
            if finding.get("disposition") == "open"
        )
    counts_by_severity: dict[str, int] = {}
    for _, finding in open_findings:
        severity = finding["severity"]
        counts_by_severity[severity] = counts_by_severity.get(severity, 0) + 1
    categories = {
        "skipped_or_omitted_stages": [
            {"reason": "profile=short", "stage": "design", "status": "omitted"}
        ],
        "waiver_escapes": [
            {"reason": waiver_reason, "stage": "check", "target": "F1"}
        ],
        "non_passing_executions": [
            {
                "category": "tests",
                "name": "red",
                "outcome": "failed",
                "stage": "check",
            }
        ],
        "green_test_evidence": [
            {
                "name": "red",
                "provenance": "executed",
                "stage": "implementation",
                "tests": [],
            }
        ],
        "test_selections": [],
        "check_changes": [],
        "changed_tests": [".agentic/tests/test_red.py"],
        "fingerprint_comparison": "performed",
        "red_before_green": {
            "approved_exception": True,
            "check_skipped": False,
            "conclusion": "witness_established",
            "later_executed_green": True,
            "recorded_witness": True,
            "valid_witness": True,
        },
        "open_findings": {
            "total": len(open_findings),
            "by_severity": dict(sorted(counts_by_severity.items())),
            "stages": sorted({stage for stage, _ in open_findings}),
        },
    }
    assert delivery_state["sections"]["recorded_state"] == "\n".join(
        f"- {name}: "
        + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for name, value in categories.items()
    )


def test_delivery_records_actual_test_selection_and_green_provenance(
    tmp_path: Path,
) -> None:
    """@brief Author prose cannot hide selected tests or green provenance."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic" / "tests" / "test_retry.py").write_text(
        "def test_retry_history(): pass\n", encoding="utf-8"
    )
    created = create_run(repo, profile="short")
    assert invoke(repo, "requirement-create", requirement_data())[0] == 0
    impacted = invoke(
        repo,
        "trace-impacted",
        {"changed_files": ["src/retry.py"], "changed_tests": []},
    )[1]["data"]
    fallback = invoke(
        repo,
        "trace-impacted",
        {"changed_files": ["src/unmapped.py"], "changed_tests": []},
    )[1]["data"]
    assert impacted["mode"] == "impacted"
    assert fallback["mode"] == "full"
    advance_to(repo, "check")
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "exception_approved",
                "actor": "agent",
                "target": "red_before_green",
                "reason": "Selection reporting is the behavior under test.",
                "alternative_confirmation": "Inspect durable execution evidence.",
            },
        )[0]
        == 0
    )
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    executed = invoke(
        repo,
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "select",
        "--selection",
        impacted["label"],
    )[1]
    assert executed["outcome"] == "passed"
    assert (
        invoke(
            repo,
            "evidence-add",
            {
                "kind": "automated",
                "category": "tests",
                "command": ["python", "-m", "pytest", "-q"],
                "working_directory": ".",
                "outcome": "passed",
                "exit_status": 0,
                "observed_result": "A separately reported green run passed.",
                "tests": [".agentic/tests/test_retry.py::test_retry_history"],
            },
        )[0]
        == 0
    )
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "validation")[0] == 0
    _prepare_delivery(repo)
    _set_delivery_section(repo, "evidence_summary", "No test selection was recorded.")
    _set_delivery_section(repo, "findings_and_residual_risk", "Nothing to report.")

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    categories = _recorded_categories(repo, created["run_id"])
    selections = {item["label"]: item for item in categories["test_selections"]}
    assert selections[impacted["label"]] == {
        "executions": [
            {
                "fallback_reasons": [],
                "mode": "impacted",
                "name": "select",
                "outcome": "passed",
                "stage": "implementation",
            }
        ],
        "fallback_reasons": [],
        "full_suite_commands": [],
        "label": impacted["label"],
        "mode": "impacted",
        "stage": "intake",
        "tests": [".agentic/tests/test_retry.py::test_retry_history"],
    }
    assert selections[fallback["label"]]["mode"] == "full"
    assert selections[fallback["label"]]["fallback_reasons"] == [
        "No complete test coverage for src/unmapped.py."
    ]
    assert selections[fallback["label"]]["full_suite_commands"] == fallback[
        "full_suite_commands"
    ]
    assert selections[fallback["label"]]["executions"] == []
    assert categories["green_test_evidence"] == [
        {
            "name": "select",
            "provenance": "executed",
            "stage": "implementation",
            "tests": [".agentic/tests/test_retry.py::test_retry_history"],
        },
        {
            "name": None,
            "provenance": "reported",
            "stage": "implementation",
            "tests": [".agentic/tests/test_retry.py::test_retry_history"],
        },
    ]
    assert categories["red_before_green"] == {
        "approved_exception": True,
        "check_skipped": False,
        "conclusion": "exception_approved",
        "later_executed_green": True,
        "recorded_witness": False,
        "valid_witness": False,
    }


def test_delivery_records_check_content_and_repository_state_changes(
    tmp_path: Path,
) -> None:
    """@brief Author findings text cannot hide either Check change category."""
    repo = installed_repository(tmp_path)
    (repo / "src").mkdir()
    source = repo / "src" / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "src/app.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    created = create_run(repo, profile="short")
    advance_to(repo, "check")
    source.write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "src/app.py"], check=True)
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    assert invoke(repo, "stage-skip", {"actor": "agent", "reason": "No build."})[0] == 0
    assert invoke(repo, "stage-start", None, "validation")[0] == 0
    assert (
        invoke(repo, "stage-skip", {"actor": "agent", "reason": "No validation."})[0]
        == 0
    )
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    _set_delivery_section(repo, "findings_and_residual_risk", "Nothing to report.")
    _set_delivery_section(repo, "terminal_result", "partially_achieved")
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "approved",
                "actor": "agent",
                "target": "delivery",
                "reason": "Approve the truthful durable state.",
            },
        )[0]
        == 0
    )

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    assert _recorded_categories(repo, created["run_id"])["check_changes"] == [
        {"artifact": "src/app.py", "code": "check_out_of_zone_change"},
        {
            "artifact": ".agentic/runs/" + created["run_id"] + "/05-check.md",
            "code": "check_git_state_changed",
        },
    ]


def test_skipped_check_red_is_not_a_valid_delivery_witness(tmp_path: Path) -> None:
    """@brief A skipped Check cannot launder an earlier red without green."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    created = create_run(repo, profile="short")
    advance_to(repo, "check")
    red = invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")
    assert red[1]["outcome"] == "failed"
    assert (
        invoke(
            repo,
            "stage-skip",
            {"actor": "agent", "reason": "Check cannot continue."},
        )[0]
        == 0
    )
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    assert (
        invoke(
            repo,
            "stage-skip",
            {"actor": "agent", "reason": "No implementation."},
        )[0]
        == 0
    )
    assert invoke(repo, "stage-start", None, "validation")[0] == 0
    assert (
        invoke(repo, "stage-skip", {"actor": "agent", "reason": "No validation."})[0]
        == 0
    )
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    _set_delivery_section(repo, "terminal_result", "not_achieved")
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "approved",
                "actor": "agent",
                "target": "delivery",
                "reason": "Approve the incomplete outcome.",
            },
        )[0]
        == 0
    )

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    categories = _recorded_categories(repo, created["run_id"])
    assert categories["red_before_green"] == {
        "approved_exception": False,
        "check_skipped": True,
        "conclusion": "not_established",
        "later_executed_green": False,
        "recorded_witness": True,
        "valid_witness": False,
    }
    assert categories["green_test_evidence"] == []
    assert any(
        item["stage"] == "check" and item["outcome"] == "failed"
        for item in categories["non_passing_executions"]
    )


def test_clean_delivery_reports_every_evaluated_expectation(tmp_path: Path) -> None:
    """@brief Clean results count evaluated sections and approval, not findings."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    advance_to(repo, "validation")
    _prepare_delivery(repo)
    for section in (
        "project_artifact_changes",
        "implementation_changes",
        "test_integrity",
        "component_drift_review",
        "delivery_decision",
    ):
        _set_delivery_section(repo, section, f"Recorded {section}.")

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    assert completed["findings"] == []
    assert completed["data"]["evaluated_expectation_count"] == 11


def test_non_clean_stage_counts_clean_and_failing_expectations_once(
    tmp_path: Path,
) -> None:
    """@brief Evaluation count remains distinct when only one section is clean."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    _set_delivery_section(repo, "inputs", "Recorded Intake input.")

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    assert len(completed["findings"]) == 6
    assert completed["data"]["evaluated_expectation_count"] == 7


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
    created = create_run(repo)
    advance_to(repo, "check")

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    finding = next(
        item
        for item in completed["findings"]
        if item["code"] == "check_red_witness_missing"
    )
    assert finding["disposition"] == "open"
    _, check_state = _stage_document(repo, created["run_id"], "check")
    durable_finding = next(
        item
        for item in check_state["findings"]
        if item["code"] == "check_red_witness_missing"
    )
    guidance = " ".join(
        (durable_finding["observation"], durable_finding["consequence"])
    )
    for required in (
        "execution-run",
        "decision-add",
        "red_before_green",
        "exception_approved",
        "reason",
        "alternative_confirmation",
    ):
        assert required in guidance


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
        "audits.pass",
        "lints.exit5",
        "lints.pass",
        "tests.arbitrary_exit5",
        "tests.cache",
        "tests.discover",
        "tests.fail",
        "tests.integrity",
        "tests.large",
        "tests.missing",
        "tests.pass",
        "tests.pytest_empty",
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
