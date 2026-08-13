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
@file    test_cli_protocol.py
@brief   Verify the runnable version 1 CLI and machine response spine.
@details Covers PR-PROTO, PR-MODEL-003-005, and AC-PROTO-001 through 003.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

import io
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from aegis.composition import create_dispatcher
from aegis.domain.results import OperationResult, ProtocolError
from aegis.interface.cli import run_cli
from aegis.interface.human_presenter import render_human

from tests.test_machine_revision_contract import (
    create_run,
    show_stage,
)
from tests.test_machine_revision_contract import invoke as invoke_revision
from tests.test_project_knowledge_trace import requirement_data
from tests.test_run_stage_workflow import installed_repository

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

RESPONSE_FIELDS = [
    "schema",
    "schema_version",
    "product",
    "product_version",
    "operation",
    "operation_id",
    "operation_status",
    "run_id",
    "stage",
    "revision",
    "outcome",
    "message",
    "data",
    "findings",
    "artifacts",
    "next_actions",
    "error",
    "truncated",
    "details_ref",
]


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------


class FixedUuidService:
    """@brief Return one deterministic UUID for protocol assertions."""

    def new_uuid(self) -> str:
        """@return A stable UUIDv4 string."""
        return "d9428888-f2d6-4e6f-9c2d-70e1965815b7"


def invoke(
    arguments: Sequence[str], dispatcher: Any | None = None
) -> tuple[int, str, str]:
    """
    @brief Execute the CLI against in-memory streams.
    @param[in] arguments CLI argument tokens.
    @param[in] dispatcher Optional injected application dispatcher.
    @return Exit code, standard output, and standard error.
    """
    stdout = io.StringIO()
    stderr = io.StringIO()
    application = create_dispatcher() if dispatcher is None else dispatcher
    exit_code = run_cli(
        list(arguments),
        stdout=stdout,
        stderr=stderr,
        dispatcher=application,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


def invoke_json(arguments: Sequence[str]) -> tuple[int, dict[str, Any], str, str]:
    """@brief Invoke machine mode and decode its one response line."""
    exit_code, stdout, stderr = invoke(["--format", "json", *arguments])
    return exit_code, json.loads(stdout), stdout, stderr


# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command,operation", [("help-show", "help.show"), ("version-show", "version.show")]
)
def test_implemented_commands_return_complete_one_line_json(
    command: str,
    operation: str,
) -> None:
    """@brief Verify exact machine framing and required version 1 fields."""
    exit_code, response, stdout, stderr = invoke_json([command])

    assert exit_code == 0
    assert stderr == ""
    assert stdout.endswith("\n")
    assert stdout.count("\n") == 1
    assert stdout.encode("utf-8").decode("utf-8") == stdout
    assert list(response) == RESPONSE_FIELDS
    assert response["schema"] == "aegis.machine.response"
    assert response["schema_version"] == 1
    assert response["product"] == "AEGIS"
    assert response["product_version"] == "1.0.0"
    assert response["operation"] == operation
    assert response["operation_status"] == "completed"
    assert response["error"] is None
    assert len(response["next_actions"]) <= 3


@pytest.mark.parametrize("command", ["help-show", "version-show"])
def test_human_and_json_present_the_same_implemented_result(command: str) -> None:
    """@brief Verify semantic parity for each implemented IP-01 operation."""
    human_exit, human, human_error = invoke([command])
    json_exit, machine, _, json_error = invoke_json([command])

    assert human_exit == json_exit == 0
    assert human_error == json_error == ""
    assert machine["message"] in human
    assert machine["operation"] in human
    assert machine["operation_status"] in human
    assert machine["product_version"] in human
    for key in machine["data"]:
        assert f"{key}:" in human


def test_version_human_and_json_results_have_the_same_semantics() -> None:
    """@brief Verify PR-PROTO-005 without freezing incidental human prose."""
    dispatcher = create_dispatcher(uuid_service=FixedUuidService())
    human_exit, human, human_error = invoke(["version-show"], dispatcher)
    json_exit, machine, _, json_error = invoke_json(["version-show"])

    assert human_exit == json_exit == 0
    assert human_error == json_error == ""
    assert "version.show" in human
    assert machine["product_version"] in human
    assert str(machine["data"]["protocol_version"]) in human
    assert machine["operation_status"] in human


