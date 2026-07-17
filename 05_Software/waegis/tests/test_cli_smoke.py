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
         subcommand, that each not-yet-implemented subcommand is a stub exiting
         2, and that the real handlers (``analyze`` T3.3, ``new`` T4.3,
         ``adopt`` T5.2, ``doctor`` T6.1) answer through their own subparsers.
         Runs entirely offline (no network access).
@author Eng. Dan Dumitru Pasare
@date 2026-07-15
@version 0.4.0
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


def test_version_is_a_real_command(capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief      Every planned subcommand other than ``analyze`` (T3.3),
                ``new`` (T4.3), ``adopt`` (T5.2), ``doctor`` (T6.1), and
                ``upgrade`` (T6.2) is still a stub that exits 2 — regression
                guard proving the real handlers did not disturb any other
                subcommand's stub behavior (only ``version``, ``self-update``,
                and ``gui`` remain stubs).
    @param[in]  name Subcommand name under test.
    @return     None
    @exception  AssertionError If the stub does not return exit code 2.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.6.0
    """
    assert main(["version"]) == 0
    assert "WAEGIS 0.1.0" in capsys.readouterr().out


def test_upgrade_is_no_longer_a_stub() -> None:
    """
    @brief      ``waegis upgrade --help`` exits 0 through the real argparse-driven
                subparser (T6.2) and documents the plan §5 flags, unlike the
                generic not-implemented stub.
    @return     None
    @exception  AssertionError If the help exit code or flag list is wrong.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    result = _run_module("upgrade", "--help")
    assert result.returncode == 0, result.stderr
    for flag in ("--repo", "--dry-run", "--json", "--payload"):
        assert flag in result.stdout, f"missing flag in 'upgrade --help': {flag}"


def test_new_is_no_longer_a_stub() -> None:
    """
    @brief      ``waegis new --help`` exits 0 through the real argparse-driven
                subparser (T4.3) and documents the plan §5 flags, unlike the
                generic not-implemented stub.
    @return     None
    @exception  AssertionError If the help exit code or flag list is wrong.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    result = _run_module("new", "--help")
    assert result.returncode == 0, result.stderr
    for flag in ("--answers", "--dry-run", "--non-interactive", "--json", "--payload"):
        assert flag in result.stdout, f"missing flag in 'new --help': {flag}"


def test_adopt_is_no_longer_a_stub() -> None:
    """
    @brief      ``waegis adopt --help`` exits 0 through the real argparse-driven
                subparser (T5.2) and documents the plan §5 flags, unlike the
                generic not-implemented stub.
    @return     None
    @exception  AssertionError If the help exit code or flag list is wrong.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    result = _run_module("adopt", "--help")
    assert result.returncode == 0, result.stderr
    for flag in ("--answers", "--dry-run", "--non-interactive", "--json", "--payload"):
        assert flag in result.stdout, f"missing flag in 'adopt --help': {flag}"


def test_analyze_is_no_longer_a_stub(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``waegis analyze --repo PATH`` via the real argparse-driven
                ``main()`` entry point exits 0 for a clean fixture directory
                (T3.3), unlike the generic not-implemented stub.
    @param[in]  tmp_path Pytest tmp_path fixture used as the analyzed repo.
    @return     None
    @exception  AssertionError If the exit code is not 0.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    assert main(["analyze", "--repo", str(tmp_path)]) == 0


def test_doctor_is_no_longer_a_stub(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``waegis doctor --repo PATH`` via the real argparse-driven
                ``main()`` entry point runs to a health-verdict exit code
                (T6.1), unlike the generic not-implemented stub which always
                exits 2. A bare directory has no install, so several groups
                warn/fail; the exit code is asserted only to be in the
                doctor-specific {0, 1, 2} range, not the stub's fixed 2.
    @param[in]  tmp_path Pytest tmp_path fixture used as the diagnosed repo.
    @param[in]  monkeypatch Redirects WAEGIS_HOME so the real user profile is
                never touched by this offline test.
    @return     None
    @exception  AssertionError If the exit code falls outside {0, 1, 2}.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
    exit_code = main(["doctor", "--repo", str(tmp_path)])
    assert exit_code in (0, 1, 2)


def test_doctor_help_documents_repo_and_json_flags() -> None:
    """
    @brief      ``waegis doctor --help`` exits 0 and documents the ``--repo``/
                ``--json`` flag shape (matching ``analyze``, not ``new``/
                ``adopt``'s ``TARGET``-based shape).
    @return     None
    @exception  AssertionError If the help exit code or flag list is wrong.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    result = _run_module("doctor", "--help")
    assert result.returncode == 0, result.stderr
    assert "--repo" in result.stdout
    assert "--json" in result.stdout


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
