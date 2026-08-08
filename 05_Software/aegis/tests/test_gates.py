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
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

import aegis.gates as gates_module
from aegis.cli import main
from aegis.config import DEFAULT_GATE_TIMEOUT_SECONDS, ConfigurationError, load_config
from aegis.gates import (
    _argv_for_simple_command,
    _run_command,
    gate_failure_blockers,
    run_gates,
)
from aegis.invariants import _no_regression
from aegis.models import Graph
from aegis.store import init_graph, load_graph, save_graph, set_access_mode
from aegis.verification import _gate_result

# TESTS


def test_timeout_kills_descendants_that_hold_captured_pipes(tmp_path: Path) -> None:
    """@brief A grandchild cannot keep a timed-out gate blocked indefinitely."""
    script = (
        "import subprocess,sys,time;"
        "subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
        "time.sleep(60)"
    )
    started = time.monotonic()

    with pytest.raises(subprocess.TimeoutExpired):
        gates_module._run_with_timeout(
            tmp_path,
            [sys.executable, "-c", script],
            shell=False,
            timeout=1,
        )

    assert time.monotonic() - started < 10


@pytest.mark.parametrize(
    "refusal",
    [
        PermissionError(5, "Access is denied"),
        FileNotFoundError(2, "The system cannot find the file specified"),
    ],
    ids=["permission-denied", "pathext-shim-not-found"],
)
def test_windows_launch_refusal_retries_the_command_through_the_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    refusal: OSError,
) -> None:
    """
    @brief Launch an argv-eligible gate through the shell when direct exec is
           refused by Windows.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest replacement helper.
    @param[in] refusal Launch refusal raised by direct exec; `PermissionError`
               for an unlaunchable target and `FileNotFoundError` for a
               PATH-resolved `.cmd`/`.bat` shim such as `npm`, which
               CreateProcess cannot find because it does not apply `PATHEXT`.
    @return None.
    """
    monkeypatch.setattr("os.name", "nt")
    calls: list[bool] = []

    def refuse_then_succeed(*args: object, **kwargs: object) -> object:
        """@brief Refuse direct exec once, then complete through the shell."""
        calls.append(bool(kwargs["shell"]))
        if not kwargs["shell"]:
            raise refusal
        return subprocess.CompletedProcess("npm run build", 0, "built", "")

    monkeypatch.setattr(gates_module, "_run_with_timeout", refuse_then_succeed)

    result = _run_command(tmp_path, "npm run build", 30)

    assert calls == [False, True]
    assert result.returncode == 0
    assert result.stdout == "built"