def test_help_show_returns_bounded_catalog_and_operation_help() -> None:
    """@brief Verify catalog and exact-operation help use registry metadata."""
    exit_code, catalog, _, _ = invoke_json(["help-show"])
    detail_exit, detail, _, _ = invoke_json(
        ["help-show", "--operation", "version.show"]
    )

    assert exit_code == detail_exit == 0
    assert len(catalog["data"]["operations"]) == 48
    assert detail["data"]["operation"] == "version.show"
    assert detail["data"]["command"] == "version-show"
    assert detail["data"]["implemented"] is True


def test_exact_operation_help_exposes_complete_registry_owned_contract() -> None:
    """@brief Verify CP-MODEL-001 fields for exact-operation help."""
    expected = {
        "operation": "run.create",
        "command": "run-create",
        "purpose": "Create one Run from ticket text.",
        "required_arguments": [
            {
                "name": "--input <source>",
                "description": "Read ticket input from a JSON file or standard input.",
            }
        ],
        "optional_arguments": [],
        "result": "Created Run summary.",
        "example": "aegis run-create --input ticket.json",
        "implemented": True,
    }

    exit_code, response, _, stderr = invoke_json(
        ["help-show", "--operation", "run.create"]
    )
    command_exit, command_response, _, command_stderr = invoke_json(
        ["run-create", "--help"]
    )

    assert exit_code == command_exit == 0
    assert stderr == command_stderr == ""
    for data in (response["data"], command_response["data"]):
        machine_input = data.pop("machine_input")
        assert data == expected
        assert machine_input["envelope"] == {
            "schema": "aegis.machine.input",
            "schema_version": 1,
            "operation": "run.create",
            "data": "Object containing the data_fields below.",
        }
        assert machine_input["data_fields"]


def test_help_documents_revision_read_and_structured_input_envelope() -> None:
    """@brief Verify PR-MODEL-001 and CP-INPUT-004 render actionable help."""
    exit_code, response, _, _ = invoke_json(
        ["help-show", "--operation", "stage.set_section"]
    )

    assert exit_code == 0
    data = response["data"]
    assert data["required_arguments"][-1] == {
        "name": "--expected-revision <sha256>",
        "description": (
            "Use the revision returned by stage.show before this mutation."
        ),
    }
    assert data["revision"] == {
        "policy": "required:stage",
        "read_operation": "stage.show",
    }
    assert data["example"].startswith("aegis --expected-revision sha256:")
    assert data["machine_input"] == {
        "source": "Use --input <path> for UTF-8 JSON or --input - for stdin.",
        "envelope": {
            "schema": "aegis.machine.input",
            "schema_version": 1,
            "operation": "stage.set_section",
            "data": "Object containing the data_fields below.",
        },
        "data_fields": [
            {
                "name": "section",
                "type": "string",
                "required": True,
                "description": "Allowed section name from stage.show.",
            },
            {
                "name": "content",
                "type": "string",
                "required": True,
                "description": "Non-empty replacement section content.",
            },
            {
                "name": "actor",
                "type": "string",
                "required": False,
                "description": ("Actor replacing the section; defaults to operator."),
            },
        ],
        "constraints": [],
    }


@pytest.mark.parametrize(
    "arguments",
    [
        ["run-create"],
        ["run-set-profile", "--profile", "impossible"],
        ["config-show", "--future-input", "value"],
        ["version-show", "unexpected"],
    ],
)
def test_malformed_operation_arguments_report_invalid_input(
    arguments: list[str],
) -> None:
    """@brief Verify unavailable operations still enforce declared inputs."""
    exit_code, response, stdout, stderr = invoke_json(arguments)

    assert exit_code == 2
    assert stderr == ""
    assert stdout.count("\n") == 1
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == "invalid_input"


@pytest.mark.parametrize(
    "arguments",
    [
        ["execution-run", "--category", "test", "--name", "project"],
        ["stage-start", "review"],
        ["execution-list", "--stage", "review"],
    ],
)
def test_noncanonical_execution_categories_and_stages_are_invalid(
    arguments: list[str],
) -> None:
    """@brief Verify known enums reject values outside their final schema."""
    exit_code, response, _, stderr = invoke_json(arguments)

    assert exit_code == 2
    assert stderr == ""
    assert response["error"]["code"] == "invalid_input"


@pytest.mark.parametrize(
    "arguments",
    [
        ["execution-run", "--category", "tests", "--name", "project"],
        ["stage-start", "validation"],
        ["execution-list", "--stage", "check"],
    ],
)
def test_canonical_execution_categories_and_stages_reach_the_operation(
    arguments: list[str],
) -> None:
    """@brief Verify valid final enum values pass parsing and reach discovery."""
    exit_code, response, _, stderr = invoke_json(arguments)

    assert exit_code == 5
    assert stderr == ""
    assert response["error"]["code"] == "repository_error"


