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
         ``SubprocessCommandRunner`` against missing and unlaunchable process
         inputs.
"""

# IMPORTS

from __future__ import annotations

import sys
from unittest.mock import Mock

import pytest

from waegis.probes.runner import CommandResult, SubprocessCommandRunner

from _fake_command_runner import FakeCommandRunner, failing_result, not_found_result, ok_result

# TESTS


def test_command_result_ok_requires_found_and_zero_exit() -> None:
    """
    @brief      ``CommandResult.ok()`` is true only for found + exit code 0.
    @return     None
    @exception  AssertionError If any of the three combinations disagrees.
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
    """
    runner = SubprocessCommandRunner()
    result = runner.run(("waegis-test-definitely-nonexistent-binary-xyz",))
    assert result.found is False
    assert result.exit_code is None
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.parametrize(
    "launch_error",
    (
        PermissionError("executable is not permitted"),
        NotADirectoryError("working directory is invalid"),
    ),
)
def test_subprocess_command_runner_captures_other_launch_errors(
    monkeypatch: pytest.MonkeyPatch,
    launch_error: OSError,
) -> None:
    """
    @brief Map non-missing OS launch failures to diagnostic result values.
    @param[in] monkeypatch Pytest patching fixture.
    @param[in] launch_error Spawn failure raised by ``subprocess.run``.
    @return None.
    """
    monkeypatch.setattr(
        "waegis.probes.runner.subprocess.run",
        Mock(side_effect=launch_error),
    )

    result = SubprocessCommandRunner().run(("present-but-unlaunchable",))

    assert result.found is False
    assert result.exit_code is None
    assert result.stdout == ""
    assert str(launch_error) in result.stderr


def test_subprocess_command_runner_decodes_non_ascii_output_as_utf8() -> None:
    """
    @brief      ``SubprocessCommandRunner`` decodes UTF-8 child output on any
                host locale rather than losing it.
    @return     None
    @exception  AssertionError If the output is misdecoded or lost.
    @details    Regression guard. ``text=True`` without an explicit ``encoding``
                decodes with the locale preferred encoding, which is ``cp1252``
                on a stock Windows host. ``Ё`` encodes to ``d0 81`` in UTF-8 and
                ``cp1252`` cannot map ``0x81``. The failure is quieter than a
                raised error: the decode happens in ``subprocess``'s own reader
                thread, so that thread dies and ``run`` returns ``stdout=None``
                — a ``None`` where the ``CommandResult`` contract promises
                ``str``. Asserting the exact text catches both the lost output
                and any future mojibake. Git reports such a path whenever a
                repository contains one, so this is reachable from a plain
                ``waegis adopt``. The child writes raw bytes so the assertion
                does not depend on the child's own stdout encoding.
    """
    runner = SubprocessCommandRunner()
    result = runner.run(
        (sys.executable, "-c", "import sys; sys.stdout.buffer.write('Ё.txt'.encode('utf-8'))"),
    )
    assert result.found is True
    assert result.exit_code == 0
    assert result.stdout == "Ё.txt"


# END OF FILE
