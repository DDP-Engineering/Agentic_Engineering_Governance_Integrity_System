#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_cli_core.py
@brief P2 tests for the AEGIS CLI: ids, header parsing, init, scaffolding.
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
import os
import re
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


def config_sections(text: str) -> dict[str, list[str]]:
    """@brief The generated aegis.toml split into {table name: its lines}."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = sections.setdefault(stripped[1:-1], [])
        elif current is not None:
            current.append(line)
    return sections


def declares(lines: list[str], key: str) -> bool:
    """@brief True when the table assigns `key`, live or commented out."""
    pattern = re.compile(rf"^\s*(?:#\s*)?{re.escape(key)}\s*=")
    return any(pattern.match(line) for line in lines)


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
            "interaction": "checkpoint",
            "requirements": "",
        "parent": "",
        "branch": "<branch>",
        "base": "",
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


def test_legacy_journal_without_new_sections_still_parses(tmp_path):
    """REQ-FUNC-7ea14fe4: old journals have empty additive durable state."""
    _, aegis = make_repo(tmp_path)
    text = "# TASK-1234 - legacy\n\nstage: build\ntype: feature\n\n## Log\n\n- old\n"
    data = aegis.parse_journal(text)

    assert data["header"].get("parent", "") == ""
    assert aegis.parse_rulings(text) == ([], [])
    assert aegis.parse_handoff(text) == {}


def test_new_task_template_has_parent_rulings_handoff_and_review_fields(tmp_path):
    """REQ-FUNC-b8f0efc5: the canonical task scaffold carries additive fields."""
    agentic, aegis = make_repo(tmp_path)
    text = (agentic / "templates" / "task.md").read_text(encoding="utf-8")
    data = aegis.parse_journal(text)

    assert data["header"]["parent"] == ""
    assert text.index("## Rulings") < text.index("## Handoff") < text.index("## Stage report")
    assert aegis.parse_rulings(text) == ([], [])
    assert aegis.parse_handoff(text) == {
        "current": "", "status": "", "next": "", "must_read": "", "blockers": ""
    }
    report = aegis.parse_stage_report(text)
    assert list(report)[-3:] == [
        "spec_compliance", "implementation_quality", "review_round"
    ]


def test_rulings_parse_in_order_and_supersede_without_mutating_history(tmp_path):
    """REQ-FUNC-7ea14fe4: later rulings supersede but never rewrite history."""
    _, aegis = make_repo(tmp_path)
    text = """# TASK-1234 - rulings

stage: build

## Rulings

- RULING-001 | date=2026-08-31 | decision=First | reason=Initial | source=user | supersedes=none
- RULING-002 | date=2026-08-31 | decision=Second | reason=Refined | source=technical | supersedes=RULING-001
- RULING-003 | date=2026-08-31 | decision=Third | reason=Independent | source=requirement | supersedes=none
"""
    records, errors = aegis.parse_rulings(text)

    assert errors == []
    assert [record["id"] for record in records] == [
        "RULING-001", "RULING-002", "RULING-003"
    ]
    assert [record["id"] for record in aegis.active_rulings(records)] == [
        "RULING-002", "RULING-003"
    ]
    assert records[0]["decision"] == "First"


def test_malformed_ruling_is_reported_without_hiding_valid_records(tmp_path):
    """REQ-FUNC-7ea14fe4: bounded diagnostics preserve valid ruling records."""
    _, aegis = make_repo(tmp_path)
    text = """# TASK-1234 - rulings

stage: build

## Rulings

- RULING-001 | date=2026-08-31 | decision=Keep | reason=Works | source=user | supersedes=none
- RULING-XYZ | decision={long_value}
""".format(long_value="x" * 10000)
    records, errors = aegis.parse_rulings(text)

    assert [record["id"] for record in records] == ["RULING-001"]
    assert len(errors) == 1 and len(errors[0]) < 240


def test_forward_supersession_does_not_hide_a_later_valid_ruling(tmp_path):
    """REQ-FUNC-7ea14fe4: only a valid earlier ID can be superseded."""
    _agentic, aegis = make_repo(tmp_path)
    text = """## Rulings

