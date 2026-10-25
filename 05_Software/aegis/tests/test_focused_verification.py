#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file test_focused_verification.py
@brief Verify portable selection, non-executing previews, and lean scaffolds.
@details Uses isolated Git fixtures and argument-recording commands; no real
         project test runner or host-specific selector grammar is assumed.
"""

import json
import re

import pytest
import tomllib
from test_check import make_git_repo, make_repo, needs_git, write, write_req, write_task
from test_cli_core import snapshot
from test_run_report import PY, cmd_exit, config, run


@needs_git
@pytest.mark.parametrize("suffix", ["renders a result", "case[hello world]",
                                   "résultat attendu", "name; echo injected",
                                   "$(echo injected)", 'name"quoted'])
def test_selector_suffix_is_discarded_and_file_is_run_once(tmp_path, capsys, suffix):
    """@brief Unsupported names never reach the shell, even beside exact refs."""
    agentic, aegis = make_git_repo(tmp_path)
    write(tmp_path / "argdump.py",
          "import json,pathlib,sys\n"
          "pathlib.Path('args.json').write_text(json.dumps(sys.argv[1:]))\n")
    config(agentic, f"test = {cmd_exit(9)}\n"
           f"test_impacted = '{PY} argdump.py {{tests}}'")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests=json.dumps([f"tests/app.test.ts::{suffix}",
                                "tests/app.test.ts::exact_name"]))
    write(tmp_path / "src/app.py", "changed\n")
    code, output = run(aegis, capsys, "test", "--impacted", "--no-fallback")
    assert code == 0
    assert "reduced to file granularity" in output
    assert json.loads((tmp_path / "args.json").read_text()) == ["tests/app.test.ts"]


@needs_git
@pytest.mark.parametrize("reference", ["tests/bad name.py::a name",
                                       "tests/bad;name.py::a name",
                                       "../../outside.py::a name",
                                       "--collect-only::a name"])
def test_invalid_paths_cannot_be_rescued_by_discarding_selectors(
        tmp_path, monkeypatch, capsys, reference):
    """@brief Path hygiene and containment remain prerequisites to execution."""
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic, f"test = {cmd_exit(0)}\ntest_impacted = 'unused {{tests}}'")
    write_req(agentic, "REQ-FUNC-1111", paths='["src/app.py"]',
              tests=json.dumps([reference]))
    write(tmp_path / "src/app.py", "changed\n")
    monkeypatch.setattr(aegis, "run_command", lambda *_a, **_k: pytest.fail("ran tests"))
    assert aegis.main(["test", "--impacted", "--no-fallback"]) == 1
    assert "no command run" in capsys.readouterr().err


@pytest.mark.parametrize("arguments", [[], ["--impacted"]])
def test_dry_run_does_not_execute_or_append_evidence(tmp_path, monkeypatch,
                                                   capsys, arguments):
    """@brief A preview names its working directory and cannot become test proof."""
    agentic, aegis = make_repo(tmp_path)
    config(agentic, f"test = {cmd_exit(9)}", extra='')
    write_task(agentic, "TASK-ab12")
    before = snapshot(tmp_path)
    monkeypatch.setattr(aegis, "run_command", lambda *_a, **_k: pytest.fail("ran tests"))
    code, output = run(aegis, capsys, "test", *arguments, "--dry-run",
                       "--task", "TASK-ab12")
    assert code == 0
    assert "workdir=" in output and "no verification result recorded" in output
    assert "would run" in output if arguments else "would run" not in output
    assert snapshot(tmp_path) == before


def test_missing_impacted_configuration_refuses_without_writing(tmp_path,
                                                              monkeypatch, capsys):
    """@brief Refusing a fallback does not run or log a successful test."""
    agentic, aegis = make_repo(tmp_path)
    config(agentic, f"test = {cmd_exit(0)}")
    write_task(agentic, "TASK-ab12")
    before = snapshot(tmp_path)
    monkeypatch.setattr(aegis, "run_command", lambda *_a, **_k: pytest.fail("ran tests"))
    assert aegis.main(["test", "--impacted", "--no-fallback", "--task", "TASK-ab12"]) == 1
    assert "no command run" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
    assert aegis.main(["test", "--no-fallback"]) == 1


@needs_git
def test_selected_preview_rebases_files_without_running(tmp_path, monkeypatch, capsys):
    """@brief Preview uses the execution selector path and configured workdir."""
    agentic, aegis = make_git_repo(tmp_path)
    config(agentic, f"test = {cmd_exit(9)}\n"
           "test_impacted = 'unused {tests}'\nworkdir = 'app'",
           source='["app/src/"]')
    write_req(agentic, "REQ-FUNC-1111", paths='["app/src/entry.py"]',
              tests='["app/tests/entry_test.go::accepts an input"]')
    write(tmp_path / "app/src/entry.py", "changed\n")
    before = snapshot(tmp_path)
    monkeypatch.setattr(aegis, "run_command", lambda *_a, **_k: pytest.fail("ran tests"))
    code, output = run(aegis, capsys, "test", "--impacted", "--base", "HEAD",
                       "--dry-run", "--no-fallback")
    assert code == 0
    assert "$ unused tests/entry_test.go\n" in output
    assert f"workdir={tmp_path / 'app'}" in output
    assert snapshot(tmp_path) == before


def test_requirement_scaffold_omits_notes_without_changing_toml_data(tmp_path, capsys):
    """@brief Marked guidance and the payload license disappear; literal text survives."""
    agentic, aegis = make_repo(tmp_path)
    template = agentic / "templates/requirement.toml"
    text = template.read_text(encoding="utf-8").replace(
        "State exactly one behavior here.", "# A literal requirement line.\nA behavior.")
    template.write_text(text, encoding="utf-8")
    assert aegis.main(["req", "functional", "Portable behavior"]) == 0
    result = (tmp_path / capsys.readouterr().out.strip()).read_text(encoding="utf-8")
    assert "AEGIS:TEMPLATE" not in result and "Recommended shape" not in result
    assert "SPDX-License-Identifier" not in result and result.startswith("schema = 1\n")
    assert "# A literal requirement line." in result
    original, generated = tomllib.loads(text), tomllib.loads(result)
    for key in set(original) - {"id", "title", "created", "updated"}:
        assert generated[key] == original[key]
    assert template.read_text(encoding="utf-8") == text


def test_task_scaffold_omits_authoring_notes_but_retains_durable_sections(tmp_path,
                                                                       capsys):
    """@brief Reduced scaffolds keep resume, review and decision sections, not the license."""
    agentic, aegis = make_repo(tmp_path)
    assert aegis.main(["task", "Portable work"]) == 0
    result = (tmp_path / capsys.readouterr().out.strip()).read_text(encoding="utf-8")
    template = (agentic / "templates/task.md").read_text(encoding="utf-8")
    assert "AEGIS:TEMPLATE" not in result and "Task journal: one per task" not in result
    assert "SPDX-License-Identifier" not in result and result.startswith("# TASK-")
    assert re.findall(r"^## .*", result, re.MULTILINE) == re.findall(r"^## .*", template, re.MULTILINE)
    assert set(aegis.parse_state(result)) == set(aegis.parse_state(template)) == set(aegis.STATE_FIELDS)
    assert not any(aegis.parse_state(template).values())
    assert aegis.parse_state(result)["status"] == "working"
