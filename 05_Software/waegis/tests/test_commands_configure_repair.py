#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_configure_repair.py
@brief Lifecycle acceptance tests for transactional configure and repair.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path

from waegis.commands.configure import run_configure
from waegis.commands.new import (
    NO_ACTIVE_RUN_MARKER,
    WORKFLOW_TOML_RELATIVE_PATH,
    _amend_manifest_generated,
    _wrapper_invocation,
)
from waegis.commands.repair import run_repair
from waegis.payload.copier import copy_payload
from waegis.payload.locate import locate_payload
from waegis.payload.manifest import hash_file, read_manifest
from waegis.repo.workflow_toml import ALL_STAGES
from waegis.transaction import FileTransaction

from _fake_command_runner import FakeCommandRunner, failing_result

# CONSTANTS

_ANSWERS = {
    "source_roots": ["src", "app", "lib"],
    "test_roots": ["tests", "test"],
    "language": "python",
    "gate_build_cmds": [],
    "gate_typecheck_cmds": [],
    "gate_lint_cmds": [],
    "gate_test_cmds": [],
    "gate_security_cmds": [],
    "alignment_enabled": True,
    "baseline_guard_mode": "disabled",
    "baseline_minimum_completion_level": "baseline-usable",
    "coverage_mode": "disabled",
    "coverage_roots": [],
    "coverage_exclude": [],
    "source_changes_mode": "unrestricted",
    "alignment_protected_scope_mode": "disabled",
    "alignment_protected_scope_patterns": [],
    "stage_form_retention": "discard",
    "check_execution": "external",
    "gate_build_mode": "disabled",
    "gate_typecheck_mode": "disabled",
    "gate_lint_mode": "disabled",
    "gate_test_mode": "disabled",
    "gate_security_mode": "disabled",
    "secrets_mode": "disabled",
    "secret_patterns": [],
    "protected_paths_mode": "disabled",
    "protected_path_patterns": [],
    "protected_path_operations": [],
    "working_tree_mode": "unrestricted",
    "working_tree_blocked_patterns": [],
    "write_access_mode": "unrestricted",
    "write_access_stages": {stage: [] for stage in ALL_STAGES},
    "scope_mode": "unrestricted",
    "scope_allowed_roots": [],
    "delivery_mode": "disabled",
    "delivery_command_patterns": [],
}
_ENVELOPE_KEYS = {"schema_version", "command", "status", "exit_code", "plan", "result", "messages"}


# LOCAL HELPERS


def _write_answers(path: Path, data: dict[str, object]) -> Path:
    """@brief Write one JSON answers file and return its path."""
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _install(repo: Path) -> Path:
    """@brief Install the current payload with complete generated metadata."""
    payload = locate_payload()
    copy_payload(payload, repo, mode="new")
    _amend_manifest_generated(repo, answers=_ANSWERS)
    return payload


def _json(stream: io.StringIO) -> dict[str, object]:
    """@brief Parse and validate one command envelope."""
    document = json.loads(stream.getvalue())
    assert set(document) == _ENVELOPE_KEYS
    return document


# TESTS


def test_configure_change_and_no_op(tmp_path: Path) -> None:
    """@brief Configure owned fields, persist metadata last, then report a no-op."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    answers = _write_answers(
        tmp_path / "configure.json",
        {"source_roots": ["src"], "run_smoke": False},
    )
    stream = io.StringIO()
    code = run_configure(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    )
    assert code == 0
    document = _json(stream)
    assert document["command"] == "configure"
    assert document["status"] == "ok"
    assert document["result"]["configured"] is True
    assert 'roots = ["src"]' in (repo / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
    manifest = read_manifest(repo)
    assert manifest.configuration["answers"]["source_roots"] == ["src"]
    assert manifest.configuration["generated_files"][WORKFLOW_TOML_RELATIVE_PATH]["sha256"] == hash_file(
        repo / WORKFLOW_TOML_RELATIVE_PATH
    ).sha256

    stream = io.StringIO()
    assert run_configure(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    ) == 0
    assert _json(stream)["result"] == {"configured": False, "no_op": True}


def test_configure_requires_yes_for_automation(tmp_path: Path) -> None:
    """@brief JSON configuration plans but does not mutate without explicit yes."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    before = (repo / WORKFLOW_TOML_RELATIVE_PATH).read_bytes()
    answers = _write_answers(tmp_path / "configure.json", {"source_roots": ["src"], "run_smoke": False})
    stream = io.StringIO()
    code = run_configure(
        repo,
        stream=stream,
        answers_path=answers,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    )
    assert code == 1
    assert _json(stream)["status"] == "needs-input"
    assert (repo / WORKFLOW_TOML_RELATIVE_PATH).read_bytes() == before


