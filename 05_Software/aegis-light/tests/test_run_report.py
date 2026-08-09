#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import sys
from pathlib import Path

from test_check import (
    make_git_repo,
    make_repo,
    needs_git,
    write,
    write_req,
    write_task,
)

# CONSTANTS

PY = f'"{sys.executable}"'


# HELPERS


def config(agentic: Path, commands: str, check: str = "") -> None:
    """@brief Write an aegis.toml with the given [commands] and [check] bodies."""
    write(
        agentic / "aegis.toml",
        f"schema = 1\n\n[commands]\n{commands}\n\n"
        f'[layout]\nsource = ["src/"]\ntests = ["tests/"]\n\n[check]\n{check}\n',
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
    code, out = run(aegis, capsys, "check", "--strict")
    assert code == 0
    assert "strict: ok" in out


def test_strict_fails_on_an_error(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
    config(agentic,
           f"bad = '{PY} -c \"print(chr(66) + chr(79) + chr(79) + chr(77));"
           " import sys; sys.exit(2)\"'")
    _code, out = run(aegis, capsys, "check", "--run")
    assert "  | BOOM" in out


def test_run_skips_templates_and_timeout_key(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
    config(agentic,
           "test_impacted = \"pytest {tests}\"\ntimeout = 60")
    _code, out = run(aegis, capsys, "check", "--run")
    assert "run: nothing ran" in out  # neither the template nor timeout ran


def test_run_times_out_as_exit_124(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
    config(agentic,
           f"slow = '{PY} -c \"import time; time.sleep(30)\"'\ntimeout = 1")
    _code, out = run(aegis, capsys, "check", "--run")
    assert any(line.startswith("run: slow FAIL exit 124 (")
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
    assert b"AEGIS-LIGHT:BEGIN" in first

    # corrupt the digest, re-init: refresh must not eat trailing user bytes
    text = first.replace(b"advisory", b"advis0ry")
    tail = b"KEEP-THIS-TRAILING-LINE\r\n"
    (tmp_path / "CLAUDE.md").write_bytes(text + tail)
    aegis.main(["init"])
    refreshed = (tmp_path / "CLAUDE.md").read_bytes()
    assert tail in refreshed
    assert b"advis0ry" not in refreshed
    assert mine.encode() in refreshed


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
    assert "- checks: errors=0 warnings=1 notes=6" in text
    assert "- checklist: 1/2 done; open: report appended" in text

    aegis.main(["report", "TASK-ab12"])  # append-only: a second dated section
    text = (agentic / "tasks" / "TASK-ab12.md").read_text(encoding="utf-8")
    assert text.count("## Delivery report (") == 2


def test_report_rejects_an_unknown_task(tmp_path, capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    assert run(aegis, capsys, "report", "TASK-dead")[0] == 1


# TESTS - review-hardening regressions


def test_crafted_task_ids_cannot_escape_the_tasks_folder(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
    config(agentic, f"test = {cmd_exit(0)}")
    _code, out = run(aegis, capsys, "check", "--run")
    lines = [line for line in out.splitlines() if line.startswith("run: test")]
    assert lines[0] == "run: test started"       # printed before the wait
    assert lines[1].startswith("run: test ok (")


def test_findings_are_capped_unless_full_or_strict(tmp_path, monkeypatch,
                                                   capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
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


def test_command_timeout_is_clamped_to_at_least_one_second(tmp_path):
    _agentic, aegis = make_repo(tmp_path)
    assert aegis.command_timeout({"commands": {"timeout": 0}}) == 1
    assert aegis.command_timeout({"commands": {"timeout": -5}}) == 1
    assert aegis.command_timeout({"commands": {"timeout": "x"}}) == 1800


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
