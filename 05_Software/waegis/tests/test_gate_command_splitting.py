#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_gate_command_splitting.py
@brief Host-correct argv splitting for configured gate command strings (DPT-F07).
@details The deployment test observed a repository-root ``uv run --directory``
         gate exiting nonzero while the identical suite passed by hand from the
         package root. The cause was not uv: ``_read_gates`` split the
         configured command with POSIX ``shlex.split``, where a backslash is an
         escape character, so every unquoted native Windows path in a gate
         command silently lost its separators before the child ever started.
@details The Windows cases run a *real* child process against a real directory
         tree whose path must survive splitting intact, because an assertion on
         the argv list alone cannot show that the resulting command actually
         locates the package. One test deliberately pins the pre-fix behaviour
         (POSIX split -> mangled path -> nonzero child) so the regression proves
         failure-before as well as literal-after.
"""

# IMPORTS

from __future__ import annotations

import os
import shlex
from pathlib import Path

import pytest
from waegis.commands.new import (
    WORKFLOW_TOML_RELATIVE_PATH,
    _read_gates,
    split_gate_command,
)
from waegis.probes.runner import SubprocessCommandRunner

# CONSTANTS

# @brief Gate command strings whose split must be identical on every host:
#        no backslashes, or backslashes protected by quotes.
_HOST_NEUTRAL_COMMANDS = (
    "ruff check .",
    "uv run --directory 05_Software/pkg python -m pytest -q tests",
    'python -m pytest -q "tests/with space"',
    'uv run --directory "C:\\sp ace\\pkg" python -m pytest',
    "uv run --directory 'C:\\sp ace\\pkg' python -m pytest",
)

# @brief The DPT-F07 shape: a native Windows path written unquoted, exactly as
#        the field's own help text ("Run exactly as given") invites.
_NATIVE_PATH_COMMAND = "python 05_Software\\pkg\\ok.py"

# @brief What the pre-fix POSIX split produced from the command above.
_MANGLED_ARGV = ["python", "05_Softwarepkgok.py"]

_WINDOWS_ONLY = pytest.mark.skipif(
    os.name != "nt",
    reason="backslash path syntax is meaningful only on Windows",
)


# LOCAL HELPERS


def _monorepo(root: Path) -> Path:
    """
    @brief      Build the disposable monorepo shape the finding describes:
                a package below the repository root holding a trivial script.
    @param[in]  root Repository root (the wizard's ``cwd=target``).
    @return     The created package directory.
    @exception  OSError If the tree cannot be created.
    """
    package = root / "05_Software" / "pkg"
    package.mkdir(parents=True)
    (package / "ok.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    return package


def _write_gate(root: Path, command: str) -> None:
    """
    @brief      Write the minimal workflow.toml ``_read_gates`` reads.
    @param[in]  root Repository root.
    @param[in]  command The single enforced test-gate command string.
    @return     None
    @exception  OSError If the file cannot be written.
    """
    path = root / WORKFLOW_TOML_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[gates.test]\nmode = 'enforce'\ncommands = [\n  '''" + command + "''',\n]\n",
        encoding="utf-8",
    )


# TESTS


@pytest.mark.parametrize("command", _HOST_NEUTRAL_COMMANDS)
def test_host_neutral_commands_split_exactly_as_before(command: str) -> None:
    """
    @brief      Commands without unquoted backslashes are unaffected on every
                host, so no existing configuration changes meaning.
    @details    This is the compatibility half of the fix: quote handling,
                quoted spaces, and quote removal all stay POSIX. On a
                non-Windows host it additionally asserts that the new splitter
                is byte-identical to ``shlex.split`` for these inputs.
    """
    assert split_gate_command(command) == shlex.split(command)


def test_posix_hosts_are_unchanged() -> None:
    """
    @brief      On a non-Windows host the splitter is ``shlex.split``, including
                for backslash escapes, so Linux gate behaviour is untouched.
    """
    if os.name == "nt":
        pytest.skip("asserts the POSIX branch")
    assert split_gate_command(_NATIVE_PATH_COMMAND) == shlex.split(_NATIVE_PATH_COMMAND)


@_WINDOWS_ONLY
def test_native_windows_path_survives_splitting() -> None:
    """
    @brief      A gate command containing an unquoted native Windows path keeps
                its separators (the literal-after half of DPT-F07).
    """
    assert split_gate_command(_NATIVE_PATH_COMMAND) == ["python", "05_Software\\pkg\\ok.py"]


@_WINDOWS_ONLY
def test_configured_native_path_gate_runs_a_real_child(tmp_path: Path) -> None:
    """
    @brief      End to end: the configured gate string is read from
                workflow.toml, split, and executed as a real child process from
                the repository root, and it finds its package.
    @details    Uses the shipping ``SubprocessCommandRunner`` with ``cwd=target``
                — the same argv-array, no-shell, explicit-cwd contract the
                wizard's gate step uses — so a pass here means a real Windows
                process resolved the path.
    """
    _monorepo(tmp_path)
    _write_gate(tmp_path, _NATIVE_PATH_COMMAND)

    argv = _read_gates(tmp_path)["test"][1][0]
    assert argv == ["python", "05_Software\\pkg\\ok.py"]

    result = SubprocessCommandRunner().run(tuple(argv), timeout=60.0, cwd=tmp_path)

    assert result.found is True
    assert result.exit_code == 0, result.stderr


@_WINDOWS_ONLY
def test_posix_split_of_the_same_gate_fails_the_child(tmp_path: Path) -> None:
    """
    @brief      Pin the DPT-F07 mechanism: the pre-fix POSIX split of the very
                same gate string yields a path whose separators are gone, and
                the real child process fails on it.
    @details    Without this, a future change back to ``shlex.split`` would only
                break the assertion above with no record of why it mattered.
    """
    _monorepo(tmp_path)

    mangled = shlex.split(_NATIVE_PATH_COMMAND)
    assert mangled == _MANGLED_ARGV

    result = SubprocessCommandRunner().run(tuple(mangled), timeout=60.0, cwd=tmp_path)

    assert result.exit_code not in (0, None), "the mangled gate must not succeed"


# END OF FILE
