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
             paths: str = "[]", tests: str = "[]", spec: str = "") -> str:
    """@brief A minimal valid requirement body with the six required fields."""
    return (
        "schema = 1\n"
        f'id = "{rid}"\n'
        'title = "A behavior"\n'
        f'status = "{status}"\n'
        f'requirement = """\n{prose}\n"""\n'
        'verification = "Run the linked test."\n'
        f"affected_paths = {paths}\n"
        f"linked_tests = {tests}\n"
        + (f'spec = "{spec}"\n' if spec else "")
    )


def write_req(agentic: Path, rid: str, folder: str = "functional", **kw) -> Path:
    """@brief Write a requirement file named after its id."""
    return write(agentic / "requirements" / folder / f"{rid}.toml",
                 req_toml(rid, **kw))


def write_task(agentic: Path, tid: str, stage: str = "build", reqs: str = "",
               checklist: str = "- [x] done") -> Path:
    """@brief Write a parseable task journal."""
    return write(
        agentic / "tasks" / f"{tid}.md",
        f"# {tid} — a task\n\nstage: {stage}\ntype: feature\npath: full\n"
        f"requirements: {reqs}\nbranch: feature\nopened: 2026-08-02\n\n"
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


def git(repo: Path, *args: str) -> None:
    """@brief Run git with a fixed identity and signing off; fail loudly."""
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=T",
         "-c", "commit.gpgsign=false", *args],
        cwd=str(repo), check=True, capture_output=True, timeout=60,
    )


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
def test_scope_drift_fires_and_is_silent_when_requirement_is_touched(tmp_path,
                                                                     capsys):
    agentic, aegis = make_git_repo(tmp_path)
    write_req(agentic, "REQ-FUNC-1111", paths='["src/other.py"]',
              tests='["tests/test_app.py"]')
    write_task(agentic, "TASK-aaaa", stage="build", reqs="REQ-FUNC-1111")
    git(tmp_path, "add", "-A")           # the artifacts are part of the base,
    git(tmp_path, "commit", "-m", "wip")  # not untracked work-in-progress
    write(tmp_path / "src" / "app.py", "def app():\n    return 2\n")
    out = run_check(aegis, capsys)
    assert any("TASK-aaaa" in line
               and "build diff touches no linked requirement" in line
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


def test_unscanned_files_surface_as_warnings(tmp_path, monkeypatch, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n')
    monkeypatch.setattr(aegis, "collect_diff",
                        lambda _cfg: (["src/a.py"], [], ["src/a.py"], ""))
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
                        lambda _cfg: (["src/a.py"], [], ["src/a.py"], ""))

    capsys.readouterr()
    assert aegis.main(["check", "--strict"]) == 1
    out = capsys.readouterr().out
    assert "strict: exit 1 (0 error(s), 1 promoted warning(s))" in out

    # and the same repo without the promotion stays advisory
    write(agentic / "aegis.toml",
          'schema = 1\n\n[layout]\nsource = ["src/"]\ntests = ["tests/"]\n')
    assert aegis.main(["check", "--strict"]) == 0


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


# TESTS - degraded modes


def test_missing_git_degrades_every_diff_check_to_a_note(nogit_repo, capsys):
    _agentic, aegis = nogit_repo
    out = run_check(aegis, capsys)
    notes = [line for line in out.splitlines() if line.startswith("NOTE")]
    assert len(notes) == 5
    assert all("(diff) - skipped: git executable not found" in line for line in notes)
    assert "result: NOTE" in out


def test_not_a_repository_degrades_with_its_own_reason(tmp_path, monkeypatch,
                                                       capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: (128, ""))
    out = run_check(aegis, capsys)
    assert sum("skipped: not a git repository" in line
               for line in out.splitlines()) == 5


@needs_git
def test_no_merge_base_degrades_with_a_note(tmp_path, capsys):
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    git(tmp_path, "init")  # a repo with no commit has no default branch yet
    out = run_check(aegis, capsys)
    assert sum("skipped: no default branch" in line for line in out.splitlines()) == 5


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
        "NOTE   uncovered-source  (diff) - skipped: git executable not found\n"
        "WARN   no-linked-tests  .agentic/requirements/functional/REQ-FUNC-aaaa.toml"
        " - empty linked_tests\n"
        "WARN   unticked-deliver  .agentic/tasks/TASK-bbbb.md"
        " - 1 unticked item(s) in deliver\n"
        "summary: errors=0 warnings=2 notes=5\n"
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
    monkeypatch.setattr(aegis, "collect_diff", lambda _cfg: ([], [], [], ""))
    out = run_check(aegis, capsys)
    assert out == "summary: errors=0 warnings=0 notes=0\nresult: ok\n"


def test_help_lists_all_fifteen_slugs_and_the_diff_basis(nogit_repo, capsys):
    _agentic, aegis = nogit_repo
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        aegis.main(["check", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for slug, _desc in aegis.CHECKS:
        assert slug in out
    assert len(aegis.CHECKS) == 15
    assert "merge-base" in out and "origin/HEAD" in out
