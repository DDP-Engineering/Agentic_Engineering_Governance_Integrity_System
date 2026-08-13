#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Verify WAEGIS CLI protocol containment and presenter parity."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from io import StringIO

import pytest
from test_lifecycle import make_payload

from waegis import composition
from waegis.composition import create_application
from waegis.domain.plans import PlanError, canonical_plan
from waegis.interface.cli import _wizard_show_plan, run_cli


def test_wizard_plan_review_proves_every_paginated_action_was_displayed(
    tmp_path,
) -> None:
    """Paged review shows exact ranges and confirms a gap-free complete list."""
    app = create_application(make_payload(tmp_path / "source"))
    plan = tmp_path / "review.json"
    actions = [
        {
            "kind": "delete",
            "path": f"payload/file-{index:02}.txt",
            "ownership": "payload",
        }
        for index in range(1, 53)
    ]
    plan.write_bytes(
        canonical_plan(
            {
                "schema": "waegis.lifecycle.plan",
                "schema_version": 1,
                "operation": "remove.plan",
                "target": str(tmp_path / "target"),
                "target_fingerprint": "sha256:" + ("0" * 64),
                "source_payload_version": "test",
                "actions": actions,
                "prerequisites": [],
                "warnings": [],
            }
        )
    )
    output = StringIO()

    exit_code = _wizard_show_plan(
        app,
        plan,
        StringIO("y\ny\ny\n"),
        output,
    )

    rendered = output.getvalue()
    assert exit_code == 0
    assert "Actions 1-25 of 52:" in rendered
    assert "Actions 26-50 of 52:" in rendered
    assert "Actions 51-52 of 52:" in rendered
    assert "Review complete: displayed all 52 actions (1-52)." in rendered
    displayed = [int(value) for value in re.findall(r"^  (\d+)\. ", rendered, re.M)]
    assert displayed == list(range(1, 53))


