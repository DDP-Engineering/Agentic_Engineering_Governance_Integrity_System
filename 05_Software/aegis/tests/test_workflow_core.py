#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_workflow_core.py
@brief Workflow support module for test_workflow_core.
@details Covers expected workflow behavior through focused pytest checks.
@author Eng. Dan Dumitru Pasare
@date 2026-06-20
@version 0.4.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.invariants import blocking_failures, evaluate
from aegis.models import Graph
from aegis.store import load_graph


def run_cli(tmp_path: Path, *args: str) -> None:
    """
    @brief      Run CLI workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  args Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        main(list(args))
    finally:
        os.chdir(cwd)


def test_feature_flow_reaches_green_invariants(tmp_path: Path) -> None:
    """
    @brief      Handle test feature flow reaches green invariants workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(
        tmp_path,
        "add-spec",
        "--id",
        "S-0001",
        "--tag",
        "behavior",
        "--statement",
        "WHEN a valid discount is applied, total is reduced.",
        "--status",
        "accepted",
        "--example",
        "Given total 100, when SAVE10, then total 90.",
    )
    run_cli(
        tmp_path,
        "add-check",
        "--id",
        "C-0001",
        "--cites-spec",
        "S-0001",
        "--path",
        "tests/test_discount.py",
    )
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "fail",
        "--summary",
        "C-0001 fails before implementation",
        "--check-id",
        "C-0001",
    )
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "pass",
        "--summary",
        "C-0001 passes after implementation",
        "--check-id",
        "C-0001",
    )
    graph = load_graph(tmp_path)
    failures = blocking_failures(evaluate(tmp_path, graph))
    assert failures == []


def test_green_check_without_red_evidence_fails(tmp_path: Path) -> None:
    """
    @brief      Handle test green check without red evidence fails workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(
        tmp_path,
        "add-spec",
        "--id",
        "S-0001",
        "--tag",
        "behavior",
        "--statement",
        "WHEN a valid discount is applied, total is reduced.",
        "--status",
        "accepted",
    )
    run_cli(
        tmp_path,
        "add-check",
        "--id",
        "C-0001",
        "--cites-spec",
        "S-0001",
        "--state",
        "green",
    )
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "pass",
        "--summary",
        "C-0001 passes",
    )
    graph = load_graph(tmp_path)
    failures = {item.id for item in blocking_failures(evaluate(tmp_path, graph))}
    assert "INV-3" in failures


def test_report_contains_intent_and_invariants(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief      Handle test report contains intent and invariants workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "fix", "--statement", "Fix rounding")
    run_cli(tmp_path, "report")
    output = capsys.readouterr().out
    assert "Fix rounding" in output
    assert "INV-1" in output
    assert "Report written:" in output


def test_status_is_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief      Handle test status is json workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.3.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    capsys.readouterr()
    run_cli(tmp_path, "status")
    data = json.loads(capsys.readouterr().out)
    assert data["stage"] == "intake"
    assert data["access_mode"] == "standard"
    assert data["intent"]["kind"] == "feature"
    assert data["alignment"] is None


def test_next_enters_alignment_when_enabled(tmp_path: Path) -> None:
    """
    @brief      Verify standard next routing enters intent alignment by default.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.2.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add export")
    run_cli(tmp_path, "next")

    graph = load_graph(tmp_path)
    assert graph.stage == "alignment"


def test_next_skips_alignment_when_disabled(tmp_path: Path) -> None:
    """
    @brief      Verify disabled alignment policy skips the standard alignment stage.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    (agentic / "workflow.toml").write_text(
        """
[alignment]
enabled = false
""",
        encoding="utf-8",
    )

    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add export")
    run_cli(tmp_path, "next")

    graph = load_graph(tmp_path)
    assert graph.stage == "requirement"


def test_intake_triage_command_is_not_registered(tmp_path: Path) -> None:
    """
    @brief      Verify the old intake-triage command is not exposed.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  SystemExit Expected argparse exit for unknown command.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    with pytest.raises(SystemExit):
        run_cli(tmp_path, "intake-triage", "--help")


