#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_execution_integrity.py
@brief   Verify configured execution, red witnesses, and Git integrity findings.
@details Covers IP-10/IP-11, PR-CONFIG-006/008-013, PR-RED, PR-INT,
         PR-ZONE, AC-EXEC-001, AC-RED-001, AC-INT-001, and AC-ZONE-001.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aegis.domain.execution import CancellationToken, ExecutionRequest
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
    summaries = [finding["summary"] for finding in green["findings"]]
    assert any(".agentic/tests/test_red.py" in summary for summary in summaries)
    assert any(
        ".agentic/tests/test_added_after_red.py" in summary for summary in summaries
    )
    _, completed_check_state, _ = parse_markdown_document(
        check_path.read_bytes(), path=str(check_path)
    )
    assert completed_check_state["evidence"][-1] == immutable_red


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
    workspace = FileWorkspace(repo)

    def git_unavailable(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", git_unavailable)

    assert workspace.git_visible_files(".agentic/tests") == (
        ".agentic/tests/test_fallback.py",
    )


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