- RULING-001 | date=2026-08-31 | decision=wait | reason=future | source=technical | supersedes=RULING-002
- RULING-002 | date=2026-08-31 | decision=ship | reason=current | source=user | supersedes=none
"""
    records, _errors = aegis.parse_rulings(text)
    assert [record["id"] for record in aegis.active_rulings(records)] == [
        "RULING-001", "RULING-002"]


def test_ruling_parser_bounds_malformed_record_diagnostics(tmp_path):
    """REQ-FUNC-7ea14fe4: malformed ruling output stays bounded."""
    _agentic, aegis = make_repo(tmp_path)
    text = "## Rulings\n\n" + "\n".join(f"invalid {n}" for n in range(100))
    _records, errors = aegis.parse_rulings(text)
    assert len(errors) == aegis.RULING_DIAGNOSTIC_LIMIT
    assert errors[-1] == "...[81 ruling diagnostics omitted; read journal]"


def test_handoff_requires_known_fields_and_accepts_blank_scaffold(tmp_path):
    """REQ-FUNC-7ea14fe4: handoff is one strict replaceable field record."""
    _, aegis = make_repo(tmp_path)
    blank = """# TASK-1234 - handoff

stage: frame

## Handoff

current:
status:
next:
must_read:
blockers:
"""
    assert aegis.parse_handoff(blank) == {
        "current": "", "status": "", "next": "", "must_read": "", "blockers": ""
    }
    with pytest.raises(aegis.UserError, match="unknown Handoff field"):
        aegis.parse_handoff(blank + "surprise: value\n")


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
    for path in [agentic / "aegis.toml", tmp_path / aegis.IGNORE_FILE] + \
            [tmp_path / n for n in aegis.POINTER_FILES]:
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


def test_generated_config_documents_every_validated_key(tmp_path):
    """Every key the CLI reads is named in the config init writes."""
    agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0

    sections = config_sections((agentic / "aegis.toml").read_text(encoding="utf-8"))
    for table, keys in aegis.CONFIG_SHAPE.items():
        assert table in sections, f"[{table}] is missing from the default config"
        for key in keys:
            assert declares(sections[table], key), (
                f"[{table}] {key} is read by the CLI but absent from the "
                "default config, live or commented"
            )


def test_init_scaffolds_current_context_without_authoring_notes(tmp_path):
    """Project-owned context starts as UTF-8 structure, not invented facts."""
    agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0
    for name in aegis.CONTEXT_FILES:
        path = agentic / "context" / name
        assert path.read_text(encoding="utf-8") == aegis.scaffold_template(name)
        assert "AEGIS:TEMPLATE" not in path.read_text(encoding="utf-8")
        assert b"\r\n" not in path.read_bytes()
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("existing", ["project.md", "environment.md"])
@pytest.mark.parametrize("mine", [b"", b"# My context\r\n\r\nCurrent fact: caf\xc3\xa9\r\n"])
def test_init_preserves_each_context_file_when_adding_its_sibling(tmp_path, existing, mine):
    """Upgrade scaffolding preserves even empty or CRLF project-owned files."""
    agentic, aegis = make_repo(tmp_path)
    context = agentic / "context"
    context.mkdir()
    (context / existing).write_bytes(mine)
    sibling = next(name for name in aegis.CONTEXT_FILES if name != existing)
    assert aegis.main(["init"]) == 0
    assert (context / existing).read_bytes() == mine
    assert (context / sibling).is_file()
    before = snapshot(tmp_path)
    assert aegis.main(["init"]) == 0
    assert snapshot(tmp_path) == before


def test_init_preserves_concurrently_created_context(tmp_path, monkeypatch):
    """A file appearing after the absence check keeps its owner's bytes."""
    agentic, aegis = make_repo(tmp_path)
    original = aegis.scaffold_template

    def concurrent_owner(name):
        content = original(name)
        (agentic / "context" / name).write_bytes(b"Owner's current facts\n")
        return content

    monkeypatch.setattr(aegis, "scaffold_template", concurrent_owner)
    assert aegis.main(["init"]) == 0
    for name in aegis.CONTEXT_FILES:
        assert (agentic / "context" / name).read_bytes() == b"Owner's current facts\n"


def test_init_writes_review_disabled_with_two_fix_cycles(tmp_path):
    """REQ-FUNC-9514e017: fresh workspaces preserve behavior with review off."""
    _agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0
    assert aegis.load_config()["review"] == {"enabled": False, "max_fix_cycles": 2}


