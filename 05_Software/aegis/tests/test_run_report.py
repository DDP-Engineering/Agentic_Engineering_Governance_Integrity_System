#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_run_report.py
@brief P4 tests: `check --strict`/`--run`, `aegis test [--impacted]`, `report`.
@details Configured commands are built on `sys.executable` so they run
         identically on Windows and Linux under `shell=True`. Diff-based
         impacted-set tests reuse the real-git fixture from test_check and
         skip cleanly when git is absent.
"""

# IMPORTS

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_check import (
    git,
    lines_for,
    make_git_repo,
    make_repo,
    needs_git,
    run_check,
    write,
    write_req,
    write_task,
)
from test_cli_core import snapshot

# CONSTANTS

PY = f'"{sys.executable}"'


# HELPERS


def config(agentic: Path, commands: str, check: str = "",
           source: str = '["src/"]', tests: str = '["tests/"]',
           extra: str = "") -> None:
    """@brief Write an aegis.toml with the given [commands] and [check] bodies."""
    write(
        agentic / "aegis.toml",
        f"schema = 1\n\n[commands]\n{commands}\n\n"
        f"[layout]\nsource = {source}\ntests = {tests}\n\n[check]\n{check}\n"
        + (f"\n{extra}\n" if extra else ""),
    )


def cmd_exit(code: int) -> str:
    """@brief A cross-platform command exiting with `code`, as a TOML value."""
    return f"'{PY} -c \"import sys; sys.exit({code})\"'"


def run(aegis, capsys, *argv: str) -> tuple[int, str]:
    """@brief Run one CLI invocation; return (exit code, stdout)."""
    capsys.readouterr()
    code = aegis.main(list(argv))
    return code, capsys.readouterr().out


# TESTS - check --strict exit codes


def test_strict_ok_on_a_clean_repo(tmp_path, monkeypatch, capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    code, out = run(aegis, capsys, "check", "--strict")
    assert code == 0
    assert "strict: ok" in out


def test_strict_fails_on_an_error(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    write(agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml",
          "not [ toml\n")
    code, out = run(aegis, capsys, "check", "--strict")
    assert code == 1
    assert "strict: exit 1 (1 error(s), 0 promoted warning(s))" in out


def test_strict_ignores_unpromoted_warnings_and_notes(tmp_path, monkeypatch,
                                                      capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)  # NOTEs appear
    write_req(agentic, "REQ-FUNC-1111")  # active, empty linked_tests -> WARN
    code, out = run(aegis, capsys, "check", "--strict")
    assert code == 0
    assert "result: WARN" in out and "strict: ok" in out


def test_strict_promote_turns_a_warning_into_a_failure(tmp_path, monkeypatch,
                                                       capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic, 'test = "unused"',
           'strict_promote = ["no-linked-tests"]')
    write_req(agentic, "REQ-FUNC-1111")
    code, out = run(aegis, capsys, "check", "--strict")
    assert code == 1
    assert "strict: exit 1 (0 error(s), 1 promoted warning(s))" in out

    code, _out = run(aegis, capsys, "check")  # without --strict: advisory
    assert code == 0


# TESTS - check --run


def test_run_reports_ok_and_fail_and_feeds_strict(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic, f"good = {cmd_exit(0)}\nbad = {cmd_exit(3)}")

    code, out = run(aegis, capsys, "check", "--run")
    assert code == 0  # advisory without --strict, even with a failing command
    assert any(line.startswith("run: good ok (") for line in out.splitlines())
    assert any(line.startswith("run: bad FAIL exit 3 (") for line in out.splitlines())
    assert "ERROR  command-failed  (run) - bad exit 3" in out
    assert "summary: errors=1" in out

    code, out = run(aegis, capsys, "check", "--run", "--strict")
    assert code == 1
    assert "strict: exit 1 (1 error(s), 0 promoted warning(s))" in out


def test_run_prints_the_captured_tail_of_a_failure(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic,
           f"bad = '{PY} -c \"print(chr(66) + chr(79) + chr(79) + chr(77));"
           " import sys; sys.exit(2)\"'")
    _code, out = run(aegis, capsys, "check", "--run")
    assert "  | BOOM" in out


def test_run_skips_templates_and_timeout_key(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic,
           "test_impacted = \"pytest {tests}\"\ntimeout = 60")
    _code, out = run(aegis, capsys, "check", "--run")
    assert "run: nothing ran" in out  # neither the template nor timeout ran


def test_run_stops_a_command_at_its_configured_limit(tmp_path, monkeypatch,
                                                      capsys):
    """A configured limit still stops a command - it just says so honestly."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic,
           f"slow = '{PY} -c \"import time; time.sleep(30)\"'\ntimeout = 1")
    _code, out = run(aegis, capsys, "check", "--run")
    assert any(line.startswith("run: slow stopped at its 1s limit (")
               for line in out.splitlines())


# TESTS - aegis test


def test_test_runs_the_configured_command_and_mirrors_its_exit(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, f"test = {cmd_exit(0)}\nflaky = {cmd_exit(5)}")

    code, out = run(aegis, capsys, "test")
    assert code == 0
    assert any(line.startswith("test: exit 0 (") for line in out.splitlines())

    code, out = run(aegis, capsys, "test", "flaky")
    assert code == 5
    assert any(line.startswith("flaky: exit 5 (") for line in out.splitlines())


