#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_cli_v2.py
@brief Contract tests for the AEGIS 2 stage-oriented CLI.
@details Covers the hard-break parser, stable response envelope, strict
         schema-3 graph, captured interface policy, form reconstruction, and
         prepare/apply/close lifecycle.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 1.2.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

import pytest

from aegis.cli import TOP_LEVEL_COMMANDS, main
from aegis.config import load_config
from aegis.models import Check, Graph, Intent, STAGES, StageRecord
from aegis.stage_forms import prepare_stage
from aegis.store import load_graph, save_graph

# TESTS


def test_hard_break_parser_exposes_only_grouped_interface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Verify the new inventory and explicit rejection of a removed command."""
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    output = capsys.readouterr().out
    assert tuple(TOP_LEVEL_COMMANDS) == (
        "run",
        "stage",
        "requirement",
        "check",
        "evidence",
        "waive",
        "verify",
        "delivery",
        "adoption",
        "config",
    )
    for command in TOP_LEVEL_COMMANDS:
        assert command in output
    with pytest.raises(SystemExit) as removed_exit:
        main(["next"])
    assert removed_exit.value.code == 2
    for mutation in ("create", "update", "activate", "retire"):
        with pytest.raises(SystemExit) as mutation_exit:
            main(["requirement", mutation])
        assert mutation_exit.value.code == 2


def test_start_intake_apply_close_prepares_alignment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief Exercise a schema-3 stage lifecycle using default discard retention.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "feature", "--json"])
    started = json.loads(capsys.readouterr().out)
    assert tuple(started)[:4] == ("status", "stage", "artifact", "next")
    assert started["stage"] == "intake"
    graph = load_graph(tmp_path, started["run_id"])
    assert graph.schema_version == 3
    form = tmp_path / started["artifact"]
    text = form.read_text(encoding="utf-8")
    text = text.replace('statement = ""', 'statement = "Add grouped workflow"')
    text = text.replace('summary = ""', 'summary = "Intent approved"')
    form.write_text(text, encoding="utf-8")
    replace_workflow_toml(
        'stage_form_retention = "discard"',
        'stage_form_retention = "latest"',
    )

    main(["stage", "apply", "--json"])
    applied = json.loads(capsys.readouterr().out)
    assert applied["next"] == "aegis stage close"
    assert not form.exists()

    main(["stage", "close", "--json"])
    closed = json.loads(capsys.readouterr().out)
    assert closed["stage"] == "alignment"
    assert closed["artifact"].endswith("/alignment/alignment.toml")
    graph = load_graph(tmp_path, started["run_id"])
    assert graph.stage_records["intake"].retention == "discard"
    assert graph.stage_records["alignment"].retention == "latest"
    assert STAGES == [
        "intake",
        "alignment",
        "requirement",
        "design",
        "check",
        "implementation",
        "validation",
        "delivery",
    ]


def test_schema_two_graph_is_rejected() -> None:
    """@brief Verify the graph reader has no schema-2 fallback."""
    with pytest.raises(ValueError, match="requires schema_version 3"):
        Graph.from_dict({"schema_version": 2})


def test_nested_graph_schema_errors_are_reported_as_value_errors() -> None:
    """
    @brief Wrap unknown nested record keys in the graph schema contract.
    @version 0.1.0
    """
    graph = Graph(
        run_id="fix-20260730T120000Z-1234abcd",
        stage="intake",
        intent=Intent(id="I-1", kind="fix", statement="Validate graph schema"),
    )
    data = graph.to_dict()
    data["intent"]["unexpected"] = "value"

    with pytest.raises(ValueError, match="graph record does not match schema 3"):
        Graph.from_dict(data)


def test_discarded_collections_reconstruct_authoritative_ids(
    tmp_path: Path,
) -> None:
    """
    @brief Rehydrate requirement and check collections without new identities.
    @details Requirement/check forms are transient, but their imported IDs and
             values remain authoritative after discard and routing.
    """
    requirement_id = "REQ-FUNC-8b11c230-cab4-4e33-b357-7f95bf8c5571"
    check_id = "CHK-52272d95-c6e2-4f4f-8508-258fd57feebe"
    graph = Graph(
        run_id="fix-20260729T120000Z-1234abcd",
        stage="requirement",
        intent=Intent(id="I-1", kind="fix", statement="Repair state"),
        stage_records={
            "requirement": StageRecord(
                stage="requirement",
                revision=1,
                status="applied",
                retention="discard",
                check_execution="external",
                payload={
                    "requirements": [
                        {
                            "schema_version": 1,
                            "id": requirement_id,
                            "category": "functional",
                            "status": "Planned",
                            "priority": "Must",
                            "requirement": "State is cleared.",
                            "rationale": "Avoid stale results.",
                            "verification": "Linked deterministic check.",
                            "spec_ref": (
                                ".agentic/runs/fix-20260729T120000Z-1234abcd/"
                                f"requirements/{requirement_id}.md"
                            ),
                            "affected_paths": ["src/state.py"],
                            "linked_tests": ["tests/test_state.py"],
                            "created_on": "2026-07-29T12:00:00Z",
                            "last_updated": "2026-07-29T12:00:00Z",
                        }
                    ],
                    "control": {
                        "requested_access_mode": "",
                        "access_rationale": "",
                        "route_to": "",
                        "route_rationale": "",
                        "summary": "Imported requirements",
                        "unresolved_questions": [],
                    },
                },
            )
        },
    )
    save_graph(tmp_path, graph)
    requirement_form = prepare_stage(tmp_path, graph, load_config(tmp_path))
    assert _toml_value(requirement_form, "id") == requirement_id
    assert 'requirement = "State is cleared."' in requirement_form.read_text(
        encoding="utf-8"
    )

    graph.stage = "check"
    graph.checks = [
        Check(
            id=check_id,
            level="test",
            cites_spec=[],
            cites_requirement=[requirement_id],
            command="python tests/test_state.py",
            concerns=["stale-state cleanup"],
        )
    ]
    graph.stage_records["check"] = StageRecord(
        stage="check",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="external",
    )
    check_form = prepare_stage(tmp_path, graph, load_config(tmp_path))
    assert _toml_value(check_form, "id") == check_id
    assert f'cites_requirement = ["{requirement_id}"]' in check_form.read_text(
        encoding="utf-8"
    )


def test_complete_fix_flow_uses_forms_red_green_design_and_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Exercise all eight standard stages and automatic activation.
    @details Covers requirement/check IDs, design approval, external red/green
             evidence, discard retention, and delivery closure without Git.
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "fix", "--json"])
    started = json.loads(capsys.readouterr().out)
    run_id = started["run_id"]

    _replace(
        tmp_path / started["artifact"],
        {
            'statement = ""': 'statement = "Fix stale state"',
            'summary = ""': 'summary = "Intent approved"',
        },
    )
    _apply_close(capsys)

    alignment = _artifact(tmp_path, run_id)
    _replace(
        alignment,
        {
            'understanding = ""': 'understanding = "Remove stale observable state"',
            "in_scope = []": 'in_scope = ["src/state.py"]',
            "acceptance_criteria = []": 'acceptance_criteria = ["stale state is cleared"]',
            'summary = ""': 'summary = "Alignment approved"',
        },
    )
    _apply_close(capsys)

    requirement_dir = _stage_dir(tmp_path, run_id, "requirement")
    requirement_form = next(requirement_dir.glob("requirement-*.toml"))
    requirement_id = _toml_value(requirement_form, "id")
    _replace(
        requirement_form,
        {
            'requirement = ""': 'requirement = "Clearing succeeds without stale state."',
            'rationale = ""': 'rationale = "Prevents an observable regression."',
            'verification = ""': 'verification = "Manual: inspect linked check evidence"',
            "affected_paths = []": 'affected_paths = ["src/state.py"]',
        },
    )
    _replace(
        requirement_dir / "stage.toml",
        {'summary = ""': 'summary = "Requirements approved"'},
    )
    _apply_close(capsys)

    design = _artifact(tmp_path, run_id)
    design_form = _stage_dir(tmp_path, run_id, "design") / "design.toml"
    _replace(
        design_form,
        {
            "cited_requirement_ids = []": f'cited_requirement_ids = ["{requirement_id}"]',
            'selected_option = ""': 'selected_option = "Clear state transactionally"',
            'summary = ""': 'summary = "Design approved"',
        },
    )
    design.write_text(
        design.read_text(encoding="utf-8")
        + "\nSelected option: clear state transactionally.\n",
        encoding="utf-8",
    )
    _apply_close(capsys)

    check_dir = _stage_dir(tmp_path, run_id, "check")
    check_form = next(check_dir.glob("check-*.toml"))
    check_id = _toml_value(check_form, "id")
    _replace(
        check_form,
        {
            "cites_requirement = []": f'cites_requirement = ["{requirement_id}"]',
            'command = ""': 'command = "python tests/check_state.py"',
            "concerns = []": 'concerns = ["stale-state cleanup", "idempotency"]',
        },
    )
    _replace(
        check_dir / "stage.toml",
        {'summary = ""': 'summary = "Checks approved"'},
    )
    main(["stage", "apply", "--json"])
    capsys.readouterr()
    main(["check", "prepare", "--json"])
    evidence_path = tmp_path / json.loads(capsys.readouterr().out)["artifact"]
    _replace(
        evidence_path,
        {
            'result = ""': 'result = "fail"',
            "exit_status = 0": "exit_status = 1",
            'summary = ""': 'summary = "Reproduces stale state"',
        },
    )
    main(["check", "record", "--json"])
    capsys.readouterr()
    main(["stage", "close", "--json"])
    capsys.readouterr()

    implementation = _artifact(tmp_path, run_id)
    _replace(
        implementation,
        {
            "changed_paths = []": 'changed_paths = ["src/state.py"]',
            'summary = ""': 'summary = "State cleanup implemented"',
        },
    )
    main(["stage", "apply", "--json"])
    capsys.readouterr()
    main(["check", "prepare", "--json"])
    green_path = tmp_path / json.loads(capsys.readouterr().out)["artifact"]
    _replace(
        green_path,
        {
            'result = ""': 'result = "pass"',
            'summary = ""': 'summary = "Observable contract passes"',
        },
    )
    main(["check", "record", "--json"])
    capsys.readouterr()
    main(["stage", "close", "--json"])
    capsys.readouterr()

    validation = _artifact(tmp_path, run_id)
    _replace(
        validation,
        {
            "deterministic_verification = []": f'deterministic_verification = ["{check_id}"]',
            'diff_review = "pending"': 'diff_review = "pass"',
            'documentation_review = "pending"': 'documentation_review = "not-applicable"',
            'style_review = "pending"': 'style_review = "pass"',
            'summary = ""': 'summary = "Validation approved"',
        },
    )
    _apply_close(capsys)

    delivery = _artifact(tmp_path, run_id)
    _replace(
        delivery,
        {
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "Ready for human handoff"',
        },
    )
    _apply_close(capsys)
    graph = load_graph(tmp_path, run_id)
    assert graph.complete
    requirement = next((tmp_path / ".agentic" / "requirements").rglob("*.toml"))
    assert 'status = "Active"' in requirement.read_text(encoding="utf-8")


def test_complete_adoption_flow_uses_stage_specific_forms(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Exercise the unchanged seven-stage adoption sequence via forms."""
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "adoption", "--json"])
    started = json.loads(capsys.readouterr().out)
    run_id = started["run_id"]
    assert started["stage"] == "adoption-intake"

    _replace(
        tmp_path / started["artifact"],
        {
            'statement = ""': 'statement = "Adopt the billing component"',
            'adoption_slice = ""': 'adoption_slice = "billing"',
            'summary = ""': 'summary = "Adoption intake approved"',
        },
    )
    _apply_close(capsys)
    _replace(
        _artifact(tmp_path, run_id),
        {
            'understanding = ""': 'understanding = "Map billing without behavior changes"',
            "in_scope = []": 'in_scope = ["src/billing"]',
            "acceptance_criteria = []": 'acceptance_criteria = ["billing baseline documented"]',
            'summary = ""': 'summary = "Adoption alignment approved"',
        },
    )
    _apply_close(capsys)
    _replace(
        _artifact(tmp_path, run_id),
        {
            "candidate_components = []": 'candidate_components = ["billing"]',
            'summary = ""': 'summary = "Repository discovery complete"',
        },
    )
    _apply_close(capsys)
    _replace(
        _artifact(tmp_path, run_id),
        {
            "components = []": 'components = ["billing"]',
            "approved_slice = []": 'approved_slice = ["billing"]',
            'approval_decision = "pending"': 'approval_decision = "approved"',
            'summary = ""': 'summary = "Component map approved"',
        },
    )
    _apply_close(capsys)
    _replace(
        _artifact(tmp_path, run_id),
        {
            "adopted_components = []": 'adopted_components = ["billing"]',
            "changed_paths = []": (
                'changed_paths = [".agentic/knowledge/components/billing.md"]'
            ),
            "documentation = []": (
                'documentation = [".agentic/knowledge/components/billing.md"]'
            ),
            'summary = ""': 'summary = "Billing component adopted"',
        },
    )
    _apply_close(capsys)
    _replace(
        _artifact(tmp_path, run_id),
        {
            "reviewed_components = []": 'reviewed_components = ["billing"]',
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "Baseline review approved"',
        },
    )
    _apply_close(capsys)
    _replace(
        _artifact(tmp_path, run_id),
        {
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "Adoption handoff approved"',
        },
    )
    _apply_close(capsys)
    graph = load_graph(tmp_path, run_id)
    assert graph.complete
    expected_stages = {
        "adoption-intake",
        "adoption-alignment",
        "repo-discovery",
        "component-map",
        "component-adoption",
        "baseline-review",
        "adoption-delivery",
    }
    assert set(graph.stage_records) == expected_stages
    assert all(record.status == "closed" for record in graph.stage_records.values())


