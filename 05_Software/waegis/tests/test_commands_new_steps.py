#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_new_steps.py
@brief Per-step offline tests for the Wizard N catalog (T4.3).
@details Strictly offline: every subprocess-backed step runs against the
         scripted ``FakeCommandRunner`` (which also records the ``cwd`` each
         invocation would have used) and every prompt against a
         ``ScriptedAsker``. Covers the exact wrapper invocation shapes for the
         smoke steps (``powershell -File run.ps1`` / ``bash run.sh``, run
         inside TARGET), the fresh-install `RUN-POINTER-MISSING` acceptance,
         the gates-recording contract, the pending repo-local git identity,
         the nested-work-tree confirmation, hooks/adapter presence, and the
         manifest ``generated`` amendment.
@details Gate tests updated for the 0.2.0 ``deploy.gates`` behavior (added a
         leading top-level "proceed?" confirm ahead of the per-gate prompts;
         see ``test_gates_top_level_decline_defers_everything_without_further_prompts``).
@author Eng. Dan Dumitru Pasare
@date 2026-07-18
@version 0.3.0
"""

# IMPORTS

from __future__ import annotations

import os
from pathlib import Path

import pytest

from waegis.commands.new import (
    HOOK_FILES,
    SHARED_ANSWERS,
    SHARED_GATE_OUTCOMES,
    SHARED_PENDING_IDENTITY,
    SHARED_RUNNER,
    SHARED_TARGET,
    WORKFLOW_TOML_RELATIVE_PATH,
    _amend_manifest_generated,
    build_new_catalog,
)
from waegis.commands.analyze import ADAPTER_DIR_NAMES
from waegis.engine import EngineContext, StepResult
from waegis.io.prompts import ScriptedAsker
from waegis.payload.manifest import FileEntry, Manifest, hash_file, read_manifest, write_manifest

from _fake_command_runner import FakeCommandRunner, failing_result, ok_result

# CONSTANTS

# @brief The Wizard N catalog under test (built once; steps are stateless data).
_CATALOG = build_new_catalog()


# LOCAL HELPERS


def _ctx(
    target: Path,
    runner: FakeCommandRunner,
    *,
    answers: dict | None = None,
    confirms: bool | list[bool] = True,
    shared_extra: dict | None = None,
) -> EngineContext:
    """
    @brief      Build a step-test context with an activated StepResult so the
                ``ctx.note``/``record_answer`` helpers work outside the runner.
    @param[in]  target Target path placed under the shared contract.
    @param[in]  runner Fake CommandRunner placed under the shared contract.
    @param[in]  answers Answers mapping for the shared contract.
    @param[in]  confirms ScriptedAsker confirm scripting.
    @param[in]  shared_extra Additional shared entries.
    @return     A ready :class:`EngineContext` with an active result.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    shared = {
        SHARED_TARGET: target,
        SHARED_RUNNER: runner,
        SHARED_ANSWERS: answers if answers is not None else {},
    }
    if shared_extra:
        shared.update(shared_extra)
    ctx = EngineContext(mode="new", asker=ScriptedAsker({}, confirms=confirms), shared=shared)
    ctx._begin(StepResult(step_id="test"))
    return ctx


def _write_workflow_toml(target: Path, *, test_cmds: str = "[]", lint_cmds: str = "[]") -> None:
    """
    @brief      Write a minimal workflow.toml carrying only the [gates] table.
    @param[in]  target Target repository root.
    @param[in]  test_cmds TOML literal for [gates].test.
    @param[in]  lint_cmds TOML literal for [gates].lint.
    @return     None
    @exception  OSError If the file cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.2.0
    """
    path = target / WORKFLOW_TOML_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "enforce" if test_cmds != "[]" or lint_cmds != "[]" else "disabled"
    path.write_text(
        f'[gates]\nmode = "{mode}"\ntest = {test_cmds}\nlint = {lint_cmds}\n',
        encoding="utf-8",
    )


# TESTS

# --- verify.cli-smoke ---------------------------------------------------------


