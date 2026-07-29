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
@brief Gate parsing and command-tokenization tests for schema 3.
@details Execution, ordering, timeout, missing executable, and execute-all
         semantics are covered by test_aegis_v2_policy.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 2.0.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.config import ConfigurationError, load_config
from aegis.gates import _argv_for_simple_command

# TESTS


def test_repo_relative_executable_is_resolved(tmp_path: Path) -> None:
    """@brief Resolve a repository-relative executable without a shell."""
    executable = tmp_path / "tools" / "python.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    argv = _argv_for_simple_command(tmp_path, "tools/python.exe audit.py")
    assert argv == [str(executable), "audit.py"]


def test_quoted_argument_and_windows_path_are_preserved(tmp_path: Path) -> None:
    """@brief Keep quoted spaces and literal Windows backslashes intact."""
    assert _argv_for_simple_command(
        tmp_path,
        'pytest -k "test name with space"',
    ) == ["pytest", "-k", "test name with space"]
    assert _argv_for_simple_command(
        tmp_path,
        r"C:\Users\demo\run.exe --path C:\Users\demo\data",
    ) == [
        r"C:\Users\demo\run.exe",
        "--path",
        r"C:\Users\demo\data",
    ]


@pytest.mark.parametrize("invalid", ['"pytest"', "123"])
def test_gate_commands_require_a_string_array(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    invalid: str,
) -> None:
    """@brief Reject scalar command values at the exact group key."""
    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        f'[gates.test]\nmode = "enforce"\ncommands = {invalid}',
    )
    with pytest.raises(ConfigurationError) as raised:
        load_config(tmp_path)
    assert raised.value.key_path == "gates.test.commands"


def test_enforced_gate_requires_a_command(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Reject an enforced group with no deterministic command."""
    replace_workflow_toml(
        '[gates.security]\nmode = "disabled"\ncommands = []',
        '[gates.security]\nmode = "enforce"\ncommands = []',
    )
    with pytest.raises(ConfigurationError, match="at least one command"):
        load_config(tmp_path)


def test_unknown_gate_selector_is_rejected_by_grouped_cli() -> None:
    """@brief Reject unknown group names through the parser."""
    with pytest.raises(SystemExit) as raised:
        main(["verify", "gates", "typo"])
    assert raised.value.code == 2


# END OF FILE
