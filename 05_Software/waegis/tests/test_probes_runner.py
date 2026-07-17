#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_probes_runner.py
@brief CommandRunner primitive tests for the WAEGIS probe layer (T2.1).
@details Covers the fake runner's found/not-found/exit-code behavior (used by
         every other probe test in this suite) and the real
         ``SubprocessCommandRunner`` against a definitely-missing executable
         name, which stays offline since no such binary can exist.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from waegis.probes.runner import CommandResult, SubprocessCommandRunner

from _fake_command_runner import FakeCommandRunner, failing_result, not_found_result, ok_result

# TESTS


def test_command_result_ok_requires_found_and_zero_exit() -> None:
    """
    @brief      ``CommandResult.ok()`` is true only for found + exit code 0.
    @return     None
    @exception  AssertionError If any of the three combinations disagrees.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    assert ok_result().ok() is True
    assert failing_result(exit_code=1).ok() is False
    assert not_found_result().ok() is False
    assert CommandResult(found=True, exit_code=None, stdout="", stderr="", timed_out=True).ok() is False


def test_command_result_combined_output_joins_both_streams() -> None:
    """
    @brief      ``combined_output`` joins stdout and stderr when both are set,
                and returns whichever one is non-empty otherwise.
    @return     None
    @exception  AssertionError If a stream is dropped or misordered.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    both = CommandResult(found=True, exit_code=0, stdout="out", stderr="err")
    assert both.combined_output() == "out\nerr"
    stdout_only = CommandResult(found=True, exit_code=0, stdout="out", stderr="")
    assert stdout_only.combined_output() == "out"
    stderr_only = CommandResult(found=True, exit_code=0, stdout="", stderr="err")
    assert stderr_only.combined_output() == "err"


def test_fake_command_runner_distinguishes_not_found_from_nonzero_exit() -> None:
    """
    @brief      The fake runner reports a scripted non-zero exit differently
                from an argv it was never told about (not found).
    @return     None
    @exception  AssertionError If the two outcomes collapse to the same thing.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({("git", "--version"): failing_result(exit_code=1, stderr="boom")})

    known = runner.run(("git", "--version"))
    assert known.found is True
    assert known.exit_code == 1

    unknown = runner.run(("does-not-exist", "--version"))
    assert unknown.found is False
    assert unknown.exit_code is None

    assert runner.calls == [("git", "--version"), ("does-not-exist", "--version")]


def test_subprocess_command_runner_reports_not_found_for_missing_executable() -> None:
    """
    @brief      ``SubprocessCommandRunner`` maps a missing executable to
                ``found=False`` rather than raising ``FileNotFoundError``.
    @return     None
    @exception  AssertionError If the missing executable raises or is
                misreported.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = SubprocessCommandRunner()
    result = runner.run(("waegis-test-definitely-nonexistent-binary-xyz",))
    assert result.found is False
    assert result.exit_code is None
    assert result.stdout == ""
    assert result.stderr == ""


# END OF FILE
