#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_check.py
@brief P3 tests for `aegis check`: every catalog check firing and silent.
@details Non-git tests monkeypatch `run_git` to None so the five diff-based
         checks degrade to deterministic NOTE lines regardless of the host.
         Diff tests build a real repo with `git init` (skipped cleanly when
         git is absent): one commit on master, then a `feature` branch whose
         worktree changes are the diff against the merge base.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import itertools
import shutil
import subprocess
from pathlib import Path

import pytest

# CONSTANTS

PAYLOAD = Path(__file__).resolve().parents[1] / "template" / ".agentic"
_COUNTER = itertools.count(1000)

HAS_GIT = shutil.which("git") is not None
needs_git = pytest.mark.skipif(not HAS_GIT, reason="git executable not available")

# HELPERS


def make_repo(tmp_path: Path) -> tuple[Path, object]:
    """@brief Copy the payload into tmp_path and import that copy's aegis.py."""
    agentic = tmp_path / ".agentic"
    shutil.copytree(PAYLOAD, agentic)
    spec = importlib.util.spec_from_file_location(
        f"aegis_check_under_test_{next(_COUNTER)}", agentic / "aegis.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return agentic, module


@pytest.fixture
def nogit_repo(tmp_path, monkeypatch):
    """@brief An initialised repo where git is simulated as missing."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    return agentic, aegis


def write(path: Path, text: str) -> Path:
    """@brief Write LF text creating parents; returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def req_toml(rid: str, status: str = "active", prose: str = "One behavior.",
             paths: str = "[]", tests: str = "[]", spec: str = "",
             title: str = "A behavior",
             verification: str = "Run the linked test.") -> str:
    """@brief A minimal valid requirement body with the six required fields."""
    return (
        "schema = 1\n"
        f'id = "{rid}"\n'
        f'title = "{title}"\n'
        f'status = "{status}"\n'
        f'requirement = """\n{prose}\n"""\n'
        f'verification = "{verification}"\n'
        f"affected_paths = {paths}\n"
        f"linked_tests = {tests}\n"
        + (f'spec = "{spec}"\n' if spec else "")
    )


def write_req(agentic: Path, rid: str, folder: str = "functional", **kw) -> Path:
    """@brief Write a requirement file named after its id."""
    return write(agentic / "requirements" / folder / f"{rid}.toml",
                 req_toml(rid, **kw))


def write_task(agentic: Path, tid: str, stage: str = "build", reqs: str = "",
               checklist: str = "- [x] done", base: str = "", parent: str = "") -> Path:
    """@brief Write a parseable task journal."""
    return write(
        agentic / "tasks" / f"{tid}.md",
        f"# {tid} — a task\n\nstage: {stage}\ntype: feature\npath: full\n"
        f"requirements: {reqs}\nparent: {parent}\nbranch: feature\nbase: {base}\n"
        "opened: 2026-08-02\n\n"
        f"## Done checklist (current stage)\n\n{checklist}\n\n"
        "## Log\n\n- 2026-08-02 frame: opened\n",
    )


def run_check(aegis, capsys, *argv: str) -> str:
    """@brief Run `aegis check`, assert exit 0, return the captured output."""
    capsys.readouterr()
    assert aegis.main(["check", *argv]) == 0
    return capsys.readouterr().out


def lines_for(out: str, slug: str) -> list[str]:
    """@brief The finding lines of one check slug."""
    return [line for line in out.splitlines() if f"  {slug}  " in line]


def git(repo: Path, *args: str) -> str:
    """@brief Run git with a fixed identity and signing off; fail loudly.
    Returns stdout, so a test can ask for a commit id."""
    done = subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=T",
         "-c", "commit.gpgsign=false", *args],
        cwd=str(repo), check=True, capture_output=True, timeout=60,
    )
    return done.stdout.decode("utf-8", errors="replace")


