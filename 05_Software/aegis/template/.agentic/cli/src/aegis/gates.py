#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file gates.py
@brief Gate execution helpers for workflow validation commands.
@details Executes build, typecheck, lint, test, and security in deterministic
         order. Disabled groups are reported as disabled and never as passed.
@details Simple-command argv splitting (0.2.0, code-review follow-up) now uses
         a `shlex.shlex` lexer instead of `shlex.split(..., posix=os.name !=
         "nt")`: the previous non-POSIX mode on Windows only grouped a quoted
         span when the quote started the token, corrupting a quoted argument
         containing a space.
@details Command failures (0.3.0, analysis-review follow-up) can no longer
         escape as raw tracebacks: a missing/unlaunchable executable (argv
         mode used to raise `FileNotFoundError` while shell mode returned
         non-zero) and a timeout (`subprocess.TimeoutExpired`, both modes)
         are synthesized into failed `CompletedProcess` results (exit 127 and
         124 respectively), so they end as recorded failing gate evidence.
@details Gate subprocesses (1.2.0) execute without the run-scoped graph lock.
         The graph transaction is reacquired only to verify the captured stage,
         allocate evidence identifiers, and publish the collected results.
@details Gate evidence is superseded on publication the way check evidence
         already was, so a fixed gate can go green again instead of keeping its
         failure active forever, and each gate record carries an `output_log`
         path so a failure is diagnosable from the evidence itself rather than
         only from the journal, which has no CLI read surface.
