#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_cli_smoke.py
@brief Smoke tests for the WAEGIS CLI scaffold (task T0.1 acceptance).
@details Asserts ``python -m waegis --help`` exits 0 and lists every planned
         subcommand, and that each subcommand is a stub exiting 2 "not
         implemented". Runs entirely offline (no network access).
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from waegis.cli import SUBCOMMANDS, main

# CONSTANTS

# @brief Source root added to PYTHONPATH for the ``-m waegis`` subprocess.
_SRC = Path(__file__).resolve().parents[1] / "src"


# LOCAL HELPERS


def _run_module(*args: str) -> subprocess.CompletedProcess[str]:
    """
    @brief      Invoke ``python -m waegis`` in a subprocess with ``src`` on the
                path, capturing text output.
    @param[in]  args Command-line arguments passed after ``-m waegis``.
    @return     Completed process with captured stdout/stderr.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(_SRC) + (os.pathsep + existing if existing else "")
    return subprocess.run(
        [sys.executable, "-m", "waegis", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


# TESTS


def test_help_exits_zero_and_lists_subcommands() -> None:
    """
    @brief      ``python -m waegis --help`` exits 0 and lists every planned
                subcommand (T0.1 acceptance).
    @return     None
    @exception  AssertionError On non-zero exit or a missing subcommand.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    result = _run_module("--help")
    assert result.returncode == 0, result.stderr
    for name, _help in SUBCOMMANDS:
        assert name in result.stdout, f"missing subcommand in help: {name}"


@pytest.mark.parametrize("name", [n for n, _ in SUBCOMMANDS])
def test_subcommand_stub_exits_two(name: str) -> None:
    """
    @brief      Every planned subcommand is a stub that exits 2 (T0.1
                acceptance).
    @param[in]  name Subcommand name under test.
    @return     None
    @exception  AssertionError If the stub does not return exit code 2.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    assert main([name]) == 2


def test_no_command_errors() -> None:
    """
    @brief      Invoking ``waegis`` with no subcommand raises the argparse error
                exit (code 2).
    @return     None
    @exception  AssertionError If argparse does not exit with code 2.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2

# END OF FILE