def test_init_writes_records_commit_fingerprints_false(tmp_path):
    """Fresh workspaces keep anchor/evolution sidecars out of git."""
    _agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0
    assert aegis.load_config()["records"] == {"commit_fingerprints": False}


def test_commit_fingerprints_setting_fails_safe(tmp_path):
    """Only an exact TOML Boolean can turn sidecar commits on."""
    _, aegis = make_repo(tmp_path)
    assert aegis.commit_fingerprints({"schema": 1}) is False
    assert aegis.commit_fingerprints({"records": {"commit_fingerprints": True}}) is True
    assert aegis.commit_fingerprints({"records": {"commit_fingerprints": "true"}}) is False


def test_init_creates_gitignore_with_the_managed_fingerprint_block(tmp_path, capsys):
    _, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert text == "\n".join((aegis.IGNORE_MARK_BEGIN, *aegis.FINGERPRINT_PATTERNS,
                              aegis.IGNORE_MARK_END)) + "\n"
    assert ".gitignore       created (anchor/evolution sidecars stay local)" in \
        capsys.readouterr().out


def test_init_appends_ignore_block_and_keeps_crlf_without_clobbering(tmp_path):
    _, aegis = make_repo(tmp_path)
    prior = "node_modules/\r\n*.log"
    (tmp_path / ".gitignore").write_bytes(prior.encode("utf-8"))

    assert aegis.main(["init"]) == 0
    raw = (tmp_path / ".gitignore").read_bytes()
    assert raw.startswith(b"node_modules/\r\n*.log\r\n")
    assert b"\r\n.agentic/tasks/*.anchor.json\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")

    aegis.main(["init"])
    assert (tmp_path / ".gitignore").read_bytes() == raw


def test_init_refreshes_a_stale_ignore_block_in_place(tmp_path):
    _, aegis = make_repo(tmp_path)
    stale = (f"build/\n{aegis.IGNORE_MARK_BEGIN}\nold-pattern\n{aegis.IGNORE_MARK_END}\n"
             "dist/\n")
    (tmp_path / ".gitignore").write_text(stale, encoding="utf-8", newline="\n")
    assert aegis.main(["init"]) == 0
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert text.startswith("build/\n" + aegis.IGNORE_MARK_BEGIN)
    assert text.endswith(aegis.IGNORE_MARK_END + "\ndist/\n")
    assert "old-pattern" not in text and text.count(aegis.IGNORE_MARK_BEGIN) == 1


def test_init_removes_the_ignore_block_when_sidecars_are_committed(tmp_path, capsys):
    agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0
    (tmp_path / ".gitignore").write_text(
        "mine/\n" + (tmp_path / ".gitignore").read_text(encoding="utf-8") + "*.tmp\n",
        encoding="utf-8", newline="\n")
    write_config = (agentic / "aegis.toml").read_text(encoding="utf-8").replace(
        "commit_fingerprints = false", "commit_fingerprints = true")
    (agentic / "aegis.toml").write_text(write_config, encoding="utf-8", newline="\n")

    capsys.readouterr()
    assert aegis.main(["init"]) == 0
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "mine/\n*.tmp\n"
    assert ".gitignore       removed" in capsys.readouterr().out

    (tmp_path / ".gitignore").unlink()
    capsys.readouterr()
    assert aegis.main(["init"]) == 0
    assert not (tmp_path / ".gitignore").exists()
    assert ".gitignore       absent" in capsys.readouterr().out


def test_init_writes_autopilot_disabled(tmp_path):
    """REQ-FUNC-d60b322b: fresh workspaces stop at every stage by default."""
    _agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["init"]) == 0
    assert aegis.load_config()["interaction"] == {"autopilot": False}


def test_missing_interaction_table_is_backward_compatible(tmp_path):
    """REQ-FUNC-d60b322b: legacy configuration fails safe to checkpoints."""
    _, aegis = make_repo(tmp_path)
    assert aegis.autopilot_enabled({"schema": 1}) is False
    assert aegis.interaction_mode({"schema": 1}) == "checkpoint"


