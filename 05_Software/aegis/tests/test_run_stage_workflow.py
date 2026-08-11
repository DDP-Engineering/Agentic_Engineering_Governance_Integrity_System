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
@file    test_run_stage_workflow.py
@brief   Verify Run identity, Stage snapshots, entries, and escape behavior.
@details Covers IP-04 through IP-06, PR-RUN, PR-WORKFLOW, PR-SNAPSHOT,
         PR-EVOL, PR-ROLE, and PR-ESCAPE through the public machine interface.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from aegis.composition import create_dispatcher
from aegis.interface.cli import run_cli


def installed_repository(tmp_path: Path) -> Path:
    """@brief Create one synthetic installed repository with real Git state."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    source_template = Path(__file__).parents[1] / "template" / ".agentic"
    shutil.copy2(source_template / "config.toml", agentic / "config.toml")
    shutil.copytree(
        source_template / "aegis" / "workflows", agentic / "aegis" / "workflows"
    )
    for name in ("requirements", "components", "tests", "adoptions", "runs"):
        (agentic / name).mkdir(exist_ok=True)
    return tmp_path


def invoke(
    repo: Path, command: str, data: dict[str, Any] | None = None, *args: str
) -> tuple[int, dict[str, Any]]:
    """@brief Invoke one operation using a versioned stdin machine input."""
    stdin = io.StringIO()
    arguments = ["--repo", str(repo), "--format", "json", command, *args]
    if data is not None:
        operation = command.replace("-", ".", 1)
        special = {
            "run-set-profile": "run.set_profile",
            "stage-set-section": "stage.set_section",
            "stage-revisit": "stage.revisit",
            "finding-set-disposition": "finding.set_disposition",
            "finding-waive": "finding.waive",
            "scope-revise": "scope.revise",
            "attachment-add": "attachment.add",
            "evidence-add": "evidence.add",
            "finding-add": "finding.add",
            "decision-add": "decision.add",
            "stage-skip": "stage.skip",
            "run-create": "run.create",
            "adoption-set-section": "adoption.set_section",
        }
        stdin = io.StringIO(
            json.dumps(
                {
                    "schema": "aegis.machine.input",
                    "schema_version": 1,
                    "operation": special.get(command, operation),
                    "data": data,
                }
            )
        )
        arguments.extend(("--input", "-"))
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = run_cli(
        arguments,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        dispatcher=create_dispatcher(),
    )
    assert stderr.getvalue() == ""
    return exit_code, json.loads(stdout.getvalue())


def create_run(repo: Path, *, profile: str = "full") -> dict[str, Any]:
    """@brief Create one selected synthetic Run."""
    exit_code, response = invoke(
        repo,
        "run-create",
        {
            "ticket_text": "Preserve exact retry evidence.",
            "profile": profile,
            "work_type": "bug_fix",
            "actor": "agent",
            "execution_instruction": "Complete without intermediate prompts.",
        },
    )
    assert exit_code == 0, response
    return response


def test_config_validate_accepts_existing_empty_configured_roots(
    tmp_path: Path,
) -> None:
    """@brief Empty but present project roots are not reported as missing."""
    repo = installed_repository(tmp_path)

    exit_code, response = invoke(repo, "config-validate")

    assert exit_code == 0
    assert response["data"]["finding_count"] == 0


def test_run_creation_publishes_eight_stages_dirty_baseline_and_local_selection(
    tmp_path: Path,
) -> None:
    """@brief Raw ticket text creates an isolated Run without rejecting dirt."""
    repo = installed_repository(tmp_path)
    (repo / "preexisting.txt").write_text("dirty\n", encoding="utf-8")

    response = create_run(repo, profile="short")
    run_id = response["run_id"]
    run_dir = repo / ".agentic" / "runs" / run_id

    assert response["stage"] == "intake"
    assert sorted(path.name for path in run_dir.glob("*.md")) == [
        "01-intake.md",
        "02-alignment.md",
        "03-requirement.md",
        "04-design.md",
        "05-check.md",
        "06-implementation.md",
        "07-validation.md",
        "08-delivery.md",
        "run.md",
    ]
    assert "preexisting.txt" in (run_dir / "run.md").read_text(encoding="utf-8")
    assert 'selected_run = "' + run_id + '"' in (
        repo / ".agentic" / "runs" / "context.toml"
    ).read_text(encoding="utf-8")
    assert 'status = "omitted"' in (run_dir / "04-design.md").read_text(
        encoding="utf-8"
    )


def test_multiple_runs_list_select_and_profile_change_do_not_combine_state(
    tmp_path: Path,
) -> None:
    """@brief Multiple Runs coexist and selection/profile changes stay isolated."""
    repo = installed_repository(tmp_path)
    first = create_run(repo)
    second = create_run(repo, profile="short")

    exit_code, listed = invoke(repo, "run-list")
    assert exit_code == 0
    assert {item["id"] for item in listed["data"]["items"]} == {
        first["run_id"],
        second["run_id"],
    }
    exit_code, selected = invoke(repo, "run-select", None, first["run_id"])
    assert exit_code == 0
    exit_code, changed = invoke(repo, "run-set-profile", None, "--profile", "short")
    assert exit_code == 0
    assert changed["data"]["profile"] == "short"
    assert first["run_id"] in (repo / ".agentic" / "runs" / "context.toml").read_text(
        encoding="utf-8"
    )


def test_stage_sections_transitions_and_resume_state_are_atomic(tmp_path: Path) -> None:
    """@brief Each command changes one Stage concern without auto-advancing."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)

    exit_code, updated = invoke(
        repo,
        "stage-set-section",
        {
            "section": "restated_ask",
            "content": "Keep every retry outcome.",
            "actor": "agent",
        },
    )
    assert exit_code == 0
    assert updated["stage"] == "intake"
    exit_code, completed = invoke(repo, "stage-complete")
    assert exit_code == 0
    assert completed["data"]["status"] == "completed"
    assert completed["stage"] == "intake"
    exit_code, started = invoke(repo, "stage-start", None, "alignment")
    assert exit_code == 0
    assert started["stage"] == "alignment"
    exit_code, shown = invoke(repo, "stage-show")
    assert exit_code == 0
    assert shown["data"]["instruction"]
    assert shown["data"]["sections"]
    assert shown["run_id"] == created["run_id"]


