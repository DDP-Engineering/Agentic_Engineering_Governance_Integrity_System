#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file gitops.py
@brief Minimal Git operations allowed by WAEGIS 3.
@details Provides status, HEAD, tracked-path, initialization, restore, and clean
         primitives only. It has no history-writing operations.
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .runner import CommandResult, Runner


# DATA MODELS / TYPEDEFINITIONS


class GitError(RuntimeError):
    """@brief Raised when a required Git operation fails."""


# EXPORTED FUNCTIONS / PUBLIC API


def run_git(
    runner: Runner,
    repository: Path,
    args: Sequence[str],
    *,
    timeout: float = 30.0,
) -> CommandResult:
    """@brief Execute one allowed Git argument array at a repository."""
    return runner.run(("git", "-C", str(repository), *args), cwd=repository, timeout=timeout)


def require_git_success(result: CommandResult, operation: str) -> CommandResult:
    """@brief Return a successful result or raise a concise Git failure."""
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise GitError(f"git {operation} failed: {detail}")
    return result


def initialize_repository(runner: Runner, target: Path) -> None:
    """@brief Run the only WAEGIS-authorized Git mutation outside recovery."""
    result = runner.run(("git", "init", str(target)), cwd=target.parent, timeout=30)
    require_git_success(result, "init")


# END OF FILE
