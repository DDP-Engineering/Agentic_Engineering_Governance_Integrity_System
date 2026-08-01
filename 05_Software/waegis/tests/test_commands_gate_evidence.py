#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_gate_evidence.py
@brief Failed-gate evidence and gate-acceptance consent for ``deploy.gates``.
@details The evidence tests drive the step through the *real*
         ``SubprocessCommandRunner`` against synthetic gate scripts that emit
         known stdout/stderr and exit codes, so what is asserted is what a real
         child process actually produced — a fake runner cannot prove that the
         captured output, exit code, and working directory belong together.
         Volume-bound and redaction behaviour additionally uses the fake runner
         where byte-exact control of the captured streams is the point.
         Every context pins its own WAEGIS home under ``tmp_path``: the step
         writes evidence logs there, and a test must never reach the real one.
"""

# IMPORTS

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest
from waegis.commands.new import (
    ACCEPT_FAILING_GATES_KEY,
    GATE_OUTPUT_TAIL_LIMIT,
    SHARED_ANSWERS,
    SHARED_GATE_OUTCOMES,
    SHARED_HOME,
    SHARED_RUNNER,
    SHARED_TARGET,
    WORKFLOW_TOML_RELATIVE_PATH,
    build_new_catalog,
)
from waegis.engine import EngineContext, StepResult
from waegis.io.prompts import MissingAnswerError, ScriptedAsker
from waegis.probes.runner import SubprocessCommandRunner

from _fake_command_runner import FakeCommandRunner, failing_result

# CONSTANTS

# @brief The Wizard N catalog under test (steps are stateless data).
_CATALOG = build_new_catalog()

# @brief The gate step both wizards share.
_GATES = _CATALOG.get("deploy.gates")

# @brief A planted credential the synthetic gate prints, matched by the
#        repository's own configured secret pattern.
_PLANTED_SECRET = "token-999888777"

# @brief The repository's configured secret pattern (guardrails.secrets).
_SECRET_PATTERN = "token-[0-9]+"


# LOCAL HELPERS


def _write_workflow_toml(
    target: Path,
    *,
    test_cmds: str = "[]",
    secret_patterns: str = "[]",
) -> None:
    """
    @brief      Write a workflow.toml carrying the five schema-3 gates and the
                repository's own secret-scanning configuration.
    @param[in]  target Target repository root.
    @param[in]  test_cmds TOML literal for the enforced ``test`` gate.
    @param[in]  secret_patterns TOML literal for guardrails.secrets.patterns.
    @return     None
    @exception  OSError If the file cannot be written.
    """
    path = target / WORKFLOW_TOML_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "enforce" if test_cmds != "[]" else "disabled"
    secrets_mode = "enforce" if secret_patterns != "[]" else "disabled"
    path.write_text(
        '[gates.build]\nmode = "disabled"\ncommands = []\n\n'
        '[gates.typecheck]\nmode = "disabled"\ncommands = []\n\n'
        '[gates.lint]\nmode = "disabled"\ncommands = []\n\n'
        f'[gates.test]\nmode = "{mode}"\ncommands = {test_cmds}\n\n'
        '[gates.security]\nmode = "disabled"\ncommands = []\n\n'
        f'[guardrails.secrets]\nmode = "{secrets_mode}"\n'
        f"patterns = {secret_patterns}\n",
        encoding="utf-8",
    )


def _write_gate_script(target: Path, name: str, body: str) -> str:
    """
    @brief      Write a synthetic gate script into TARGET and return the shell
                command that runs it.
    @details    The interpreter path is quoted and slash-normalized so
                ``shlex.split`` (what ``_read_gates`` uses) reproduces it
                verbatim on Windows as well as POSIX; the script itself is
                named relatively, which is also what proves the step ran it
                with ``cwd`` set to TARGET.
    @param[in]  target Target repository root.
    @param[in]  name Script file name.
    @param[in]  body Python source for the script.
    @return     The command string to place in workflow.toml.
    @exception  OSError If the script cannot be written.
    """
    (target / name).write_text(body, encoding="utf-8")
    interpreter = Path(sys.executable).as_posix()
    return f'"{interpreter}" {name}'


def _ctx(
    target: Path,
    home: Path,
    *,
    runner=None,
    confirms=True,
    answers: dict | None = None,
) -> EngineContext:
    """
    @brief      Build a gate-step context with an activated ``StepResult``.
    @param[in]  target Target repository root.
    @param[in]  home Isolated WAEGIS home the evidence logs are written under.
    @param[in]  runner CommandRunner; the real subprocess runner by default.
    @param[in]  confirms ScriptedAsker confirm scripting.
    @param[in]  answers Scripted answers mapping (decision keys live here).
    @return     A ready :class:`EngineContext` with an active result.
    @exception  None
    """
    resolved = answers if answers is not None else {}
    return _begun(
        EngineContext(
            mode="new",
            asker=ScriptedAsker(resolved, confirms=confirms),
            shared={
                SHARED_TARGET: target,
                SHARED_RUNNER: runner if runner is not None else SubprocessCommandRunner(),
                SHARED_ANSWERS: resolved,
                SHARED_HOME: home,
            },
        )
    )


def _begun(ctx: EngineContext) -> EngineContext:
    """
    @brief      Activate a step result so the recording helpers work outside
                the engine runner.
    @param[in]  ctx The context to activate.
    @return     The same context, with an active result.
    @exception  None
    """
    ctx._begin(StepResult(step_id="deploy.gates"))
    return ctx


def _failures(ctx: EngineContext) -> list[dict]:
    """
    @brief      The failed-gate evidence records the step journalled.
    @param[in]  ctx The context the step ran in.
    @return     The recorded evidence list (empty when nothing failed).
    @exception  None
    """
    return ctx._require_current().answers.get("gate_failures", [])


# TESTS

# --- DPT-F03: failed-gate evidence -----------------------------------------------


def test_a_failing_gate_records_the_full_invocation_and_its_output(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A real failing gate child process is diagnosable from the
                recorded evidence alone: argv, resolved cwd, exit code,
                duration, timeout, both output streams, the log path, and the
                exact reproduction command.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If any part of the invocation is not recorded.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    command = _write_gate_script(
        target,
        "gate_fail.py",
        "import sys\n"
        "print('collected 3 items')\n"
        "sys.stderr.write('E   assert 1 == 2\\n')\n"
        "sys.exit(3)\n",
    )
    _write_workflow_toml(target, test_cmds=json.dumps([command]))
    ctx = _ctx(target, home, answers={ACCEPT_FAILING_GATES_KEY: True})

    _GATES.act(ctx)

    records = _failures(ctx)
    assert len(records) == 1
    record = records[0]
    assert record["gate"] == "test"
    assert record["argv"][-1] == "gate_fail.py"
    assert record["cwd"] == str(target)
    assert record["exit_code"] == 3
    assert record["found"] is True and record["timed_out"] is False
    assert record["timeout_seconds"] > 0
    assert record["duration_seconds"] >= 0.0
    assert "collected 3 items" in record["stdout_tail"]
    assert "assert 1 == 2" in record["stderr_tail"]
    assert record["truncated"] is False
    assert record["decision"] == "accepted"
    assert "gate_fail.py" in record["reproduce"] and str(target) in record["reproduce"]

    log = Path(record["log_path"])
    assert log.is_file() and log.parent == home / "logs" / "gates"
    body = log.read_text(encoding="utf-8")
    assert "collected 3 items" in body and "assert 1 == 2" in body
    assert "exit_code: 3" in body and str(target) in body


def test_a_passing_gate_records_its_outcome_and_no_evidence_volume(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A gate that passes stays cheap: the outcome is recorded, no
                evidence record is journalled, and no log file is written.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If a passing gate produces evidence volume.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    command = _write_gate_script(
        target, "gate_pass.py", "print('7 passed')\n"
    )
    _write_workflow_toml(target, test_cmds=json.dumps([command]))
    ctx = _ctx(target, home)

    _GATES.act(ctx)

    # The recorded label is the shlex round-trip of the configured command.
    label = " ".join(shlex.split(command))
    assert ctx.shared[SHARED_GATE_OUTCOMES][label] == "pass"
    assert _failures(ctx) == []
    assert ctx._require_current().answers["gate_accepted_failing"] == []
    assert not (home / "logs" / "gates").exists()
    assert _GATES.verify(ctx) is True


def test_recorded_output_is_bounded_and_flags_its_own_truncation(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Output larger than the inline bound is cut to the *tail* (where
                a failing suite prints its verdict), flagged as truncated, and
                kept whole only in the log file — so the journal and the
                ``--json`` envelope stay bounded without losing evidence.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If the bound, the flag, or the log is wrong.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["noisy-cmd"]')
    noise = "x" * (GATE_OUTPUT_TAIL_LIMIT * 2) + "THE-VERDICT"
    runner = FakeCommandRunner({("noisy-cmd",): failing_result(exit_code=1, stdout=noise)})
    ctx = _ctx(target, home, runner=runner, answers={ACCEPT_FAILING_GATES_KEY: True})

    _GATES.act(ctx)

    record = _failures(ctx)[0]
    assert len(record["stdout_tail"]) == GATE_OUTPUT_TAIL_LIMIT
    assert record["stdout_tail"].endswith("THE-VERDICT")
    assert record["truncated"] is True
    assert noise in Path(record["log_path"]).read_text(encoding="utf-8")


def test_a_planted_secret_never_reaches_the_journal_or_the_log(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A gate that leaks a credential matching the repository's *own*
                configured secret pattern has it redacted everywhere it would
                otherwise be persisted: both recorded tails and the log file.
    @details    The pattern comes from ``guardrails.secrets.patterns`` — the
                persisted form of the ``secret_patterns`` answer — rather than
                from a second list invented for redaction.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If the planted secret survives anywhere.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    command = _write_gate_script(
        target,
        "gate_leak.py",
        "import sys\n"
        f"print('auth header: {_PLANTED_SECRET}')\n"
        f"sys.stderr.write('retry with {_PLANTED_SECRET}\\n')\n"
        "sys.exit(1)\n",
    )
    _write_workflow_toml(
        target,
        test_cmds=json.dumps([command]),
        secret_patterns=json.dumps([_SECRET_PATTERN]),
    )
    ctx = _ctx(target, home, answers={ACCEPT_FAILING_GATES_KEY: True})

    _GATES.act(ctx)

    record = _failures(ctx)[0]
    assert _PLANTED_SECRET not in json.dumps(record)
    assert "[REDACTED]" in record["stdout_tail"] and "[REDACTED]" in record["stderr_tail"]
    assert "auth header:" in record["stdout_tail"]  # only the secret was removed
    log_body = Path(record["log_path"]).read_text(encoding="utf-8")
    assert _PLANTED_SECRET not in log_body
    assert "[REDACTED]" in log_body
    # The whole journalled step, not just the record, is clean.
    assert _PLANTED_SECRET not in json.dumps(ctx._require_current().to_dict())


def test_the_failure_notes_carry_the_log_path_and_reproduction_command(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Human output gets the same three facts the JSON result does:
                the one-line failure, the evidence log path, and the exact
                command that reproduces it. Notes are the shared carrier —
                they are printed live *and* journalled.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If any of the three facts is missing.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["broken-cmd"]')
    runner = FakeCommandRunner({("broken-cmd",): failing_result(exit_code=9, stderr="nope")})
    ctx = _ctx(target, home, runner=runner, answers={ACCEPT_FAILING_GATES_KEY: True})

    _GATES.act(ctx)

    notes = "\n".join(ctx._require_current().messages)
    record = _failures(ctx)[0]
    assert "gate 'test' FAILED: broken-cmd exited 9" in notes
    assert record["log_path"] in notes
    assert record["reproduce"] in notes


def test_evidence_survives_a_rejected_failing_gate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Refusing a failing gate fails the step by raising, but the
                evidence is recorded on the way out — a rejected gate is the
                case an operator most needs to diagnose.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If the raise loses the evidence.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["broken-cmd"]')
    runner = FakeCommandRunner({("broken-cmd",): failing_result(exit_code=1, stderr="boom")})
    ctx = _ctx(target, home, runner=runner, answers={ACCEPT_FAILING_GATES_KEY: False})

    with pytest.raises(RuntimeError):
        _GATES.act(ctx)

    record = _failures(ctx)[0]
    assert record["decision"] == "rejected"
    assert "boom" in record["stderr_tail"]
    assert Path(record["log_path"]).is_file()


# --- DPT-F04: gate-acceptance consent ---------------------------------------------


def test_blanket_consent_alone_cannot_accept_a_failing_gate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``--non-interactive`` (blanket confirms) does not waive a
                failing enforced gate: the step fails, naming the decision the
                answers file has to state.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If the gate is silently accepted, or the error
                does not name the missing decision.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["broken-cmd"]')
    runner = FakeCommandRunner({("broken-cmd",): failing_result(exit_code=1, stderr="boom")})
    ctx = _ctx(target, home, runner=runner, confirms=True, answers={})

    with pytest.raises(MissingAnswerError) as raised:
        _GATES.act(ctx)

    assert raised.value.key == ACCEPT_FAILING_GATES_KEY
    assert ACCEPT_FAILING_GATES_KEY in str(raised.value)
    # The evidence was still recorded before the decision was asked for.
    assert _failures(ctx)[0]["exit_code"] == 1


def test_the_explicit_decision_records_an_accepted_failing_gate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      With the decision stated, the failing gate is recorded as
                ``accepted-failing`` and separately listed, so a machine reader
                can tell "succeeded" from "succeeded with an accepted failure"
                without re-deriving it from the outcome map.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If the accepted state is not distinguishable.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["broken-cmd"]')
    runner = FakeCommandRunner({("broken-cmd",): failing_result(exit_code=1, stderr="boom")})
    ctx = _ctx(target, home, runner=runner, answers={ACCEPT_FAILING_GATES_KEY: True})

    _GATES.act(ctx)

    answers = ctx._require_current().answers
    assert answers["gate_outcomes"]["broken-cmd"] == "accepted-failing"
    assert answers["gate_accepted_failing"] == ["broken-cmd"]
    assert _failures(ctx)[0]["decision"] == "accepted"
    assert _GATES.verify(ctx) is True


def test_an_explicit_refusal_stops_the_run(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Stating the decision as ``false`` is a refusal, not a waiver:
                the step fails exactly as an interactive "no" does.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If a false decision does not stop the run.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["broken-cmd"]')
    runner = FakeCommandRunner({("broken-cmd",): failing_result(exit_code=1)})
    ctx = _ctx(target, home, runner=runner, answers={ACCEPT_FAILING_GATES_KEY: False})

    with pytest.raises(RuntimeError):
        _GATES.act(ctx)


def test_interactive_default_refuse_behaviour_is_unchanged(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      The interactive path is untouched: a scripted confirmation
                queue (what an operator's answers stand in for in tests) still
                decides acceptance in either direction, and the prompt states
                the consequence of saying yes.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If interactive acceptance or refusal changed.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["broken-cmd"]')
    responses = {("broken-cmd",): failing_result(exit_code=1, stderr="boom")}

    # proceed with gates? yes; run the test gate? yes; accept the failure? yes.
    accepted = _ctx(
        target, home, runner=FakeCommandRunner(responses), confirms=[True, True, True]
    )
    _GATES.act(accepted)
    assert accepted.shared[SHARED_GATE_OUTCOMES]["broken-cmd"] == "accepted-failing"

    rejected = _ctx(
        target, home, runner=FakeCommandRunner(responses), confirms=[True, True, False]
    )
    with pytest.raises(RuntimeError):
        _GATES.act(rejected)


def test_the_acceptance_prompt_states_the_consequence(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      An operator is told what saying yes means before they say it:
                the failure is recorded as accepted-failing and the deployment
                reports success with an accepted failure.
    @param[in]  tmp_path Pytest tmp fixture (TARGET and home).
    @return     None
    @exception  AssertionError If the consequence is not stated in the prompt.
    """
    target = tmp_path / "repo"
    target.mkdir()
    home = tmp_path / "home"
    _write_workflow_toml(target, test_cmds='["broken-cmd"]')
    prompts: list[str] = []

    class _RecordingAsker(ScriptedAsker):
        """@brief ScriptedAsker that records the prompts it is asked."""

        def confirm(self, prompt: str, *, default: bool = True, decision=None) -> bool:
            """@brief Record the prompt, then answer as the base class would."""
            prompts.append(prompt)
            return super().confirm(prompt, default=default, decision=decision)

    ctx = EngineContext(
        mode="new",
        asker=_RecordingAsker({ACCEPT_FAILING_GATES_KEY: True}, confirms=True),
        shared={
            SHARED_TARGET: target,
            SHARED_RUNNER: FakeCommandRunner(
                {("broken-cmd",): failing_result(exit_code=1)}
            ),
            SHARED_ANSWERS: {},
            SHARED_HOME: home,
        },
    )
    _begun(ctx)

    _GATES.act(ctx)

    acceptance = next(p for p in prompts if p.startswith("Gate command failed"))
    assert "recorded as accepted-failing" in acceptance
    assert "report success with an accepted failure" in acceptance


# END OF FILE
