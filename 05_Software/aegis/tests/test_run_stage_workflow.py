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
import tomllib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from aegis.composition import create_dispatcher
from aegis.domain.values import RepositoryPath
from aegis.infrastructure.codecs import render_markdown_document, render_requirement
from aegis.infrastructure.transactions import (
    FileMutation,
    TransactionCheckpoint,
    TransactionStore,
)
from aegis.infrastructure.workspace import FileWorkspace
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


def test_shipped_workflow_guidance_has_bounded_advisory_shape() -> None:
    """@brief Every shipped Stage provides compact findings and recovery actions."""
    workflows = (
        Path(__file__).parents[1]
        / "template"
        / ".agentic"
        / "aegis"
        / "workflows"
    )
    resources = {
        path.stem: tomllib.loads(path.read_text(encoding="utf-8"))
        for path in workflows.glob("*.toml")
    }

    assert set(resources) == {
        "intake",
        "alignment",
        "requirement",
        "design",
        "check",
        "implementation",
        "validation",
        "delivery",
    }
    operations = set()
    for stage, resource in resources.items():
        assert resource["schema"] == 1
        assert resource["stage"] == stage
        assert 1 <= len(resource["common_findings"]) <= 4
        assert all(
            isinstance(finding, str) and 1 <= len(finding) <= 240
            for finding in resource["common_findings"]
        )
        assert 1 <= len(resource["recovery_actions"]) <= 4
        for action in resource["recovery_actions"]:
            assert set(action) == {"condition", "operation", "guidance"}
            assert all(
                isinstance(action[key], str) and 1 <= len(action[key]) <= 240
                for key in action
            )
            operations.add(action["operation"])
        assert len((workflows / f"{stage}.toml").read_bytes()) <= 1600

    assert {
        "stage.set_section",
        "stage.skip",
        "stage.revisit",
        "decision.add",
    } <= operations


