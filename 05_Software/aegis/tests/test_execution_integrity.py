#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_execution_integrity.py
@brief   Verify configured execution, red witnesses, and Git integrity findings.
@details Covers IP-10/IP-11, PR-DEFAULT-003/004, PR-POSTURE-002,
         PR-CONFIG-006/008-013, PR-RED, PR-INT, PR-ZONE, AC-EXEC-001,
         AC-RED-001, AC-INT-001, and AC-ZONE-001.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aegis.domain.execution import CancellationToken, ExecutionRequest, ExecutionResult
from aegis.infrastructure import process as process_adapter
from aegis.infrastructure.codecs import parse_markdown_document
from aegis.infrastructure.process import execute_process
from aegis.infrastructure.workspace import FileWorkspace

from tests.test_project_knowledge_trace import requirement_data
from tests.test_run_stage_workflow import create_run, installed_repository, invoke


def configure_commands(repo: Path) -> None:
    """@brief Install deterministic synthetic validation commands."""
    python = sys.executable.replace("\\", "\\\\")
    config = repo / ".agentic" / "config.toml"
    config.write_text(
        f'''schema = 1
artifact_type = "project_config"
[paths]
requirements = ".agentic/requirements"
components = ".agentic/components"
tests = [".agentic/tests"]
adoptions = ".agentic/adoptions"
runs = ".agentic/runs"
[validation.tests.pass]
command = ["{python}", "-c", "print('passed')"]
working_directory = "."
timeout_seconds = 0
[validation.tests.fail]
command = ["{python}", "-c", "import sys; print('failed'); sys.exit(7)"]
working_directory = "."
timeout_seconds = 0
[validation.tests.slow]
command = ["{python}", "-c", "import time; time.sleep(5)"]
working_directory = "."
timeout_seconds = 1
[validation.tests.large]
command = ["{python}", "-c", "print('x' * 20000)"]
working_directory = "."
timeout_seconds = 0
[validation.tests.cache]
command = [
    "{python}",
    "-c",
    """from pathlib import Path
p = Path(".pytest_cache/v/cache")
p.mkdir(parents=True, exist_ok=True)
(p / "nodeids").write_text("[]", encoding="utf-8")
""",
]
working_directory = "."
timeout_seconds = 0
[validation.tests.red]
command = ["{python}", ".agentic/tests/test_red.py"]
working_directory = "."
timeout_seconds = 0
[validation.tests.missing]
command = ["definitely-missing-aegis-command"]
working_directory = "."
timeout_seconds = 0
[validation.tests.select]
command = [
    "{python}",
    "-c",
    "import sys; print('|'.join(sys.argv[1:]))",
    "pytest-marker",
]
working_directory = "."
timeout_seconds = 0
[validation.tests.discover]
command = [
    "{python}",
    "-m",
    "unittest",
    "discover",
    "-s",
    ".agentic/tests",
    "-p",
    "test_discover.py",
]
working_directory = "."
timeout_seconds = 0
[validation.tests.integrity]
command = [
    "{python}",
    "-B",
    "-m",
    "unittest",
    "discover",
    "-s",
    ".agentic/tests",
    "-p",
    "test_*.py",
]
working_directory = "."
timeout_seconds = 0
[validation.tests.pytest_empty]
command = ["{python}", "-m", "pytest", "-q", ".agentic/tests"]
working_directory = "."
timeout_seconds = 0
[validation.tests.arbitrary_exit5]
command = ["some-tool", "-m", "pytest"]
working_directory = "."
timeout_seconds = 0
[validation.lints.pass]
command = ["{python}", "-c", "print('lint passed')"]
working_directory = "."
timeout_seconds = 0
[validation.lints.exit5]
command = ["{python}", "-c", "import sys; sys.exit(5)"]
working_directory = "."
timeout_seconds = 0
[validation.audits.pass]
command = ["{python}", "-c", "print('audit passed')"]
working_directory = "."
timeout_seconds = 0
[policy]
risk_attention_threshold = "medium"
protected_scope_patterns = []
''',
        encoding="utf-8",
        newline="\n",
    )


def advance_to(repo: Path, target: str) -> None:
    """@brief Advance truthfully through completed empty synthetic Stages."""
    order = [
        "intake",
        "alignment",
        "requirement",
        "design",
        "check",
        "implementation",
        "validation",
        "delivery",
    ]
    while True:
        current = invoke(repo, "stage-show")[1]["stage"]
        if current == target:
            return
        assert invoke(repo, "stage-complete")[0] == 0
        following_index = order.index(current) + 1
        while following_index < len(order):
            following = order[following_index]
            status = invoke(repo, "stage-show", None, "--stage", following)[1]["data"][
                "status"
            ]
            if status != "omitted":
                break
            following_index += 1
        assert invoke(repo, "stage-start", None, following)[0] == 0


