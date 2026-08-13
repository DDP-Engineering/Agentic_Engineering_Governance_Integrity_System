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

import pytest
from test_lifecycle import make_payload

from waegis import composition
from waegis.composition import create_application
from waegis.domain.plans import PlanError
from waegis.interface.cli import run_cli


def test_machine_parse_failure_is_one_structured_line(tmp_path, capsys) -> None:
    """Operator-producible malformed CLI input never exits through argparse."""
    app = create_application(make_payload(tmp_path))
    exit_code = run_cli(app, ["--format=json", "install-plan", "--future"])
    captured = capsys.readouterr()
    response = json.loads(captured.out)

    assert exit_code == 2
    assert captured.err == ""
    assert captured.out.count("\n") == 1
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == "invalid_input"
    assert "Traceback" not in captured.out


def test_machine_output_is_compact_utf8_json_with_one_lf(
    tmp_path, capsys, monkeypatch
) -> None:
    """PR-PROTO-001, PR-ENC-001: Machine output is strict canonical JSON."""
    app = create_application(make_payload(tmp_path))
    original_dumps = json.dumps
    dump_options = []

    def observed_dumps(value, **options):
        dump_options.append(options)
        return original_dumps(value, **options)

    monkeypatch.setattr("waegis.interface.cli.json.dumps", observed_dumps)
    monkeypatch.setattr(
        app,
        "execute",
        lambda *_args, **_kwargs: app.error_result(
            "help.show", "invalid_input", "Entrée non valide."
        ),
    )

    exit_code = run_cli(app, ["--format=json", "help-show"])
    captured = capsys.readouterr()
    response = json.loads(captured.out)
    expected = original_dumps(
        response,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )

    assert exit_code == 2
    assert captured.err == ""
    assert captured.out == expected + "\n"
    assert captured.out.encode("utf-8").decode("utf-8") == captured.out
    assert dump_options == [
        {"ensure_ascii": False, "allow_nan": False, "separators": (",", ":")}
    ]


@pytest.mark.parametrize(
    ("error_code", "expected_exit"),
    [
        ("invalid_input", 2),
        ("not_found", 3),
        ("ambiguous_run", 3),
        ("invalid_transition", 4),
        ("state_conflict", 4),
        ("malformed_state", 4),
        ("unsupported_schema", 4),
        ("capability_unavailable", 4),
        ("repository_error", 5),
        ("missing_prerequisite", 5),
        ("publication_failed", 6),
        ("internal_error", 70),
    ],
)
def test_protocol_error_uses_shared_exit_class(
    tmp_path, capsys, monkeypatch, error_code, expected_exit
) -> None:
    """PR-PROTO-004: Every documented protocol error has an explicit exit class."""
    app = create_application(make_payload(tmp_path))
    monkeypatch.setattr(
        app,
        "execute",
        lambda *_args, **_kwargs: app.error_result(
            "help.show", error_code, "Bounded protocol error."
        ),
    )

    exit_code = run_cli(app, ["--format=json", "help-show"])
    response = json.loads(capsys.readouterr().out)

    assert response["error"]["code"] == error_code
    assert exit_code == expected_exit


def test_machine_startup_failure_is_one_stdout_envelope(capsys, monkeypatch) -> None:
    """PR-PROTO-001: Startup failures retain the requested machine protocol."""

    def fail_startup(*_args, **_kwargs):
        raise PlanError("Payload manifest is unavailable.")

    monkeypatch.setattr(composition, "create_application", fail_startup)

    exit_code = composition.main(["--format=json", "version-show"])
    captured = capsys.readouterr()
    response = json.loads(captured.out)

    assert exit_code == 4
    assert captured.err == ""
    assert captured.out.count("\n") == 1
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == "malformed_state"


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
