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

from waegis.commands.adopt import (
    ADOPT_OVER_EXISTING_INSTALL_KEY,
    DEFAULT_ADOPTION_BRANCH,
    build_adopt_catalog,
    run_adopt,
)
from waegis.commands.configure import run_configure
from waegis.commands.new import (
    EXIT_OK,
    NO_ACTIVE_RUN_MARKER,
    WORKFLOW_TOML_RELATIVE_PATH,
    _wrapper_invocation,
)
from waegis.payload.locate import locate_payload
from waegis.payload.manifest import ManifestState, compute_drift, hash_file, load_manifest
from waegis.probes.runner import SubprocessCommandRunner
from waegis.repo import gitops
from waegis.repo.workflow_toml import (
    GENERATOR_ANSWER_KEYS,
    WORKFLOW_FIELD_SPECS,
    derive_answers_from_workflow,
)

from _fake_command_runner import FakeCommandRunner, failing_result, ok_result

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
    """
    out = io.StringIO()
    code = run_adopt(
        target,
        stream=out,
        answers_path=answers_path,
        non_interactive=True,
        yes=True,
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
                one result per catalog step except the filtered ``net.proxy``
                (count derived from the catalog so a step addition cannot
                strand this test), all ``skipped``, ``ok`` true.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If any step re-ran or the summary drifted.
    """
    target = tmp_path / "repo"
    home = tmp_path / "home"
    _make_python_repo(target)
    first_code, first_text = _run(target, home)
    assert first_code == EXIT_OK, first_text
    head_before = gitops.head_commit(SubprocessCommandRunner(), target)

    # The second run finds a valid install manifest, so it hits the
    # default-refuse "adopt over an existing install?" question. Blanket
    # --yes/--non-interactive consent deliberately does not answer that one:
    # the decision has to be stated by name.
    rerun_answers = _write_answers(
        tmp_path / "rerun.json", {ADOPT_OVER_EXISTING_INSTALL_KEY: True}
    )
    second_code, second_text = _run(target, home, answers_path=rerun_answers, as_json=True)
    assert second_code == EXIT_OK, second_text
    envelope = json.loads(second_text)
    assert envelope["command"] == "adopt" and envelope["status"] == "ok"
    summary = envelope["result"]
    assert summary["mode"] == "adopt" and summary["ok"] is True and summary["stopped_at"] is None
    # One result per catalog step; net.proxy is filtered out (no clone URL).
    expected_steps = sum(1 for spec in build_adopt_catalog().ordered() if spec.id != "net.proxy")
    assert len(summary["results"]) == expected_steps
    assert all(result["status"] in {"skipped", "done"} for result in summary["results"])
    assert any(result["status"] == "skipped" for result in summary["results"])

    # Nothing re-ran: no new commit.
    assert gitops.head_commit(SubprocessCommandRunner(), target) == head_before


def test_adoption_persists_the_normalized_workflow_answers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Adoption records the configuration it just applied: the manifest
                carries the same three-part configuration block a fresh install
                writes, holding exactly the generator's own answer keys — the
                adopt-only answers (branch, conflict decisions) stay out of it.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the answers are missing, or the wrong ones.
    """
    target = tmp_path / "repo"
    home = tmp_path / "home"
    _make_python_repo(target)
    answers = _write_answers(
        tmp_path / "answers.json",
        {
            "source_roots": ["lib"],
            "adoption_branch": "agentic-adoption",
            "stage_form_retention": "versioned",
        },
    )

    code, text = _run(target, home, answers_path=answers)
    assert code == EXIT_OK, text

    load = load_manifest(target)
    assert load.state is ManifestState.VALID and load.manifest is not None
    configuration = load.manifest.configuration
    assert set(configuration) == {"answers", "generator_version", "generated_files"}
    assert configuration["generated_files"][WORKFLOW_TOML_RELATIVE_PATH]["sha256"] == hash_file(
        target / WORKFLOW_TOML_RELATIVE_PATH
    ).sha256

    stored = configuration["answers"]
    # A preset language answers the two "other" fields by itself, so the stored
    # set is the workflow table exactly - the same shape `new` writes.
    assert set(stored) == {spec.key for spec in WORKFLOW_FIELD_SPECS}
    assert set(stored).isdisjoint({"adoption_branch", "adoption_conflicts"})
    assert set(stored) <= GENERATOR_ANSWER_KEYS
    assert stored["source_roots"] == ["lib"]  # the override, not the proposal
    assert stored["stage_form_retention"] == "versioned"
    # What was stored is what the generated file says.
    assert stored == derive_answers_from_workflow(
        (target / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
    )


def test_adopted_repo_configures_repowise_without_restating_the_workflow(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      The reported field failure, end to end: after adoption, an
                answers file naming only RepoWise keys configures successfully,
                changes no workflow field, and leaves the generated file byte
                for byte as adoption wrote it.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the run failed or restated any field.
    """
    target = tmp_path / "repo"
    home = tmp_path / "home"
    _make_python_repo(target)
    assert _run(target, home)[0] == EXIT_OK
    workflow_before = (target / WORKFLOW_TOML_RELATIVE_PATH).read_bytes()

    repowise_only = _write_answers(tmp_path / "repowise.json", {"repowise_source": "disabled"})
    stream = io.StringIO()
    code = run_configure(
        target,
        stream=stream,
        answers_path=repowise_only,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=locate_payload(),
        runner=FakeCommandRunner(
            {
                _wrapper_invocation(target, "--help"): ok_result(),
                _wrapper_invocation(target, "run", "status", "--json"): failing_result(
                    exit_code=2, stderr=NO_ACTIVE_RUN_MARKER
                ),
            }
        ),
    )
    document = json.loads(stream.getvalue())
    assert code == EXIT_OK, document["messages"]
    assert document["plan"]["changes"] == []
    assert document["plan"]["workflow_content_changed"] is False
    assert document["result"]["configured"] is True
    assert (target / WORKFLOW_TOML_RELATIVE_PATH).read_bytes() == workflow_before


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