def make_git_repo(tmp_path: Path) -> tuple[Path, object]:
    """@brief Initialised repo with one commit on master, working on feature."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write(tmp_path / "src" / "app.py", "def app():\n    return 1\n")
    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    assert True\n")
    git(tmp_path, "init")
    git(tmp_path, "symbolic-ref", "HEAD", "refs/heads/master")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "checkout", "-b", "feature")
    return agentic, aegis


# TESTS - check 1: req-parse


def test_req_parse_fires_on_bad_toml_and_missing_fields(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write(agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml",
          "this is = not [ toml\n")
    write(agentic / "requirements" / "functional" / "REQ-FUNC-2222.toml",
          'schema = 1\nid = "REQ-FUNC-2222"\ntitle = "t"\n')
    out = run_check(aegis, capsys)
    assert any("not valid TOML" in line for line in lines_for(out, "req-parse"))
    assert any("missing/empty: status" in line for line in lines_for(out, "req-parse"))
    assert "result: ERROR" in out


def test_req_parse_silent_on_a_valid_requirement(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", status="draft")
    assert not lines_for(run_check(aegis, capsys), "req-parse")


# TESTS - check 2: dup-id


def test_dup_id_fires_on_mismatch_wrong_folder_and_duplicates(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write(agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml",
          req_toml("REQ-FUNC-9999", status="draft"))
    write(agentic / "requirements" / "security" / "REQ-FUNC-2222.toml",
          req_toml("REQ-FUNC-2222", status="draft"))
    write(agentic / "requirements" / "functional" / "REQ-FUNC-3333.toml",
          req_toml("REQ-FUNC-3333", status="draft"))
    write(agentic / "requirements" / "ux" / "REQ-FUNC-3333.toml",
          req_toml("REQ-FUNC-3333", status="draft"))
    out = run_check(aegis, capsys)
    hits = lines_for(out, "dup-id")
    assert any("id does not match filename" in line for line in hits)
    assert any("id says FUNC, folder expects SEC" in line for line in hits)
    assert sum("duplicate id (2 files)" in line for line in hits) == 2
    assert "result: ERROR" in out


def test_dup_id_silent_on_a_well_placed_unique_id(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-SEC-4444", folder="security", status="draft")
    assert not lines_for(run_check(aegis, capsys), "dup-id")


# TESTS - check 3: journal-header


def test_journal_header_fires_on_garbage_and_unknown_requirement(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write(agentic / "tasks" / "TASK-aaaa.md", "not a journal at all\n")
    write_task(agentic, "TASK-bbbb", reqs="REQ-FUNC-dead")
    out = run_check(aegis, capsys)
    hits = lines_for(out, "journal-header")
    assert any("heading" in line for line in hits)
    assert any("unknown requirement REQ-FUNC-dead" in line for line in hits)
    assert "result: ERROR" in out


def test_journal_header_silent_when_requirements_exist(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", status="draft")
    write_task(agentic, "TASK-bbbb", reqs="REQ-FUNC-1111")
    assert not lines_for(run_check(aegis, capsys), "journal-header")


def test_check_warns_for_missing_or_malformed_parent_relationship(nogit_repo, capsys):
    """REQ-FUNC-3bc8597c: invalid reverse links are visible advisory findings."""
    agentic, aegis = nogit_repo
    write_task(agentic, "TASK-bb22", parent="TASK-dead")
    write_task(agentic, "TASK-cc33", parent="not-a-task")
    hits = lines_for(run_check(aegis, capsys), "journal-header")
    assert any("unknown parent TASK-dead visible in this" in line for line in hits)
    assert any("malformed parent visible in this checkout" in line for line in hits)


def test_check_warns_when_done_parent_has_visible_unfinished_children(nogit_repo, capsys):
    """REQ-FUNC-3bc8597c: integrated delivery reports visible incomplete work."""
    agentic, aegis = nogit_repo
    write_task(agentic, "TASK-aa11", stage="done")
    write_task(agentic, "TASK-bb22", stage="build", parent="TASK-aa11")
    hits = lines_for(run_check(aegis, capsys), "journal-header")
    assert any("done parent has 1 unfinished child visible" in line
               for line in hits)


def test_check_accepts_done_parent_with_done_visible_children(nogit_repo, capsys):
    """REQ-FUNC-3bc8597c: completed visible integration has no relationship warning."""
    agentic, aegis = nogit_repo
    write_task(agentic, "TASK-aa11", stage="done")
    write_task(agentic, "TASK-bb22", stage="done", parent="TASK-aa11")
    assert not any("parent" in line or "child" in line
                   for line in lines_for(run_check(aegis, capsys), "journal-header"))


def test_check_does_not_claim_children_hidden_on_other_branches(nogit_repo, capsys):
    """REQ-FUNC-3bc8597c: check reports only journals present in the checkout."""
    agentic, aegis = nogit_repo
    write_task(agentic, "TASK-aa11", stage="done")
    assert not any("child" in line
                   for line in lines_for(run_check(aegis, capsys), "journal-header"))


def test_check_warns_for_duplicate_or_invalid_ruling_ids(nogit_repo, capsys):
    """REQ-FUNC-7ea14fe4: malformed append-only records stay visible."""
    agentic, aegis = nogit_repo
    path = write_task(agentic, "TASK-aa11")
    write(path, path.read_text(encoding="utf-8") + """

## Rulings

- RULING-001 | date=2026-08-31 | decision=One | reason=First | source=user | supersedes=none
- RULING-001 | date=2026-08-31 | decision=Two | reason=Duplicate | source=user | supersedes=none
- RULING-XYZ | broken
""")
    hits = lines_for(run_check(aegis, capsys), "journal-header")
    assert sum("invalid ruling record" in line for line in hits) == 2


def test_check_warns_for_unknown_superseded_ruling(nogit_repo, capsys):
    """REQ-FUNC-7ea14fe4: supersession references an earlier valid ruling."""
    agentic, aegis = nogit_repo
    path = write_task(agentic, "TASK-aa11")
    write(path, path.read_text(encoding="utf-8") + """

## Rulings

- RULING-001 | date=2026-08-31 | decision=One | reason=First | source=user | supersedes=RULING-099
""")
    hits = lines_for(run_check(aegis, capsys), "journal-header")
    assert any("supersedes unknown earlier" in line for line in hits)


def test_check_warns_for_stale_handoff_current_stage(nogit_repo, capsys):
    """REQ-FUNC-7ea14fe4: a handoff cannot silently survive a stage change."""
    agentic, aegis = nogit_repo
    path = write_task(agentic, "TASK-aa11", stage="validate")
    write(path, path.read_text(encoding="utf-8") + """

## Handoff

current: build
status: ready
next: run review
must_read: .agentic/steps/5_validate.md
blockers:
""")
    hits = lines_for(run_check(aegis, capsys), "journal-header")
    assert any("stale Handoff current build != validate" in line for line in hits)


def test_check_warns_for_invalid_handoff_status(nogit_repo, capsys):
    """REQ-FUNC-7ea14fe4: unknown readiness state is an advisory finding."""
    agentic, aegis = nogit_repo
    path = write_task(agentic, "TASK-aa11")
    write(path, path.read_text(encoding="utf-8") + """

## Handoff

