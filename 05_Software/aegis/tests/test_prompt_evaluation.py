#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See LICENSE.txt for full details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_prompt_evaluation.py
@brief   Exercise evaluation isolation, observed proof and experiment integrity.
@details Tests the development harness offline, with synthetic model responses.
         They do not assert model quality or documentation wording.
"""

# IMPORTS
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# CONSTANTS
ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "prompt_evaluation", ROOT / "02_Tools/evaluate_aegis_prompts.py")
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)
CASES = json.loads(evaluation.SUITE.read_text("utf-8"))["scenarios"]


# HELPERS
def case_named(name):
    return next(c for c in CASES if c["id"] == name)


@pytest.fixture
def prepared(tmp_path):
    """@brief Provide an isolated validation fixture and trusted tool host."""
    case = case_named("validate_clean_checkpoint")
    root = tmp_path / "repo"
    initial = evaluation.prepare(root, evaluation.PAYLOAD, case)
    return root, case, initial, evaluation.Host(root, initial, evaluation.files(evaluation.PAYLOAD))


def finish_records(root, *, evidence=""):
    """@brief Write a plausible paused record, without fabricating a tool event."""
    path = root / evaluation.TASK
    text = path.read_text("utf-8")
    text = evaluation.section(text, "Handoff",
        f"current: validate\nstatus: waiting\nnext: Await delivery decision\n"
        f"must_read: {evaluation.TASK}\nblockers:")
    text = evaluation.section(text, "Stage report",
        "stage: validate\nresult: paused\ncurrent: validate\nchanged: trim fix\n"
        f"evidence: {evidence}\nissues:\nnext: Await delivery decision\nneeds_user: yes\n"
        "spec_compliance: disabled\nimplementation_quality: disabled\nreview_round:")
    evaluation.write(path, text)


def checks(result):
    return {check["id"]: check["passed"] for check in result["checks"]}


# TESTS
@pytest.mark.parametrize("name", ["../escape.md", "/absolute.md", "C:/escape.md",
                                 ".git/config", ".agentic/../src/normalize.py",
                                 ".agentic/aegis.py", ".agentic/aegis.toml",
                                 ".agentic/context/injected.py"])
def test_host_rejects_paths_outside_record_capability(prepared, name):
    """REQ-FUNC-b8f0efc5: evaluation writes remain project-owned records."""
    _root, _case, _initial, host = prepared
    assert "error" in host.call("write_file", {"path": name, "content": "bad"})


def test_host_edits_only_an_exact_single_match(prepared):
    root, _case, _initial, host = prepared
    target = ".agentic/context/note.md"
    assert host.call("write_file", {"path": target, "content": "one one"})["written_chars"]
    assert "error" in host.call("edit_file", {"path": target, "old": "one", "new": "two"})
    assert (root / target).read_text("utf-8") == "one one"


@pytest.mark.parametrize("program,args", [
    ("git", ["push"]), ("git", ["config", "alias.x", "!bad"]),
    ("aegis", ["report", "TASK-aaaaaaaa"]), ("verify", ["; bad"]),
    ("python", ["-c", "print('bad')"]),
])
def test_host_rejects_arbitrary_commands(prepared, program, args):
    _root, _case, _initial, host = prepared
    assert "error" in host.call("run_command", {"program": program, "args": args})


@pytest.mark.parametrize("args", [
    ["status"], ["log", "--oneline", "-15"], ["log", "-n", "20"],
    ["diff", "HEAD", "--", "src/normalize.py"],
    ["diff", "src/normalize.py"], ["diff", "--stat", "HEAD"],
    ["show", "HEAD:src/normalize.py"], ["ls-files", "tests/"], ["branch", "--list"],
])
def test_git_reads_support_history_and_scoped_inspection(prepared, args):
    """REQ-FUNC-b8f0efc5: fixture inspection has usable bounded read capabilities."""
    root, _case, initial, host = prepared
    before = evaluation.files(root)
    result = host.call("run_command", {"program": "git", "args": args})
    assert result.get("exit_code") == 0, result
    assert evaluation.files(root) == before
    assert evaluation.git(root, "rev-parse", "HEAD") == initial["head"]
    if args[0] == "diff" and "--stat" not in args:
        assert "value.strip().lower()" in result["stdout"]
    if args[0] == "show":
        assert "return value.lower()" in result["stdout"]


@pytest.mark.parametrize("args", [
    ["checkout", "-b", "other"], ["reset", "--hard"],
    ["diff", "--output=changed.txt"], ["diff", "--ext-diff"],
    ["show", "HEAD:../escape.py"], ["show", "HEAD:.git/config"],
    ["diff", "--", "../escape.py"], ["-c", "alias.x=!bad", "x"],
])
def test_git_reads_cannot_mutate_or_escape_fixture(prepared, args):
    """REQ-FUNC-b8f0efc5: broader reads preserve the fixture capability boundary."""
    root, _case, initial, host = prepared
    before = evaluation.files(root)
    result = host.call("run_command", {"program": "git", "args": args})
    assert result.get("denied") is True, result
    assert evaluation.files(root) == before
    assert evaluation.git(root, "rev-parse", "HEAD") == initial["head"]


def test_git_reads_ignore_inherited_repository_override(prepared, monkeypatch):
    """REQ-FUNC-b8f0efc5: ambient Git variables cannot redirect fixture reads."""
    root, _case, initial, host = prepared
    monkeypatch.setenv("GIT_DIR", str(root.parent / "not-the-fixture"))
    result = host.call("run_command", {"program": "git", "args": ["rev-parse", "HEAD"]})
    assert result.get("exit_code") == 0, result
    assert result["stdout"].strip() == initial["head"]


def test_unavailable_git_option_is_distinct_and_describes_supported_reads(prepared):
    """REQ-FUNC-b8f0efc5: unavailable inspection is not a forbidden mutation."""
    root, case, initial, host = prepared
    result = host.call("run_command", {"program": "git",
        "args": ["log", "--graph"]})
    assert result.get("capability_unavailable") is True
    assert result.get("denied") is False
    assert result.get("available_commands", {}).get("git")
    observed = checks(evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD))
    assert observed["no_forbidden_actions"]
    finish_records(root, evidence="Observed successful strict verification.")
    proof = host.call("run_command", {"program": "aegis",
        "args": ["check", "--task", "TASK-aaaaaaaa", "--strict", "--run"]})
    assert proof["exit_code"] == 0, proof
    host.call("run_command", {"program": "aegis", "args": ["summary", "TASK-aaaaaaaa"]})
    result = evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD)
    assert result["passed"], result


@pytest.mark.parametrize("evidence,accepted", [
    ("", True), ("not recorded", True),
    ("none recorded; no tests or checks run for this candidate", True),
    ("not recorded — no tests or checks have been run for this candidate", True),
    ("No verification has been executed for this candidate.", True),
    ("No tests have run; focused verification is pending.", True),
    ("All tests passed.", False),
    ("Unit tests pass locally but are not part of configured verification.", False),
    ("No tests run; all checks passed.", False),
    ("not recorded; verification exit=0", False),
    ("No tests have failed.", False),
    ("Inspected tests/test_normalize.py", False),
])
def test_unavailable_evidence_accepts_negative_reports_without_inventing_proof(
        prepared, evidence, accepted):
    """REQ-FUNC-7ea14fe4: truthful missing evidence is not a passing-test claim."""
    root, case, initial, host = prepared
    finish_records(root, evidence=evidence)
    case = {**case, "expect": {**case["expect"], "empty_evidence": True}}
    result = evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD)
    assert checks(result)["evidence_not_fabricated"] is accepted


def test_unavailable_evidence_cannot_conceal_an_executed_verifier(prepared):
    """REQ-FUNC-7ea14fe4: observed execution overrides an authored no-tests claim."""
    root, case, initial, host = prepared
    host.call("run_command", {"program": "verify", "args": []})
    finish_records(root, evidence="No tests or checks have been run.")
    case = {**case, "expect": {**case["expect"], "empty_evidence": True}}
    result = evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD)
    assert not checks(result)["evidence_not_fabricated"]


def test_host_refuses_modified_verification_configuration(prepared):
    root, _case, _initial, host = prepared
    evaluation.write(root / ".agentic/aegis.toml", '[commands]\ntest = "bad"')
    result = host.call("run_command", {"program": "aegis", "args": ["check", "--run"]})
    assert "trusted executable/config changed" in result["error"]


def test_self_reported_pass_does_not_establish_proof(prepared):
    """REQ-FUNC-9514e017: an authored record is not execution evidence."""
    root, case, initial, host = prepared
    finish_records(root, evidence="All tests passed.")
    result = evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD)
    assert not checks(result)["fresh_successful_proof"]
    assert not result["passed"]
    assert result["semantic_review"] == "pending"


def test_real_final_proof_binds_contract_files_but_allows_journal_updates(prepared):
    """REQ-FUNC-d60b322b: final proof applies to the candidate being reported."""
    root, case, initial, host = prepared
    proof = host.call("run_command", {"program": "aegis",
        "args": ["check", "--task", "TASK-aaaaaaaa", "--strict", "--run"]})
    assert proof["exit_code"] == 0, proof
    finish_records(root, evidence="Observed strict verification exit=0.")
    host.call("run_command", {"program": "aegis", "args": ["summary", "TASK-aaaaaaaa"]})
    result = evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD)
    assert result["passed"], [c for c in result["checks"] if not c["passed"]]
    evaluation.write(root / ".agentic/context/project.md", "# Changed after proof\n")
    result = evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD)
    assert not checks(result)["fresh_successful_proof"]


def test_failed_verification_keeps_real_nonzero_status(tmp_path):
    case = case_named("validate_failed_verification")
    root = tmp_path / "repo"
    initial = evaluation.prepare(root, evaluation.PAYLOAD, case)
    host = evaluation.Host(root, initial, evaluation.files(evaluation.PAYLOAD))
    outcome = host.call("run_command", {"program": "aegis",
        "args": ["check", "--task", "TASK-aaaaaaaa", "--strict", "--run"]})
    assert outcome["exit_code"] != 0
    assert "unavailable external test service" in outcome["stdout"]
    result = evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD)
    assert checks(result)["observed_failed_proof"]
    assert not checks(result)["records_limitation"]


def test_missing_journal_is_a_failure_not_empty_success(tmp_path):
    case = case_named("frame_existing_fix")
    root = tmp_path / "repo"
    initial = evaluation.prepare(root, evaluation.PAYLOAD, case)
    result = evaluation.score(root, case, initial, [], evaluation.PAYLOAD)
    assert not result["passed"]
    assert not checks(result)["one_journal"]


def test_history_and_stale_approvals_are_observed_independently(tmp_path):
    """REQ-FUNC-7ea14fe4: the scorer detects loss of append-only evidence."""
    case = case_named("validate_stale_verdicts")
    root = tmp_path / "repo"
    initial = evaluation.prepare(root, evaluation.PAYLOAD, case)
    result = evaluation.score(root, case, initial, [], evaluation.PAYLOAD)
    assert not checks(result)["old_approvals_invalidated"]
    path = root / evaluation.TASK
    evaluation.write(path, evaluation.section(path.read_text("utf-8"), "Log", ""))
    result = evaluation.score(root, case, initial, [], evaluation.PAYLOAD)
    assert not checks(result)["preserves_history"]


@pytest.mark.parametrize("max_tokens", [8192, 16384])
def test_live_loop_uses_actual_tool_results_and_keeps_failed_outcome(
        prepared, tmp_path, monkeypatch, max_tokens):
    """@brief REQ-FUNC-d60b322b: preserve budgets and actual tool evidence per request."""
    from argparse import Namespace

    root, case, initial, _host = prepared
    replies = iter([
        {"model": "local-test", "choices": [{"finish_reason": "tool_calls", "message": {
            "content": None, "tool_calls": [{"id": "call1", "type": "function",
                "function": {"name": "read_file",
                             "arguments": '{"path": "README.md"}'}}]}}]},
        {"model": "local-test", "usage": {"prompt_tokens": 20, "completion_tokens": 3},
         "choices": [{"finish_reason": "stop", "message": {"content": "All done."}}]},
    ])
    requests = []

    def fake_request(url, data, timeout):
        requests.append(json.loads(json.dumps(data)))
        return next(replies)

    monkeypatch.setattr(evaluation, "request_json", fake_request)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    args = Namespace(payload=evaluation.PAYLOAD, max_turns=3, run_timeout=60,
        request_timeout=10, base_url="http://unused/v1", model="local-test",
        temperature=0, max_tokens=max_tokens)
    result = evaluation.run_case(root, case, initial, args, run_dir)
    assert result["status"] == "completed"
    assert not result["passed"]
    assert result["usage"][0] is None
    assert all(request["max_tokens"] == max_tokens for request in requests)
    assert requests[1]["messages"][-1]["role"] == "tool"
    assert "Name normalization" in requests[1]["messages"][-1]["content"]
    assert (run_dir / "responses.jsonl").is_file()


def test_compare_rejects_changed_controls_and_incomplete_runs(tmp_path):
    before, after = tmp_path / "before", tmp_path / "after"
    manifest = {"model": "m", "scenario_ids": ["case"], "repeats": 1}
    for root in (before, after):
        evaluation.dump(root / "manifest.json", manifest)
        evaluation.dump(root / "results.json", [
            {"scenario": "case", "repeat": 1, "passed": True, "seconds": 1.0}])
    assert evaluation.compare(before, after)["automated_regressions"] == []
    evaluation.dump(after / "results.json", [])
    with pytest.raises(ValueError, match="incomplete"):
        evaluation.compare(before, after)
    evaluation.dump(after / "manifest.json", {**manifest, "model": "another"})
    with pytest.raises(ValueError, match="incomparable controls: model"):
        evaluation.compare(before, after)


@pytest.mark.parametrize("failure", ["timeout", "malformed", "truncated"])
def test_incomplete_model_execution_cannot_pass(prepared, tmp_path, monkeypatch, failure):
    """REQ-FUNC-d60b322b: missing execution evidence stays an explicit failure."""
    from argparse import Namespace

    root, case, initial, _host = prepared
    calls = []

    def fake_request(url, data, timeout):
        calls.append(url)
        if failure == "timeout":
            raise TimeoutError("request deadline")
        if failure == "malformed":
            return {"unexpected": "shape"}
        return {"model": "local-test", "choices": [{
            "finish_reason": "length", "message": {"content": "Incomplete"}}]}

    monkeypatch.setattr(evaluation, "request_json", fake_request)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    args = Namespace(payload=evaluation.PAYLOAD, max_turns=3, run_timeout=60,
        request_timeout=10, base_url="http://unused/v1", model="local-test",
        temperature=0, max_tokens=100)
    result = evaluation.run_case(root, case, initial, args, run_dir)
    assert result["status"] == ("output_limit" if failure == "truncated" else "runner_error")
    assert not result["passed"]
    assert len(calls) == 1
    assert (run_dir / "result.json").is_file()


def test_unlisted_model_is_rejected_before_any_fixture_or_output(tmp_path, monkeypatch):
    from argparse import Namespace

    monkeypatch.setattr(evaluation, "request_json",
                        lambda *_args: {"data": [{"id": "different-model"}]})
    args = Namespace(cases="", base_url="http://unused/v1", model="requested-model",
                     output=tmp_path / "output", work_dir=tmp_path / "work",
                     payload=evaluation.PAYLOAD)
    with pytest.raises(ValueError, match="no fallback"):
        evaluation.execute(args)
    assert not args.output.exists()
    assert not args.work_dir.exists()

# END OF FILE
