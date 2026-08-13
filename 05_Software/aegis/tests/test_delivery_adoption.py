#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_delivery_adoption.py
@brief   Verify truthful Delivery, abandonment, and resumable Adoption.
@details Covers IP-12/IP-13, PR-DELIVERY, PR-REPORT, PR-ESCAPE-003/010,
         PR-ADOPT, AC-DELIVERY-001, AC-ABANDON-001, and AC-ADOPT-001.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

from aegis.infrastructure.codecs import (
    parse_markdown_document,
    render_markdown_document,
)
from aegis.infrastructure.workspace import FileWorkspace

from tests.test_execution_integrity import advance_to
from tests.test_run_stage_workflow import create_run, installed_repository, invoke


def _select_terminal_run(repo: Path, run_id: str) -> None:
    """@brief Restore the non-authoritative pointer to one terminal Run."""
    (repo / ".agentic" / "runs" / "context.toml").write_text(
        f'schema = 1\nartifact_type = "working_context"\nselected_run = "{run_id}"\n',
        encoding="utf-8",
    )


def _assert_terminal_run_rejects_mutation(
    repo: Path, run_id: str, status: str
) -> None:
    """@brief Verify terminal Runs remain readable but reject shared mutations."""
    _select_terminal_run(repo, run_id)
    assert invoke(repo, "run-show")[0] == 0
    assert invoke(repo, "stage-show")[0] == 0

    attempts = (
        (
            "stage-set-section",
            {"section": "terminal_result", "content": "changed", "actor": "agent"},
            (),
        ),
        ("stage-complete", None, ()),
        (
            "stage-revisit",
            {"actor": "agent", "reason": "Reopen terminal work."},
            ("validation" if status == "delivered" else "intake",),
        ),
        (
            "run-set-profile",
            {"actor": "agent", "reason": "Attempt a terminal profile change."},
            ("--profile", "full"),
        ),
        (
            "scope-revise",
            {
                "before": "Original scope.",
                "after": "Changed terminal scope.",
                "actor": "agent",
                "reason": "Attempt a terminal mutation.",
                "affected_work": [],
            },
            (),
        ),
    )
    for command, data, arguments in attempts:
        exit_code, rejected = invoke(repo, command, data, *arguments)
        assert exit_code == 4, (command, rejected)
        assert rejected["error"]["code"] == "invalid_transition"
        assert status in rejected["error"]["summary"], (command, rejected)