def test_envelope_marks_bounded_next_actions_as_truncated() -> None:
    """@brief Verify omitted bounded content is represented honestly."""
    result = OperationResult(
        product="AEGIS",
        product_version="1.0.0",
        operation="test.operation",
        operation_id="OP-test",
        operation_status="completed",
        outcome="success",
        message="Completed.",
        next_actions=(
            {"operation": "one"},
            {"operation": "two"},
            {"operation": "three"},
            {"operation": "four"},
        ),
    )

    envelope = result.to_envelope(schema_version=1)

    assert envelope["next_actions"] == [
        {"operation": "one"},
        {"operation": "two"},
        {"operation": "three"},
    ]
    assert envelope["truncated"] is True


def test_stage_show_returns_next_actions(tmp_path: Path) -> None:
    """@brief Stage resume reads propose one status-appropriate atomic action."""
    repo = installed_repository(tmp_path)
    create_run(repo)

    active = show_stage(repo)

    assert active["next_actions"][0]["operation"] == "stage.set_section"
    assert active["next_actions"][0]["arguments"] == {"section": "restated_ask"}
    assert active["next_actions"][0]["reason"]

    completed_exit, _ = invoke_revision(
        repo,
        "stage.complete",
        "stage-complete",
        expected_revision=active["revision"],
    )
    assert completed_exit == 0

    completed = show_stage(repo)

    assert completed["next_actions"][0]["operation"] == "stage.start"
    assert completed["next_actions"][0]["arguments"] == {"stage_name": "alignment"}
    assert completed["next_actions"][0]["reason"]


def test_required_revision_error_proposes_a_read(tmp_path: Path) -> None:
    """@brief A missing caller revision identifies the read that returns it."""
    repo = installed_repository(tmp_path)
    create_run(repo)

    exit_code, response = invoke_revision(
        repo,
        "stage.set_section",
        "stage-set-section",
        {"section": "restated_ask", "content": "Missing revision."},
    )

    assert exit_code == 2
    assert isinstance(response, dict)
    assert response["error"]["code"] == "invalid_input"
    assert response["error"]["field"] == "expected_revision"
    assert response["next_actions"] == [
        {
            "operation": "stage.show",
            "arguments": {},
            "reason": "Read the current Stage revision before retrying.",
        }
    ]

    requirement_id = "REQ-" + ("0" * 32)
    requirement_exit, requirement_error = invoke_revision(
        repo,
        "requirement.delete",
        "requirement-delete",
        None,
        "--requirement",
        requirement_id,
    )

    assert requirement_exit == 2
    assert isinstance(requirement_error, dict)
    assert requirement_error["next_actions"] == [
        {
            "operation": "requirement.show",
            "arguments": {"requirement": requirement_id},
            "reason": "Read the current Requirement revision before retrying.",
        }
    ]