def test_interaction_settings_accept_only_a_toml_boolean(tmp_path):
    """REQ-FUNC-d60b322b: invalid autopilot values fail safe."""
    _, aegis = make_repo(tmp_path)
    assert aegis.autopilot_enabled({"interaction": {"autopilot": True}}) is True
    assert aegis.interaction_mode({"interaction": {"autopilot": True}}) == "autopilot"
    assert aegis.autopilot_enabled({"interaction": {"autopilot": "true"}}) is False


def test_missing_review_table_is_backward_compatible(tmp_path):
    """REQ-FUNC-9514e017: legacy config means disabled with the default bound."""
    _, aegis = make_repo(tmp_path)
    assert aegis.review_settings({"schema": 1}) == (False, 2)


def test_review_settings_accept_exact_boolean_and_bounded_integer(tmp_path):
    """REQ-FUNC-9514e017: valid policy values retain their exact meaning."""
    _, aegis = make_repo(tmp_path)
    assert aegis.review_settings({"review": {"enabled": True, "max_fix_cycles": 0}}) == \
        (True, 0)
    assert aegis.review_settings({"review": {"enabled": False, "max_fix_cycles": 5}}) == \
        (False, 5)
    assert aegis.review_settings({"review": {"enabled": True, "max_fix_cycles": 255}}) == \
        (True, 255)
    assert aegis.review_settings({"review": {"enabled": True, "max_fix_cycles": 256}}) == \
        (True, 0)


def test_review_settings_reject_boolean_as_integer(tmp_path):
    """REQ-FUNC-9514e017: TOML Boolean never masquerades as an integer bound."""
    _, aegis = make_repo(tmp_path)
    assert aegis.review_settings({"review": {"enabled": True, "max_fix_cycles": True}}) == \
        (True, 0)


def test_init_preserves_existing_workspace_config(tmp_path):
    """REQ-FUNC-9514e017: init never injects review policy into owned config."""
    agentic, aegis = make_repo(tmp_path)
    path = agentic / "aegis.toml"
    original = "schema = 1\n\n[review]\nenabled = true\nmax_fix_cycles = 4\n"
    path.write_text(original, encoding="utf-8")
    assert aegis.main(["init"]) == 0
    assert path.read_text(encoding="utf-8") == original


