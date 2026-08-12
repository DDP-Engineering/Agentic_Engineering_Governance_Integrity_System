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

import hashlib
import io
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from aegis.composition import create_dispatcher
from aegis.interface.cli import run_cli

_AUTO_REVISION = object()
_CURRENT_STAGE_MUTATIONS = {
    "stage-set-section",
    "stage-complete",
    "stage-skip",
    "evidence-add",
    "finding-add",
    "finding-set-disposition",
    "finding-waive",
    "decision-add",
    "attachment-add",
    "trace-impacted",
    "execution-run",
}


def _option_value(arguments: tuple[str, ...], option: str) -> str | None:
    """@return One option value from a public test invocation."""
    try:
        return arguments[arguments.index(option) + 1]
    except (ValueError, IndexError):
        return None


def _observed_revision(
    repo: Path, command: str, arguments: tuple[str, ...]
) -> str | None:
    """@brief Read the exact public target revision used by a test mutation."""
    read_command: str | None = None
    read_arguments: tuple[str, ...] = ()
    if command in _CURRENT_STAGE_MUTATIONS:
        read_command = "stage-show"
    elif command in {"stage-start", "stage-revisit"} and arguments:
        read_command = "stage-show"
        read_arguments = ("--stage", arguments[0])
    elif command in {"run-set-profile", "run-abandon", "scope-revise"}:
        read_command = "run-show"
    elif command in {
        "requirement-update",
        "requirement-delete",
        "specification-set",
        "specification-delete",
    }:
        target = _option_value(arguments, "--requirement")
        if target is not None:
            read_command = "requirement-show"
            read_arguments = ("--requirement", target)
    elif command in {"component-update", "component-delete"}:
        target = _option_value(arguments, "--component")
        if target is not None:
            read_command = "component-show"
            read_arguments = ("--component", target)
    elif command in {
        "adoption-set-section",
        "adoption-complete",
        "adoption-abandon",
    }:
        target = _option_value(arguments, "--adoption")
        if target is not None:
            read_command = "adoption-show"
            read_arguments = ("--adoption", target)
    if read_command is None:
        return None
    exit_code, response = invoke(
        repo,
        read_command,
        None,
        *read_arguments,
        expected_revision=None,
    )
    if exit_code != 0:
        return None
    return response["revision"]


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
    repo: Path,
    command: str,
    data: dict[str, Any] | None = None,
    *args: str,
    expected_revision: str | None | object = _AUTO_REVISION,
) -> tuple[int, dict[str, Any]]:
    """@brief Invoke one operation using a versioned stdin machine input."""
    stdin = io.StringIO()
    revision = (
        _observed_revision(repo, command, args)
        if expected_revision is _AUTO_REVISION
        else expected_revision
    )
    arguments = ["--repo", str(repo), "--format", "json"]
    if isinstance(revision, str):
        arguments.extend(("--expected-revision", revision))
    arguments.extend((command, *args))
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


def commit_repository(repo: Path, message: str = "baseline") -> None:
    """@brief Commit prepared synthetic Git state for an attribution baseline."""
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", message], check=True)


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
    run_text = (run_dir / "run.md").read_text(encoding="utf-8")
    assert "state_json" not in run_text
    assert run_text.count("[[stages]]") == 8
    for heading in (
        "## Ticket input",
        "## Intent",
        "## Current scope",
        "## Execution instruction",
        "## Scope-change log",
        "## Stage summary",
        "## Change attribution",
        "## Current handoff",
        "## Terminal outcome",
        "## Run event history",
    ):
        assert heading in run_text
    assert "Complete without intermediate prompts." in run_text


