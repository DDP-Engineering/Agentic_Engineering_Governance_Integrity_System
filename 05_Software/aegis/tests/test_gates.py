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
@version 2.1.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess
import threading

import pytest

import aegis.gates as gates_module
from aegis.cli import main
from aegis.config import ConfigurationError, load_config
from aegis.gates import _argv_for_simple_command, run_gates
from aegis.store import init_graph, load_graph, set_access_mode

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


def test_slow_gate_does_not_block_concurrent_graph_operation(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Allow a same-run graph operation while a gate subprocess is active.
    @param[in] tmp_path Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @version 0.1.0
    """
    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\nmode = "enforce"\ncommands = ["slow-gate"]',
    )
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "fix", "Exercise gate lock scope")
    started = threading.Event()
    release = threading.Event()
    operation_done = threading.Event()
    gate_errors: list[BaseException] = []
    operation_errors: list[BaseException] = []

    def slow_runner(
        _repo_root: Path,
        command: str,
        _timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        """
        @brief Hold the scripted subprocess phase until the test releases it.
        @version 0.1.0
        """
        started.set()
        if not release.wait(5):
            raise RuntimeError("slow gate release was not received")
        return subprocess.CompletedProcess(command, 0, "gate complete", "")

    monkeypatch.setattr(gates_module, "_run_command", slow_runner)

    def execute_gate() -> None:
        """@brief Run the gate command in the background."""
        try:
            run_gates(tmp_path, graph.run_id, config, ["test"])
        except BaseException as exc:
            gate_errors.append(exc)

    def update_graph() -> None:
        """@brief Perform a second serialized AEGIS graph operation."""
        try:
            current = load_graph(tmp_path, graph.run_id)
            set_access_mode(
                tmp_path,
                current,
                "elevated",
                "Concurrent operation during gate execution.",
            )
        except BaseException as exc:
            operation_errors.append(exc)
        finally:
            operation_done.set()

    gate_thread = threading.Thread(target=execute_gate)
    operation_thread = threading.Thread(target=update_graph)
    gate_thread.start()
    started_in_time = started.wait(5)
    try:
        assert started_in_time, gate_errors
        operation_thread.start()
        completed_while_gate_running = operation_done.wait(1)
    finally:
        release.set()
        gate_thread.join(5)
        if operation_thread.ident is not None:
            operation_thread.join(5)

    assert completed_while_gate_running
    assert not gate_thread.is_alive()
    assert not operation_thread.is_alive()
    assert gate_errors == []
    assert operation_errors == []
    persisted = load_graph(tmp_path, graph.run_id)
    assert persisted.access_mode == "elevated"
    assert [(item.gate_name, item.result) for item in persisted.evidence] == [
        ("test", "pass")
    ]


# END OF FILE