def test_timeout_is_never_relaunched_through_the_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Keep a timed-out gate on the timeout path instead of retrying it.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @details `subprocess.TimeoutExpired` is not an `OSError`, so the broadened
             Windows launch-refusal retry must not reach it.
    """
    monkeypatch.setattr("os.name", "nt")
    calls: list[bool] = []

    def time_out(*args: object, **kwargs: object) -> object:
        """@brief Time out on every launch attempt."""
        calls.append(bool(kwargs["shell"]))
        raise subprocess.TimeoutExpired("pytest -q", 30)

    monkeypatch.setattr(gates_module, "_run_with_timeout", time_out)

    result = _run_command(tmp_path, "pytest -q", 30)

    assert calls == [False]
    assert result.returncode == 124
    assert "TimeoutExpired" in result.stderr


@pytest.mark.parametrize(
    ("retry_error", "returncode"),
    [
        (subprocess.TimeoutExpired("pytest -q", 30), 124),
        (OSError("shell unavailable"), 127),
    ],
)
def test_failed_shell_retry_stays_on_the_evidence_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    retry_error: BaseException,
    returncode: int,
) -> None:
    """
    @brief Synthesize a failing gate when the shell retry also cannot complete.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest replacement helper.
    @param[in] retry_error Failure raised by the retried shell launch.
    @param[in] returncode Synthesized timeout or unlaunchable exit status.
    @return None.
    """
    monkeypatch.setattr("os.name", "nt")

    def refuse_then_fail(*args: object, **kwargs: object) -> object:
        """@brief Refuse direct exec, then fail the shell retry."""
        if not kwargs["shell"]:
            raise PermissionError(5, "Access is denied")
        raise retry_error

    monkeypatch.setattr(gates_module, "_run_with_timeout", refuse_then_fail)

    result = _run_command(tmp_path, "pytest -q", 30)

    assert result.returncode == returncode
    assert result.stdout == ""
    assert type(retry_error).__name__ in result.stderr


@pytest.mark.parametrize(
    ("os_name", "command"),
    [("posix", "pytest -q"), ("nt", "pytest -q && ruff check")],
)
def test_permission_error_is_not_retried_outside_windows_direct_exec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_name: str,
    command: str,
) -> None:
    """
    @brief Report a refused launch as unlaunchable when no retry applies.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest replacement helper.
    @param[in] os_name Platform reported to the gate runner.
    @param[in] command Argv-eligible or shell-only gate command.
    @return None.
    """
    monkeypatch.setattr("os.name", os_name)
    calls: list[bool] = []

    def always_refuse(*args: object, **kwargs: object) -> object:
        """@brief Refuse every launch attempt."""
        calls.append(bool(kwargs["shell"]))
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(gates_module, "_run_with_timeout", always_refuse)

    result = _run_command(tmp_path, command, 30)

    assert len(calls) == 1
    assert result.returncode == 127
    assert "PermissionError" in result.stderr


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


def test_gate_timeout_defaults_when_absent(tmp_path: Path) -> None:
    """@brief Fall back to DEFAULT_GATE_TIMEOUT_SECONDS when unconfigured."""
    config = load_config(tmp_path)
    assert config.gates.test.timeout == DEFAULT_GATE_TIMEOUT_SECONDS
    assert config.gates.build.timeout == DEFAULT_GATE_TIMEOUT_SECONDS


def test_gate_timeout_accepts_a_configured_override(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Parse a per-gate timeout override from workflow.toml."""
    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\nmode = "disabled"\ncommands = []\ntimeout = 2400',
    )
    config = load_config(tmp_path)
    assert config.gates.test.timeout == 2400
    assert config.gates.build.timeout == DEFAULT_GATE_TIMEOUT_SECONDS


def test_gate_timeout_rejects_a_non_positive_value(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Reject a zero or negative configured gate timeout."""
    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\nmode = "disabled"\ncommands = []\ntimeout = 0',
    )
    with pytest.raises(ConfigurationError) as raised:
        load_config(tmp_path)
    assert raised.value.key_path == "gates.test.timeout"


def test_impacted_command_is_optional_argv_and_rejects_control_characters(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Preserve schema-3 omission while rejecting unsafe argv prefixes."""
    assert load_config(tmp_path).gates.test.impacted_command == ()

    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\nmode = "disabled"\ncommands = []\n'
        'impacted_command = ["python", "-m", "pytest", "-q"]',
    )
    assert load_config(tmp_path).gates.test.impacted_command == (
        "python",
        "-m",
        "pytest",
        "-q",
    )

    replace_workflow_toml(
        'impacted_command = ["python", "-m", "pytest", "-q"]',
        'impacted_command = ["python\\n-m"]',
    )
    with pytest.raises(ConfigurationError) as raised:
        load_config(tmp_path)
    assert raised.value.key_path == "gates.test.impacted_command"


