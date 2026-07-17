#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_adopt_run.py
@brief Command-level offline tests for ``waegis adopt`` (T5.2): the plan §5
       contract before/around the engine run, mirroring the Wizard N parity set.
@details Strictly offline (fake CommandRunner drives the pre-run analysis through
         its filesystem-walk fallback; no prompting reaches a real terminal).
         Covers: TARGET must exist; ``--non-interactive`` failing loudly with
         every missing required key (roots the analysis could not propose, and
         the ``other``-language extras) before the engine or journal starts;
         ``--dry-run`` emitting the plan preview (human + frozen ``--json``)
         while leaving TARGET and the journal untouched; the unknown-answer-key
         warning; a malformed answers file; and an invalid conflict decision.
@author Eng. Dan Dumitru Pasare
@date 2026-07-14
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path

from waegis.commands.adopt import ADOPT_STEP_IDS, run_adopt
from waegis.commands.new import EXIT_FAILURE, EXIT_OK

from _fake_command_runner import FakeCommandRunner

# CONSTANTS

# @brief Roots pinned so the "other"-language required-extras test isolates the
#        conditional requirement (an empty target proposes no roots).
_ROOTS: dict = {"source_roots": ["src"], "test_roots": ["tests"]}


# LOCAL HELPERS


def _existing_target(tmp_path: Path) -> Path:
    """
    @brief      Create an empty existing TARGET directory (adopt requires one).
    @param[in]  tmp_path Pytest tmp fixture.
    @return     The created directory.
    @exception  OSError If the directory cannot be created.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    target.mkdir()
    return target


def _write_answers(path: Path, answers: dict) -> Path:
    """
    @brief      Write a JSON answers file for the test.
    @param[in]  path Destination file path (.json).
    @param[in]  answers Answers mapping to serialize.
    @return     The written path.
    @exception  OSError If the file cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path.write_text(json.dumps(answers), encoding="utf-8")
    return path


# TESTS


def test_target_must_exist(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A non-existent TARGET fails cleanly (adopt is for existing
                repositories).
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the failure is not clean.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    out = io.StringIO()
    code = run_adopt(
        tmp_path / "missing",
        stream=out,
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )
    assert code == 2
    assert "does not exist" in out.getvalue()


def test_non_interactive_missing_roots_fails_before_engine(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``--non-interactive`` on an empty repo (analysis proposes no
                roots) fails naming both unproposable required keys, before any
                engine or journal work.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the failure is late, partial, or silent.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    home = tmp_path / "home"
    out = io.StringIO()
    code = run_adopt(
        _existing_target(tmp_path),
        stream=out,
        non_interactive=True,
        runner=FakeCommandRunner({}),
        home=home,
    )
    assert code == EXIT_FAILURE
    text = out.getvalue()
    assert "source_roots" in text and "test_roots" in text
    assert not (home / "journals").exists()


def test_non_interactive_other_language_requires_extension_answers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      language="other" additionally requires source_extensions and
                test_file_patterns in a non-interactive adopt run.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the conditional requirement is not enforced.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    answers = _write_answers(tmp_path / "answers.json", {**_ROOTS, "language": "other"})
    out = io.StringIO()
    code = run_adopt(
        _existing_target(tmp_path),
        stream=out,
        answers_path=answers,
        non_interactive=True,
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )
    assert code == EXIT_FAILURE
    assert "source_extensions" in out.getvalue()
    assert "test_file_patterns" in out.getvalue()


def test_dry_run_emits_plan_preview_and_touches_nothing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``--dry-run`` renders the Wizard E plan preview (net.proxy
                filtered out - adopt never clones) and leaves the journal
                untouched.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the preview is wrong or a journal appeared.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    home = tmp_path / "home"
    out = io.StringIO()
    code = run_adopt(
        _existing_target(tmp_path),
        stream=out,
        dry_run=True,
        stdin=io.StringIO(""),
        runner=FakeCommandRunner({}),
        home=home,
    )
    assert code == EXIT_OK
    text = out.getvalue()
    assert "WAEGIS plan preview" in text
    assert "repo.validate-existing" in text and "handoff.adoption" in text
    assert "net.proxy" not in text
    assert "dry run: no changes were made." in text
    assert not home.exists()


def test_dry_run_json_is_the_frozen_plan_preview_shape(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``--dry-run --json`` emits exactly one JSON document with the
                frozen plan-preview field names and adopt-mode step ids.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the JSON shape deviates from the contract.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    out = io.StringIO()
    answers = _write_answers(
        tmp_path / "answers.json",
        {**_ROOTS, "language": "python"},
    )
    code = run_adopt(
        _existing_target(tmp_path),
        stream=out,
        answers_path=answers,
        dry_run=True,
        as_json=True,
        stdin=io.StringIO(""),
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )
    assert code == EXIT_OK
    document = json.loads(out.getvalue())
    assert set(document) == {"schema_version", "command", "status", "exit_code", "plan", "result", "messages"}
    assert document["command"] == "adopt"
    plan = document["plan"]
    assert plan["mode"] == "adopt"
    assert plan["dry_run"] is True
    planned_ids = [step["id"] for step in plan["steps"]]
    assert planned_ids == [step_id for step_id in ADOPT_STEP_IDS if step_id != "net.proxy"]
    for step in plan["steps"]:
        assert set(step) == {"id", "title", "why", "phase", "automation", "change_summary"}


def test_unknown_answer_keys_are_warned_not_fatal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      An unrecognized answers key produces a warning naming it, and
                the run proceeds (dry run here exits 0).
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the warning is missing or the run fails.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    answers = _write_answers(tmp_path / "answers.json", {**_ROOTS, "language": "python", "bogus_key": 1})
    out = io.StringIO()
    code = run_adopt(
        _existing_target(tmp_path),
        stream=out,
        answers_path=answers,
        dry_run=True,
        non_interactive=True,
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )
    assert code == EXIT_OK
    assert "bogus_key" in out.getvalue()


def test_malformed_answers_file_fails_cleanly(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      An unsupported answers file exits 1 with the answers-seam error
                message, before any engine work.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the failure is not clean.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    bad = tmp_path / "answers.txt"
    bad.write_text("not = usable", encoding="utf-8")
    out = io.StringIO()
    code = run_adopt(
        _existing_target(tmp_path),
        stream=out,
        answers_path=bad,
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )
    assert code == 2
    assert "answers file" in out.getvalue()


def test_invalid_conflict_decision_fails_cleanly(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      An ``adoption_conflicts`` answer with an unknown decision exits 1
                naming the offending path, before any engine work.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the invalid table is not rejected cleanly.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    answers = _write_answers(tmp_path / "answers.json", {"adoption_conflicts": {"CLAUDE.md": "bogus"}})
    out = io.StringIO()
    code = run_adopt(
        _existing_target(tmp_path),
        stream=out,
        answers_path=answers,
        dry_run=True,
        stdin=io.StringIO(""),
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )
    assert code == 2
    assert "CLAUDE.md" in out.getvalue()


# END OF FILE
