#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_waivers.py
@brief Contract tests for exact, run-local, journaled blocker waivers.
@details Covers CLI approval validation, persistence, hard-block consumption,
         digest staleness, honest WAIVED rendering, and the non-waivable
         persistence-integrity floor.
"""

# IMPORTS

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

import aegis.cli as cli_module
import aegis.stage_forms as stage_forms_module
import aegis.verification as verification
import aegis.waiver_targets as waiver_targets
from aegis.cli import main
from aegis.config import WorkflowConfig, load_config
from aegis.gates import gate_failure_blockers
from aegis.invariants import blocking_failures, evaluate
from aegis.models import Check, Evidence, Graph, SolutionDesign, StageRecord
from aegis.persistence import PersistenceError
from aegis.report import render_report
from aegis.repowise import RepoWiseInspection
from aegis.requirement_store import create_requirement_record
from aegis.requirements import AuditIssue, RequirementPatch, audit_coverage, update_requirement
from aegis.stage_forms import close_stage, stage_blocker_details, stage_blockers
from aegis.store import (
    GraphConflictError,
    add_waiver,
    init_graph,
    load_graph,
    save_graph,
)
from aegis.verification import run_verification, validation_summary_path
from aegis.waiver_targets import (
    annotate_audit_issues,
    audit_issue_blocker,
    working_tree_blocker,
)

# CONSTANTS

CHECK_ID = "CHK-0001"
REQUIREMENT_UUID = uuid.UUID("4bd8e00d-3e41-4bcb-a39f-b4ac421bac75")

# LOCAL HELPERS


def _journal(repo_root: Path, run_id: str) -> list[dict[str, object]]:
    """
    @brief Read one run journal as parsed JSON Lines.
    @param[in] repo_root Temporary repository root.
    @param[in] run_id Run whose journal is inspected.
    @return Parsed journal entries in append order.
    """
    path = repo_root / ".agentic" / "runs" / run_id / "journal.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _configure_failing_test_gate(repo_root: Path) -> WorkflowConfig:
    """
    @brief Enable one deterministic enforced gate that exits with status seven.
    @param[in] repo_root Temporary repository root.
    @return Reloaded workflow configuration.
    """
    path = repo_root / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    executable = Path(sys.executable).as_posix()
    command = f'"{executable}" -c "import sys; sys.exit(7)"'
    old = '[gates.test]\nmode = "disabled"\ncommands = []'
    new = f"[gates.test]\nmode = \"enforce\"\ncommands = [{command!r}]"
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return load_config(repo_root)


def _approve_empty_design(repo_root: Path, graph: Graph) -> None:
    """
    @brief Attach a digest-stable approved design that cites no requirements.
    @param[in] repo_root Temporary repository root.
    @param[in,out] graph Mutable workflow graph.
    @return None.
    """
    design_path = repo_root / ".agentic" / "runs" / graph.run_id / "design.md"
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text(
        "# Design\n\nRun the configured deterministic gate.\n",
        encoding="utf-8",
        newline="\n",
    )
    graph.design = SolutionDesign(
        revision=1,
        status="approved",
        document_path=design_path.relative_to(repo_root).as_posix(),
        document_digest=sha256(design_path.read_bytes()).hexdigest(),
        requirement_digests={},
        selected_option="Deterministic gate",
        approval="human",
        approved_at="2026-07-31T08:00:00+00:00",
    )


def _configure_coverage(repo_root: Path) -> WorkflowConfig:
    """
    @brief Enable source coverage enforcement for one temporary repository.
    @param[in] repo_root Temporary repository root.
    @return Reloaded workflow configuration.
    """
    path = repo_root / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    old = (
        '[traceability.coverage]\nmode = "disabled"\n'
        "coverable_roots = []\nexclude = []"
    )
    new = (
        '[traceability.coverage]\nmode = "enforce"\n'
        'coverable_roots = ["src"]\nexclude = ["__init__.py"]'
    )
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return load_config(repo_root)


def _invariant(
    repo_root: Path,
    graph: Graph,
    config: WorkflowConfig,
    item_id: str,
):
    """
    @brief Return one named invariant from a complete evaluation.
    @return Matching invariant result.
    """
    return next(
        item
        for item in evaluate(repo_root, graph, config)
        if item.id == item_id
    )


# TESTS


def test_cli_add_mints_persists_and_journals_one_waiver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Record an exact waiver through the CLI and expose it through list.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Journal one waiver")
    monkeypatch.chdir(tmp_path)

    main(
        [
            "waive",
            "add",
            "INV-6",
            "--reason",
            "Proceed with evidence captured by the next step.",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    waiver = payload["waiver"]
    assert waiver["id"].startswith("WVR-")
    assert uuid.UUID(waiver["id"].removeprefix("WVR-")).version == 4
    assert waiver["blocker_id"] == "INV-6"
    assert waiver["approver"] == "human"

    persisted = load_graph(tmp_path, graph.run_id)
    assert [item.id for item in persisted.waivers] == [waiver["id"]]
    events = [
        entry for entry in _journal(tmp_path, graph.run_id)
        if entry["event"] == "waiver.added"
    ]
    assert len(events) == 1
    assert events[0]["data"] == waiver

    main(["waive", "list", "--json"])
    listed = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in listed["active_waivers"]] == [waiver["id"]]


@pytest.mark.parametrize("reason", ["", "   \t"])
def test_store_rejects_empty_waiver_reason(
    tmp_path: Path,
    reason: str,
) -> None:
    """
    @brief Reject empty and whitespace-only human approval reasons in storage.
    @param[in] tmp_path Configured temporary repository.
    @param[in] reason Invalid reason variant.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Reject empty reason")

    with pytest.raises(ValueError, match="reason must be non-empty"):
        add_waiver(
            tmp_path,
            graph,
            "INV-6",
            reason,
            {"invariant:INV-6": "current"},
        )

    assert load_graph(tmp_path, graph.run_id).waivers == []
    assert not any(
        entry["event"] == "waiver.added"
        for entry in _journal(tmp_path, graph.run_id)
    )


