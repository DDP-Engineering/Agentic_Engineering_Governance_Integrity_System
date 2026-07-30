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
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 1.1.0
"""

# IMPORTS

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .config import GATE_ORDER, WorkflowConfig
from .models import Evidence
from .persistence import locked
from .store import (
    add_evidence,
    append_journal,
    load_graph,
    next_evidence_id,
    run_lock_path,
    save_graph,
)

# PUBLIC API


def run_gates(
    repo_root: Path,
    run_id: str,
    config: WorkflowConfig,
    names: list[str] | None = None,
    timeout: int = 300,
) -> int:
    """
    @brief      Run gates workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  run_id Already resolved run ID selected by CLI orchestration.
    @param[in]  config Validated workflow configuration.
    @param[in]  names Input value used by the workflow helper.
    @param[in]  timeout Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  ValueError If a requested gate name is unsupported.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    1.1.0
    """
    unknown = sorted(set(names or ()) - set(GATE_ORDER))
    if unknown:
        raise ValueError(
            f"Unknown gate name(s): {', '.join(unknown)}. "
            f"Expected one or more of {', '.join(GATE_ORDER)}."
        )
    with locked(run_lock_path(repo_root, run_id)):
        return _run_gates_locked(repo_root, run_id, config, names, timeout)


def _run_gates_locked(
    repo_root: Path,
    run_id: str,
    config: WorkflowConfig,
    names: list[str] | None,
    timeout: int,
) -> int:
    """
    @brief Execute gate commands while holding the complete graph transaction.
    @param[in] repo_root Repository root.
    @param[in] run_id Selected run identity.
    @param[in] config Validated workflow configuration.
    @param[in] names Optional gate selection.
    @param[in] timeout Per-command timeout.
    @return Aggregate gate exit code.
    @version 1.1.0
    """
    graph = load_graph(repo_root, run_id)
    selected = [name for name in GATE_ORDER if not names or name in names]

    exit_code = 0
    for name in selected:
        group = getattr(config.gates, name)
        if group.mode == "disabled":
            append_journal(
                repo_root,
                graph.run_id,
                "gate.disabled",
                {"gate": name, "status": "disabled"},
            )
            continue
        commands = group.commands
        for command in commands:
            result = _run_command(repo_root, command, timeout)
            evidence = Evidence(
                id=next_evidence_id(graph),
                kind="gate",
                result="pass" if result.returncode == 0 else "fail",
                summary=f"{name}: {command}",
                command=command,
                stage=graph.stage,
                gate_name=name,
                exit_status=result.returncode,
            )
            graph = add_evidence(repo_root, graph, evidence)
            append_journal(
                repo_root,
                graph.run_id,
                "gate.output",
                {
                    "gate": name,
                    "command": command,
                    "returncode": result.returncode,
                    "stdout_tail": result.stdout[-4000:],
                    "stderr_tail": result.stderr[-4000:],
                },
            )
            if result.returncode != 0:
                exit_code = result.returncode
    save_graph(repo_root, graph)
    return exit_code


# HELPER FUNCTIONS


def _run_command(repo_root: Path, command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    """
    @brief      Run command workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  command Input value used by the workflow helper.
    @param[in]  timeout Input value used by the workflow helper.
    @return     Completed process, synthesized as a failure (exit 127 for an
                unlaunchable executable, 124 for a timeout) when the command
                could not run to completion.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
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
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as exc:
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout="",
        stderr=f"{type(exc).__name__}: {exc}",
    )


def _argv_for_simple_command(repo_root: Path, command: str) -> list[str] | None:
    """
    @brief      Handle argv for simple command workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  command Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
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
    @param[in]  command Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    return list(lexer)


# END OF FILE