def test_delivery_prefill_references_large_prior_state_without_repr(
    tmp_path: Path,
) -> None:
    """@brief PR-REPORT-002 keeps Delivery prose concise and reviewable."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    intake_path = run_dir / "01-intake.md"
    metadata, state, _ = parse_markdown_document(
        intake_path.read_bytes(), path=intake_path.relative_to(repo).as_posix()
    )
    windows_command = [
        "C:\\Users\\reviewer\\workspace\\" + ("very-long-segment\\" * 80),
        "--artifact",
        "D:\\evidence\\" + ("nested\\" * 80) + "result.json",
    ]
    state["evidence"].extend(
        {
            "kind": "automated",
            "category": "tests",
            "name": f"prior-{index:03d}",
            "command": windows_command,
            "working_directory": windows_command[0],
            "outcome": "failed",
            "exit_status": 1,
            "observed_result": "The prior command reported a failure.",
            "tests": [windows_command[1]],
        }
        for index in range(80)
    )
    state["findings"].extend(
        {
            "label": f"F{index + 1}",
            "code": "prior_review_finding",
            "severity": "warning",
            "summary": "A prior review item remains visible.",
            "observation": windows_command[0],
            "consequence": "Review the durable Stage artifact.",
            "disposition": "open",
        }
        for index in range(80)
    )
    intake_path.write_bytes(render_markdown_document(metadata, state, kind="stage"))
    advance_to(repo, "validation")
    assert invoke(repo, "stage-complete")[0] == 0

    evidence_count = 0
    finding_count = 0
    for stage_path in sorted(run_dir.glob("0[1-7]-*.md")):
        _, prior_state, _ = parse_markdown_document(
            stage_path.read_bytes(), path=stage_path.relative_to(repo).as_posix()
        )
        evidence_count += len(prior_state.get("evidence", []))
        finding_count += len(prior_state.get("findings", []))
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    _, delivery_state, _ = parse_markdown_document(
        (run_dir / "08-delivery.md").read_bytes(),
        path=f".agentic/runs/{created['run_id']}/08-delivery.md",
    )
    delivery = delivery_state["sections"]

    evidence_summary = delivery["evidence_summary"]
    residual_risk = delivery["findings_and_residual_risk"]
    durable_root = f".agentic/runs/{created['run_id']}/"
    assert len(evidence_summary) <= 240
    assert len(residual_risk) <= 240
    assert f"{evidence_count} prior Stage evidence record" in evidence_summary
    assert f"{finding_count} prior Stage finding record" in residual_risk
    assert durable_root in evidence_summary
    assert durable_root in residual_risk
    for prose in (evidence_summary, residual_risk):
        assert "\\\\" not in prose
        assert "C:\\Users" not in prose
        assert "{'" not in prose
        assert '"command"' not in prose
        assert "passed" not in prose.lower()
        assert "success" not in prose.lower()


def test_adoption_list_rediscovers_paginated_and_unreadable_journals(
    tmp_path: Path,
) -> None:
    """@brief PR-ADOPT-005 rediscovers every Adoption without a central index."""
    repo = installed_repository(tmp_path)
    created: dict[str, dict[str, str]] = {}
    for index in range(25):
        component_id = f"COMP-{index:032x}"
        exit_code, response = invoke(
            repo,
            "adoption-create",
            {
                "scope": f"Observe component {index}.",
                "actor": "agent",
                "observed_implementation": [f"src/component_{index}.py"],
                "observed_tests": [],
                "unresolved_gaps": [f"Gap {index}"],
                "component_id": component_id,
            },
        )
        assert exit_code == 0, response
        created[response["data"]["id"]] = {"component_id": component_id}
    identities = sorted(created)
    unreadable_id = identities[5]
    unreadable_path = repo / ".agentic" / "adoptions" / f"{unreadable_id}.md"
    unreadable_bytes = b"unreadable Adoption state\xff\x00"
    unreadable_path.write_bytes(unreadable_bytes)
    before = {
        path: path.read_bytes()
        for path in (repo / ".agentic" / "adoptions").glob("ADOPT-*.md")
    }

    first_exit, first = invoke(repo, "adoption-list")
    second_exit, second = invoke(repo, "adoption-list", None, "--cursor", "20")

    assert first_exit == second_exit == 0
    assert [item["id"] for item in first["data"]["items"]] == identities[:20]
    assert first["data"]["has_more"] is True
    assert first["data"]["next_cursor"] == "20"
    assert [item["id"] for item in second["data"]["items"]] == identities[20:]
    assert second["data"]["has_more"] is False
    assert second["data"]["next_cursor"] is None
    listed = {item["id"]: item for item in first["data"]["items"]}
    assert listed[unreadable_id]["status"] == "unreadable"
    assert listed[unreadable_id]["path"] == unreadable_path.relative_to(repo).as_posix()
    healthy_id = identities[6]
    healthy = listed[healthy_id]
    assert healthy["status"] == "active"
    assert healthy["component_id"] == created[healthy_id]["component_id"]
    assert healthy["path"] == f".agentic/adoptions/{healthy_id}.md"
    assert healthy["revision"].startswith("sha256:")
    assert healthy["resume_state"] == {
        "completed_discovery_count": 0,
        "current_artifact_count": 0,
        "current_gap_count": 1,
        "next_action": "Continue bounded observation.",
    }
    assert {path: path.read_bytes() for path in before} == before


def test_approved_delivery_atomically_completes_stage_run_and_pointer(
    tmp_path: Path,
) -> None:
    """@brief Delivery approval accepts truth and ends before developer Git work."""
    repo = installed_repository(tmp_path)
    created = create_run(repo, profile="short")
    advance_to(repo, "validation")
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    assert (
        invoke(
            repo,
            "stage-set-section",
            {
                "section": "requested_and_delivered_outcome",
                "content": "Requested retry integrity; delivered retry integrity.",
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
            },
        )[0]
        == 0
    )

    exit_code, delivered = invoke(repo, "stage-complete")

    assert exit_code == 0, delivered
    assert delivered["outcome"] == "delivered"
    run_text = (repo / ".agentic" / "runs" / created["run_id"] / "run.md").read_text(
        encoding="utf-8"
    )
    assert 'status = "delivered"' in run_text
    assert 'selected_run = ""' in (
        repo / ".agentic" / "runs" / "context.toml"
    ).read_text(encoding="utf-8")


def test_delivery_gate_errors_name_their_required_input(tmp_path: Path) -> None:
    """@brief Delivery precondition errors provide exact atomic corrections."""
    repo = installed_repository(tmp_path)
    create_run(repo, profile="short")
    advance_to(repo, "validation")
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0

    approval_exit, approval_error = invoke(repo, "stage-complete")

    assert approval_exit == 4, approval_error
    assert approval_error["error"]["code"] == "invalid_transition"
    assert approval_error["error"]["summary"] == (
        'Delivery requires the latest decision.add with target "delivery" to have '
        "value approved."
    )
    assert approval_error["next_actions"] == [
        {
            "operation": "decision.add",
            "arguments": {"value": "approved", "target": "delivery"},
            "reason": (
                "Supply actor and reason to approve the truthful Delivery report."
            ),
        }
    ]

    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "approved",
                "actor": "agent",
                "target": "delivery",
                "reason": "The report is accurate.",
            },
        )[0]
        == 0
    )

    assessment_exit, assessment_error = invoke(repo, "stage-complete")

    assert assessment_exit == 4, assessment_error
    assert assessment_error["error"]["code"] == "invalid_transition"
    assert assessment_error["error"]["summary"] == (
        'Delivery requires stage.set_section with section "terminal_result" set to '
        "achieved, partially_achieved, or not_achieved."
    )
    assert assessment_error["next_actions"] == [
        {
            "operation": "stage.set_section",
            "arguments": {"section": "terminal_result"},
            "reason": (
                "Set content to exactly one of achieved, partially_achieved, or "
                "not_achieved; the caller must choose the truthful assessment."
            ),
        }
    ]


def test_delivered_run_rejects_stage_mutation(tmp_path: Path) -> None:
    """@brief PR-RUN-008/009 keep delivered Runs terminal through the pointer."""
    repo = installed_repository(tmp_path)
    created = create_run(repo, profile="short")
    advance_to(repo, "validation")
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
                "reason": "The report is accurate.",
            },
        )[0]
        == 0
    )
    assert invoke(repo, "stage-complete")[0] == 0

    _assert_terminal_run_rejects_mutation(repo, created["run_id"], "delivered")


def test_abandoned_run_rejects_stage_mutation(tmp_path: Path) -> None:
    """@brief PR-RUN-008/009 keep abandoned Runs terminal through the pointer."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    assert (
        invoke(
            repo,
            "run-abandon",
            {"actor": "agent", "reason": "The ticket was withdrawn."},
        )[0]
        == 0
    )

    _assert_terminal_run_rejects_mutation(repo, created["run_id"], "abandoned")


