#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_stage_context_budget.py
@brief Regression tests for the bounded fresh-session context contract.
@details Verifies requirement AEGIS-WP2-CTX: read-only context resolution uses
         only payload-owned bootstrap files and remains independent of evidence
         history.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.models import ALL_STAGES, Evidence
from aegis.stage_schema import STAGE_REFERENCE_PATHS
from aegis.store import graph_path, load_graph, save_graph

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_LIMIT_BYTES = 4 * 1024
BOOTSTRAP_LIMIT_BYTES = 30 * 1024


# LOCAL HELPERS


def _invoke(capsys: pytest.CaptureFixture[str], arguments: list[str]) -> dict:
    """@brief Invoke the CLI and parse its JSON response."""
    main([*arguments, "--json"])
    return json.loads(capsys.readouterr().out)


def _invoke_output(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> tuple[dict, bytes]:
    """@brief Invoke a public JSON command and retain its emitted UTF-8 bytes."""
    main([*arguments, "--json"])
    output = capsys.readouterr().out
    return json.loads(output), output.encode("utf-8")


def _replace(path: Path, replacements: dict[str, str]) -> None:
    """@brief Apply exact form edits through the file-first CLI workflow."""
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert text.count(old) == 1, (path, old)
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")


def _enable_latest_retention(root: Path) -> None:
    """@brief Keep closed primary forms available for a realistic handoff."""
    path = root / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    assert text.count('stage_form_retention = "discard"') == 1
    path.write_text(
        text.replace('stage_form_retention = "discard"', 'stage_form_retention = "latest"'),
        encoding="utf-8",
        newline="\n",
    )


def _apply_close(capsys: pytest.CaptureFixture[str]) -> dict:
    """@brief Apply and human-close the current form through the public CLI."""
    _invoke(capsys, ["stage", "apply"])
    return _invoke(capsys, ["stage", "close"])


def _start_and_close_intake(
    root: Path,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    *,
    quick: bool = False,
) -> tuple[str, dict]:
    """@brief Create a real full, quick, or adoption handoff from intake."""
    started = _invoke(capsys, ["run", "start", kind, *(["--quick"] if quick else [])])
    edits = {
        'statement = ""': 'statement = "Record a bounded context handoff"',
        'summary = ""': 'summary = "Intake approved"',
    }
    if kind == "adoption":
        edits['adoption_slice = ""'] = 'adoption_slice = "billing"'
    _replace(root / str(started["artifact"]), edits)
    return str(started["run_id"]), _apply_close(capsys)


def _advance_adoption_to_delivery(root: Path, capsys: pytest.CaptureFixture[str]) -> str:
    """@brief Drive actual adoption forms to the prepared adoption-delivery stage."""
    run_id, closed = _start_and_close_intake(root, capsys, "adoption")
    assert closed["stage"] == "adoption-alignment"
    stage_edits = (
        {
            'understanding = ""': 'understanding = "Document billing without behavior changes"',
            "in_scope = []": 'in_scope = ["src/billing"]',
            "acceptance_criteria = []": 'acceptance_criteria = ["billing baseline documented"]',
            'summary = ""': 'summary = "Adoption alignment approved"',
        },
        {
            "candidate_components = []": 'candidate_components = ["billing"]',
            'summary = ""': 'summary = "Repository discovery complete"',
        },
        {
            "components = []": 'components = ["billing"]',
            "approved_slice = []": 'approved_slice = ["billing"]',
            'approval_decision = "pending"': 'approval_decision = "approved"',
            'summary = ""': 'summary = "Component map approved"',
        },
        {
            "adopted_components = []": 'adopted_components = ["billing"]',
            "changed_paths = []": 'changed_paths = [".agentic/knowledge/components/billing.md"]',
            "documentation = []": 'documentation = [".agentic/knowledge/components/billing.md"]',
            'summary = ""': 'summary = "Billing component adopted"',
        },
        {
            "reviewed_components = []": 'reviewed_components = ["billing"]',
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "Baseline review approved"',
        },
    )
    for edits in stage_edits:
        graph = load_graph(root, run_id)
        artifact = graph.stage_records[graph.stage].artifact
        _replace(root / artifact, edits)
        _apply_close(capsys)
    assert load_graph(root, run_id).stage == "adoption-delivery"
    return run_id


def _bootstrap_bytes(
    payload_root: Path,
    run_root: Path,
    context: dict,
    context_output: bytes,
) -> tuple[int, dict[str, int]]:
    """
    @brief Measure the exact UTF-8 bootstrap components named by context.
    @param[in] payload_root Installed payload root.
    @param[in] run_root Repository root holding generated run forms.
    @param[in] context `run context --json` response.
    @return Total bytes and an individual component breakdown.
    """
    paths = [*context["required_reads"]]
    components = {}
    for path in paths:
        source_root = run_root if path.startswith(".agentic/runs/") else payload_root
        components[path] = len((source_root / path).read_bytes())
    components["run-context.json"] = len(context_output)
    return sum(components.values()), components


# TESTS


def test_context_reference_mapping_covers_every_stage() -> None:
    """@brief Requirement AEGIS-WP2-CTX maps every executable stage once."""
    assert tuple(STAGE_REFERENCE_PATHS) == tuple(ALL_STAGES)


@pytest.mark.parametrize(
    ("kind", "quick", "expected_skill", "expected_reference"),
    (
        (
            "feature",
            False,
            ".agentic/skills/agentic-development/SKILL.md",
            ".agentic/skills/agentic-development/reference/intake.md",
        ),
        (
            "fix",
            True,
            ".agentic/skills/agentic-development/SKILL.md",
            ".agentic/skills/agentic-development/reference/intake.md",
        ),
        (
            "adoption",
            False,
            ".agentic/skills/agentic-adoption/SKILL.md",
            ".agentic/skills/agentic-adoption/reference/adoption-intake.md",
        ),
    ),
)
def test_run_context_is_bounded_for_full_quick_and_adoption_starts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    quick: bool,
    expected_skill: str,
    expected_reference: str,
) -> None:
    """@brief A new run exposes only the selected stage's bootstrap surface."""
    monkeypatch.chdir(tmp_path)
    start = _invoke(capsys, ["run", "start", kind, *( ["--quick"] if quick else [])])
    context = _invoke(capsys, ["run", "context"])

    assert context["status"] == "ok"
    assert context["next"] == "aegis stage apply"
    assert context["context_schema_version"] == 1
    assert context["run_id"] == start["run_id"]
    assert context["kind"] == kind
    assert context["profile"] == ("quick" if quick else "full")
    assert context["skill"] == expected_skill
    assert context["reference"] == expected_reference
    assert context["artifact"] in context["required_reads"]
    assert context["unavailable_current_artifact"] is None
    assert context["previous_stage_artifacts"] == []
    assert context["unavailable_previous_stage_artifacts"] == []
    assert all("graph.json" not in path and "journal.jsonl" not in path for path in context["required_reads"])
    assert context["next_commands"] == [
        "aegis stage prepare",
        "aegis stage apply",
        "aegis stage close",
    ]
    assert context["human_gate"] == "stage close"
    assert len(json.dumps(context, ensure_ascii=False).encode("utf-8")) <= CONTEXT_LIMIT_BYTES