def test_entries_scope_skip_attachment_and_revisit_preserve_distinct_meaning(
    tmp_path: Path,
) -> None:
    """@brief Findings, decisions, waivers, skips, and revisions remain distinct."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    attachment = repo / "raw.log"
    attachment.write_bytes(b"raw evidence\n")

    assert (
        invoke(
            repo,
            "evidence-add",
            {
                "kind": "manual",
                "actor": "agent",
                "procedure": "inspect",
                "expected": "present",
                "actual": "present",
            },
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "finding-add",
            {
                "severity": "warning",
                "observation": "Coverage uncertain.",
                "consequence": "Use full suite.",
            },
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "finding-waive",
            {"actor": "agent", "reason": "Accepted for this run."},
            "--finding",
            "F1",
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "exception_approved",
                "actor": "agent",
                "target": "red_before_green",
                "reason": "Documentation-only behavior.",
                "alternative_confirmation": "Rendered review",
            },
        )[0]
        == 0
    )
    attached = invoke(
        repo,
        "attachment-add",
        {
            "source": str(attachment),
            "purpose": "raw output",
            "content_type": "text/plain",
        },
    )[1]
    assert attached["artifacts"][0]["action"] == "created"
    revised = invoke(
        repo,
        "scope-revise",
        {
            "before": "retry",
            "after": "all attempts",
            "actor": "agent",
            "reason": "Found cancellation path.",
            "affected_work": ["intake"],
        },
    )[1]
    assert revised["data"]["affected_work"] == ["intake"]
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "alignment")[0] == 0
    skipped = invoke(
        repo, "stage-skip", {"actor": "agent", "reason": "Scope was already explicit."}
    )[1]
    assert skipped["data"]["status"] == "skipped"
    revisited = invoke(
        repo,
        "stage-revisit",
        {"actor": "agent", "reason": "Developer requested detail."},
        "alignment",
    )[1]
    assert revisited["data"]["status"] == "active"