def test_alignment_records_graph_and_journal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief      Verify intent alignment stores structured graph and journal data.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @param[in]  capsys Pytest capture helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add export")
    run_cli(tmp_path, "next")
    capsys.readouterr()
    run_cli(
        tmp_path,
        "alignment",
        "--source",
        "human prompt",
        "--understanding",
        "Add export support.",
        "--scope",
        "in: export command; out: billing model changes",
        "--assumption",
        "CSV is acceptable.",
        "--acceptance",
        "Export command writes a CSV file.",
        "--question",
        "Should the first export be CSV or JSON?",
        "--recommended-response",
        "Use CSV because it matches the requested export workflow.",
        "--planned-path",
        "src/exporter.py",
        "--risk",
        "low",
        "--decision",
        "proceed",
        "--reason",
        "No open questions and low risk.",
    )
    output = json.loads(capsys.readouterr().out)

    graph = load_graph(tmp_path)
    alignment = graph.alignment
    assert alignment is not None
    assert alignment.source == "human prompt"
    assert alignment.assumptions == ["CSV is acceptable."]
    assert alignment.acceptance == ["Export command writes a CSV file."]
    assert alignment.open_questions == ["Should the first export be CSV or JSON?"]
    assert alignment.recommended_responses == ["Use CSV because it matches the requested export workflow."]
    assert alignment.planned_paths == ["src/exporter.py"]
    assert output["decision"] == "proceed"

    journal = tmp_path / ".agentic" / "runs" / graph.run_id / "journal.jsonl"
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "alignment.recorded"
    assert events[-1]["data"]["understanding"] == "Add export support."


def test_alignment_status_and_report_include_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief      Verify status and report surface intent-alignment details.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @param[in]  capsys Pytest capture helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add export")
    run_cli(tmp_path, "next")
    run_cli(
        tmp_path,
        "alignment",
        "--source",
        "ISSUE-1",
        "--understanding",
        "Add export support.",
        "--scope",
        "in: exporter",
        "--acceptance",
        "Exporter has a passing check.",
        "--risk",
        "low",
        "--decision",
        "proceed",
        "--reason",
        "Low risk.",
    )
    capsys.readouterr()

    run_cli(tmp_path, "status")
    status = json.loads(capsys.readouterr().out)
    assert status["alignment"]["source"] == "ISSUE-1"
    assert status["alignment"]["decision"] == "proceed"

    run_cli(tmp_path, "report")
    report = capsys.readouterr().out
    assert "## Intent Alignment" in report
    assert "Add export support." in report


def test_alignment_requires_pause_for_questions_without_recommended_responses(tmp_path: Path) -> None:
    """
    @brief      Verify unanswered open questions reject a proceed decision.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add export")
    run_cli(tmp_path, "next")

    with pytest.raises(SystemExit, match="open questions need recommended responses"):
        run_cli(
            tmp_path,
            "alignment",
            "--source",
            "human prompt",
            "--understanding",
            "Add export support.",
            "--scope",
            "in: exporter",
            "--acceptance",
            "Exporter has a passing check.",
            "--question",
            "Which file format is required?",
            "--risk",
            "low",
            "--decision",
            "proceed",
            "--reason",
            "Trying to proceed.",
        )


def test_alignment_allows_questions_with_recommended_responses(tmp_path: Path) -> None:
    """
    @brief      Verify open questions can proceed with recommended responses.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add export")
    run_cli(tmp_path, "next")
    run_cli(
        tmp_path,
        "alignment",
        "--source",
        "human prompt",
        "--understanding",
        "Add export support.",
        "--scope",
        "in: exporter",
        "--acceptance",
        "Exporter has a passing check.",
        "--question",
        "Which file format is required?",
        "--recommended-response",
        "Use CSV because no alternate format was requested.",
        "--risk",
        "low",
        "--decision",
        "proceed",
        "--reason",
        "Question has a default response for automated flow.",
    )

    graph = load_graph(tmp_path)
    assert graph.alignment is not None
    assert graph.alignment.decision == "proceed"
    assert graph.alignment.recommended_responses == ["Use CSV because no alternate format was requested."]