current: build
status: finished
next: continue
must_read:
blockers:
""")
    hits = lines_for(run_check(aegis, capsys), "journal-header")
    assert any("invalid Handoff status" in line for line in hits)


# TESTS - check 4: spec-missing


def test_spec_missing_fires_and_resolves(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", status="draft",
              spec="specs/REQ-FUNC-1111.md")
    out = run_check(aegis, capsys)
    assert any("specs/REQ-FUNC-1111.md" in line
               for line in lines_for(out, "spec-missing"))

    write(agentic / "specs" / "REQ-FUNC-1111.md", "# spec\n")
    assert not lines_for(run_check(aegis, capsys), "spec-missing")


# TESTS - check 6: no-linked-tests


def test_no_linked_tests_fires_on_empty_and_missing_file(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111")
    write_req(agentic, "REQ-FUNC-2222",
              tests='["tests/test_gone.py::test_a"]')
    out = run_check(aegis, capsys)
    hits = lines_for(out, "no-linked-tests")
    assert any("empty linked_tests" in line for line in hits)
    assert any("tests/test_gone.py" in line for line in hits)


def test_no_linked_tests_silent_for_draft_or_existing_file(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    tmp_path = agentic.parent
    write(tmp_path / "tests" / "test_app.py", "def test_a():\n    pass\n")
    write_req(agentic, "REQ-FUNC-1111", status="draft")
    write_req(agentic, "REQ-FUNC-2222", tests='["tests/test_app.py::test_a"]')
    assert not lines_for(run_check(aegis, capsys), "no-linked-tests")


# TESTS - check 7: stale-paths


def test_stale_paths_fires_on_a_gone_file_and_not_on_an_existing_one(nogit_repo,
                                                                     capsys):
    agentic, aegis = nogit_repo
    tmp_path = agentic.parent
    write(tmp_path / "src" / "here.py", "x = 1\n")
    write_req(agentic, "REQ-FUNC-1111", status="draft",
              paths='["src/here.py", "src/gone.py"]')
    out = run_check(aegis, capsys)
    hits = lines_for(out, "stale-paths")
    assert len(hits) == 1
    assert "src/gone.py" in hits[0]


# TESTS - check 10: ticket-ref


def test_ticket_ref_fires_on_ticket_patterns_in_prose(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", status="draft",
              prose="Implements #123 per ABC-42; see also TASK-9f9f.")
    out = run_check(aegis, capsys)
    hits = lines_for(out, "ticket-ref")
    assert any("ticket pattern: #123" in line for line in hits)
    assert any("ticket pattern: ABC-42" in line for line in hits)
    assert any("ticket pattern: TASK-9f9f" in line for line in hits)


def test_ticket_ref_ignores_standards_and_formats(nogit_repo, capsys):
    """Standards share the JIRA shape; technical prose is full of them.
    Found against a real 495-requirement register, where UTF-8 was flagged."""
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", status="draft",
              prose="Text is decoded as UTF-8, hashed with SHA-256, served "
                    "over TLS-1 per RFC-2119, encoded AES-128, licensed "
                    "AGPL-3, resampled to 44100 Hz for MP-3 output.")
    assert not lines_for(run_check(aegis, capsys), "ticket-ref")

    write_req(agentic, "REQ-FUNC-2222", status="draft",
              prose="Implements ABC-123 as agreed.")   # still caught
    assert any("ABC-123" in line
               for line in lines_for(run_check(aegis, capsys), "ticket-ref"))


def test_ticket_ref_silent_on_self_contained_prose(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", status="draft",
              prose="Exporting a playlist writes one M3U file per playlist.")
    assert not lines_for(run_check(aegis, capsys), "ticket-ref")


# TESTS - check 11: unticked-deliver


def test_unticked_deliver_fires_only_in_deliver(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_task(agentic, "TASK-aaaa", stage="deliver",
               checklist="- [x] suite green\n- [ ] report appended")
    write_task(agentic, "TASK-bbbb", stage="build", checklist="- [ ] open item")
    out = run_check(aegis, capsys)
    hits = lines_for(out, "unticked-deliver")
    assert len(hits) == 1
    assert "TASK-aaaa" in hits[0] and "1 unticked item(s)" in hits[0]


def test_unticked_deliver_silent_when_all_ticked(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_task(agentic, "TASK-aaaa", stage="deliver", checklist="- [x] all done")
    assert not lines_for(run_check(aegis, capsys), "unticked-deliver")


# TESTS - diff-based checks against a real git repo


@needs_git
def test_uncovered_source_fires_then_covered_is_silent(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    out = run_check(aegis, capsys)
    hits = lines_for(out, "uncovered-source")
    assert len(hits) == 1 and "src/app.py" in hits[0]

    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests='["tests/test_app.py::test_app"]')
    assert not lines_for(run_check(aegis, capsys), "uncovered-source")


@needs_git
def test_uncovered_source_ignores_deleted_files(tmp_path, capsys):
    """A deleted file stays in the diff, but no requirement can cover a file
    that no longer exists - found in a real repository after a refactor."""
    _agentic, aegis = make_git_repo(tmp_path)
    (tmp_path / "src" / "app.py").unlink()          # remove a covered file
    write(tmp_path / "src" / "kept.py", "y = 1\n")  # and add an uncovered one
    git(tmp_path, "add", "-A")
    out = run_check(aegis, capsys)
    hits = lines_for(out, "uncovered-source")
    assert not any("src/app.py" in line for line in hits)  # deleted: silent
    assert any("src/kept.py" in line for line in hits)     # present: flagged


@needs_git
@pytest.mark.parametrize("stage", ["build", "validate", "deliver"])
def test_scope_drift_fires_and_is_silent_when_requirement_is_touched(tmp_path,
                                                                     capsys,
                                                                     stage):
    agentic, aegis = make_git_repo(tmp_path)
    write_req(agentic, "REQ-FUNC-1111", paths='["src/other.py"]',
              tests='["tests/test_app.py"]')
    write_task(agentic, "TASK-aaaa", stage=stage, reqs="REQ-FUNC-1111")
    git(tmp_path, "add", "-A")           # the artifacts are part of the base,
    git(tmp_path, "commit", "-m", "wip")  # not untracked work-in-progress
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    out = run_check(aegis, capsys)
    assert any("TASK-aaaa" in line
               and f"{stage} diff touches no linked requirement" in line
               for line in lines_for(out, "scope-drift"))

    # touching a file inside the linked requirement's affected_paths silences
    # it - and an untracked new file counts as touched work-in-progress
    write(tmp_path / "src" / "other.py", "y = 1\n")
    assert not lines_for(run_check(aegis, capsys), "scope-drift")


@needs_git
def test_secret_in_diff_fires_on_builtin_and_extra_patterns(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n\n'
          '[check]\nsecret_patterns_extra = ["MYCO_[0-9]{6}"]\nignore = []\n')
    write(tmp_path / "src" / "cfg.py",
          'AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\npassword = "hunter2"\n'
          'MYCO = "MYCO_123456"\n')
    git(tmp_path, "add", "-A")  # `git diff` does not see untracked files
    out = run_check(aegis, capsys)
    hits = lines_for(out, "secret-in-diff")
    assert any("possible secret (aws-style access key)" in line for line in hits)
    assert any("possible secret (password literal)" in line for line in hits)
    assert any("possible secret (secret_patterns_extra)" in line for line in hits)


@needs_git
def test_secret_in_diff_silent_on_a_clean_diff(tmp_path, capsys):
    _agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    assert not lines_for(run_check(aegis, capsys), "secret-in-diff")


@needs_git
def test_outside_layout_ignores_the_pointer_files_init_creates(tmp_path,
                                                               capsys):
    """A fresh install must not greet the user with warnings about the
    AGENTS.md / CLAUDE.md / QWEN.md that init itself wrote."""
    _agentic, aegis = make_git_repo(tmp_path)
    aegis.main(["init"])          # re-run: pointer files are in the diff
    git(tmp_path, "add", "-A")
    out = run_check(aegis, capsys)
    assert not [line for line in lines_for(out, "outside-layout")
                if any(name in line for name in aegis.POINTER_FILES)]


@needs_git
def test_outside_layout_fires_for_a_stray_file_only(tmp_path, capsys):
    _agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "docs" / "notes.md", "stray\n")
    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    assert 1\n")
    git(tmp_path, "add", "-A")  # `git diff` does not see untracked files
    out = run_check(aegis, capsys)
    hits = lines_for(out, "outside-layout")
    assert len(hits) == 1 and "docs/notes.md" in hits[0]


@needs_git
def test_documentation_layout_keeps_security_and_source_checks(tmp_path, capsys):
    """@brief Declared documentation is in layout, still scanned, not source."""
    agentic, aegis = make_git_repo(tmp_path)
    write(agentic / "aegis.toml",
          'schema = 1\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n'
          'docs = ["docs/", "CHANGELOG.md"]\n[check]\n'
          'secret_patterns_extra = ["EXAMPLE_SECRET_[0-9]{6}"]\n')
    write(tmp_path / "docs" / "guide.md", "EXAMPLE_SECRET_123456\n")
    write(tmp_path / "CHANGELOG.md", "Documented behavior.\n")
    write(tmp_path / "stray.md", "Undeclared documentation.\n")
    out = run_check(aegis, capsys)
    hits = lines_for(out, "outside-layout")
    assert len(hits) == 1 and "stray.md" in hits[0]
    assert any("docs/guide.md" in line
               for line in lines_for(out, "secret-in-diff"))
    assert not lines_for(out, "uncovered-source")
    assert not lines_for(out, "source-no-test-changes")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    out = run_check(aegis, capsys)
    assert lines_for(out, "uncovered-source")
    assert lines_for(out, "source-no-test-changes")


def test_documentation_layout_reports_invalid_type(nogit_repo, capsys):
    """@brief Malformed documentation globs produce an actionable finding."""
    agentic, aegis = nogit_repo
    write(agentic / "aegis.toml", 'schema = 1\n[layout]\ndocs = "docs/"\n')
    assert any("[layout] docs should be list" in line for line in
               lines_for(run_check(aegis, capsys), "config"))


@needs_git
def test_source_no_test_changes_fires_then_a_test_change_silences_it(tmp_path,
                                                                     capsys):
    _agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    out = run_check(aegis, capsys)
    hits = lines_for(out, "source-no-test-changes")
    assert len(hits) == 1 and "1 source file(s) changed, no test changes" in hits[0]

    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    assert 2\n")
    assert not lines_for(run_check(aegis, capsys), "source-no-test-changes")


# TESTS - untracked work-in-progress is visible


@needs_git
def test_untracked_source_file_fires_uncovered_and_secret_checks(tmp_path,
                                                                 capsys):
    _agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "src" / "brand_new.py",
          'AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n')  # never staged, never added
    out = run_check(aegis, capsys)
    assert any("src/brand_new.py" in line
               for line in lines_for(out, "uncovered-source"))
    assert any("src/brand_new.py" in line for line in lines_for(out, "secret-in-diff"))
    assert any("src/brand_new.py" in line or "(diff)" in line
               for line in lines_for(out, "source-no-test-changes"))


#: a patch where the second file's header is git-quoted, so the header
#: regex cannot parse it - exactly the tracked non-ASCII/quoted-name case.
QUOTED_PATCH = (
    'diff --git a/src/app.py b/src/app.py\n'
    '--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n'
    '+def app():\n'
    'diff --git "a/src/we\\"ird.py" "b/src/we\\"ird.py"\n'
    '--- "a/src/we\\"ird.py"\n+++ "b/src/we\\"ird.py"\n@@ -0,0 +1 @@\n'
    '+password = "hunter2"\n'
)


def stub_git(patch: str, names: list[str]):
    """@brief A run_git stand-in serving one crafted diff, no real repo."""
    def fake(*args):
        if args[:1] == ("rev-parse",) and args[1:2] == ("--git-dir",):
            return 0, ".git"
        if args[:1] == ("symbolic-ref",):
            return 1, ""
        if args[:1] == ("rev-parse",):        # refs/heads/master probe
            return 0, "ok"
        if args[:1] == ("merge-base",):
            return 0, "basecommit"
        if "--name-only" in args:
            return 0, "\0".join(names)
        if "diff" in args:
            return 0, patch
        return 0, ""                          # ls-files --others
    return fake


def test_quoted_header_does_not_inherit_the_previous_attribution(tmp_path,
                                                                 monkeypatch):
    """An unparseable diff header clears attribution instead of inheriting it,
    and the unscanned file is reported rather than silently dropped."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    names = ["src/app.py", 'src/we"ird.py']
    monkeypatch.setattr(aegis, "run_git", stub_git(QUOTED_PATCH, names))
    monkeypatch.setattr(aegis, "MAX_REDIFF_FILES", 0)  # no per-file fallback

    files, added, gaps, reason = aegis.collect_diff({})
    assert reason == "" and files == names
    # the secret line must not be pinned on app.py, whose header parsed fine
    assert added == [("src/app.py", "def app():")]
    assert gaps == ['src/we"ird.py']


