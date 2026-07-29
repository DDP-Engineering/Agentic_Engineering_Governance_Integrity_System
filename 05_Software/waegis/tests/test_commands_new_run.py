#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_new_run.py
@brief Command-level offline tests for ``waegis new`` (T4.3): the plan §5
       contract before/around the engine run.
@details Strictly offline (fake CommandRunner, no prompting reaches a real
         terminal). Covers: ``--non-interactive`` failing loudly with *every*
         missing required key before the engine or journal starts;
         ``--dry-run`` emitting the plan preview while leaving TARGET and the
         journal untouched (human and frozen-``--json`` shapes); the
         unknown-answer-key warning; plan rejection exiting 1; and a malformed
         answers file failing cleanly.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path

from waegis.commands.new import EXIT_FAILURE, EXIT_OK, NEW_STEP_IDS, run_new
from waegis.repo.workflow_toml import ALL_STAGES

from _fake_command_runner import FakeCommandRunner

# CONSTANTS

# @brief A complete non-interactive answer set for schema-version-3 policy.
_FULL_ANSWERS: dict = {
    "source_roots": ["src"],
    "test_roots": ["tests"],
    "language": "python",
    "gate_build_cmds": [],
    "gate_typecheck_cmds": [],
    "gate_lint_cmds": [],
    "gate_test_cmds": [],
    "gate_security_cmds": [],
    "alignment_enabled": True,
    "baseline_guard_mode": "disabled",
    "baseline_minimum_completion_level": "baseline-usable",
    "coverage_mode": "disabled",
    "coverage_roots": [],
    "coverage_exclude": [],
    "source_changes_mode": "unrestricted",
    "alignment_protected_scope_mode": "disabled",
    "alignment_protected_scope_patterns": [],
    "stage_form_retention": "discard",
    "check_execution": "external",
    "gate_build_mode": "disabled",
    "gate_typecheck_mode": "disabled",
    "gate_lint_mode": "disabled",
    "gate_test_mode": "disabled",
    "gate_security_mode": "disabled",
    "secrets_mode": "disabled",
    "secret_patterns": [],
    "protected_paths_mode": "disabled",
    "protected_path_patterns": [],
    "protected_path_operations": [],
    "working_tree_mode": "unrestricted",
    "working_tree_blocked_patterns": [],
    "write_access_mode": "unrestricted",
    "write_access_stages": {stage: [] for stage in ALL_STAGES},
    "scope_mode": "unrestricted",
    "scope_allowed_roots": [],
    "delivery_mode": "disabled",
    "delivery_command_patterns": [],
}


# LOCAL HELPERS


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


