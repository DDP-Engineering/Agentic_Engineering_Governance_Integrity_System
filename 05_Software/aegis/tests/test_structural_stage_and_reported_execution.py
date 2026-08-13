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
@file    test_structural_stage_and_reported_execution.py
@brief   Verify structural Stage completion and caller-reported command evidence.
@details Covers PR-WORKFLOW-011-013, PR-CONFIG-006-013, AC-STAGE-003,
         AC-EXEC-001, REQ-FUNC-1b8843e3, REQ-FUNC-cc16f4ab,
         REQ-FUNC-785d5956, and REQ-FUNC-722376a0.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from aegis.application.operation_registry import operations_for
from aegis.application.stage_expectations import evaluate_stage_expectations
from aegis.infrastructure.codecs import parse_markdown_document

from tests.test_run_stage_workflow import create_run, installed_repository, invoke


def _stage_state(repo: Path, run_id: str, sequence: int, stage: str) -> dict:
    """@return One decoded Stage state from the synthetic repository."""
    path = repo / ".agentic" / "runs" / run_id / f"{sequence:02d}-{stage}.md"
    return parse_markdown_document(path.read_bytes(), path=str(path))[1]


def _recorded_sections(stage: str) -> dict[str, str]:
    """@return Minimal non-blank section content for one structural evaluation."""
    from aegis.application.stage_expectations import STAGE_SECTION_EXPECTATIONS

    return {name: "Recorded fact." for name in STAGE_SECTION_EXPECTATIONS[stage]}


def test_stage_evaluator_reports_only_common_structural_findings() -> None:
    """@brief Engineering-quality concerns never become completion findings."""
    state = {
        "sections": _recorded_sections("check"),
        "evidence": [
            {
                "kind": "automated",
                "category": "tests",
                "name": "project",
                "outcome": "passed",
            }
        ],
        "decisions": [],
    }

    evaluation = evaluate_stage_expectations(
        stage="check",
        profile="full",
        state=state,
        designated_references=(),
        continuous_delegation=False,
    )

    assert evaluation.findings == ()
    forbidden = ("scope", "design", "adequacy", "red_witness", "risk")
    assert not any(
        term in finding["code"]
        for finding in evaluation.findings
        for term in forbidden
    )


def test_stage_evaluator_reports_blank_none_reference_and_outcome_facts() -> None:
    """@brief Empty sections, missing references, and invalid outcomes are factual."""
    state = {
        "sections": {**_recorded_sections("validation"), "inputs": None},
        "evidence": [
            {"kind": "automated", "category": "tests", "name": "project"},
            {
                "kind": "automated",
                "category": "lints",
                "name": "ruff",
                "outcome": "unexpected",
            },
        ],
        "decisions": [],
    }

    evaluation = evaluate_stage_expectations(
        stage="validation",
        profile="full",
        state=state,
        designated_references=(("missing.log", False),),
        continuous_delegation=False,
    )
    codes = [finding["code"] for finding in evaluation.findings]

    assert codes == [
        "validation_inputs_unrecorded",
        "stage_reference_missing",
        "recorded_command_outcome_invalid",
        "recorded_command_outcome_invalid",
    ]


def test_applicable_approval_is_structural_and_continuous_delegation_satisfies_it(
) -> None:
    """@brief Approval presence is checked without judging its rationale."""
    state = {
        "sections": _recorded_sections("alignment"),
        "evidence": [],
        "decisions": [],
    }

    checkpoint = evaluate_stage_expectations(
        stage="alignment",
        profile="full",
        state=state,
        designated_references=(),
        continuous_delegation=False,
    )
    continuous = evaluate_stage_expectations(
        stage="alignment",
        profile="full",
        state=state,
        designated_references=(),
        continuous_delegation=True,
    )

    assert [item["code"] for item in checkpoint.findings] == [
        "alignment_approval_unrecorded"
    ]
    assert continuous.findings == ()


