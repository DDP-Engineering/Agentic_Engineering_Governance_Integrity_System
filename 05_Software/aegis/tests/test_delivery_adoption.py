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

from tests.test_execution_integrity import advance_to
from tests.test_run_stage_workflow import create_run, installed_repository, invoke


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
