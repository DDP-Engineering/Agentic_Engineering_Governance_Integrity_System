#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file _fake_command_runner.py
@brief Test-only fake ``CommandRunner`` for the WAEGIS probe suite (T2.1).
@details Not collected by pytest (underscore prefix). Maps an exact argv tuple
         to a canned :class:`waegis.probes.runner.CommandResult`; an argv not
         present in the mapping is reported as "not found" rather than raising,
         which mirrors what :class:`waegis.probes.runner.SubprocessCommandRunner`
         does for a missing executable. Every probe test builds one of these
         instead of touching a real subprocess. The optional ``cwd`` keyword
         (T4.3) is recorded per call in ``cwds`` so command tests can assert
         the working directory a smoke/gate invocation would have used.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import os
from typing import Sequence

from waegis.probes.runner import CommandResult

# PUBLIC API


class FakeCommandRunner:
    """
    @brief Scripted, offline stand-in for :class:`waegis.probes.runner.CommandRunner`.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        """
        @brief      Build a fake runner from a fixed argv -> result mapping.
        @param[in]  responses Mapping of exact argv tuples to the
                    :class:`CommandResult` the fake returns for that argv.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        self._responses = dict(responses)
        self.calls: list[tuple[str, ...]] = []
        self.cwds: list[str | None] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float = 5.0,
        cwd: str | os.PathLike[str] | None = None,
    ) -> CommandResult:
        """
        @brief      Return the scripted result for ``argv``, recording the call.
        @param[in]  argv Argument vector looked up verbatim in the scripted
                    mapping.
        @param[in]  timeout Ignored (no real process runs).
        @param[in]  cwd Recorded (as ``str`` or ``None``) in ``cwds``, aligned
                    index-for-index with ``calls``; never acted on.
        @return     The scripted :class:`CommandResult`, or a "not found"
                    result when ``argv`` was not scripted.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.2.0
        """
        key = tuple(argv)
        self.calls.append(key)
        self.cwds.append(str(cwd) if cwd is not None else None)
        return self._responses.get(key, CommandResult(found=False, exit_code=None, stdout="", stderr=""))


def ok_result(stdout: str = "", stderr: str = "") -> CommandResult:
    """
    @brief      Build a found, zero-exit :class:`CommandResult`.
    @param[in]  stdout Captured stdout text.
    @param[in]  stderr Captured stderr text.
    @return     ``CommandResult(found=True, exit_code=0, stdout=stdout, stderr=stderr)``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return CommandResult(found=True, exit_code=0, stdout=stdout, stderr=stderr)


def failing_result(exit_code: int = 1, stdout: str = "", stderr: str = "") -> CommandResult:
    """
    @brief      Build a found, non-zero-exit :class:`CommandResult`.
    @param[in]  exit_code Non-zero exit code to report.
    @param[in]  stdout Captured stdout text.
    @param[in]  stderr Captured stderr text.
    @return     ``CommandResult(found=True, exit_code=exit_code, ...)``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return CommandResult(found=True, exit_code=exit_code, stdout=stdout, stderr=stderr)


def not_found_result() -> CommandResult:
    """
    @brief      Build a "not found" :class:`CommandResult`.
    @return     ``CommandResult(found=False, exit_code=None, stdout="", stderr="")``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return CommandResult(found=False, exit_code=None, stdout="", stderr="")


# END OF FILE