def test_process_runner_distinguishes_pass_fail_timeout_cancel_and_launch(
    tmp_path: Path,
) -> None:
    """@brief Platform adapter returns exactly the five execution outcomes."""
    passed = execute_process(
        ExecutionRequest((sys.executable, "-c", "print('ok')"), tmp_path, 0)
    )
    failed = execute_process(
        ExecutionRequest((sys.executable, "-c", "import sys; sys.exit(3)"), tmp_path, 0)
    )
    timed = execute_process(
        ExecutionRequest(
            (sys.executable, "-c", "import time; time.sleep(5)"), tmp_path, 1
        )
    )
    token = CancellationToken()
    token.cancel()
    cancelled = execute_process(
        ExecutionRequest(
            (sys.executable, "-c", "import time; time.sleep(5)"), tmp_path, 0
        ),
        cancellation=token,
    )
    missing = execute_process(
        ExecutionRequest(("definitely-missing-aegis-command",), tmp_path, 0)
    )

    assert [item.outcome for item in (passed, failed, timed, cancelled, missing)] == [
        "passed",
        "failed",
        "timed_out",
        "cancelled",
        "launch_error",
    ]
    assert failed.exit_status == 3
    assert timed.engineering_conclusion == "unknown"


def test_keyboard_interrupt_cancels_process_group_without_escaping(
    tmp_path: Path, monkeypatch
) -> None:
    """@brief A console interrupt becomes the durable cancelled outcome seam."""

    def interrupt(_: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(process_adapter, "_sleep", interrupt)
    result = execute_process(
        ExecutionRequest(
            (sys.executable, "-c", "import time; time.sleep(5)"), tmp_path, 0
        )
    )

    assert result.outcome == "cancelled"
    assert result.engineering_conclusion == "unknown"


def test_execution_outside_the_expected_stage_records_a_finding(
    tmp_path: Path,
) -> None:
    """@brief PR-DEFAULT-003 records commands outside expected windows."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    created = create_run(repo)
    intake_path = repo / ".agentic" / "runs" / created["run_id"] / "01-intake.md"
    intake_before_missing = intake_path.read_bytes()

    missing_exit, missing = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "absent"
    )

    assert missing_exit != 0
    assert missing["error"]["code"] == "not_found"
    assert intake_path.read_bytes() == intake_before_missing

    intake_exit, intake = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "pass"
    )

    assert intake_exit == 0, intake
    assert intake["outcome"] == "passed"
    assert [finding["code"] for finding in intake["findings"]] == [
        "execution_outside_expected_stage"
    ]
    _, intake_state, _ = parse_markdown_document(
        intake_path.read_bytes(), path=str(intake_path)
    )
    intake_evidence = intake_state["evidence"][-1]
    assert intake_evidence["provenance"] == "executed"
    assert intake_evidence["outcome"] == "passed"
    assert {
        "red_witness",
        "fingerprints",
        "red_fingerprint_comparison",
    }.isdisjoint(intake_evidence)
    intake_findings = [
        finding
        for finding in intake_state["findings"]
        if finding["code"] == "execution_outside_expected_stage"
    ]
    assert len(intake_findings) == 1
    assert intake_findings[0]["disposition"] == "open"
    assert "tests.pass" in intake_findings[0]["observation"]
    assert "Intake" in intake_findings[0]["observation"]
    assert "Check, Implementation, or Validation" in intake_findings[0]["observation"]

    advance_to(repo, "implementation")
    lint_exit, lint = invoke(
        repo, "execution-run", None, "--category", "lints", "--name", "pass"
    )

    assert lint_exit == 0, lint
    assert lint["outcome"] == "passed"
    implementation_path = (
        repo / ".agentic" / "runs" / created["run_id"] / "06-implementation.md"
    )
    _, implementation_state, _ = parse_markdown_document(
        implementation_path.read_bytes(), path=str(implementation_path)
    )
    lint_evidence = implementation_state["evidence"][-1]
    assert lint_evidence["outcome"] == "passed"
    assert {
        "red_witness",
        "fingerprints",
        "red_fingerprint_comparison",
    }.isdisjoint(lint_evidence)
    lint_findings = [
        finding
        for finding in implementation_state["findings"]
        if finding["code"] == "execution_outside_expected_stage"
    ]
    assert len(lint_findings) == 1
    assert "lints.pass" in lint_findings[0]["observation"]
    assert "Implementation" in lint_findings[0]["observation"]
    assert "Validation" in lint_findings[0]["observation"]


def test_advertised_commands_are_runnable_in_the_advertising_stage(
    tmp_path: Path,
) -> None:
    """@brief Delivery runs every advertised validation category as evidence."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    created = create_run(repo)
    advance_to(repo, "validation")

    for category in ("lints", "audits"):
        exit_code, executed = invoke(
            repo,
            "execution-run",
            None,
            "--category",
            category,
            "--name",
            "pass",
        )
        assert exit_code == 0, executed
        assert executed["outcome"] == "passed"
        assert "execution_outside_expected_stage" not in {
            finding["code"] for finding in executed["findings"]
        }
    validation_path = (
        repo / ".agentic" / "runs" / created["run_id"] / "07-validation.md"
    )
    _, validation_state, _ = parse_markdown_document(
        validation_path.read_bytes(), path=str(validation_path)
    )
    assert {
        (item["category"], item["name"], item["outcome"])
        for item in validation_state["evidence"][-2:]
    } == {("lints", "pass", "passed"), ("audits", "pass", "passed")}

    advance_to(repo, "delivery")

    shown_exit, shown = invoke(repo, "stage-show")
    advertised = shown["data"]["tool_context"]["commands"]
    advertised_categories = {item["category"] for item in advertised}

    assert shown_exit == 0, shown
    assert advertised_categories == {"tests", "lints", "audits"}
    for category in sorted(advertised_categories):
        assert any(
            item["category"] == category and item["name"] == "pass"
            for item in advertised
        )
        exit_code, executed = invoke(
            repo,
            "execution-run",
            None,
            "--category",
            category,
            "--name",
            "pass",
        )
        assert exit_code == 0, executed
        assert executed["outcome"] == "passed"
        assert executed.get("error") is None
        assert [finding["code"] for finding in executed["findings"]] == [
            "execution_outside_expected_stage"
        ]

    delivery_path = repo / ".agentic" / "runs" / created["run_id"] / "08-delivery.md"
    _, delivery_state, _ = parse_markdown_document(
        delivery_path.read_bytes(), path=str(delivery_path)
    )
    evidence = delivery_state["evidence"][-3:]
    assert {(item["category"], item["name"]) for item in evidence} == {
        ("tests", "pass"),
        ("lints", "pass"),
        ("audits", "pass"),
    }
    assert all(item["outcome"] == "passed" for item in evidence)
    assert all(
        {"red_witness", "fingerprints", "red_fingerprint_comparison"}.isdisjoint(
            item
        )
        for item in evidence
    )
    outside_window = [
        finding
        for finding in delivery_state["findings"]
        if finding["code"] == "execution_outside_expected_stage"
    ]
    assert len(outside_window) == 3
    assert all("Delivery" in finding["observation"] for finding in outside_window)


def test_test_execution_consumes_recorded_impacted_selection(tmp_path: Path) -> None:
    """@brief A test command receives the exact recorded path and selector."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    (repo / "src").mkdir()
    (repo / "src/retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic/tests/test_retry.py").write_text(
        "def test_retry_history(): pass\n", encoding="utf-8"
    )
    create_run(repo)
    created = invoke(repo, "requirement-create", requirement_data())[1]
    assert created["operation_status"] == "completed"
    selected = invoke(
        repo,
        "trace-impacted",
        {"changed_files": ["src/retry.py"], "changed_tests": []},
    )[1]
    label = selected["data"]["label"]
    advance_to(repo, "check")

    executed = invoke(
        repo,
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "select",
        "--selection",
        label,
    )[1]
    assert executed["outcome"] == "passed"
    evidence = invoke(repo, "execution-list")[1]["data"]["executions"][-1]
    assert evidence["selection_mode"] == "impacted"
    assert ".agentic/tests/test_retry.py::test_retry_history" in evidence["stdout_tail"]


def test_selection_against_discover_does_not_record_failure(tmp_path: Path) -> None:
    """@brief PR-TRACE-004 keeps unittest discovery passing via explained fallback."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    (repo / "src").mkdir()
    (repo / "src/retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic/tests/test_discover.py").write_text(
        "import unittest\n\n"
        "class PassingTest(unittest.TestCase):\n"
        "    def test_suite_passes(self):\n"
        "        self.assertTrue(True)\n",
        encoding="utf-8",
    )
    create_run(repo)
    created = invoke(
        repo,
        "requirement-create",
        requirement_data(".agentic/tests/test_discover.py"),
    )[1]
    assert created["operation_status"] == "completed"
    selected = invoke(
        repo,
        "trace-impacted",
        {"changed_files": ["src/retry.py"], "changed_tests": []},
    )[1]
    label = selected["data"]["label"]
    assert selected["data"]["mode"] == "impacted"
    advance_to(repo, "check")

    exit_code, executed = invoke(
        repo,
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "discover",
        "--selection",
        label,
    )

    assert exit_code == 0, executed
    assert executed["outcome"] == "passed"
    evidence = invoke(repo, "execution-list")[1]["data"]["executions"][-1]
    assert evidence["command"] == [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        ".agentic/tests",
        "-p",
        "test_discover.py",
    ]
    assert evidence["selection"] == label
    assert evidence["selection_mode"] == "full"
    assert evidence["selection_fallback_reasons"] == [
        "Impacted selection cannot be safely applied to the configured "
        "unittest discover command; the unchanged full suite was executed."
    ]
    assert "Ran 1 test" in evidence["stderr_tail"]


def test_execution_run_records_all_operational_outcomes_and_large_attachment(
    tmp_path: Path,
) -> None:
    """@brief Unfavorable project results are successful AEGIS protocol records."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    create_run(repo)
    advance_to(repo, "check")

    for name, outcome in (
        ("pass", "passed"),
        ("fail", "failed"),
        ("slow", "timed_out"),
        ("missing", "launch_error"),
    ):
        exit_code, response = invoke(
            repo, "execution-run", None, "--category", "tests", "--name", name
        )
        assert exit_code == 0, response
        assert response["outcome"] == outcome
    exit_code, large = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "large"
    )
    assert exit_code == 0
    assert large["artifacts"] and large["artifacts"][0]["type"] == "attachment"
    listed = invoke(repo, "execution-list")[1]
    assert len(listed["data"]["executions"]) == 5


def test_reported_evidence_cannot_become_a_red_witness(tmp_path: Path) -> None:
    """@brief PR-RED-002 rejects caller integrity fields as red execution proof."""
    repo = installed_repository(tmp_path)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    created = create_run(repo)
    advance_to(repo, "check")

    added = invoke(
        repo,
        "evidence-add",
        {
            "kind": "automated",
            "category": "tests",
            "command": ["python", ".agentic/tests/test_red.py"],
            "working_directory": ".",
            "outcome": "failed",
            "exit_status": 1,
            "observed_result": "The reported test failed.",
            "tests": [".agentic/tests/test_red.py"],
            "red_witness": True,
            "fingerprints": {
                ".agentic/tests/test_red.py": "sha256:" + ("0" * 64)
            },
            "red_fingerprint_comparison": {"changed_tests": []},
        },
    )

    assert added[0] == 0, added[1]
    check_path = repo / ".agentic" / "runs" / created["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    reported = check_state["evidence"][-1]
    assert {
        "red_witness",
        "fingerprints",
        "red_fingerprint_comparison",
    }.isdisjoint(reported)

    completed = invoke(repo, "stage-complete")[1]

    assert "check_red_witness_incomplete" in {
        finding["code"] for finding in completed["findings"]
    }


def test_empty_test_root_does_not_produce_a_red_witness(tmp_path: Path) -> None:
    """@brief PR-DEFAULT-001/PR-RED-002 reject empty discovery as red proof."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    advance_to(repo, "check")

    executed = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "project"
    )

    assert executed[0] == 0, executed[1]
    assert executed[1]["outcome"] == "launch_error"
    assert executed[1]["data"]["exit_status"] == 5
    assert executed[1]["data"]["engineering_conclusion"] == "unknown"
    check_path = repo / ".agentic" / "runs" / created["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    evidence = check_state["evidence"][-1]
    assert evidence["no_tests_ran"] is True
    assert evidence["reason"] == (
        "The test runner completed without collecting or executing tests; "
        "the test conclusion remains unknown."
    )
    assert {"red_witness", "fingerprints"}.isdisjoint(evidence)


def test_pytest_exit_five_does_not_produce_a_red_witness(tmp_path: Path) -> None:
    """@brief PR-CONFIG-010/011 keep pytest no-collection evidence unknown."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    created = create_run(repo)
    advance_to(repo, "check")

    executed = invoke(
        repo,
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "pytest_empty",
    )

    assert executed[0] == 0, executed[1]
    assert executed[1]["outcome"] == "launch_error"
    assert executed[1]["data"]["exit_status"] == 5
    check_path = repo / ".agentic" / "runs" / created["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    evidence = check_state["evidence"][-1]
    assert evidence["no_tests_ran"] is True
    assert {"red_witness", "fingerprints"}.isdisjoint(evidence)


def test_non_test_exit_five_remains_a_genuine_failure(tmp_path: Path) -> None:
    """@brief PR-CONFIG-010 does not reinterpret unrelated exit status 5."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    create_run(repo)
    advance_to(repo, "validation")

    executed = invoke(
        repo, "execution-run", None, "--category", "lints", "--name", "exit5"
    )

    assert executed[0] == 0, executed[1]
    assert executed[1]["outcome"] == "failed"
    assert executed[1]["data"]["exit_status"] == 5
    assert executed[1]["data"]["engineering_conclusion"] == "failed"
    evidence = invoke(repo, "execution-list")[1]["data"]["executions"][-1]
    assert "no_tests_ran" not in evidence
    assert {"red_witness", "fingerprints"}.isdisjoint(evidence)


def test_arbitrary_test_command_with_pytest_arguments_keeps_exit_five_failed(
    tmp_path: Path, monkeypatch
) -> None:
    """@brief PR-CONFIG-010 does not infer Python from arbitrary arguments."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    created = create_run(repo)
    advance_to(repo, "check")

    def execute_arbitrary_exit_five(request, *, cancellation=None):
        assert request.command == ("some-tool", "-m", "pytest")
        assert cancellation is None
        return ExecutionResult(
            "failed",
            5,
            b"",
            b"arbitrary tool failed",
            0.01,
            "The command completed with a failing exit status.",
        )

    monkeypatch.setattr(
        "aegis.infrastructure.workspace.execute_process", execute_arbitrary_exit_five
    )

    executed = invoke(
        repo,
        "execution-run",
        None,
        "--category",
        "tests",
        "--name",
        "arbitrary_exit5",
    )

    assert executed[0] == 0, executed[1]
    assert executed[1]["outcome"] == "failed"
    assert executed[1]["data"]["exit_status"] == 5
    assert executed[1]["data"]["engineering_conclusion"] == "failed"
    check_path = repo / ".agentic" / "runs" / created["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    evidence = check_state["evidence"][-1]
    assert "no_tests_ran" not in evidence
    assert evidence["red_witness"] is True
    assert evidence["fingerprints"] == {}


def test_executed_failure_is_a_red_witness(tmp_path: Path) -> None:
    """@brief PR-RED-002/PR-INT-001 retain genuine execution fingerprints."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    created = create_run(repo)
    advance_to(repo, "check")

    executed = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "red"
    )

    assert executed[0] == 0, executed[1]
    assert executed[1]["outcome"] == "failed"
    check_path = repo / ".agentic" / "runs" / created["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    witness = check_state["evidence"][-1]
    assert witness["red_witness"] is True
    assert witness["fingerprints"]

    completed = invoke(repo, "stage-complete")[1]

    assert not {
        finding["code"] for finding in completed["findings"]
    } & {
        "check_red_witness_missing",
        "check_red_witness_incomplete",
        "check_red_witness_not_prior",
    }


def test_red_fingerprint_is_immutable_and_changed_test_is_reported(
    tmp_path: Path,
) -> None:
    """@brief Green comparison names a changed test and preserves Check red bytes."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    create_run(repo)
    advance_to(repo, "check")

    red = invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")[1]
    assert red["outcome"] == "failed"
    check_path = repo / ".agentic" / "runs" / red["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    immutable_red = check_state["evidence"][-1]
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    red_test.write_text("raise SystemExit(0)\n", encoding="utf-8")
    added_test = repo / ".agentic" / "tests" / "test_added_after_red.py"
    added_test.write_text("raise SystemExit(0)\n", encoding="utf-8")
    green = invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")[
        1
    ]

    assert green["outcome"] == "passed"
    assert [finding["code"] for finding in green["findings"]] == [
        "test_changed_after_red",
        "test_changed_after_red",
    ]
    implementation_path = (
        repo / ".agentic" / "runs" / red["run_id"] / "06-implementation.md"
    )
    _, implementation_state, _ = parse_markdown_document(
        implementation_path.read_bytes(), path=str(implementation_path)
    )
    assert implementation_state["evidence"][-1]["provenance"] == "executed"
    summaries = [finding["summary"] for finding in green["findings"]]
    assert any(".agentic/tests/test_red.py" in summary for summary in summaries)
    assert any(
        ".agentic/tests/test_added_after_red.py" in summary for summary in summaries
    )
    _, completed_check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    assert completed_check_state["evidence"][-1] == immutable_red


def test_comparison_uses_every_recorded_red_witness(tmp_path: Path) -> None:
    """@brief PR-INT-002/004 compare green against every durable red witness."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    original_test = repo / ".agentic" / "tests" / "test_calc.py"
    original_test.write_text(
        "import unittest\n\n"
        "class CalcTest(unittest.TestCase):\n"
        "    def test_calculation(self):\n"
        "        self.assertEqual(1, 2)\n",
        encoding="utf-8",
    )
    created = create_run(repo)
    advance_to(repo, "check")

    first_red = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "integrity"
    )
    assert first_red[0] == 0, first_red[1]
    assert first_red[1]["outcome"] == "failed"
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    original_test.write_text(
        "import unittest\n\n"
        "class CalcTest(unittest.TestCase):\n"
        "    def test_calculation(self):\n"
        "        self.assertEqual(1, 1)\n",
        encoding="utf-8",
    )
    throwaway_test = repo / ".agentic" / "tests" / "test_tmp.py"
    throwaway_test.write_text(
        "import unittest\n\n"
        "class TemporaryTest(unittest.TestCase):\n"
        "    def test_temporary_failure(self):\n"
        "        self.fail('temporary red witness')\n",
        encoding="utf-8",
    )
    revisited = invoke(
        repo,
        "stage-revisit",
        {"actor": "agent", "reason": "Record corrected Check evidence."},
        "check",
    )
    assert revisited[0] == 0, revisited[1]
    second_red = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "integrity"
    )
    assert second_red[0] == 0, second_red[1]
    assert second_red[1]["outcome"] == "failed"
    check_path = repo / ".agentic" / "runs" / created["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    recorded_witnesses = [
        item for item in check_state["evidence"] if item.get("red_witness") is True
    ]
    assert len(recorded_witnesses) == 2
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    throwaway_test.unlink()

    green = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "integrity"
    )

    assert green[0] == 0, green[1]
    assert green[1]["outcome"] == "passed"
    implementation_path = (
        repo / ".agentic" / "runs" / created["run_id"] / "06-implementation.md"
    )
    _, implementation_state, _ = parse_markdown_document(
        implementation_path.read_bytes(), path=str(implementation_path)
    )
    comparison = implementation_state["evidence"][-1][
        "red_fingerprint_comparison"
    ]
    assert comparison["changed_tests"] == [
        ".agentic/tests/test_calc.py",
        ".agentic/tests/test_tmp.py",
    ]
    assert [finding["code"] for finding in green[1]["findings"]] == [
        "test_changed_after_red",
        "test_changed_after_red",
    ]
    _, final_check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    assert [
        item
        for item in final_check_state["evidence"]
        if item.get("red_witness") is True
    ] == recorded_witnesses


