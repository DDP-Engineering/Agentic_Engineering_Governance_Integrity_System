#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_machine_revision_contract.py
@brief   Verify mandatory optimistic concurrency for machine mutations.
@details Covers CP-REVISION-001 through 006, AC-PROTO-005, and TA-CONCURRENCY-001.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from aegis.application.operation_registry import ALL_OPERATIONS
from aegis.composition import create_dispatcher
from aegis.infrastructure.workspace import FileWorkspace
from aegis.interface.cli import run_cli

from tests.test_execution_integrity import configure_commands
from tests.test_project_knowledge_trace import requirement_data
from tests.test_run_stage_workflow import installed_repository


def invoke(
    repo: Path,
    operation: str,
    command: str,
    data: dict[str, Any] | None = None,
    *command_arguments: str,
    expected_revision: str | None = None,
    output_format: str = "json",
) -> tuple[int, dict[str, Any] | str]:
    """@brief Invoke one public CLI operation with an optional caller token."""
    arguments = ["--repo", str(repo), "--format", output_format]
    if expected_revision is not None:
        arguments.extend(("--expected-revision", expected_revision))
    arguments.extend((command, *command_arguments))
    stdin = io.StringIO()
    if data is not None:
        stdin = io.StringIO(
            json.dumps(
                {
                    "schema": "aegis.machine.input",
                    "schema_version": 1,
                    "operation": operation,
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
    rendered = stdout.getvalue()
    return exit_code, json.loads(rendered) if output_format == "json" else rendered


def create_run(repo: Path) -> dict[str, Any]:
    """@brief Create one Run through the exempt unique-identity operation."""
    exit_code, response = invoke(
        repo,
        "run.create",
        "run-create",
        {
            "ticket_text": "Require caller-observed mutation revisions.",
            "profile": "full",
            "work_type": "change",
            "actor": "agent",
        },
    )
    assert exit_code == 0
    assert isinstance(response, dict)
    return response


def show_stage(repo: Path, stage: str | None = None) -> dict[str, Any]:
    """@brief Read one Stage and return its machine response."""
    arguments = () if stage is None else ("--stage", stage)
    exit_code, response = invoke(repo, "stage.show", "stage-show", None, *arguments)
    assert exit_code == 0
    assert isinstance(response, dict)
    return response


def advance_to_check(repo: Path) -> None:
    """@brief Advance with the exact current/requested Stage revisions."""
    order = ("intake", "alignment", "requirement", "design", "check")
    for current, following in zip(order, order[1:]):
        shown = show_stage(repo)
        assert shown["stage"] == current
        completed_exit, _ = invoke(
            repo,
            "stage.complete",
            "stage-complete",
            expected_revision=shown["revision"],
        )
        assert completed_exit == 0
        pending = show_stage(repo, following)
        started_exit, _ = invoke(
            repo,
            "stage.start",
            "stage-start",
            None,
            following,
            expected_revision=pending["revision"],
        )
        assert started_exit == 0


def test_registry_declares_the_complete_machine_revision_policy() -> None:
    """@brief Every operation is explicitly applicable or contractually exempt."""
    read_only = {
        "help.show",
        "version.show",
        "config.show",
        "config.validate",
        "payload.verify",
        "run.list",
        "run.show",
        "stage.show",
        "requirement.show",
        "requirement.list",
        "requirement.validate",
        "component.show",
        "component.list",
        "component.validate",
        "component.find",
        "trace.validate",
        "execution.list",
        "adoption.show",
    }
    creates = {
        "run.create",
        "requirement.create",
        "component.create",
        "adoption.create",
    }
    expected = {operation: "exempt:read_only" for operation in read_only}
    expected.update({operation: "exempt:create" for operation in creates})
    expected.update(
        {
            "run.select": "exempt:working_context",
            "run.set_profile": "required:run",
            "run.abandon": "conditional:run",
            "scope.revise": "required:run",
            "stage.start": "required:stage",
            "stage.set_section": "required:stage",
            "stage.complete": "required:stage",
            "stage.skip": "required:stage",
            "stage.revisit": "required:stage",
            "evidence.add": "required:stage",
            "finding.add": "required:stage",
            "finding.set_disposition": "required:stage",
            "finding.waive": "required:stage",
            "decision.add": "required:stage",
            "attachment.add": "required:stage",
            "requirement.update": "required:requirement",
            "requirement.delete": "required:requirement",
            "specification.set": "required:requirement",
            "specification.delete": "required:requirement",
            "component.update": "required:component",
            "component.delete": "required:component",
            "trace.impacted": "required:stage",
            "execution.run": "required:stage",
            "adoption.set_section": "required:adoption",
            "adoption.complete": "required:adoption",
            "adoption.abandon": "required:adoption",
            "repository_init.plan": "exempt:separate_plan_protocol",
            "repository_init.apply": "exempt:separate_plan_protocol",
            "install.plan": "exempt:separate_plan_protocol",
            "install.apply": "exempt:separate_plan_protocol",
            "upgrade.plan": "exempt:separate_plan_protocol",
            "upgrade.apply": "exempt:separate_plan_protocol",
            "remove.plan": "exempt:separate_plan_protocol",
            "remove.apply": "exempt:separate_plan_protocol",
        }
    )
    actual = {}
    for entry in ALL_OPERATIONS:
        policy = getattr(entry, "machine_revision_policy", "undeclared")
        actual[entry.operation] = getattr(policy, "value", policy)

    assert actual == expected


def test_missing_run_revision_is_invalid_input_and_preserves_run_bytes(
    tmp_path: Path,
) -> None:
    """@brief A machine Run replacement cannot substitute its just-loaded token."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    run_path = run_dir / "run.md"
    design_path = run_dir / "04-design.md"
    before = (run_path.read_bytes(), design_path.read_bytes())

    exit_code, response = invoke(
        repo, "run.set_profile", "run-set-profile", None, "--profile", "short"
    )

    assert exit_code == 2
    assert isinstance(response, dict)
    assert response["error"]["code"] == "invalid_input"
    assert response["error"]["field"] == "expected_revision"
    assert (run_path.read_bytes(), design_path.read_bytes()) == before


def test_stage_matching_and_stale_revisions_preserve_exact_stage_and_run_bytes(
    tmp_path: Path,
) -> None:
    """@brief Matching Stage state publishes; stale state conflicts byte-exactly."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    original = show_stage(repo)
    data = {"section": "restated_ask", "content": "First observed state."}

    matching_exit, matching = invoke(
        repo,
        "stage.set_section",
        "stage-set-section",
        data,
        expected_revision=original["revision"],
    )
    assert matching_exit == 0
    assert isinstance(matching, dict)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    stage_path = run_dir / "01-intake.md"
    run_path = run_dir / "run.md"
    before_stale = (stage_path.read_bytes(), run_path.read_bytes())

    stale_exit, stale = invoke(
        repo,
        "stage.set_section",
        "stage-set-section",
        {"section": "restated_ask", "content": "Stale overwrite."},
        expected_revision=original["revision"],
    )

    assert stale_exit == 4
    assert isinstance(stale, dict)
    assert stale["error"]["code"] == "state_conflict"
    assert (stage_path.read_bytes(), run_path.read_bytes()) == before_stale


def test_missing_and_stale_project_revisions_preserve_project_and_workflow_bytes(
    tmp_path: Path,
) -> None:
    """@brief Requirement mutations require the caller-observed Requirement token."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    create_exit, requirement = invoke(
        repo, "requirement.create", "requirement-create", requirement_data()
    )
    assert create_exit == 0
    assert isinstance(requirement, dict)
    requirement_id = requirement["data"]["id"]
    shown_exit, shown = invoke(
        repo,
        "requirement.show",
        "requirement-show",
        None,
        "--requirement",
        requirement_id,
    )
    assert shown_exit == 0
    assert isinstance(shown, dict)
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    paths = (
        repo / ".agentic" / "requirements" / f"{requirement_id}.toml",
        run_dir / "01-intake.md",
        run_dir / "run.md",
    )
    before_missing = tuple(path.read_bytes() for path in paths)

    missing_exit, missing = invoke(
        repo,
        "requirement.update",
        "requirement-update",
        requirement_data(),
        "--requirement",
        requirement_id,
    )
    assert missing_exit == 2
    assert isinstance(missing, dict)
    assert missing["error"]["code"] == "invalid_input"
    assert tuple(path.read_bytes() for path in paths) == before_missing

    updated_data = requirement_data()
    updated_data["behavior"] = "A matching caller revision permits replacement."
    matching_exit, _ = invoke(
        repo,
        "requirement.update",
        "requirement-update",
        updated_data,
        "--requirement",
        requirement_id,
        expected_revision=shown["revision"],
    )
    assert matching_exit == 0
    before_stale = tuple(path.read_bytes() for path in paths)
    stale_exit, stale = invoke(
        repo,
        "requirement.update",
        "requirement-update",
        requirement_data(),
        "--requirement",
        requirement_id,
        expected_revision=shown["revision"],
    )
    assert stale_exit == 4
    assert isinstance(stale, dict)
    assert stale["error"]["code"] == "state_conflict"
    assert tuple(path.read_bytes() for path in paths) == before_stale


def test_missing_adoption_revision_is_invalid_input_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    """@brief Adoption replacements cannot use a revision loaded by the use case."""
    repo = installed_repository(tmp_path)
    create_exit, created = invoke(
        repo,
        "adoption.create",
        "adoption-create",
        {
            "scope": "retry history",
            "actor": "agent",
            "observed_implementation": [],
            "observed_tests": [],
            "unresolved_gaps": [],
        },
    )
    assert create_exit == 0
    assert isinstance(created, dict)
    adoption_id = created["data"]["id"]
    path = repo / ".agentic" / "adoptions" / f"{adoption_id}.md"
    before = path.read_bytes()

    exit_code, response = invoke(
        repo,
        "adoption.set_section",
        "adoption-set-section",
        {"section": "scope", "content": "Observed scope."},
        "--adoption",
        adoption_id,
    )

    assert exit_code == 2
    assert isinstance(response, dict)
    assert response["error"]["code"] == "invalid_input"
    assert response["error"]["field"] == "expected_revision"
    assert path.read_bytes() == before


def test_missing_attachment_revision_rejects_before_any_publication(
    tmp_path: Path,
) -> None:
    """@brief Attachment import requires current Stage authority before copying."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    source = repo / "external.log"
    source.write_bytes(b"external bytes\n")
    run_dir = repo / ".agentic" / "runs" / created["run_id"]
    stage_path = run_dir / "01-intake.md"
    run_path = run_dir / "run.md"
    before = (stage_path.read_bytes(), run_path.read_bytes(), sorted(run_dir.iterdir()))

    exit_code, response = invoke(
        repo,
        "attachment.add",
        "attachment-add",
        {
            "source": str(source),
            "purpose": "raw output",
            "content_type": "text/plain",
        },
    )

    assert exit_code == 2
    assert isinstance(response, dict)
    assert response["error"]["code"] == "invalid_input"
    after = (stage_path.read_bytes(), run_path.read_bytes(), sorted(run_dir.iterdir()))
    assert after == before


@pytest.mark.parametrize("stale", [False, True], ids=("missing", "stale"))
def test_execution_revision_is_rejected_before_process_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stale: bool
) -> None:
    """@brief Missing/stale Stage authority prevents the configured side effect."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    create_run(repo)
    advance_to_check(repo)
    observed = show_stage(repo)
    expected_revision = None
    if stale:
        evidence_exit, _ = invoke(
            repo,
            "evidence.add",
            "evidence-add",
            {
                "kind": "manual",
                "actor": "agent",
                "procedure": "inspect",
                "expected": "present",
                "actual": "present",
            },
            expected_revision=observed["revision"],
        )
        assert evidence_exit == 0
        expected_revision = observed["revision"]
    calls = 0

    def fail_if_launched(self: FileWorkspace, *args: Any, **kwargs: Any) -> Any:
        del self, args, kwargs
        nonlocal calls
        calls += 1
        raise AssertionError("configured command launched before revision rejection")

    monkeypatch.setattr(FileWorkspace, "execute_command", fail_if_launched)
    exit_code, response = invoke(
        repo,
        "execution.run",
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "pass",
        expected_revision=expected_revision,
    )

    assert exit_code == (4 if stale else 2)
    assert isinstance(response, dict)
    assert response["error"]["code"] == ("state_conflict" if stale else "invalid_input")
    assert calls == 0


def test_read_only_machine_operations_and_human_mutation_need_no_token(
    tmp_path: Path,
) -> None:
    """@brief Machine reads remain open and human mutation keeps planned behavior."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    read_exit, shown = invoke(repo, "stage.show", "stage-show")
    assert read_exit == 0
    assert isinstance(shown, dict)
    stage_path = repo / ".agentic" / "runs" / created["run_id"] / "01-intake.md"
    before = stage_path.read_bytes()

    human_exit, human = invoke(
        repo,
        "stage.set_section",
        "stage-set-section",
        {"section": "restated_ask", "content": "Human-mode mutation."},
        output_format="human",
    )

    assert human_exit == 0
    assert isinstance(human, str)
    assert stage_path.read_bytes() != before


def test_exceptional_abandonment_is_exempt_when_no_readable_run_target_exists(
    tmp_path: Path,
) -> None:
    """@brief Exceptional abandonment preserves unreadable Run bytes without a token."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_path = repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    unreadable = b"not a supported Run artifact\r\n"
    run_path.write_bytes(unreadable)

    exit_code, response = invoke(
        repo,
        "run.abandon",
        "run-abandon",
        {"actor": "agent", "reason": "Run state cannot be read safely."},
    )

    assert exit_code == 0
    assert isinstance(response, dict)
    assert response["data"]["exceptional"] is True
    assert run_path.read_bytes() == unreadable


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
