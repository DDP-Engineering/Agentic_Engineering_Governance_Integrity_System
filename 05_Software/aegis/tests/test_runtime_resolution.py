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


@pytest.mark.skipif(os.name != "nt", reason="PowerShell wrapper is Windows-only")
def test_run_ps1_preserves_remaining_arguments(tmp_path: Path) -> None:
    """@brief Round-trip spaces, trailing slashes, quotes, empties, and switches."""
    shell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if shell is None:
        pytest.skip("PowerShell is not installed in this test environment")
    tools = tmp_path / "tools"
    tools.mkdir()
    wrapper = tools / "run.ps1"
    shutil.copy2(TEMPLATE_ROOT / ".agentic/tools/run.ps1", wrapper)
    (tools / "run_aegis.py").write_text(
        "import json, os, sys\n"
        "args = json.loads(os.environ['AEGIS_WRAPPER_ARGUMENTS']) "
        "if sys.argv[1:] == ['--aegis-wrapper-args-env'] else sys.argv[1:]\n"
        "print(json.dumps(args))\n",
        encoding="utf-8",
    )
    expected = [
        "plain",
        "C:\\a b\\",
        "second",
        "",
        'embedded"quote',
        "-v",
        "-d",
        "-ev",
        "value",
    ]
    environment = dict(os.environ)
    environment["AEGIS_PYTHON"] = sys.executable
    environment["WRAPPER_PATH"] = str(wrapper)
    environment["PROBE_ARGS"] = json.dumps(expected)
    command = (
        "$probeArgs = [string[]](ConvertFrom-Json -InputObject $env:PROBE_ARGS); "
        "& $env:WRAPPER_PATH @probeArgs"
    )

    result = subprocess.run(
        [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected


@pytest.mark.skipif(os.name != "nt", reason="Windows installer parity probe")
def test_installers_support_bracket_paths_and_repeated_runs(tmp_path: Path) -> None:
    """@brief Install twice through PowerShell and Git Bash in a bracket path."""
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if powershell is None or not git_bash.is_file() or shutil.which("uv") is None:
        pytest.skip("PowerShell, Git Bash, and uv are required")
    project = tmp_path / "project[1]"
    shutil.copytree(TEMPLATE_ROOT, project)
    powershell_command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(project / ".agentic/tools/install.ps1"),
        "-UseUv",
    ]
    bash_command = [str(git_bash), ".agentic/tools/install.sh"]

    for command in (powershell_command, powershell_command, bash_command, bash_command):
        result = subprocess.run(
            command,
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr

    assert (project / ".agentic/.venv/Scripts/python.exe").is_file()


# END OF FILE