def test_delivery_latest_applicable_decision_must_be_approved(tmp_path: Path) -> None:
    """@brief A rejection after an approval keeps Delivery and the Run active."""
    repo = installed_repository(tmp_path)
    created = create_run(repo, profile="short")
    advance_to(repo, "validation")
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
    for value, reason in (
        ("approved", "The report was accurate at first review."),
        ("rejected", "A later review found the report incomplete."),
    ):
        assert (
            invoke(
                repo,
                "decision-add",
                {
                    "value": value,
                    "actor": "agent",
                    "target": "delivery",
                    "reason": reason,
                },
            )[0]
            == 0
        )

    exit_code, rejected = invoke(repo, "stage-complete")

    assert exit_code == 4, rejected
    assert rejected["error"]["code"] == "invalid_transition"
    assert "latest" in rejected["error"]["summary"].lower()
    current = invoke(repo, "stage-show")[1]
    assert current["data"]["status"] == "active"
    run_text = (repo / ".agentic" / "runs" / created["run_id"] / "run.md").read_text(
        encoding="utf-8"
    )
    assert 'status = "active"' in run_text


def test_normal_and_exceptional_abandonment_preserve_existing_bytes(
    tmp_path: Path,
) -> None:
    """@brief Readable state is terminally updated; unreadable state gets a sibling."""
    repo = installed_repository(tmp_path)
    normal = create_run(repo)
    abandoned = invoke(
        repo, "run-abandon", {"actor": "agent", "reason": "Ticket was withdrawn."}
    )[1]
    assert abandoned["outcome"] == "abandoned"
    assert 'status = "abandoned"' in (
        repo / ".agentic" / "runs" / normal["run_id"] / "run.md"
    ).read_text(encoding="utf-8")

    damaged = create_run(repo)
    damaged_path = repo / ".agentic" / "runs" / damaged["run_id"] / "run.md"
    damaged_bytes = b"\xff\x00unreadable"
    damaged_path.write_bytes(damaged_bytes)
    exit_code, exceptional = invoke(
        repo, "run-abandon", {"actor": "agent", "reason": "Run state cannot be read."}
    )

    assert exit_code == 0, exceptional
    assert exceptional["data"]["exceptional"] is True
    assert exceptional["data"]["run_summary_updated"] is False
    assert exceptional["data"]["last_known_state"] == "unknown"
    assert damaged_path.read_bytes() == damaged_bytes
    sibling = repo / ".agentic" / "runs" / f"ABANDON-{damaged['run_id']}.md"
    assert sibling.exists()
    _, sibling_state, _ = parse_markdown_document(
        sibling.read_bytes(), path=sibling.relative_to(repo).as_posix()
    )
    run_relative = damaged_path.relative_to(repo).as_posix()
    assert exceptional["data"]["unreadable_paths"] == [run_relative]
    assert sibling_state["unreadable_paths"] == [run_relative]
    assert sibling_state["last_known_state"] == "unknown"


