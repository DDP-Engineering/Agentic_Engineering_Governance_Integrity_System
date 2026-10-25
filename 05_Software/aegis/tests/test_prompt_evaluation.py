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
from argparse import Namespace
from pathlib import Path
import shutil
import zipfile

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
    text = evaluation.resume_state(path.read_text("utf-8"), evaluation.PAYLOAD, "validate",
                                   "Await delivery decision", waiting=True,
                                   changed="trim fix", evidence=evidence)
    evaluation.write(path, text)


def checks(result):
    return {check["id"]: check["passed"] for check in result["checks"]}


def run_args(**changes):
    """@brief Minimal live-loop settings for synthetic model responses."""
    settings = dict(payload=evaluation.PAYLOAD, max_turns=3, run_timeout=60,
                    request_timeout=10, base_url="http://unused/v1", model="local-test",
                    temperature=0, max_tokens=100)
    return Namespace(**{**settings, **changes})


def tool_call(identifier, name, arguments):
    return {"id": identifier, "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)}}


def reply(*, content=None, calls=None, usage=None):
    """@brief One synthetic Chat Completions response."""
    message = {"content": content}
    if calls:
        message["tool_calls"] = calls
    response = {"model": "local-test", "choices": [{
        "finish_reason": "tool_calls" if calls else "stop", "message": message}]}
    if usage:
        response["usage"] = usage
    return response


def capability_case(name):
    capabilities = evaluation.load_capabilities()
    return capabilities, next(c for c in json.loads(
        capabilities.SUITE.read_text("utf-8"))["scenarios"] if c["id"] == name)


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
    ("aegis", ["init"]), ("verify", ["; bad"]),
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


def test_git_named_again_in_its_args_is_a_wrong_call_unless_it_writes(prepared):
    """`git git status` is a malformed read; a write named after the repeat stays forbidden."""
    root, case, initial, host = prepared
    repeated = host.call("run_command", {"program": "git", "args": ["git", "status", "--short"]})
    assert repeated.get("capability_unavailable") is True and repeated.get("denied") is False
    assert "leave it out of args" in repeated["error"]
    assert host.call("run_command", {"program": "git", "args": ["git", "push"]})["denied"] is True
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
    ("unavailable: no tests or checks run for this candidate", True),
    ("unavailable: all checks passed", False),
    ("tests: passed", False),
    ("not recorded - no tests or checks run for this candidate yet", True),
    ("tests - passed", False),
    ("No tests or checks run for this candidate; focused verification remains pending.", True),
    ("Verification remains pending; tests passed.", False),
    ("No tests or checks run; unavailable evidence remains unavailable.", True),
    ("Evidence is unavailable; all tests passed.", False),
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


def test_directory_read_is_unavailable_not_forbidden(prepared):
    """REQ-FUNC-b8f0efc5: reading a directory is a wrong tool, not a forbidden action."""
    root, case, initial, host = prepared
    result = host.call("read_file", {"path": "src"})
    assert result.get("capability_unavailable") is True
    assert result.get("denied") is False
    observed = checks(evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD))
    assert observed["no_forbidden_actions"]


def test_read_file_returns_whole_lines_and_says_where_the_file_ends(prepared):
    """`offset` is the first line, 1-based, and `limit` a line count; the result
    names the end of the file, so a reader never pages in small character slices."""
    root, _case, _initial, host = prepared
    lines = (root / evaluation.TASK).read_text("utf-8").splitlines(keepends=True)
    whole = host.call("read_file", {"path": evaluation.TASK})
    assert whole == {"text": "".join(lines), "total_lines": len(lines), "eof": True,
                     "next_offset": None}
    part = host.call("read_file", {"path": evaluation.TASK, "offset": 2, "limit": 3})
    assert part["text"] == "".join(lines[1:4])
    assert (part["eof"], part["next_offset"]) == (False, 5)
    tail = host.call("read_file", {"path": evaluation.TASK, "offset": len(lines) - 1,
                                   "limit": 60})
    assert tail["text"] == "".join(lines[-2:]) and tail["eof"] is True
    past = host.call("read_file", {"path": evaluation.TASK, "offset": len(lines) + 10})
    assert (past["text"], past["eof"], past["next_offset"]) == ("", True, None)
    for offset, limit in ((0, None), (-4, 0), (1, -2)):  # read from the top, to the end
        arguments = {"path": evaluation.TASK, "offset": offset}
        if limit is not None:
            arguments["limit"] = limit
        assert host.call("read_file", arguments)["text"] == "".join(lines)
    wrong = host.call("read_file", {"path": evaluation.TASK, "offset": "second"})
    assert "error" in wrong and wrong["denied"] is False


