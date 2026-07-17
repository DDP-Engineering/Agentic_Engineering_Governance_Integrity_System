#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_adopt_e2e.py
@brief End-to-end integration tests for ``waegis adopt`` (T5.2, milestone M5
       acceptance): real payload, real git, real wrapper scripts.
@details Marked ``integration`` (real subprocesses, still no network) and
         auto-skipped when git or the OS shell is absent. Proves the M5 shape on
         an existing Python repo: accepting T5.1's proposals yields a full green
         adoption with a generated workflow.toml, a commit on the adoption
         branch, and the real adoption-intake hand-off prompt; that an operator
         override (not the proposal) lands in workflow.toml; that a re-run
         resumes with every step skipped; and that a conflicting pre-existing
         CLAUDE.md is resolved exactly once, per the chosen decision, on disk and
         in the manifest.
@author Eng. Dan Dumitru Pasare
@date 2026-07-14
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

from waegis.commands.adopt import DEFAULT_ADOPTION_BRANCH, run_adopt
from waegis.commands.new import EXIT_OK, WORKFLOW_TOML_RELATIVE_PATH
from waegis.payload.locate import locate_payload
from waegis.payload.manifest import ManifestState, compute_drift, hash_file, load_manifest
from waegis.probes.runner import SubprocessCommandRunner
from waegis.repo import gitops

# CONSTANTS

# @brief Shell the wrapper smoke steps need on this host OS.
_REQUIRED_SHELL = "powershell" if os.name == "nt" else "bash"

# @brief Skip markers: integration tier + required real tools present.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="real git not available"),
    pytest.mark.skipif(shutil.which(_REQUIRED_SHELL) is None, reason=f"{_REQUIRED_SHELL} not available"),
]


# LOCAL HELPERS


def _make_python_repo(target: Path, *, extra_files: dict[str, str] | None = None) -> None:
    """
    @brief      Build an existing Python git repository (committed src/tests, a
                repo-local identity), optionally with extra files.
    @param[in]  target Directory to create the repo in.
    @param[in]  extra_files Optional ``{relative_path: content}`` extra files.
    @return     None
    @exception  RuntimeError If a git operation fails.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = SubprocessCommandRunner()
    target.mkdir(parents=True, exist_ok=True)
    init = gitops.init_repo(runner, target, initial_branch="main")
    assert init.ok, init.detail
    identity = gitops.set_identity(runner, target, "WAEGIS E2E", "waegis-e2e@example.com", local=True)
    assert identity.ok, identity.detail
    (target / "src").mkdir()
    (target / "src" / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (target / "tests").mkdir()
    (target / "tests" / "test_app.py").write_text("def test_add():\n    assert True\n", encoding="utf-8")
    for rel, content in (extra_files or {}).items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    add = gitops.add_all(runner, target)
    assert add.ok, add.detail
    committed = gitops.commit(runner, target, "existing project baseline")
    assert committed.ok, committed.detail


def _run(target: Path, home: Path, *, answers_path: Path | None = None, as_json: bool = False) -> tuple[int, str]:
    """
    @brief      Run ``waegis adopt`` non-interactively with the real runner
                against the real repo-checkout payload.
    @param[in]  target Existing repository directory.
    @param[in]  home WAEGIS home for journals (isolated per test).
    @param[in]  answers_path Optional prepared answers JSON file.
    @param[in]  as_json Emit the frozen run-summary JSON instead of human text.
    @return     ``(exit_code, captured_output)``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    out = io.StringIO()
    code = run_adopt(
        target,
        stream=out,
        answers_path=answers_path,
        non_interactive=True,
        as_json=as_json,
        runner=SubprocessCommandRunner(),
        home=home,
    )
    return code, out.getvalue()