def test_reported_green_records_absent_fingerprint_comparison(
    tmp_path: Path,
) -> None:
    """@brief PR-INT-002 keeps reported green distinct from compared execution."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    created = create_run(repo, profile="short")
    advance_to(repo, "check")
    red = invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")
    assert red[0] == 0, red[1]
    assert red[1]["outcome"] == "failed"
    check_path = repo / ".agentic" / "runs" / created["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    assert check_state["evidence"][-1]["provenance"] == "executed"
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    red_test.write_text("raise SystemExit(0)\n", encoding="utf-8")
    failed_execution = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "fail"
    )
    assert failed_execution[0] == 0, failed_execution[1]
    assert failed_execution[1]["outcome"] == "failed"
    implementation_path = (
        repo / ".agentic" / "runs" / created["run_id"] / "06-implementation.md"
    )
    _, implementation_state, _ = parse_markdown_document(
        implementation_path.read_bytes(), path=str(implementation_path)
    )
    failed_evidence = implementation_state["evidence"][-1]
    assert failed_evidence["provenance"] == "executed"
    assert "red_fingerprint_comparison" in failed_evidence

    reported = invoke(
        repo,
        "evidence-add",
        {
            "kind": "automated",
            "category": "tests",
            "command": ["python", ".agentic/tests/test_red.py"],
            "working_directory": ".",
            "outcome": "passed",
            "exit_status": 0,
            "observed_result": "The externally run test passed.",
            "tests": [".agentic/tests/test_red.py"],
            "provenance": "executed",
        },
    )

    assert reported[0] == 0, reported[1]
    assert reported[1]["data"]["entry"]["provenance"] == "reported"
    _, implementation_state, _ = parse_markdown_document(
        implementation_path.read_bytes(), path=str(implementation_path)
    )
    assert implementation_state["evidence"][-1]["provenance"] == "reported"
    implementation = invoke(repo, "stage-complete")
    assert implementation[0] == 0, implementation[1]
    assert "implementation_green_evidence_missing" not in {
        finding["code"] for finding in implementation[1]["findings"]
    }
    assert invoke(repo, "stage-start", None, "validation")[0] == 0
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "delivery")[0] == 0
    assert (
        invoke(
            repo,
            "stage-set-section",
            {"section": "terminal_result", "content": "achieved", "actor": "agent"},
        )[0]
        == 0
    )
    assert (
        invoke(
            repo,
            "decision-add",
            {
                "value": "approved",
                "actor": "agent",
                "target": "delivery",
                "reason": "The recorded result is truthful.",
            },
        )[0]
        == 0
    )
    delivery = invoke(repo, "stage-complete")
    assert delivery[0] == 0, delivery[1]
    delivery_path = repo / ".agentic" / "runs" / created["run_id"] / "08-delivery.md"
    _, delivery_state, _ = parse_markdown_document(
        delivery_path.read_bytes(), path=str(delivery_path)
    )

    assert (
        '- fingerprint_comparison: "not_performed"'
        in delivery_state["sections"]["recorded_state"]
    )


def test_fingerprints_exclude_ignored_cache_files(tmp_path: Path) -> None:
    """@brief PR-INT-001 fingerprints Git-visible tests, not ignored caches."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    cache = repo / ".agentic" / "tests" / "__pycache__"
    cache.mkdir()
    (cache / "test_red.cpython-312.pyc").write_bytes(b"ignored cache")
    create_run(repo)
    advance_to(repo, "check")

    red = invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")

    assert red[0] == 0, red[1]
    check_path = repo / ".agentic" / "runs" / red[1]["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    assert set(check_state["evidence"][-1]["fingerprints"]) == {
        ".agentic/tests/test_red.py"
    }