def test_alignment_requires_pause_for_threshold_risk(tmp_path: Path) -> None:
    """
    @brief      Verify configured risk threshold rejects proceed decisions.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Change auth")
    run_cli(tmp_path, "next")

    with pytest.raises(SystemExit, match="risk medium meets threshold medium"):
        run_cli(
            tmp_path,
            "alignment",
            "--source",
            "human prompt",
            "--understanding",
            "Change authentication behavior.",
            "--scope",
            "in: auth flow",
            "--acceptance",
            "Existing auth checks pass.",
            "--risk",
            "medium",
            "--decision",
            "proceed",
            "--reason",
            "Trying to proceed.",
        )


def test_alignment_requires_pause_for_protected_planned_path(tmp_path: Path) -> None:
    """
    @brief      Verify protected planned paths reject proceed decisions.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    (agentic / "workflow.toml").write_text(
        """
[alignment]
risk_threshold = "high"
protected_scope_patterns = ["src/security/**"]
""",
        encoding="utf-8",
    )
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Change auth")
    run_cli(tmp_path, "next")

    with pytest.raises(SystemExit, match="protected scope"):
        run_cli(
            tmp_path,
            "alignment",
            "--source",
            "human prompt",
            "--understanding",
            "Change authentication behavior.",
            "--scope",
            "in: auth flow",
            "--acceptance",
            "Existing auth checks pass.",
            "--planned-path",
            "src/security/auth.py",
            "--risk",
            "low",
            "--decision",
            "proceed",
            "--reason",
            "Trying to proceed.",
        )


def test_alignment_accepts_pause_for_adoption_alignment(tmp_path: Path) -> None:
    """
    @brief      Verify adoption-alignment can record a pause alignment record.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt existing project")
    run_cli(tmp_path, "next")
    run_cli(
        tmp_path,
        "alignment",
        "--source",
        "human prompt",
        "--understanding",
        "Adopt one component.",
        "--scope",
        "in: component map",
        "--acceptance",
        "Component slice is identified.",
        "--question",
        "Which component is first?",
        "--risk",
        "medium",
        "--decision",
        "pause",
        "--reason",
        "Need component selection.",
    )

    graph = load_graph(tmp_path)
    assert graph.stage == "adoption-alignment"
    assert graph.alignment is not None
    assert graph.alignment.decision == "pause"


def test_old_graph_without_alignment_loads(tmp_path: Path) -> None:
    """
    @brief      Verify older graph files without alignment data remain readable.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    graph = Graph.from_dict(
        {
            "run_id": "feature-1",
            "stage": "intake",
            "intent": {
                "id": "I-0001",
                "kind": "feature",
                "statement": "Old graph",
            },
        }
    )

    assert graph.alignment is None


def test_old_graph_with_intake_triage_loads_as_alignment(tmp_path: Path) -> None:
    """
    @brief      Verify older graph intake-triage data migrates to alignment data.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    graph = Graph.from_dict(
        {
            "run_id": "feature-1",
            "stage": "alignment",
            "intent": {
                "id": "I-0001",
                "kind": "feature",
                "statement": "Old graph",
            },
            "intake_triage": {
                "source": "old prompt",
                "understanding": "Old understanding.",
                "scope": ["in: exporter"],
                "assumptions": [],
                "acceptance": ["Exporter works."],
                "open_questions": [],
                "recommended_responses": [],
                "risk": "low",
                "decision": "proceed",
                "reason": "Old run data.",
            },
        }
    )

    assert graph.alignment is not None
    assert graph.alignment.source == "old prompt"


def test_adoption_run_starts_in_adoption_intake(tmp_path: Path) -> None:
    """
    @brief      Verify adoption runs start in adoption intake.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt existing project")

    graph = load_graph(tmp_path)

    assert graph.intent.kind == "adoption"
    assert graph.stage == "adoption-intake"


def test_adoption_next_uses_adoption_stage_sequence(tmp_path: Path) -> None:
    """
    @brief      Verify adoption next routing follows adoption-only stages.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.2.0
    """
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt existing project")

    graph = load_graph(tmp_path)
    assert graph.stage == "adoption-intake"

    for expected_stage in [
        "adoption-alignment",
        "repo-discovery",
        "component-map",
        "component-adoption",
        "baseline-review",
        "adoption-delivery",
        "adoption-delivery",
    ]:
        run_cli(tmp_path, "next")
        graph = load_graph(tmp_path)
        assert graph.stage == expected_stage