def test_non_interactive_incomplete_answers_fails_before_engine(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``--non-interactive`` with an incomplete answers file fails
                naming EVERY missing required key (not just the first), before
                any engine or journal work: TARGET untouched, no journal dir.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the failure is late, partial, or silent.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    home = tmp_path / "home"
    target = tmp_path / "proj"
    answers = _write_answers(tmp_path / "answers.json", {"source_roots": ["src"]})
    out = io.StringIO()

    code = run_new(
        target,
        stream=out,
        answers_path=answers,
        non_interactive=True,
        runner=FakeCommandRunner({}),
        home=home,
    )

    assert code == EXIT_FAILURE
    text = out.getvalue()
    for key in (
        "test_roots",
        "language",
        "gate_build_cmds",
        "gate_typecheck_cmds",
        "gate_lint_cmds",
        "gate_test_cmds",
        "gate_security_cmds",
        "stage_form_retention",
        "check_execution",
        "alignment_enabled",
    ):
        assert key in text, f"missing key not named: {key}"
    assert not target.exists()
    assert not (home / "journals").exists()


def test_non_interactive_other_language_requires_extension_answers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      language="other" additionally requires source_extensions and
                test_file_patterns in a non-interactive run.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the conditional requirement is not enforced.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    answers = _write_answers(tmp_path / "answers.json", {**_FULL_ANSWERS, "language": "other"})
    out = io.StringIO()

    code = run_new(
        tmp_path / "proj",
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
    @brief      ``--dry-run`` renders the plan preview (net.proxy filtered out
                for a local flow) and leaves TARGET and the journal untouched.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If anything was created or the preview is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    home = tmp_path / "home"
    target = tmp_path / "proj"
    out = io.StringIO()

    code = run_new(
        target,
        stream=out,
        dry_run=True,
        stdin=io.StringIO(""),
        runner=FakeCommandRunner({}),
        home=home,
    )

    assert code == EXIT_OK
    text = out.getvalue()
    assert "WAEGIS plan preview" in text
    assert "home.init" in text and "handoff.summary" in text
    assert "net.proxy" not in text  # no clone URL -> the step does not apply
    assert "dry run: no changes were made." in text
    assert not target.exists()
    assert not home.exists()


def test_dry_run_json_is_the_frozen_plan_preview_shape(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      ``--dry-run --json`` emits exactly one JSON document with the
                frozen plan-preview field names from io/console.py.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the JSON shape deviates from the contract.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    out = io.StringIO()
    answers = _write_answers(tmp_path / "answers.json", _FULL_ANSWERS)

    code = run_new(
        tmp_path / "proj",
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
    assert document["command"] == "new"
    assert document["status"] == "ok"
    plan = document["plan"]
    assert plan["mode"] == "new"
    assert plan["dry_run"] is True
    planned_ids = [step["id"] for step in plan["steps"]]
    assert planned_ids == [step_id for step_id in NEW_STEP_IDS if step_id != "net.proxy"]
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
    answers = _write_answers(tmp_path / "answers.json", {**_FULL_ANSWERS, "bogus_key": 1})
    out = io.StringIO()

    code = run_new(
        tmp_path / "proj",
        stream=out,
        answers_path=answers,
        dry_run=True,
        non_interactive=True,
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )

    assert code == EXIT_OK
    assert "bogus_key" in out.getvalue()


def test_plan_rejection_exits_one_and_changes_nothing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Answering 'n' at the plan-approval gate stops the run before
                any step: exit 1, TARGET untouched.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the rejection path misbehaves.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "proj"
    out = io.StringIO()

    code = run_new(
        target,
        stream=out,
        stdin=io.StringIO("n\n"),
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )

    assert code == EXIT_FAILURE
    assert "plan not approved" in out.getvalue()
    assert not target.exists()


def test_malformed_answers_file_fails_cleanly(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      An unreadable/unsupported answers file exits 1 with the
                answers-seam error message, before any engine work.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the failure is not clean.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    bad = tmp_path / "answers.txt"
    bad.write_text("not = usable", encoding="utf-8")
    out = io.StringIO()

    code = run_new(
        tmp_path / "proj",
        stream=out,
        answers_path=bad,
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )

    assert code == 2
    assert "answers file" in out.getvalue()


def test_incompatible_payload_is_rejected_before_planning(tmp_path: Path) -> None:
    """
    @brief      Verify a payload outside the supported range cannot reach the engine.
    @param[in]  tmp_path Temporary payload and target workspace.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    payload = tmp_path / "payload"
    (payload / ".agentic/cli").mkdir(parents=True)
    (payload / ".agentic/workflow.toml").write_text("[source]\nroots=[]\n", encoding="utf-8")
    (payload / ".agentic/cli/pyproject.toml").write_text(
        '[project]\nname="aegis"\nversion="1.9.9"\n',
        encoding="utf-8",
    )
    out = io.StringIO()
    code = run_new(
        tmp_path / "repo",
        stream=out,
        dry_run=True,
        as_json=True,
        payload=payload,
        runner=FakeCommandRunner({}),
        home=tmp_path / "home",
    )
    assert code == 2
    document = json.loads(out.getvalue())
    assert document["status"] == "failed"
    assert "incompatible" in " ".join(document["messages"])


# END OF FILE