def test_run_mutation_records_new_changes_without_claiming_authorship(
    tmp_path: Path,
) -> None:
    """@brief PR-RUN-005 records a later path at a normal mutation boundary."""
    repo = installed_repository(tmp_path)
    (repo / "preexisting.txt").write_text("opening\n", encoding="utf-8")
    created = create_run(repo)
    (repo / "later.py").write_text("VALUE = 1\n", encoding="utf-8")

    exit_code, updated = invoke(
        repo,
        "stage-set-section",
        {"section": "facts_and_uncertainties", "content": "Record later state."},
    )

    assert exit_code == 0, updated
    state = invoke(repo, "run-show")[1]["data"]["state"]
    assert [item["path"] for item in state["changes_first_observed"]] == ["later.py"]
    assert state["changes_first_observed"][0]["state"] == ["untracked"]
    assert state["changes_first_observed"][0]["observed_at"].endswith("Z")
    assert state["changes_adopted"] == []
    assert state["uncertain_authorship"][0]["path"] == "later.py"
    assert state["uncertain_authorship"][0]["observed_at"].endswith("Z")
    assert "preexisting.txt" not in str(state["changes_first_observed"])
    context = invoke(repo, "stage-show")[1]["data"]["run_summary"]
    observed = context["change_attribution"]["first_observed"]["items"]
    assert json.loads(observed[0]["content"])["path"] == "later.py"
    assert json.loads(observed[0]["content"])["observed_at"].endswith("Z")

    before = (repo / ".agentic" / "runs" / created["run_id"] / "run.md").read_bytes()
    assert invoke(repo, "run-show")[0] == 0
    shown_exit, shown = invoke(repo, "stage-show")
    assert shown_exit == 0, shown
    assert (
        repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    ).read_bytes() == before


def test_committed_opening_snapshot_excludes_clean_paths_from_attribution(
    tmp_path: Path,
) -> None:
    """@brief PR-RUN-005 retains clean baseline revisions across Run reload."""
    repo = installed_repository(tmp_path)
    tracked = repo / "tracked.py"
    tracked.write_text("VALUE = 1\n", encoding="utf-8")
    commit_repository(repo)
    create_run(repo)
    opening = invoke(repo, "run-show")[1]["data"]["state"]["opening_repository_state"]
    assert "working_files" not in opening
    assert opening["dirty_paths"] == []
    tracked.write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "later.py").write_text("VALUE = 3\n", encoding="utf-8")

    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": "facts_and_uncertainties", "content": "Observe changes."},
        )[0]
        == 0
    )

    state = invoke(repo, "run-show")[1]["data"]["state"]
    assert [item["path"] for item in state["changes_first_observed"]] == [
        "later.py",
        "tracked.py",
    ]


def test_index_transition_is_durable_attribution_uncertainty(tmp_path: Path) -> None:
    """@brief PR-RUN-007 keeps an index transition after Run publication."""
    repo = installed_repository(tmp_path)
    (repo / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_repository(repo)
    create_run(repo)
    (repo / "tracked.py").write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.py"], check=True)

    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": "facts_and_uncertainties", "content": "Observe index."},
        )[0]
        == 0
    )

    state = invoke(repo, "run-show")[1]["data"]["state"]
    assert [item["code"] for item in state["attribution_findings"]] == [
        "repository_index_revision_changed"
    ]
    assert (
        invoke(repo, "stage-show")[1]["data"]["run_summary"]["change_attribution"]
        ["findings"]["total_count"]
        == 1
    )


def test_branch_and_head_transition_record_exact_timed_uncertainty(
    tmp_path: Path,
) -> None:
    """@brief FS-BASE-005 retains observed branch and revision transitions."""
    repo = installed_repository(tmp_path)
    (repo / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit_repository(repo)
    create_run(repo)
    before_branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    before_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "-C", str(repo), "switch", "-qc", "other"], check=True)
    (repo / "tracked.py").write_text("VALUE = 2\n", encoding="utf-8")
    commit_repository(repo, "other")

    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": "facts_and_uncertainties", "content": "Observe switch."},
        )[0]
        == 0
    )

    findings = invoke(repo, "run-show")[1]["data"]["state"]["attribution_findings"]
    expected = (
        ("repository_branch_changed", before_branch),
        ("repository_head_changed", before_head),
    )
    for code, before in expected:
        finding = next(item for item in findings if item["code"] == code)
        assert finding["before"] == before
        assert finding["after"] != before
        assert finding["observed_at"].endswith("Z")