def test_task_records_the_configured_interaction_mode(tmp_path, capsys, monkeypatch):
    """REQ-FUNC-d60b322b: resolved task mode survives later sessions."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    path = agentic / "aegis.toml"
    text = path.read_text(encoding="utf-8").replace("autopilot = false",
                                                    "autopilot = true")
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(aegis, "git_branch", lambda: "master")
    capsys.readouterr()

    assert aegis.main(["task", "Remember interaction mode"]) == 0
    journal = tmp_path / capsys.readouterr().out.strip()
    assert aegis.parse_journal(journal.read_text("utf-8"))["header"]["interaction"] == \
        "autopilot"


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


def test_init_migrates_legacy_pointer_markers_without_duplication(tmp_path):
    _agentic, aegis = make_repo(tmp_path)
    legacy_begin, legacy_end = aegis.LEGACY_MARK_PAIRS[0]
    prior = ("# AGENTS.md\n\nRepository rules before.\n\n"
             f"{legacy_begin}\n\nold digest\n{legacy_end}\n\n"
             "Repository rules after.\n")
    (tmp_path / "AGENTS.md").write_text(prior, encoding="utf-8", newline="\n")

    assert aegis.main(["init"]) == 0
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert text.count(aegis.MARK_BEGIN) == 1
    assert legacy_begin not in text and legacy_end not in text
    assert "Repository rules before." in text
    assert "Repository rules after." in text


def test_init_collapses_legacy_and_current_duplicate_blocks(tmp_path):
    _agentic, aegis = make_repo(tmp_path)
    legacy_begin, legacy_end = aegis.LEGACY_MARK_PAIRS[0]
    current = f"{aegis.MARK_BEGIN}\n\nnew digest\n{aegis.MARK_END}\n"
    text = (f"# AGENTS.md\n\n{legacy_begin}\nold digest\n{legacy_end}\n\n"
            f"Repository-owned middle.\n\n{current}")
    (tmp_path / "AGENTS.md").write_text(text, encoding="utf-8", newline="\n")

    assert aegis.main(["init"]) == 0
    migrated = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert migrated.count(aegis.MARK_BEGIN) == 1
    assert legacy_begin not in migrated and legacy_end not in migrated
    assert "Repository-owned middle." in migrated


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


def test_init_reports_when_git_is_unavailable(tmp_path, monkeypatch, capsys):
    _agentic, aegis = make_repo(tmp_path)
    monkeypatch.setattr(aegis, "run_git", lambda *_args: None)

    assert aegis.main(["init"]) == 0
    out = capsys.readouterr().out
    assert "git              unavailable" in out
    assert "diff, impacted, anchor, and evolution evidence disabled" in out


def test_init_offers_opt_in_git_initialization(tmp_path, monkeypatch, capsys):
    _agentic, aegis = make_repo(tmp_path)
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args == ("--version",):
            return 0, "git version 2.50.0"
        if args == ("init",):
            return 0, "Initialized empty Git repository"
        return 128, ""

    monkeypatch.setattr(aegis, "run_git", fake_git)
    assert aegis.main(["init"]) == 0
    assert "init --git" in capsys.readouterr().out
    assert ("init",) not in calls

    assert aegis.main(["init", "--git"]) == 0
    assert ("init",) in calls
    assert "repository initialized" in capsys.readouterr().out


def test_init_git_option_fails_cleanly_without_git(tmp_path, monkeypatch, capsys):
    _agentic, aegis = make_repo(tmp_path)
    monkeypatch.setattr(aegis, "run_git", lambda *_args: None)

    assert aegis.main(["init", "--git"]) == 1
    assert "git is not installed or unavailable" in capsys.readouterr().err


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


@pytest.mark.parametrize(
    "abbreviation,folder,code",
    [
        ("func", "functional", "FUNC"),
        ("sec", "security", "SEC"),
        ("plat", "platform", "PLAT"),
        ("rel", "reliability", "REL"),
    ],
)
def test_req_accepts_the_identifier_abbreviations(tmp_path, capsys,
                                                  abbreviation, folder, code):
    """REQ-PLAT-2e23ac26: the abbreviation the id shows is a valid category."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    capsys.readouterr()
    assert aegis.main(["req", abbreviation, "A behavior"]) == 0
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


# TESTS - component catalogue


def test_components_lists_titles_paths_and_stem_fallback_without_writes(
        tmp_path, capsys, monkeypatch):
    """REQ-FUNC-8ec7a0c7: catalogue rows are deterministic and read-only."""
    agentic, aegis = make_repo(tmp_path)
    knowledge = agentic / "knowledge"
    knowledge.mkdir(exist_ok=True)
    (knowledge / "zeta.md").write_text(
        "# Zeta component\n\n## Routing\n", encoding="utf-8", newline="\n")
    (knowledge / "alpha.md").write_text(
        "<!-- orientation -->\n\n# Alpha component\n", encoding="utf-8", newline="\n")
    (knowledge / "untitled.md").write_text(
        "## Routing\n\nNo level-one title.\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(
        aegis,
        "knowledge_components",
        lambda *_args, **_kwargs: pytest.fail(
            "components must not parse component requirement claims"),
    )
    before = snapshot(tmp_path)

    assert aegis.main(["components"]) == 0
    assert capsys.readouterr().out == (
        "Alpha component\t.agentic/knowledge/alpha.md\n"
        "untitled\t.agentic/knowledge/untitled.md\n"
        "Zeta component\t.agentic/knowledge/zeta.md\n"
    )
    assert snapshot(tmp_path) == before


def test_components_normalizes_and_bounds_titles(tmp_path, capsys):
    """REQ-FUNC-8ec7a0c7: titles remain one short printable output field."""
    agentic, aegis = make_repo(tmp_path)
    knowledge = agentic / "knowledge"
    knowledge.mkdir(exist_ok=True)
    raw_title = "Alpha\t\x1b[31m" + ("x" * 100)
    (knowledge / "alpha.md").write_text(
        f"# {raw_title}\n", encoding="utf-8", newline="\n")

    assert aegis.main(["components"]) == 0
    title, path = capsys.readouterr().out.rstrip("\n").split("\t")
    assert path == ".agentic/knowledge/alpha.md"
    assert title.startswith("Alpha [31m")
    assert title.endswith("…")
    assert len(title) == aegis.COMPONENT_TITLE_WIDTH
    assert all(char.isprintable() for char in title)