def test_zero_waiver_inv7_preserves_legacy_policy_shape(
    tmp_path: Path,
) -> None:
    """
    @brief Preserve ordinary INV-7 output while making failures eligible.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Preserve zero-waiver output")

    inv_7 = _invariant(tmp_path, graph, config, "INV-7")

    assert inv_7.policy == "non-waivable"
    assert inv_7.can_waive is True
    assert inv_7.to_dict() == {
        "id": "INV-7",
        "name": "Clean secrets",
        "holds": True,
        "policy": "non-waivable",
        "message": "Secret scanning is disabled by workflow.toml.",
    }


def test_cli_rejects_whitespace_reason_and_unmatched_broad_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Enforce one current exact target and a non-empty approval reason.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Reject broad waiver")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as empty_exit:
        main(["waive", "add", "INV-6", "--reason", "  ", "--json"])
    assert empty_exit.value.code == 1
    empty_payload = json.loads(capsys.readouterr().out)
    assert empty_payload["status"] == "blocked"
    assert "reason must not be empty" in empty_payload["error"]

    with pytest.raises(SystemExit) as wildcard_exit:
        main(["waive", "add", "INV-*", "--reason", "Too broad", "--json"])
    assert wildcard_exit.value.code == 1
    wildcard_payload = json.loads(capsys.readouterr().out)
    assert wildcard_payload["status"] == "blocked"
    assert "not currently active or is not waivable" in wildcard_payload["error"]
    assert load_graph(tmp_path, graph.run_id).waivers == []


def test_cli_accepts_exact_working_tree_id_containing_brackets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Treat metacharacters inside a current blocker ID as exact text.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    finding = {
        "code": "WORKTREE-GENERATED-ARTIFACT",
        "message": "Generated route artifact requires review.",
        "path": "src/routes/[id].py",
    }
    monkeypatch.setattr(
        waiver_targets,
        "audit_working_tree",
        lambda *_args, **_kwargs: {
            "entries": [],
            "untracked": [],
            "blocking_findings": [finding],
        },
    )
    graph = init_graph(tmp_path, "feature", "Waive an exact bracketed path")
    blocker = working_tree_blocker(finding)
    assert "[" in blocker.id
    monkeypatch.chdir(tmp_path)

    main(
        [
            "waive",
            "add",
            blocker.id,
            "--reason",
            "This generated route is covered by framework integration tests.",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["waiver"]["blocker_id"] == blocker.id
    assert payload["blocker"]["waived"] is True
    assert len(load_graph(tmp_path, graph.run_id).waivers) == 1


def test_gate_waiver_unblocks_verification_and_renders_honest_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Keep a waived gate and inherited INV-4 failed while returning success.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @return None.
    """
    monkeypatch.setattr(
        verification,
        "audit_working_tree",
        lambda *_args, **_kwargs: {
            "entries": [],
            "untracked": [],
            "blocking_findings": [],
        },
    )
    config = _configure_failing_test_gate(tmp_path)
    graph = init_graph(tmp_path, "feature", "Waive one failing test gate")
    graph.stage = "implementation"
    _approve_empty_design(tmp_path, graph)
    save_graph(tmp_path, graph)

    _first_summary, first_code = run_verification(
        tmp_path,
        graph,
        config,
    )
    assert first_code == 1
    graph = load_graph(tmp_path, graph.run_id)
    blocker = next(
        item
        for item in gate_failure_blockers(graph, config)
        if item.id == "gate:test"
    )
    waiver = add_waiver(
        tmp_path,
        graph,
        blocker.id,
        "The known test-environment failure is accepted for this run.",
        blocker.state_digests,
    )

    summary, code = run_verification(tmp_path, graph, config)

    assert code == 0, json.dumps(summary, indent=2)
    gate = summary["gates"]["test"]
    assert gate["status"] == "waived"
    assert gate["status"] != "passed"
    assert gate["failure_status"] == "failed"
    assert gate["waived"] is True
    assert gate["waivers"] == [
        {
            "id": waiver.id,
            "reason": waiver.reason,
            "created_at": waiver.created_at,
            "approver": "human",
        }
    ]
    inv_4 = next(item for item in summary["invariants"] if item["id"] == "INV-4")
    assert inv_4["holds"] is False
    assert inv_4["waived"] is True
    assert inv_4["waivers"][0]["reason"] == waiver.reason
    persisted = json.loads(
        validation_summary_path(tmp_path, graph).read_text(encoding="utf-8")
    )
    assert persisted["gates"]["test"] == gate

    report = render_report(tmp_path, load_graph(tmp_path, graph.run_id), config)
    inv_4_line = next(
        line for line in report.splitlines() if line.startswith("- `INV-4`")
    )
    assert "WAIVED" in inv_4_line
    assert "PASS" not in inv_4_line
    assert waiver.reason in inv_4_line
    assert waiver.created_at in inv_4_line
    failed_gate_lines = [
        line
        for line in report.splitlines()
        if "gate/fail" in line and "test:" in line
    ]
    assert failed_gate_lines
    assert all("WAIVED" in line and "gate/pass" not in line for line in failed_gate_lines)