def test_execution_run_is_absent_and_execution_list_cannot_spawn(
    tmp_path: Path,
) -> None:
    """@brief Public guidance remains read-only and exposes no process launcher."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    operations = {item.operation for item in operations_for("AEGIS")}
    source_root = Path(__file__).parents[1] / "template/.agentic/aegis/cli/src/aegis"

    assert "execution.run" not in operations
    assert not (source_root / "domain/execution.py").exists()
    assert not (source_root / "infrastructure/process.py").exists()
    with patch.object(subprocess, "Popen", side_effect=AssertionError("spawned")):
        listed_exit, listed = invoke(repo, "execution-list")
        removed_exit, removed = invoke(
            repo, "execution-run", None, "--category", "tests", "--name", "project"
        )

    assert listed_exit == 0, listed
    assert listed["data"]["commands"][0]["command"]
    assert "timeout_seconds" not in listed["data"]["commands"][0]
    assert removed_exit == 2
    assert removed["error"]["code"] == "invalid_input"


def test_reported_evidence_supports_all_outcomes_optional_tests_and_attachment(
    tmp_path: Path,
) -> None:
    """@brief evidence.add records every operational outcome without execution."""
    repo = installed_repository(tmp_path)
    run_id = create_run(repo)["run_id"]
    output = tmp_path / "large-output.log"
    output.write_text("external command output\n", encoding="utf-8")
    attachment = invoke(
        repo,
        "attachment-add",
        {
            "source": str(output),
            "purpose": "retained external output",
            "content_type": "text/plain",
        },
    )[1]["data"]["attachment"]["path"]
    cases = (
        ("passed", 0),
        ("failed", 7),
        ("timed_out", None),
        ("cancelled", None),
        ("launch_error", None),
    )
    for index, (outcome, exit_status) in enumerate(cases):
        data = {
            "kind": "automated",
            "category": "tests" if index < 2 else "audits",
            "name": f"reported-{outcome}",
            "command": ["tool", "--check"],
            "working_directory": ".",
            "outcome": outcome,
            "exit_status": exit_status,
            "observed_result": f"Caller observed {outcome}.",
        }
        if index < 2:
            data["tests"] = ["tests/test_feature.py::test_behavior"]
        if outcome == "launch_error":
            data["attachment"] = attachment
        exit_code, response = invoke(repo, "evidence-add", data)
        assert exit_code == 0, response
        assert response["outcome"] == outcome

    evidence = _stage_state(repo, run_id, 1, "intake")["evidence"]
    assert [item["outcome"] for item in evidence] == [item[0] for item in cases]
    assert [item["engineering_conclusion"] for item in evidence] == [
        "passed",
        "failed",
        "unknown",
        "unknown",
        "unknown",
    ]
    assert evidence[-1]["attachment"] == attachment
    assert all(item["provenance"] == "reported" for item in evidence)


def test_reported_red_and_green_preserve_fingerprint_comparison(
    tmp_path: Path,
) -> None:
    """@brief Reported red/green evidence remains visible in Delivery."""
    repo = installed_repository(tmp_path)
    created = create_run(repo, profile="short")
    test_path = repo / ".agentic" / "tests" / "test_feature.py"
    test_path.write_text("assert False\n", encoding="utf-8")
    next_stage = {
        "intake": "alignment",
        "alignment": "requirement",
        "requirement": "check",
    }
    for stage in ("intake", "alignment", "requirement"):
        assert invoke(repo, "stage-show")[1]["stage"] == stage
        assert invoke(repo, "stage-complete")[0] == 0
        assert invoke(repo, "stage-start", None, next_stage[stage])[0] == 0

    red = {
        "kind": "automated",
        "category": "tests",
        "name": "project",
        "selector": ".agentic/tests/test_feature.py",
        "working_directory": ".",
        "outcome": "failed",
        "exit_status": 1,
        "observed_result": "The selected test failed.",
        "tests": [".agentic/tests/test_feature.py"],
    }
    assert invoke(repo, "evidence-add", red)[0] == 0
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    test_path.write_text("assert True\n", encoding="utf-8")
    green = {
        **red,
        "outcome": "passed",
        "exit_status": 0,
        "observed_result": "The selected test passed.",
    }
    exit_code, response = invoke(repo, "evidence-add", green)

    assert exit_code == 0, response
    state = _stage_state(repo, created["run_id"], 6, "implementation")
    comparison = state["evidence"][-1]["red_fingerprint_comparison"]
    assert comparison["changed_tests"] == [".agentic/tests/test_feature.py"]
    assert any(item["code"] == "test_changed_after_red" for item in state["findings"])

    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "validation")[0] == 0
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    assert (
        invoke(
            repo,
            "stage-set-section",
            {
                "section": "requested_and_delivered_outcome",
                "content": "Requested test integrity; delivered recorded evidence.",
                "actor": "agent",
            },
        )[0]
        == 0
    )
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
                "reason": "The report is accurate.",
                "approval_source": "developer",
            },
        )[0]
        == 0
    )
    assert invoke(repo, "stage-complete")[0] == 0

    delivery = _stage_state(repo, created["run_id"], 8, "delivery")
    recorded_state = delivery["sections"]["recorded_state"]
    assert '- changed_tests: [".agentic/tests/test_feature.py"]' in recorded_state
    assert '- fingerprint_comparison: "performed"' in recorded_state
    assert '"later_executed_green":true' in recorded_state


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