def test_components_preserves_internal_symlink_lexical_path(
        tmp_path, capsys, monkeypatch):
    """REQ-FUNC-8ec7a0c7: an in-catalogue link keeps its catalogue path."""
    repo = tmp_path / "repo"
    agentic, aegis = make_repo(repo)
    knowledge = agentic / "knowledge"
    knowledge.mkdir(exist_ok=True)
    target = knowledge / "target.md"
    target.write_text("# Target\n", encoding="utf-8", newline="\n")
    alias = knowledge / "alias.md"
    try:
        alias.symlink_to(target)
    except OSError:
        alias.write_text("# Target\n", encoding="utf-8", newline="\n")
        original_resolve = aegis.Path.resolve

        def resolve(path, *args, **kwargs):
            return target if path == alias else original_resolve(
                path, *args, **kwargs)

        monkeypatch.setattr(aegis.Path, "resolve", resolve)

    assert aegis.main(["components"]) == 0
    assert capsys.readouterr().out == (
        "Target\t.agentic/knowledge/alias.md\n"
        "Target\t.agentic/knowledge/target.md\n"
    )


def test_components_rejects_symlinks_escaping_the_catalogue(
        tmp_path, capsys, monkeypatch):
    """REQ-FUNC-8ec7a0c7: catalogue links cannot make external files pages."""
    repo = tmp_path / "repo"
    agentic, aegis = make_repo(repo)
    knowledge = agentic / "knowledge"
    knowledge.mkdir(exist_ok=True)
    external = tmp_path / "external.md"
    external.write_text("# External secret\n", encoding="utf-8", newline="\n")
    escape = knowledge / "escape.md"
    try:
        escape.symlink_to(external)
    except OSError:
        escape.write_text("# External secret\n", encoding="utf-8", newline="\n")
        original_resolve = aegis.Path.resolve

        def resolve(path, *args, **kwargs):
            return external if path == escape else original_resolve(
                path, *args, **kwargs)

        monkeypatch.setattr(aegis.Path, "resolve", resolve)
    before = snapshot(repo)

    assert aegis.main(["components"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "error: .agentic/knowledge/escape.md resolves outside "
        ".agentic/knowledge\n"
    )
    assert snapshot(repo) == before


def test_components_bounds_symlink_resolution_loops(tmp_path, capsys,
                                                      monkeypatch):
    """REQ-FUNC-8ec7a0c7: resolution loops use the one-line error path."""
    agentic, aegis = make_repo(tmp_path)
    knowledge = agentic / "knowledge"
    knowledge.mkdir(exist_ok=True)
    loop = knowledge / "loop.md"
    loop.write_text("# Loop\n", encoding="utf-8", newline="\n")
    original_resolve = aegis.Path.resolve

    def resolve(path, *args, **kwargs):
        if path == loop:
            raise RuntimeError("symlink loop")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(aegis.Path, "resolve", resolve)

    assert aegis.main(["components"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "error: .agentic/knowledge/loop.md cannot be resolved: symlink loop\n"
    )


def test_components_rejects_nonprintable_catalogue_paths(tmp_path, capsys,
                                                          monkeypatch):
    """REQ-FUNC-8ec7a0c7: unsafe filenames cannot corrupt catalogue rows."""
    agentic, aegis = make_repo(tmp_path)
    unsafe = agentic / "knowledge" / "bad\tname.md"
    monkeypatch.setattr(
        aegis, "knowledge_page_texts", lambda: [(unsafe, "## No title\n")])

    assert aegis.main(["components"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "error: component knowledge page path contains non-printable "
        "characters\n"
    )
    assert aegis.component_title("\x07", "\x1b") == "component"


def test_components_reports_an_empty_catalogue_without_writes(tmp_path, capsys):
    """REQ-FUNC-8ec7a0c7: no pages is a successful, explicit empty result."""
    agentic, aegis = make_repo(tmp_path)
    (agentic / "knowledge").mkdir(exist_ok=True)
    before = snapshot(tmp_path)

    assert aegis.main(["components"]) == 0
    assert capsys.readouterr().out == "no component knowledge pages\n"
    assert snapshot(tmp_path) == before


def test_components_rejects_unreadable_utf8_without_partial_output(tmp_path,
                                                                    capsys):
    """REQ-FUNC-8ec7a0c7: an unreadable page uses the bounded CLI error path."""
    agentic, aegis = make_repo(tmp_path)
    knowledge = agentic / "knowledge"
    knowledge.mkdir(exist_ok=True)
    (knowledge / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (knowledge / "broken.md").write_bytes(b"# Broken\n\xff")
    before = snapshot(tmp_path)

    assert aegis.main(["components"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(
        "error: .agentic/knowledge/broken.md is not valid UTF-8:")
    assert snapshot(tmp_path) == before


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


def test_task_records_the_commit_it_started_from(tmp_path, capsys, monkeypatch):
    """REQ-DATA-71fcf08e: every later measurement needs an exact start."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "git_head", lambda: "0123456789abcdef0123")
    capsys.readouterr()

    assert aegis.main(["task", "Measurable work"]) == 0
    path = tmp_path / capsys.readouterr().out.strip()
    data = aegis.parse_journal(path.read_text(encoding="utf-8"))
    assert data["header"]["base"] == "0123456789abcdef0123"


def test_task_records_no_commit_without_history(tmp_path, capsys, monkeypatch):
    """REQ-DATA-71fcf08e: no history is recorded as no commit, not a guess."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "git_head", lambda: "")
    capsys.readouterr()

    assert aegis.main(["task", "Unrepeatable work"]) == 0
    path = tmp_path / capsys.readouterr().out.strip()
    data = aegis.parse_journal(path.read_text(encoding="utf-8"))
    assert data["header"]["base"] == ""


def test_task_keeps_the_template_structure(tmp_path, capsys, monkeypatch):
    """The durable template structure survives substitutions and note removal."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "git_branch", lambda: "main")
    capsys.readouterr()

    aegis.main(["task", "Keep the shape"])
    generated = (tmp_path / capsys.readouterr().out.strip()).read_text("utf-8")
    original = aegis.scaffold_template("task.md")

    assert "Keep the shape\n\nstage: frame\n" in generated
    changed = [
        (a, b)
        for a, b in zip(original.split("\n"), generated.split("\n"))
        if a != b
    ]
    assert len(original.split("\n")) == len(generated.split("\n"))
    assert len(changed) == 4  # title, type (unchanged text), branch, opened, log
    assert {b.split(":")[0] for _a, b in changed} >= {"branch", "opened"}


def test_task_without_parent_remains_a_top_level_task(tmp_path, capsys, monkeypatch):
    """REQ-FUNC-3bc8597c: ordinary task creation keeps a blank parent."""
    _agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "git_branch", lambda: "feature/top")
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: "aa11")
    capsys.readouterr()

    assert aegis.main(["task", "Top level"]) == 0
    path = tmp_path / capsys.readouterr().out.strip()
    assert aegis.parse_journal(path.read_text(encoding="utf-8"))["header"]["parent"] == ""


def test_task_with_parent_records_only_the_child_side_link(tmp_path, capsys, monkeypatch):
    """REQ-FUNC-3bc8597c: child creation never mutates its parent journal."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    draws = iter(["aa11", "bb22"])
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: next(draws))
    monkeypatch.setattr(aegis, "git_branch", lambda: "feature/children")
    capsys.readouterr()
    assert aegis.main(["task", "Parent"]) == 0
    capsys.readouterr()
    parent = agentic / "tasks" / "TASK-aa11.md"
    before = parent.read_bytes()

    assert aegis.main(["task", "Child", "--parent", "aa11"]) == 0
    child = agentic / "tasks" / "TASK-bb22.md"
    assert aegis.parse_journal(child.read_text(encoding="utf-8"))["header"]["parent"] == \
        "TASK-aa11"
    assert parent.read_bytes() == before


def test_task_rejects_unknown_parent(tmp_path, capsys, monkeypatch):
    """REQ-FUNC-3bc8597c: a missing visible parent cannot create a child."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: "bb22")
    capsys.readouterr()

    assert aegis.main(["task", "Child", "--parent", "dead"]) == 1
    assert "no such task journal" in capsys.readouterr().err
    assert not (agentic / "tasks" / "TASK-bb22.md").exists()


def test_task_rejects_a_parent_that_is_itself_a_child(tmp_path, capsys, monkeypatch):
    """REQ-FUNC-3bc8597c: task relationships cannot nest beyond one level."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    parent = (agentic / "templates" / "task.md").read_text(encoding="utf-8")
    parent = parent.replace("TASK-0000", "TASK-aa11").replace(
        "# TASK-aa11 - <one-line title>", "# TASK-aa11 - Parent")
    (agentic / "tasks").mkdir(exist_ok=True)
    (agentic / "tasks" / "TASK-aa11.md").write_text(parent, encoding="utf-8")
    nested = parent.replace("TASK-aa11", "TASK-bb22").replace(
        "# TASK-bb22 - Parent", "# TASK-bb22 - Existing child").replace(
        "parent:", "parent: TASK-aa11", 1)
    (agentic / "tasks" / "TASK-bb22.md").write_text(nested, encoding="utf-8")
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: "cc33")
    capsys.readouterr()

    assert aegis.main(["task", "Nested", "--parent", "TASK-bb22"]) == 1
    assert "already a child" in capsys.readouterr().err
    assert not (agentic / "tasks" / "TASK-cc33.md").exists()


def test_child_keeps_its_own_current_branch_and_base(tmp_path, capsys, monkeypatch):
    """REQ-FUNC-3bc8597c: a child records its own repository context."""
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    parent = (agentic / "templates" / "task.md").read_text(encoding="utf-8")
    parent = parent.replace("TASK-0000", "TASK-aa11").replace(
        "# TASK-aa11 - <one-line title>", "# TASK-aa11 - Parent")
    (agentic / "tasks").mkdir(exist_ok=True)
    (agentic / "tasks" / "TASK-aa11.md").write_text(parent, encoding="utf-8")
    monkeypatch.setattr(aegis.secrets, "token_hex", lambda _n: "bb22")
    monkeypatch.setattr(aegis, "git_branch", lambda: "feature/child")
    monkeypatch.setattr(aegis, "git_head", lambda: "0123456789abcdef")
    capsys.readouterr()

    assert aegis.main(["task", "Child", "--parent", "TASK-aa11"]) == 0
    child = aegis.parse_journal(
        (agentic / "tasks" / "TASK-bb22.md").read_text(encoding="utf-8"))
    assert child["header"]["branch"] == "feature/child"
    assert child["header"]["base"] == "0123456789abcdef"


def test_visible_children_are_sorted_and_ignore_unrelated_tasks(tmp_path):
    """REQ-FUNC-3bc8597c: reverse links expose only sorted visible children."""
    agentic, aegis = make_repo(tmp_path)
    (agentic / "tasks").mkdir(exist_ok=True)
    template = (agentic / "templates" / "task.md").read_text(encoding="utf-8")
    for task_id, parent in (("TASK-cc33", "TASK-aa11"), ("TASK-bb22", "TASK-aa11"),
                            ("TASK-dd44", "TASK-ffff"), ("TASK-aa11", "")):
        text = template.replace("TASK-0000", task_id).replace(
            f"# {task_id} - <one-line title>", f"# {task_id} - Task")
        text = text.replace("parent:", f"parent: {parent}".rstrip(), 1)
        (agentic / "tasks" / f"{task_id}.md").write_text(text, encoding="utf-8")

    children = aegis.visible_children("TASK-aa11")
    assert [data["id"] for _path, data in children] == ["TASK-bb22", "TASK-cc33"]


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
    # Git runs by the absolute path found on PATH outside the repository
    assert seen == [[aegis.system_program("git"), "branch", "--show-current"]]
    assert os.path.isabs(seen[0][0])


def test_git_branch_falls_back_on_empty_output_or_failure(tmp_path, monkeypatch):
    _, aegis = make_repo(tmp_path)

    class Result:
        def __init__(self, code, out):
            self.returncode, self.stdout = code, out

    monkeypatch.setattr(aegis.subprocess, "run", lambda *a, **k: Result(0, "\n"))
    assert aegis.git_branch() == "unknown"
    monkeypatch.setattr(aegis.subprocess, "run", lambda *a, **k: Result(128, "x"))
    assert aegis.git_branch() == "unknown"
