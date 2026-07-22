#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_gates.py
@brief Workflow support module for test_gates.
@details Covers expected workflow behavior through focused pytest checks.
@author Eng. Dan Dumitru Pasare
@date 2026-06-20
@version 0.3.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

import pytest

from aegis.cli import main
from aegis.config import ConfigurationError, load_config
from aegis.gates import _argv_for_simple_command
from aegis.store import load_graph, resolve_run_id


# LOCAL HELPERS


def run_cli(tmp_path: Path, *args: str) -> None:
    """
    @brief      Run CLI workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  args Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        main(list(args))
    finally:
        os.chdir(cwd)


# TESTS


def test_simple_gate_command_runs_without_shell(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Handle test simple gate command runs without shell workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.3.0
    """
    python = sys.executable.replace("\\", "/")
    replace_workflow_toml(
        '[gates]\nmode = "disabled"\ntest = []\nlint = []',
        f'[gates]\nmode = "enforce"\ntest = [\'"{python}" -c "print(123)"\']\nlint = []',
    )
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")

    run_cli(tmp_path, "gates", "run")
    graph = load_graph(tmp_path, resolve_run_id(tmp_path))

    assert graph.evidence[-1].kind == "gate"
    assert graph.evidence[-1].result == "pass"


def test_repo_relative_executable_path_is_resolved_for_simple_gate_command(tmp_path: Path) -> None:
    """
    @brief      Handle test repo relative executable path is resolved for simple gate command workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    executable = tmp_path / "04_Software" / "App" / ".venv" / "Scripts" / "python.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")

    argv = _argv_for_simple_command(
        tmp_path,
        "04_Software/App/.venv/Scripts/python.exe 02_Tools/audit.py --changed-only",
    )

    assert argv is not None
    assert argv[0] == str(executable)


def test_quoted_argument_with_space_stays_one_token(tmp_path: Path) -> None:
    """
    @brief      A quoted argument containing a space parses as one argv token.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18):
                `shlex.split(command, posix=os.name != "nt")` on Windows only
                treats a quote as significant when it starts a token, so
                `pytest -k "test name with space"` used to split into
                `['pytest', '-k', '"test', 'name', 'with', 'space"']` instead
                of one `-k` value, silently running a different (narrower or
                invalid) command than configured.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    argv = _argv_for_simple_command(tmp_path, 'pytest -k "test name with space"')

    assert argv == ["pytest", "-k", "test name with space"]


def test_windows_backslash_path_is_preserved_unquoted(tmp_path: Path) -> None:
    """
    @brief      An unquoted Windows-style path keeps its literal backslashes.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18): plain
                POSIX-mode `shlex.split` treats backslash as its own escape
                character and would strip it from an unquoted Windows path
                (e.g. turning `C:\\Users\\x` into `C:Usersx`); the argv
                splitter must preserve it literally regardless of platform.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    argv = _argv_for_simple_command(tmp_path, r"C:\Users\demo\run.exe --path C:\Users\demo\data")

    assert argv == [r"C:\Users\demo\run.exe", "--path", r"C:\Users\demo\data"]


def test_scalar_gate_value_is_rejected_by_schema(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      A scalar `[gates]` string value is rejected by the strict schema.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Schema version 2 requires each gate collection to be a list of
                complete command strings and performs no compatibility coercion.
    @exception  ConfigurationError When the scalar value is parsed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    replace_workflow_toml(
        '[gates]\nmode = "disabled"\ntest = []\nlint = []',
        '[gates]\nmode = "enforce"\ntest = "pytest"\nlint = []',
    )

    with pytest.raises(ConfigurationError) as exc_info:
        load_config(tmp_path)

    assert exc_info.value.code == "CONFIG-TYPE-INVALID"
    assert exc_info.value.key_path == "gates.test"


def test_invalid_gate_value_type_fails_with_clear_message(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      A non-string, non-list `[gates]` value exits with a clear error.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Configuration content must never surface as a raw traceback;
                the error names the offending `[gates]` key.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    replace_workflow_toml(
        '[gates]\nmode = "disabled"\ntest = []\nlint = []',
        '[gates]\nmode = "enforce"\ntest = 123\nlint = []',
    )

    with pytest.raises(ConfigurationError) as exc_info:
        load_config(tmp_path)

    assert exc_info.value.code == "CONFIG-TYPE-INVALID"
    assert exc_info.value.key_path == "gates.test"


def test_unknown_gate_selector_is_rejected_by_cli(tmp_path: Path) -> None:
    """
    @brief      Reject an unknown explicit gate name instead of succeeding silently.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    with pytest.raises(SystemExit) as exc_info:
        run_cli(tmp_path, "gates", "run", "--name", "typo")

    assert exc_info.value.code == 2


def test_missing_executable_records_failing_gate_evidence(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      A gate whose executable does not exist records failing evidence.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Regression test (analysis-review follow-up, 2026-07-20): a
                mistyped command in argv mode used to raise an unhandled
                `FileNotFoundError` traceback (while shell mode returned
                non-zero) — it now ends as a normal failing gate with exit
                code 127, consistent across both execution modes.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.3.0
    """
    replace_workflow_toml(
        '[gates]\nmode = "disabled"\ntest = []\nlint = []',
        '[gates]\nmode = "enforce"\n'
        'test = ["definitely-not-a-command-xyz --version"]\nlint = []',
    )
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")

    with pytest.raises(SystemExit) as exc_info:
        run_cli(tmp_path, "gates", "run")

    assert exc_info.value.code == 127
    graph = load_graph(tmp_path, resolve_run_id(tmp_path))
    assert graph.evidence[-1].kind == "gate"
    assert graph.evidence[-1].result == "fail"


def test_gate_timeout_records_failing_gate_evidence(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      A gate exceeding the timeout records failing evidence.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    `subprocess.TimeoutExpired` used to propagate as a raw
                traceback in both execution modes; it now ends as a normal
                failing gate with exit code 124.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.3.0
    """
    python = sys.executable.replace("\\", "/")
    # No `;` in the command (a semicolon would route it through the shell
    # path, where the timeout kill only reaches the shell and the sleeping
    # child keeps the pipes open for the full duration) and no quotes in the
    # `-c` code (TOML literal strings cannot contain single quotes), so the
    # module name "time" is spelled with chr() calls.
    replace_workflow_toml(
        '[gates]\nmode = "disabled"\ntest = []\nlint = []',
        f'[gates]\nmode = "enforce"\n'
        f'test = [\'"{python}" -c __import__(chr(116)+chr(105)+chr(109)+chr(101)).sleep(30)\']\n'
        'lint = []',
    )
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")

    with pytest.raises(SystemExit) as exc_info:
        run_cli(tmp_path, "gates", "run", "--timeout", "1")

    assert exc_info.value.code == 124
    graph = load_graph(tmp_path, resolve_run_id(tmp_path))
    assert graph.evidence[-1].kind == "gate"
    assert graph.evidence[-1].result == "fail"


# END OF FILE
