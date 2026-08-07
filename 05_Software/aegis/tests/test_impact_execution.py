#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_impact_execution.py
@brief Public CLI coverage for safe focused impact-test execution.
@details Verifies argv-only selector execution, deterministic selection,
         fail-safe full-gate fallback, and transactional evidence publication.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import subprocess

import pytest

import aegis.cli as cli_module
import aegis.gates as gates_module
import aegis.store as store_module
from aegis.cli import main
from aegis.config import load_config
from aegis.requirements import create_requirement
from aegis.store import init_graph, journal_path

# CONSTANTS

_TEST_GATE_DISABLED = '[gates.test]\nmode = "disabled"\ncommands = []'


# HELPER FUNCTIONS


def _configure_test_gate(
    replace_workflow_toml: Callable[[str, str], Path],
    *,
    commands: str,
    impacted_command: str | None,
) -> None:
    """@brief Configure one enforced test gate for an impact execution test."""
    fragment = f'[gates.test]\nmode = "enforce"\ncommands = {commands}'
    if impacted_command is not None:
        fragment += f'\nimpacted_command = {impacted_command}'
    replace_workflow_toml(_TEST_GATE_DISABLED, fragment)


def _write_test(repo_root: Path, relative_path: str, identifier: str) -> None:
    """@brief Create one resolvable Python test selector target."""
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"def {identifier}():\n    assert True\n", encoding="utf-8")


def _add_requirement(
    repo_root: Path,
    *,
    affected_paths: list[str],
    linked_tests: list[str],
    verification: str = "Automated test",
) -> None:
    """@brief Persist one requirement used by the impact resolver."""
    create_requirement(
        repo_root,
        category="functional",
        priority="Must",
        requirement="The changed behavior remains covered.",
        rationale="Impact execution requires a deterministic test link.",
        verification=verification,
        affected_paths=affected_paths,
        linked_tests=linked_tests,
        config=load_config(repo_root),
    )


def _start_run(repo_root: Path) -> str:
    """@brief Create one selected run for public impact command execution."""
    return init_graph(repo_root, "fix", "Exercise focused impact execution").run_id


def _run_impact(
    paths_file: str,
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    """@brief Execute the public JSON impact-run command and decode its result."""
    main(["verify", "impact", paths_file, "--run", "--json"])
    return json.loads(capsys.readouterr().out)


# TESTS


def test_impact_run_executes_stable_deduplicated_argv_selectors(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Execute exact, directory, and glob matches through one argv prefix.
    @details Requires deduplicated, sorted selectors as separate argv
             values, never as shell-interpolated text.
    """
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command='["focused-command", "--selected"]',
    )
    for relative, identifier in (
        ("tests/test_alpha.py", "test_alpha"),
        ("tests/test_beta.py", "test_beta"),
    ):
        _write_test(tmp_path, relative, identifier)
    _add_requirement(
        tmp_path,
        affected_paths=["src/exact.py", "lib", "app/**/*.py"],
        linked_tests=["tests/test_beta.py::test_beta", "tests/test_alpha.py::test_alpha"],
    )
    _add_requirement(
        tmp_path,
        affected_paths=["src/exact.py"],
        linked_tests=["tests/test_alpha.py::test_alpha"],
    )
    (tmp_path / "changed.txt").write_text(
        "src/exact.py\nlib/math/core.py\napp/ui/view.py\n",
        encoding="utf-8",
    )
    _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls: list[tuple[list[str], bool]] = []

    def capture_argv(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        """@brief Capture the focused execution call without relying on quoting."""
        calls.append((list(args[0]), bool(kwargs["shell"])))
        return subprocess.CompletedProcess(args[0], 0, "focused ok", "")

    monkeypatch.setattr(gates_module.subprocess, "run", capture_argv)

    payload = _run_impact("changed.txt", capsys)

    assert payload["execution_status"] == "pass"
    assert payload["impact_execution"]["mode"] == "focused"
    assert payload["impact_execution"]["selectors"] == [
        "tests/test_alpha.py::test_alpha",
        "tests/test_beta.py::test_beta",
    ]
    assert calls == [(
        [
            "focused-command",
            "--selected",
            "tests/test_alpha.py::test_alpha",
            "tests/test_beta.py::test_beta",
        ],
        False,
    )]


def test_impact_run_falls_back_for_uncovered_and_testless_sources(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Fail safe to every full command for incomplete source coverage."""
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-one", "full-two"]',
        impacted_command='["focused-command"]',
    )
    _write_test(tmp_path, "tests/test_feature.py", "test_feature")
    _add_requirement(
        tmp_path,
        affected_paths=["src/testless.py"],
        linked_tests=[],
        verification="Manual: the behavior is inspected",
    )
    (tmp_path / "changed.txt").write_text(
        "src/uncovered.py\nsrc/testless.py\n",
        encoding="utf-8",
    )
    _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda _root, command, _timeout: (
            calls.append(command)
            or subprocess.CompletedProcess(command, 0, "full ok", "")
        ),
    )

    payload = _run_impact("changed.txt", capsys)

    assert payload["execution_status"] == "pass"
    assert payload["impact_execution"]["mode"] == "full-fallback"
    assert "uncovered changed source" in payload["impact_execution"]["fallback_reason"]
    assert calls == ["full-one", "full-two"]