def test_tracked_test_stays_fingerprinted_when_gitignored(tmp_path: Path) -> None:
    """@brief PR-INT-001/003 keep tracked tests in red/green comparison."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    red_test = repo / ".agentic" / "tests" / "test_red.py"
    red_test.write_text("raise SystemExit(1)\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", ".agentic/tests/test_red.py"], check=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "track test",
        ],
        check=True,
    )
    (repo / ".gitignore").write_text(
        ".agentic/tests/test_red.py\n", encoding="utf-8"
    )
    create_run(repo)
    advance_to(repo, "check")

    red = invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")

    assert red[0] == 0, red[1]
    check_path = repo / ".agentic" / "runs" / red[1]["run_id"] / "05-check.md"
    _, check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    assert ".agentic/tests/test_red.py" in check_state["evidence"][-1][
        "fingerprints"
    ]
    assert invoke(repo, "stage-complete")[0] == 0
    assert invoke(repo, "stage-start", None, "implementation")[0] == 0
    red_test.write_text("raise SystemExit(0)\n", encoding="utf-8")

    green = invoke(repo, "execution-run", None, "--category", "tests", "--name", "red")

    assert green[0] == 0, green[1]
    assert any(
        finding["code"] == "test_changed_after_red"
        and ".agentic/tests/test_red.py" in finding["summary"]
        for finding in green[1]["findings"]
    )


def test_git_visible_files_fall_back_when_git_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    """@brief PR-INT-001 keeps filesystem fingerprints when Git is unavailable."""
    repo = installed_repository(tmp_path)
    test_path = repo / ".agentic" / "tests" / "test_fallback.py"
    test_path.write_text("def test_fallback(): pass\n", encoding="utf-8")
    runtime_path = repo / ".agentic" / ".runtime" / "generated.bin"
    runtime_path.parent.mkdir()
    runtime_path.write_bytes(b"generated")
    workspace = FileWorkspace(repo)

    def git_unavailable(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", git_unavailable)

    assert workspace.git_visible_files(".agentic/tests") == (
        ".agentic/tests/test_fallback.py",
    )
    root_files = workspace.git_visible_files(".")
    assert ".agentic/tests/test_fallback.py" in root_files
    assert not any(path.startswith(".git/") for path in root_files)
    assert not any(path.startswith(".agentic/.runtime/") for path in root_files)


def test_git_visible_files_skip_tracked_deleted_paths(tmp_path: Path) -> None:
    """@brief PR-INT-001 omits index entries without existing regular files."""
    repo = installed_repository(tmp_path)
    deleted = repo / ".agentic" / "tests" / "test_deleted.py"
    deleted.write_text("def test_deleted(): pass\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", ".agentic/tests/test_deleted.py"], check=True
    )
    deleted.unlink()

    assert FileWorkspace(repo).git_visible_files(".agentic/tests") == ()


def test_check_git_comparison_reports_implementation_change_without_mutation(
    tmp_path: Path,
) -> None:
    """@brief Read-only Check comparison reports an out-of-zone source edit."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    (repo / "src").mkdir()
    source = repo / "src" / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "src/app.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    create_run(repo)
    advance_to(repo, "check")
    source.write_text("VALUE = 2\n", encoding="utf-8")

    completed = invoke(repo, "stage-complete")[1]

    assert "src/app.py" in [
        finding["artifact"]
        for finding in completed["findings"]
        if finding["code"] == "check_out_of_zone_change"
    ]
    assert source.read_text(encoding="utf-8") == "VALUE = 2\n"


