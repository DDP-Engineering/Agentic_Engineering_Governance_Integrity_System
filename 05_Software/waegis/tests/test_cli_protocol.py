#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Verify WAEGIS CLI protocol containment and presenter parity."""

from __future__ import annotations

import json
import subprocess
import sys

from test_lifecycle import make_payload

from waegis.composition import create_application
from waegis.interface.cli import run_cli


def test_machine_parse_failure_is_one_structured_line(tmp_path, capsys) -> None:
    """Operator-producible malformed CLI input never exits through argparse."""
    app = create_application(make_payload(tmp_path))
    exit_code = run_cli(app, ["--format", "json", "install-plan", "--future"])
    captured = capsys.readouterr()
    response = json.loads(captured.out)

    assert exit_code == 2
    assert captured.err == ""
    assert captured.out.count("\n") == 1
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == "invalid_input"
    assert "Traceback" not in captured.out


def test_human_and_json_present_the_same_help_semantics(tmp_path, capsys) -> None:
    """Both presenters consume one result without changing its meaning."""
    app = create_application(make_payload(tmp_path))
    human_exit = run_cli(app, ["help-show"])
    human = capsys.readouterr()
    json_exit = run_cli(app, ["--format", "json", "help-show"])
    machine_output = capsys.readouterr()
    machine = json.loads(machine_output.out)

    assert human_exit == json_exit == 0
    assert machine["message"] in human.out
    assert machine["operation"] in human.out
    assert machine["operation_status"] in human.out
    assert machine["product_version"] in human.out


def test_module_help_routes_through_registry_without_an_error(tmp_path, capsys) -> None:
    """IP-16: The mandated module help command succeeds through help.show."""
    app = create_application(make_payload(tmp_path))

    exit_code = run_cli(app, ["--help"])

    assert exit_code == 0
    assert "help.show" in capsys.readouterr().out


def test_python_module_forwards_process_arguments() -> None:
    """IP-16: python -m waegis forwards its real process arguments."""
    completed = subprocess.run(
        [sys.executable, "-m", "waegis", "--help"],
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0
    assert b"help.show" in completed.stdout


def test_operator_interrupt_is_bounded_protocol_output(
    tmp_path, capsys, monkeypatch
) -> None:
    """IP-16: An operator interrupt cannot escape the CLI as a traceback."""
    app = create_application(make_payload(tmp_path))

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(app, "execute", interrupt)
    exit_code = run_cli(app, ["--format", "json", "help-show"])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert captured.err == ""
    response = json.loads(captured.out)
    assert response["error"]["code"] == "internal_error"
    assert "Traceback" not in captured.out
