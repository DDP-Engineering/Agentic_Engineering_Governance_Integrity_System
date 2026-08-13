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
@file    test_runtime_integrity_contracts.py
@brief   Verify Stage immutability, artifact schemas, and evidence truthfulness.
@details Covers AM-SCHEMA-004, AM-EVIDENCE-002/009-011, FS-STAGE-006,
         FS-EVIDENCE-002-003, CP-ENTRY-003, CP-ERROR-005, and TA-VERSION-002.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from aegis.infrastructure.workspace import FileWorkspace
from aegis.ports.workspace import WorkspaceError

from tests.test_execution_integrity import advance_to, configure_commands
from tests.test_project_knowledge_trace import requirement_data
from tests.test_run_stage_workflow import create_run, installed_repository, invoke


def _current_paths(repo: Path, run_id: str, stage_file: str) -> tuple[Path, Path]:
    """@brief Return the authoritative current Stage and Run paths."""
    run_directory = repo / ".agentic" / "runs" / run_id
    return run_directory / stage_file, run_directory / "run.md"


def _assert_invalid_transition_without_run_mutation(
    repo: Path,
    stage_path: Path,
    run_path: Path,
    command: str,
    data: dict[str, Any] | None = None,
    *arguments: str,
) -> dict[str, Any]:
    """@brief Assert one rejected operation preserves exact Stage and Run bytes."""
    before_stage = stage_path.read_bytes()
    before_run = run_path.read_bytes()

    exit_code, response = invoke(repo, command, data, *arguments)

    assert exit_code == 4, response
    assert response["error"]["code"] == "invalid_transition"
    assert stage_path.read_bytes() == before_stage
    assert run_path.read_bytes() == before_run
    return response


def _invoke_completed_stage_case(repo: Path, case: str) -> tuple[int, dict[str, Any]]:
    """@brief Invoke one representative current-Stage mutation path."""
    if case == "evidence":
        return invoke(
            repo,
            "evidence-add",
            {
                "kind": "manual",
                "actor": "agent",
                "procedure": "Inspect exact bytes.",
                "expected": "Bytes remain stable.",
                "actual": "Bytes remain stable.",
            },
        )
    if case == "finding_disposition":
        return invoke(
            repo,
            "finding-set-disposition",
            {
                "disposition": "resolved",
                "actor": "agent",
                "reason": "The observation was addressed.",
            },
            "--finding",
            "F1",
        )
    if case == "attachment":
        return invoke(
            repo,
            "attachment-add",
            {
                "source": "support.log",
                "purpose": "Retain raw supporting output.",
                "content_type": "text/plain",
            },
        )
    if case == "project_knowledge":
        return invoke(repo, "requirement-create", requirement_data())
    if case == "trace_selection":
        return invoke(
            repo,
            "trace-impacted",
            {"changed_files": ["src/retry.py"], "changed_tests": []},
        )
    raise AssertionError(f"Unknown completed Stage case: {case}")