def test_configure_gate_failure_rolls_back_file_and_manifest(tmp_path: Path) -> None:
    """@brief A failed selected gate restores workflow and manifest bytes."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    workflow = repo / WORKFLOW_TOML_RELATIVE_PATH
    manifest_path = repo / ".agentic/install-manifest.json"
    workflow_before, manifest_before = workflow.read_bytes(), manifest_path.read_bytes()
    answers = _write_answers(
        tmp_path / "configure.json",
        {
            "source_roots": ["src"],
            "gate_test_cmds": [["test-command"]],
            "gate_test_mode": "enforce",
            "run_gates": True,
            "run_smoke": False,
        },
    )
    stream = io.StringIO()
    code = run_configure(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    )
    assert code == 2
    assert _json(stream)["result"]["rolled_back"] is True
    assert workflow.read_bytes() == workflow_before
    assert manifest_path.read_bytes() == manifest_before


def test_repair_restores_missing_managed_file(tmp_path: Path) -> None:
    """@brief Repair restores a missing file only from matching payload bytes."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    missing = repo / "AGENTS.md"
    expected = missing.read_bytes()
    missing.unlink()
    answers = _write_answers(tmp_path / "repair.json", {"run_smoke": False})
    stream = io.StringIO()
    code = run_repair(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    )
    assert code == 0
    assert _json(stream)["result"]["repaired"] is True
    assert missing.read_bytes() == expected


def test_repair_modified_keep_local_relinquishes_ownership(tmp_path: Path) -> None:
    """@brief Explicit keep-local preserves bytes and records the path as skipped."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    managed = repo / "AGENTS.md"
    managed.write_text("local edit\n", encoding="utf-8")
    answers = _write_answers(
        tmp_path / "repair.json",
        {"repair_conflicts": {"AGENTS.md": "keep-local"}, "run_smoke": False},
    )
    stream = io.StringIO()
    assert run_repair(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    ) == 0
    assert managed.read_text(encoding="utf-8") == "local edit\n"
    manifest = read_manifest(repo)
    assert "AGENTS.md" not in manifest.files
    assert "AGENTS.md" in manifest.skipped


def test_repair_generated_drift_preserves_unowned_text_and_restamps(tmp_path: Path) -> None:
    """@brief Generated repair rewrites owned fields and preserves unowned text."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    workflow = repo / WORKFLOW_TOML_RELATIVE_PATH
    workflow.write_text(workflow.read_text(encoding="utf-8") + "\n# local unowned note\n", encoding="utf-8")
    answers = _write_answers(tmp_path / "repair.json", {"run_smoke": False})
    stream = io.StringIO()
    assert run_repair(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    ) == 0
    assert "# local unowned note" in workflow.read_text(encoding="utf-8")
    recorded = read_manifest(repo).configuration["generated_files"][WORKFLOW_TOML_RELATIVE_PATH]["sha256"]
    assert recorded == hash_file(workflow).sha256


def test_repair_missing_configuration_metadata_routes_to_configure(tmp_path: Path) -> None:
    """@brief Generated damage without answers stops and names configure."""
    repo = tmp_path / "repo"
    payload = locate_payload()
    copy_payload(payload, repo, mode="new")
    _amend_manifest_generated(repo)
    (repo / WORKFLOW_TOML_RELATIVE_PATH).unlink()
    answers = _write_answers(tmp_path / "repair.json", {"run_smoke": False})
    stream = io.StringIO()
    code = run_repair(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    )
    assert code == 1
    assert "configure" in " ".join(_json(stream)["messages"])


def test_repair_smoke_failure_rolls_back(tmp_path: Path) -> None:
    """@brief Smoke verification failure removes a tentatively restored file."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    missing = repo / "AGENTS.md"
    missing.unlink()
    runner = FakeCommandRunner(
        {
            _wrapper_invocation(repo, "--help"): failing_result(exit_code=1, stderr="boom"),
            _wrapper_invocation(repo, "status"): failing_result(exit_code=2, stderr=NO_ACTIVE_RUN_MARKER),
        }
    )
    stream = io.StringIO()
    code = run_repair(
        repo,
        stream=stream,
        answers_path=_write_answers(tmp_path / "repair.json", {}),
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=runner,
    )
    assert code == 2
    assert _json(stream)["result"]["rolled_back"] is True
    assert not missing.exists()


def test_repair_recovers_interrupted_transaction_before_detection(tmp_path: Path) -> None:
    """@brief A later repair invocation restores an interrupted transaction first."""
    repo = tmp_path / "repo"
    payload = _install(repo)
    managed = repo / "AGENTS.md"
    original = managed.read_bytes()
    transaction = FileTransaction.begin(repo, command="test", paths=("AGENTS.md",))
    transaction.mark("applying")
    managed.write_text("interrupted bytes\n", encoding="utf-8")
    stream = io.StringIO()
    assert run_repair(
        repo,
        stream=stream,
        answers_path=_write_answers(tmp_path / "repair.json", {"run_smoke": False}),
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
    ) == 0
    document = _json(stream)
    assert document["result"]["no_op"] is True
    assert transaction.state["id"] in document["plan"]["recovered_transactions"]
    assert managed.read_bytes() == original


# END OF FILE
