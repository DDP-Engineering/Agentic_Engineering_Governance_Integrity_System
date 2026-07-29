#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_new_e2e.py
@brief End-to-end integration tests for ``waegis new`` (T4.3, milestone M4
       acceptance): real payload, real git, real wrapper scripts.
@details Marked ``integration`` (real subprocesses — still no network: git is
         used only for local init/add/commit and the wrapper scripts run the
         bundled CLI). Deselect with ``-m "not integration"``; each test also
         auto-skips when git or the OS shell (powershell/bash) is absent.
         Proves the M4 acceptance shape: a scripted run from an empty
         directory to a committed, smoke-verified AEGIS repo with zero manual
         file editing, and a re-run that skips every step (resumable /
         idempotent).
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json
import os
import shutil
import tomllib
from pathlib import Path

import pytest

from waegis.commands.new import EXIT_OK, WORKFLOW_TOML_RELATIVE_PATH, build_new_catalog, run_new
from waegis.payload.manifest import ManifestState, compute_drift, load_manifest
from waegis.probes.runner import SubprocessCommandRunner
from waegis.repo import gitops
from waegis.repo.workflow_toml import ALL_STAGES, verify_workflow_invariants

# CONSTANTS

# @brief Shell the wrapper smoke steps need on this host OS.
_REQUIRED_SHELL = "powershell" if os.name == "nt" else "bash"

# @brief Skip markers: integration tier + required real tools present.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="real git not available"),
    pytest.mark.skipif(shutil.which(_REQUIRED_SHELL) is None, reason=f"{_REQUIRED_SHELL} not available"),
]

# @brief Complete scripted answer set: local init, Python preset, five disabled
#        gates, file-first interface defaults, and hermetic Git identity.
_ANSWERS: dict = {
    "source_roots": ["src"],
    "test_roots": ["tests"],
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
    "git_user_name": "WAEGIS E2E",
    "git_user_email": "waegis-e2e@example.com",
}


# LOCAL HELPERS


def _run(target: Path, home: Path, answers_file: Path, *, as_json: bool = False) -> tuple[int, str]:
    """
    @brief      Run ``waegis new`` non-interactively with the real subprocess
                runner against the real repo-checkout payload.
    @param[in]  target Target project directory.
    @param[in]  home WAEGIS home for journals (isolated per test).
    @param[in]  answers_file Prepared answers JSON file.
    @param[in]  as_json Emit the frozen run-summary JSON instead of human text.
    @return     ``(exit_code, captured_output)``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.2.0
    """
    out = io.StringIO()
    code = run_new(
        target,
        stream=out,
        answers_path=answers_file,
        non_interactive=True,
        as_json=as_json,
        runner=SubprocessCommandRunner(),
        home=home,
    )
    return code, out.getvalue()


@pytest.fixture()
def answers_file(tmp_path: Path) -> Path:
    """
    @brief      Write the complete scripted answers file for the run.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     Path to the answers JSON file.
    @exception  OSError If the file cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.1
    """
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(_ANSWERS), encoding="utf-8")
    return path


# TESTS