@pytest.mark.parametrize(
    "case",
    (
        "evidence",
        "finding_disposition",
        "attachment",
        "project_knowledge",
        "trace_selection",
    ),
)
def test_completed_stage_rejects_mutation_and_preserves_exact_bytes(
    tmp_path: Path, case: str
) -> None:
    """@brief AM-STAGE/CP-ENTRY mutations require an active current Stage."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    stage_path, run_path = _current_paths(repo, created["run_id"], "01-intake.md")
    (repo / "support.log").write_bytes(b"raw supporting output\n")
    if case == "finding_disposition":
        added = invoke(
            repo,
            "finding-add",
            {
                "severity": "warning",
                "observation": "A bounded observation.",
                "consequence": "Review is required.",
            },
        )
        assert added[0] == 0, added[1]

    active_result = _invoke_completed_stage_case(repo, case)
    assert active_result[0] == 0, active_result[1]
    completed = invoke(repo, "stage-complete")
    assert completed[0] == 0, completed[1]
    before_stage = stage_path.read_bytes()
    before_run = run_path.read_bytes()

    exit_code, rejected = _invoke_completed_stage_case(repo, case)

    assert exit_code == 4, rejected
    assert rejected["error"]["code"] == "invalid_transition"
    assert stage_path.read_bytes() == before_stage
    assert run_path.read_bytes() == before_run


def test_completed_stage_rejects_execution_before_launch_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    """@brief CP-EXECUTION-002 runs only while the current Stage is active."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    created = create_run(repo)
    advance_to(repo, "check")
    stage_path, run_path = _current_paths(repo, created["run_id"], "05-check.md")
    active = invoke(
        repo,
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "pass",
    )
    assert active[0] == 0, active[1]
    completed = invoke(repo, "stage-complete")
    assert completed[0] == 0, completed[1]

    _assert_invalid_transition_without_run_mutation(
        repo,
        stage_path,
        run_path,
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "pass",
    )


def test_abandonment_remains_valid_while_active(tmp_path: Path) -> None:
    """@brief AM-ABANDON-001 records stopping context in the current Stage."""
    active_repo = installed_repository(tmp_path / "active")
    create_run(active_repo)
    abandoned = invoke(
        active_repo,
        "run-abandon",
        {"actor": "agent", "reason": "The request was withdrawn."},
    )
    assert abandoned[0] == 0, abandoned[1]


def _markdown_artifact(
    workspace: FileWorkspace, kind: str, schema: int | bool
) -> bytes:
    """@brief Render one structurally valid Markdown artifact for schema probes."""
    metadata: dict[str, Any] = {"schema": schema, "artifact_type": kind}
    state: dict[str, Any] = {}
    if kind == "run":
        metadata.update(
            {
                "id": "RUN-0123456789abcdef0123456789abcdef",
                "status": "active",
                "profile": "full",
                "work_type": "bug_fix",
                "current_stage": "intake",
            }
        )
        state.update(
            {"title": "Schema probe", "ticket_text": "Schema probe", "stages": []}
        )
    elif kind == "stage":
        metadata.update(
            {
                "run_id": "RUN-0123456789abcdef0123456789abcdef",
                "stage": "intake",
                "status": "active",
            }
        )
    elif kind == "component":
        metadata.update(
            {
                "id": "COMP-0123456789abcdef0123456789abcdef",
                "status": "active",
                "files": [],
                "requirement_ids": [],
            }
        )
    elif kind == "specification":
        metadata.update(
            {
                "requirement_id": "REQ-0123456789abcdef0123456789abcdef",
                "status": "active",
            }
        )
    elif kind == "adoption":
        metadata.update(
            {
                "id": "ADOPT-0123456789abcdef0123456789abcdef",
                "status": "active",
            }
        )
    elif kind == "abandonment":
        metadata.update(
            {
                "run_id": "RUN-0123456789abcdef0123456789abcdef",
                "status": "abandoned",
            }
        )
    return workspace.render_document(metadata, state, kind=kind)


@pytest.mark.parametrize(
    "kind", ("run", "stage", "component", "specification", "adoption", "abandonment")
)
@pytest.mark.parametrize("schema", (2, True))
def test_markdown_artifacts_reject_unsupported_schema_without_rewrite(
    tmp_path: Path, kind: str, schema: int | bool
) -> None:
    """@brief TA-VERSION-002 accepts exact integer schema 1 for every reader."""
    repo = installed_repository(tmp_path)
    workspace = FileWorkspace(repo)
    relative = f".agentic/schema-probes/{kind}.md"
    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    content = _markdown_artifact(workspace, kind, schema)
    target.write_bytes(content)

    with pytest.raises(WorkspaceError) as captured:
        workspace.load_document(relative)

    assert captured.value.code == "unsupported_schema"
    assert target.read_bytes() == content