def test_read_slices_stop_on_a_line_boundary_at_the_character_bound():
    """At most READ_CHARS characters per result, in whole lines; one longer line is cut."""
    text = "".join(f"{index:098d}\n" for index in range(1000))  # 99 characters a line
    first = evaluation.read_slice(text, None, None)
    assert len(first["text"]) <= evaluation.READ_CHARS
    assert first["text"].endswith("\n") and first["eof"] is False
    resumed = evaluation.read_slice(text, first["next_offset"], None)
    assert resumed["text"].startswith(f"{first['next_offset'] - 1:098d}\n")
    long_line = evaluation.read_slice("x" * (evaluation.READ_CHARS + 5) + "\nend\n", 1, 1)
    assert len(long_line["text"]) == evaluation.READ_CHARS and long_line["next_offset"] == 2
    assert evaluation.read_slice("", None, None) == {"text": "", "total_lines": 0, "eof": True,
                                                     "next_offset": None}


def test_a_tool_requested_as_a_program_is_unavailable_not_forbidden(prepared):
    """REQ-FUNC-b8f0efc5: run_command program=list_files is a wrong tool choice."""
    root, case, initial, host = prepared
    result = host.call("run_command", {"program": "list_files", "args": [".agentic"]})
    assert result.get("capability_unavailable") is True and result.get("denied") is False
    assert "call it directly" in result["error"]
    observed = checks(evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD))
    assert observed["no_forbidden_actions"]
    shell = host.call("run_command", {"program": "python", "args": ["-c", "print(1)"]})
    assert shell.get("denied") is True


def test_an_unknown_cli_command_is_unavailable_but_a_disallowed_one_is_forbidden(prepared):
    """REQ-FUNC-b8f0efc5: guessing a command name is not a forbidden action."""
    root, case, initial, host = prepared
    guess = host.call("run_command", {"program": "aegis", "args": ["journal", "TASK-aaaaaaaa"]})
    assert guess.get("capability_unavailable") is True and guess.get("denied") is False
    assert "pause" in guess["available_commands"]["aegis"]
    observed = checks(evaluation.score(root, case, initial, host.events, evaluation.PAYLOAD))
    assert observed["no_forbidden_actions"]
    assert host.call("run_command", {"program": "aegis", "args": ["init"]}).get("denied") is True


@pytest.mark.parametrize("value", [None, 7, ["src"]])
def test_non_string_paths_are_rejected_without_stopping_the_host(prepared, value):
    """REQ-FUNC-b8f0efc5: malformed model arguments become tool errors, never crashes."""
    root, _case, _initial, host = prepared
    before = evaluation.files(root)
    for name in ("read_file", "list_files", "write_file"):
        result = host.call(name, {"path": value, "content": "x"})
        assert "error" in result and result["denied"] is False, (name, result)
    assert evaluation.files(root) == before


@pytest.mark.parametrize("sequence,expected", [
    ("AAAAAA", True), ("ABABAB", True), ("CABABAB", True),
    ("AAAAA", False), ("ABABAC", False), ("ABCABC", False),
])
def test_repetition_loop_recognizes_repeated_and_alternating_calls(sequence, expected):
    assert evaluation.repetition_loop(list(sequence)) is expected