def test_impact_run_falls_back_when_a_related_requirement_has_no_tests(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Execute the full gate when a covered source has no linked test."""
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command='["focused-command"]',
    )
    _add_requirement(
        tmp_path,
        affected_paths=["src/testless.py"],
        linked_tests=[],
        verification="Manual: the behavior is inspected",
    )
    (tmp_path / "changed.txt").write_text("src/testless.py\n", encoding="utf-8")
    _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda _root, command, _timeout: (
            calls.append(command)
            or subprocess.CompletedProcess(command, 0, "full ok", "")
        ),
    )

    payload = _run_impact("changed.txt", capsys)

    assert payload["impact_execution"]["mode"] == "full-fallback"
    assert "no linked tests" in payload["impact_execution"]["fallback_reason"]
    assert calls == ["full-command"]


def test_impact_run_falls_back_when_any_matched_requirement_is_testless(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Run every full command when mixed matched requirements lack coverage.
    @details Proves that one linked record cannot mask a testless matching
             record, and that output, evidence, and journal records describe
             only the full fallback execution.
    """
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command='["focused-command"]',
    )
    _write_test(tmp_path, "tests/test_linked.py", "test_linked")
    _add_requirement(
        tmp_path,
        affected_paths=["src/mixed.py"],
        linked_tests=["tests/test_linked.py::test_linked"],
    )
    _add_requirement(
        tmp_path,
        affected_paths=["src/mixed.py"],
        linked_tests=[],
        verification="Manual: the behavior is inspected",
    )
    (tmp_path / "changed.txt").write_text("src/mixed.py\n", encoding="utf-8")
    run_id = _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    full_calls: list[str] = []
    focused_calls: list[list[str]] = []
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda _root, command, _timeout: (
            full_calls.append(command)
            or subprocess.CompletedProcess(command, 0, "full ok", "")
        ),
    )

    def capture_focused(
        *args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        """@brief Record an unexpected focused launch without executing it."""
        focused_calls.append(list(args[0]))
        return subprocess.CompletedProcess(args[0], 0, "focused ok", "")

    monkeypatch.setattr(gates_module.subprocess, "run", capture_focused)

    payload = _run_impact("changed.txt", capsys)

    execution = payload["impact_execution"]
    assert payload["execution_status"] == "pass"
    assert payload["executed_count"] == 1
    assert execution["mode"] == "full-fallback"
    assert execution["fallback_reason"] == (
        "changed requirement has no linked tests: src/mixed.py"
    )
    assert full_calls == ["full-command"]
    assert focused_calls == []

    graph = json.loads(
        (tmp_path / ".agentic" / "runs" / run_id / "graph.json").read_text(
            encoding="utf-8"
        )
    )
    evidence = graph["evidence"][-1]
    assert evidence["command"] == "full-command"
    assert evidence["result"] == "pass"
    journal = [
        json.loads(line)
        for line in journal_path(tmp_path, run_id).read_text(encoding="utf-8").splitlines()
    ]
    gate_outputs = [
        event["data"] for event in journal if event["event"] == "gate.output"
    ]
    impact_event = next(
        event["data"]
        for event in reversed(journal)
        if event["event"] == "impact.execution"
    )
    assert [output["command"] for output in gate_outputs] == ["full-command"]
    assert impact_event["mode"] == execution["mode"]
    assert impact_event["fallback_reason"] == execution["fallback_reason"]
    assert impact_event["execution_status"] == "pass"
    assert impact_event["executed_count"] == 1


def test_impact_run_falls_back_for_a_git_rename_with_an_uncovered_old_path(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Treat both sides of a rename as impact input and fail safe."""
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command='["focused-command"]',
    )
    source = tmp_path / "src" / "before.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _write_test(tmp_path, "tests/test_feature.py", "test_feature")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    source.rename(tmp_path / "src" / "after.py")
    _add_requirement(
        tmp_path,
        affected_paths=["src/after.py"],
        linked_tests=["tests/test_feature.py::test_feature"],
    )
    _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda _root, command, _timeout: (
            calls.append(command)
            or subprocess.CompletedProcess(command, 0, "full ok", "")
        ),
    )

    main(["verify", "impact", "--run", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["impact_execution"]["mode"] == "full-fallback"
    assert "uncovered changed source: src/before.py" in payload["impact_execution"]["fallback_reason"]
    assert calls == ["full-command"]


@pytest.mark.parametrize(
    "selector",
    [
        "-k=unexpected",
        "tests/test_safe.py::test_safe\n--capture=no",
        "tests/test_safe.py::test_safe\x00suffix",
        "../outside.py::test_outside",
    ],
    ids=["leading-option", "newline", "nul", "repository-escape"],
)
def test_impact_run_rejects_unsafe_selector_and_uses_full_fallback(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    selector: str,
) -> None:
    """@brief Keep hostile or malformed selectors out of the focused argv."""
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command='["focused-command"]',
    )
    _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli_module,
        "impact",
        lambda *_args, **_kwargs: [
            {
                "file": "docs/notes.md",
                "uncovered": False,
                "requirements": [{"id": "REQ-1", "linked_tests": [selector]}],
                "linked_tests": [selector],
                "full_regression_recommended": False,
            }
        ],
    )
    full_calls: list[str] = []
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda _root, command, _timeout: (
            full_calls.append(command)
            or subprocess.CompletedProcess(command, 0, "full ok", "")
        ),
    )
    focused_calls: list[object] = []
    monkeypatch.setattr(
        gates_module.subprocess,
        "run",
        lambda *args, **kwargs: focused_calls.append((args, kwargs)),
    )
    (tmp_path / "changed.txt").write_text("docs/notes.md\n", encoding="utf-8")

    payload = _run_impact("changed.txt", capsys)

    assert payload["impact_execution"]["mode"] == "full-fallback"
    assert "unsafe selector" in payload["impact_execution"]["fallback_reason"]
    assert full_calls == ["full-command"]
    assert focused_calls == []


def test_impact_run_missing_prefix_falls_back_and_no_commands_is_nothing_ran(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Preserve fallback and WP4 nothing-ran distinctions."""
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command=None,
    )
    _write_test(tmp_path, "tests/test_feature.py", "test_feature")
    _add_requirement(
        tmp_path,
        affected_paths=["src/feature.py"],
        linked_tests=["tests/test_feature.py::test_feature"],
    )
    (tmp_path / "changed.txt").write_text("src/feature.py\n", encoding="utf-8")
    run_id = _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)
    full_calls: list[str] = []
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda _root, command, _timeout: (
            full_calls.append(command)
            or subprocess.CompletedProcess(command, 0, "full ok", "")
        ),
    )

    fallback = _run_impact("changed.txt", capsys)

    assert fallback["impact_execution"]["mode"] == "full-fallback"
    assert "not configured" in fallback["impact_execution"]["fallback_reason"]
    assert full_calls == ["full-command"]

    replace_workflow_toml(
        '[gates.test]\nmode = "enforce"\ncommands = ["full-command"]',
        _TEST_GATE_DISABLED,
    )
    with pytest.raises(SystemExit) as raised:
        _run_impact("changed.txt", capsys)
    nothing_ran = json.loads(capsys.readouterr().out)

    assert raised.value.code == 1
    assert nothing_ran["execution_status"] == "nothing-ran"
    assert nothing_ran["executed_count"] == 0
    assert "no executable focused or full test command" in nothing_ran["reason"].lower()
    events = [
        json.loads(line)["event"]
        for line in journal_path(tmp_path, run_id).read_text(encoding="utf-8").splitlines()
    ]
    assert "impact.execution" in events


