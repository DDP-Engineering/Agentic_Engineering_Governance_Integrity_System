#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_quick_runs.py
@brief Contract tests for proportional AEGIS quick runs.
@details Covers declarative lifecycle selection, schema-3 compatibility,
         typed profile validation, honest bypass reporting, the complete
         four-stage workflow, and the optional changed-path advisory.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import aegis.store as store_module
from aegis.cli import main
from aegis.config import load_config
from aegis.models import (
    ADOPTION_STAGES,
    QUICK_STAGES,
    STAGES,
    Graph,
    Intent,
    StageRecord,
)
from aegis.stage_schema import RUN_STAGE_SCHEMAS, StageOperationError, run_stage_spec
from aegis.stage_forms import close_stage
from aegis.store import init_graph, load_graph, save_graph

# CONSTANTS

QUICK_BYPASSED_STAGES = ["alignment", "requirement", "design", "check"]
NOT_APPLICABLE_INVARIANTS = ("INV-1", "INV-2", "INV-3", "INV-8", "INV-10")

# LOCAL HELPERS


def _invoke_json(
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> dict[str, object]:
    """
    @brief Invoke one successful CLI command and parse its JSON response.
    @param[in] capsys Pytest capture fixture.
    @param[in] arguments Grouped command arguments without the global JSON flag.
    @return Parsed stable response envelope.
    """
    main([*arguments, "--json"])
    return json.loads(capsys.readouterr().out)


def _replace(path: Path, replacements: dict[str, str]) -> None:
    """
    @brief Apply exact substitutions to one generated workflow form.
    @param[in] path Generated form path.
    @param[in] replacements Expected old fragments and their replacements.
    @return None.
    """
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert text.count(old) == 1, (path, old)
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")


def _journal(repo_root: Path, run_id: str) -> list[dict[str, object]]:
    """
    @brief Read one durable run journal as JSON Lines.
    @param[in] repo_root Temporary repository root.
    @param[in] run_id Run whose events are inspected.
    @return Parsed journal entries in append order.
    """
    path = repo_root / ".agentic" / "runs" / run_id / "journal.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _complete_quick_intake(
    repo_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> tuple[str, dict[str, object]]:
    """
    @brief Start a quick fix and close its human-approved intake stage.
    @param[in] repo_root Temporary repository root.
    @param[in] capsys Pytest capture fixture.
    @return Run ID and intake-close response positioned at implementation.
    """
    started = _invoke_json(capsys, ["run", "start", "fix", "--quick"])
    run_id = str(started["run_id"])
    intake = repo_root / str(started["artifact"])
    _replace(
        intake,
        {
            'statement = ""': 'statement = "Repair a bounded observable defect"',
            'summary = ""': 'summary = "Quick intake approved"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    closed = _invoke_json(capsys, ["stage", "close"])
    assert closed["stage"] == "implementation"
    assert closed["next"] == "aegis evidence prepare add"
    return run_id, closed


def _record_manual_evidence(
    repo_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> str:
    """
    @brief Record real manual implementation evidence through its form contract.
    @param[in] repo_root Temporary repository root.
    @param[in] capsys Pytest capture fixture.
    @return CLI-minted evidence ID.
    """
    prepared = _invoke_json(capsys, ["evidence", "prepare", "add"])
    form = repo_root / str(prepared["artifact"])
    _replace(
        form,
        {'summary = ""': 'summary = "Inspected the bounded state repair"'},
    )
    applied = _invoke_json(capsys, ["evidence", "apply"])
    result = applied["result"]
    assert isinstance(result, dict)
    assert applied["next"] == "aegis stage apply"
    return str(result["evidence_id"])


def _configure_quick_path_policy(
    repo_root: Path,
    mode: str,
    max_paths: int,
) -> None:
    """
    @brief Append one explicit optional quick changed-path policy table.
    @param[in] repo_root Temporary repository root.
    @param[in] mode Disabled or advise policy mode.
    @param[in] max_paths Positive path-count threshold.
    @return None.
    """
    path = repo_root / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    text += (
        "\n[quick.changed_paths]\n"
        f'mode = "{mode}"\n'
        f"max_paths = {max_paths}\n"
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def _initialize_git_repository(repo_root: Path) -> None:
    """
    @brief Create a committed baseline for real working-tree verification.
    @param[in] repo_root Temporary repository root.
    @return None.
    """
    source = repo_root / "src" / "state.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("STATE = 'stale'\n", encoding="utf-8", newline="\n")
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main"],
        cwd=repo_root,
        check=True,
    )
    # Persisted, not passed per-command: the CLI reads `git config` to attribute
    # approvals, so the identity has to be readable from the repository rather
    # than only from the commit invocation.
    subprocess.run(
        ["git", "config", "user.name", "AEGIS Tests"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "aegis-tests@example.invalid"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "--quiet",
            "-m",
            "baseline",
        ],
        cwd=repo_root,
        check=True,
    )


def _invariant_map(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    """
    @brief Index serialized verification invariants by stable identifier.
    @param[in] summary Validation summary returned by verify run.
    @return Mapping from invariant ID to its serialized result.
    """
    invariants = summary["invariants"]
    assert isinstance(invariants, list)
    return {
        str(item["id"]): item
        for item in invariants
        if isinstance(item, dict)
    }


# TESTS


def test_run_stage_schema_declares_full_adoption_and_quick_sequences() -> None:
    """
    @brief Keep every supported kind/profile lifecycle in one declarative table.
    @return None.
    """
    assert QUICK_STAGES == ["intake", "implementation", "validation", "delivery"]
    assert set(RUN_STAGE_SCHEMAS) == {
        ("feature", "full"),
        ("fix", "full"),
        ("change", "full"),
        ("adoption", "full"),
        ("fix", "quick"),
        ("change", "quick"),
    }

    for (kind, profile), expected in RUN_STAGE_SCHEMAS.items():
        graph = Graph(
            run_id=f"{kind}-20260731T120000Z-1234abcd",
            stage=expected.stages[0],
            intent=Intent(id="I-declarative", kind=kind, statement="Resolve schema"),
            profile=profile,
        )
        resolved = run_stage_spec(graph)
        assert resolved is expected

    assert RUN_STAGE_SCHEMAS[("feature", "full")].stages == tuple(STAGES)
    assert RUN_STAGE_SCHEMAS[("adoption", "full")].stages == tuple(ADOPTION_STAGES)
    quick = RUN_STAGE_SCHEMAS[("fix", "quick")]
    assert quick.stages == tuple(QUICK_STAGES)
    assert list(quick.bypassed_stages) == QUICK_BYPASSED_STAGES


def test_old_full_graph_serialization_loads_without_profile_drift(tmp_path: Path) -> None:
    """
    @brief Preserve old schema-3 full graphs and their serialized byte shape.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    graph = Graph(
        run_id="fix-2026-07-31T120000Z-1234abcd",
        stage="intake",
        intent=Intent(id="I-legacy", kind="fix", statement="Load old graph"),
    )
    old_payload = graph.to_dict()
    assert "profile" not in old_payload

    restored = Graph.from_dict(old_payload)
    assert restored.profile == "full"
    assert restored.to_dict() == old_payload

    save_graph(tmp_path, graph)
    graph_path = (
        tmp_path / ".agentic" / "runs" / graph.run_id / "graph.json"
    )
    persisted = json.loads(graph_path.read_text(encoding="utf-8"))
    assert "profile" not in persisted
    loaded = load_graph(tmp_path, graph.run_id)
    assert loaded.profile == "full"
    assert loaded.to_dict() == old_payload


@pytest.mark.parametrize(
    ("kind", "stage"),
    [("feature", "intake"), ("adoption", "adoption-intake")],
)
def test_hand_edited_quick_kind_mismatch_raises_typed_stage_error(
    tmp_path: Path,
    kind: str,
    stage: str,
) -> None:
    """
    @brief Reject unsupported hand-edited quick profiles without a traceback.
    @param[in] tmp_path Configured temporary repository.
    @param[in] kind Full-run kind changed incompatibly to quick.
    @param[in] stage Valid starting stage for the original full run.
    @return None.
    """
    graph = init_graph(tmp_path, kind, "Hand edit profile")  # type: ignore[arg-type]
    assert graph.stage == stage
    path = tmp_path / ".agentic" / "runs" / graph.run_id / "graph.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["profile"] = "quick"
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(StageOperationError, match="kind/profile mismatch"):
        load_graph(tmp_path, graph.run_id)


def test_hand_edited_quick_route_to_bypassed_stage_raises_typed_error(
    tmp_path: Path,
) -> None:
    """
    @brief Reject a persisted quick route into a bypassed lifecycle stage.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    graph = init_graph(
        tmp_path,
        "fix",
        "Reject a corrupt quick route",
        profile="quick",
    )
    graph.stage = "implementation"
    graph.stage_records = {
        "implementation": StageRecord(
            stage="implementation",
            revision=1,
            status="applied",
            retention="latest",
            check_execution="external",
            route_to="alignment",
        )
    }
    save_graph(tmp_path, graph)

    with pytest.raises(
        StageOperationError,
        match="stage-record route conflicts with the run profile",
    ):
        load_graph(tmp_path, graph.run_id)


@pytest.mark.parametrize(
    ("kind", "current_stage", "record_stage", "route_to"),
    [
        ("fix", "design", "implementation", "design"),
        ("adoption", "component-map", "baseline-review", "component-map"),
    ],
)
def test_persisted_earlier_routes_remain_valid_for_full_run_sequences(
    kind: str,
    current_stage: str,
    record_stage: str,
    route_to: str,
) -> None:
    """
    @brief Preserve valid earlier-stage routing for full and adoption runs.
    @param[in] kind Standard or adoption run kind.
    @param[in] current_stage Stage selected by the completed route.
    @param[in] record_stage Stage whose close requested the route.
    @param[in] route_to Earlier stage within the selected lifecycle.
    @return None.
    """
    graph = Graph(
        run_id=f"{kind}-20260731T120000Z-1234abcd",
        stage=current_stage,  # type: ignore[arg-type]
        intent=Intent(
            id="I-valid-route",
            kind=kind,  # type: ignore[arg-type]
            statement="Preserve valid routing",
        ),
        stage_records={
            record_stage: StageRecord(
                stage=record_stage,  # type: ignore[arg-type]
                revision=1,
                status="closed",
                retention="latest",
                check_execution="external",
                route_to=route_to,
            )
        },
    )

    assert run_stage_spec(graph).stages in {
        tuple(STAGES),
        tuple(ADOPTION_STAGES),
    }


@pytest.mark.parametrize("kind", ["feature", "adoption"])
def test_quick_start_rejects_ineligible_kinds_before_state_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """
    @brief Return a typed blocked response for feature/adoption quick starts.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @param[in] kind Ineligible run kind.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as raised:
        main(["run", "start", kind, "--quick", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert raised.value.code == 1
    assert payload["status"] == "blocked"
    assert "kind/profile mismatch" in payload["error"]
    assert "Traceback" not in captured.out + captured.err
    assert not (tmp_path / ".agentic" / "runs").exists()
    assert not (tmp_path / ".agentic" / ".workspace").exists()


def test_quick_change_start_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Accept the proportional profile for a change run.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    started = _invoke_json(capsys, ["run", "start", "change", "--quick"])

    assert started["status"] == "ok"
    assert started["stage"] == "intake"
    assert started["run_profile"] == "quick"
    graph = load_graph(tmp_path, str(started["run_id"]))
    assert graph.intent.kind == "change"
    assert graph.profile == "quick"


def test_complete_quick_fix_lifecycle_reports_bypassed_stages_honestly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Complete all four real quick stages with evidence and verification.
    @details Proves the collapsed stages are journaled and rendered as bypassed,
             while their invariants remain not applicable rather than passed.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    _initialize_git_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    run_id, intake_closed = _complete_quick_intake(tmp_path, capsys)

    bypass_events = [
        entry
        for entry in _journal(tmp_path, run_id)
        if entry["event"] == "run.stages_bypassed"
    ]
    assert len(bypass_events) == 1
    bypass_data = bypass_events[0]["data"]
    assert isinstance(bypass_data, dict)
    assert bypass_data["profile"] == "quick"
    assert bypass_data["status"] == "bypassed"
    assert bypass_data["stages"] == QUICK_BYPASSED_STAGES
    # The literal "human" until 2.1.0 (B19); the approval is now attributable
    # and defaults to the repository's own git identity.
    assert bypass_data["approver"] == "AEGIS Tests <aegis-tests@example.invalid>"
    assert all(
        not (
            entry["event"] == "stage.approved"
            and isinstance(entry["data"], dict)
            and entry["data"].get("stage") in QUICK_BYPASSED_STAGES
        )
        for entry in _journal(tmp_path, run_id)
    )

    status = _invoke_json(capsys, ["run", "status"])
    assert status["run_profile"] == "quick"
    assert status["bypass_status"] == "bypassed"
    assert status["bypassed_stages"] == QUICK_BYPASSED_STAGES

    evidence_id = _record_manual_evidence(tmp_path, capsys)
    source = tmp_path / "src" / "state.py"
    source.write_text("STATE = 'repaired'\n", encoding="utf-8", newline="\n")
    implementation = tmp_path / str(intake_closed["artifact"])
    _replace(
        implementation,
        {
            "changed_paths = []": 'changed_paths = ["src/state.py"]',
            "documentation_effects = []": 'documentation_effects = ["none"]',
            "linked_check_evidence = []": (
                f'linked_check_evidence = ["{evidence_id}"]'
            ),
            'summary = ""': 'summary = "Bounded state repair implemented"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    implementation_closed = _invoke_json(capsys, ["stage", "close"])
    assert implementation_closed["stage"] == "validation"
    assert "advisories" not in implementation_closed

    verified = _invoke_json(capsys, ["verify", "run"])
    summary = verified["verification"]
    assert isinstance(summary, dict)
    assert summary["run_profile"] == "quick"
    assert summary["bypass_status"] == "bypassed"
    assert summary["bypassed_stages"] == QUICK_BYPASSED_STAGES
    impact_rows = summary["impact"]
    assert isinstance(impact_rows, list)
    assert impact_rows == [
        {
            "file": "src/state.py",
            "uncovered": None,
            "coverage_status": "not-applicable",
            "requirements": [],
            "linked_tests": [],
            "full_regression_recommended": False,
        }
    ]
    invariant_by_id = _invariant_map(summary)
    for invariant_id in NOT_APPLICABLE_INVARIANTS:
        item = invariant_by_id[invariant_id]
        assert item["holds"] is None
        assert item["status"] == "not-applicable"
        assert item["message"] == "Not applicable - quick run."
    gates = summary["gates"]
    assert isinstance(gates, dict)
    assert all(
        isinstance(value, dict) and value["status"] == "disabled"
        for value in gates.values()
    )

    validation = tmp_path / str(implementation_closed["artifact"])
    verification_path = str(verified["artifact"])
    _replace(
        validation,
        {
            "deterministic_verification = []": (
                f'deterministic_verification = ["{verification_path}"]'
            ),
            'diff_review = "pending"': 'diff_review = "pass"',
            'documentation_review = "pending"': (
                'documentation_review = "not-applicable"'
            ),
            'style_review = "pending"': 'style_review = "pass"',
            "manual_evidence = []": f'manual_evidence = ["{evidence_id}"]',
            'summary = ""': 'summary = "Quick validation approved"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    validation_closed = _invoke_json(capsys, ["stage", "close"])
    assert validation_closed["stage"] == "delivery"

    report_relative = f".agentic/runs/{run_id}/report.md"
    delivery = tmp_path / str(validation_closed["artifact"])
    _replace(
        delivery,
        {
            'preflight_reference = ""': f'preflight_reference = "{verification_path}"',
            'report = ""': f'report = "{report_relative}"',
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "Quick run ready for handoff"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    completed = _invoke_json(capsys, ["stage", "close"])
    assert completed["complete"] is True

    reported = _invoke_json(capsys, ["delivery", "report"])
    report = (tmp_path / str(reported["artifact"])).read_text(encoding="utf-8")
    plain_report = report.replace("`", "").lower()
    assert (
        "quick run - stages bypassed: alignment, requirement, design, check"
        in plain_report
    )
    for invariant_id in NOT_APPLICABLE_INVARIANTS:
        line = next(
            item for item in report.splitlines() if f"`{invariant_id}`" in item
        )
        assert "PASS" not in line
        assert any(
            marker in line.upper() for marker in ("N/A", "NOT APPLICABLE")
        )

    graph = load_graph(tmp_path, run_id)
    assert graph.complete
    assert set(graph.stage_records) == set(QUICK_STAGES)
    assert all(record.status == "closed" for record in graph.stage_records.values())
    assert [item.id for item in graph.evidence] == [evidence_id]


def test_quick_run_with_waived_enforced_gate_completes_and_reports_honestly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief A mid-flight waiver of one enforced failing gate lets the quick run
           verify with exit zero while the failure and bypasses stay visible.
    @details End-to-end over the CLI: quick fix intake, implementation with
             real evidence, a first verify failing on the enforced test gate,
             `waive add gate:test`, a second verify returning success with the
             gate WAIVED (failure preserved) and the bypassed stages still
             bypassed, and a delivery report rendering both honestly.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    _initialize_git_repository(tmp_path)
    executable = Path(sys.executable).as_posix()
    command = f'"{executable}" -c "import sys; sys.exit(7)"'
    workflow = tmp_path / ".agentic" / "workflow.toml"
    text = workflow.read_text(encoding="utf-8")
    old = '[gates.test]\nmode = "disabled"\ncommands = []'
    assert text.count(old) == 1
    workflow.write_text(
        text.replace(
            old,
            f"[gates.test]\nmode = \"enforce\"\ncommands = [{command!r}]",
        ),
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.chdir(tmp_path)
    run_id, intake_closed = _complete_quick_intake(tmp_path, capsys)
    evidence_id = _record_manual_evidence(tmp_path, capsys)
    source = tmp_path / "src" / "state.py"
    source.write_text("STATE = 'repaired'\n", encoding="utf-8", newline="\n")
    implementation = tmp_path / str(intake_closed["artifact"])
    _replace(
        implementation,
        {
            "changed_paths = []": 'changed_paths = ["src/state.py"]',
            "documentation_effects = []": 'documentation_effects = ["none"]',
            "linked_check_evidence = []": (
                f'linked_check_evidence = ["{evidence_id}"]'
            ),
            'summary = ""': 'summary = "Bounded state repair implemented"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    implementation_closed = _invoke_json(capsys, ["stage", "close"])
    assert implementation_closed["stage"] == "validation"

    with pytest.raises(SystemExit) as blocked:
        main(["verify", "run", "--json"])
    assert blocked.value.code == 1
    first = json.loads(capsys.readouterr().out)
    first_summary = first["verification"]
    assert isinstance(first_summary, dict)
    first_gate = first_summary["gates"]["test"]
    assert isinstance(first_gate, dict)
    assert first_gate["status"] == "failed"

    waived = _invoke_json(
        capsys,
        [
            "waive",
            "add",
            "gate:test",
            "--reason",
            "The known deterministic gate failure is accepted for this run.",
        ],
    )
    waiver = waived["waiver"]
    assert isinstance(waiver, dict)
    assert waiver["blocker_id"] == "gate:test"

    verified = _invoke_json(capsys, ["verify", "run"])
    assert verified["status"] == "ok"
    summary = verified["verification"]
    assert isinstance(summary, dict)
    gate = summary["gates"]["test"]
    assert isinstance(gate, dict)
    assert gate["status"] == "waived"
    assert gate["failure_status"] == "failed"
    assert gate["waived"] is True
    assert summary["bypass_status"] == "bypassed"
    assert summary["bypassed_stages"] == QUICK_BYPASSED_STAGES

    verification_path = str(verified["artifact"])
    validation = tmp_path / str(implementation_closed["artifact"])
    _replace(
        validation,
        {
            "deterministic_verification = []": (
                f'deterministic_verification = ["{verification_path}"]'
            ),
            'diff_review = "pending"': 'diff_review = "pass"',
            'documentation_review = "pending"': (
                'documentation_review = "not-applicable"'
            ),
            'style_review = "pending"': 'style_review = "pass"',
            "manual_evidence = []": f'manual_evidence = ["{evidence_id}"]',
            'summary = ""': 'summary = "Quick validation approved"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    validation_closed = _invoke_json(capsys, ["stage", "close"])
    assert validation_closed["stage"] == "delivery"

    report_relative = f".agentic/runs/{run_id}/report.md"
    delivery = tmp_path / str(validation_closed["artifact"])
    _replace(
        delivery,
        {
            'preflight_reference = ""': f'preflight_reference = "{verification_path}"',
            'report = ""': f'report = "{report_relative}"',
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "Quick run ready for handoff"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    completed = _invoke_json(capsys, ["stage", "close"])
    assert completed["complete"] is True

    reported = _invoke_json(capsys, ["delivery", "report"])
    report = (tmp_path / str(reported["artifact"])).read_text(encoding="utf-8")
    plain_report = report.replace("`", "").lower()
    assert (
        "quick run - stages bypassed: alignment, requirement, design, check"
        in plain_report
    )
    failed_gate_lines = [
        line
        for line in report.splitlines()
        if "gate/fail" in line and "test:" in line
    ]
    assert failed_gate_lines
    assert all(
        "WAIVED" in line and "gate/pass" not in line
        for line in failed_gate_lines
    )


@pytest.mark.parametrize(
    ("mode", "expects_advisory"),
    [("advise", True), ("disabled", False)],
)
def test_quick_changed_path_advisory_is_soft_and_mode_controlled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
    expects_advisory: bool,
) -> None:
    """
    @brief Advise above the path limit without blocking, and stay silent disabled.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @param[in] mode Quick changed-path policy mode.
    @param[in] expects_advisory Whether the close response should advise.
    @return None.
    """
    _configure_quick_path_policy(tmp_path, mode, max_paths=1)
    monkeypatch.chdir(tmp_path)
    _run_id, intake_closed = _complete_quick_intake(tmp_path, capsys)
    evidence_id = _record_manual_evidence(tmp_path, capsys)
    implementation = tmp_path / str(intake_closed["artifact"])
    _replace(
        implementation,
        {
            "changed_paths = []": (
                'changed_paths = ["src/one.py", "src/two.py"]'
            ),
            "linked_check_evidence = []": (
                f'linked_check_evidence = ["{evidence_id}"]'
            ),
            'summary = ""': 'summary = "Two-path repair implemented"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    closed = _invoke_json(capsys, ["stage", "close"])

    assert closed["status"] == "ok"
    assert closed["stage"] == "validation"
    assert closed["next"] == "aegis stage apply"
    if expects_advisory:
        advisories = closed["advisories"]
        assert isinstance(advisories, list)
        assert len(advisories) == 1
        advisory = advisories[0]
        assert advisory == {
            "code": "QUICK-SCOPE-ADVISORY",
            "status": "advisory",
            "changed_path_count": 2,
            "max_paths": 1,
            "message": (
                "Quick run touches 2 changed paths, above the configured maximum "
                "of 1. Quick runs cannot route into bypassed stages; restart as a "
                "full run and carry the recorded context forward with "
                "`aegis run start fix`."
            ),
            "restart_command": "aegis run start fix",
        }
    else:
        assert "advisories" not in closed


def test_quick_implementation_requires_real_active_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Reject missing or invented quick implementation evidence IDs.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    _run_id, intake_closed = _complete_quick_intake(tmp_path, capsys)
    implementation = tmp_path / str(intake_closed["artifact"])
    _replace(
        implementation,
        {
            "changed_paths = []": 'changed_paths = ["src/fix.py"]',
            'summary = ""': 'summary = "Bounded fix implemented"',
        },
    )

    with pytest.raises(SystemExit) as empty_error:
        main(["stage", "apply", "--json"])
    empty_payload = json.loads(capsys.readouterr().out)
    assert empty_error.value.code == 1
    assert empty_payload["status"] == "blocked"
    assert "must not be empty" in str(empty_payload["error"])

    _replace(
        implementation,
        {
            "linked_check_evidence = []": (
                'linked_check_evidence = ["E-9999"]'
            ),
        },
    )
    with pytest.raises(SystemExit) as unknown_error:
        main(["stage", "apply", "--json"])
    unknown_payload = json.loads(capsys.readouterr().out)
    assert unknown_error.value.code == 1
    assert unknown_payload["status"] == "blocked"
    assert "E-9999" in str(unknown_payload["error"])

    evidence_id = _record_manual_evidence(tmp_path, capsys)
    _replace(
        implementation,
        {
            'linked_check_evidence = ["E-9999"]': (
                f'linked_check_evidence = ["{evidence_id}"]'
            ),
        },
    )
    applied = _invoke_json(capsys, ["stage", "apply"])
    assert applied["status"] == "ok"


def test_quick_bypass_journal_rolls_back_with_failed_graph_coupled_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Publish exactly one bypass record only with durable intake closure.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    started = _invoke_json(capsys, ["run", "start", "fix", "--quick"])
    run_id = str(started["run_id"])
    intake = tmp_path / str(started["artifact"])
    _replace(
        intake,
        {
            'statement = ""': 'statement = "Repair one bounded defect"',
            'summary = ""': 'summary = "Quick intake approved"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    graph = load_graph(tmp_path, run_id)
    config = load_config(tmp_path)
    original_atomic_write = store_module.atomic_write_bytes

    def fail_bypass_journal(path: Path, content: bytes) -> None:
        """
        @brief Inject one journal replacement failure after graph save.
        """
        if path.name == "journal.jsonl" and b"run.stages_bypassed" in content:
            raise OSError("injected bypass journal failure")
        original_atomic_write(path, content)

    monkeypatch.setattr(store_module, "atomic_write_bytes", fail_bypass_journal)
    with pytest.raises(OSError, match="injected bypass journal failure"):
        close_stage(tmp_path, graph, config)

    rolled_back = load_graph(tmp_path, run_id)
    assert rolled_back.stage == "intake"
    assert rolled_back.stage_records["intake"].status == "applied"
    assert not any(
        entry["event"] == "run.stages_bypassed"
        for entry in _journal(tmp_path, run_id)
    )

    monkeypatch.setattr(store_module, "atomic_write_bytes", original_atomic_write)
    closed, _artifact = close_stage(tmp_path, rolled_back, config)
    assert closed.stage == "implementation"
    bypass_events = [
        entry
        for entry in _journal(tmp_path, run_id)
        if entry["event"] == "run.stages_bypassed"
    ]
    assert len(bypass_events) == 1


def test_full_start_without_quick_preserves_legacy_shape_and_sequence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Leave full-run graph, journal, response, and stage progression unchanged.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    config = load_config(tmp_path)
    assert config.quick_changed_paths.mode == "disabled"
    assert config.quick_changed_paths.max_paths == 10
    monkeypatch.chdir(tmp_path)

    started = _invoke_json(capsys, ["run", "start", "fix"])
    assert set(started) == {
        "status",
        "stage",
        "artifact",
        "next",
        "run_id",
        "kind",
    }
    run_id = str(started["run_id"])
    graph_path = tmp_path / ".agentic" / "runs" / run_id / "graph.json"
    persisted = json.loads(graph_path.read_text(encoding="utf-8"))
    assert "profile" not in persisted
    graph = load_graph(tmp_path, run_id)
    assert graph.profile == "full"

    started_events = [
        entry for entry in _journal(tmp_path, run_id) if entry["event"] == "run.started"
    ]
    assert len(started_events) == 1
    assert started_events[0]["data"] == {
        "kind": "fix",
        "statement": "",
        "access_mode": "standard",
        "scope_hint": [],
    }

    intake = tmp_path / str(started["artifact"])
    _replace(
        intake,
        {
            'statement = ""': 'statement = "Preserve the full route"',
            'summary = ""': 'summary = "Full intake approved"',
        },
    )
    _invoke_json(capsys, ["stage", "apply"])
    closed = _invoke_json(capsys, ["stage", "close"])
    assert closed["stage"] == "alignment"
    assert "run_profile" not in closed
    assert "bypass_status" not in closed
    assert "bypassed_stages" not in closed
    assert not any(
        entry["event"] == "run.stages_bypassed"
        for entry in _journal(tmp_path, run_id)
    )


# END OF FILE