def test_alternating_tool_calls_end_the_session_as_a_loop(prepared, tmp_path, monkeypatch):
    """REQ-FUNC-d60b322b: a repetition loop is a distinct outcome and never a pass."""
    root, case, initial, _host = prepared
    calls = [tool_call(f"call{i}", "run_command", {"program": "git", "args": args})
             for i, args in enumerate([["diff", "--stat"], ["diff"]])]
    requests = []
    monkeypatch.setattr(evaluation, "request_json",
                        lambda url, data, timeout: requests.append(data) or reply(calls=calls))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = evaluation.run_case(root, case, initial, run_args(max_turns=40), run_dir)
    assert result["status"] == "loop"
    assert len(requests) == evaluation.LOOP_CALLS // 2
    assert not result["passed"]


@pytest.mark.parametrize("sampling", [{}, {"top_p": 0.8, "top_k": 20},
                                      {"presence_penalty": 1.0},
                                      {"reasoning_effort": "medium"}])
def test_sampling_options_are_sent_only_when_configured(prepared, tmp_path, monkeypatch,
                                                        sampling):
    root, case, initial, _host = prepared
    requests = []
    monkeypatch.setattr(evaluation, "request_json", lambda url, data, timeout:
                        requests.append(data) or reply(content="Stopping."))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    evaluation.run_case(root, case, initial, run_args(**sampling), run_dir)
    sent = {key: requests[0][key] for key in evaluation.SAMPLING if key in requests[0]}
    assert sent == sampling


def test_a_turn_reasoning_is_not_sent_back_with_the_history(prepared, tmp_path, monkeypatch):
    """Thinking output is the model's own scratch space; the next turn sees the content
    and the tool calls only, as the model's chat template expects."""
    root, case, initial, _host = prepared
    requests = []
    answers = iter([reply(calls=[tool_call("c1", "list_files", {"path": "src"})]),
                    reply(content="Stopping.")])

    def fake(url, data, timeout):
        requests.append(json.loads(json.dumps(data)))
        answer = next(answers)
        answer["choices"][0]["message"]["reasoning_content"] = "private scratch"
        return answer

    monkeypatch.setattr(evaluation, "request_json", fake)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    evaluation.run_case(root, case, initial, run_args(reasoning_effort="medium"), run_dir)
    history = requests[1]["messages"]
    assert [m["role"] for m in history][-2:] == ["assistant", "tool"]
    assert "private scratch" not in json.dumps(history)


@pytest.mark.parametrize("text,degenerate", [
    ("Review complete.\n" + "\n</br>" * 300, True),
    ("ab" * 600, True),
    (" ".join(f"Sentence {i} inspects a different file." for i in range(80)), False),
    ("| a | b |\n|---|---|\n" * 10, False),
    ("\n</br>" * 100, False),
])
def test_repetition_run_flags_only_degenerate_text(text, degenerate):
    """REQ-FUNC-d60b322b: a generation loop is recognized without flagging normal prose."""
    assert bool(evaluation.repetition_run(text)) is degenerate


def test_output_cut_inside_repeated_text_ends_as_a_loop(prepared, tmp_path, monkeypatch):
    """REQ-FUNC-d60b322b: text that repeats until the output limit is a loop, not a pass."""
    root, case, initial, _host = prepared
    response = reply(content="The candidate matches.\n" + "\n</br>" * 400)
    response["choices"][0]["finish_reason"] = "length"
    monkeypatch.setattr(evaluation, "request_json", lambda *_args: response)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = evaluation.run_case(root, case, initial, run_args(), run_dir)
    assert result["status"] == "loop"
    assert "repeated text" in result["error"]
    assert result["degenerate_responses"] == 1
    assert not result["passed"]