def test_cli_smoke_windows_invocation_shape(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      On Windows the smoke step runs run.ps1 via ``powershell
                -NoProfile -ExecutionPolicy Bypass -File`` with ``--help``,
                inside TARGET (cwd), and verify passes on exit 0.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If the argv, cwd, or verify outcome is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    monkeypatch.setattr(os, "name", "nt")
    script = tmp_path / ".agentic" / "tools" / "run.ps1"
    expected = ("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "--help")
    runner = FakeCommandRunner({expected: ok_result(stdout="usage: aegis")})
    ctx = _ctx(tmp_path, runner)
    spec = _CATALOG.get("verify.cli-smoke")

    spec.act(ctx)

    assert runner.calls == [expected]
    assert runner.cwds == [str(tmp_path)]
    assert spec.verify(ctx) is True


def test_cli_smoke_posix_invocation_shape(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      On POSIX the smoke step runs run.sh via ``bash`` explicitly
                (the script requires bash: BASH_SOURCE + pipefail), inside
                TARGET, and verify fails on a non-zero exit.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If the argv, cwd, or verify outcome is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    monkeypatch.setattr(os, "name", "posix")
    script = tmp_path / ".agentic" / "tools" / "run.sh"
    expected = ("bash", str(script), "--help")
    runner = FakeCommandRunner({expected: failing_result(exit_code=2, stderr="Python 3.11+ was not found.")})
    ctx = _ctx(tmp_path, runner)
    spec = _CATALOG.get("verify.cli-smoke")

    spec.act(ctx)

    assert runner.calls == [expected]
    assert runner.cwds == [str(tmp_path)]
    assert spec.verify(ctx) is False


def test_cli_smoke_verify_false_without_result(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      verify.cli-smoke never trusts a run that did not happen: with
                no recorded result the verify is False.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If verify passes without an act.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = _ctx(tmp_path, FakeCommandRunner({}))

    assert _CATALOG.get("verify.cli-smoke").verify(ctx) is False


# --- verify.workflow-smoke ------------------------------------------------------


def test_workflow_smoke_accepts_fresh_install_missing_pointer(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A fresh install's coherent `RUN-POINTER-MISSING` response
                (non-zero exit, confirmed against the real template CLI) is the
                healthy outcome for the ``status`` smoke.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If the argv or the acceptance is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.2.0
    """
    monkeypatch.setattr(os, "name", "posix")
    _write_workflow_toml(tmp_path)
    expected = ("bash", str(tmp_path / ".agentic" / "tools" / "run.sh"), "status")
    runner = FakeCommandRunner(
        {expected: failing_result(exit_code=2, stderr="RUN-POINTER-MISSING: No active AEGIS run is selected")}
    )
    ctx = _ctx(tmp_path, runner)
    spec = _CATALOG.get("verify.workflow-smoke")

    spec.act(ctx)

    assert runner.calls == [expected]
    assert runner.cwds == [str(tmp_path)]
    assert spec.verify(ctx) is True


def test_workflow_smoke_zero_exit_requires_parseable_json(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A zero-exit ``status`` must print JSON-parseable output: valid
                JSON verifies, garbage does not.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If the parseability rule is not enforced.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    monkeypatch.setattr(os, "name", "posix")
    _write_workflow_toml(tmp_path)
    expected = ("bash", str(tmp_path / ".agentic" / "tools" / "run.sh"), "status")
    spec = _CATALOG.get("verify.workflow-smoke")

    good = _ctx(tmp_path, FakeCommandRunner({expected: ok_result(stdout='{"run_id": "r1", "stage": "intake"}')}))
    spec.act(good)
    assert spec.verify(good) is True

    bad = _ctx(tmp_path, FakeCommandRunner({expected: ok_result(stdout="not json at all")}))
    spec.act(bad)
    assert spec.verify(bad) is False


def test_workflow_smoke_runs_gates_only_when_configured_and_passed(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``gates run`` is invoked only when gates are configured
                non-empty AND every deploy.gates outcome was a pass; an
                accepted-failing outcome suppresses it.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If the gates-run guard misbehaves.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    monkeypatch.setattr(os, "name", "posix")
    _write_workflow_toml(tmp_path, test_cmds='["echo hi"]')
    wrapper = str(tmp_path / ".agentic" / "tools" / "run.sh")
    status_argv = ("bash", wrapper, "status")
    gates_argv = ("bash", wrapper, "gates", "run")
    responses = {
        status_argv: failing_result(exit_code=2, stderr="RUN-POINTER-MISSING"),
        gates_argv: ok_result(stdout="gates ok"),
    }
    spec = _CATALOG.get("verify.workflow-smoke")

    passing = _ctx(
        tmp_path,
        FakeCommandRunner(responses),
        shared_extra={SHARED_GATE_OUTCOMES: {"echo hi": "pass"}},
    )
    spec.act(passing)
    assert gates_argv in passing.shared[SHARED_RUNNER].calls
    assert spec.verify(passing) is True

    accepted_failing = _ctx(
        tmp_path,
        FakeCommandRunner(responses),
        shared_extra={SHARED_GATE_OUTCOMES: {"echo hi": "accepted-failing"}},
    )
    spec.act(accepted_failing)
    assert gates_argv not in accepted_failing.shared[SHARED_RUNNER].calls


# --- prereq.python --------------------------------------------------------------


def test_prereq_python_detects_and_reprobes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      prereq.python detect/verify follow the probe verdict, and a
                missing interpreter surfaces guidance notes instead of any
                privileged install attempt.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If detect/verify or the guidance notes are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = _CATALOG.get("prereq.python")
    good = _ctx(tmp_path, FakeCommandRunner({("py", "-3", "--version"): ok_result(stdout="Python 3.12.1")}))
    assert spec.detect(good) is True
    assert spec.verify(good) is True

    missing = _ctx(tmp_path, FakeCommandRunner({}))
    assert spec.detect(missing) is False
    spec.act(missing)
    assert spec.verify(missing) is False
    assert any("privileged installs" in message for message in missing._current.messages)


# --- prereq.git-identity ----------------------------------------------------------


def test_git_identity_detects_configured_identity(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A fully configured identity (name and e-mail) detects green.
    @param[in]  tmp_path Pytest tmp fixture (TARGET, exists).
    @return     None
    @exception  AssertionError If detect misreads the identity.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", str(tmp_path), "config", "user.name"): ok_result(stdout="Ada Lovelace\n"),
            ("git", "-C", str(tmp_path), "config", "user.email"): ok_result(stdout="ada@example.com\n"),
        }
    )
    ctx = _ctx(tmp_path, runner)

    assert _CATALOG.get("prereq.git-identity").detect(ctx) is True


def test_git_identity_records_pending_repo_local_pair_from_answers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      With no configured identity but answered
                git_user_name/git_user_email, act records the pending
                repo-local pair (plan §8.1 "or will be set repo-local") and
                verify accepts it.
    @param[in]  tmp_path Pytest tmp fixture (TARGET, exists).
    @return     None
    @exception  AssertionError If the pending path is not recorded/accepted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({})  # every git config read fails -> identity unset
    ctx = _ctx(tmp_path, runner, answers={"git_user_name": "Ada", "git_user_email": "ada@example.com"})
    spec = _CATALOG.get("prereq.git-identity")

    assert spec.detect(ctx) is False
    spec.act(ctx)

    assert ctx.shared[SHARED_PENDING_IDENTITY] == ("Ada", "ada@example.com")
    assert ctx._current.answers == {"git_user_name": "Ada", "git_user_email": "ada@example.com"}
    assert spec.verify(ctx) is True


def test_git_identity_guides_and_fails_without_answers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      With no identity and no answers, act only guides (manual
                automation) and verify stays red until the human acts.
    @param[in]  tmp_path Pytest tmp fixture (TARGET, exists).
    @return     None
    @exception  AssertionError If verify passes without identity or guidance
                is missing.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = _ctx(tmp_path, FakeCommandRunner({}))
    spec = _CATALOG.get("prereq.git-identity")

    spec.act(ctx)

    assert spec.verify(ctx) is False
    assert any("git config --global user.name" in message for message in ctx._current.messages)


# --- repo.target-path ---------------------------------------------------------------


def test_target_path_nested_worktree_needs_confirmation(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A TARGET whose parent is inside another work tree requires an
                explicit confirmation: declined -> the act raises (step
                fails); confirmed -> the directory is created.
    @param[in]  tmp_path Pytest tmp fixture (TARGET parent).
    @return     None
    @exception  AssertionError If the confirmation gate misbehaves.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "proj"
    nested = {
        ("git", "-C", str(tmp_path), "rev-parse", "--is-inside-work-tree"): ok_result(stdout="true\n")
    }
    spec = _CATALOG.get("repo.target-path")

    declined = _ctx(target, FakeCommandRunner(nested), confirms=[False])
    assert spec.detect(declined) is False
    with pytest.raises(RuntimeError):
        spec.act(declined)
    assert not target.exists()

    confirmed = _ctx(target, FakeCommandRunner(nested), confirms=[True])
    spec.act(confirmed)
    assert target.is_dir()
    assert spec.verify(confirmed) is True


# --- deploy.gates ---------------------------------------------------------------------


def test_gates_records_pass_and_accepted_empty(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A passing gate command and an accepted empty gate are both
                recorded (run inside TARGET), and verify accepts the recorded
                outcomes without requiring all-pass.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If outcomes or the cwd are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write_workflow_toml(tmp_path, test_cmds='["echo hi"]')
    runner = FakeCommandRunner({("echo", "hi"): ok_result(stdout="hi")})
    ctx = _ctx(tmp_path, runner)
    spec = _CATALOG.get("deploy.gates")

    spec.act(ctx)

    assert ctx.shared[SHARED_GATE_OUTCOMES] == {"echo hi": "pass", "lint (empty)": "accepted-empty"}
    assert ctx._current.answers["gate_outcomes"] == ctx.shared[SHARED_GATE_OUTCOMES]
    assert runner.cwds == [str(tmp_path)]
    assert spec.verify(ctx) is True


def test_gates_failing_command_must_be_explicitly_accepted(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A failing gate command is recorded as accepted-failing only on
                explicit confirmation; a refusal fails the step (raises).
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If acceptance recording misbehaves.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.1
    """
    _write_workflow_toml(tmp_path, test_cmds='["false-cmd"]')
    responses = {("false-cmd",): failing_result(exit_code=1, stderr="boom")}
    spec = _CATALOG.get("deploy.gates")

    # confirms: proceed with gates? yes; run gate? yes; accept failing? yes;
    # accept empty lint? yes.
    accepted = _ctx(tmp_path, FakeCommandRunner(responses), confirms=[True, True, True, True])
    spec.act(accepted)
    assert accepted.shared[SHARED_GATE_OUTCOMES]["false-cmd"] == "accepted-failing"
    assert spec.verify(accepted) is True

    # confirms: proceed with gates? yes; run gate? yes; accept failing? NO ->
    # the step fails.
    rejected = _ctx(tmp_path, FakeCommandRunner(responses), confirms=[True, True, False])
    with pytest.raises(RuntimeError):
        spec.act(rejected)


def test_gates_deferred_execution_is_recorded(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Declining to run a gate now records every command as deferred
                (a valid outcome per plan §7) without invoking anything.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If deferral is not recorded or a command ran.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.1
    """
    _write_workflow_toml(tmp_path, test_cmds='["echo hi"]')
    runner = FakeCommandRunner({})
    # confirms: proceed with gates? yes; run test gate now? NO; accept empty
    # lint? yes.
    ctx = _ctx(tmp_path, runner, confirms=[True, False, True])
    spec = _CATALOG.get("deploy.gates")

    spec.act(ctx)

    assert ctx.shared[SHARED_GATE_OUTCOMES]["echo hi"] == "deferred"
    assert runner.calls == []
    assert spec.verify(ctx) is True


def test_gates_top_level_decline_defers_everything_without_further_prompts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Declining the step's own top-level "proceed?" confirmation
                defers every configured gate command (and marks an empty gate
                accepted-empty) in one shot, with no further prompts and no
                command invoked — this is the AUTO-automation fix that lets
                the run finish instead of halting when gates are declined
                (unlike the old ASSISTED generic gate, which stopped the
                whole run on a decline).
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If deferral is not recorded, a command ran, or
                more confirms than the single top-level one were consumed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    _write_workflow_toml(tmp_path, test_cmds='["echo hi"]')
    runner = FakeCommandRunner({})
    # A single False must be enough: no per-gate follow-up prompt occurs.
    ctx = _ctx(tmp_path, runner, confirms=[False])
    spec = _CATALOG.get("deploy.gates")

    spec.act(ctx)

    assert ctx.shared[SHARED_GATE_OUTCOMES] == {"echo hi": "deferred", "lint (empty)": "accepted-empty"}
    assert runner.calls == []
    assert spec.verify(ctx) is True


# --- verify.hooks-present ----------------------------------------------------------------


def test_hooks_present_requires_all_hooks_and_adapters(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      All four real hook files plus every adapter directory must be
                present; removing any one turns detect/verify red.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If presence checking misbehaves.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    hooks_dir = tmp_path / ".agentic" / "hooks"
    hooks_dir.mkdir(parents=True)
    for hook in HOOK_FILES:
        (hooks_dir / hook).write_text("# hook\n", encoding="utf-8")
    for adapter in ADAPTER_DIR_NAMES:
        (tmp_path / adapter).mkdir()
    ctx = _ctx(tmp_path, FakeCommandRunner({}))
    spec = _CATALOG.get("verify.hooks-present")

    assert spec.detect(ctx) is True
    assert spec.verify(ctx) is True

    (hooks_dir / HOOK_FILES[0]).unlink()
    broken = _ctx(tmp_path, FakeCommandRunner({}))
    assert spec.detect(broken) is False
    assert spec.verify(broken) is False


# --- manifest amendment ----------------------------------------------------------------


def test_amend_manifest_moves_workflow_toml_to_generated(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      The amendment moves .agentic/workflow.toml out of ``files``
                into ``generated`` and is idempotent on a second call.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If the amendment or its idempotence is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _write_workflow_toml(tmp_path)
    workflow_entry = hash_file(tmp_path / WORKFLOW_TOML_RELATIVE_PATH)
    write_manifest(
        tmp_path,
        Manifest(
            manifest_version=1,
            product="aegis",
            payload_version="0.4.0",
            installed_at="2026-07-13T00:00:00Z",
            installed_by="waegis test",
            mode="new",
            files={WORKFLOW_TOML_RELATIVE_PATH: workflow_entry, "AGENTS.md": FileEntry(sha256="ab", size=2)},
        ),
    )

    _amend_manifest_generated(tmp_path)
    _amend_manifest_generated(tmp_path)  # idempotent

    manifest = read_manifest(tmp_path)
    assert WORKFLOW_TOML_RELATIVE_PATH not in manifest.files
    assert manifest.generated == (WORKFLOW_TOML_RELATIVE_PATH,)
    assert "AGENTS.md" in manifest.files


# --- repo.initial-commit ---------------------------------------------------------------


def test_initial_commit_detect_requires_head_not_just_clean_status(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      An empty porcelain status alone (which a *failed* git call also
                produces) must not detect green: a HEAD commit is required too
                — the reason gitops.head_commit exists.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If detect green-lights without a commit.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = _CATALOG.get("repo.initial-commit")
    status_argv = ("git", "-C", str(tmp_path), "status", "--porcelain")
    head_argv = ("git", "-C", str(tmp_path), "rev-parse", "HEAD")

    no_head = _ctx(tmp_path, FakeCommandRunner({status_argv: ok_result(stdout="")}))
    assert spec.detect(no_head) is False

    committed = _ctx(
        tmp_path,
        FakeCommandRunner({status_argv: ok_result(stdout=""), head_argv: ok_result(stdout="abc123\n")}),
    )
    assert spec.detect(committed) is True
    assert spec.verify(committed) is True


# END OF FILE
