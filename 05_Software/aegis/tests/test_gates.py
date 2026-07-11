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
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path
import sys

from aegis.cli import main
from aegis.gates import _argv_for_simple_command
from aegis.store import load_graph


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


def test_simple_gate_command_runs_without_shell(tmp_path: Path) -> None:
    """
    @brief      Handle test simple gate command runs without shell workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    python = sys.executable.replace("\\", "/")
    (agentic / "workflow.toml").write_text(
        f"""
[gates]
smoke = ['"{python}" -c "print(123)"']
""",
        encoding="utf-8",
    )
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")

    run_cli(tmp_path, "gates", "run")
    graph = load_graph(tmp_path)

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