def test_full_green_run_installs_verifies_and_commits(tmp_path, answers_file) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      M4 acceptance happy path: scripted answers + real payload +
                real git -> full green run; manifest with workflow.toml under
                ``generated`` (and out of ``files``); invariant-clean
                workflow.toml; clean tree with a bootstrap commit; handoff
                text surfaced from the shipped cheat sheet.
    @param[in]  tmp_path Pytest tmp fixture.
    @param[in]  answers_file Prepared answers file fixture.
    @return     None
    @exception  AssertionError If any acceptance artifact is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "proj"
    home = tmp_path / "home"

    code, text = _run(target, home, answers_file)

    assert code == EXIT_OK, text

    # Manifest: valid, drift-clean, workflow.toml moved from files to generated.
    load = load_manifest(target)
    assert load.state is ManifestState.VALID and load.manifest is not None
    assert WORKFLOW_TOML_RELATIVE_PATH in load.manifest.generated
    assert WORKFLOW_TOML_RELATIVE_PATH not in load.manifest.files
    drift = compute_drift(target, load.manifest)
    assert drift.modified == () and drift.missing == ()

    # workflow.toml: parses and satisfies the plan §7 invariants for the answers.
    document = tomllib.loads((target / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8"))
    verify_workflow_invariants(document, source_roots=["src"], test_roots=["tests"])
    assert all(
        document["gates"][name] == {"mode": "disabled", "commands": []}
        for name in ("build", "typecheck", "lint", "test", "security")
    )
    assert (target / "src" / ".gitkeep").is_file() and (target / "tests" / ".gitkeep").is_file()
    gitignore_lines = (target / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".agentic/.workspace/" in gitignore_lines
    # `new` and `adopt` now write through a rollback journal, so the transaction
    # root must be ignored before the bootstrap commit can pick it up.
    assert ".agentic/.waegis-transactions/" in gitignore_lines
    assert not (target / ".agentic" / ".workspace").exists()

    # Git: work tree, clean, with the bootstrap commit.
    runner = SubprocessCommandRunner()
    assert gitops.is_work_tree(runner, target)
    assert gitops.status_porcelain(runner, target) == []
    assert gitops.head_commit(runner, target) is not None

    # Handoff: real first prompt and explicit disabled-gate status.
    assert "First prompt to try" in text
    assert "aegis run start feature" in text
    assert "config show --json" in text
    assert "gate execution is disabled explicitly" in text

    # Journal: completed run recorded under the isolated home.
    journals = list((home / "journals").glob("*.json"))
    assert len(journals) == 1
    journal_doc = json.loads(journals[0].read_text(encoding="utf-8"))
    assert journal_doc["status"] == "completed"
    assert journal_doc["target"] == str(target.resolve())


def test_completed_rerun_freshly_detects_every_step(tmp_path, answers_file) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Re-running against the same TARGET auto-discovers the prior
                journal and skips every step (plan §4 detect-and-skip /
                resume): the run-summary JSON shows one result per catalog
                step except the filtered ``net.proxy`` (count derived from
                the catalog so a step addition cannot strand this test), all
                ``skipped``, and ``ok`` true.
    @param[in]  tmp_path Pytest tmp fixture.
    @param[in]  answers_file Prepared answers file fixture.
    @return     None
    @exception  AssertionError If any step re-ran or the summary shape drifted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "proj"
    home = tmp_path / "home"
    first_code, first_text = _run(target, home, answers_file)
    assert first_code == EXIT_OK, first_text
    head_before = gitops.head_commit(SubprocessCommandRunner(), target)

    second_code, second_text = _run(target, home, answers_file, as_json=True)

    assert second_code == EXIT_OK, second_text
    envelope = json.loads(second_text)
    assert envelope["command"] == "new" and envelope["status"] == "ok"
    summary = envelope["result"]
    assert set(summary) == {"mode", "dry_run", "ok", "stopped_at", "results"}
    assert summary["mode"] == "new" and summary["ok"] is True and summary["stopped_at"] is None
    # One result per catalog step; net.proxy is filtered out (no clone URL).
    expected_steps = sum(1 for spec in build_new_catalog().ordered() if spec.id != "net.proxy")
    assert len(summary["results"]) == expected_steps
    assert all(result["status"] in {"skipped", "done"} for result in summary["results"])
    assert any(result["status"] == "skipped" for result in summary["results"])
    for result in summary["results"]:
        assert set(result) == {
            "id",
            "status",
            "detected",
            "acted",
            "verified",
            "started_at",
            "finished_at",
            "answers",
            "artifacts",
            "messages",
            "failure",
            "error",
        }

    # Nothing re-ran: no new commit, tree still clean.
    runner = SubprocessCommandRunner()
    assert gitops.head_commit(runner, target) == head_before
    assert gitops.status_porcelain(runner, target) == []


# END OF FILE