@pytest.mark.parametrize(
    ("kind", "quick", "expected_stage"),
    (
        ("feature", False, "alignment"),
        ("fix", True, "implementation"),
        ("adoption", False, "adoption-delivery"),
    ),
)
def test_public_lifecycle_context_stays_bounded_with_evidence_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    quick: bool,
    expected_stage: str,
) -> None:
    """@brief WP2 bounds real full, quick, and adoption handoff context output."""
    monkeypatch.chdir(tmp_path)
    _enable_latest_retention(tmp_path)
    if kind == "adoption":
        run_id = _advance_adoption_to_delivery(tmp_path, capsys)
    else:
        run_id, closed = _start_and_close_intake(tmp_path, capsys, kind, quick=quick)
        assert closed["stage"] == expected_stage

    before, before_output = _invoke_output(capsys, ["run", "context"])
    graph = load_graph(tmp_path, run_id)
    graph.evidence.extend(
        Evidence(id=f"EV-{index:04d}", kind="note", result="info", summary="history")
        for index in range(1_000)
    )
    save_graph(tmp_path, graph)
    graph_before_context = graph_path(tmp_path, run_id).read_bytes()
    after, after_output = _invoke_output(capsys, ["run", "context"])

    total, components = _bootstrap_bytes(
        PACKAGE_ROOT / "template",
        tmp_path,
        after,
        after_output,
    )

    assert after["stage"] == expected_stage
    assert after["previous_stage_artifacts"]
    assert before == after
    assert before_output == after_output
    assert graph_path(tmp_path, run_id).read_bytes() == graph_before_context
    assert len(after_output) <= CONTEXT_LIMIT_BYTES, components
    assert total <= BOOTSTRAP_LIMIT_BYTES, components
    assert all("graph.json" not in path and "journal.jsonl" not in path for path in after["required_reads"])