def test_run_gates_uses_each_groups_own_configured_timeout(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Pass each gate group's configured timeout to its own commands."""
    replace_workflow_toml(
        '[gates.lint]\nmode = "disabled"\ncommands = []',
        '[gates.lint]\nmode = "enforce"\ncommands = ["lint-cmd"]\ntimeout = 15',
    )
    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\nmode = "enforce"\ncommands = ["test-cmd"]\ntimeout = 45',
    )
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "fix", "Exercise per-gate timeout wiring")
    observed: dict[str, int] = {}

    def capturing_runner(
        _repo_root: Path,
        command: str,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        """@brief Record the timeout each command was actually invoked with."""
        observed[command] = timeout
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(gates_module, "_run_command", capturing_runner)
    run_gates(tmp_path, graph.run_id, config, ["lint", "test"])

    assert observed == {"lint-cmd": 15, "test-cmd": 45}


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


def _enforced_test_gate_graph(
    repo_root: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    stage: str = "implementation",
) -> Graph:
    """
    @brief Enforce the `test` gate and persist a graph at a scanned stage.
    @param[in] repo_root Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] stage Active stage the gate evidence is recorded at.
    @return Persisted graph ready for `run_gates`.
    """
    replace_workflow_toml(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\nmode = "enforce"\ncommands = ["test-cmd"]',
    )
    graph = init_graph(repo_root, "fix", "Exercise gate evidence supersession")
    graph.stage = stage  # type: ignore[assignment]
    save_graph(repo_root, graph)
    return graph


def _scripted_gate_runner(
    monkeypatch: pytest.MonkeyPatch,
    *results: tuple[int, str, str],
) -> None:
    """
    @brief Return one scripted gate result per `run_gates` command execution.
    @param[in] monkeypatch Pytest replacement helper.
    @param[in] results Ordered `(returncode, stdout, stderr)` triples.
    @return None.
    """
    pending = list(results)

    def scripted(
        _repo_root: Path,
        command: str,
        _timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        """@brief Hand back the next scripted result for this command."""
        returncode, stdout, stderr = pending.pop(0)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    monkeypatch.setattr(gates_module, "_run_command", scripted)


def test_passing_gate_rerun_supersedes_the_prior_failure(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Let a fixed gate go green again instead of failing forever.
    @param[in] tmp_path Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @details Without supersession the first failing record stays `active`, so
             `_gate_result` keeps reporting `failed`, `gate_failure_blockers`
             keeps yielding `gate:test`, and INV-4 keeps reporting a live
             regression after the failure was already fixed.
    """
    graph = _enforced_test_gate_graph(tmp_path, replace_workflow_toml)
    config = load_config(tmp_path)
    _scripted_gate_runner(monkeypatch, (1, "", "assertion failed"), (0, "ok", ""))

    assert run_gates(tmp_path, graph.run_id, config, ["test"]) == 1
    assert run_gates(tmp_path, graph.run_id, config, ["test"]) == 0

    persisted = load_graph(tmp_path, graph.run_id)
    failed, passed = persisted.evidence
    assert (failed.result, failed.status) == ("fail", "superseded")
    assert failed.superseded_by == passed.id
    assert failed.supersede_reason is not None
    assert (passed.result, passed.status) == ("pass", "active")
    assert _gate_result(persisted, "test") == "passed"
    assert gate_failure_blockers(persisted, config, ["test"]) == []
    assert _no_regression(persisted, config).holds is True


def test_failing_gate_rerun_never_retires_an_earlier_pass(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Keep an earlier pass active so INV-4 still sees a regression.
    @param[in] tmp_path Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @details Retiring the pass would hide that the command once succeeded,
             which is exactly the regression signal INV-4 exists to report.
    """
    graph = _enforced_test_gate_graph(tmp_path, replace_workflow_toml)
    config = load_config(tmp_path)
    _scripted_gate_runner(monkeypatch, (0, "ok", ""), (1, "", "assertion failed"))

    assert run_gates(tmp_path, graph.run_id, config, ["test"]) == 0
    assert run_gates(tmp_path, graph.run_id, config, ["test"]) == 1

    persisted = load_graph(tmp_path, graph.run_id)
    passed, failed = persisted.evidence
    assert (passed.result, passed.status) == ("pass", "active")
    assert (failed.result, failed.status) == ("fail", "active")
    assert _gate_result(persisted, "test") == "failed"
    assert _no_regression(persisted, config).holds is False


def test_same_result_gate_rerun_supersedes_its_predecessor(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Replace a repeated identical observation rather than accumulate it.
    @param[in] tmp_path Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    """
    graph = _enforced_test_gate_graph(tmp_path, replace_workflow_toml)
    config = load_config(tmp_path)
    _scripted_gate_runner(monkeypatch, (1, "", "first"), (1, "", "second"))

    run_gates(tmp_path, graph.run_id, config, ["test"])
    run_gates(tmp_path, graph.run_id, config, ["test"])

    persisted = load_graph(tmp_path, graph.run_id)
    first, second = persisted.evidence
    assert first.status == "superseded"
    assert first.superseded_by == second.id
    assert second.status == "active"
    assert _gate_result(persisted, "test") == "failed"


def test_check_stage_gate_failure_is_retired_by_a_later_validation_pass(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Keep the summary status and the exit code telling the same story.
    @param[in] tmp_path Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @details At the check stage tests are red by design, so an enforced gate
             fails there. INV-4 ignores that record because it scans only
             implementation/validation/delivery, so `verify run` at validation
             exits 0 — while `_gate_result` reads every active record and would
             report `failed` in `validation-summary.json`. Supersession is what
             removes the divergence: the validation pass retires the
             check-stage failure of the same command across stages.
    """
    graph = _enforced_test_gate_graph(
        tmp_path, replace_workflow_toml, stage="check"
    )
    config = load_config(tmp_path)
    _scripted_gate_runner(monkeypatch, (1, "", "red by design"), (0, "ok", ""))
    run_gates(tmp_path, graph.run_id, config, ["test"])

    graph = load_graph(tmp_path, graph.run_id)
    graph.stage = "validation"  # type: ignore[assignment]
    save_graph(tmp_path, graph)
    assert run_gates(tmp_path, graph.run_id, config, ["test"]) == 0

    persisted = load_graph(tmp_path, graph.run_id)
    red, green = persisted.evidence
    assert (red.stage, red.status) == ("check", "superseded")
    assert (green.stage, green.status) == ("validation", "active")
    assert _gate_result(persisted, "test") == "passed"
    assert _no_regression(persisted, config).holds is True


def test_gate_evidence_records_the_captured_output_log(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Persist gate stdout/stderr so a failure is diagnosable.
    @param[in] tmp_path Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @details The journal already carries a `gate.output` event, but it has no
             CLI read surface, so the evidence record must carry the log path.
    """
    graph = _enforced_test_gate_graph(tmp_path, replace_workflow_toml)
    config = load_config(tmp_path)
    _scripted_gate_runner(
        monkeypatch,
        (1, "collected 1 item", "ModuleNotFoundError: No module named 'numpy'"),
    )

    run_gates(tmp_path, graph.run_id, config, ["test"])

    recorded = load_graph(tmp_path, graph.run_id).evidence[0]
    assert recorded.output_log is not None
    log_path = tmp_path / recorded.output_log
    assert log_path.is_file()
    captured = log_path.read_text(encoding="utf-8")
    assert "collected 1 item" in captured
    assert "ModuleNotFoundError: No module named 'numpy'" in captured


def test_superseded_gate_evidence_keeps_its_own_output_log(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief A superseded gate record's log is not overwritten by the rerun.
    @param[in] tmp_path Temporary repository root.
    @param[in] replace_workflow_toml Workflow configuration editor.
    @param[in] monkeypatch Pytest replacement helper.
    @return None.
    @details Regression test (B24, 2026-08-04): the log filename was
             `gate-<name>-<ordinal>-<stage>.log`, so a rerun of the same gate at
             the same stage reused the same ordinal/stage pair and overwrote the
             file. Before B11 added supersession there was no historical gate
             record left pointing at it; after B11, every rerun creates one, and
             the record whose log gets clobbered is precisely the failure an
             agent would want to read. The fix folds the evidence ID — unique
             and stable — into the filename.
    """
    graph = _enforced_test_gate_graph(tmp_path, replace_workflow_toml)
    config = load_config(tmp_path)
    _scripted_gate_runner(monkeypatch, (1, "", "first failure"), (0, "ok", ""))

    run_gates(tmp_path, graph.run_id, config, ["test"])
    run_gates(tmp_path, graph.run_id, config, ["test"])

    persisted = load_graph(tmp_path, graph.run_id)
    failed, passed = persisted.evidence
    assert failed.status == "superseded"
    assert failed.output_log != passed.output_log
    failed_log = tmp_path / failed.output_log
    passed_log = tmp_path / passed.output_log
    assert failed_log.is_file()
    assert passed_log.is_file()
    assert "first failure" in failed_log.read_text(encoding="utf-8")
    assert "first failure" not in passed_log.read_text(encoding="utf-8")


# END OF FILE