def test_test_prints_the_command_before_piped_child_output(tmp_path):
    """The command announcement is flushed before the child process starts."""
    agentic, _aegis = make_repo(tmp_path)
    config(agentic, f'test = \'{PY} -c "print(12345)"\'')

    result = subprocess.run(
        [sys.executable, str(agentic / "aegis.py"), "test"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = result.stdout.splitlines()
    assert result.returncode == 0
    assert lines[0].startswith("$ ")
    assert lines[1] == "12345"


def test_test_rejects_unknown_or_template_names(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, "test_impacted = \"pytest {tests}\"")
    assert run(aegis, capsys, "test", "nope")[0] == 1
    assert run(aegis, capsys, "test", "test_impacted")[0] == 1
    assert run(aegis, capsys, "test", "lint", "--impacted")[0] == 1


def test_test_task_appends_a_dated_log_line(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, f"test = {cmd_exit(0)}")
    write_task(agentic, "TASK-ab12")
    code, _out = run(aegis, capsys, "test", "--task", "TASK-ab12")
    assert code == 0
    text = (agentic / "tasks" / "TASK-ab12.md").read_text(encoding="utf-8")
    last = [line for line in text.splitlines() if line.strip()][-1]
    assert last.startswith("- ") and " test: test exit 0 (" in last


# TESTS - aegis test --impacted


def test_impacted_falls_back_without_a_template(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, f"test = {cmd_exit(0)}")
    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "impacted: no test_impacted template" in out


@needs_git
def test_impacted_substitutes_the_focused_set(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "argdump.py",
          "import pathlib, sys\n"
          "pathlib.Path('args.txt').write_text(' '.join(sys.argv[1:]))\n")
    config(agentic,
           f"test = {cmd_exit(0)}\n"
           f"test_impacted = '{PY} argdump.py {{tests}}'")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["tests/test_app.py::test_app", "tests/test_more.py"]')
    write_req(agentic, "REQ-FUNC-2222", paths='["src/unrelated.py"]',
              tests='["tests/test_unrelated.py"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")

    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "test --impacted (2 test ref(s)): exit 0" in out
    assert (tmp_path / "args.txt").read_text() == \
        "tests/test_app.py::test_app tests/test_more.py"


@needs_git
def test_impacted_ignores_generated_python_bytecode(tmp_path, capsys):
    """A pytest-created source cache cannot force a permanent full-suite loop."""
    agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "argdump.py",
          "import pathlib, sys\n"
          "pathlib.Path('args.txt').write_text(' '.join(sys.argv[1:]))\n")
    config(agentic,
           f"test = {cmd_exit(0)}\n"
           f"test_impacted = '{PY} argdump.py {{tests}}'")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["tests/test_app.py::test_app"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    write(tmp_path / "src" / "__pycache__" / "app.cpython-312.pyc",
          "generated bytecode\n")

    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "test --impacted (1 test ref(s)): exit 0" in out
    assert "changed source not fully covered" not in out
    assert (tmp_path / "args.txt").read_text() == "tests/test_app.py::test_app"


@needs_git
def test_impacted_falls_back_when_nothing_is_covered(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic,
           f"test = {cmd_exit(0)}\ntest_impacted = \"never run {{tests}}\"")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/unrelated.py"]',
              tests='["tests/test_unrelated.py"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "impacted: changed source not fully covered (src/app.py)" in out


@needs_git
def test_impacted_rejects_unsafe_test_references(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic,
           f"test = {cmd_exit(0)}\ntest_impacted = \"never run {{tests}}\"")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["tests/x.py; rm -rf tmp"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "impacted: unsafe test reference" in out


def test_log_lines_land_in_the_log_section_even_after_a_report(tmp_path,
                                                               monkeypatch,
                                                               capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    config(agentic, f"test = {cmd_exit(0)}")
    write_task(agentic, "TASK-ab12")
    aegis.main(["report", "TASK-ab12"])
    code, _out = run(aegis, capsys, "test", "--task", "TASK-ab12")
    assert code == 0
    data = aegis.parse_journal(
        (agentic / "tasks" / "TASK-ab12.md").read_text(encoding="utf-8"))
    assert any("test: test exit 0" in line for line in data["log"])


def test_status_hides_done_tasks_unless_all(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write_task(agentic, "TASK-aaaa", stage="build")
    write_task(agentic, "TASK-bbbb", stage="done")
    _code, out = run(aegis, capsys, "status")
    assert "TASK-aaaa" in out and "TASK-bbbb" not in out
    assert "(1 done hidden - use --all)" in out
    _code, out = run(aegis, capsys, "status", "--all")
    assert "TASK-bbbb" in out


def test_pointer_update_preserves_crlf_and_following_bytes(tmp_path):
    _agentic, aegis = make_repo(tmp_path)
    mine = "# Mine\r\n\r\nMy own CRLF notes.\r\n"
    (tmp_path / "CLAUDE.md").write_bytes(mine.encode())
    aegis.main(["init"])
    first = (tmp_path / "CLAUDE.md").read_bytes()
    assert mine.encode() in first          # user bytes untouched, CRLF intact
    assert b"AEGIS:BEGIN" in first

    # corrupt the digest, re-init: refresh must not eat trailing user bytes
    text = first.replace(b"advisory", b"advis0ry")
    tail = b"KEEP-THIS-TRAILING-LINE\r\n"
    (tmp_path / "CLAUDE.md").write_bytes(text + tail)
    aegis.main(["init"])
    refreshed = (tmp_path / "CLAUDE.md").read_bytes()
    assert tail in refreshed
    assert b"advis0ry" not in refreshed
    assert mine.encode() in refreshed


# TESTS - compact recorded stage summaries


def stage_record(path: Path, **overrides: str) -> None:
    """@brief Append a complete reporting record to an existing fixture journal."""
    fields = {"stage": "specify", "result": "completed", "current": "design",
              "changed": "REQ-FUNC-1111 created", "evidence": "check exit 0; tests not run",
              "issues": "none recorded", "next": "follow 3_design.md", "needs_user": "no",
              "spec_compliance": "", "implementation_quality": "", "review_round": ""}
    fields.update(overrides)
    write(path, path.read_text(encoding="utf-8") + "\n## Stage report\n\n"
          + "\n".join(f"{key}: {value}" for key, value in fields.items()) + "\n")


def summary_fields(out: str) -> dict[str, str]:
    """@brief Decode the human-readable summary without depending on padding."""
    return {key: value.strip() for key, value in
            (line.split(":", 1) for line in out.splitlines())}


def test_stage_report_accepts_independent_review_fields(tmp_path):
    """REQ-FUNC-9514e017: the two verdicts and round parse independently."""
    _, aegis = make_repo(tmp_path)
    text = """## Stage report

stage: validate
result: completed
current: deliver
spec_compliance: approved
implementation_quality: changes_required
review_round: 3
"""
    record = aegis.parse_stage_report(text)
    assert record["spec_compliance"] == "approved"
    assert record["implementation_quality"] == "changes_required"
    assert record["review_round"] == "3"


@pytest.mark.parametrize("field", [
    "spec_compliance: maybe", "implementation_quality: passed",
    "review_round: 0", "review_round: 7", "review_round: two",
])
def test_stage_report_rejects_invalid_verdicts_and_review_rounds(tmp_path, field):
    """REQ-FUNC-9514e017: malformed enabled-review evidence is never approval."""
    _, aegis = make_repo(tmp_path)
    with pytest.raises(aegis.UserError):
        aegis.parse_stage_report("## Stage report\n\n" + field + "\n")


def test_bound_stage_report_rejects_stale_current_binding(tmp_path):
    """REQ-FUNC-1844e18d: one helper owns current-stage freshness."""
    _, aegis = make_repo(tmp_path)
    text = """## Stage report

stage: specify
result: completed
current: design
evidence: check exit 0
"""
    record, notice = aegis.bound_stage_report(text, "build")
    assert record == {}
    assert notice == "stale stage report: current stage changed; refresh from journal"


def test_summary_reads_recorded_facts_without_side_effects(tmp_path, monkeypatch, capsys):
    """REQ-FUNC-1844e18d: summary reads the journal only and preserves status JSON."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="design", reqs="REQ-FUNC-1111")
    stage_record(path)
    before = snapshot(tmp_path)
    _code, status_before = run(aegis, capsys, "status", "ab12", "--json")

    def unexpected(*_args, **_kwargs):
        pytest.fail("summary must not run commands or inspect repository/config state")

    monkeypatch.setattr(aegis, "run_git", unexpected)
    monkeypatch.setattr(aegis, "load_config", unexpected)
    monkeypatch.setattr(aegis.subprocess, "run", unexpected)
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    fields = summary_fields(out)
    assert list(fields) == ["Stage", "Task", "Current", "Requirements", "Changed",
                            "Evidence", "Issues", "Next", "Needs user",
                            "Specification compliance", "Implementation quality",
                            "Review round", "Details"]
    assert fields["Stage"] == "specify - completed"
    assert fields["Current"] == "design"
    assert fields["Task"] == "TASK-ab12"
    assert fields["Requirements"] == "REQ-FUNC-1111"
    assert fields["Changed"] == "REQ-FUNC-1111 created"
    assert fields["Evidence"] == "check exit 0; tests not run"
    assert fields["Needs user"] == "no"
    assert ".agentic/tasks/TASK-ab12.md" in fields["Details"]
    assert snapshot(tmp_path) == before
    _code, status_after = run(aegis, capsys, "status", "ab12", "--json")
    assert status_after == status_before


def test_summary_displays_independent_verdicts_and_review_round(tmp_path, capsys):
    """REQ-FUNC-9514e017: summary projects each recorded review fact separately."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="deliver")
    stage_record(path, stage="validate", current="deliver", result="completed",
                 spec_compliance="approved", implementation_quality="changes_required",
                 review_round="2")
    code, out = run(aegis, capsys, "summary", path.stem)
    assert code == 0
    fields = summary_fields(out)
    assert fields["Specification compliance"] == "approved"
    assert fields["Implementation quality"] == "changes_required"
    assert fields["Review round"] == "2"


def test_summary_legacy_record_displays_not_recorded(tmp_path, capsys):
    """REQ-FUNC-9514e017: omitted review fields never imply approval."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="build")
    write(path, path.read_text(encoding="utf-8") + """

## Stage report

stage: build
result: in_progress
current: build
""")
    code, out = run(aegis, capsys, "summary", path.stem)
    fields = summary_fields(out)
    assert code == 0
    assert fields["Specification compliance"] == "not recorded"
    assert fields["Implementation quality"] == "not recorded"
    assert fields["Review round"] == "not recorded"


@pytest.mark.parametrize("reported,current,result", [
    ("frame", "build", "completed"), ("components", "components", "paused"),
    ("validate", "build", "blocked"), ("design", "build", "skipped"),
    ("close", "done", "completed"), ("build", "build", "in_progress"),
])
def test_summary_handles_transitions_and_pauses(tmp_path, capsys, reported, current, result):
    """REQ-FUNC-1844e18d: recorded outcomes do not relabel the current stage."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage=current)
    stage_record(path, stage=reported, current=current, result=result,
                 needs_user="confirm scope" if reported == "frame" else "no")
    code, out = run(aegis, capsys, "summary", "TASK-ab12")
    assert code == 0
    fields = summary_fields(out)
    assert fields["Stage"] == f"{reported} - {result}"
    assert fields["Current"] == current


@pytest.mark.parametrize("record", ["", "\n## Stage report\n\nstage:\ncurrent:\n"])
def test_summary_missing_record_does_not_infer_success(tmp_path, capsys, record):
    """REQ-FUNC-1844e18d: a ticked checklist and green log are not a stage report."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="deliver", checklist="- [x] green")
    write(path, path.read_text(encoding="utf-8") + "- 2026-08-28 validate: all passed\n"
          + record)
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    fields = summary_fields(out)
    assert fields["Stage"] == "not recorded"
    assert fields["Evidence"] == "not recorded"
    assert fields["Current"] == "deliver"
    assert fields["Needs user"] != "no"
    assert "completed" not in out and "all passed" not in out


def test_summary_partial_record_keeps_missing_values_explicit(tmp_path, capsys):
    """REQ-FUNC-1844e18d: missing evidence or decisions must not become success."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="build")
    write(path, path.read_text(encoding="utf-8")
          + "\n## Stage report\n\nstage: build\ncurrent: build\n")
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    fields = summary_fields(out)
    assert fields["Stage"] == "build - not recorded"
    for key in ("Changed", "Evidence", "Issues", "Next", "Needs user"):
        assert fields[key] == "not recorded"


@pytest.mark.parametrize("binding", ["specify", ""])
def test_summary_suppresses_stale_or_unbound_claims(tmp_path, capsys, binding):
    """REQ-FUNC-1844e18d: a mismatched record cannot authorize continuation."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="build")
    stage_record(path, current=binding, evidence="all passed", next="publish now")
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    fields = summary_fields(out)
    assert fields["Current"] == "build"
    assert fields["Evidence"] == "not recorded"
    assert fields["Next"] != "publish now"
    assert fields["Needs user"] != "no"
    assert "stale" in out if binding else "incomplete" in out


@pytest.mark.parametrize("extra", [
    "stage: build\nstage: design\n", "stage: requirement\n",
    "result: passed\n", "surprise: value\n", "not a field\n",
    "current: unknown\n", "stage: build\n\n## Stage report\nstage: design\n",
])
def test_summary_rejects_ambiguous_or_invalid_records(tmp_path, capsys, extra):
    """REQ-FUNC-1844e18d: malformed records fail without printing a partial report."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12")
    write(path, path.read_text(encoding="utf-8") + "\n## Stage report\n" + extra)
    capsys.readouterr()
    assert aegis.main(["summary", "ab12"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "error:" in captured.err


def test_summary_bounds_output_and_requires_review_of_omissions(tmp_path, capsys):
    """REQ-FUNC-1844e18d: long records cannot silently hide unresolved issues."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="design", reqs="REQ-FUNC-1111 " * 100)
    write(path, path.read_text(encoding="utf-8") + "- old log entry\n" * 10000)
    stage_record(path, changed="x" * 2000, issues="warning " * 1000 + "BLOCKER")
    before = path.read_bytes()
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    fields = summary_fields(out)
    assert len(fields) == 13 and all(len(value) <= 240 for value in fields.values())
    assert "[truncated; read journal]" in fields["Issues"]
    assert "review" in fields["Needs user"] and "truncated" in fields["Needs user"]
    assert "old log entry" not in out
    assert path.read_bytes() == before


def test_summary_does_not_emit_terminal_control_characters(tmp_path, capsys):
    """REQ-FUNC-1844e18d: recorded text cannot forge additional output lines."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="design")
    stage_record(path, changed="hello\tworld\x1b[2J")
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    assert "\x1b" not in out and "\t" not in out and len(out.splitlines()) == 13


def test_summary_rejects_unknown_task(tmp_path, capsys):
    """REQ-FUNC-1844e18d: missing task errors remain concise and read-only."""
    _agentic, aegis = make_repo(tmp_path)
    capsys.readouterr()
    assert aegis.main(["summary", "dead"]) == 1
    captured = capsys.readouterr()
    assert not captured.out and "no such task" in captured.err


@pytest.mark.parametrize("field", ["stage: " + "x" * 10000, "x" * 10000 + ": value"],
                         ids=["long-value", "long-key"])
def test_summary_errors_do_not_echo_unbounded_record_content(tmp_path, capsys, field):
    """REQ-FUNC-1844e18d: malformed-record diagnostics also stay compact."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12")
    write(path, path.read_text(encoding="utf-8") + "\n## Stage report\n" + field + "\n")
    capsys.readouterr()
    assert aegis.main(["summary", "ab12"]) == 1
    captured = capsys.readouterr()
    assert not captured.out and len(captured.err) < 300


def test_summary_scaffold_and_test_log_remain_independent(tmp_path, monkeypatch, capsys):
    """REQ-FUNC-1844e18d: fresh sessions never confuse log results with report state."""
    agentic, aegis = make_repo(tmp_path)
    monkeypatch.setattr(aegis, "git_branch", lambda: "feature")
    monkeypatch.setattr(aegis, "git_head", lambda: "")
    code, out = run(aegis, capsys, "task", "fresh session")
    assert code == 0
    path = tmp_path / out.strip()
    assert "## Stage report" in path.read_text(encoding="utf-8")
    code, out = run(aegis, capsys, "summary", path.stem)
    assert code == 0 and summary_fields(out)["Stage"] == "not recorded"
    config(agentic, f"test = {cmd_exit(0)}")
    assert aegis.main(["test", "--task", path.stem]) == 0
    code, out = run(aegis, capsys, "summary", path.stem)
    assert code == 0 and summary_fields(out)["Evidence"] == "not recorded"
    data = aegis.parse_journal(path.read_text(encoding="utf-8"))
    assert any("test exit 0" in line for line in data["log"])


@pytest.mark.parametrize("prefix,suffix", [
    ("<!--\n", "\n## End example\n-->\n"),
    ("Example: <!--\n", "\n## End example\n-->\n"),
    ("```text\n", "\n```\n"),
    ("~~~text\n", "\n~~~\n"),
    ("````text\n```\n<!--\n", "\n```\n````\n"),
], ids=["comment", "inline-comment", "backticks", "tildes", "long-fence"])
@pytest.mark.parametrize("live_record", [False, True], ids=["example-only", "with-live"])
def test_summary_ignores_commented_and_fenced_examples(
        tmp_path, capsys, prefix, suffix, live_record):
    """REQ-FUNC-1844e18d: quoted examples cannot supply or conflict with live facts."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="build")
    example = ("## Stage report\nstage: deliver\nresult: completed\ncurrent: build\n"
               "evidence: fake passed\nnext: publish now\nneeds_user: no\n")
    write(path, path.read_text(encoding="utf-8") + prefix + example + suffix)
    if live_record:
        stage_record(path, stage="build", current="build", result="in_progress",
                     evidence="actual check not run")
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    fields = summary_fields(out)
    assert "fake passed" not in out and "publish now" not in out
    assert fields["Stage"] == ("build - in_progress" if live_record else "not recorded")
    assert fields["Evidence"] == ("actual check not run" if live_record else "not recorded")


@pytest.mark.parametrize("example", [
    "- Parser accepts the literal `<!--` token.\n",
    "- Parser accepts the literal ``<!--`` token.\n",
    "```text <!--\nexample\n```\n",
])
def test_summary_literal_comment_markers_do_not_hide_live_report(tmp_path, capsys, example):
    """REQ-FUNC-1844e18d: code-span literals and fence info are not comments."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="design")
    write(path, path.read_text(encoding="utf-8") + example)
    stage_record(path)
    code, out = run(aegis, capsys, "summary", "ab12")
    assert code == 0
    assert summary_fields(out)["Stage"] == "specify - completed"


# TESTS - deterministic bounded task brief


def write_brief_fixture(agentic: Path) -> Path:
    """@brief Write one representative current journal plus a visible child."""
    path = write_task(
        agentic, "TASK-ab12", stage="validate", reqs="REQ-FUNC-1111",
        checklist="- [x] build candidate\n- [ ] review candidate",
    )
    write(path, path.read_text(encoding="utf-8") + """

## Rulings

- RULING-001 | date=2026-08-31 | decision=Old | reason=Replaced | source=user | supersedes=none
- RULING-002 | date=2026-08-31 | decision=Use brief | reason=bounded | source=technical | supersedes=RULING-001

## Handoff

current: validate
status: ready
next: review candidate
must_read: .agentic/steps/5_validate.md
blockers:

## Stage report

stage: validate
result: in_progress
current: validate
changed: candidate
evidence: tests passed
issues: none
next: review
needs_user: no
spec_compliance:
implementation_quality:
review_round:
""")
    write_task(agentic, "TASK-bb22", stage="done", parent="TASK-ab12")
    return path


def test_brief_has_fixed_section_order_and_no_side_effects(tmp_path, monkeypatch, capsys):
    """REQ-FUNC-e55c43d1: one exact durable snapshot defines the public format."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    path = write_brief_fixture(agentic)
    before = snapshot(tmp_path)

    def unexpected(*_args, **_kwargs):
        pytest.fail("brief must not run Git, configured commands, or subprocesses")

    monkeypatch.setattr(aegis, "run_git", unexpected)
    monkeypatch.setattr(aegis.subprocess, "run", unexpected)
    code, out = run(aegis, capsys, "brief", "ab12")
    assert code == 0
    assert out == """AEGIS brief
Task: TASK-ab12 - a task
Stage: validate
Branch/base: feature @ not recorded
Parent: none
Requirements: REQ-FUNC-1111
Checklist: 1/2 done; next=review candidate
Stage report: validate - in_progress; changed=candidate; evidence=tests passed; issues=none; next=review; needs_user=no
Review: policy=disabled; max_fix_cycles=2; spec=not recorded; quality=not recorded; round=not recorded
Active rulings:
- RULING-002 | decision=Use brief | reason=bounded | source=technical | supersedes=RULING-001
Handoff: ready; current=validate; next=review candidate; must_read=.agentic/steps/5_validate.md; blockers=not recorded
Visible children:
- TASK-bb22 | stage=done | title=a task
Details: .agentic/tasks/TASK-ab12.md (durable snapshot; read journal for full history)
"""
    assert path.read_bytes() == (agentic / "tasks" / "TASK-ab12.md").read_bytes()
    assert snapshot(tmp_path) == before


def test_brief_reads_only_durable_workspace_files(tmp_path, monkeypatch, capsys):
    """REQ-FUNC-e55c43d1: the resume view has no live-state dependency."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write_brief_fixture(agentic)
    for name in ("git_branch", "git_head", "collect_diff", "run_configured_commands"):
        monkeypatch.setattr(aegis, name, lambda *_a, _name=name, **_k: pytest.fail(_name))
    code, out = run(aegis, capsys, "brief", "TASK-ab12")
    assert code == 0 and out.startswith("AEGIS brief\n")


def test_brief_renders_legacy_journal_without_guessing(tmp_path, capsys):
    """REQ-FUNC-e55c43d1: missing additive records stay explicit."""
    agentic, aegis = make_repo(tmp_path)
    write(agentic / "tasks" / "TASK-ab12.md", """# TASK-ab12 - legacy

stage: build
type: feature
requirements:
branch: feature
base:
opened: 2026-08-31

## Done checklist (current stage)

- [ ] continue

## Log

- legacy
""")
    code, out = run(aegis, capsys, "brief", "ab12")
    assert code == 0
    assert "Parent: none" in out
    assert "Stage report: not recorded" in out
    assert "Active rulings:\n- none recorded" in out
    assert "Handoff: not recorded" in out
    assert "Visible children:\n- none visible" in out
    assert "approved" not in out


def test_brief_lists_active_rulings_and_sorted_visible_children(tmp_path, capsys):
    """REQ-FUNC-e55c43d1: durable collections use contract-defined order."""
    agentic, aegis = make_repo(tmp_path)
    path = write_brief_fixture(agentic)
    write_task(agentic, "TASK-aa11", stage="build", parent="TASK-ab12")
    code, out = run(aegis, capsys, "brief", path.stem)
    assert code == 0 and "- RULING-001 | decision=" not in out and "RULING-002" in out
    assert out.index("TASK-aa11 |") < out.index("TASK-bb22 |")


def test_brief_marks_stale_stage_report_and_handoff(tmp_path, capsys):
    """REQ-FUNC-e55c43d1: stale bindings cannot be resume authority."""
    agentic, aegis = make_repo(tmp_path)
    path = write_brief_fixture(agentic)
    text = path.read_text(encoding="utf-8").replace("current: validate", "current: build")
    write(path, text)
    code, out = run(aegis, capsys, "brief", path.stem)
    assert code == 0
    assert "Stage report: stale stage report" in out
    assert "Handoff: stale handoff: current stage changed" in out
    assert "tests passed" not in out


def test_brief_bounds_scalars_rulings_children_and_control_characters(tmp_path, capsys):
    """REQ-FUNC-e55c43d1: every unshown value is visibly accounted for."""
    agentic, aegis = make_repo(tmp_path)
    path = write_task(agentic, "TASK-ab12", stage="build", reqs="REQ-FUNC-1111 " * 100)
    rulings = "\n".join(
        f"- RULING-{n:03d} | date=2026-08-31 | decision={'x' * 400}\x1b | "
        f"reason=reason | source=technical | supersedes=none"
        for n in range(1, 11)
    )
    write(path, path.read_text(encoding="utf-8") + f"\n## Rulings\n\n{rulings}\n")
    for n in range(25):
        write_task(agentic, f"TASK-{n + 256:04x}", parent="TASK-ab12")
    code, out = run(aegis, capsys, "brief", path.stem)
    assert code == 0
    assert "\x1b" not in out and "...[2 omitted; read journal]" in out
    assert "...[5 omitted; read journal]" in out
    assert "[truncated; read journal]" in out
    assert all(len(line) <= 260 for line in out.splitlines())


def test_brief_output_is_byte_identical_across_two_runs(tmp_path, capsys):
    """REQ-FUNC-e55c43d1: unchanged durable state yields identical UTF-8 text."""
    agentic, aegis = make_repo(tmp_path)
    write_brief_fixture(agentic)
    first = run(aegis, capsys, "brief", "ab12")
    second = run(aegis, capsys, "brief", "ab12")
    assert first == second


def test_brief_rejects_unknown_task_with_one_line_error(tmp_path, capsys):
    """REQ-FUNC-e55c43d1: unknown tasks fail concisely without partial output."""
    _agentic, aegis = make_repo(tmp_path)
    capsys.readouterr()
    assert aegis.main(["brief", "dead"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and len(captured.err.splitlines()) == 1
    assert captured.err.startswith("error: no such task journal")


# TESTS - aegis report


def test_report_appends_the_delivery_section(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    pass\n")
    write_req(agentic, "REQ-FUNC-1111",
              tests='["tests/test_app.py::test_app"]')
    write_task(agentic, "TASK-ab12", stage="deliver", reqs="REQ-FUNC-1111",
               checklist="- [x] suite green\n- [ ] report appended")

    code, out = run(aegis, capsys, "report", "TASK-ab12")
    assert code == 0
    assert "report appended to .agentic/tasks/TASK-ab12.md" in out

    text = (agentic / "tasks" / "TASK-ab12.md").read_text(encoding="utf-8")
    assert "## Delivery report (" in text
    assert "- stage: deliver; type: feature; path: full; branch: feature" in text
    assert "  - REQ-FUNC-1111 - A behavior" in text
    assert "- diff vs merge base: unavailable (git executable not found)" in text
    assert "- checks: errors=0 warnings=1 notes=7" in text
    assert "- checklist: 1/2 done; open: report appended" in text

    aegis.main(["report", "TASK-ab12"])  # append-only: a second dated section
    text = (agentic / "tasks" / "TASK-ab12.md").read_text(encoding="utf-8")
    assert text.count("## Delivery report (") == 2


def test_report_rejects_an_unknown_task(tmp_path, capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    assert run(aegis, capsys, "report", "TASK-dead")[0] == 1


def test_report_labels_review_disabled_without_skipping_validation(tmp_path,
                                                                    monkeypatch,
                                                                    capsys):
    """REQ-FUNC-9514e017: disabled explicit verdicts do not weaken validation."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    path = write_task(agentic, "TASK-ab12", stage="deliver")
    stage_record(path, stage="validate", current="deliver", result="completed",
                 spec_compliance="disabled", implementation_quality="disabled")
    assert run(aegis, capsys, "report", path.stem)[0] == 0
    text = path.read_text(encoding="utf-8")
    assert "- explicit review: disabled; existing validation remains required" in text


def test_report_records_enabled_approved_verdicts_from_bound_record(tmp_path,
                                                                    monkeypatch,
                                                                    capsys):
    """REQ-FUNC-9514e017: report uses both current recorded approvals."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, 'test = "unused"', extra="[review]\nenabled = true\nmax_fix_cycles = 2")
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    path = write_task(agentic, "TASK-ab12", stage="deliver")
    stage_record(path, stage="validate", current="deliver", result="completed",
                 spec_compliance="approved", implementation_quality="approved",
                 review_round="1")
    assert run(aegis, capsys, "report", path.stem)[0] == 0
    assert ("- explicit review: enabled; spec_compliance=approved; "
            "implementation_quality=approved; review_round=1" in
            path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mode", ["missing", "malformed", "stale"])
def test_report_exposes_missing_malformed_or_stale_verdict_evidence(tmp_path,
                                                                    monkeypatch,
                                                                    capsys,
                                                                    mode):
    """REQ-FUNC-9514e017: unsafe review evidence is reported, never promoted."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, 'test = "unused"', extra="[review]\nenabled = true\nmax_fix_cycles = 2")
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    path = write_task(agentic, "TASK-ab12", stage="deliver")
    if mode == "missing":
        stage_record(path, stage="validate", current="deliver", result="completed")
    elif mode == "malformed":
        stage_record(path, stage="validate", current="deliver", result="completed",
                     spec_compliance="maybe")
    else:
        stage_record(path, stage="validate", current="build", result="completed",
                     spec_compliance="approved", implementation_quality="approved",
                     review_round="1")
    assert run(aegis, capsys, "report", path.stem)[0] == 0
    report = path.read_text(encoding="utf-8").rsplit("## Delivery report", 1)[1]
    assert "explicit review: enabled" in report
    assert "approved; implementation_quality=approved" not in report
    assert any(word in report for word in ("not recorded", "malformed", "stale"))


def test_report_never_converts_missing_verdict_to_approval(tmp_path, monkeypatch, capsys):
    """REQ-FUNC-9514e017: incomplete verdict pairs cannot read as approved."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, 'test = "unused"', extra="[review]\nenabled = true\nmax_fix_cycles = 2")
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    path = write_task(agentic, "TASK-ab12", stage="deliver")
    stage_record(path, stage="validate", current="deliver", result="completed",
                 spec_compliance="approved", implementation_quality="", review_round="1")
    assert run(aegis, capsys, "report", path.stem)[0] == 0
    report = path.read_text(encoding="utf-8").rsplit("## Delivery report", 1)[1]
    assert "implementation_quality=not recorded" in report


def test_brief_combines_workspace_review_policy_with_recorded_verdicts(tmp_path, capsys):
    """REQ-FUNC-9514e017: brief distinguishes policy from recorded evidence."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, 'test = "unused"', extra="[review]\nenabled = true\nmax_fix_cycles = 2")
    path = write_brief_fixture(agentic)
    text = path.read_text(encoding="utf-8").replace(
        "spec_compliance:\nimplementation_quality:\nreview_round:",
        "spec_compliance: approved\nimplementation_quality: changes_required\nreview_round: 2")
    write(path, text)
    code, out = run(aegis, capsys, "brief", path.stem)
    assert code == 0
    assert ("Review: policy=enabled; max_fix_cycles=2; spec=approved; "
            "quality=changes_required; round=2" in out)


# TESTS - review-hardening regressions


def test_crafted_task_ids_cannot_escape_the_tasks_folder(tmp_path, capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    (tmp_path / "outside.md").write_text("# TASK-aaaa — victim\n\nstage: build\n")
    for evil in ("TASK-../../outside", "../outside", "TASK-..%2f..%2foutside"):
        code, _out = run(aegis, capsys, "status", evil)
        assert code == 1
        code, _out = run(aegis, capsys, "report", evil)
        assert code == 1
    assert "victim" in (tmp_path / "outside.md").read_text()  # untouched


def test_run_skips_side_effect_names_and_honors_check_run_list(tmp_path,
                                                               monkeypatch,
                                                               capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic, f"test = {cmd_exit(0)}\ndeploy_prod = {cmd_exit(0)}")
    _code, out = run(aegis, capsys, "check", "--run")
    assert any(line.startswith("run: test ok") for line in out.splitlines())
    assert "run: deploy_prod skipped (name suggests side effects" in out

    config(agentic, f"test = {cmd_exit(0)}\nlint = {cmd_exit(0)}",
           'run = ["lint"]')
    _code, out = run(aegis, capsys, "check", "--run")
    assert "run: test skipped (not listed in [check] run)" in out
    assert any(line.startswith("run: lint ok") for line in out.splitlines())


@needs_git
def test_impacted_falls_back_when_a_covered_file_has_no_tests(tmp_path,
                                                              capsys):
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic,
           f"test = {cmd_exit(0)}\ntest_impacted = \"never run {{tests}}\"")
    # app.py is covered by 1111 (no tests); other.py by 2222 (has tests).
    # The per-file rule must fall back even though the union is non-empty.
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]', tests="[]")
    write_req(agentic, "REQ-FUNC-2222", paths='["src/other.py"]',
              tests='["tests/test_app.py"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    write(tmp_path / "src" / "other.py", "y = 1\n")
    _code, out = run(aegis, capsys, "test", "--impacted")
    assert "impacted: no linked tests for changed source (src/app.py)" in out


@needs_git
def test_impacted_rejects_option_like_references(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic,
           f"test = {cmd_exit(0)}\ntest_impacted = \"never run {{tests}}\"")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["--collect-only"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    _code, out = run(aegis, capsys, "test", "--impacted")
    assert "impacted: unsafe test reference" in out


def test_run_with_nothing_to_run_is_visible_not_silent(tmp_path, monkeypatch,
                                                       capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic, "test_impacted = \"pytest {tests}\"")  # nothing runnable
    code, out = run(aegis, capsys, "check", "--run")
    assert code == 0                       # advisory: still exits 0
    assert "run: nothing ran" in out
    assert "ERROR  nothing-ran" in out     # visible; strict fails on it

    config(agentic, f"test = {cmd_exit(0)}\ndeploy = {cmd_exit(0)}",
           'run = ["deploy"]')             # test excluded by the run list
    _code, out = run(aegis, capsys, "check", "--run")
    assert "run: test skipped (not listed in [check] run)" in out
    assert "nothing-ran" not in out        # deploy did run, so not silent


def test_strict_fails_when_run_verified_nothing(tmp_path, monkeypatch, capsys):
    """--run promised verification; delivering none must fail strict on its
    own, without needing a strict_promote entry."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic, "test_impacted = \"pytest {tests}\"")  # nothing runnable

    code, out = run(aegis, capsys, "check", "--run")       # advisory
    assert code == 0 and "ERROR  nothing-ran" in out

    code, out = run(aegis, capsys, "check", "--run", "--strict")
    assert code == 1
    assert "strict: exit 1 (1 error(s), 0 promoted warning(s))" in out

    code, doc, _err = json_out(aegis, capsys, "check", "--run", "--strict",
                               "--json")
    assert code == 1 and doc["strict"]["passed"] is False


def test_run_announces_each_command_before_it_starts(tmp_path, monkeypatch,
                                                     capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic, f"test = {cmd_exit(0)}")
    _code, out = run(aegis, capsys, "check", "--run")
    lines = [line for line in out.splitlines() if line.startswith("run: test")]
    assert lines[0] == "run: test started"       # printed before the wait
    assert lines[1].startswith("run: test ok (")


def test_findings_are_capped_unless_full_or_strict(tmp_path, monkeypatch,
                                                   capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    for index in range(60):  # 60 active requirements, each missing tests
        write_req(agentic, f"REQ-FUNC-{index:08x}")

    _code, out = run(aegis, capsys, "check")
    assert sum(1 for line in out.splitlines() if "no-linked-tests" in line) == 40
    assert "more finding(s) - use --full" in out

    _code, out = run(aegis, capsys, "check", "--full")
    assert sum(1 for line in out.splitlines() if "no-linked-tests" in line) == 60
    _code, out = run(aegis, capsys, "check", "--strict")  # CI implies --full
    assert sum(1 for line in out.splitlines() if "no-linked-tests" in line) == 60


def test_status_caps_the_task_list(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    for index in range(25):
        write_task(agentic, f"TASK-{index:04x}")
    _code, out = run(aegis, capsys, "status")
    assert "25 open task journal(s)" in out
    assert "... 5 more (see .agentic/tasks/)" in out


def test_captured_output_is_bounded_by_a_temp_file(tmp_path, monkeypatch,
                                                   capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    # ~2 MB of output: only the tail may reach the report
    config(agentic,
           f"""noisy = '{PY} -c "print(chr(88) * 2000000); import sys;"""
           """ sys.exit(1)"'""")
    _code, out = run(aegis, capsys, "check", "--run")
    assert "run: noisy FAIL exit 1" in out
    for line in out.splitlines():
        assert len(line) < 5000  # the tail is a slice, never the whole stream


# TESTS - --json output contract


def json_out(aegis, capsys, *argv: str) -> tuple[int, dict, str]:
    """@brief Run a command with --json; parse stdout, return stderr too."""
    capsys.readouterr()
    code = aegis.main(list(argv))
    captured = capsys.readouterr()
    return code, json.loads(captured.out), captured.err


def test_check_json_is_a_parseable_document_with_a_schema(tmp_path,
                                                          monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write_req(agentic, "REQ-FUNC-11111111")  # active, no linked tests -> WARN

    code, doc, _err = json_out(aegis, capsys, "check", "--json")
    assert code == 0
    assert doc["schema"] == aegis.JSON_SCHEMA
    assert doc["command"] == "check"
    assert doc["result"] == "WARN"
    assert doc["summary"] == {"errors": 0, "warnings": 1, "notes": 6}
    assert doc["strict"] is None and doc["run"] == []
    finding = next(f for f in doc["findings"] if f["check"] == "no-linked-tests")
    assert set(finding) == {"level", "check", "path", "message"}
    assert finding["level"] == "WARN"
    assert finding["path"].endswith("REQ-FUNC-11111111.toml")


def test_check_json_is_never_capped(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    for index in range(60):  # more than FINDING_CAP
        write_req(agentic, f"REQ-FUNC-{index:08x}")
    _code, doc, _err = json_out(aegis, capsys, "check", "--json")
    assert sum(1 for f in doc["findings"]
               if f["check"] == "no-linked-tests") == 60


def test_check_json_keeps_stdout_pure_while_running_commands(tmp_path,
                                                             monkeypatch,
                                                             capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic, f"test = {cmd_exit(0)}\nbad = {cmd_exit(3)}")

    code, doc, err = json_out(aegis, capsys, "check", "--json", "--run")
    assert code == 0                       # advisory without --strict
    assert "run: test ok" in err           # progress on stderr...
    assert "run:" not in json.dumps(doc)   # ...never inside the document
    results = {entry["name"]: entry for entry in doc["run"]}
    assert results["test"]["status"] == "ok" and results["test"]["exit"] == 0
    assert results["bad"]["status"] == "failed" and results["bad"]["exit"] == 3
    assert any(f["check"] == "command-failed" for f in doc["findings"])


def test_check_json_reports_strict_and_keeps_the_exit_code(tmp_path,
                                                           monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    write(agentic / "requirements" / "functional" / "REQ-FUNC-11111111.toml",
          "not [ toml\n")
    code, doc, _err = json_out(aegis, capsys, "check", "--json", "--strict")
    assert code == 1                       # same exit code as the text mode
    assert doc["strict"] == {"enabled": True, "promoted_warnings": 0,
                             "passed": False}


def test_status_json_lists_tasks_and_flags_unreadable(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write_task(agentic, "TASK-aaaa", stage="build")
    write_task(agentic, "TASK-bbbb", stage="done")
    (agentic / "tasks" / "TASK-cccc.md").write_bytes(b"# TASK-cccc \xff\xfe\n")

    _code, doc, _err = json_out(aegis, capsys, "status", "--json")
    assert doc["command"] == "status"
    assert [t["id"] for t in doc["tasks"]] == ["TASK-aaaa"]
    assert doc["hidden_done"] == 1
    assert doc["unreadable"] == [".agentic/tasks/TASK-cccc.md"]
    assert doc["tasks"][0]["stage"] == "build"

    _code, doc, _err = json_out(aegis, capsys, "status", "--json", "--all")
    assert {t["id"] for t in doc["tasks"]} == {"TASK-aaaa", "TASK-bbbb"}


def test_status_human_list_names_a_headingless_journal(tmp_path, capsys):
    """A malformed journal remains identifiable by its filename."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write(agentic / "tasks" / "TASK-broken.md", "stage: build\ntype: fix\n")

    _code, out = run(aegis, capsys, "status")
    assert "TASK-broken" in out
    assert "(missing heading)" in out


def test_status_json_for_one_task_carries_the_whole_state(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write(agentic / "tasks" / "TASK-ad01.md",
          "# TASK-ad01 — Adopt repo\n\nstage: components\ntype: adopt\n"
          "path: full\nrequirements:\nbranch: adopt/repo\nopened: 2026-08-02\n\n"
          "## Components\n\n- [x] player - engine\n- [ ] export - writers\n\n"
          "## Done checklist (current stage)\n\n- [ ] all components adopted\n\n"
          "## Log\n\n- 2026-08-02 survey: list agreed\n")

    _code, doc, _err = json_out(aegis, capsys, "status", "TASK-ad01", "--json")
    task = doc["task"]
    assert task["id"] == "TASK-ad01" and task["stage"] == "components"
    assert task["step_file"] == "adopt.md" and task["done"] is False
    assert task["header"]["branch"] == "adopt/repo"
    assert task["checklist"] == [{"done": False, "item": "all components adopted"}]
    assert task["components"] == [{"done": True, "item": "player - engine"},
                                  {"done": False, "item": "export - writers"}]
    assert task["log"] == ["2026-08-02 survey: list agreed"]


def test_status_json_rejects_an_unknown_task_without_json_noise(tmp_path,
                                                                capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()
    assert aegis.main(["status", "TASK-dead", "--json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""                     # nothing half-written
    assert captured.err.startswith("error: ")


def test_test_validates_the_task_before_running_anything(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    sentinel = tmp_path / "ran.txt"
    config(agentic,
           f"""test = '{PY} -c "open(r\\"{sentinel}\\", \\"w\\").write(\\"x\\")"'""")
    code, _out = run(aegis, capsys, "test", "--task", "TASK-dead")
    assert code == 1                 # AEGIS error, not the command's exit
    assert not sentinel.exists()     # the suite never ran


def test_corrupt_journal_is_reported_not_a_traceback(tmp_path, monkeypatch,
                                                     capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write_task(agentic, "TASK-aaaa")                       # a good one
    (agentic / "tasks" / "TASK-bbbb.md").write_bytes(b"# TASK-bbbb \xff\xfe\n")

    code, out = run(aegis, capsys, "status")               # list survives
    assert code == 0
    assert "TASK-aaaa" in out and "(unreadable)" in out

    code, out = run(aegis, capsys, "status", "TASK-bbbb")  # one-line error
    assert code == 1

    code, out = run(aegis, capsys, "check")                # reported, exit 0
    assert code == 0
    assert any("not valid UTF-8" in line for line in out.splitlines())


def test_config_shape_warnings(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    write(agentic / "aegis.toml",
          'schema = 2\n\n[commands]\ntest = 7\ntimeout = "soon"\n\n'
          '[layout]\nsource = "src/"\n\n[check]\nignore = "nope"\n')
    _code, out = run(aegis, capsys, "check")
    text = "\n".join(line for line in out.splitlines() if "  config  " in line)
    assert "schema should be the integer 1" in text
    assert "[commands] test should be a string" in text
    assert "[commands] timeout should be int" in text
    assert "[layout] source should be list" in text
    assert "[check] ignore should be list" in text


def test_components_section_is_parsed_and_shown(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write(agentic / "tasks" / "TASK-ad01.md",
          "# TASK-ad01 — Adopt repo\n\nstage: components\ntype: adopt\n"
          "path: full\nrequirements:\nbranch: adopt/repo\nopened: 2026-08-02\n\n"
          "## Components\n\n- [x] player - engine (src/player/)\n"
          "- [ ] export - writers (src/export/)\n\n"
          "## Done checklist (current stage)\n\n- [ ] all components adopted\n\n"
          "## Log\n\n- 2026-08-02 survey: list agreed\n")
    _code, out = run(aegis, capsys, "status", "TASK-ad01")
    assert "components: 1/2 adopted" in out
    assert "[ ] export - writers (src/export/)" in out
    assert "adopt.md (stage 'components')" in out

    run(aegis, capsys, "report", "TASK-ad01")
    text = (agentic / "tasks" / "TASK-ad01.md").read_text(encoding="utf-8")
    assert "- components: 1/2 adopted; open: export - writers (src/export/)" in text


def test_symlinked_journal_cannot_escape_on_posix(tmp_path, capsys):
    import sys as _sys
    if _sys.platform == "win32":
        import pytest as _pytest
        _pytest.skip("symlink semantics differ on Windows")
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    outside = tmp_path.parent / "outside_victim.md"
    outside.write_text("# TASK-abcd — victim\n\nstage: build\n")
    (agentic / "tasks" / "TASK-abcd.md").symlink_to(outside)
    code, _out = run(aegis, capsys, "status", "TASK-abcd")
    assert code == 1


def test_an_unusable_timeout_value_means_no_limit(tmp_path):
    """Zero, negative, Boolean and unreadable values all mean no limit."""
    _agentic, aegis = make_repo(tmp_path)
    assert aegis.command_timeout({"commands": {"timeout": 0}}) is None
    assert aegis.command_timeout({"commands": {"timeout": -5}}) is None
    assert aegis.command_timeout({"commands": {"timeout": True}}) is None
    assert aegis.command_timeout({"commands": {"timeout": False}}) is None
    assert aegis.command_timeout({"commands": {"timeout": "x"}}) is None


def test_invalid_utf8_config_is_a_one_line_error(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    (agentic / "aegis.toml").write_bytes(b"schema = 1\n\xff\xfe garbage\n")
    code, _out = run(aegis, capsys, "check")
    assert code == 1  # UserError, not a traceback


@needs_git
def test_configured_default_branch_wins_over_local_master(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)  # local master exists
    config(agentic, f"test = {cmd_exit(0)}")
    text = (agentic / "aegis.toml").read_text(encoding="utf-8")
    write(agentic / "aegis.toml",
          text.replace('source = ["src/"]',
                       'default_branch = "develop"\nsource = ["src/"]'))
    _code, out = run(aegis, capsys, "check")
    assert "no merge base between HEAD and develop" in out


@needs_git
def test_impacted_rejects_repository_escaping_references(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic,
           f"test = {cmd_exit(0)}\ntest_impacted = \"never run {{tests}}\"")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["../../outside_test.py"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    _code, out = run(aegis, capsys, "test", "--impacted")
    assert "impacted: test reference escapes the repository" in out


@needs_git
def test_check_task_notes_a_branch_mismatch(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)  # current branch: feature
    write_task(agentic, "TASK-ab12")          # helper writes branch: feature
    text = (agentic / "tasks" / "TASK-ab12.md").read_text(encoding="utf-8")
    write(agentic / "tasks" / "TASK-ab12.md",
          text.replace("branch: feature", "branch: task/somewhere-else"))
    _code, out = run(aegis, capsys, "check", "--task", "TASK-ab12")
    assert "journal branch 'task/somewhere-else' != current 'feature'" in out


# TESTS - [commands] workdir


def argdump(path: Path) -> None:
    """@brief A script recording its argv and its working directory."""
    write(path,
          "import pathlib, sys\n"
          "pathlib.Path('args.txt').write_text(' '.join(sys.argv[1:]))\n")


def test_configured_workdir_runs_the_command_there(tmp_path, capsys):
    """REQ-PLAT-83b50d11: commands run in [commands] workdir, not the root."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    argdump(tmp_path / "app" / "argdump.py")
    config(agentic, f'workdir = "app"\ntest = \'{PY} argdump.py ran\'')
    code, _out = run(aegis, capsys, "test")
    assert code == 0
    assert (tmp_path / "app" / "args.txt").read_text() == "ran"
    assert not (tmp_path / "args.txt").exists()


def test_workdir_is_not_executed_as_a_command(tmp_path, capsys):
    """REQ-PLAT-83b50d11: workdir names configuration, never a command."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    config(agentic, f'workdir = "."\ntest = {cmd_exit(0)}')
    _code, out = run(aegis, capsys, "check", "--run")
    assert "run: test ok" in out
    assert "workdir" not in out


# TESTS - impacted references are rebased onto the workdir


@needs_git
def test_impacted_rebases_references_to_the_workdir(tmp_path, capsys):
    """REQ-TEST-2bfb7a86: stored refs are repo-relative, run refs are not."""
    agentic, aegis = make_git_repo(tmp_path)
    argdump(tmp_path / "app" / "argdump.py")
    config(agentic,
           f'workdir = "app"\ntest = {cmd_exit(0)}\n'
           f"test_impacted = '{PY} argdump.py {{tests}}'",
           source='["app/src/"]', tests='["app/tests/"]')
    write_req(agentic, "REQ-FUNC-1111", paths='["app/src/thing.py"]',
              tests='["app/tests/test_thing.py::test_x"]')
    write(tmp_path / "app" / "src" / "thing.py", "def thing():\n    return 2\n")

    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "test --impacted (1 test ref(s)): exit 0" in out
    assert (tmp_path / "app" / "args.txt").read_text() == \
        "tests/test_thing.py::test_x"


@needs_git
def test_impacted_falls_back_when_a_reference_is_outside_the_workdir(tmp_path,
                                                                    capsys):
    """REQ-TEST-2bfb7a86: a ref the command could not reach is unusable."""
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic,
           f'workdir = "app"\ntest = {cmd_exit(0)}\n'
           'test_impacted = "never run {tests}"',
           source='["app/src/"]', tests='["tests/"]')
    write_req(agentic, "REQ-FUNC-1111", paths='["app/src/thing.py"]',
              tests='["tests/test_app.py::test_app"]')
    write(tmp_path / "app" / "src" / "thing.py", "def thing():\n    return 2\n")
    _code, out = run(aegis, capsys, "test", "--impacted")
    assert "impacted: test reference is outside the command working directory" \
        in out


# TESTS - an oversized impacted set degrades instead of failing to launch


@needs_git
def test_impacted_collapses_to_test_files_when_the_command_is_too_long(
        tmp_path, monkeypatch, capsys):
    """REQ-TEST-5d8f424b: too long to launch becomes one entry per file."""
    agentic, aegis = make_git_repo(tmp_path)
    argdump(tmp_path / "argdump.py")
    template = f"{PY} argdump.py {{tests}}"
    config(agentic, f"test = {cmd_exit(0)}\ntest_impacted = '{template}'")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["tests/test_app.py::test_one",'
                    ' "tests/test_app.py::test_two",'
                    ' "tests/test_more.py::test_three"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    # exactly wide enough for the two files, too narrow for the three
    # selectors, whatever this interpreter's path length happens to be
    files_command = template.replace("{tests}",
                                     "tests/test_app.py tests/test_more.py")
    monkeypatch.setattr(aegis, "COMMAND_LENGTH_LIMIT", len(files_command))

    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "impacted: too long to launch - reduced to 2 test file(s)" in out
    assert (tmp_path / "args.txt").read_text() == \
        "tests/test_app.py tests/test_more.py"


@needs_git
def test_impacted_falls_back_when_even_the_files_are_too_long(tmp_path,
                                                              monkeypatch,
                                                              capsys):
    """REQ-TEST-07679fdc: unlaunchable is a visible full-suite fallback."""
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic,
           f"test = {cmd_exit(0)}\n"
           'test_impacted = "never run {tests}"')
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["tests/test_app.py::test_one",'
                    ' "tests/test_more.py::test_two"]')
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    monkeypatch.setattr(aegis, "COMMAND_LENGTH_LIMIT", 20)

    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "impacted: still too long to launch after reduction" in out


# TESTS - the impacted diff basis is selectable


@needs_git
def test_impacted_base_option_narrows_the_diff_basis(tmp_path, capsys):
    """REQ-TEST-db8d4d31: --base selects against a revision, not the fork."""
    agentic, aegis = make_git_repo(tmp_path)
    argdump(tmp_path / "argdump.py")
    config(agentic,
           f"test = {cmd_exit(0)}\n"
           f"test_impacted = '{PY} argdump.py {{tests}}'")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["tests/test_app.py::test_app"]')
    write_req(agentic, "REQ-FUNC-2222", paths='["src/other.py"]',
              tests='["tests/test_other.py::test_other"]')
    # committed on the branch: inside the merge-base diff, outside HEAD's
    write(tmp_path / "src" / "other.py", "def other():\n    return 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "committed work")
    # uncommitted: inside both
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")

    code, out = run(aegis, capsys, "test", "--impacted")
    assert code == 0
    assert "test --impacted (2 test ref(s)): exit 0" in out

    code, out = run(aegis, capsys, "test", "--impacted", "--base", "HEAD")
    assert code == 0
    assert "test --impacted (1 test ref(s)): exit 0" in out
    assert (tmp_path / "args.txt").read_text() == \
        "tests/test_app.py::test_app"


# TESTS - command time limits


def test_no_time_limit_is_imposed_by_default(tmp_path):
    """REQ-PLAT-7365bed5: the shipped configuration limits nothing."""
    _agentic, aegis = make_repo(tmp_path)
    assert aegis.command_timeout({}) is None
    assert aegis.command_timeout({"commands": {"timeout": 0}}) is None
    assert aegis.command_timeout({"commands": {"timeout": True}}) is None
    assert aegis.command_timeout({"commands": {"timeout": "x"}}) is None
    # a repository that wants a limit still gets exactly the one it asked for
    assert aegis.command_timeout({"commands": {"timeout": 90}}) == 90


def test_a_per_command_limit_overrides_the_shared_one(tmp_path, monkeypatch,
                                                       capsys):
    """REQ-PLAT-19a2faa6: one number cannot fit a suite and a linter."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic,
           f"quick = {cmd_exit(0)}\n"
           f"slow = '{PY} -c \"import time; time.sleep(30)\"'\ntimeout = 600",
           extra="[timeouts]\nslow = 1")
    assert aegis.command_timeout({"commands": {"timeout": 600}}) == 600

    _code, out = run(aegis, capsys, "check", "--run")
    assert "run: quick ok" in out
    assert any("run: slow stopped at its 1s limit" in line
               for line in out.splitlines())


def test_a_stopped_command_is_reported_as_unproven(tmp_path, monkeypatch,
                                                    capsys):
    """REQ-REL-bcd7400b: a command that was cut off produced no verdict."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    config(agentic,
           f"slow = '{PY} -c \"import time; time.sleep(30)\"'\ntimeout = 1")
    _code, out = run(aegis, capsys, "check", "--run")

    stopped = [line for line in out.splitlines()
               if line.startswith("ERROR") and "command-timeout" in line]
    assert stopped, out
    assert "nothing proven" in stopped[0]
    # never conflated with a command that ran to completion and failed
    assert not any("command-failed" in line for line in out.splitlines())


# TESTS - the recorded task base


@needs_git
def test_report_diffs_against_the_recorded_task_base(tmp_path, capsys):
    """REQ-FUNC-791ebe07: a report must describe this task, not the branch."""
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic, f"test = {cmd_exit(0)}")
    # earlier, unrelated work already on the branch
    write(tmp_path / "src" / "earlier.py", "def earlier():\n    return 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "earlier work")
    head = git(tmp_path, "rev-parse", "HEAD").strip()
    # this task's own work, after that point
    write(tmp_path / "src" / "mine.py", "def mine():\n    return 1\n")

    def reported_basis_and_count(tid: str) -> tuple[str, int]:
        text = (agentic / "tasks" / f"{tid}.md").read_text(encoding="utf-8")
        line = next(ln for ln in text.splitlines() if ln.startswith("- diff vs "))
        basis, _, counts = line[len("- diff vs "):].partition(": ")
        return basis, int(counts.split(" ")[0])

    write_task(agentic, "TASK-ab12", base=head)
    assert aegis.main(["report", "TASK-ab12"]) == 0
    scoped_basis, scoped = reported_basis_and_count("TASK-ab12")
    assert scoped_basis == f"task base {head[:7]}"

    # without the header line the merge-base measurement returns, and counts
    # the earlier commit as this task's work too
    write_task(agentic, "TASK-cd34")
    assert aegis.main(["report", "TASK-cd34"]) == 0
    whole_basis, whole = reported_basis_and_count("TASK-cd34")
    assert whole_basis == "merge base"
    assert scoped < whole, (scoped, whole)


# TESTS - diagram


def knowledge(agentic: Path, stem: str, name: str, *rids: str) -> Path:
    """@brief A component page claiming `rids` under its Key behaviors."""
    behaviors = "".join(f"- `{rid}` - one line.\n" for rid in rids)
    return write(agentic / "knowledge" / f"{stem}.md",
                 f"# {name}\n\n## Purpose\n\nA component.\n\n"
                 f"## Key behaviors\n\n{behaviors}")


def register(agentic: Path, tmp_path: Path) -> None:
    """@brief One requirement of every coverage class, most of them claimed."""
    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    pass\n")
    write_req(agentic, "REQ-FUNC-1111", title="Covered behavior",
              tests='["tests/test_app.py::test_app"]')
    write_req(agentic, "REQ-FUNC-2222", title="By-hand behavior",
              verification="Inspection: read the printed page.")
    write_req(agentic, "REQ-FUNC-3333", title="Uncovered behavior")
    write_req(agentic, "REQ-FUNC-5555", title="Broken-link behavior",
              tests='["tests/test_gone.py::test_gone"]')
    write_req(agentic, "REQ-FUNC-6666", title="Drafted behavior", status="draft")
    write_req(agentic, "REQ-FUNC-7777", title="Withdrawn behavior", status="retired")
    write_req(agentic, "REQ-DATA-4444", folder="data", title="Unclaimed behavior")
    knowledge(agentic, "parser", "Parser",
              "REQ-FUNC-1111", "REQ-FUNC-2222", "REQ-FUNC-3333",
              "REQ-FUNC-5555", "REQ-FUNC-6666", "REQ-FUNC-7777")


def test_diagram_groups_requirements_by_component_and_coverage(tmp_path, capsys):
    """REQ-FUNC-6b4ff1ad: every mark is read off a requirement field."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    register(agentic, tmp_path)

    code, out = run(aegis, capsys, "diagram")
    assert code == 0
    assert out.startswith("flowchart LR\n")
    assert 'subgraph parser["Parser"]' in out
    assert 'REQ_FUNC_1111["REQ-FUNC-1111<br/>Covered behavior"]:::tested' in out
    assert 'REQ_FUNC_2222["REQ-FUNC-2222<br/>By-hand behavior"]:::manual' in out
    assert 'REQ_FUNC_3333["REQ-FUNC-3333<br/>Uncovered behavior"]:::uncovered' in out
    # a link that no longer resolves is its own class: it is the check's
    # warning drawn, not a behavior nobody ever verified
    assert 'REQ_FUNC_5555["REQ-FUNC-5555<br/>Broken-link behavior"]:::broken' in out
    assert 'REQ_FUNC_6666["REQ-FUNC-6666<br/>Drafted behavior"]:::draft' in out
    assert 'REQ_FUNC_7777["REQ-FUNC-7777<br/>Withdrawn behavior"]:::retired' in out
    # a requirement no page claims is shown apart, never dropped
    assert 'subgraph unclaimed["(no knowledge page)"]' in out
    assert 'REQ_DATA_4444["REQ-DATA-4444<br/>Unclaimed behavior"]:::uncovered' in out
    for name in ("tested", "manual", "broken", "uncovered", "draft", "retired"):
        assert f"classDef {name}" in out


def test_every_coverage_class_matches_what_check_reports(tmp_path, capsys):
    """REQ-FUNC-6b4ff1ad: the picture renders the findings, never rivals them."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    register(agentic, tmp_path)

    records = {str(data["id"]): data
               for _relpath, _path, data in aegis.scan_requirements(
                   lambda *_a: None, lambda _p: False)}
    assert aegis.coverage_class(records["REQ-FUNC-1111"]) == "tested"
    assert aegis.coverage_class(records["REQ-FUNC-2222"]) == "manual"
    assert aegis.coverage_class(records["REQ-FUNC-3333"]) == "uncovered"
    assert aegis.coverage_class(records["REQ-FUNC-5555"]) == "broken"
    assert aegis.coverage_class(records["REQ-FUNC-6666"]) == "draft"
    assert aegis.coverage_class(records["REQ-FUNC-7777"]) == "retired"

    # the classes that stand for a finding are exactly the ones check reports,
    # and the two silent ones are exactly the ones it says nothing about
    findings = run_check(aegis, capsys)
    warned = {Path(line.split()[2]).stem
              for line in lines_for(findings, "no-linked-tests")}
    noted = {Path(line.split()[2]).stem
             for line in lines_for(findings, "manual-verification")}
    assert warned == {"REQ-FUNC-3333", "REQ-DATA-4444", "REQ-FUNC-5555"}
    assert noted == {"REQ-FUNC-2222"}
    # the draft and the retired one are in neither: check is silent about both,
    # so neither may be drawn in a color that says otherwise
    assert "REQ-FUNC-6666" not in findings
    assert "REQ-FUNC-7777" not in findings


def test_a_declared_method_does_not_excuse_a_link_that_no_longer_resolves(
        tmp_path, capsys):
    """REQ-FUNC-6b4ff1ad: a broken link outranks the by-hand method beside it."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    record = {"status": "active",
              "linked_tests": ["tests/gone.py::test_gone"],
              "verification": "Manual: inspect the printed page."}
    assert aegis.coverage_class(record) == "broken"
    # and a second, resolving link does not hide the broken one either
    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    pass\n")
    record["linked_tests"].append("tests/test_app.py::test_app")
    assert aegis.coverage_class(record) == "broken"


def test_diagram_writes_utf8_independent_of_the_console_encoding(tmp_path,
                                                                 capsys):
    """REQ-FUNC-6b4ff1ad: --out is a file artifact, not console output."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write_req(agentic, "REQ-FUNC-1111", title="Grüße — a rendered dash")
    target = tmp_path / "docs" / "coverage.mmd"

    code, out = run(aegis, capsys, "diagram", "--out", str(target))
    assert code == 0
    assert "flowchart LR" not in out
    assert "diagram written to docs/coverage.mmd" in out
    assert target.read_bytes().decode("utf-8").count("Grüße — a rendered dash") == 1


def test_diagram_narrows_to_one_component(tmp_path, capsys):
    """REQ-FUNC-e46f1d0c: a named component carries only its own behaviors."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    register(agentic, tmp_path)
    knowledge(agentic, "writer", "Writer", "REQ-DATA-4444")

    code, out = run(aegis, capsys, "diagram", "--component", "writer")
    assert code == 0
    assert "REQ-DATA-4444" in out
    assert "REQ-FUNC-1111" not in out
    assert 'subgraph parser[' not in out


def test_diagram_narrows_to_one_task(tmp_path, capsys):
    """REQ-FUNC-e46f1d0c: a named task carries only the header's requirements."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    register(agentic, tmp_path)
    write_task(agentic, "TASK-ab12", reqs="REQ-FUNC-2222, REQ-DATA-4444")

    code, out = run(aegis, capsys, "diagram", "--task", "TASK-ab12")
    assert code == 0
    assert "REQ-FUNC-2222" in out
    assert "REQ-DATA-4444" in out
    assert "REQ-FUNC-1111" not in out


def test_diagram_rejects_a_scope_that_does_not_exist(tmp_path, capsys):
    """REQ-FUNC-e46f1d0c: an empty picture would read as an empty register."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    register(agentic, tmp_path)

    assert aegis.main(["diagram", "--component", "nope"]) == 1
    assert "nope" in capsys.readouterr().err
    assert aegis.main(["diagram", "--task", "TASK-9999"]) == 1
    assert "TASK-9999" in capsys.readouterr().err

    # two scopes at once would answer a question nobody asked; like every
    # expected CLI error it is one stderr line and exit 1, not an argparse dump
    assert aegis.main(
        ["diagram", "--component", "parser", "--task", "TASK-ab12"]) == 1
    err = capsys.readouterr().err
    assert "--component and --task" in err
    assert len([line for line in err.splitlines() if line]) == 1


# TESTS - report leads with judgement


def journal_with_log(agentic: Path, tid: str, log: str) -> Path:
    """@brief A journal whose Log section is exactly `log`."""
    return write(
        agentic / "tasks" / f"{tid}.md",
        f"# {tid} — a task\n\nstage: deliver\ntype: feature\npath: full\n"
        f"requirements: \nbranch: feature\nbase: \nopened: 2026-08-02\n\n"
        "## Done checklist (current stage)\n\n- [x] done\n\n"
        f"## Log\n\n{log}\n",
    )


def test_report_leads_with_the_recorded_deviations(tmp_path, monkeypatch, capsys):
    """REQ-UX-48bb759b: judgement above totals, in the order it was recorded."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    journal_with_log(agentic, "TASK-ab12",
                     "- 2026-08-02 frame: opened\n"
                     "- 2026-08-02 frame: DEVIATION frame - no task branch,\n"
                     "  at the owner's instruction.\n"
                     "- 2026-08-02 build: implemented\n"
                     "- 2026-08-02 validate: DEVIATION validate - accepted a warning.\n")

    assert aegis.main(["report", "TASK-ab12"]) == 0
    text = (agentic / "tasks" / "TASK-ab12.md").read_text(encoding="utf-8")
    body = text.split("## Delivery report (")[1]

    assert "- deviations: 2 recorded" in body
    # recorded wording, and a wrapped line is carried whole
    assert "frame - no task branch, at the owner's instruction." in body
    assert "validate - accepted a warning." in body
    # order preserved, and both stand above the totals
    assert body.index("no task branch") < body.index("accepted a warning")
    assert body.index("accepted a warning") < body.index("- diff vs ")
    assert body.index("- deviations:") < body.index("- checks:")


def test_report_says_plainly_when_no_deviation_was_recorded(tmp_path, monkeypatch,
                                                            capsys):
    """REQ-UX-48bb759b: silence must be stated, not inferred from absence."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    journal_with_log(agentic, "TASK-cd34", "- 2026-08-02 frame: opened\n")

    assert aegis.main(["report", "TASK-cd34"]) == 0
    text = (agentic / "tasks" / "TASK-cd34.md").read_text(encoding="utf-8")
    assert "- deviations: none recorded" in text


def test_report_harvests_the_marker_shape_and_not_a_mention_of_it(tmp_path,
                                                                  monkeypatch,
                                                                  capsys):
    """REQ-UX-48bb759b: the marker is `DEVIATION <stage>`, never the word."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)

    # every line here talks about deviations; none of them records one
    for text in ("- Discussed DEVIATION format - we agreed on one line.\n",
                 "- Reviewed the DEVIATION policy: it says one line per call.\n",
                 "- See AGENTS.md for DEVIATION lines - they are mandatory.\n",
                 "- no-DEVIATION: a hyphenated prefix is a different word.\n",
                 "- The contract prints `DEVIATION <stage>: <what> - <why>`.\n",
                 "- Two DEVIATIONS: both were about the same warning.\n",
                 # a journal explaining the rule quotes the marker, and the
                 # stage is the only thing that tells the two apart
                 "- The stage-less `DEVIATION:` form is not a record.\n",
                 "- DEVIATION framework: a stage prefix is not a stage.\n"):
        assert aegis.recorded_deviations(text) == [], text

    # and the recorded shape, bulleted or bare, in both its spellings
    assert aegis.recorded_deviations(
        "## Log\n\nDEVIATION build: skipped perf test - flaky\n"
    ) == ["build: skipped perf test - flaky"]
    assert aegis.recorded_deviations(
        "- DEVIATION build: skipped perf test - flaky\n"
    ) == ["build: skipped perf test - flaky"]
    assert aegis.recorded_deviations(
        "DEVIATION validate - accepted a warning\n  about a stale path.\n"
    ) == ["validate - accepted a warning about a stale path."]


def test_report_does_not_re_list_the_deviations_an_earlier_report_carried(
        tmp_path, monkeypatch, capsys):
    """REQ-UX-48bb759b: the token is stripped, so the count cannot grow."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    journal_with_log(agentic, "TASK-ef56",
                     "- 2026-08-02 build: DEVIATION build - skipped the slow suite.\n"
                     "DEVIATION validate: accepted one warning.\n"
                     "- 2026-08-02 deliver: two DEVIATION lines - see above.\n")

    assert aegis.main(["report", "TASK-ef56"]) == 0
    assert aegis.main(["report", "TASK-ef56"]) == 0
    text = (agentic / "tasks" / "TASK-ef56.md").read_text(encoding="utf-8")
    assert text.count("- deviations: 2 recorded") == 2
    assert "- deviations: 3 recorded" not in text
    assert "- deviations: 4 recorded" not in text


# TESTS - explain


def governed_repo(agentic: Path, tmp_path: Path) -> None:
    """@brief Two components, one shared file, and one file nobody claims."""
    write(tmp_path / "src" / "export" / "m3u.py", "def write():\n    pass\n")
    write(tmp_path / "src" / "orphan.py", "def nobody():\n    pass\n")
    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    pass\n")
    write_req(agentic, "REQ-FUNC-1111", title="Export playlist as M3U",
              paths='["src/export/"]',
              tests='["tests/test_app.py::test_app"]')
    write_req(agentic, "REQ-FUNC-2222", title="Preserve relative paths",
              paths='["src/export/m3u.py"]',
              verification="Inspection: open the written file.")
    write_req(agentic, "REQ-DATA-3333", folder="data", title="Unclaimed behavior",
              paths='["src/export/m3u.py"]')
    knowledge(agentic, "export", "Export writers", "REQ-FUNC-1111")
    knowledge(agentic, "paths", "Path handling", "REQ-FUNC-2222")
    write_task(agentic, "TASK-ab12", stage="done", reqs="REQ-FUNC-1111")


def test_explain_traces_a_path_to_its_requirements_and_tasks(tmp_path, capsys):
    """REQ-FUNC-0f4eb4c5: file -> requirements -> components -> journals."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    governed_repo(agentic, tmp_path)

    code, out = run(aegis, capsys, "explain", "src/export/m3u.py")
    assert code == 0
    # a directory entry in affected_paths still covers the file beneath it
    assert "REQ-FUNC-1111" in out and "Export playlist as M3U" in out
    assert "REQ-FUNC-2222" in out and "REQ-DATA-3333" in out
    # grouped by the component whose page claims each requirement
    assert "Export writers" in out and "Path handling" in out
    assert "no knowledge page" in out
    # how each one is verified, read off the same fields check judges by
    assert "tested" in out and "manual" in out and "uncovered" in out
    # the journals that list them
    assert "TASK-ab12" in out


def test_explain_reports_an_ungoverned_path_plainly(tmp_path, capsys):
    """REQ-FUNC-0f4eb4c5: ungoverned code is a finding, not an empty page."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    governed_repo(agentic, tmp_path)

    code, out = run(aegis, capsys, "explain", "src/orphan.py")
    assert code == 0
    assert "no requirement" in out.lower()
    assert "REQ-FUNC-1111" not in out


def test_explain_accepts_native_and_absolute_paths(tmp_path, capsys):
    """REQ-FUNC-0f4eb4c5: an operator pastes whatever their shell gave them."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    governed_repo(agentic, tmp_path)

    _code, native = run(aegis, capsys, "explain", r"src\export\m3u.py")
    _code, absolute = run(aegis, capsys, "explain", str(tmp_path / "src" / "export" / "m3u.py"))
    for out in (native, absolute):
        assert "src/export/m3u.py" in out
        assert "REQ-FUNC-1111" in out

    assert aegis.main(["explain", str(tmp_path.parent / "elsewhere.py")]) == 1
    assert "outside this repository" in capsys.readouterr().err