def test_the_per_file_fallback_recovers_a_quoted_name(tmp_path, monkeypatch):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    names = ["src/app.py", 'src/we"ird.py']

    base = stub_git(QUOTED_PATCH, names)

    def fake(*args):  # the per-file re-diff returns just that file's hunk
        if args and args[-1] == 'src/we"ird.py':
            return 0, '--- a\n+++ b\n@@ -0,0 +1 @@\n+password = "hunter2"\n'
        return base(*args)

    monkeypatch.setattr(aegis, "run_git", fake)
    _files, added, gaps, _reason = aegis.collect_diff({})
    assert ('src/we"ird.py', 'password = "hunter2"') in added
    assert gaps == []


def test_added_content_starting_with_two_pluses_is_scanned(tmp_path, monkeypatch):
    """A content line beginning ``++`` is not Git's ``+++ path`` header."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    patch = (
        "diff --git a/src/app.py b/src/app.py\n"
        "--- a/src/app.py\n+++ b/src/app.py\n@@ -0,0 +1 @@\n"
        "+++literal-added-content\n"
    )
    monkeypatch.setattr(aegis, "run_git", stub_git(patch, ["src/app.py"]))

    _files, added, gaps, reason = aegis.collect_diff({})
    assert reason == "" and gaps == []
    assert added == [("src/app.py", "++literal-added-content")]


def test_unscanned_files_surface_as_warnings(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n')
    monkeypatch.setattr(aegis, "collect_diff",
                        lambda _cfg, _rev="": (["src/a.py"], [], ["src/a.py"], ""))
    out = run_check(aegis, capsys)
    gap = [line for line in lines_for(out, "secret-in-diff")
           if "added lines not scanned" in line]
    # WARN, not NOTE: a promoted secret-in-diff must catch an unscanned file
    assert gap and gap[0].startswith("WARN")


def test_promoted_secret_in_diff_fails_strict_on_an_unscanned_file(tmp_path,
                                                                   monkeypatch,
                                                                   capsys):
    """The end-to-end guarantee: a team that promotes secret-in-diff gets a
    failing gate when part of the diff could not be inspected."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n\n'
          '[check]\nstrict_promote = ["secret-in-diff"]\n')
    monkeypatch.setattr(aegis, "collect_diff",
                        lambda _cfg, _rev="": (["src/a.py"], [], ["src/a.py"], ""))

    capsys.readouterr()
    assert aegis.main(["check", "--strict"]) == 1
    out = capsys.readouterr().out
    assert "strict: exit 1 (0 error(s), 1 promoted warning(s))" in out

    # and the same repo without the promotion stays advisory
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n')
    assert aegis.main(["check", "--strict"]) == 0