def test_state_conflict_proposes_a_read(tmp_path: Path) -> None:
    """@brief A stale caller revision identifies the read that refreshes it."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    original = show_stage(repo)
    changed_exit, _ = invoke_revision(
        repo,
        "stage.set_section",
        "stage-set-section",
        {"section": "restated_ask", "content": "Current state."},
        expected_revision=original["revision"],
    )
    assert changed_exit == 0

    stale_exit, stale = invoke_revision(
        repo,
        "stage.set_section",
        "stage-set-section",
        {"section": "restated_ask", "content": "Stale state."},
        expected_revision=original["revision"],
    )

    assert stale_exit == 4
    assert isinstance(stale, dict)
    assert stale["error"]["code"] == "state_conflict"
    assert stale["next_actions"] == [
        {
            "operation": "stage.show",
            "arguments": {},
            "reason": "Read the current Stage revision before retrying.",
        }
    ]

    create_exit, requirement = invoke_revision(
        repo,
        "requirement.create",
        "requirement-create",
        requirement_data(),
    )
    assert create_exit == 0
    assert isinstance(requirement, dict)
    requirement_id = requirement["data"]["id"]
    show_exit, shown = invoke_revision(
        repo,
        "requirement.show",
        "requirement-show",
        None,
        "--requirement",
        requirement_id,
    )
    assert show_exit == 0
    assert isinstance(shown, dict)
    changed_data = requirement_data()
    changed_data["behavior"] = "The current Requirement state."
    changed_exit, _ = invoke_revision(
        repo,
        "requirement.update",
        "requirement-update",
        changed_data,
        "--requirement",
        requirement_id,
        expected_revision=shown["revision"],
    )
    assert changed_exit == 0

    stale_exit, stale = invoke_revision(
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
    assert stale["next_actions"] == [
        {
            "operation": "requirement.show",
            "arguments": {"requirement": requirement_id},
            "reason": "Read the current Requirement revision before retrying.",
        }
    ]


def test_explicit_repo_is_validated_while_repo_free_version_remains_available(
    tmp_path: Path,
) -> None:
    """@brief Verify an explicit repository option is never accepted and ignored."""
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    valid = tmp_path / "valid"
    (valid / ".git").mkdir(parents=True)
    (valid / ".agentic").mkdir()
    (valid / ".agentic" / "config.toml").write_text("", encoding="utf-8")

    invalid_exit, invalid_response, _, _ = invoke_json(
        ["--repo", str(invalid), "version-show"]
    )
    valid_exit, valid_response, _, _ = invoke_json(
        ["--repo", str(valid), "version-show"]
    )
    repo_free_exit, repo_free_response, _, _ = invoke_json(["version-show"])

    assert invalid_exit == 5
    assert invalid_response["error"]["code"] == "repository_error"
    assert valid_exit == repo_free_exit == 0
    assert valid_response["operation_status"] == "completed"
    assert repo_free_response["operation_status"] == "completed"


def test_human_root_help_renders_catalog_as_readable_bounded_lines() -> None:
    """@brief Verify the human catalog does not collapse into one huge line."""
    exit_code, stdout, stderr = invoke(["--help"])
    lines = stdout.splitlines()

    assert exit_code == 0
    assert stderr == ""
    assert len(lines) >= 52
    assert max(map(len, lines)) < 240
    assert any(line.startswith("  - help-show:") for line in lines)


def test_human_operation_help_preserves_arguments_and_input_fields() -> None:
    """@brief Exact help remains actionable while nested metadata stays bounded."""
    exit_code, stdout, stderr = invoke(
        ["help-show", "--operation", "stage.set_section"]
    )
    lines = stdout.splitlines()

    assert exit_code == 0
    assert stderr == ""
    assert max(map(len, lines)) < 240
    assert "required_arguments:" in lines
    assert "machine_input:" in lines
    assert "  data_fields:" in lines
    assert any("--expected-revision" in line for line in lines)
    assert any("section (string, required)" in line for line in lines)


def test_human_output_is_bounded(tmp_path: Path) -> None:
    """@brief Run and Stage reads stay compact without changing machine data."""
    repo = installed_repository(tmp_path)
    create_run(repo)

    for command in ("run-show", "stage-show"):
        exit_code, stdout, stderr = invoke(["--repo", str(repo), command])
        lines = stdout.splitlines()

        assert exit_code == 0
        assert stderr == ""
        assert len(stdout) < 8_000
        assert max(map(len, lines)) < 240
        assert any(line.startswith("Operation:") for line in lines)
        assert any(line.startswith("Status:") for line in lines)
        assert any(line.startswith("Run:") for line in lines)
        assert not any('"stage_state":{' in line for line in lines)


def test_human_output_preserves_bounded_response_guidance() -> None:
    """@brief Important response guidance remains readable around data summaries."""
    marker = "nested-value-that-must-not-be-dumped"
    result = OperationResult(
        product="AEGIS",
        product_version="1.0.0",
        operation="stage.show",
        operation_id="operation-id",
        operation_status="completed",
        message="Stage loaded.",
        data={
            "count": 3,
            "mode": "active",
            "state": {"items": [{"value": marker * 100}]},
        },
        run_id="RUN-123",
        stage="intake",
        revision="sha256:123",
        outcome="active",
        findings=(
            {
                "code": "missing-evidence",
                "label": "Missing evidence",
                "severity": "warning",
                "summary": "Attach an observed result.",
                "artifact": ".agentic/runs/RUN-123/01-intake.md",
            },
        ),
        artifacts=(
            {
                "action": "updated",
                "path": ".agentic/runs/RUN-123/01-intake.md",
            },
        ),
        next_actions=(
            {
                "operation": "stage.set_section",
                "arguments": {"section": "evidence"},
                "reason": "Record the missing evidence.",
            },
        ),
        error=ProtocolError(
            code="example-error",
            summary="An example bounded error.",
            path=".agentic/runs/RUN-123/01-intake.md",
        ),
        details_ref=".agentic/runs/RUN-123/01-intake.md",
    )

    output = render_human(result)
    lines = output.splitlines()

    assert max(map(len, lines)) < 240
    assert marker not in output
    assert "count: 3" in output
    assert "mode: active" in output
    assert any(line.startswith("Run:") and "RUN-123" in line for line in lines)
    assert any(line.startswith("Stage:") and "intake" in line for line in lines)
    assert any(line.startswith("Finding:") for line in lines)
    assert "Missing evidence" in output
    assert "warning" in output
    assert "Attach an observed result." in output
    assert any(line.startswith("Artifact:") and "updated" in line for line in lines)
    assert any(line.startswith("Error:") and "example-error" in line for line in lines)
    assert any(
        line.startswith("Next:") and "Record the missing evidence." in line
        for line in lines
    )
    assert output.count(".agentic/runs/RUN-123/01-intake.md") >= 2


@pytest.mark.parametrize(
    "arguments,expected_code,expected_exit",
    [
        (["not-a-command"], "invalid_input", 2),
        (["--protocol-version", "2", "version-show"], "unsupported_schema", 4),
        (["help-show", "--operation", "missing.operation"], "not_found", 3),
    ],
)
def test_invalid_requests_return_structured_errors_without_tracebacks(
    arguments: list[str],
    expected_code: str,
    expected_exit: int,
) -> None:
    """@brief Verify protocol exit classes and traceback containment."""
    exit_code, response, stdout, stderr = invoke_json(arguments)

    assert exit_code == expected_exit
    assert stderr == ""
    assert stdout.count("\n") == 1
    assert "Traceback" not in stdout
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == expected_code


def test_unexpected_exception_is_contained_as_internal_error() -> None:
    """@brief Verify the outer error boundary never leaks exception detail."""

    class BrokenDispatcher:
        def __init__(self) -> None:
            self._fallback = create_dispatcher()

        def dispatch(self, operation: str, inputs: dict[str, Any]) -> Any:
            raise RuntimeError("sensitive implementation detail")

        def error_result(self, **arguments: Any) -> Any:
            return self._fallback.error_result(**arguments)

    exit_code, stdout, stderr = invoke(
        ["--format", "json", "version-show"],
        BrokenDispatcher(),
    )
    response = json.loads(stdout)

    assert exit_code == 70
    assert stderr == ""
    assert response["error"]["code"] == "internal_error"
    assert "sensitive implementation detail" not in stdout
    assert "Traceback" not in stdout


def test_toml_dates_in_front_matter_are_readable(tmp_path: Path) -> None:
    """@brief TOML temporal values cross the protocol as stable strings."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_path = repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    original = run_path.read_text(encoding="utf-8")
    run_path.write_text(
        original.replace(
            "+++\n",
            "+++\n"
            "reviewed_on = 2026-08-12\n"
            "reviewed_at = 2026-08-12T09:10:11Z\n"
            "reviewed_time = 09:10:11\n",
            1,
        ),
        encoding="utf-8",
    )

    exit_code, response, stdout, stderr = invoke_json(["--repo", str(repo), "run-show"])

    assert exit_code == 0
    assert stderr == ""
    assert stdout.count("\n") == 1
    assert response["data"]["metadata"]["reviewed_on"] == "2026-08-12"
    assert response["data"]["metadata"]["reviewed_at"] == ("2026-08-12T09:10:11+00:00")
    assert response["data"]["metadata"]["reviewed_time"] == "09:10:11"


@pytest.mark.parametrize(
    "unsupported",
    [
        pytest.param(object(), id="unsupported-object"),
        pytest.param(float("nan"), id="non-finite-number"),
    ],
)
def test_unserializable_data_returns_a_structured_error(unsupported: Any) -> None:
    """@brief Presentation failures return the stable internal-error envelope."""

    class UnserializableDispatcher:
        def __init__(self) -> None:
            self._fallback = create_dispatcher()

        def dispatch(self, operation: str, inputs: dict[str, Any]) -> Any:
            result = self._fallback.dispatch(operation, inputs)
            return OperationResult(
                product=result.product,
                product_version=result.product_version,
                operation=result.operation,
                operation_id=result.operation_id,
                operation_status=result.operation_status,
                message=result.message,
                data={"unsupported": unsupported},
            )

        def error_result(self, **arguments: Any) -> Any:
            return self._fallback.error_result(**arguments)

    exit_code, stdout, stderr = invoke(
        ["--format", "json", "version-show"],
        UnserializableDispatcher(),
    )
    response = json.loads(stdout)

    assert exit_code == 70
    assert stderr == ""
    assert stdout.count("\n") == 1
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == "internal_error"
    assert "unsupported" not in response["data"]
    assert "Traceback" not in stdout


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