def test_public_stage_read_classifies_unsupported_schema_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    """@brief CP-ERROR/EXIT expose unsupported artifact schemas through the CLI."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    stage_path, _ = _current_paths(repo, created["run_id"], "01-intake.md")
    unsupported = stage_path.read_bytes().replace(b"schema = 1", b"schema = 2", 1)
    stage_path.write_bytes(unsupported)

    exit_code, response = invoke(repo, "stage-show")

    assert exit_code == 4, response
    assert response["error"]["code"] == "unsupported_schema"
    assert stage_path.read_bytes() == unsupported


def _valid_automated_evidence() -> dict[str, Any]:
    """@brief Return one complete truthful imported automated execution record."""
    return {
        "kind": "automated",
        "command": ["python", "-m", "pytest", ".agentic/tests/test_retry.py"],
        "working_directory": ".",
        "outcome": "passed",
        "exit_status": 0,
        "observed_result": "One relevant test passed.",
        "tests": [".agentic/tests/test_retry.py::test_retry_history"],
    }


def _without(field: str) -> dict[str, Any]:
    value = _valid_automated_evidence()
    value.pop(field)
    return value


@pytest.mark.parametrize(
    "evidence",
    (
        _without("command"),
        {**_valid_automated_evidence(), "command": []},
        {**_valid_automated_evidence(), "command": ["python", ""]},
        _without("working_directory"),
        {**_valid_automated_evidence(), "working_directory": ""},
        _without("outcome"),
        {**_valid_automated_evidence(), "outcome": "unknown"},
        _without("exit_status"),
        {**_valid_automated_evidence(), "exit_status": True},
        {**_valid_automated_evidence(), "exit_status": 1},
        {**_valid_automated_evidence(), "outcome": "failed", "exit_status": 0},
        {**_valid_automated_evidence(), "outcome": "timed_out", "exit_status": 1},
        _without("observed_result"),
        {**_valid_automated_evidence(), "observed_result": ""},
        _without("tests"),
        {**_valid_automated_evidence(), "tests": []},
        {**_valid_automated_evidence(), "tests": "test_retry_history"},
        {**_valid_automated_evidence(), "tests": [""]},
    ),
)
def test_automated_evidence_rejects_incomplete_or_inconsistent_claims(
    tmp_path: Path, evidence: dict[str, Any]
) -> None:
    """@brief AM-EVIDENCE-002/009-011 reject claims without execution facts."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    stage_path, run_path = _current_paths(repo, created["run_id"], "01-intake.md")
    before_stage = stage_path.read_bytes()
    before_run = run_path.read_bytes()

    exit_code, response = invoke(repo, "evidence-add", deepcopy(evidence))

    assert exit_code == 2, response
    assert response["error"]["code"] == "invalid_input"
    assert stage_path.read_bytes() == before_stage
    assert run_path.read_bytes() == before_run


def test_complete_valid_evidence_kinds_remain_recordable(
    tmp_path: Path,
) -> None:
    """@brief Every accepted evidence kind remains recordable."""
    repo = installed_repository(tmp_path)
    create_run(repo)

    automated = invoke(repo, "evidence-add", _valid_automated_evidence())
    manual = invoke(
        repo,
        "evidence-add",
        {
            "kind": "manual",
            "actor": "agent",
            "procedure": "Inspect the rendered evidence entries.",
            "expected": "Both entries remain visible.",
            "actual": "Both entries remain visible.",
        },
    )
    imported = invoke(repo, "evidence-add", {"kind": "imported"})

    assert automated[0] == 0, automated[1]
    assert automated[1]["data"]["entry"]["outcome"] == "passed"
    assert automated[1]["data"]["entry"]["time"].endswith("Z")
    assert manual[0] == 0, manual[1]
    assert manual[1]["data"]["entry"]["kind"] == "manual"
    assert imported[0] == 0, imported[1]
    assert imported[1]["data"]["entry"]["kind"] == "imported"


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