def test_ignored_unscanned_file_does_not_fail_promoted_secret_check(
        tmp_path, monkeypatch, capsys):
    """Ignored paths are excluded from secret matches and scan-gap warnings."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n\n'
          '[check]\nignore = ["vendor/"]\n'
          'strict_promote = ["secret-in-diff"]\n')
    monkeypatch.setattr(
        aegis, "collect_diff",
        lambda _cfg, _rev="": (["vendor/blob.bin"], [], ["vendor/blob.bin"], ""),
    )

    capsys.readouterr()
    assert aegis.main(["check", "--strict"]) == 0
    assert "added lines not scanned" not in capsys.readouterr().out


# TESTS - stricter artifact validation


def test_req_parse_fires_on_bad_status_schema_and_id_format(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write(agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml",
          req_toml("REQ-FUNC-1111", status="activ"))
    write(agentic / "requirements" / "functional" / "REQ-FUNC-XYZ.toml",
          req_toml("REQ-FUNC-XYZ", status="draft"))
    out = run_check(aegis, capsys)
    hits = lines_for(out, "req-parse")
    assert any("status 'activ'" in line for line in hits)
    assert any("id does not match" in line for line in hits)


def test_escaping_paths_are_flagged_not_crashing(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", status="draft",
              paths='["../outside.py", "C:/abs/x.py"]',
              spec="../../etc/passwd")
    out = run_check(aegis, capsys)
    assert sum("escapes" in line for line in lines_for(out, "stale-paths")) == 2
    assert any("../../etc/passwd" in line for line in lines_for(out, "spec-missing"))


def test_req_parse_fires_on_boolean_schema_and_non_string_fields(nogit_repo,
                                                                 capsys):
    agentic, aegis = nogit_repo
    write(agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml",
          'schema = true\nid = "REQ-FUNC-1111"\ntitle = ["a", "list"]\n'
          'status = "draft"\nrequirement = "One behavior."\n'
          'verification = "Run it."\naffected_paths = []\nlinked_tests = []\n')
    out = run_check(aegis, capsys)
    hits = lines_for(out, "req-parse")
    assert any("schema must be the integer 1" in line for line in hits)
    assert any("title must be a string" in line for line in hits)


def test_journal_heading_must_match_filename(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    text = write_task(agentic, "TASK-cccc").read_text(encoding="utf-8")
    (agentic / "tasks" / "TASK-cccc.md").write_text(
        text.replace("TASK-cccc", "TASK-dddd"), encoding="utf-8")
    out = run_check(aegis, capsys)
    assert any("heading id TASK-dddd does not match" in line
               for line in lines_for(out, "journal-header"))


@needs_git
def test_secret_in_a_unicode_named_tracked_file_is_attributed(tmp_path,
                                                              capsys):
    _agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "src" / "uü.py", 'password = "hunter2"\n')
    git(tmp_path, "add", "-A")  # tracked: found via the patch, not ls-files
    out = run_check(aegis, capsys)
    assert any("uü.py" in line or "secret" in line
               for line in lines_for(out, "secret-in-diff"))


def test_unknown_journal_stage_warns(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_task(agentic, "TASK-aaaa", stage="polishing")
    out = run_check(aegis, capsys)
    assert any("unknown stage 'polishing'" in line
               for line in lines_for(out, "journal-header"))


def test_wrongly_typed_config_tables_do_not_crash(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write(agentic / "aegis.toml",
          'schema = 1\ncommands = "oops"\nlayout = 7\ncheck = "no"\n')
    out = run_check(aegis, capsys)  # exit 0 asserted inside run_check
    assert "summary:" in out


@pytest.mark.parametrize("body,expected,settings", [
    ('enabled = "yes"\nmax_fix_cycles = 2', "enabled should be bool", (False, 2)),
    ('enabled = true\nmax_fix_cycles = true', "max_fix_cycles should be int", (True, 0)),
    ('enabled = true\nmax_fix_cycles = 6', "max_fix_cycles should be 0 through 5", (True, 0)),
    ('enabled = true\nmax_fix_cycles = -1', "max_fix_cycles should be 0 through 5", (True, 0)),
])
def test_invalid_review_values_warn_and_fail_safe(nogit_repo, capsys, body, expected,
                                                   settings):
    """REQ-FUNC-9514e017: invalid policy is visible and grants no fix cycles."""
    agentic, aegis = nogit_repo
    write(agentic / "aegis.toml", f"schema = 1\n\n[review]\n{body}\n")
    cfg = aegis.load_config()
    assert aegis.review_settings(cfg) == settings
    assert any(expected in line for line in lines_for(run_check(aegis, capsys), "config"))


def review_config(agentic: Path, enabled: bool = True, cycles: int = 2) -> None:
    """@brief Write one valid explicit-review policy for advisory-check tests."""
    write(agentic / "aegis.toml",
          f"schema = 1\n\n[review]\nenabled = {'true' if enabled else 'false'}\n"
          f"max_fix_cycles = {cycles}\n")


def append_review_record(path: Path, *, current: str, spec: str, quality: str,
                         round_: str) -> None:
    """@brief Append one bound Stage report with review fields."""
    write(path, path.read_text(encoding="utf-8") + f"""

