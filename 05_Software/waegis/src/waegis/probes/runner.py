#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file runner.py
@brief Injectable command-runner primitive shared by every WAEGIS probe (T2.1).
@details Ports the proven ador ``doctor.py`` design: no probe module calls
         ``subprocess`` directly. Every probe accepts a :class:`CommandRunner`
         and calls its single ``run`` method, so tests substitute a fake runner
         and stay offline (plan AD-3). ``CommandResult.found`` distinguishes
         "the executable does not exist" from "the executable ran and exited
         non-zero", which the tool probes (T2.1 ``probes/tools.py``) rely on to
         fall through a candidate list (e.g. ``py -3`` -> ``python3`` ->
         ``python``) instead of treating a missing launcher as a hard error.
@details This lives in its own small module (``probes/runner.py``) rather than
         ``probes/__init__.py`` so the package marker stays a marker and the
         runner can be imported without pulling in probe-specific code
         (``from waegis.probes.runner import CommandRunner, SubprocessCommandRunner``).
@details ``run`` accepts an optional ``cwd`` keyword (added for T4.3): the
         template payload's workflow CLI resolves its repository root from the
         process working directory, so the wizard's smoke and gate steps must
         run wrapper scripts *inside* the target repo. ``cwd=None`` (the
         default) preserves the original behavior for every existing caller.
@details Child output is decoded as UTF-8 with replacement (0.3.0). ``text=True``
         alone decodes with the locale preferred encoding, which is ``cp1252``
         on a stock Windows host: a Git command reporting a path such as
         ``Ё.txt`` returns bytes (``d0 81``) that ``cp1252`` cannot map. The
         resulting ``UnicodeDecodeError`` is raised inside ``subprocess``'s
         own reader thread, so it never reaches this caller — the thread dies
         and ``run`` returns ``stdout=None``. That silently violated the
         ``CommandResult.stdout: str`` contract: a probe testing truthiness saw
         "no output" and concluded the command produced nothing, while one
         calling ``.strip()`` or ``.splitlines()`` got an ``AttributeError``
         far from the real cause. Git and the tools probed here emit UTF-8
         regardless of the console code page.
"""

# IMPORTS

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

# CONSTANTS

# @brief Shared default for every probe's subprocess timeout.
DEFAULT_PROBE_TIMEOUT = 5.0

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class CommandResult:
    """
    @brief Outcome of one command invocation through a :class:`CommandRunner`.
    @details ``found`` is ``False`` when the process could not be launched.
             A missing executable keeps ``stdout``/``stderr`` empty; other
             operating-system launch failures retain their diagnostic in
             ``stderr``. In either case ``exit_code`` is ``None``.
             ``timed_out`` is ``True`` when the process exceeded the caller's
             timeout; the executable is known to exist (``found`` stays
             ``True``) but ``exit_code`` is ``None`` since the process did not
             finish.
    """

    found: bool
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False

    def ok(self) -> bool:
        """
        @brief      Report whether the command was found and exited zero.
        @return     ``True`` when ``found`` is ``True``, the process did not
                    time out, and ``exit_code == 0``.
        @exception  None
        """
        return self.found and not self.timed_out and self.exit_code == 0

    def combined_output(self) -> str:
        """
        @brief      Concatenate stdout and stderr for output that may land on
                    either stream (some tools print version text to stderr).
        @return     ``stdout`` then ``stderr``, joined with a newline when both
                    are non-empty.
        @exception  None
        """
        if self.stdout and self.stderr:
            return f"{self.stdout}\n{self.stderr}"
        return self.stdout or self.stderr


@runtime_checkable
class CommandRunner(Protocol):
    """
    @brief Injectable seam for running a subprocess (plan AD-3, ported from
           ador ``doctor.py``'s ``CommandRunner``).
    @details Probe modules depend only on this protocol, never on
             ``subprocess`` directly, so tests substitute a fake runner and the
             probe suite stays fully offline.
    """

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float = DEFAULT_PROBE_TIMEOUT,
        cwd: str | os.PathLike[str] | None = None,
    ) -> CommandResult:
        """
        @brief      Run one command and capture its outcome.
        @param[in]  argv Argument vector; ``argv[0]`` is the executable name or
                    path.
        @param[in]  timeout Seconds to allow the process to run before it is
                    treated as timed out.
        @param[in]  cwd Optional working directory for the process; ``None``
                    inherits the caller's working directory (the pre-T4.3
                    behavior, unchanged for existing callers).
        @return     A :class:`CommandResult` describing what happened.
        """
        ...


# PUBLIC API


class SubprocessCommandRunner:
    """
    @brief Real, subprocess-backed :class:`CommandRunner` implementation.
    @details The only place in the probe layer allowed to import
             ``subprocess``. Captures stdout/stderr as text, maps operating
             system launch failures to ``CommandResult(found=False, ...)``,
             and maps :class:`subprocess.TimeoutExpired` to
             ``CommandResult(found=True, timed_out=True, exit_code=None, ...)``.
    """

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float = DEFAULT_PROBE_TIMEOUT,
        cwd: str | os.PathLike[str] | None = None,
    ) -> CommandResult:
        """
        @brief      Run ``argv`` as a real subprocess.
        @param[in]  argv Argument vector; ``argv[0]`` is the executable name or
                    path.
        @param[in]  timeout Seconds to allow the process to run before it is
                    killed and reported as timed out.
        @param[in]  cwd Optional working directory for the process; ``None``
                    inherits the current working directory.
        @return     A :class:`CommandResult` capturing the real outcome.
        @exception  None All failure modes are captured in the returned
                    :class:`CommandResult` rather than raised.
        @details    Decoding is pinned to UTF-8 with replacement rather than
                    left to the locale, so non-ASCII child output cannot come
                    back as ``stdout=None`` from a decode that failed inside
                    ``subprocess``'s reader thread. See the module docstring for
                    the concrete ``cp1252`` case this closes.
        """
        try:
            completed = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=str(cwd) if cwd is not None else None,
                check=False,
            )
        except FileNotFoundError:
            return CommandResult(found=False, exit_code=None, stdout="", stderr="")
        except OSError as exc:
            # Capture rarer launch failures such as PermissionError (present
            # but not executable) and NotADirectoryError (bad cwd) without
            # changing the established missing-executable response contract.
            return CommandResult(found=False, exit_code=None, stdout="", stderr=str(exc))
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return CommandResult(
                found=True,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
            )
        return CommandResult(
            found=True,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


# END OF FILE