def test_red_before_green_waiver_closes_implementation_but_inv3_stays_failed(
    tmp_path: Path,
) -> None:
    """
    @brief Waive one check's missing red evidence without reporting INV-3 passed.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "fix", "Accept one missing red observation")
    graph.stage = "implementation"
    graph.checks = [
        Check(
            id=CHECK_ID,
            level="test",
            cites_spec=[],
            command="python tests/test_state.py",
            state="green",
            green_evidence="E-0001",
        )
    ]
    graph.evidence = [
        Evidence(
            id="E-0001",
            kind="test-run",
            result="pass",
            summary="The implementation is green.",
            command="python tests/test_state.py",
            stage="implementation",
            check_id=CHECK_ID,
            exit_status=0,
        )
    ]
    graph.stage_records["implementation"] = StageRecord(
        stage="implementation",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="external",
        digest="implementation-state",
    )
    save_graph(tmp_path, graph)
    assert stage_blockers(tmp_path, graph) == [
        f"{CHECK_ID} is missing prior red evidence"
    ]
    blocker = next(
        item
        for item in stage_blocker_details(tmp_path, graph)
        if item.id == f"red-before-green:{CHECK_ID}"
    )
    waiver = add_waiver(
        tmp_path,
        graph,
        blocker.id,
        "The pre-existing behavior could not be reproduced locally.",
        blocker.state_digests,
    )

    assert stage_blockers(tmp_path, graph) == []
    graph, artifact = close_stage(tmp_path, graph, config)

    assert graph.stage == "validation"
    assert artifact is not None
    inv_3 = _invariant(tmp_path, graph, config, "INV-3")
    assert inv_3.holds is False
    assert inv_3.waived is True
    assert inv_3.waivers == (waiver,)
    assert blocking_failures([inv_3]) == []
    rendered = inv_3.to_dict()
    assert rendered["holds"] is False
    assert rendered["waived"] is True
    assert "passed" not in json.dumps(rendered).lower()


def test_inv10_waiver_goes_stale_after_cited_requirement_changes_again(
    tmp_path: Path,
) -> None:
    """
    @brief Pin an INV-10 approval to state B and restore blocking for state C.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    config = load_config(tmp_path)
    record = create_requirement_record(
        tmp_path,
        config,
        category="functional",
        priority="Must",
        requirement="Requirement content state A.",
        rationale="The design cites this exact requirement.",
        verification="Inspection: compare the design and requirement.",
        affected_paths=("src/state.py",),
        timestamp="2026-07-31T08:00:00Z",
        uuid_factory=lambda: REQUIREMENT_UUID,
    )
    requirement_path = tmp_path / str(record.source_file)
    graph = init_graph(tmp_path, "change", "Exercise INV-10 waiver staleness")
    graph.stage = "check"
    design_path = (
        tmp_path / ".agentic" / "runs" / graph.run_id / "design.md"
    )
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text(
        "# Design\n\nCite the durable requirement.\n",
        encoding="utf-8",
        newline="\n",
    )
    graph.design = SolutionDesign(
        revision=1,
        status="approved",
        document_path=design_path.relative_to(tmp_path).as_posix(),
        document_digest=sha256(design_path.read_bytes()).hexdigest(),
        requirement_digests={
            record.id: sha256(requirement_path.read_bytes()).hexdigest()
        },
        selected_option="Digest-pinned requirement",
        approval="human",
        approved_at="2026-07-31T08:00:00+00:00",
    )
    save_graph(tmp_path, graph)

    update_requirement(
        tmp_path,
        record.id,
        config=config,
        patch=RequirementPatch(
            requirement="Requirement content state B.",
            timestamp="2026-07-31T08:01:00Z",
        ),
    )
    state_b = _invariant(tmp_path, graph, config, "INV-10")
    assert state_b.holds is False
    assert state_b.waived is False
    waiver = add_waiver(
        tmp_path,
        graph,
        state_b.id,
        "State B is accepted for this run while design catches up.",
        state_b.state_digests,
    )
    state_b_waived = _invariant(tmp_path, graph, config, "INV-10")
    assert state_b_waived.holds is False
    assert state_b_waived.waived is True
    assert state_b_waived.waivers == (waiver,)

    update_requirement(
        tmp_path,
        record.id,
        config=config,
        patch=RequirementPatch(
            requirement="Requirement content state C.",
            timestamp="2026-07-31T08:02:00Z",
        ),
    )
    state_c = _invariant(tmp_path, graph, config, "INV-10")
    assert state_c.holds is False
    assert state_c.waived is False
    assert state_c.waivers == ()
    assert blocking_failures([state_c]) == [state_c]


