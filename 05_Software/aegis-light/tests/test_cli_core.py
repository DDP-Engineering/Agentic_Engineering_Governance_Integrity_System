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
@file test_cli_core.py
@brief P2 tests for the AEGIS Light CLI: ids, header parsing, init, scaffolding.
@details Every test copies `template/.agentic` into a tmp_path repo and imports
         `aegis.py` from that copy, so the module's `__file__`-derived paths
         point at the throwaway tree and the real payload is never written to.
@details No network and no git: `git_branch` is monkeypatched wherever a
         generated branch value matters.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import itertools
import shutil
from pathlib import Path

import pytest

# CONSTANTS

PAYLOAD = Path(__file__).resolve().parents[1] / "template" / ".agentic"
_COUNTER = itertools.count()

# HELPERS


def make_repo(tmp_path: Path) -> tuple[Path, object]:
    """@brief Copy the payload into tmp_path and import that copy's aegis.py."""
    agentic = tmp_path / ".agentic"
    shutil.copytree(PAYLOAD, agentic)
    spec = importlib.util.spec_from_file_location(
        f"aegis_under_test_{next(_COUNTER)}", agentic / "aegis.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.ROOT == tmp_path.resolve()
    return agentic, module


def snapshot(root: Path) -> dict[str, bytes]:
    """@brief Every file under root as {posix relative path: exact bytes}."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# TESTS - id generation


def test_new_id_is_eight_lowercase_hex_chars(tmp_path):
    _, aegis = make_repo(tmp_path)
    for _ in range(50):
        value = aegis.new_id(set())
        assert len(value) == 8
        assert all(char in "0123456789abcdef" for char in value)


def test_new_id_retries_on_collision(tmp_path, monkeypatch):
    _, aegis = make_repo(tmp_path)
    draws = iter(["aaaa", "aaaa", "bbbb"])
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: next(draws))
    assert aegis.new_id({"aaaa"}) == "bbbb"


def test_new_id_gives_up_with_a_user_error(tmp_path, monkeypatch):
    _, aegis = make_repo(tmp_path)
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: "aaaa")
    with pytest.raises(aegis.UserError):
        aegis.new_id({"aaaa"})


def test_ids_are_collision_checked_against_existing_files(tmp_path, monkeypatch):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    (agentic / "tasks" / "TASK-abcd.md").write_text("# TASK-abcd — taken\n")
    (agentic / "requirements" / "security").mkdir(parents=True)
    (agentic / "requirements" / "security" / "REQ-SEC-abcd.toml").write_text("")

    assert "abcd" in aegis.taken_ids("tasks", "TASK-*.md")
    assert "abcd" in aegis.taken_ids("requirements", "**/REQ-*.toml")
    draws = iter(["abcd", "0f0f", "abcd", "1e1e"])
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: next(draws))
    monkeypatch.setattr(aegis, "git_branch", lambda: "main")

    assert aegis.main(["task", "second"]) == 0
    assert (agentic / "tasks" / "TASK-0f0f.md").is_file()
    assert aegis.main(["req", "functional", "second"]) == 0
    assert (agentic / "requirements" / "functional" / "REQ-FUNC-1e1e.toml").is_file()


# TESTS - journal header parsing


def test_header_parser_round_trip_against_the_template(tmp_path):
    agentic, aegis = make_repo(tmp_path)
    data = aegis.parse_journal((agentic / "templates" / "task.md").read_text("utf-8"))

    assert data["id"] == "TASK-0000"
    assert data["title"] == "<one-line title>"
    assert data["header"] == {
        "stage": "frame",
        "type": "feature",
        "path": "full",
        "requirements": "",
        "branch": "<branch>",
        "opened": "2026-01-01",
    }
    assert data["checklist"] == [
        (False, 'copy the "Done when" list from the current step file here')
    ]
    assert len(data["log"]) == 1
    assert data["log"][0].startswith("2026-01-01 frame:")


def test_header_parser_tolerates_a_journal_without_a_header(tmp_path):
    _, aegis = make_repo(tmp_path)
    assert aegis.parse_journal("no title here\n")["id"] == ""
    data = aegis.parse_journal("# TASK-1234 — t\n\n## Log\n- a\n- b\n")
    assert data["header"] == {} and data["log"] == ["a", "b"]


# TESTS - init


def test_init_creates_folders_config_and_pointers(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0

    for name in aegis.DATA_DIRS:
        assert (agentic / name).is_dir()
    config = agentic / "aegis.toml"
    assert config.is_file()
    assert aegis.load_config()["schema"] == aegis.SCHEMA
    for name in aegis.POINTER_FILES:
        text = (tmp_path / name).read_text(encoding="utf-8")
        assert aegis.MARK_BEGIN in text and aegis.MARK_END in text
        assert ".agentic/AGENTS.md" in text
        assert "aegis.py status" in text
    assert "created" in capsys.readouterr().out


def test_init_writes_lf_only_and_no_bom(tmp_path):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    for path in [agentic / "aegis.toml"] + [tmp_path / n for n in aegis.POINTER_FILES]:
        raw = path.read_bytes()
        assert b"\r\n" not in raw
        assert not raw.startswith(b"\xef\xbb\xbf")


def test_init_is_a_byte_for_byte_no_op_on_the_second_run(tmp_path):
    _, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    before = snapshot(tmp_path)
    assert aegis.main(["init"]) == 0
    assert snapshot(tmp_path) == before


def test_init_never_overwrites_an_existing_aegis_toml(tmp_path):
    agentic, aegis = make_repo(tmp_path)
    config = agentic / "aegis.toml"
    mine = 'schema = 1\n\n[commands]\ntest = "pytest -x tests/mine"\n'
    config.write_text(mine, encoding="utf-8", newline="\n")

    assert aegis.main(["init"]) == 0
    assert config.read_text(encoding="utf-8") == mine


def test_init_appends_to_pointer_files_without_clobbering(tmp_path):
    _, aegis = make_repo(tmp_path)
    prior = "# AGENTS.md\n\nOur own house rules that must survive.\n"
    (tmp_path / "AGENTS.md").write_text(prior, encoding="utf-8", newline="\n")

    assert aegis.main(["init"]) == 0
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert text.startswith(prior)
    assert aegis.MARK_BEGIN in text

    aegis.main(["init"])
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == text


def test_init_leaves_user_data_folders_untouched(tmp_path):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    kept = agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml"
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text("schema = 1\n", encoding="utf-8", newline="\n")
    journal = agentic / "tasks" / "TASK-2222.md"
    journal.write_text("# TASK-2222 — mine\n", encoding="utf-8", newline="\n")
    before = snapshot(agentic / "requirements") | snapshot(agentic / "tasks")

    assert aegis.main(["init"]) == 0
    assert snapshot(agentic / "requirements") | snapshot(agentic / "tasks") == before


def test_init_reports_an_incomplete_payload(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    (agentic / "AGENTS.md").unlink()
    assert aegis.main(["init"]) == 1
    assert capsys.readouterr().err.startswith("error: payload looks incomplete")


# TESTS - req


def test_req_writes_the_category_folder_and_id(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()
    assert aegis.main(["req", "security", "Reject unsigned payloads"]) == 0

    printed = capsys.readouterr().out.strip()
    path = tmp_path / printed
    assert path.parent == agentic / "requirements" / "security"
    assert "/" in printed and "\\" not in printed

    import tomllib

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data["id"] == path.stem
    assert data["id"].startswith("REQ-SEC-")
    assert data["title"] == "Reject unsigned payloads"
    assert data["created"] == data["updated"]
    assert data["schema"] == aegis.SCHEMA
    assert b"\r\n" not in path.read_bytes()


@pytest.mark.parametrize(
    "category,folder,code",
    [
        ("functional", "functional", "FUNC"),
        ("ux", "ux", "UX"),
        ("non_functional", "nfr", "NFR"),
        ("security", "security", "SEC"),
        ("data_privacy", "data", "DATA"),
        ("platform", "platform", "PLAT"),
        ("release", "reliability", "REL"),
        ("testing", "test", "TEST"),
    ],
)
def test_req_covers_all_eight_categories(tmp_path, capsys, category, folder, code):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()
    assert aegis.main(["req", category, "A behavior"]) == 0
    path = tmp_path / capsys.readouterr().out.strip()
    assert path.parent == agentic / "requirements" / folder
    assert path.stem.startswith(f"REQ-{code}-")


def test_req_rejects_an_unknown_category(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()
    assert aegis.main(["req", "performance", "Be fast"]) == 1

    err = capsys.readouterr().err
    assert err.startswith("error: unknown category 'performance'")
    assert len(err.splitlines()) == 1
    assert not list((agentic / "requirements").rglob("*.toml"))


def test_req_reports_a_missing_template(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    (agentic / "templates" / "requirement.toml").unlink()
    assert aegis.main(["req", "ux", "A behavior"]) == 1
    assert "missing template" in capsys.readouterr().err


def test_req_quotes_a_title_containing_quotes(tmp_path, capsys):
    _, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()
    assert aegis.main(["req", "ux", 'Show "n of m" in the footer']) == 0

    import tomllib

    path = tmp_path / capsys.readouterr().out.strip()
    loaded = tomllib.loads(path.read_text("utf-8"))
    assert loaded["title"] == 'Show "n of m" in the footer'


@pytest.mark.parametrize("argv", [
    ["task", "new", "Legacy task form"],
    ["req", "new", "functional", "Legacy requirement form"],
])
def test_nested_new_forms_are_not_accepted(tmp_path, argv):
    """The public CLI has one flat creation form, without compatibility parsing."""
    _, aegis = make_repo(tmp_path)
    with pytest.raises(SystemExit):
        aegis.build_parser().parse_args(argv)


# TESTS - task and status round trip


def test_task_then_status_round_trip(tmp_path, capsys, monkeypatch):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "git_branch", lambda: "feature/m3u-export")
    capsys.readouterr()

    assert aegis.main(["task", "Export playlist as M3U", "--type", "fix"]) == 0
    printed = capsys.readouterr().out.strip()
    path = tmp_path / printed
    assert path.parent == agentic / "tasks"
    assert "\\" not in printed

    data = aegis.parse_journal(path.read_text(encoding="utf-8"))
    assert data["id"] == path.stem
    assert data["title"] == "Export playlist as M3U"
    assert data["header"]["stage"] == "frame"
    assert data["header"]["type"] == "fix"
    assert data["header"]["branch"] == "feature/m3u-export"
    assert data["header"]["opened"] == aegis.today()
    assert data["log"][0].startswith(aegis.today())
    assert b"\r\n" not in path.read_bytes()

    assert aegis.main(["status"]) == 0
    listing = capsys.readouterr().out
    assert data["id"] in listing
    assert "frame" in listing and "fix" in listing
    assert "Export playlist as M3U" in listing

    assert aegis.main(["status", data["id"]]) == 0
    detail = capsys.readouterr().out
    assert "branch: feature/m3u-export" in detail
    assert "checklist: 0/1 done" in detail
    assert "log (last 1 of 1)" in detail


def test_status_accepts_a_bare_id_and_shows_only_the_last_five_log_lines(tmp_path,
                                                                        capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    logs = "\n".join(f"- 2026-08-0{n} build: line {n}" for n in range(1, 8))
    (agentic / "tasks" / "TASK-9f9f.md").write_text(
        f"# TASK-9f9f — Seven log lines\n\nstage: build\ntype: feature\n\n"
        f"## Done checklist (current stage)\n\n- [x] one\n- [ ] two\n\n"
        f"## Log\n\n{logs}\n",
        encoding="utf-8",
        newline="\n",
    )
    capsys.readouterr()

    assert aegis.main(["status", "9f9f"]) == 0
    out = capsys.readouterr().out
    assert "log (last 5 of 7)" in out
    assert "line 1" not in out and "line 3" in out and "line 7" in out
    assert "checklist: 1/2 done" in out


def test_status_resolves_validate_and_deliver_step_files(tmp_path, capsys):
    """REQ-FUNC-24ea4f73: both post-build stages are resumable."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()

    for suffix, stage, step in (
        ("aaaa", "validate", "5_validate.md"),
        ("bbbb", "deliver", "6_deliver.md"),
    ):
        (agentic / "tasks" / f"TASK-{suffix}.md").write_text(
            f"# TASK-{suffix} - stage\n\nstage: {stage}\ntype: change\n"
            "path: full\nrequirements:\nbranch: feature\nopened: 2026-08-12\n\n"
            "## Done checklist (current stage)\n\n- [ ] continue\n\n## Log\n\n"
            "- 2026-08-12 frame: opened\n",
            encoding="utf-8",
            newline="\n",
        )
        assert aegis.main(["status", f"TASK-{suffix}"]) == 0
        out = capsys.readouterr().out
        assert f"stage: {stage}" in out
        assert f"open .agentic/steps/{step}" in out


def test_status_on_an_empty_repo_and_on_a_missing_task(tmp_path, capsys):
    _, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()

    assert aegis.main(["status"]) == 0
    empty = capsys.readouterr().out
    assert "no task journals yet" in empty
    assert 'aegis.py task "<title>"' in empty
    assert "task new" not in empty
    assert aegis.main(["status", "TASK-dead"]) == 1
    assert capsys.readouterr().err.startswith("error: no such task journal")


def test_task_keeps_the_template_structure(tmp_path, capsys, monkeypatch):
    """The only differences from the template are the substituted values."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "git_branch", lambda: "main")
    capsys.readouterr()

    aegis.main(["task", "Keep the shape"])
    generated = (tmp_path / capsys.readouterr().out.strip()).read_text("utf-8")
    original = (agentic / "templates" / "task.md").read_text("utf-8")

    assert "Keep the shape\n\nstage: frame\n" in generated
    changed = [
        (a, b)
        for a, b in zip(original.split("\n"), generated.split("\n"))
        if a != b
    ]
    assert len(original.split("\n")) == len(generated.split("\n"))
    assert len(changed) == 4  # title, type (unchanged text), branch, opened, log
    assert {b.split(":")[0] for _a, b in changed} >= {"branch", "opened"}


# TESTS - git branch lookup


def test_git_branch_falls_back_when_git_is_absent(tmp_path, monkeypatch):
    _, aegis = make_repo(tmp_path)

    def boom(*_args, **_kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(aegis.subprocess, "run", boom)
    assert aegis.git_branch() == "unknown"


def test_git_branch_asks_git_for_the_current_branch(tmp_path, monkeypatch):
    """`branch --show-current` also answers before the first commit exists."""
    _, aegis = make_repo(tmp_path)
    seen: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = "feature/m3u-export\n"

    def fake_run(argv, **kwargs):
        seen.append(argv)
        assert kwargs["cwd"] == str(aegis.ROOT)
        return Result()

    monkeypatch.setattr(aegis.subprocess, "run", fake_run)
    assert aegis.git_branch() == "feature/m3u-export"
    assert seen == [["git", "branch", "--show-current"]]


def test_git_branch_falls_back_on_empty_output_or_failure(tmp_path, monkeypatch):
    _, aegis = make_repo(tmp_path)

    class Result:
        def __init__(self, code, out):
            self.returncode, self.stdout = code, out

    monkeypatch.setattr(aegis.subprocess, "run", lambda *a, **k: Result(0, "\n"))
    assert aegis.git_branch() == "unknown"
    monkeypatch.setattr(aegis.subprocess, "run", lambda *a, **k: Result(128, "x"))
    assert aegis.git_branch() == "unknown"