def test_exceptional_abandonment_closes_a_readable_run(tmp_path: Path) -> None:
    """@brief PR-ESCAPE-003/010 close a readable Run around a corrupt Stage."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    run_path = run_dir / "run.md"
    stage_path = run_dir / "01-intake.md"
    pointer_path = repo / ".agentic" / "runs" / "context.toml"
    damaged_stage = b"\xff\x00unreadable Stage bytes\r\n"
    (repo / "later.py").write_text("VALUE = 1\n", encoding="utf-8")
    stage_path.write_bytes(damaged_stage)
    reason = "The current Stage cannot be decoded safely."

    exit_code, abandoned = invoke(
        repo, "run-abandon", {"actor": "agent", "reason": reason}
    )

    assert exit_code == 0, abandoned
    assert abandoned["outcome"] == "abandoned"
    assert abandoned["data"]["exceptional"] is True
    assert abandoned["data"]["run_summary_updated"] is True
    assert abandoned["data"]["last_known_state"] == "active at intake"
    run_bytes = run_path.read_bytes()
    run_metadata, run_state, _ = parse_markdown_document(
        run_bytes, path=run_path.relative_to(repo).as_posix()
    )
    outcome = run_state["outcome"]
    assert run_metadata["status"] == "abandoned"
    assert run_metadata["updated_at"] == outcome["time"]
    assert outcome == {
        "workflow": "abandoned",
        "reason": reason,
        "actor": "agent",
        "time": outcome["time"],
    }
    assert run_state["next_action"] == "None; this Run is terminal."
    assert run_state["events"][-1] == {
        "time": outcome["time"],
        "actor": "agent",
        "event": "run_abandoned",
        "result": reason,
    }
    assert any(
        item["path"] == "later.py" for item in run_state["changes_first_observed"]
    )
    assert abandoned["revision"] == f"sha256:{hashlib.sha256(run_bytes).hexdigest()}"
    sibling = repo / ".agentic" / "runs" / f"ABANDON-{created['run_id']}.md"
    assert sibling.exists()
    _, sibling_state, _ = parse_markdown_document(
        sibling.read_bytes(), path=sibling.relative_to(repo).as_posix()
    )
    assert sibling_state["last_known_state"] == "active at intake"
    assert stage_path.read_bytes() == damaged_stage
    assert 'selected_run = ""' in pointer_path.read_text(encoding="utf-8")

    list_exit, listed = invoke(repo, "run-list")
    assert list_exit == 0, listed
    item = next(
        item
        for item in listed["data"]["items"]
        if item["id"] == created["run_id"]
    )
    assert item["status"] == "abandoned"
    select_exit, selected = invoke(repo, "run-select", None, created["run_id"])
    assert select_exit == 4, selected
    assert selected["error"]["code"] == "invalid_transition"


def test_unreadable_paths_names_the_failing_path(tmp_path: Path) -> None:
    """@brief FS-ABANDON-005 names the corrupt Stage without exposing its bytes."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    stage_path = run_dir / "01-intake.md"
    damaged_stage = b"SECRET-RAW-BYTES:\xff\x00"
    stage_path.write_bytes(damaged_stage)
    expected_path = stage_path.relative_to(repo).as_posix()

    exit_code, abandoned = invoke(
        repo,
        "run-abandon",
        {"actor": "agent", "reason": "The current Stage is unreadable."},
    )

    assert exit_code == 0, abandoned
    assert abandoned["data"]["unreadable_paths"] == [expected_path]
    sibling = repo / ".agentic" / "runs" / f"ABANDON-{created['run_id']}.md"
    _, sibling_state, _ = parse_markdown_document(
        sibling.read_bytes(), path=sibling.relative_to(repo).as_posix()
    )
    assert sibling_state["unreadable_paths"] == [expected_path]
    assert sibling_state["last_known_state"] == "active at intake"
    assert sibling_state["normal_update_failure"]
    assert sibling_state["diagnostics"] == "Original bytes were preserved."
    rendered = sibling.read_text(encoding="utf-8")
    assert "SECRET-RAW-BYTES" not in rendered
    assert stage_path.read_bytes() == damaged_stage