def test_discarded_current_form_uses_non_mutating_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief An applied discarded form is never advertised as a readable input."""
    monkeypatch.chdir(tmp_path)
    run_id = str(_invoke(capsys, ["run", "start", "feature"])["run_id"])
    graph = load_graph(tmp_path, run_id)
    form = tmp_path / graph.stage_records["intake"].artifact
    _replace(form, {
        'statement = ""': 'statement = "Keep applied state safe"',
        'summary = ""': 'summary = "Applied intake"',
    })
    _invoke(capsys, ["stage", "apply"])
    graph_before = graph_path(tmp_path, run_id).read_bytes()
    context, _ = _invoke_output(capsys, ["run", "context"])

    assert context["artifact"] == "none"
    assert context["unavailable_current_artifact"] == {
        "stage": "intake",
        "reason": "the applied stage form is unavailable under its captured retention policy",
        "recovery_command": "aegis stage show",
    }
    assert context["next_commands"] == ["aegis stage show"]
    assert all("/intake/intake.toml" not in path for path in context["required_reads"])
    assert graph_path(tmp_path, run_id).read_bytes() == graph_before


def test_missing_prepared_form_stage_show_reports_state_without_recreating_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief AEGIS-WP8-PILOT preserves prepared-state recovery through stage show."""
    monkeypatch.chdir(tmp_path)
    started = _invoke(capsys, ["run", "start", "change"])
    run_id = str(started["run_id"])
    graph = load_graph(tmp_path, run_id)
    artifact = tmp_path / graph.stage_records["intake"].artifact
    artifact.unlink()
    graph_before = graph_path(tmp_path, run_id).read_bytes()

    context = _invoke(capsys, ["run", "context"])
    shown = _invoke(capsys, ["stage", "show"])

    assert context["unavailable_current_artifact"] == {
        "stage": "intake",
        "reason": "the current prepared form is unavailable",
        "recovery_command": "aegis stage show",
    }
    assert shown["stage"] == "intake"
    assert shown["artifact"] == graph.stage_records["intake"].artifact
    assert shown["state"] == "prepared"
    assert shown["revision"] == 1
    assert shown["imported_revision"] == 0
    assert shown["files"] == []
    assert not artifact.exists()
    assert graph_path(tmp_path, run_id).read_bytes() == graph_before


def test_adoption_delivery_context_uses_the_adoption_router(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Public CLI context keeps adoption-delivery out of standard delivery."""
    monkeypatch.chdir(tmp_path)
    _enable_latest_retention(tmp_path)
    _advance_adoption_to_delivery(tmp_path, capsys)

    context = _invoke(capsys, ["run", "context"])

    assert context["stage"] == "adoption-delivery"
    assert context["skill"] == ".agentic/skills/agentic-adoption/SKILL.md"
    assert context["reference"] == ".agentic/skills/agentic-adoption/reference/adoption-delivery.md"


# END OF FILE