def test_no_argument_wizard_guides_installation_and_verification(tmp_path) -> None:
    """A first-time user can plan, review, authorize, and verify an install."""
    app = create_application(make_payload(tmp_path / "source"))
    target = tmp_path / "project"
    (target / "tests").mkdir(parents=True)
    (target / "tests/test_feature.py").write_text(
        "def test_feature():\n    assert True\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    answers = StringIO(f"{target}\n\n\nn\ny\n")
    output = StringIO()

    exit_code = run_cli(app, [], stdin=answers, stdout=output)

    rendered = output.getvalue()
    assert exit_code == 0
    assert "Welcome to WAEGIS" in rendered
    assert "Python 3.12" in rendered
    assert "Git repository: yes" in rendered
    assert "AEGIS installed: no" in rendered
    assert "Selected pytest test framework" in rendered
    assert "Apply this exact plan? [y/N]" in rendered
    assert "AEGIS installed successfully." in rendered
    assert ".agentic\\aegis\\bin\\aegis.cmd payload-verify" in rendered
    assert (target / ".agentic/aegis/manifest.toml").is_file()
    assert (tmp_path / "project-aegis-install.json").is_file()


def test_no_argument_wizard_cancellation_preserves_target(tmp_path) -> None:
    """Declining apply retains only the external plan and changes no target."""
    app = create_application(make_payload(tmp_path / "source"))
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    answers = StringIO(f"{target}\n\n\nn\n\n")
    output = StringIO()

    exit_code = run_cli(app, [], stdin=answers, stdout=output)

    assert exit_code == 0
    assert "Installation canceled. The target repository was not changed." in (
        output.getvalue()
    )
    assert not (target / ".agentic").exists()
    assert (tmp_path / "project-aegis-install.json").is_file()


def test_no_argument_wizard_selects_upgrade_for_an_installed_target(tmp_path) -> None:
    """An installed target is upgraded instead of being sent through install."""
    app = create_application(make_payload(tmp_path / "source"))
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    install_plan = tmp_path / "initial-install.json"
    planned = app.execute(
        "install-plan", {"target": str(target), "output": str(install_plan)}
    )
    assert planned.operation_status == "completed"
    applied = app.execute(
        "install-apply",
        {
            "target": str(target),
            "plan": str(install_plan),
            "confirm_digest": planned.data["plan_digest"],
        },
    )
    assert applied.operation_status == "completed"
    answers = StringIO(f"{target}\n\n\nn\ny\n")
    output = StringIO()

    exit_code = run_cli(app, [], stdin=answers, stdout=output)

    rendered = output.getvalue()
    assert exit_code == 0
    assert "AEGIS installed: yes" in rendered
    assert "create the aegis upgrade plan" in rendered.casefold()
    assert "AEGIS upgraded successfully." in rendered
    assert (tmp_path / "project-aegis-upgrade.json").is_file()


def test_no_argument_wizard_can_authorize_local_git_initialization(tmp_path) -> None:
    """A non-repository target uses its own reviewed Git-init plan first."""
    app = create_application(make_payload(tmp_path / "source"))
    target = tmp_path / "project"
    target.mkdir()
    answers = StringIO(f"{target}\n\ny\n\nn\ny\nn\n")
    output = StringIO()

    exit_code = run_cli(app, [], stdin=answers, stdout=output)

    rendered = output.getvalue()
    assert exit_code == 0
    assert "Git repository: no" in rendered
    assert "Initialize this directory as a local Git repository? [y/N]" in rendered
    assert "Local Git repository initialized successfully." in rendered
    assert "Installation canceled. The target repository was not changed." in rendered
    assert (target / ".git").is_dir()
    assert not (target / ".agentic").exists()
    assert (tmp_path / "project-git-init.json").is_file()


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


@pytest.mark.parametrize(
    ("failure", "expected_exit", "expected_code"),
    [
        (PlanError("Payload manifest is unavailable."), 4, "malformed_state"),
        (RuntimeError("composition failed"), 70, "internal_error"),
    ],
)
def test_machine_startup_failure_is_one_stdout_envelope(
    capsys, monkeypatch, failure, expected_exit, expected_code
) -> None:
    """PR-PROTO-001: Startup failures retain the requested machine protocol."""

    def fail_startup(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(composition, "create_application", fail_startup)

    exit_code = composition.main(["--format=json", "version-show"])
    captured = capsys.readouterr()
    response = json.loads(captured.out)

    assert exit_code == expected_exit
    assert captured.err == ""
    assert captured.out.count("\n") == 1
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == expected_code


@pytest.mark.parametrize(
    ("failure", "expected_exit", "expected_code"),
    [
        (PlanError("Payload manifest is unavailable."), 4, "malformed_state"),
        (RuntimeError("composition failed"), 70, "internal_error"),
    ],
)
def test_human_startup_failure_uses_standard_result_envelope(
    capsys, monkeypatch, failure, expected_exit, expected_code
) -> None:
    """PR-PROTO-001: Every startup failure uses the shared result presenter."""

    def fail_startup(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(composition, "create_application", fail_startup)

    exit_code = composition.main(["version-show"])
    captured = capsys.readouterr()

    assert exit_code == expected_exit
    assert captured.err == ""
    assert "Operation: version.show" in captured.out
    assert "Status: error" in captured.out
    assert f"Error: {expected_code}:" in captured.out
    assert "Traceback" not in captured.out


def test_human_and_json_present_the_same_help_semantics(tmp_path, capsys) -> None:
    """Human help is readable while JSON preserves the complete registry."""
    app = create_application(make_payload(tmp_path))
    human_exit = run_cli(app, ["help-show"])
    human = capsys.readouterr()
    json_exit = run_cli(app, ["--format", "json", "help-show"])
    machine_output = capsys.readouterr()
    machine = json.loads(machine_output.out)

    assert human_exit == json_exit == 0
    assert "Usage:" in human.out
    assert "Run waegis without a command to start the guided setup." in human.out
    assert "Commands:" in human.out
    assert "Lifecycle workflow:" in human.out
    assert "--format json" not in human.out
    assert machine["product_version"] in human.out
    assert "operations: [" not in human.out
    for operation in machine["data"]["operations"]:
        assert f"  {operation['command']}" in human.out
        assert operation["purpose"] in human.out
    assert "plan-show --plan <PLAN> [--offset <OFFSET>] [--limit <LIMIT>]" in human.out
    assert (
        "install-apply --target <TARGET> --plan <PLAN> "
        "--confirm-digest <CONFIRM-DIGEST>"
    ) in human.out


def test_plan_show_cli_is_body_free_and_does_not_require_git(
    tmp_path, capsys
) -> None:
    """PR-WAEGIS-002/006: Plan review is a read-only flat protocol operation."""
    app = create_application(make_payload(tmp_path / "source"))
    target = tmp_path / "target"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    planned = app.execute(
        "install.plan", {"target": str(target), "output": str(plan)}
    ).to_envelope(1)

    exit_code = run_cli(
        app,
        [
            "--format=json",
            "plan-show",
            "--plan",
            str(plan),
            "--offset",
            "0",
            "--limit",
            "1",
        ],
        git_available=False,
    )
    captured = capsys.readouterr()
    response = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert response["operation"] == "plan.show"
    assert response["data"]["plan_digest"] == planned["data"]["plan_digest"]
    assert response["data"]["returned_count"] == 1
    assert "content_base64" not in captured.out

    human_exit = run_cli(
        app,
        ["plan-show", "--plan", str(plan), "--offset", "0", "--limit", "1"],
        git_available=False,
    )
    human = capsys.readouterr()

    assert human_exit == 0
    assert human.err == ""
    assert "Operation: plan.show" in human.out
    assert 'actions: [{"index":' in human.out
    assert "'kind':" not in human.out
    assert "content_base64" not in human.out


def test_git_prerequisite_only_gates_repository_init_apply(
    tmp_path, capsys, monkeypatch
) -> None:
    """PR-WAEGIS-006/007: Only the authorized Git initializer needs Git."""
    app = create_application(make_payload(tmp_path))
    dispatched = []

    def observe(command, _values):
        dispatched.append(command)
        operation = command.replace("-", ".")
        return app.error_result(operation, "not_found", "Operation reached dispatch.")

    monkeypatch.setattr(app, "execute", observe)
    filesystem_operations = (
        ["help-show"],
        ["version-show"],
        ["plan-show", "--plan", "plan.json"],
        ["repository-init-plan", "--target", "target", "--output", "plan.json"],
        ["install-plan", "--target", "target", "--output", "plan.json"],
        [
            "install-apply",
            "--target",
            "target",
            "--plan",
            "plan.json",
            "--confirm-digest",
            "sha256:" + ("a" * 64),
        ],
        ["upgrade-plan", "--target", "target", "--output", "plan.json"],
        [
            "upgrade-apply",
            "--target",
            "target",
            "--plan",
            "plan.json",
            "--confirm-digest",
            "sha256:" + ("a" * 64),
        ],
        ["remove-plan", "--target", "target", "--output", "plan.json"],
        [
            "remove-apply",
            "--target",
            "target",
            "--plan",
            "plan.json",
            "--confirm-digest",
            "sha256:" + ("a" * 64),
        ],
    )
    for arguments in filesystem_operations:
        exit_code = run_cli(
            app, ["--format=json", *arguments], git_available=False
        )
        response = json.loads(capsys.readouterr().out)
        assert exit_code == 3
        assert response["error"]["summary"] == "Operation reached dispatch."

    before = list(dispatched)
    exit_code = run_cli(
        app,
        [
            "--format=json",
            "repository-init-apply",
            "--target",
            "target",
            "--plan",
            "plan.json",
            "--confirm-digest",
            "sha256:" + ("a" * 64),
        ],
        git_available=False,
    )
    response = json.loads(capsys.readouterr().out)

    assert exit_code == 5
    assert response["error"]["code"] == "missing_prerequisite"
    assert dispatched == before


def test_module_help_routes_through_registry_without_an_error(tmp_path, capsys) -> None:
    """IP-16: The mandated module help command succeeds through help.show."""
    app = create_application(make_payload(tmp_path))

    exit_code = run_cli(app, ["--help"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Usage:" in output
    assert "install-plan --target <TARGET> --output <OUTPUT>" in output


def test_python_module_forwards_process_arguments() -> None:
    """IP-16: python -m waegis forwards its real process arguments."""
    completed = subprocess.run(
        [sys.executable, "-m", "waegis", "--help"],
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0
    assert b"Usage:" in completed.stdout
    assert b"install-plan --target <TARGET> --output <OUTPUT>" in completed.stdout


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
