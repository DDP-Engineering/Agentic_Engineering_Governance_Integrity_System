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

from pathlib import Path

from aegis.infrastructure.codecs import parse_markdown_document

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
        ("run-set-profile", None, ("--profile", "full")),
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
    assert damaged_path.read_bytes() == damaged_bytes
    sibling = repo / ".agentic" / "runs" / f"ABANDON-{damaged['run_id']}.md"
    assert sibling.exists()


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