def test_adoption_next_skips_alignment_when_disabled(tmp_path: Path) -> None:
    """
    @brief      Verify disabled alignment policy skips the adoption-alignment stage.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    (agentic / "workflow.toml").write_text(
        """
[alignment]
enabled = false
""",
        encoding="utf-8",
    )

    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt existing project")
    run_cli(tmp_path, "next")

    graph = load_graph(tmp_path)
    assert graph.stage == "repo-discovery"


def test_set_stage_accepts_adoption_stage_and_routes_run(tmp_path: Path) -> None:
    """
    @brief      Verify set-stage records decisions for adoption stages.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt existing project")
    run_cli(
        tmp_path,
        "set-stage",
        "repo-discovery",
        "--reason",
        "Human-approved adoption discovery",
    )

    graph = load_graph(tmp_path)

    assert graph.stage == "repo-discovery"
    assert graph.decisions[-1].question == "Workflow stage route"
    assert graph.decisions[-1].chosen == "repo-discovery"
    assert graph.decisions[-1].rationale == "Human-approved adoption discovery"


def test_repo_wide_access_mode_requires_reason(tmp_path: Path) -> None:
    """
    @brief      Handle test repo wide access mode requires reason workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    with pytest.raises(SystemExit):
        run_cli(
            tmp_path,
            "start",
            "--kind",
            "change",
            "--statement",
            "Maintain repo docs",
            "--access-mode",
            "repo-wide",
        )


def test_repo_wide_access_mode_records_decision(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief      Handle test repo wide access mode records decision workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "change", "--statement", "Maintain repo docs")
    run_cli(
        tmp_path,
        "set-access-mode",
        "repo-wide",
        "--reason",
        "Human-approved broad maintenance",
    )
    capsys.readouterr()

    graph = load_graph(tmp_path)

    assert graph.access_mode == "repo-wide"
    assert graph.decisions[-1].chosen == "repo-wide"
    assert graph.decisions[-1].rationale == "Human-approved broad maintenance"


def test_set_stage_records_decision_and_routes_run(tmp_path: Path) -> None:
    """
    @brief      Handle test set stage records decision and routes run workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(tmp_path, "set-stage", "check", "--reason", "Human-approved test revision")

    graph = load_graph(tmp_path)

    assert graph.stage == "check"
    assert graph.decisions[-1].question == "Workflow stage route"
    assert graph.decisions[-1].chosen == "check"
    assert graph.decisions[-1].rationale == "Human-approved test revision"


def test_unsuperseded_late_failure_blocks_no_regression(tmp_path: Path) -> None:
    """
    @brief      Handle test unsuperseded late failure blocks no regression workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(tmp_path, "set-stage", "implementation", "--reason", "Testing late failure")
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "fail",
        "--summary",
        "Focused regression failed",
    )

    graph = load_graph(tmp_path)
    failures = {item.id for item in blocking_failures(evaluate(tmp_path, graph))}

    assert "INV-4" in failures


def test_superseded_late_failure_no_longer_blocks_no_regression(tmp_path: Path) -> None:
    """
    @brief      Handle test superseded late failure no longer blocks no regression workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(tmp_path, "set-stage", "implementation", "--reason", "Testing supersede flow")
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "fail",
        "--failure-kind",
        "environment",
        "--summary",
        "Gate failed because the command used a bad interpreter path",
    )
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "pass",
        "--summary",
        "Same gate passed with the configured interpreter path",
    )
    run_cli(
        tmp_path,
        "supersede-evidence",
        "--id",
        "E-0001",
        "--by",
        "E-0002",
        "--reason",
        "Passing rerun proves the old failure was environmental",
    )

    graph = load_graph(tmp_path)
    failures = blocking_failures(evaluate(tmp_path, graph))

    assert failures == []
    assert graph.evidence[0].status == "superseded"
    assert graph.evidence[0].superseded_by == "E-0002"