def test_check_reports_staged_only_transition_without_repeating_existing_dirt(
    tmp_path: Path,
) -> None:
    """@brief Check names Git-state deltas when working bytes stay unchanged.

    @details Covers PR-ZONE-003/004/005/007.
    """
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    (repo / "src").mkdir()
    staged_only = repo / "src" / "staged_only.py"
    unchanged_dirty = repo / "src" / "unchanged_dirty.py"
    staged_only.write_text("VALUE = 1\n", encoding="utf-8")
    unchanged_dirty.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "src"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    create_run(repo)
    staged_only.write_text("VALUE = 2\n", encoding="utf-8")
    unchanged_dirty.write_text("VALUE = 2\n", encoding="utf-8")
    advance_to(repo, "check")
    subprocess.run(
        ["git", "-C", str(repo), "add", "src/staged_only.py"], check=True
    )

    exit_code, completed = invoke(repo, "stage-complete")

    assert exit_code == 0, completed
    out_of_zone = {
        finding["artifact"]
        for finding in completed["findings"]
        if finding["code"] == "check_out_of_zone_change"
    }
    assert out_of_zone == {"src/staged_only.py"}
    assert any(
        finding["code"] == "check_git_state_changed"
        for finding in completed["findings"]
    )
    assert staged_only.read_text(encoding="utf-8") == "VALUE = 2\n"
    assert unchanged_dirty.read_text(encoding="utf-8") == "VALUE = 2\n"