def test_exceptional_abandonment_refuses_a_readable_terminal_run_atomically(
    tmp_path: Path,
) -> None:
    """@brief A stale active load cannot abandon a terminal Run a second time."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    run_path = run_dir / "run.md"
    stage_path = run_dir / "01-intake.md"
    pointer_path = repo / ".agentic" / "runs" / "context.toml"
    active_run_bytes = run_path.read_bytes()
    abandoned = invoke(
        repo,
        "run-abandon",
        {"actor": "agent", "reason": "End the active Run."},
    )
    assert abandoned[0] == 0, abandoned[1]
    _select_terminal_run(repo, created["run_id"])
    damaged_stage = b"terminal Run Stage is unreadable\xff"
    stage_path.write_bytes(damaged_stage)
    sibling = repo / ".agentic" / "runs" / f"ABANDON-{created['run_id']}.md"
    before = (run_path.read_bytes(), stage_path.read_bytes(), pointer_path.read_bytes())
    run_relative = run_path.relative_to(repo).as_posix()
    original_load_document = FileWorkspace.load_document
    stale_run_loads = 0

    def load_stale_active_then_terminal(
        workspace: FileWorkspace, path: str
    ) -> tuple[dict[str, object], dict[str, object], str]:
        """@brief Reproduce two stale active reads before terminal fallback load."""
        nonlocal stale_run_loads
        if path == run_relative and stale_run_loads < 2:
            stale_run_loads += 1
            metadata, state, _ = parse_markdown_document(active_run_bytes, path=path)
            revision = f"sha256:{hashlib.sha256(active_run_bytes).hexdigest()}"
            return metadata, state, revision
        return original_load_document(workspace, path)

    with patch.object(
        FileWorkspace, "load_document", load_stale_active_then_terminal
    ):
        exit_code, refused = invoke(
            repo,
            "run-abandon",
            {"actor": "agent", "reason": "Do not abandon terminal state again."},
            expected_revision=None,
        )

    assert stale_run_loads == 2
    assert exit_code == 4, refused
    assert refused["error"]["code"] == "invalid_transition"
    assert (
        run_path.read_bytes(),
        stage_path.read_bytes(),
        pointer_path.read_bytes(),
    ) == before
    assert not sibling.exists()


def test_run_abandons_from_a_completed_stage(tmp_path: Path) -> None:
    """@brief PR-ESCAPE-001/003 allow abandonment between Stages."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    completed = invoke(repo, "stage-complete")
    assert completed[0] == 0, completed[1]
    run_shown = invoke(repo, "run-show")
    assert run_shown[0] == 0, run_shown[1]

    exit_code, abandoned = invoke(
        repo,
        "run-abandon",
        {"actor": "agent", "reason": "The approved work is no longer needed."},
        expected_revision=run_shown[1]["revision"],
    )

    assert exit_code == 0, abandoned
    assert abandoned["outcome"] == "abandoned"
    run_path = repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    run_metadata, run_state, _ = parse_markdown_document(
        run_path.read_bytes(), path=str(run_path)
    )
    stage_path = repo / ".agentic" / "runs" / created["run_id"] / "01-intake.md"
    stage_metadata, stage_state, _ = parse_markdown_document(
        stage_path.read_bytes(), path=str(stage_path)
    )
    outcome = run_state["outcome"]
    assert run_metadata["status"] == "abandoned"
    assert outcome["workflow"] == "abandoned"
    assert outcome["actor"] == "agent"
    assert outcome["reason"] == "The approved work is no longer needed."
    assert outcome["time"]
    run_event = run_state["events"][-1]
    assert run_event == {
        "time": outcome["time"],
        "actor": "agent",
        "event": "run_abandoned",
        "result": "The approved work is no longer needed.",
    }
    assert stage_metadata["status"] == "completed"
    stage_event = stage_state["events"][-1]
    assert stage_event == run_event