def test_repeated_text_that_still_finishes_is_counted_not_failed(prepared, tmp_path,
                                                                monkeypatch):
    root, case, initial, _host = prepared
    monkeypatch.setattr(evaluation, "request_json", lambda *_args:
                        reply(content="\n</br>" * 400 + "\nStopping."))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = evaluation.run_case(root, case, initial, run_args(), run_dir)
    assert result["status"] == "completed"
    assert result["degenerate_responses"] == 1
    saved = json.loads((run_dir / "responses.jsonl").read_text("utf-8").splitlines()[0])
    assert saved["repetition_chars"] >= evaluation.REPETITION_CHARS


def test_context_metrics_attribute_prompt_growth_to_each_read(prepared, tmp_path,
                                                              monkeypatch):
    """REQ-FUNC-d60b322b: context use is measured per request and per file read."""
    root, case, initial, _host = prepared
    reads = [tool_call(f"read{i}", "read_file", {"path": path})
             for i, path in enumerate(["README.md", "src/normalize.py"])]
    replies = iter([
        reply(calls=reads, usage={"prompt_tokens": 1000, "completion_tokens": 20}),
        reply(content="Stopping.", usage={"prompt_tokens": 1400, "completion_tokens": 10})])
    monkeypatch.setattr(evaluation, "request_json", lambda *_args: next(replies))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = evaluation.run_case(root, case, initial, run_args(), run_dir, window=2000)
    context = result["context"]
    assert (context["first_prompt_tokens"], context["peak_prompt_tokens"],
            context["total_prompt_tokens"], context["completion_tokens"]) == (1000, 1400, 2400, 30)
    assert context["peak_window_fraction"] == 0.7
    assert context["above_window_thresholds"] == [0.5]
    costs = {item["path"]: item for item in context["reads"]}
    assert set(costs) == {"README.md", "src/normalize.py"}
    assert all(item["measured"] and item["reads"] == 1 for item in costs.values())
    assert abs(sum(item["tokens"] for item in costs.values()) - 380) <= 1
    assert costs["README.md"]["tokens"] > costs["src/normalize.py"]["tokens"]


def test_reads_without_a_following_request_stay_unmeasured():
    events = [{"tool": "read_file", "arguments": {"path": "notes.md"}, "result": {"text": "x"}}]
    turns = [{"turn": 0, "tool_results": [{"event": 0, "chars": 40}]}]
    metrics = evaluation.context_metrics(
        [{"prompt_tokens": 50, "completion_tokens": 5}], turns, events, None)
    assert metrics["reads"] == [{"path": "notes.md", "reads": 1, "chars": 40,
                                 "tokens": 0, "measured": False}]
    assert metrics["peak_window_fraction"] is None
    assert metrics["above_window_thresholds"] == []


def test_core_instructions_supply_the_installed_digest_to_both_transports():
    """@brief Local and subscription core profiles start from one instruction text."""
    text = evaluation.instructions()
    assert text.startswith(evaluation.SYSTEM)
    assert text.endswith(evaluation.bootstrap_text())
    assert evaluation.core_profile()["system"] == text
    spec = importlib.util.spec_from_file_location(
        "subscription_instructions", ROOT / "02_Tools/evaluate_aegis_subscription.py")
    subscription = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subscription)
    assert subscription.core.instructions() == text