def test_stage_show_exposes_snapshotted_workflow_guidance(tmp_path: Path) -> None:
    """@brief Resume context exposes the guidance captured when a Run begins."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    source = tomllib.loads(
        (
            repo
            / ".agentic"
            / "aegis"
            / "workflows"
            / "check.toml"
        ).read_text(encoding="utf-8")
    )

    exit_code, shown = invoke(repo, "stage-show", None, "--stage", "check")

    assert exit_code == 0, shown
    assert shown["data"]["guidance"] == {
        "common_findings": source["common_findings"],
        "recovery_actions": source["recovery_actions"],
    }


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


def write_list_artifacts(repo: Path, *, count: int = 25) -> dict[str, list[str]]:
    """@brief Write deterministic Run, Requirement, and Component list fixtures."""
    identities = {"run-list": [], "requirement-list": [], "component-list": []}
    for index in range(count):
        suffix = f"{index:032x}"
        run_id = f"RUN-{suffix}"
        requirement_id = f"REQ-{suffix}"
        component_id = f"COMP-{suffix}"
        identities["run-list"].append(run_id)
        identities["requirement-list"].append(requirement_id)
        identities["component-list"].append(component_id)

        run_dir = repo / ".agentic" / "runs" / run_id
        run_dir.mkdir()
        (run_dir / "run.md").write_bytes(
            render_markdown_document(
                {
                    "schema": 1,
                    "artifact_type": "run",
                    "id": run_id,
                    "status": "delivered",
                    "profile": "full",
                    "current_stage": "delivery",
                    "updated_at": "2026-08-12T00:00:00Z",
                },
                {"ticket_text": f"Run ticket {index}", "stages": []},
                kind="run",
            )
        )
        (repo / ".agentic" / "requirements" / f"{requirement_id}.toml").write_bytes(
            render_requirement(
                {
                    "id": requirement_id,
                    "title": f"Requirement {index}",
                    "status": "active",
                    "priority": "Must",
                    "behavior": "The numbered behavior remains addressable.",
                    "confirmation": "List the numbered Requirement.",
                    "verification_kind": "manual",
                    "manual_method": "Inspect the list response.",
                    "impacted_files": [],
                    "tests": [],
                    "updated_at": "2026-08-12T00:00:00Z",
                }
            )
        )
        (
            repo / ".agentic" / "components" / f"{component_id}.md"
        ).write_bytes(
            render_markdown_document(
                {
                    "schema": 1,
                    "artifact_type": "component",
                    "id": component_id,
                    "status": "active",
                    "name": f"Component {index}",
                    "files": [],
                    "requirement_ids": [],
                    "reviewed_at": "2026-08-12T00:00:00Z",
                },
                {"known_gaps": [], "test_links": []},
                kind="component",
            )
        )
    return identities


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


def test_config_validate_reports_pending_transaction_before_lazy_recovery(
    tmp_path: Path,
) -> None:
    """@brief AM validation item 18 reports residue without recovering it."""
    repo = installed_repository(tmp_path)
    store = TransactionStore(repo)

    def interrupt(checkpoint: TransactionCheckpoint) -> None:
        if checkpoint == TransactionCheckpoint.PREPARED:
            raise RuntimeError("simulated interruption")

    with pytest.raises(RuntimeError, match="simulated interruption"):
        store.publish(
            (
                FileMutation(
                    RepositoryPath(".agentic/rules.md"), b"recovered content\n"
                ),
            ),
            checkpoint=interrupt,
        )
    transaction = next(store.transactions.glob("TXN-*"))
    for index in range(11):
        shutil.copytree(
            transaction,
            store.transactions / f"TXN-{index:032x}",
        )
    transactions = sorted(store.transactions.glob("TXN-*"))

    exit_code, response = invoke(repo, "config-validate")

    assert exit_code == 0, response
    assert response["data"] == {
        "finding_count": 10,
        "pending_recovery_count": 12,
        "reported_pending_recovery_count": 10,
    }
    assert response["truncated"] is True
    expected_findings = [
        {
            "label": f"F{index}",
            "code": "pending_recovery_transaction",
            "severity": "info",
            "summary": "Pending interrupted publication recovery material is present.",
            "disposition": "open",
            "artifact": item.relative_to(repo).as_posix(),
        }
        for index, item in enumerate(transactions[:10], start=1)
    ]
    assert response["findings"] == expected_findings
    assert all(item.is_dir() for item in transactions)
    assert not (repo / ".agentic/rules.md").exists()

    recovered_exit, recovered = invoke(repo, "config-show")
    assert recovered_exit == 0, recovered
    assert (repo / ".agentic/rules.md").exists() is False
    assert not store.transactions.exists() or not list(store.transactions.iterdir())


def test_config_validate_preserves_malformed_transaction_material(
    tmp_path: Path,
) -> None:
    """@brief PR-STATE-002/003 validation never rewrites malformed residue."""
    repo = installed_repository(tmp_path)
    transaction = (
        repo
        / ".agentic"
        / ".runtime"
        / "transactions"
        / "TXN-malformed"
    )
    transaction.mkdir(parents=True)
    malformed = b"\xffnot a recovery plan\x00"
    (transaction / "plan.json").write_bytes(malformed)

    exit_code, response = invoke(repo, "config-validate")

    assert exit_code == 0, response
    assert response["data"]["pending_recovery_count"] == 1
    assert response["findings"][0]["artifact"] == (
        ".agentic/.runtime/transactions/TXN-malformed"
    )
    assert (transaction / "plan.json").read_bytes() == malformed


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
    observed = context["change_attribution"]["first_observed"]
    assert observed[0]["path"] == "later.py"
    assert observed[0]["observed_at"].endswith("Z")

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
        len(
            invoke(repo, "stage-show")[1]["data"]["run_summary"]
            ["change_attribution"]["findings"]
        )
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


def test_scope_revision_records_affected_completed_stages(tmp_path: Path) -> None:
    """@brief PR-EVOL-003/004 preserve affected prior work as one finding."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]

    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "alignment")[0] == 0
    assert (
        invoke(
            repo,
            "stage-skip",
            {"actor": "agent", "reason": "The original scope was already explicit."},
        )[0]
        == 0
    )
    assert invoke(repo, "stage-start", None, "requirement")[0] == 0

    requirement_id = "REQ-11111111111111111111111111111111"
    component_id = "COMP-22222222222222222222222222222222"
    run_path = run_dir / "run.md"
    run_text = run_path.read_text(encoding="utf-8")
    run_text = run_text.replace(
        "requirement_ids = []", f'requirement_ids = ["{requirement_id}"]', 1
    ).replace("component_ids = []", f'component_ids = ["{component_id}"]', 1)
    run_path.write_text(run_text, encoding="utf-8", newline="\n")

    prior_paths = (run_dir / "01-intake.md", run_dir / "02-alignment.md")
    prior_bytes = {path: path.read_bytes() for path in prior_paths}
    stale_revision = invoke(repo, "run-show")[1]["revision"]
    affected_work = ["src/retry.py", ".agentic/requirements/current.toml"]

    exit_code, revised = invoke(
        repo,
        "scope-revise",
        {
            "before": "Only retry recording.",
            "after": "Retry recording and cancellation recovery.",
            "actor": "agent",
            "reason": "Cancellation recovery is now in scope.",
            "affected_work": affected_work,
        },
    )

    assert exit_code == 0, revised
    assert len(revised["findings"]) == 1
    finding = revised["findings"][0]
    assert finding["code"] == "scope_revision_affected_work"
    assert finding["severity"] == "warning"
    assert finding["disposition"] == "open"
    assert finding["completed_or_skipped_stages"] == ["intake", "alignment"]
    assert finding["requirement_ids"] == [requirement_id]
    assert finding["component_ids"] == [component_id]
    assert finding["affected_work"] == affected_work
    assert all(path.read_bytes() == prior_bytes[path] for path in prior_paths)

    stage_show = invoke(repo, "stage-show")[1]["data"]
    persisted = stage_show["findings"]
    assert persisted == [finding]
    stage_path = run_dir / "03-requirement.md"
    run_after = run_path.read_bytes()
    stage_after = stage_path.read_bytes()

    conflict_exit, conflict = invoke(
        repo,
        "scope-revise",
        {
            "before": "Retry recording and cancellation recovery.",
            "after": "Conflicting scope.",
            "actor": "agent",
            "reason": "Use a stale revision to verify atomic refusal.",
            "affected_work": [],
        },
        expected_revision=stale_revision,
    )

    assert conflict_exit == 4, conflict
    assert conflict["error"]["code"] == "state_conflict"
    assert run_path.read_bytes() == run_after
    assert stage_path.read_bytes() == stage_after