def test_abandonment_observes_later_path_at_its_publication_boundary(
    tmp_path: Path,
) -> None:
    """@brief PR-RUN-005 applies attribution during normal Run abandonment."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    (repo / "later.py").write_text("VALUE = 1\n", encoding="utf-8")

    exit_code, abandoned = invoke(
        repo,
        "run-abandon",
        {"actor": "agent", "reason": "Stop after observed change."},
    )

    assert exit_code == 0, abandoned
    state = invoke(repo, "run-show", None, "--run", created["run_id"])[1]["data"][
        "state"
    ]
    assert state["changes_first_observed"][0]["path"] == "later.py"
    assert state["changes_first_observed"][0]["observed_at"].endswith("Z")


def test_dirty_opening_stays_preexisting_and_later_transition_is_uncertain(
    tmp_path: Path,
) -> None:
    """@brief PR-RUN-006 retains dirty kinds and flags only later transitions."""
    repo = installed_repository(tmp_path)
    for name in ("staged.py", "unstaged.py", "deleted.py", "rename_from.py"):
        (repo / name).write_text("BASE = 1\n", encoding="utf-8")
    commit_repository(repo)
    (repo / "staged.py").write_text("STAGED = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "staged.py"], check=True)
    (repo / "unstaged.py").write_text("UNSTAGED = 1\n", encoding="utf-8")
    (repo / "untracked.py").write_text("UNTRACKED = 1\n", encoding="utf-8")
    (repo / "deleted.py").unlink()
    subprocess.run(
        ["git", "-C", str(repo), "mv", "rename_from.py", "rename_to.py"],
        check=True,
    )
    created = create_run(repo)
    (repo / "unstaged.py").write_text("UNSTAGED = 2\n", encoding="utf-8")
    stage_path = f".agentic/runs/{created['run_id']}/01-intake.md"
    revision = (repo / stage_path).read_bytes()

    exit_code, observed = invoke(
        repo,
        "stage-set-section",
        {"section": "facts_and_uncertainties", "content": "Observe dirt."},
        expected_revision="sha256:" + hashlib.sha256(revision).hexdigest(),
    )
    assert exit_code == 0, observed

    state = invoke(repo, "run-show")[1]["data"]["state"]
    assert state["changes_first_observed"] == []
    finding = next(
        item
        for item in state["attribution_findings"]
        if item["code"] == "preexisting_worktree_changed"
        and item["path"] == "unstaged.py"
    )
    assert finding["observed_at"].endswith("Z")
    assert finding["before"]["state"] == ["unstaged"]
    assert finding["after"]["state"] == ["unstaged"]


def test_scope_revision_explicitly_adopts_observed_paths_once(tmp_path: Path) -> None:
    """@brief PR-RUN-005 adopts only an explicitly scoped observed path."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "adopted.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": "facts_and_uncertainties", "content": "Observe path."},
        )[0]
        == 0
    )

    exit_code, revised = invoke(
        repo,
        "scope-revise",
        {
            "before": "Existing scope.",
            "after": "Adopted path is in scope.",
            "actor": "agent",
            "reason": "Explicitly accepted the observed implementation path.",
            "affected_work": ["adopted.py", "not-observed.py"],
        },
    )

    assert exit_code == 0, revised
    state = invoke(repo, "run-show")[1]["data"]["state"]
    assert state["changes_adopted"] == [
        {
            "path": "adopted.py",
            "scope_change": 1,
            "reason": "Explicitly accepted the observed implementation path.",
        }
    ]
    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": "facts_and_uncertainties", "content": "Repeat."},
        )[0]
        == 0
    )
    assert (
        len(invoke(repo, "run-show")[1]["data"]["state"]["changes_first_observed"])
        == 1
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
    run_path = (
        repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    )
    assert "Keep every retry outcome." in run_path.read_text(encoding="utf-8")
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
    run_text = run_path.read_text(encoding="utf-8")
    assert "| Intake | completed | Recorded |" in run_text
    assert "stage_completed" in run_text
    assert "stage_started" in run_text


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