## Stage report

stage: validate
result: completed
current: {current}
changed: candidate
evidence: tests passed
issues:
next: deliver
needs_user: no
spec_compliance: {spec}
implementation_quality: {quality}
review_round: {round_}
""")


def test_check_warns_when_review_round_exceeds_configured_bound(nogit_repo, capsys):
    """REQ-FUNC-cbff6478: durable round state respects workspace policy."""
    agentic, aegis = nogit_repo
    review_config(agentic, cycles=1)
    path = write_task(agentic, "TASK-aa11", stage="validate")
    append_review_record(path, current="validate", spec="changes_required",
                         quality="approved", round_="3")
    assert any("review_round 3 exceeds configured total 2" in line
               for line in lines_for(run_check(aegis, capsys), "review-state"))


def test_check_warns_when_enabled_review_has_partial_verdicts(nogit_repo, capsys):
    """REQ-FUNC-9514e017: incomplete review evidence stays visible."""
    agentic, aegis = nogit_repo
    review_config(agentic)
    path = write_task(agentic, "TASK-aa11", stage="validate")
    append_review_record(path, current="validate", spec="approved", quality="", round_="1")
    assert any("enabled review has incomplete verdict evidence" in line
               for line in lines_for(run_check(aegis, capsys), "review-state"))


def test_check_warns_when_enabled_review_uses_disabled_verdicts(nogit_repo, capsys):
    """REQ-FUNC-9514e017: disabled markers are valid only when review is off."""
    agentic, aegis = nogit_repo
    review_config(agentic)
    path = write_task(agentic, "TASK-aa11", stage="validate")
    append_review_record(path, current="validate", spec="disabled",
                         quality="disabled", round_="1")
    assert any("enabled review has incomplete verdict evidence" in line
               for line in lines_for(run_check(aegis, capsys), "review-state"))


def test_check_warns_when_deliver_has_unapproved_current_verdicts(nogit_repo, capsys):
    """REQ-FUNC-9514e017: known failed review cannot read as deliverable."""
    agentic, aegis = nogit_repo
    review_config(agentic)
    path = write_task(agentic, "TASK-aa11", stage="deliver")
    append_review_record(path, current="deliver", spec="approved",
                         quality="changes_required", round_="2")
    assert any("deliver requires two current approved verdicts" in line
               for line in lines_for(run_check(aegis, capsys), "review-state"))


def test_check_accepts_disabled_verdict_pair_when_review_is_off(nogit_repo, capsys):
    """REQ-FUNC-9514e017: disabled explicit review adds no review-state warning."""
    agentic, aegis = nogit_repo
    review_config(agentic, enabled=False)
    path = write_task(agentic, "TASK-aa11", stage="deliver")
    append_review_record(path, current="deliver", spec="disabled",
                         quality="disabled", round_="")
    assert not lines_for(run_check(aegis, capsys), "review-state")


@pytest.mark.parametrize("stage", ["frame", "build", "done"])
def test_enabled_review_does_not_require_verdicts_outside_validation(
        nogit_repo, capsys, stage):
    """REQ-FUNC-9514e017: review policy is not retroactive or premature."""
    agentic, aegis = nogit_repo
    review_config(agentic)
    write_task(agentic, "TASK-aa11", stage=stage)
    assert not lines_for(run_check(aegis, capsys), "review-state")


# TESTS - check 19: manual-verification


#: requirement id code -> the folder that id must live in.
MANUAL_FOLDERS = {"FUNC": "functional", "UX": "ux", "NFR": "nfr"}


def manual_req(agentic, rid: str, verification: str):
    """@brief An active requirement with no linked tests and a chosen wording."""
    body = req_toml(rid).replace('verification = "Run the linked test."',
                                 f'verification = "{verification}"')
    folder = MANUAL_FOLDERS[rid.split("-")[1]]
    return write(agentic / "requirements" / folder / f"{rid}.toml", body)


def test_a_declared_manual_method_replaces_the_missing_test_warning(nogit_repo,
                                                                    capsys):
    agentic, aegis = nogit_repo
    manual_req(agentic, "REQ-UX-1111",
               "Manual: install on a clean machine and read the first screen.")
    out = run_check(aegis, capsys)
    assert not lines_for(out, "no-linked-tests")
    notes = lines_for(out, "manual-verification")
    assert len(notes) == 1
    assert notes[0].startswith("NOTE") and "by hand: install" in notes[0]


def test_inspection_is_accepted_as_a_manual_method_too(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    manual_req(agentic, "REQ-NFR-1111", "Inspection: read the generated licence.")
    out = run_check(aegis, capsys)
    assert not lines_for(out, "no-linked-tests")
    assert len(lines_for(out, "manual-verification")) == 1


def test_a_bare_prefix_naming_no_method_stays_a_missing_test_warning(nogit_repo,
                                                                     capsys):
    """The escape hatch has to state a method; the word alone buys nothing."""
    agentic, aegis = nogit_repo
    manual_req(agentic, "REQ-FUNC-1111", "Manual:   ")
    out = run_check(aegis, capsys)
    assert len(lines_for(out, "no-linked-tests")) == 1
    assert not lines_for(out, "manual-verification")


def test_a_manual_method_mid_sentence_does_not_count(nogit_repo, capsys):
    """Only the declared prefix counts - prose that mentions it does not."""
    agentic, aegis = nogit_repo
    manual_req(agentic, "REQ-FUNC-1111", "We do this Manual: check by eye.")
    out = run_check(aegis, capsys)
    assert len(lines_for(out, "no-linked-tests")) == 1
    assert not lines_for(out, "manual-verification")


def test_a_manual_requirement_cannot_fail_strict_even_when_promoted(nogit_repo,
                                                                    capsys):
    """A NOTE is unpromotable by construction - that is the whole guarantee."""
    agentic, aegis = nogit_repo
    write(agentic / "aegis.toml",
          'schema = 1\n\n[check]\n'
          'strict_promote = ["no-linked-tests", "manual-verification"]\n')
    manual_req(agentic, "REQ-UX-1111", "Manual: watch the animation once.")
    capsys.readouterr()
    assert aegis.main(["check", "--strict"]) == 0


def test_manual_method_is_ignored_once_tests_are_linked(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-1111", tests='["tests/test_app.py::test_app"]')
    write(agentic.parent / "tests" / "test_app.py", "def test_app():\n    pass\n")
    out = run_check(aegis, capsys)
    assert not lines_for(out, "manual-verification")
    assert not lines_for(out, "no-linked-tests")


# TESTS - check 20: stage-zone


@needs_git
def test_stage_zone_fires_on_source_edited_during_a_documentation_stage(tmp_path,
                                                                        capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write_task(agentic, "TASK-aa11", stage="specify")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    zone = lines_for(run_check(aegis, capsys), "stage-zone")
    assert len(zone) == 1
    assert "src/app.py" in zone[0] and "stage 'specify'" in zone[0]
    assert "write zone is .agentic/" in zone[0]


@needs_git
def test_stage_zone_is_silent_in_build_which_has_no_zone(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write_task(agentic, "TASK-aa11", stage="build")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    assert not lines_for(run_check(aegis, capsys), "stage-zone")


@needs_git
def test_adoption_components_may_write_tests_but_not_source(tmp_path, capsys):
    """Characterizing an untested behavior is adoption; changing it is not."""
    agentic, aegis = make_git_repo(tmp_path)
    write_task(agentic, "TASK-ad01", stage="components")
    write(tmp_path / "tests" / "test_app.py", "def test_app():\n    assert 1\n")
    assert not lines_for(run_check(aegis, capsys), "stage-zone")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    zone = lines_for(run_check(aegis, capsys), "stage-zone")
    assert len(zone) == 1 and "src/app.py" in zone[0]
    assert "write zone is .agentic/, tests" in zone[0]


@needs_git
def test_stage_zone_ignores_a_journal_recorded_on_another_branch(tmp_path,
                                                                 capsys):
    """The diff belongs to this branch; another branch's journal cannot judge it."""
    agentic, aegis = make_git_repo(tmp_path)
    write(agentic / "tasks" / "TASK-aa11.md",
          "# TASK-aa11 — a task\n\nstage: specify\ntype: feature\npath: full\n"
          "requirements:\nbranch: some-other-branch\nopened: 2026-08-02\n\n"
          "## Done checklist (current stage)\n\n- [x] done\n\n"
          "## Log\n\n- 2026-08-02 frame: opened\n")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    assert not lines_for(run_check(aegis, capsys), "stage-zone")