"""

# IMPORTS

from __future__ import annotations

from dataclasses import dataclass
import os
import shlex
import subprocess
from pathlib import Path

from .config import GATE_ORDER, WorkflowConfig
from .models import Evidence, Graph
from .store import (
    GraphConflictError,
    add_evidence,
    graph_transaction,
    load_graph,
    next_evidence_id,
    run_dir,
    save_graph_with_journal_events,
)
from .waivers import Blocker, active_waiver, state_digests

# PUBLIC API


@dataclass(frozen=True)
class GateExecutionOutcome:
    """
    @brief Describe the result of one explicit or aggregate gate execution.
    @param[in] execution_status Distinct execution state.
    @param[in] executed_count Number of commands launched.
    @param[in] reason Human-readable explanation for a nothing-ran outcome.
    @param[in] exit_code Aggregate process or policy result.
    """

    execution_status: str
    executed_count: int
    reason: str
    exit_code: int


def run_gates(
    repo_root: Path,
    run_id: str,
    config: WorkflowConfig,
    names: list[str] | None = None,
) -> int:
    """
    @brief      Execute the selected gate groups in order and persist gate
                evidence.
    @param[in]  repo_root Repository root the gate commands run in.
    @param[in]  run_id Already resolved run ID selected by CLI orchestration.
    @param[in]  config Validated workflow configuration. Each gate group's own
                `timeout` (defaulting to `DEFAULT_GATE_TIMEOUT_SECONDS` when
                unconfigured) applies to every command in that group.
    @param[in]  names Gate group names to run; defaults to all gates in
                `GATE_ORDER` when omitted.
    @return     Aggregate exit code: 0 when no unwaived gate failure remains,
                otherwise the last unwaived failing command's return code
                encountered in gate order.
    @exception  ValueError If a requested gate name is unsupported.
    @exception  GraphConflictError If the graph's captured stage advanced
                before the collected evidence could be published.
    """
    return run_gates_with_outcome(
        repo_root,
        run_id,
        config,
        names,
        explicit_execution=False,
    ).exit_code


def run_gates_with_outcome(
    repo_root: Path,
    run_id: str,
    config: WorkflowConfig,
    names: list[str] | None = None,
    *,
    explicit_execution: bool = True,
) -> GateExecutionOutcome:
    """
    @brief Execute gates and return their explicit execution outcome.
    @param[in] repo_root Repository root the gate commands run in.
    @param[in] run_id Already resolved run ID selected by CLI orchestration.
    @param[in] config Validated workflow configuration.
    @param[in] names Gate group names to run, or every group when omitted.
    @param[in] explicit_execution Whether zero launches are an explicit
                execution request rather than aggregate verification.
    @return Gate outcome, including `nothing-ran` when no command launched.
    @exception ValueError If a requested gate name is unsupported.
    @exception GraphConflictError If the captured stage advanced before
               collected evidence could be published.
    @details Only explicit execution emits a `nothing-ran` outcome event. The
             compatibility wrapper :func:`run_gates` retains its integer
             aggregate-verification contract and reports an all-disabled
             policy as `not-enforced` without that event.
    """
    unknown = sorted(set(names or ()) - set(GATE_ORDER))
    if unknown:
        raise ValueError(
            f"Unknown gate name(s): {', '.join(unknown)}. "
            f"Expected one or more of {', '.join(GATE_ORDER)}."
        )
    graph = load_graph(repo_root, run_id)
    captured_stage = graph.stage
    captured_record = graph.stage_records.get(captured_stage)
    captured_revision = (
        (captured_record.revision, captured_record.digest)
        if captured_record is not None
        else None
    )
    selected = [name for name in GATE_ORDER if not names or name in names]
    plan: list[tuple[str, str | None, int]] = []
    for name in selected:
        group = getattr(config.gates, name)
        if group.mode == "disabled":
            plan.append((name, None, group.timeout))
        else:
            plan.extend(
                (name, command, group.timeout) for command in group.commands
            )

    completed: list[
        tuple[str, str | None, subprocess.CompletedProcess[str] | None]
    ] = []
    for name, command, gate_timeout in plan:
        if command is None:
            completed.append((name, None, None))
            continue
        result = _run_command(repo_root, command, gate_timeout)
        completed.append((name, command, result))

    with graph_transaction(repo_root, graph):
        current_record = graph.stage_records.get(captured_stage)
        current_revision = (
            (current_record.revision, current_record.digest)
            if current_record is not None
            else None
        )
        if graph.stage != captured_stage or current_revision != captured_revision:
            raise GraphConflictError(graph.run_id)
        log_root = run_dir(repo_root, graph.run_id) / "evidence" / "logs"
        log_root.mkdir(parents=True, exist_ok=True)
        ordinals: dict[str, int] = {}
        events: list[tuple[str, dict[str, object]]] = []
        for name, command, result in completed:
            if command is None:
                events.append(
                    ("gate.disabled", {"gate": name, "status": "disabled"})
                )
                continue
            assert result is not None
            ordinals[name] = ordinals.get(name, 0) + 1
            evidence_id = next_evidence_id(graph)
            log_path = (
                log_root
                / f"gate-{name}-{ordinals[name]}-{graph.stage}-{evidence_id}.log"
            )
            log_path.write_text(
                f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}\n",
                encoding="utf-8",
            )
            evidence = Evidence(
                id=evidence_id,
                kind="gate",
                result="pass" if result.returncode == 0 else "fail",
                summary=f"{name}: {command}",
                command=command,
                stage=graph.stage,
                gate_name=name,
                exit_status=result.returncode,
                output_log=log_path.relative_to(repo_root).as_posix(),
            )
            _supersede_prior_gate_evidence(graph, evidence)
            graph = add_evidence(repo_root, graph, evidence)
            events.append(
                (
                    "gate.output",
                {
                    "gate": name,
                    "command": command,
                    "returncode": result.returncode,
                    "stdout_tail": result.stdout[-4000:],
                    "stderr_tail": result.stderr[-4000:],
                },
                )
            )
        executed_count = sum(result is not None for _, _, result in completed)
        reason = ""
        if executed_count == 0 and explicit_execution:
            reason = (
                "No configured gate command executed; every selected gate is "
                "disabled."
            )
            events.append(
                (
                    "gate.execution.nothing-ran",
                    {
                        "selected_gates": selected,
                        "executed_count": executed_count,
                        "reason": reason,
                    },
                )
            )
        save_graph_with_journal_events(repo_root, graph, events)
        blockers = {
            blocker.id: blocker
            for blocker in gate_failure_blockers(graph, config, selected)
        }
        exit_code = 0
        saw_failure = False
        for name, _command, result in completed:
            if result is None or result.returncode == 0:
                continue
            saw_failure = True
            blocker = blockers.get(f"gate:{name}")
            if blocker is None or active_waiver(graph, blocker) is None:
                exit_code = result.returncode
    if executed_count == 0 and explicit_execution:
        return GateExecutionOutcome("nothing-ran", 0, reason, 1)
    if executed_count == 0:
        return GateExecutionOutcome("not-enforced", 0, "", 0)
    if saw_failure and exit_code == 0:
        return GateExecutionOutcome("waived", executed_count, "", 0)
    return GateExecutionOutcome(
        "fail" if exit_code else "pass",
        executed_count,
        "",
        exit_code,
    )


def gate_failure_blockers(
    graph: Graph,
    config: WorkflowConfig,
    names: list[str] | None = None,
) -> list[Blocker]:
    """
    @brief Return exact waiver targets for enforced gates with active failures.
    @param[in] graph Authoritative run graph containing gate evidence.
    @param[in] config Validated gate policy and command definitions.
    @param[in] names Optional gate-name selection.
    @return Deterministically ordered failing-gate blocker records.
    """
    selected = [name for name in GATE_ORDER if not names or name in names]
    blockers: list[Blocker] = []
    for name in selected:
        group = getattr(config.gates, name)
        if group.mode != "enforce":
            continue
        failures = sorted(
            {
                (
                    item.command or "",
                    item.exit_status,
                    item.failure_kind or "",
                )
                for item in graph.evidence
                if item.kind == "gate"
                and item.gate_name == name
                and item.status == "active"
                and item.result == "fail"
            },
            key=lambda item: (item[0], item[1] if item[1] is not None else -1, item[2]),
        )
        if not failures:
            continue
        blockers.append(
            Blocker(
                id=f"gate:{name}",
                description=f"{name} gate has active failing evidence",
                state_digests=state_digests(
                    f"gate:{name}",
                    {
                        "mode": group.mode,
                        "commands": list(group.commands),
                        "failures": failures,
                    },
                ),
            )
        )
    return blockers


# HELPER FUNCTIONS


def _supersede_prior_gate_evidence(graph: Graph, evidence: Evidence) -> None:
    """
    @brief      Retire stale active gate evidence replaced by a newer run.
    @param[in,out] graph Authoritative graph, not yet carrying `evidence`.
    @param[in]  evidence Freshly created gate record about to be appended.
    @return     None.
    @details    Mirrors `check_execution._update_check_states` for gate
                evidence, which carries `check_id = None` and therefore falls
                outside that function. A rerun of the same gate command
                replaces its predecessor rather than accumulating beside it,
                and a pass additionally retires an older fail for the same
                command — the failed attempt at green. Without this a fixed
                gate stays `failed` forever: `_gate_result`,
                `gate_failure_blockers`, and INV-4 all read active records, so
                `verify run` would keep exiting 1 after the failure was fixed.
                A new fail never retires an older pass: keeping both visible is
                what lets INV-4 report a genuine regression instead of hiding
                that the command once passed.
    @exception  None
    """
    for prior in graph.evidence:
        if (
            prior.status != "active"
            or prior.kind != "gate"
            or prior.gate_name != evidence.gate_name
            or prior.command != evidence.command
        ):
            continue
        same_result = prior.result == evidence.result
        failed_attempt = evidence.result == "pass" and prior.result == "fail"
        if not (same_result or failed_attempt):
            continue
        prior.status = "superseded"
        prior.superseded_by = evidence.id
        prior.supersede_reason = (
            "superseded by a newer run of the same gate command"
        )


def _run_command(repo_root: Path, command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    """
    @brief      Run one gate command, synthesizing a failed result rather
                than raising.
    @param[in]  repo_root Working directory the command runs in.
    @param[in]  command Configured gate command text (simple argv or shell
                string).
    @param[in]  timeout Per-command timeout in seconds.
    @return     Completed process, synthesized as a failure (exit 127 for an
                unlaunchable executable, 124 for a timeout) when the command
                could not run to completion.
    @details    Windows refuses direct exec for targets CreateProcess cannot
                launch itself: `PermissionError` for a resolved directory or a
                shim the loader will not run, and `FileNotFoundError`
                (WinError 2) for a PATH-resolved `.cmd`/`.bat` shim such as
                `npm`, `npx`, `yarn`, `tsc`, or `eslint`, because CreateProcess
                does not apply `PATHEXT`. Every such launch refusal is an
                `OSError`, so the retry covers `OSError` rather than
                `PermissionError` alone — otherwise a command that succeeds on
                Linux/macOS is recorded as a failing gate on Windows. The
                command is still a real gate, so it is retried once through the
                shell rather than reported as an unlaunchable configuration
                error. Only argv-eligible commands retry: they were accepted by
                `_argv_for_simple_command` and therefore carry no shell
                metacharacter, so shell mode changes launch behavior only.
                `subprocess.TimeoutExpired` is handled first; it is not an
                `OSError` and a timed-out command must not be relaunched.
    @exception  None
    """
    argv = _argv_for_simple_command(repo_root, command)
    try:
        if argv:
            return subprocess.run(
                argv,
                cwd=repo_root,
                shell=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        return subprocess.run(
            command,
            cwd=repo_root,
            shell=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _failed_process(command, 124, exc)
    except OSError as exc:
        if argv and os.name == "nt":
            try:
                return subprocess.run(
                    command,
                    cwd=repo_root,
                    shell=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as retry_exc:
                return _failed_process(command, 124, retry_exc)
            except OSError as retry_exc:
                return _failed_process(command, 127, retry_exc)
        return _failed_process(command, 127, exc)


def _failed_process(command: str, returncode: int, exc: BaseException) -> subprocess.CompletedProcess[str]:
    """
    @brief      Synthesize a failed process result for an unrunnable command.
    @param[in]  command Configured gate command text.
    @param[in]  returncode Exit code to report (127 unlaunchable, 124 timeout).
    @param[in]  exc The exception that prevented normal completion.
    @return     Completed process carrying the exception text as stderr.
    @details    Keeps configuration mistakes (missing executables, timeouts)
                on the normal evidence path: the caller records a failing gate
                with this stderr tail instead of crashing with a traceback.
    @exception  None
    """
    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout="",
        stderr=f"{type(exc).__name__}: {exc}",
    )


def _argv_for_simple_command(repo_root: Path, command: str) -> list[str] | None:
    """
    @brief      Split a command into argv for direct exec, or signal that
                shell mode is required.
    @param[in]  repo_root Repository root used to resolve a relative
                executable path.
    @param[in]  command Configured gate command text.
    @return     Argv list for direct subprocess exec, or `None` when the
                command contains shell metacharacters or cannot be split.
    @exception  None
    """
    if any(token in command for token in ("&&", "||", "|", ">", "<", ";")):
        return None
    try:
        parts = _shlex_split_preserving_backslashes(command)
    except ValueError:
        return None
    if not parts:
        return None
    executable = Path(parts[0])
    if not executable.is_absolute() and any(sep in parts[0] for sep in ("/", "\\")):
        candidate = repo_root / executable
        if candidate.exists():
            parts[0] = str(candidate)
    return parts


def _shlex_split_preserving_backslashes(command: str) -> list[str]:
    """
    @brief      Split a command string into argv, quote-aware on every platform.
    @param[in]  command Gate command text to split into argv tokens.
    @return     Argv tokens with quote-grouping applied and backslashes
                preserved literally.
    @details    `shlex.split(command, posix=os.name != "nt")` used to pick
                POSIX vs. non-POSIX mode by platform: non-POSIX mode on
                Windows preserves literal backslashes (so ``C:\\Users\\x``
                survives), but it only treats a quote character as
                significant when it starts a token — a quoted argument
                containing a space, e.g. ``--flag="a b"``, is split into two
                tokens (``['--flag="a', 'b"']``) instead of one, silently
                corrupting the argv. POSIX mode groups quoted spans
                correctly but treats backslash as its own escape character,
                which would instead corrupt unquoted Windows paths.
                ``shlex.shlex`` lets quote-grouping and escape-handling be
                configured independently: POSIX mode for correct quote
                grouping, with ``escape`` cleared so backslashes are always
                passed through literally, on every platform.
    @exception  ValueError Raised when the command has unbalanced quoting.
    """
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    return list(lexer)


# END OF FILE