def _apply_close(capsys: pytest.CaptureFixture[str]) -> None:
    """@brief Apply and close the current prepared stage."""
    main(["stage", "apply", "--json"])
    capsys.readouterr()
    main(["stage", "close", "--json"])
    capsys.readouterr()


def _stage_dir(tmp_path: Path, run_id: str, stage: str) -> Path:
    """@brief Return one run-local stage directory."""
    return tmp_path / ".agentic" / "runs" / run_id / "stages" / stage


def _artifact(tmp_path: Path, run_id: str) -> Path:
    """@brief Resolve the authoritative active artifact from the graph."""
    graph = load_graph(tmp_path, run_id)
    if graph.stage == "design":
        return tmp_path / ".agentic" / "runs" / run_id / "design.md"
    record = graph.stage_records[graph.stage]
    return tmp_path / record.artifact


def _replace(path: Path, replacements: dict[str, str]) -> None:
    """@brief Apply exact test-form substitutions."""
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert text.count(old) == 1, (path, old)
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def _toml_value(path: Path, key: str) -> str:
    """@brief Read one simple quoted TOML value used by generated forms."""
    prefix = f"{key} = "
    line = next(item for item in path.read_text(encoding="utf-8").splitlines() if item.startswith(prefix))
    return json.loads(line[len(prefix) :])


# END OF FILE