def legacy_payload(tmp_path):
    """@brief A copy of the payload whose journal template predates the State block."""
    payload = tmp_path / "legacy-payload"
    shutil.copytree(evaluation.PAYLOAD, payload,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    template = payload / "templates/task.md"
    text = template.read_text("utf-8").split("\n## State\n", 1)[0]
    template.write_text(text + "\n## Handoff\n\ncurrent:\nstatus:\nnext:\nmust_read:\n"
                        "blockers:\n\n## Stage report\n\nstage:\nresult:\ncurrent:\n"
                        "changed:\nevidence:\nissues:\nnext:\nneeds_user:\n"
                        "spec_compliance:\nimplementation_quality:\nreview_round:\n",
                        encoding="utf-8", newline="\n")
    return payload


@pytest.mark.parametrize("legacy", [False, True], ids=["state", "legacy"])
def test_fixture_state_uses_each_payloads_format_and_scores_alike(tmp_path, legacy):
    """@brief Paired payloads receive the same facts, each in its own record format."""
    payload = legacy_payload(tmp_path) if legacy else evaluation.PAYLOAD
    aegis = evaluation.load_aegis(payload)
    text = aegis.scaffold_template("task.md")
    for waiting in (False, True):
        saved = evaluation.resume_state(text, payload, "build", "Run the focused test",
                                        verdict="approved", review_round="1",
                                        waiting=waiting, evidence="verify exit 1")
        assert ("## State" in saved) is (not legacy)
        assert ("## Handoff" in saved) is legacy
        state = evaluation.recorded_state(aegis, saved, "build")
        assert (state["next"], state["must_read"]) == ("Run the focused test", evaluation.TASK)
        assert (state["result"], state["needs_user"]) == (
            ("paused", "yes") if waiting else ("in_progress", "no"))
        assert (state["spec_compliance"], state["review_round"]) == ("approved", "1")
        assert state["evidence"] == "verify exit 1"
        assert state["synchronized"]
        assert not evaluation.recorded_state(aegis, saved, "validate")["synchronized"]


def test_entry_digest_comes_from_the_evaluated_payload(tmp_path):
    """@brief init installs each payload's own digest; the host contract stays fixed."""
    payload = tmp_path / "payload"
    shutil.copytree(evaluation.PAYLOAD, payload,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    source = (payload / "aegis.py").read_text("utf-8")
    (payload / "aegis.py").write_text(source.replace(
        "## AEGIS workflow\n", "## AEGIS workflow\n\nA distinct entry line.\n", 1),
        encoding="utf-8", newline="\n")
    entry = evaluation.bootstrap_text(payload)
    assert "A distinct entry line." in entry
    assert entry != evaluation.bootstrap_text()
    profiles = evaluation.core_profile(payload), evaluation.core_profile()
    assert profiles[0]["system"].endswith(entry)
    assert profiles[0]["system"] != profiles[1]["system"]
    assert profiles[0]["contract"] == profiles[1]["contract"]
    assert evaluation.ENTRY_PLACEHOLDER in profiles[0]["contract"]


def test_tool_schema_names_each_payloads_commands_but_the_contract_stays_generic(tmp_path):
    """@brief A model sees the writers its payload has; comparisons see one contract."""
    current, legacy = evaluation.core_profile(), evaluation.core_profile(legacy_payload(tmp_path))
    run_command = next(t for t in current["tools"] if t["function"]["name"] == "run_command")
    assert "advance, pause, log, ruling, verdict" in run_command["function"]["description"]
    assert current["contract_tools"] == legacy["contract_tools"] == evaluation.TOOLS
    generic = next(t for t in evaluation.TOOLS if t["function"]["name"] == "run_command")
    assert "--help lists" in generic["function"]["description"]
    assert "a read-only native sandbox does not limit these tools" in " ".join(
        evaluation.SYSTEM.split())


def test_host_offers_only_the_commands_the_fixture_payload_defines(prepared):
    """@brief A writer the payload lacks is unavailable rather than misreported."""
    root, _case, _initial, host = prepared
    assert {"advance", "pause", "log", "ruling", "verdict", "report"} <= set(host.aegis)
    assert set(host.aegis) <= set(evaluation.AEGIS_COMMANDS)
    result = host.call("run_command", {"program": "aegis",
                                       "args": ["log", "TASK-aaaaaaaa", "red", "observed"]})
    assert result["exit_code"] == 0
    assert "red observed" in (root / evaluation.TASK).read_text("utf-8")
    host.aegis = tuple(c for c in host.aegis if c != "log")
    assert "error" in host.call("run_command", {"program": "aegis",
                                                "args": ["log", "TASK-aaaaaaaa", "x"]})


def test_compare_rejects_changed_sampling_and_reports_context_medians(tmp_path):
    before, after = tmp_path / "before", tmp_path / "after"
    manifest = {"model": "m", "scenario_ids": ["case"], "repeats": 1, "top_p": 0.8}
    for root, peak in ((before, 900), (after, 600)):
        evaluation.dump(root / "manifest.json", manifest)
        evaluation.dump(root / "results.json", [{
            "scenario": "case", "repeat": 1, "passed": True, "seconds": 1.0,
            "context": {"peak_prompt_tokens": peak, "total_prompt_tokens": 5000}}])
    outcome = evaluation.compare(before, after)
    assert (outcome["median_peak_prompt_before"], outcome["median_peak_prompt_after"]) == (900, 600)
    server = {"id": "m", "quantization": "Q4_K_M"}
    evaluation.dump(before / "manifest.json", {**manifest, "server_model": {
        **server, "state": "not-loaded"}})
    evaluation.dump(after / "manifest.json", {**manifest, "server_model": {
        **server, "state": "loaded", "loaded_context_length": 65536}})
    assert evaluation.compare(before, after)["automated_regressions"] == []
    evaluation.dump(after / "manifest.json", {**manifest, "top_p": 0.95, "server_model": {
        **server, "state": "loaded"}})
    with pytest.raises(ValueError, match="incomparable controls: top_p"):
        evaluation.compare(before, after)


def test_execute_records_profile_sampling_window_and_sources(tmp_path, monkeypatch):
    """REQ-FUNC-d60b322b: a baseline records every control that shapes its context use."""
    server_reads = []

    def fake_request(url, data, timeout):
        if url.endswith("/v1/models"):
            return {"data": [{"id": "local-test"}]}
        if url.endswith("/api/v0/models"):
            # a just-in-time server unloads idle models and reloads on first use
            server_reads.append(url)
            if len(server_reads) == 1:
                return {"data": [{"id": "local-test", "state": "not-loaded"}]}
            return {"data": [{"id": "local-test", "state": "loaded",
                              "loaded_context_length": 4096}]}
        return reply(content="Stopping.", usage={"prompt_tokens": 1024, "completion_tokens": 8})

    monkeypatch.setattr(evaluation, "request_json", fake_request)
    args = run_args(cases="frame_existing_fix", output=tmp_path / "out", work_dir=tmp_path / "work",
                    profile="core", repeats=1, top_p=0.8, top_k=20, context_window=None,
                    review_timeout=60, reasoning_effort="medium")
    assert evaluation.execute(args) == 1
    manifest = json.loads((args.output / "manifest.json").read_text("utf-8"))
    assert (manifest["profile"], manifest["top_p"], manifest["top_k"],
            manifest["context_window"]) == ("core", 0.8, 20, 4096)
    assert manifest["reasoning_effort"] == "medium"
    assert manifest["system_sha256"] == evaluation.digest(evaluation.instructions().encode())
    assert "05_Software/aegis/evaluations/profiles/installed-entry.json" in manifest["sources"]
    results = json.loads((args.output / "results.json").read_text("utf-8"))
    assert results[0]["context"]["peak_window_fraction"] == 0.25
    assert "Peak prompt" in (args.output / "report.md").read_text("utf-8")
    with zipfile.ZipFile(args.output / "evidence.zip") as bundle:
        assert "harness/05_Software/aegis/evaluations/scenarios.json" in bundle.namelist()


def test_capability_profile_runs_locally_through_the_capability_host(tmp_path, monkeypatch):
    """@brief The local transport exposes capability tools and capability scoring."""
    capabilities, selected = capability_case("diagrams_disabled")
    profile = evaluation.capability_profile()
    root, run_dir = tmp_path / "repo", tmp_path / "run"
    run_dir.mkdir()
    initial = profile["prepare"](root, evaluation.PAYLOAD, selected)
    replies = iter([reply(calls=[tool_call("digest", "candidate_digest", {})]),
                    reply(content="Stopping.")])
    requests = []
    monkeypatch.setattr(evaluation, "request_json",
                        lambda url, data, timeout: requests.append(data) or next(replies))
    result = evaluation.run_case(root, selected, initial, run_args(), run_dir, profile)
    assert result["profile"] == "capabilities"
    assert {t["function"]["name"] for t in requests[0]["tools"]} == {
        t["function"]["name"] for t in capabilities.TOOLS}
    events = json.loads((run_dir / "tools.json").read_text("utf-8"))
    assert events[0]["result"]["candidate"] == evaluation.candidate(root)
    assert "design_saved" in checks(result["evaluation"])
    assert not result["passed"]


def local_review_backend(monkeypatch, bound, verdict="approved", candidate=None):
    """@brief Script reviewer sessions: one digest read, then a final JSON verdict."""
    sessions = []

    def fake_request(url, data, timeout):
        if len(data["messages"]) == 2:
            sessions.append({"system": data["messages"][0]["content"],
                             "tools": {t["function"]["name"] for t in data["tools"]}})
            return reply(calls=[tool_call("digest", "candidate_digest", {})])
        response = {"task": "TASK-aaaaaaaa", "candidate": candidate or bound,
                    "verdict": verdict, "findings": [], "inspected_paths": [],
                    "limitations": []}
        return reply(content="```json\n" + json.dumps(response) + "\n```")

    monkeypatch.setattr(evaluation, "request_json", fake_request)
    return sessions


def test_local_reviewers_run_fresh_sessions_on_one_snapshot(tmp_path, monkeypatch):
    """REQ-FUNC-cbff6478: local roles review one candidate in isolated read-only sessions."""
    capabilities, selected = capability_case("review_enabled_current")
    root, run_dir = tmp_path / "repo", tmp_path / "run"
    run_dir.mkdir()
    initial = capabilities.prepare(root, evaluation.PAYLOAD, selected)
    bound = evaluation.candidate(root)
    sessions = local_review_backend(monkeypatch, bound)
    ledger = []
    delegate = evaluation.local_reviewer(capabilities, run_args(), run_dir, root, initial,
                                         evaluation.files(evaluation.PAYLOAD), ledger)
    for role in capabilities.ROLES:
        result = delegate({"role": role, "task": "TASK-aaaaaaaa", "candidate": bound})
        assert (result["status"], result["verdict"]) == ("completed", "approved")
        assert result["snapshot_unchanged"] and result["digest_reads"] == 1
        evaluation.write(root / evaluation.TASK,
                         (root / evaluation.TASK).read_text("utf-8") + "\nPRIVATE_VERDICT\n")
    snapshot_task = (run_dir / "review-snapshot" / evaluation.TASK).read_text("utf-8")
    assert "PRIVATE_VERDICT" not in snapshot_task
    assert len(sessions) == 2 and sessions[0]["system"] != sessions[1]["system"]
    assert all(s["tools"] <= {"list_files", "read_file", "run_command", "candidate_digest"}
               for s in sessions)
    assert len({entry["thread_id"] for entry in ledger}) == 2
    assert delegate({"role": "aegis-spec-review", "task": "TASK-aaaaaaaa",
                     "candidate": bound})["reused_observation"]
    assert len(sessions) == 2
    with pytest.raises(ValueError, match="round consumed"):
        delegate({"role": "aegis-spec-review", "task": "TASK-aaaaaaaa", "candidate": "changed"})


def test_local_review_with_mismatched_identity_is_not_a_verdict(tmp_path, monkeypatch):
    """REQ-FUNC-cbff6478: a verdict bound to another candidate cannot count as review."""
    capabilities, selected = capability_case("review_enabled_current")
    root, run_dir = tmp_path / "repo", tmp_path / "run"
    run_dir.mkdir()
    initial = capabilities.prepare(root, evaluation.PAYLOAD, selected)
    bound = evaluation.candidate(root)
    local_review_backend(monkeypatch, bound, candidate="stale")
    delegate = evaluation.local_reviewer(capabilities, run_args(), run_dir, root, initial,
                                         evaluation.files(evaluation.PAYLOAD), [])
    result = delegate({"role": "aegis-quality-review", "task": "TASK-aaaaaaaa",
                       "candidate": bound})
    assert result["status"] == "invalid_review_response"
    assert result["verdict"] is None


def test_semantic_checks_read_the_saved_frame_card(tmp_path):
    """@brief Configured predicates grade the saved Frame fields, including bold labels."""
    case = case_named("frame_ambiguous_retention")
    root = tmp_path / "repo"
    initial = evaluation.prepare(root, evaluation.PAYLOAD, case)
    journal = root / ".agentic/tasks/TASK-12345678.md"
    evaluation.write(journal, "# TASK-12345678 - Clean up names\n\nstage: frame\n\n## Frame\n\n"
                     "**Desired outcome:** Remove saved names older than 30 days.\n"
                     "Unknowns:\n- How old counts as old?\n- Must removal be reversible?\n"
                     "\n## Log\n")
    semantic = {c["id"]: c["passed"] for c in evaluation.semantic_checks(root, case, initial)}
    assert semantic == {"age_threshold_open": True, "reversibility_open": True,
                        "no_invented_period": False}
    evaluation.write(journal, journal.read_text("utf-8").replace(
        "older than 30 days", "after an undecided period"))
    assert all(c["passed"] for c in evaluation.semantic_checks(root, case, initial))


@pytest.mark.parametrize("proses,expected", [
    (["For a string serialize_name shall return bytes; for None it shall raise ValueError."],
     False),
    (["serialize_name shall return the UTF-8 bytes.",
      "When given None, serialize_name shall raise ValueError."], True),
    (["serialize_name shall raise ValueError for None.",
      "serialize_name shall raise ValueError for numbers."], False),
])
def test_requirement_split_counts_only_new_requirements(tmp_path, proses, expected):
    """@brief Each independently failing response needs its own new requirement."""
    root = tmp_path / "repo"
    initial = evaluation.prepare(root, evaluation.PAYLOAD, case_named("validate_clean_checkpoint"))
    for index, prose in enumerate(proses):
        evaluation.write(root / f".agentic/requirements/functional/REQ-FUNC-0000000{index}.toml",
                         f'id = "REQ-FUNC-0000000{index}"\nrequirement = {json.dumps(prose)}\n')
    result = evaluation.semantic_checks(root, {"id": "specify_exact_serialization"}, initial)
    assert [check["passed"] for check in result] == [expected]


def test_report_and_compare_show_pass_rates_by_case(tmp_path):
    """@brief Repeats are summarized per case, with strict and semantic passes apart."""
    def run(repeat, passed, semantic):
        return {"scenario": "case", "repeat": repeat, "status": "completed", "passed": passed,
                "seconds": 1.0, "requests": 1, "tool_calls": 0, "evaluation": {"checks": []},
                "semantic_checks": [{"id": "check", "passed": semantic, "detail": ""}],
                "semantic_passed": semantic, "context": {}}

    results = [run(1, True, False), run(2, False, True)]
    assert "| case | 1/2 | 1/2 |" in evaluation.report(results, {"model": "m"})
    before, after = tmp_path / "before", tmp_path / "after"
    manifest = {"model": "m", "scenario_ids": ["case"], "repeats": 2}
    for root, runs in ((before, results), (after, [run(1, True, True), run(2, True, True)])):
        evaluation.dump(root / "manifest.json", manifest)
        evaluation.dump(root / "results.json", runs)
    outcome = evaluation.compare(before, after)
    assert outcome["case_pass_rates"] == {"case": {"before": {"strict": "1/2", "semantic": "1/2"},
                                                   "after": {"strict": "2/2", "semantic": "2/2"}}}
    assert (outcome["semantic_passes_before"], outcome["semantic_passes_after"]) == ("1/2", "2/2")

# END OF FILE