@needs_git
def test_detached_head_needs_an_explicit_task_for_stage_zone(tmp_path, capsys):
    """Without a branch identity, unrelated journals must not judge the diff."""
    agentic, aegis = make_git_repo(tmp_path)
    write_task(agentic, "TASK-aa11", stage="specify")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    git(tmp_path, "checkout", "--detach")

    unscoped = lines_for(run_check(aegis, capsys), "stage-zone")
    assert len(unscoped) == 1
    assert unscoped[0].startswith("NOTE")
    assert "use --task on detached HEAD" in unscoped[0]

    scoped = lines_for(run_check(aegis, capsys, "--task", "TASK-aa11"),
                       "stage-zone")
    assert len(scoped) == 1
    assert scoped[0].startswith("WARN") and "src/app.py" in scoped[0]


@needs_git
def test_a_file_outside_the_layout_is_check_12_not_check_17(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write_task(agentic, "TASK-aa11", stage="specify")
    write(tmp_path / "notes.txt", "scratch\n")
    out = run_check(aegis, capsys)
    assert not lines_for(out, "stage-zone")
    assert any("notes.txt" in line for line in lines_for(out, "outside-layout"))


@needs_git
def test_a_zones_entry_widens_a_stage(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n\n'
          '[zones]\nspecify = ["source"]\n')
    write_task(agentic, "TASK-aa11", stage="specify")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    assert not lines_for(run_check(aegis, capsys), "stage-zone")


def test_an_unknown_zone_name_is_reported_as_a_config_warning(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write(agentic / "aegis.toml",
          'schema = 1\n\n[zones]\nspecify = ["sources"]\n')
    out = run_check(aegis, capsys)
    assert any("unknown zone 'sources'" in line for line in lines_for(out, "config"))


# TESTS - degraded modes


def test_missing_git_degrades_every_diff_check_to_a_note(nogit_repo, capsys):
    _agentic, aegis = nogit_repo
    out = run_check(aegis, capsys)
    notes = [line for line in out.splitlines() if line.startswith("NOTE")]
    assert len(notes) == 6
    assert all("(diff) - skipped: git executable not found" in line for line in notes)
    assert "result: NOTE" in out


def test_not_a_repository_degrades_with_its_own_reason(tmp_path, monkeypatch,
                                                       capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: (128, ""))
    out = run_check(aegis, capsys)
    assert sum("skipped: not a git repository" in line
               for line in out.splitlines()) == 6


@needs_git
def test_no_merge_base_degrades_with_a_note(tmp_path, capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    git(tmp_path, "init")  # a repo with no commit has no default branch yet
    out = run_check(aegis, capsys)
    assert sum("skipped: no default branch" in line for line in out.splitlines()) == 6


# TESTS - ignore globs and --task scoping


def test_ignore_globs_exclude_files_from_every_check(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n\n'
          '[check]\nsecret_patterns_extra = []\n'
          'ignore = ["**/fixtures/**", "**/TASK-eeee.md"]\n')
    write(agentic / "requirements" / "functional" / "fixtures" / "broken.toml",
          "not [ toml\n")
    write(agentic / "tasks" / "TASK-eeee.md", "garbage journal\n")
    out = run_check(aegis, capsys)
    assert "summary: errors=0" in out


@needs_git
def test_task_scoping_narrows_coverage_and_drift(tmp_path, capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write_req(agentic, "REQ-FUNC-aaa1", paths='["src/app.py"]',
              tests='["tests/test_app.py"]')
    write_req(agentic, "REQ-FUNC-bbb1", paths='["src/other.py"]',
              tests='["tests/test_app.py"]')
    write_task(agentic, "TASK-aa11", stage="build", reqs="REQ-FUNC-aaa1")
    write_task(agentic, "TASK-bb22", stage="build", reqs="REQ-FUNC-bbb1")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "wip")
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")

    out = run_check(aegis, capsys)  # unscoped: drift only for the b task
    drift = lines_for(out, "scope-drift")
    assert len(drift) == 1 and "TASK-bb22" in drift[0]
    assert not lines_for(out, "uncovered-source")

    out = run_check(aegis, capsys, "--task", "TASK-aa11")
    assert not lines_for(out, "scope-drift")
    assert not lines_for(out, "uncovered-source")

    out = run_check(aegis, capsys, "--task", "TASK-bb22")
    assert len(lines_for(out, "scope-drift")) == 1
    # only the scoped task's requirements count as coverage now
    assert any("src/app.py" in line for line in lines_for(out, "uncovered-source"))


def test_task_scoping_rejects_an_unknown_task(nogit_repo, capsys):
    _agentic, aegis = nogit_repo
    capsys.readouterr()
    assert aegis.main(["check", "--task", "TASK-dead"]) == 1
    assert capsys.readouterr().err.startswith("error: no such task journal")


# TESTS - output contract


def test_golden_output_is_stable(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-aaaa")
    write_task(agentic, "TASK-bbbb", stage="deliver", reqs="REQ-FUNC-aaaa",
               checklist="- [ ] ship it")
    assert run_check(aegis, capsys) == (
        "NOTE   outside-layout  (diff) - skipped: git executable not found\n"
        "NOTE   scope-drift  (diff) - skipped: git executable not found\n"
        "NOTE   secret-in-diff  (diff) - skipped: git executable not found\n"
        "NOTE   source-no-test-changes  (diff) - skipped: git executable not found\n"
        "NOTE   stage-zone  (diff) - skipped: git executable not found\n"
        "NOTE   uncovered-source  (diff) - skipped: git executable not found\n"
        "WARN   no-linked-tests  .agentic/requirements/functional/REQ-FUNC-aaaa.toml"
        " - empty linked_tests\n"
        "WARN   unticked-deliver  .agentic/tasks/TASK-bbbb.md"
        " - 1 unticked item(s) in deliver\n"
        "summary: errors=0 warnings=2 notes=6\n"
        "result: WARN\n"
    )


def test_output_lines_are_ascii_and_at_most_100_columns(nogit_repo, capsys):
    agentic, aegis = nogit_repo
    write_req(agentic, "REQ-FUNC-aaaa",
              prose="A very long prose mentioning #123 " + "and ABC-999 " * 8)
    write(agentic / "requirements" / "functional" / "REQ-FUNC-cccc.toml",
          "definitely not toml [ = \n")
    out = run_check(aegis, capsys)
    for line in out.splitlines():
        assert len(line) <= 100
        assert line.isascii()


def test_clean_repo_reports_ok(tmp_path, monkeypatch, capsys):
    """A repo with no artifacts and a working diff has zero findings."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg, _rev="": ([], [], [], ""))
    out = run_check(aegis, capsys)
    assert out == "summary: errors=0 warnings=0 notes=0\nresult: ok\n"


def test_help_lists_every_slug_and_the_diff_basis(nogit_repo, capsys):
    _agentic, aegis = nogit_repo
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        aegis.main(["check", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for slug, _desc in aegis.CHECKS:
        assert slug in out
    assert len(aegis.CHECKS) == 21
    # the count the help announces must be the count it lists
    assert f"the {len(aegis.CHECKS)} checks" in out
    assert "merge-base" in out and "origin/HEAD" in out
    assert "`timeout`" in out and "`workdir`" in out