def test_exact_coverage_finding_waiver_annotates_and_unblocks(
    tmp_path: Path,
) -> None:
    """
    @brief Neutralize one exact coverage finding while retaining failed detail.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    config = _configure_coverage(tmp_path)
    source = tmp_path / "src" / "uncovered.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
    graph = init_graph(tmp_path, "feature", "Waive one uncovered source file")
    issues = audit_coverage(tmp_path, config)
    assert [(item.code, item.path) for item in issues] == [
        ("REQ-COVERAGE-MISSING", "src/uncovered.py")
    ]
    blocker = audit_issue_blocker("coverage", issues[0])
    waiver = add_waiver(
        tmp_path,
        graph,
        blocker.id,
        "This generated compatibility shim has no direct test.",
        blocker.state_digests,
    )

    annotated, blockers = annotate_audit_issues("coverage", issues, graph)

    assert blockers == []
    assert annotated == [
        {
            **issues[0].to_dict(),
            "waived": True,
            "waivers": [
                {
                    "id": waiver.id,
                    "reason": waiver.reason,
                    "created_at": waiver.created_at,
                    "approver": "human",
                }
            ],
        }
    ]
    assert annotated[0].get("status") != "passed"


def test_same_requirement_traceability_findings_have_independent_targets(
    tmp_path: Path,
) -> None:
    """
    @brief Give every unresolved linked test its own exact waiver identity.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Waive linked tests independently")
    issues = [
        AuditIssue(
            code="REQ-LINK-MISSING",
            message="F-0001 linked test is missing: tests/test_first.py",
            req_id="F-0001",
            path="tests/test_first.py",
        ),
        AuditIssue(
            code="REQ-LINK-MISSING",
            message="F-0001 linked test is missing: tests/test_second.py",
            req_id="F-0001",
            path="tests/test_second.py",
        ),
    ]
    targets = [
        audit_issue_blocker("traceability", issue)
        for issue in issues
    ]
    assert len({target.id for target in targets}) == 2

    add_waiver(
        tmp_path,
        graph,
        targets[0].id,
        "The first missing linked test is accepted for this run.",
        targets[0].state_digests,
    )
    first_pass, first_blockers = annotate_audit_issues(
        "traceability",
        issues,
        graph,
    )
    assert first_pass[0]["waived"] is True
    assert first_pass[1].get("waived") is None
    assert [blocker.id for blocker in first_blockers] == [targets[1].id]

    add_waiver(
        tmp_path,
        graph,
        targets[1].id,
        "The second missing linked test is accepted for this run.",
        targets[1].state_digests,
    )
    second_pass, second_blockers = annotate_audit_issues(
        "traceability",
        issues,
        graph,
    )
    assert second_blockers == []
    assert all(item["waived"] is True for item in second_pass)