@pytest.mark.parametrize(
    ("failure", "returncode"),
    [
        (subprocess.TimeoutExpired(["focused-command"], 30), 124),
        (FileNotFoundError(2, "not found"), 127),
    ],
    ids=["timeout", "unlaunchable"],
)
def test_impact_run_records_focused_timeout_and_launch_failure(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: BaseException,
    returncode: int,
) -> None:
    """@brief Persist normal failing test-gate evidence for focused launch errors."""
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command='["focused-command"]',
    )
    _write_test(tmp_path, "tests/test_feature.py", "test_feature")
    _add_requirement(
        tmp_path,
        affected_paths=["src/feature.py"],
        linked_tests=["tests/test_feature.py::test_feature"],
    )
    (tmp_path / "changed.txt").write_text("src/feature.py\n", encoding="utf-8")
    run_id = _start_run(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fail_launch(*_args: object, **_kwargs: object) -> object:
        """@brief Raise one launcher failure from the argv-only subprocess seam."""
        raise failure

    monkeypatch.setattr(gates_module.subprocess, "run", fail_launch)

    with pytest.raises(SystemExit) as raised:
        _run_impact("changed.txt", capsys)
    payload = json.loads(capsys.readouterr().out)

    assert raised.value.code == returncode
    assert payload["execution_status"] == "fail"
    evidence = json.loads(
        (tmp_path / ".agentic" / "runs" / run_id / "graph.json").read_text(
            encoding="utf-8"
        )
    )["evidence"]
    assert evidence[-1]["gate_name"] == "test"
    assert evidence[-1]["result"] == "fail"
    assert evidence[-1]["exit_status"] == returncode
    assert (tmp_path / evidence[-1]["output_log"]).is_file()


def test_impact_run_publication_rolls_back_output_evidence_and_journal(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Keep output, evidence, and journal publication atomic."""
    _configure_test_gate(
        replace_workflow_toml,
        commands='["full-command"]',
        impacted_command='["focused-command"]',
    )
    _write_test(tmp_path, "tests/test_feature.py", "test_feature")
    _add_requirement(
        tmp_path,
        affected_paths=["src/feature.py"],
        linked_tests=["tests/test_feature.py::test_feature"],
    )
    (tmp_path / "changed.txt").write_text("src/feature.py\n", encoding="utf-8")
    run_id = _start_run(tmp_path)
    graph_path = tmp_path / ".agentic" / "runs" / run_id / "graph.json"
    target_journal = journal_path(tmp_path, run_id)
    graph_before = graph_path.read_bytes()
    journal_before = target_journal.read_bytes()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        gates_module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ok", ""),
    )
    original_write = store_module.atomic_write_bytes

    def fail_impact_journal(path: Path, content: bytes) -> None:
        """@brief Fail the journal replacement after the graph replacement."""
        if path == target_journal and b'"event": "impact.execution"' in content:
            raise OSError("impact journal unavailable")
        original_write(path, content)

    monkeypatch.setattr(store_module, "atomic_write_bytes", fail_impact_journal)

    with pytest.raises(OSError, match="impact journal unavailable"):
        _run_impact("changed.txt", capsys)

    assert graph_path.read_bytes() == graph_before
    assert target_journal.read_bytes() == journal_before
    assert not list((tmp_path / ".agentic" / "runs" / run_id).rglob("*.log"))


def test_reporting_only_impact_does_not_execute_or_change_its_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Preserve the reporting-only impact response when --run is absent."""
    _start_run(tmp_path)
    (tmp_path / "changed.txt").write_text("docs/notes.md\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        gates_module,
        "_run_command",
        lambda *_args, **_kwargs: pytest.fail("reporting-only impact must not execute"),
    )

    main(["verify", "impact", "changed.txt", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert set(payload) == {"status", "stage", "artifact", "next", "impact"}


# END OF FILE
