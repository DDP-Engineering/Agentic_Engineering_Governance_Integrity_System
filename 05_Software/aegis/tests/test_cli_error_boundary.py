#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_cli_error_boundary.py
@brief Public CLI tests for typed expected-failure handling.
@details Verifies stable human/JSON blocked responses while ensuring parser,
         process-control, and unexpected programming exceptions retain their
         normal semantics and diagnostic context.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn

import pytest

import aegis.cli as cli_module
from aegis.cli import main
from aegis.errors import CommandInputError

# TESTS


def test_configuration_error_keeps_structured_blocked_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Preserve structured configuration fields at the typed boundary.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    (tmp_path / ".agentic" / "workflow.toml").unlink()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as raised:
        main(["config", "validate", "--json"])

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["stage"] == "none"
    assert output["artifact"] == "none"
    assert output["next"] == "aegis config validate"
    assert output["code"] == "CONFIG-MISSING"
    assert output["key_path"] == ""
    assert output["error"]


def test_run_resolution_error_keeps_blocked_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Keep active-run resolution failures inside the expected boundary.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as raised:
        main(["run", "status", "--json"])

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["stage"] == "none"
    assert output["artifact"] == "none"
    assert output["next"] == "aegis config validate"
    assert "No active AEGIS run is selected" in output["error"]


def test_stage_operation_error_keeps_blocked_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Keep genuine workflow precondition failures human-remediable.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    _start_run(tmp_path, monkeypatch, capsys)

    with pytest.raises(SystemExit) as raised:
        main(["check", "record", "--json"])

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["stage"] == "intake"
    assert output["artifact"].endswith("/stages/intake/intake.toml")
    assert output["next"] == "aegis stage apply"
    assert "valid only during check or implementation" in output["error"]


def test_command_input_error_keeps_json_and_human_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Render a validly parsed missing local input in both output modes.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    _start_run(tmp_path, monkeypatch, capsys)

    with pytest.raises(SystemExit) as json_exit:
        main(["verify", "impact", "missing-paths.txt", "--json"])
    assert json_exit.value.code == 1
    json_output = json.loads(capsys.readouterr().out)
    assert json_output["status"] == "blocked"
    assert json_output["stage"] == "intake"
    assert json_output["artifact"].endswith("/stages/intake/intake.toml")
    assert json_output["next"] == "aegis stage apply"
    assert json_output["error"] == (
        "paths file does not exist: missing-paths.txt"
    )

    with pytest.raises(SystemExit) as human_exit:
        main(["verify", "impact", "missing-paths.txt"])
    assert human_exit.value.code == 1
    human_output = capsys.readouterr().out
    assert "status: blocked" in human_output
    assert "stage: intake" in human_output
    assert "artifact: " in human_output
    assert "next: aegis stage apply" in human_output
    assert "error: paths file does not exist: missing-paths.txt" in human_output

    with pytest.raises(CommandInputError):
        cli_module._read_paths_file(tmp_path, "missing-paths.txt")


def test_missing_validation_summary_is_typed_command_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Keep a missing requested workflow artifact as an expected input error.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    _start_run(tmp_path, monkeypatch, capsys)

    with pytest.raises(SystemExit) as raised:
        main(["verify", "status", "--json"])

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["error"] == "no validation summary; run `aegis verify run`"


def test_invalid_path_entry_is_typed_command_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Type a malformed line inside an otherwise valid paths file.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    _start_run(tmp_path, monkeypatch, capsys)
    (tmp_path / "paths.txt").write_text(
        "../outside.py\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as raised:
        main(["verify", "impact", "paths.txt", "--json"])

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["error"].startswith("invalid path in paths.txt at line 1:")


def test_malformed_component_manifest_is_typed_command_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Preserve blocked output for malformed operator-owned component data.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    _start_run(tmp_path, monkeypatch, capsys)
    (tmp_path / ".agentic" / "components.toml").write_text(
        "[components\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as raised:
        main(["adoption", "component-status", "--json"])

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["error"].startswith(
        "cannot load component manifest .agentic/components.toml:"
    )


def test_incidental_value_error_from_dispatch_is_not_reclassified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Let unexpected ValueError retain its traceback-producing semantics.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    _start_run(tmp_path, monkeypatch, capsys)

    def broken_dispatch(*args: object, **kwargs: object) -> NoReturn:
        """@brief Inject an incidental programming failure."""
        raise ValueError("incidental dispatch defect")

    monkeypatch.setattr(cli_module, "_dispatch", broken_dispatch)

    with pytest.raises(ValueError, match="incidental dispatch defect"):
        main(["run", "status", "--json"])

    assert "status" not in capsys.readouterr().out


@pytest.mark.parametrize(
    ("signal", "expected_type", "expected_code"),
    [
        (KeyboardInterrupt(), KeyboardInterrupt, None),
        (SystemExit(7), SystemExit, 7),
    ],
)
def test_process_control_exceptions_are_not_swallowed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    signal: BaseException,
    expected_type: type[BaseException],
    expected_code: int | None,
) -> None:
    """
    @brief Preserve interrupt and explicit process-exit behavior.
    @param[in] tmp_path Temporary repository root.
    @param[in] signal Injected process-control exception.
    @return None.
    """
    _start_run(tmp_path, monkeypatch, capsys)

    def interrupted_dispatch(*args: object, **kwargs: object) -> NoReturn:
        """@brief Inject one process-control exception."""
        raise signal

    monkeypatch.setattr(cli_module, "_dispatch", interrupted_dispatch)

    with pytest.raises(expected_type) as raised:
        main(["run", "status", "--json"])

    if isinstance(raised.value, SystemExit):
        assert raised.value.code == expected_code
    assert "status" not in capsys.readouterr().out


def test_argparse_errors_keep_parser_exit_behavior(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Leave parser syntax failures outside the workflow-error boundary.
    @return None.
    """
    with pytest.raises(SystemExit) as raised:
        main(["not-a-command"])

    assert raised.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
    assert "status: blocked" not in captured.out


# LOCAL HELPERS


def _start_run(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Start one selected run and consume its JSON response.
    @param[in] repo_root Temporary repository root.
    @return None.
    """
    monkeypatch.chdir(repo_root)
    main(["run", "start", "fix", "--json"])
    capsys.readouterr()


# END OF FILE