def test_scope_revision_records_empty_affected_sets_truthfully(tmp_path: Path) -> None:
    """@brief PR-EVOL-003 keeps empty impact sets explicit and advisory."""
    repo = installed_repository(tmp_path)
    create_run(repo)

    exit_code, revised = invoke(
        repo,
        "scope-revise",
        {
            "before": "Initial scope.",
            "after": "Clarified scope.",
            "actor": "agent",
            "reason": "Clarify wording without identifying prior work.",
            "affected_work": [],
        },
    )

    assert exit_code == 0, revised
    finding = revised["findings"][0]
    assert finding["completed_or_skipped_stages"] == []
    assert finding["requirement_ids"] == []
    assert finding["component_ids"] == []
    assert finding["affected_work"] == []
    assert revised["operation_status"] == "completed"


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
    exit_code, changed = invoke(
        repo,
        "run-set-profile",
        {"actor": "agent", "reason": "Use the short profile for this Run."},
        "--profile",
        "short",
    )
    assert exit_code == 0
    assert changed["data"]["profile"] == "short"
    assert first["run_id"] in (repo / ".agentic" / "runs" / "context.toml").read_text(
        encoding="utf-8"
    )


def test_run_list_degrades_over_an_unreadable_run(tmp_path: Path) -> None:
    """@brief Unreadable Run state does not hide or block a healthy Run."""
    repo = installed_repository(tmp_path)
    unreadable = create_run(repo)
    healthy = create_run(repo, profile="short")
    unreadable_path = (
        repo / ".agentic" / "runs" / unreadable["run_id"] / "run.md"
    )
    corrupted_bytes = b"corrupt\n"
    select_exit, selected = invoke(repo, "run-select", None, unreadable["run_id"])
    assert select_exit == 0, selected

    run_path = unreadable_path.relative_to(repo).as_posix()
    original_load_document = FileWorkspace.load_document
    corrupted = False

    def load_then_corrupt_selected(
        workspace: FileWorkspace, path: str
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        """@brief Corrupt the selected Run after pointer resolution reads it."""
        nonlocal corrupted
        loaded = original_load_document(workspace, path)
        if path == run_path and not corrupted:
            unreadable_path.write_bytes(corrupted_bytes)
            corrupted = True
        return loaded

    with patch.object(FileWorkspace, "load_document", load_then_corrupt_selected):
        exit_code, listed = invoke(repo, "run-list")

    assert exit_code == 0, listed
    assert listed["data"]["has_more"] is False
    assert listed["data"]["next_cursor"] is None
    items = {item["id"]: item for item in listed["data"]["items"]}
    assert items[unreadable["run_id"]] == {
        "id": unreadable["run_id"],
        "status": "unreadable",
        "path": run_path,
        "selected": True,
    }
    assert items[healthy["run_id"]]["status"] == "active"
    assert items[healthy["run_id"]]["profile"] == "short"
    assert items[healthy["run_id"]]["current_stage"] == "intake"
    assert items[healthy["run_id"]]["ticket_summary"]
    assert items[healthy["run_id"]]["selected"] is False
    assert unreadable_path.read_bytes() == corrupted_bytes

    select_exit, selected = invoke(repo, "run-select", None, healthy["run_id"])
    show_exit, shown = invoke(repo, "run-show", None, "--run", healthy["run_id"])

    assert select_exit == 0, selected
    assert show_exit == 0, shown
    assert shown["run_id"] == healthy["run_id"]
    assert unreadable_path.read_bytes() == corrupted_bytes


def test_list_cursor_returns_the_next_page(tmp_path: Path) -> None:
    """@brief PR-MODEL-006/007 keep every bounded list item reachable."""
    repo = installed_repository(tmp_path)
    identities = write_list_artifacts(repo)

    for command, expected_ids in identities.items():
        first_exit, first = invoke(repo, command)
        second_exit, second = invoke(repo, command, None, "--cursor", "20")

        assert first_exit == second_exit == 0
        assert [item["id"] for item in first["data"]["items"]] == expected_ids[:20]
        assert first["data"]["has_more"] is True
        assert first["data"]["next_cursor"] == "20"
        assert [item["id"] for item in second["data"]["items"]] == expected_ids[20:]
        assert second["data"]["has_more"] is False
        assert second["data"]["next_cursor"] is None


def test_list_cursor_rejects_invalid_offsets(tmp_path: Path) -> None:
    """@brief PR-MODEL-006 rejects malformed, negative, and out-of-range cursors."""
    repo = installed_repository(tmp_path)
    write_list_artifacts(repo)

    for command in ("run-list", "requirement-list", "component-list"):
        for cursor in ("01", "-1", "twenty", "26"):
            exit_code, response = invoke(repo, command, None, "--cursor", cursor)

            assert exit_code == 2
            assert response["operation_status"] == "error"
            assert response["error"]["code"] == "invalid_input"
            assert response["error"]["field"] == "cursor"


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


def test_implicit_workflow_events_use_run_actor_with_operator_compatibility(
    tmp_path: Path,
) -> None:
    """@brief Implicit events inherit agent or default operator Run attribution."""
    agent_repo = installed_repository(tmp_path / "agent")
    created = create_run(agent_repo)
    attachment = tmp_path / "agent-evidence.txt"
    attachment.write_text("durable evidence\n", encoding="utf-8")
    assert (
        invoke(
            agent_repo,
            "run-set-profile",
            {"actor": "agent", "reason": "Use the short profile."},
            "--profile",
            "short",
        )[0]
        == 0
    )
    assert (
        invoke(
            agent_repo,
            "attachment-add",
            {
                "source": str(attachment),
                "purpose": "actor attribution proof",
                "content_type": "text/plain",
            },
        )[0]
        == 0
    )
    assert invoke(agent_repo, "stage-complete")[0] == 0
    assert invoke(agent_repo, "stage-start", None, "alignment")[0] == 0
    workspace = FileWorkspace(agent_repo)
    _, run_state, _ = workspace.load_document(
        f".agentic/runs/{created['run_id']}/run.md"
    )
    _, intake_state, _ = workspace.load_document(
        f".agentic/runs/{created['run_id']}/01-intake.md"
    )
    _, design_state, _ = workspace.load_document(
        f".agentic/runs/{created['run_id']}/04-design.md"
    )
    all_events = [
        *run_state["events"],
        *intake_state["events"],
        *design_state["events"],
    ]
    implicit = [
        event
        for event in all_events
        if event["event"]
        in {"stage_started", "stage_completed", "profile_changed", "attachment_added"}
    ]
    assert {event["event"] for event in implicit} == {
        "attachment_added",
        "profile_changed",
        "stage_completed",
        "stage_started",
    }
    assert {event["actor"] for event in implicit} == {"agent"}

    operator_repo = installed_repository(tmp_path / "operator")
    exit_code, operator_run = invoke(
        operator_repo,
        "run-create",
        {
            "ticket_text": "Retain default operator attribution.",
            "profile": "full",
            "work_type": "change",
        },
    )
    assert exit_code == 0, operator_run
    assert invoke(operator_repo, "stage-complete")[0] == 0
    assert invoke(operator_repo, "stage-start", None, "alignment")[0] == 0
    _, operator_state, _ = FileWorkspace(operator_repo).load_document(
        f".agentic/runs/{operator_run['run_id']}/run.md"
    )
    assert operator_state["actor"] == "operator"
    assert {
        event["actor"]
        for event in operator_state["events"]
        if event["event"] in {"stage_started", "stage_completed"}
    } == {"operator"}


def test_revisit_returns_the_later_stage_to_pending(tmp_path: Path) -> None:
    """@brief PR-EVOL-004 and PR-WORKFLOW-004 keep revisited Runs resumable."""
    repo = installed_repository(tmp_path)
    create_run(repo)

    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "alignment")[0] == 0

    exit_code, revisited = invoke(
        repo,
        "stage-revisit",
        {"actor": "agent", "reason": "Correct the earlier intake record."},
        "intake",
    )

    assert exit_code == 0, revisited
    run = invoke(repo, "run-show")[1]["data"]
    summaries = {item["name"]: item for item in run["state"]["stages"]}
    intake = invoke(repo, "stage-show", None, "--stage", "intake")[1]["data"]
    alignment = invoke(repo, "stage-show", None, "--stage", "alignment")[1][
        "data"
    ]
    assert run["metadata"]["current_stage"] == "intake"
    assert [
        item["name"] for item in run["state"]["stages"] if item["status"] == "active"
    ] == ["intake"]
    assert summaries["intake"]["status"] == intake["status"] == "active"
    assert summaries["alignment"]["status"] == alignment["status"] == "pending"
    alignment_events = alignment["stage_state"]["events"]
    assert alignment_events[-1] == {
        "actor": "agent",
        "event": "stage_returned_to_pending",
        "result": "Alignment returned to pending because Intake was revisited.",
        "time": alignment["stage_state"]["updated_at"],
    }

    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "alignment")[0] == 0
    run = invoke(repo, "run-show")[1]["data"]
    summaries = {item["name"]: item for item in run["state"]["stages"]}
    intake = invoke(repo, "stage-show", None, "--stage", "intake")[1]["data"]
    alignment = invoke(repo, "stage-show", None, "--stage", "alignment")[1][
        "data"
    ]
    assert run["metadata"]["current_stage"] == "alignment"
    assert [
        item["name"] for item in run["state"]["stages"] if item["status"] == "active"
    ] == ["alignment"]
    assert summaries["intake"]["status"] == intake["status"] == "completed"
    assert summaries["alignment"]["status"] == alignment["status"] == "active"


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