def _write_answers(path: Path, answers: dict) -> Path:
    """
    @brief      Write a JSON answers file.
    @param[in]  path Destination path (.json).
    @param[in]  answers Answers mapping.
    @return     The written path.
    @exception  OSError If the file cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path.write_text(json.dumps(answers), encoding="utf-8")
    return path


# TESTS


def test_full_green_adoption_accepting_proposals(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      M5 acceptance happy path: proposals accepted -> full green;
                manifest with workflow.toml under ``generated``; a commit on the
                adoption branch; the real adoption-intake hand-off prompt.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If any acceptance artifact is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    home = tmp_path / "home"
    _make_python_repo(target)

    code, text = _run(target, home)
    assert code == EXIT_OK, text

    # Manifest: valid, drift-clean, workflow.toml moved to generated.
    load = load_manifest(target)
    assert load.state is ManifestState.VALID and load.manifest is not None
    assert WORKFLOW_TOML_RELATIVE_PATH in load.manifest.generated
    assert WORKFLOW_TOML_RELATIVE_PATH not in load.manifest.files
    assert load.manifest.mode == "adopt"
    drift = compute_drift(target, load.manifest)
    assert drift.modified == () and drift.missing == ()

    # workflow.toml: proposals (src/tests) confirmed as-is.
    document = tomllib.loads((target / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert document["source"]["roots"] == ["src"]
    assert document["tests"]["roots"] == ["tests"]

    # Git: committed on the adoption branch, clean tree.
    runner = SubprocessCommandRunner()
    assert gitops.current_branch(runner, target) == DEFAULT_ADOPTION_BRANCH
    assert gitops.status_porcelain(runner, target) == []
    assert gitops.head_commit(runner, target) is not None

    # Handoff: the real adoption prompt from the shipped cheat sheet.
    assert "agentic-adoption" in text
    assert "adoption-intake" in text

    # Journal: completed adopt run under the isolated home.
    journals = list((home / "journals").glob("*.json"))
    assert len(journals) == 1
    journal_doc = json.loads(journals[0].read_text(encoding="utf-8"))
    assert journal_doc["status"] == "completed" and journal_doc["mode"] == "adopt"


def test_operator_override_beats_the_proposal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Override path: the analysis proposes ``src`` but a scripted
                ``source_roots=["lib"]`` answer wins - ``lib`` (not ``src``) ends
                up in the generated workflow.toml, proving proposals are never
                auto-applied.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the proposal, not the override, was applied.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    home = tmp_path / "home"
    _make_python_repo(target)
    answers = _write_answers(tmp_path / "answers.json", {"source_roots": ["lib"]})

    code, text = _run(target, home, answers_path=answers)
    assert code == EXIT_OK, text

    document = tomllib.loads((target / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert document["source"]["roots"] == ["lib"]  # the override, not the proposed "src"
    assert (target / "lib" / ".gitkeep").is_file()  # the missing root was created on confirm


def test_completed_rerun_freshly_detects_every_step(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Re-running against the same TARGET auto-discovers the prior adopt
                journal and skips every step (plan §4 detect-and-skip / resume):
                17 results (net.proxy filtered out), all ``skipped``, ``ok`` true.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If any step re-ran or the summary drifted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    home = tmp_path / "home"
    _make_python_repo(target)
    first_code, first_text = _run(target, home)
    assert first_code == EXIT_OK, first_text
    head_before = gitops.head_commit(SubprocessCommandRunner(), target)

    second_code, second_text = _run(target, home, as_json=True)
    assert second_code == EXIT_OK, second_text
    envelope = json.loads(second_text)
    assert envelope["command"] == "adopt" and envelope["status"] == "ok"
    summary = envelope["result"]
    assert summary["mode"] == "adopt" and summary["ok"] is True and summary["stopped_at"] is None
    assert len(summary["results"]) == 17  # net.proxy filtered out (no clone URL)
    assert all(result["status"] in {"skipped", "done"} for result in summary["results"])
    assert any(result["status"] == "skipped" for result in summary["results"])

    # Nothing re-ran: no new commit.
    assert gitops.head_commit(SubprocessCommandRunner(), target) == head_before


@pytest.mark.parametrize("decision", ["keep-local", "take-payload", "write-new"])
def test_conflict_resolution_applies_the_chosen_decision(tmp_path, decision) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A pre-existing conflicting CLAUDE.md invokes the hook exactly once
                for that path, and each of keep-local / take-payload / write-new
                produces the correct on-disk result and manifest entry.
    @param[in]  tmp_path Pytest tmp fixture.
    @param[in]  decision The conflict decision under test.
    @return     None
    @exception  AssertionError If the decision was misapplied.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    home = tmp_path / "home"
    local_claude = "# Local CLAUDE notes\nThis is the operator's own file.\n"
    _make_python_repo(target, extra_files={"CLAUDE.md": local_claude})
    payload_claude_sha = hash_file(locate_payload() / "CLAUDE.md").sha256
    local_claude_sha = hash_file(target / "CLAUDE.md").sha256
    assert payload_claude_sha != local_claude_sha  # a genuine conflict

    answers = _write_answers(tmp_path / "answers.json", {"adoption_conflicts": {"CLAUDE.md": decision}})
    code, text = _run(target, home, answers_path=answers)
    assert code == EXIT_OK, text

    load = load_manifest(target)
    assert load.state is ManifestState.VALID and load.manifest is not None
    claude = target / "CLAUDE.md"
    sidecar = target / "CLAUDE.md.new"

    if decision == "take-payload":
        assert hash_file(claude).sha256 == payload_claude_sha
        assert "CLAUDE.md" in load.manifest.files
        assert not sidecar.exists()
    elif decision == "keep-local":
        assert hash_file(claude).sha256 == local_claude_sha
        assert "CLAUDE.md" in load.manifest.skipped
        assert "CLAUDE.md" not in load.manifest.files
        assert not sidecar.exists()
    else:  # write-new
        assert hash_file(claude).sha256 == local_claude_sha
        assert sidecar.is_file() and hash_file(sidecar).sha256 == payload_claude_sha
        assert "CLAUDE.md" in load.manifest.skipped

    # The hook fired exactly once for CLAUDE.md (journaled decision).
    journal_doc = json.loads(next((home / "journals").glob("*.json")).read_text(encoding="utf-8"))
    copy_step = next(r for r in journal_doc["steps"] if r["id"] == "deploy.adoption-copy")
    decisions = [key for key in copy_step["answers"] if key.startswith("conflict_decision:")]
    assert decisions == ["conflict_decision:CLAUDE.md"]
    assert copy_step["answers"]["conflict_decision:CLAUDE.md"] == decision


# END OF FILE
