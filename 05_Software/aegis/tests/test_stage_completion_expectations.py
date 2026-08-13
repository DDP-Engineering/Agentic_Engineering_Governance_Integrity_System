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
@file    test_stage_completion_expectations.py
@brief   Verify structural-only advisory evaluation at Stage completion.
@details Covers CP-STAGE-004, FS-STAGE-015, REQ-FUNC-1b8843e3, and
         REQ-FUNC-cc16f4ab.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from aegis.infrastructure.codecs import parse_markdown_document
from aegis.infrastructure.workspace import FileWorkspace
from aegis.ports.workspace import WorkspaceError

from tests.test_run_stage_workflow import create_run, installed_repository, invoke


def _intake_path(repo: Path, run_id: str) -> Path:
    """@return Canonical Intake path for one synthetic Run."""
    return repo / ".agentic" / "runs" / run_id / "01-intake.md"


def _intake_document(
    repo: Path, run_id: str
) -> tuple[dict[str, object], dict[str, object]]:
    """@return Decoded Intake metadata and state for one synthetic Run."""
    path = _intake_path(repo, run_id)
    metadata, state, _ = parse_markdown_document(path.read_bytes(), path=str(path))
    return metadata, state


def _set_all_intake_sections(
    repo: Path, run_id: str, content: str = "Recorded"
) -> None:
    """@brief Record nonblank content in every author-writable Intake section."""
    sections = _intake_document(repo, run_id)[1]["sections"]
    assert isinstance(sections, dict)
    for section in sections:
        assert (
            invoke(
                repo,
                "stage-set-section",
                {"section": section, "content": content, "actor": "agent"},
            )[0]
            == 0
        )


def test_completion_evaluates_only_structural_intake_expectations(
    tmp_path: Path,
) -> None:
    """@brief Nonblank structural content closes without semantic judgments."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    _set_all_intake_sections(repo, created["run_id"], "Intentionally terse")

    exit_code, response = invoke(repo, "stage-complete")

    assert exit_code == 0
    assert response["data"]["status"] == "completed"
    assert response["findings"] == []
    metadata, _ = _intake_document(repo, created["run_id"])
    assert metadata["status"] == "completed"
    assert response["data"]["evaluated_expectation_count"] == 7


def test_blank_sections_are_reported_and_completion_remains_advisory(
    tmp_path: Path,
) -> None:
    """@brief Missing structural content remains visible without blocking closure."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)

    exit_code, response = invoke(repo, "stage-complete")

    assert exit_code == 0
    codes = {finding["code"] for finding in response["findings"]}
    assert "intake_inputs_unrecorded" in codes
    assert "intake_outputs_and_handoff_unrecorded" in codes
    metadata, _ = _intake_document(repo, created["run_id"])
    assert metadata["status"] == "completed"
    assert response["data"]["evaluated_expectation_count"] == len(codes)


def test_completion_publication_failure_preserves_exact_stage_and_run_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Atomic publication failure leaves Stage and Run bytes untouched."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_id = created["run_id"]
    run_path = repo / ".agentic" / "runs" / run_id / "run.md"
    stage_path = _intake_path(repo, run_id)
    before = (run_path.read_bytes(), stage_path.read_bytes())

    def reject_publish(*_args: object, **_kwargs: object) -> None:
        raise WorkspaceError("storage_error", "synthetic publication failure")

    monkeypatch.setattr(FileWorkspace, "publish", reject_publish)
    exit_code, response = invoke(repo, "stage-complete")

    assert exit_code == 70
    assert response["error"]["code"] == "storage_error"
    assert (run_path.read_bytes(), stage_path.read_bytes()) == before


def test_stale_completion_revision_rejects_before_mutation(tmp_path: Path) -> None:
    """@brief Optimistic concurrency still protects structural completion."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    run_id = created["run_id"]
    stage_path = _intake_path(repo, run_id)
    before = stage_path.read_bytes()

    exit_code, response = invoke(
        repo,
        "stage-complete",
        expected_revision="sha256:" + ("0" * 64),
    )

    assert exit_code == 4
    assert response["error"]["code"] == "state_conflict"
    assert stage_path.read_bytes() == before
