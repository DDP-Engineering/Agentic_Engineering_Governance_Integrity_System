#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_runtime_resolution.py
@brief Clean-machine-style tests for the registered WAEGIS runtime pointer.
@details Runs the Node hook launcher and the platform CLI wrapper with an
         empty ``PATH`` and no ``AEGIS_PYTHON`` override, so the only way
         either can find a Python interpreter is through the
         ``WAEGIS_HOME/runtime-python`` pointer file.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PACKAGE_ROOT / "template"


# LOCAL HELPERS


def _runtime_environment(tmp_path: Path) -> dict[str, str]:
    """
    @brief      Build an environment with no system PATH and one runtime pointer.
    @param[in]  tmp_path Pytest-provided temporary directory for the fake
                ``WAEGIS_HOME``.
    @return     An environment mapping with ``WAEGIS_HOME`` set, ``PATH``
                cleared, and any ``AEGIS_PYTHON`` override removed.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    home = tmp_path / "waegis-home"
    home.mkdir()
    (home / "runtime-python").write_text(str(Path(sys.executable).resolve()) + "\n", encoding="utf-8")
    environment = dict(os.environ)
    environment["WAEGIS_HOME"] = str(home)
    environment["PATH"] = ""
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("AEGIS_PYTHON", None)
    return environment


# TESTS


def test_hook_launcher_uses_registered_runtime_without_system_python(tmp_path: Path) -> None:
    """
    @brief      Node hook transport runs a guard with PATH deliberately empty.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is not installed in this test environment")
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo safe"},
        "cwd": str(TEMPLATE_ROOT),
    }
    result = subprocess.run(
        [
            node,
            str(TEMPLATE_ROOT / ".agentic/tools/run_hook.mjs"),
            str(TEMPLATE_ROOT / ".agentic/hooks/secret_scan.py"),
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=TEMPLATE_ROOT,
        env=_runtime_environment(tmp_path),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "No AEGIS Python runtime" not in result.stderr


def test_cli_wrapper_uses_registered_runtime_without_system_python(tmp_path: Path) -> None:
    """
    @brief      The platform wrapper runs AEGIS help with PATH deliberately empty.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    environment = _runtime_environment(tmp_path)
    if os.name == "nt":
        shell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if shell is None:
            pytest.skip("PowerShell is not installed in this test environment")
        command = [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(TEMPLATE_ROOT / ".agentic/tools/run.ps1"),
            "--help",
        ]
    else:
        shell = shutil.which("bash")
        if shell is None:
            pytest.skip("bash is not installed in this test environment")
        command = [shell, str(TEMPLATE_ROOT / ".agentic/tools/run.sh"), "--help"]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=TEMPLATE_ROOT,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


# END OF FILE