def test_zone_comparison_ignores_gitignored_paths(tmp_path: Path) -> None:
    """@brief PR-ZONE-002 compares known files, not ignored test artifacts."""
    repo = installed_repository(tmp_path)
    configure_commands(repo)
    (repo / ".gitignore").write_text(".pytest_cache/\n", encoding="utf-8")
    (repo / "src").mkdir()
    source = repo / "src" / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    create_run(repo)
    advance_to(repo, "check")

    executed = invoke(
        repo, "execution-run", None, "--category", "tests", "--name", "cache"
    )
    assert executed[0] == 0, executed[1]
    assert executed[1]["outcome"] == "passed"
    ignored = repo / ".pytest_cache" / "v" / "cache" / "nodeids"
    assert ignored.read_text(encoding="utf-8") == "[]"
    source.write_text("VALUE = 2\n", encoding="utf-8")

    completed = invoke(repo, "stage-complete")[1]
    out_of_zone = {
        finding["artifact"]
        for finding in completed["findings"]
        if finding["code"] == "check_out_of_zone_change"
    }

    assert out_of_zone == {"src/app.py"}


def test_git_snapshot_classifies_staged_unstaged_untracked_rename_and_delete(
    tmp_path: Path,
) -> None:
    """@brief Read-only Git observation names every required mutation form."""
    repo = installed_repository(tmp_path)
    for name in ("rename-me.py", "delete-me.py", "modify-me.py"):
        (repo / name).write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "mv", "rename-me.py", "renamed.py"], check=True
    )
    (repo / "delete-me.py").unlink()
    (repo / "modify-me.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "staged.py").write_text("STAGED = True\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "staged.py"], check=True)
    (repo / "untracked.py").write_text("UNTRACKED = True\n", encoding="utf-8")

    snapshot = FileWorkspace(repo).git_snapshot()
    classified = snapshot["classifications"]

    assert "staged.py" in [item["path"] for item in classified["staged"]]
    assert "modify-me.py" in [item["path"] for item in classified["unstaged"]]
    assert "untracked.py" in classified["untracked"]
    assert {"from": "rename-me.py", "to": "renamed.py", "area": "staged"} in (
        classified["renamed"]
    )
    assert {"path": "delete-me.py", "area": "unstaged"} in classified["deleted"]
    assert snapshot["index_revision"].startswith("sha256:")
