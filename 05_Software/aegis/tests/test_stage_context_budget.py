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
from aegis.models import ALL_STAGES, Evidence, StageRecord
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


def _bootstrap_bytes(
    payload_root: Path,
    run_root: Path,
    context: dict,
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
    components["run-context.json"] = len(
        json.dumps(context, indent=2, ensure_ascii=False).encode("utf-8")
    )
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

    assert context["context_schema_version"] == 1
    assert context["run_id"] == start["run_id"]
    assert context["kind"] == kind
    assert context["profile"] == ("quick" if quick else "full")
    assert context["skill"] == expected_skill
    assert context["reference"] == expected_reference
    assert context["artifact"] in context["required_reads"]
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


def test_run_context_does_not_grow_with_evidence_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief A thousand evidence rows cannot enlarge the context response."""
    monkeypatch.chdir(tmp_path)
    run_id = str(_invoke(capsys, ["run", "start", "feature"])["run_id"])
    graph_before = graph_path(tmp_path, run_id).read_bytes()
    before = _invoke(capsys, ["run", "context"])
    assert graph_path(tmp_path, run_id).read_bytes() == graph_before

    graph = load_graph(tmp_path, run_id)
    graph.evidence.extend(
        Evidence(id=f"EV-{index:04d}", kind="note", result="info", summary="history")
        for index in range(1_000)
    )
    save_graph(tmp_path, graph)

    after = _invoke(capsys, ["run", "context"])

    assert after == before


def test_run_context_names_or_explains_the_immediately_previous_form(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Retention determines the sole predecessor form a session may read."""
    monkeypatch.chdir(tmp_path)
    run_id = str(_invoke(capsys, ["run", "start", "feature"])["run_id"])
    graph = load_graph(tmp_path, run_id)
    graph.stage = "alignment"
    graph.stage_records["intake"].status = "closed"
    graph.stage_records["intake"].retention = "latest"
    graph.stage_records["alignment"] = StageRecord(
        stage="alignment",
        revision=1,
        status="prepared",
        retention="latest",
        check_execution="external",
    )
    current = tmp_path / ".agentic" / "runs" / run_id / "stages" / "alignment" / "alignment.toml"
    current.parent.mkdir(parents=True)
    current.write_text("schema_version = 3\n", encoding="utf-8")
    save_graph(tmp_path, graph)

    retained = _invoke(capsys, ["run", "context"])

    assert retained["previous_stage_artifacts"] == [
        f".agentic/runs/{run_id}/stages/intake/intake.toml"
    ]
    assert retained["unavailable_previous_stage_artifacts"] == []

    graph = load_graph(tmp_path, run_id)
    graph.stage_records["intake"].retention = "discard"
    save_graph(tmp_path, graph)
    discarded = _invoke(capsys, ["run", "context"])

    assert discarded["previous_stage_artifacts"] == []
    assert discarded["unavailable_previous_stage_artifacts"] == [{
        "stage": "intake",
        "reason": "the captured retention policy discarded the form",
        "recovery_command": "aegis stage show",
    }]


@pytest.mark.parametrize(
    ("kind", "quick"),
    (("feature", False), ("fix", True), ("adoption", False)),
)
def test_template_bootstrap_pack_stays_within_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    quick: bool,
) -> None:
    """@brief The installable payload supplies every measured bootstrap file."""
    monkeypatch.chdir(tmp_path)
    _invoke(capsys, ["run", "start", kind, *( ["--quick"] if quick else [])])
    context = _invoke(capsys, ["run", "context"])

    total, components = _bootstrap_bytes(PACKAGE_ROOT / "template", tmp_path, context)

    assert len(json.dumps(context, ensure_ascii=False).encode("utf-8")) <= CONTEXT_LIMIT_BYTES, components
    assert total <= BOOTSTRAP_LIMIT_BYTES, components


def test_template_bootstrap_pack_includes_retained_previous_form(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief The pack budget includes both required stage forms after a handoff."""
    monkeypatch.chdir(tmp_path)
    run_id = str(_invoke(capsys, ["run", "start", "feature"])["run_id"])
    graph = load_graph(tmp_path, run_id)
    graph.stage = "alignment"
    graph.stage_records["intake"].status = "closed"
    graph.stage_records["intake"].retention = "latest"
    graph.stage_records["alignment"] = StageRecord(
        stage="alignment",
        revision=1,
        status="prepared",
        retention="latest",
        check_execution="external",
    )
    current = tmp_path / ".agentic" / "runs" / run_id / "stages" / "alignment" / "alignment.toml"
    current.parent.mkdir(parents=True)
    current.write_text("schema_version = 3\n", encoding="utf-8")
    save_graph(tmp_path, graph)

    context = _invoke(capsys, ["run", "context"])
    total, components = _bootstrap_bytes(PACKAGE_ROOT / "template", tmp_path, context)

    assert context["previous_stage_artifacts"]
    assert total <= BOOTSTRAP_LIMIT_BYTES, components


# END OF FILE
