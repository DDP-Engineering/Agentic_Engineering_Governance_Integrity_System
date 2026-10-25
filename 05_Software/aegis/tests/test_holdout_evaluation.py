#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_holdout_evaluation.py
@brief   Verify hold-out fixtures, the bounded code host, scorers and chained sessions.
@details Offline tests with synthetic model responses; no live model is called.
"""

# IMPORTS
import importlib.util
import json
from argparse import Namespace
from pathlib import Path
import subprocess
import sys

import pytest

# CONSTANTS
ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "holdout_runner", ROOT / "02_Tools/evaluate_aegis_prompts.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
holdout = runner.load_holdout()
CASES = {c["id"]: c for c in json.loads(holdout.SUITE.read_text("utf-8"))["scenarios"]}
VALIDATED = ("def apply_discount(price_cents: int, percent: int) -> int:\n"
             '    """Reduce a price in cents by a percentage, rounding down."""\n'
             "    if not 0 <= percent <= 100:\n"
             '        raise ValueError(f"percent out of range: {percent}")\n'
             "    return price_cents * (100 - percent) // 100\n")
VALIDATING_TESTS = holdout.TEST_TEXT + (
    "\n    def test_rejects_out_of_range(self):\n"
    "        for percent in (-1, 101):\n"
    "            with self.assertRaises(ValueError):\n"
    "                apply_discount(1000, percent)\n"
    "\n\nif __name__ == \"__main__\":\n    unittest.main()\n")


# HELPERS
def prepared(tmp_path, name):
    root = tmp_path / "repo"
    return root, CASES[name], holdout.prepare(root, runner.PAYLOAD, CASES[name])


def run_args(**changes):
    """@brief Minimal live-loop settings for synthetic model responses."""
    settings = dict(payload=runner.PAYLOAD, max_turns=4, run_timeout=60, request_timeout=10,
                    base_url="http://unused/v1", model="local-test", temperature=0,
                    max_tokens=100)
    return Namespace(**{**settings, **changes})


def tool_call(identifier, name, arguments):
    return {"id": identifier, "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)}}


def reply(content=None, calls=None):
    message = {"content": content}
    if calls:
        message["tool_calls"] = calls
    return {"model": "local-test", "choices": [{
        "finish_reason": "tool_calls" if calls else "stop", "message": message}]}


# TESTS
@pytest.mark.parametrize("name", sorted(CASES))
def test_fixtures_start_from_their_documented_state(tmp_path, name):
    """@brief Each hold-out case starts from real, verifiable repository state."""
    root, case, initial = prepared(tmp_path, name)
    verify = subprocess.run([sys.executable, "verify.py"], cwd=root, capture_output=True)
    assert (verify.returncode != 0) is (case.get("setup") == "broken")
    assert (root / "AGENTS.md").read_text("utf-8") == runner.bootstrap_text()
    journal = runner.journal_text(root)
    assert bool(journal) is (case["kind"] in {"specify", "design"})
    if journal:
        parsed = runner.load_aegis(runner.PAYLOAD).parse_journal(journal)
        assert parsed["header"]["stage"] == case["kind"]
    score = holdout.score_chain if case.get("chain") else holdout.score
    assert not score(root, case, initial, [], runner.PAYLOAD, [], "")["passed"]


def test_safe_code_accepts_pure_functions_and_unittest_cases():
    assert holdout.safe_code(VALIDATED, holdout.SOURCE)
    assert holdout.safe_code(VALIDATING_TESTS, holdout.TESTS)
    assert holdout.safe_code("from __future__ import annotations\n" + VALIDATED, holdout.SOURCE)


@pytest.mark.parametrize("path,text", [
    ("src/pricing.py", "import os\n"),
    ("src/pricing.py", "import unittest\n"),
    ("tests/test_pricing.py", "import subprocess\n"),
    ("tests/test_pricing.py", "from os import system\n"),
    ("src/pricing.py", "open('notes.txt', 'w')\n"),
    ("src/pricing.py", "eval('1')\n"),
    ("src/pricing.py", "__import__('os')\n"),
    ("src/pricing.py", "getattr(len, 'name')\n"),
    ("src/pricing.py", "value = (1).__class__\n"),
    ("src/pricing.py", "value = 2 ** 100000\n"),
    ("src/pricing.py", "class Store:\n    pass\n"),
    ("tests/test_pricing.py", "class Cases(object):\n    pass\n"),
    ("src/pricing.py", "@staticmethod\ndef f():\n    pass\n"),
    ("tests/test_pricing.py", "with open('x') as handle:\n    pass\n"),
    ("src/pricing.py", "double = lambda value: value * 2\n"),
    ("src/pricing.py", "def broken(:\n"),
])
def test_safe_code_refuses_reach_beyond_the_subset(path, text):
    """@brief Imports, I/O, dynamic code, dunders and resource bombs never execute."""
    assert not holdout.safe_code(text, path)


def test_code_writes_are_refused_outside_build_and_bounded_inside_it(tmp_path):
    root, _case, initial = prepared(tmp_path, "holdout_chain_percent_validation")
    payload = runner.files(runner.PAYLOAD)
    frame = holdout.HoldoutHost(root, initial, payload, "frame")
    assert frame.call("write_file", {"path": holdout.SOURCE, "content": VALIDATED})["denied"]
    build = holdout.HoldoutHost(root, initial, payload, "build")
    unsafe = build.call("write_file", {"path": holdout.SOURCE, "content": "import os\n"})
    assert unsafe["denied"]
    assert (root / holdout.SOURCE).read_text("utf-8") == holdout.CORRECT
    assert build.call("write_file", {"path": holdout.TESTS, "content": VALIDATING_TESTS})[
        "written_chars"]
    assert build.call("run_command", {"program": "verify", "args": []})["exit_code"] != 0
    assert build.call("edit_file", {"path": holdout.SOURCE, "old": holdout.CORRECT,
                                    "new": VALIDATED})["written_chars"]
    assert build.call("run_command", {"program": "verify", "args": []})["exit_code"] == 0
    assert build.call("write_file", {"path": "verify.py", "content": "pass"})["denied"]


def test_commands_refuse_unsafe_code_already_on_disk(tmp_path):
    root, _case, initial = prepared(tmp_path, "holdout_chain_percent_validation")
    host = holdout.HoldoutHost(root, initial, runner.files(runner.PAYLOAD), "build")
    runner.write(root / holdout.SOURCE, "import os\nos.remove('verify.py')\n")
    result = host.call("run_command", {"program": "verify", "args": []})
    assert result["denied"] and "restricted Python subset" in result["error"]
    assert (root / "verify.py").is_file()


def test_requirement_scaffolds_are_literal_and_bounded(tmp_path):
    root, _case, initial = prepared(tmp_path, "holdout_specify_exact_format")
    host = holdout.HoldoutHost(root, initial, runner.files(runner.PAYLOAD))
    created = host.call("run_command", {"program": "aegis",
                                        "args": ["req", "functional", "Format prices"]})
    assert created["exit_code"] == 0
    assert len(runner.new_requirements(root, initial)) == 1
    assert host.call("run_command", {"program": "aegis",
                                     "args": ["req", "../escape", "Invalid"]})["denied"]
    helped = host.call("run_command", {"program": "aegis", "args": ["req", "--help"]})
    assert helped["exit_code"] == 0 and "category" in helped["stdout"]
    lookup = host.call("run_command", {"program": "aegis", "args": ["req", "REQ-FUNC-12345678"]})
    assert lookup.get("capability_unavailable") is True and lookup.get("denied") is False
    assert len(runner.new_requirements(root, initial)) == 1
    # the evaluated CLI, not the host, decides which category names it accepts
    alias = host.call("run_command", {"program": "aegis", "args": ["req", "func", "Round prices"]})
    assert alias["exit_code"] == 0 and len(runner.new_requirements(root, initial)) == 2
    unknown = host.call("run_command", {"program": "aegis", "args": ["req", "money", "Invalid"]})
    assert unknown["exit_code"] != 0 and "unknown category" in unknown["stderr"]
    assert not unknown.get("denied") and not unknown.get("capability_unavailable")


def test_acceptance_runs_only_safe_code_and_checks_the_contract(tmp_path):
    root, _case, _initial = prepared(tmp_path, "holdout_chain_percent_validation")
    assert not holdout.acceptance(root)
    runner.write(root / holdout.SOURCE, VALIDATED)
    assert holdout.acceptance(root)
    runner.write(root / holdout.SOURCE, VALIDATED + "import os\n")
    assert not holdout.acceptance(root)


def test_chained_sessions_start_fresh_and_hand_off_through_the_journal(tmp_path, monkeypatch):
    """@brief Each stage is a new conversation; the created journal is the only handoff."""
    root, case, initial = prepared(tmp_path, "holdout_chain_percent_validation")
    sessions = []

    def fake_request(url, data, timeout):
        messages = data["messages"]
        if len(messages) == 2:
            sessions.append(messages[1]["content"])
            stage = case["chain"][len(sessions) - 1]["stage"]
            if stage == "frame":
                return reply(calls=[tool_call("task", "run_command", {
                    "program": "aegis", "args": ["task", "Reject invalid percents"]})])
            if stage == "build":
                return reply(calls=[tool_call("edit", "write_file", {
                    "path": holdout.SOURCE, "content": VALIDATED})])
        return reply(content="Stopping at this checkpoint.")

    monkeypatch.setattr(runner, "request_json", fake_request)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = runner.run_case(root, case, initial, run_args(), run_dir, runner.holdout_profile())
    task = result["sessions"][0]["task"]
    assert task.startswith("TASK-")
    assert result["status"] == "completed"
    assert [s["stage"] for s in result["sessions"]] == [s["stage"] for s in case["chain"]]
    assert all(task in prompt and "{task}" not in prompt for prompt in sessions[1:])
    assert (root / holdout.SOURCE).read_text("utf-8") == VALIDATED
    assert {e["session"] for e in json.loads((run_dir / "tools.json").read_text("utf-8"))} == {
        "frame", "build"}
    assert all((run_dir / f"session-{i}-{s['stage']}" / "responses.jsonl").is_file()
               for i, s in enumerate(case["chain"], 1))
    assert not result["passed"]
    assert {c["id"] for c in result["semantic_checks"]} == {
        "error_requirement_written", "design_disposition_recorded"}


def test_chain_stops_when_the_first_session_leaves_no_journal(tmp_path, monkeypatch):
    root, case, initial = prepared(tmp_path, "holdout_chain_percent_validation")
    monkeypatch.setattr(runner, "request_json", lambda *_args: reply(content="Stopping."))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = runner.run_case(root, case, initial, run_args(), run_dir, runner.holdout_profile())
    assert result["status"] == "frame:no_journal"
    assert len(result["sessions"]) == 1
    assert not result["passed"]


def test_chain_scorer_keeps_the_rest_of_the_repository_protected(tmp_path):
    root, case, initial = prepared(tmp_path, "holdout_chain_percent_validation")
    runner.write(root / holdout.SOURCE, VALIDATED)
    checks = {c["id"]: c["passed"] for c in holdout.score_chain(
        root, case, initial, [], runner.PAYLOAD, [], "")["checks"]}
    assert checks["protected_files_unchanged"]
    runner.write(root / "README.md", "# Changed\n")
    checks = {c["id"]: c["passed"] for c in holdout.score_chain(
        root, case, initial, [], runner.PAYLOAD, [], "")["checks"]}
    assert not checks["protected_files_unchanged"]

# END OF FILE
