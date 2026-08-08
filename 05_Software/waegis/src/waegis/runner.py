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
@brief Injectable, argument-array-only subprocess execution.
@details Centralizes timeouts and environment composition without an event
         system, shell expansion, or network-specific behavior.
"""

# IMPORTS

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence


# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True, slots=True)
class CommandResult:
    """@brief Immutable subprocess result used by command orchestrators."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    """@brief Structural injection contract for subprocess execution."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        """@brief Execute one command without invoking a shell."""


# EXPORTED FUNCTIONS / PUBLIC API


class CommandRunner:
    """@brief Standard-library implementation of the runner contract."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        """
        @brief Execute an argument array and capture text streams.
        @param[in] args Non-empty executable and argument sequence.
        @param[in] cwd Optional working directory.
        @param[in] timeout Positive timeout in seconds.
        @param[in] env Optional environment overlay.
        @return Captured result.
        @exception ValueError If arguments or timeout are invalid.
        @exception OSError If the executable cannot be started.
        @exception subprocess.TimeoutExpired If the command exceeds timeout.
        """
        command = tuple(str(item) for item in args)
        if not command or not command[0]:
            raise ValueError("command arguments must name an executable")
        if timeout <= 0:
            raise ValueError("command timeout must be positive")
        process_env = os.environ.copy()
        if env:
            process_env.update({str(key): str(value) for key, value in env.items()})
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=process_env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
        return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)


# END OF FILE