def test_invalid_required_integration_is_not_a_waiver_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Keep malformed required integration state in the structural floor.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @return None.
    """
    graph = init_graph(tmp_path, "adoption", "Reject integration corruption")
    graph.stage = "repo-discovery"
    graph.stage_records["repo-discovery"] = StageRecord(
        stage="repo-discovery",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="external",
        digest="repo-discovery-state",
        payload={"candidate_components": ["API"]},
    )
    monkeypatch.setattr(
        stage_forms_module,
        "inspect_repowise",
        lambda *_args, **_kwargs: RepoWiseInspection(
            status="invalid",
            mode="required",
            source="external",
            current=False,
            warnings=("knowledge-graph schema is malformed",),
        ),
    )

    blockers = stage_blockers(tmp_path, graph)
    targets = stage_blocker_details(tmp_path, graph)

    assert blockers == [
        "required RepoWise discovery is not current: "
        "knowledge-graph schema is malformed"
    ]
    assert targets == []


def test_stale_graph_conflict_cannot_be_bypassed_by_adding_waiver(
    tmp_path: Path,
) -> None:
    """
    @brief Preserve stale-update conflict enforcement ahead of waiver mutation.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Protect persistence integrity")
    stale = load_graph(tmp_path, graph.run_id)
    current = load_graph(tmp_path, graph.run_id)
    current.intent.statement = "A concurrently persisted edit."
    save_graph(tmp_path, current)
    stale.intent.statement = "A conflicting local edit."

    with pytest.raises(GraphConflictError):
        add_waiver(
            tmp_path,
            stale,
            "INV-6",
            "A waiver cannot override stale graph protection.",
            {"invariant:INV-6": "conflicting-state"},
        )

    persisted = load_graph(tmp_path, graph.run_id)
    assert persisted.intent.statement == "A concurrently persisted edit."
    assert persisted.waivers == []
    assert not any(
        entry["event"] == "waiver.added"
        for entry in _journal(tmp_path, graph.run_id)
    )


@pytest.mark.parametrize(
    ("corrupt_journal", "error"),
    [
        (b'{"event":"partial"', "incomplete record"),
        (b"not-json\n", "not valid JSON"),
    ],
)
def test_corrupt_journal_rejects_waiver_without_persisting_graph_record(
    tmp_path: Path,
    corrupt_journal: bytes,
    error: str,
) -> None:
    """
    @brief Keep journal corruption in the non-waivable structural floor.
    @param[in] tmp_path Configured temporary repository.
    @param[in] corrupt_journal Structurally invalid journal bytes.
    @param[in] error Expected integrity-error fragment.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Protect journal integrity")
    graph_path = (
        tmp_path / ".agentic" / "runs" / graph.run_id / "graph.json"
    )
    journal_path = (
        tmp_path / ".agentic" / "runs" / graph.run_id / "journal.jsonl"
    )
    original_graph = graph_path.read_bytes()
    journal_path.write_bytes(corrupt_journal)

    with pytest.raises(PersistenceError, match=error):
        add_waiver(
            tmp_path,
            graph,
            "INV-6",
            "A process waiver cannot bypass journal corruption.",
            {"invariant:INV-6": "current"},
        )

    assert graph_path.read_bytes() == original_graph
    assert journal_path.read_bytes() == corrupt_journal
    assert load_graph(tmp_path, graph.run_id).waivers == []


def test_concurrent_duplicate_waiver_refreshes_and_rejects_second_record(
    tmp_path: Path,
) -> None:
    """
    @brief Revalidate duplicate approval after authoritative graph refresh.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Serialize duplicate waiver")
    first = load_graph(tmp_path, graph.run_id)
    concurrent = load_graph(tmp_path, graph.run_id)
    blocker_state = {"invariant:INV-6": "current"}
    add_waiver(
        tmp_path,
        first,
        "INV-6",
        "The first human approval is authoritative.",
        blocker_state,
    )

    with pytest.raises(ValueError, match="already has an active waiver"):
        add_waiver(
            tmp_path,
            concurrent,
            "INV-6",
            "A concurrent duplicate must not be persisted.",
            blocker_state,
        )

    persisted = load_graph(tmp_path, graph.run_id)
    assert len(persisted.waivers) == 1
    assert len(
        [
            entry for entry in _journal(tmp_path, graph.run_id)
            if entry["event"] == "waiver.added"
        ]
    ) == 1