def test_adoption_is_incremental_resumable_and_preserves_visible_gaps(
    tmp_path: Path,
) -> None:
    """@brief One bounded Adoption can resume, complete with gaps, or abandon."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    exit_code, created = invoke(
        repo,
        "adoption-create",
        {
            "scope": "Retry recorder",
            "actor": "agent",
            "component_id": "",
            "observed_implementation": ["src/retry.py retains attempts"],
            "observed_tests": [],
            "unresolved_gaps": ["No existing automated test"],
        },
    )
    assert exit_code == 0, created
    adoption_id = created["data"]["id"]
    updated = invoke(
        repo,
        "adoption-set-section",
        {
            "section": "observed_tests",
            "content": ["tests/test_retry.py demonstrates retention"],
            "actor": "agent",
        },
        "--adoption",
        adoption_id,
    )[1]
    assert updated["data"]["section"] == "observed_tests"
    resumed = invoke(repo, "adoption-show", None, "--adoption", adoption_id)[1]
    assert resumed["data"]["state"]["observed_tests"] == [
        "tests/test_retry.py demonstrates retention"
    ]
    completed = invoke(repo, "adoption-complete", None, "--adoption", adoption_id)[1]
    assert completed["outcome"] == "completed"
    assert completed["data"]["remaining_gaps"] == ["No existing automated test"]