def test_cli_rejects_target_discovered_from_concurrently_changed_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Reject a waiver when graph state changes during target discovery.
    @param[in] tmp_path Configured temporary repository.
    @param[in] monkeypatch Pytest environment fixture.
    @param[in] capsys Pytest capture fixture.
    @return None.
    """
    graph = init_graph(tmp_path, "feature", "Discover against current graph")
    original_collect = cli_module.collect_waiver_targets

    def collect_then_change(*args, **kwargs):
        targets = original_collect(*args, **kwargs)
        concurrent = load_graph(tmp_path, graph.run_id)
        concurrent.intent.statement = "A concurrent authoritative change."
        save_graph(tmp_path, concurrent)
        return targets

    monkeypatch.setattr(
        cli_module,
        "collect_waiver_targets",
        collect_then_change,
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as conflict_exit:
        main(
            [
                "waive",
                "add",
                "INV-6",
                "--reason",
                "This target was discovered from stale graph state.",
                "--json",
            ]
        )

    assert conflict_exit.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    assert "GRAPH-STALE-UPDATE" in payload["error"]
    assert load_graph(tmp_path, graph.run_id).waivers == []
    assert not any(
        entry["event"] == "waiver.added"
        for entry in _journal(tmp_path, graph.run_id)
    )


def _configure_secret_scanning(repo_root: Path) -> WorkflowConfig:
    """
    @brief Enable one enforced secret pattern in the workflow policy.
    @param[in] repo_root Temporary repository root.
    @return Reloaded workflow configuration.
    """
    path = repo_root / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    old = '[guardrails.secrets]\nmode = "disabled"\npatterns = []'
    new = '[guardrails.secrets]\nmode = "enforce"\npatterns = ["AKIA[0-9A-Z]{16}"]'
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return load_config(repo_root)


def test_inv7_waiver_goes_stale_when_new_secret_matches_same_pattern(
    tmp_path: Path,
) -> None:
    """
    @brief A new secret matching an already-waived pattern must re-block.
    @details The waiver is pinned to the scanned content, not the message
             text; the message is identical for both secrets, so this test
             fails if the pin ever regresses to message-only digests.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    config = _configure_secret_scanning(tmp_path)
    graph = init_graph(tmp_path, "feature", "Secret waiver staleness")
    (tmp_path / "fixture.txt").write_text(
        "example key AKIAAAAAAAAAAAAAAAAA\n", encoding="utf-8"
    )

    first = _invariant(tmp_path, graph, config, "INV-7")
    assert first.holds is False
    assert first.state_digests

    add_waiver(
        tmp_path,
        graph,
        "INV-7",
        "Known documentation fixture value",
        dict(first.state_digests),
    )
    graph = load_graph(tmp_path, graph.run_id)
    waived = _invariant(tmp_path, graph, config, "INV-7")
    assert waived.holds is False
    assert waived.waivers
    assert blocking_failures([waived]) == []

    (tmp_path / "second.txt").write_text(
        "another key AKIABBBBBBBBBBBBBBBB\n", encoding="utf-8"
    )
    stale = _invariant(tmp_path, graph, config, "INV-7")
    assert stale.holds is False
    assert stale.waivers == ()
    assert [item.id for item in blocking_failures([stale])] == ["INV-7"]


# END OF FILE
