#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_capability_evaluation.py
@brief   Verify capability isolation, real-event grading and configuration branches.
@details Offline tests use explicitly synthetic backends, never live model calls.
"""

# IMPORTS
import importlib.util
import json
from pathlib import Path

import pytest

# CONSTANTS
ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("capability_subscription", ROOT / "02_Tools/evaluate_aegis_subscription.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
cap, core = runner.cap, runner.core
CASES = json.loads(cap.SUITE.read_text("utf-8"))["scenarios"]

# HELPERS
def case(name):
    return next(c for c in CASES if c["id"] == name)


@pytest.fixture
def prepared(tmp_path):
    selected = case("review_disabled_no_delegation")
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    return root, selected, initial


def records(root, stage="validate", verdict="disabled"):
    """@brief Supply valid report syntax without claiming any executed proof."""
    p = root / core.TASK
    text = cap.replace_field(p.read_text("utf-8"), "stage", stage)
    text = core.resume_state(text, core.PAYLOAD, stage, "Continue the scoped operation",
                             verdict=verdict, waiting=True, changed=core.TASK)
    core.write(p, text)


# TESTS
@pytest.mark.parametrize("name,args", [
    ("write_file", {"path": ".agentic/context/project.md", "content": "tampered"}),
    ("run_command", {"program": "verify", "args": []}),
    ("run_command", {"program": "aegis", "args": ["anchor", "--task", "TASK-aaaaaaaa"]}),
    ("delegate_review", {"role": "aegis-spec-review", "task": "TASK-aaaaaaaa", "candidate": "x"}),
])
def test_reviewer_cannot_mutate_verify_or_delegate(prepared, name, args):
    """REQ-FUNC-cbff6478: reviewer access is enforced by the tool host."""
    root, _case, initial = prepared
    before = core.files(root)
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD), reviewer=True)
    assert host.call(name, args)["denied"]
    assert core.files(root) == before
    assert host.call("run_command", {"program": "git", "args": ["status", "--short"]})["exit_code"] == 0


def test_disabled_review_never_calls_live_backend(prepared):
    root, _case, initial = prepared
    invoked = []
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD), delegate=lambda a: invoked.append(a))
    result = host.call("delegate_review", {"role": "aegis-spec-review", "task": "TASK-aaaaaaaa", "candidate": core.candidate(root)})
    assert result["denied"] and not invoked


def test_review_rejects_wrong_candidate_before_launch(tmp_path):
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, case("review_enabled_current"))
    invoked = []
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD), delegate=lambda a: invoked.append(a))
    assert "error" in host.call("delegate_review", {"role": "aegis-spec-review", "task": "TASK-aaaaaaaa", "candidate": "stale"})
    assert not invoked


def test_fresh_review_snapshots_hide_other_verdicts_and_reject_new_round(tmp_path, monkeypatch):
    """REQ-FUNC-cbff6478: the two roles see one candidate, never each other's output."""
    root, folder = tmp_path / "repo", tmp_path / "coordinator"
    initial = cap.prepare(root, core.PAYLOAD, case("review_enabled_current"))
    folder.mkdir()
    config = {"folder": str(folder), "repo": str(root), "payload": str(core.PAYLOAD), "initial": initial, "settings": {}}
    supplied = core.candidate(root)
    observations = []

    def fake_cli(target, snapshot, payload, initial, settings, prompt, system, **kwargs):
        target.mkdir(parents=True)
        observations.append((snapshot, prompt, system))
        assert "PRIVATE_VERDICT" not in (snapshot / core.TASK).read_text("utf-8") + prompt + system
        core.dump(target / "final.txt", {"task": "TASK-aaaaaaaa", "candidate": supplied,
            "verdict": "changes_required", "findings": ["PRIVATE_VERDICT"], "inspected_paths": [], "limitations": []})
        core.dump(target / "tools.json", [])
        return {"status": "completed", "thread_id": str(len(observations)), "error": "", "output_tokens": 1, "reasoning_tokens": 0}

    monkeypatch.setattr(runner, "run_cli", fake_cli)
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    for role in cap.ROLES:
        result = runner.launch_review(config, {"role": role, "candidate": supplied})
        assert result["snapshot_unchanged"]
        core.write(root / core.TASK, (root / core.TASK).read_text("utf-8") + "\nPRIVATE_VERDICT\n")
    assert len(observations) == 2 and observations[0][0] == observations[1][0]
    assert observations[0][2] != observations[1][2]
    assert runner.launch_review(config, {"role": "aegis-spec-review", "candidate": supplied})["reused_observation"]
    assert len(observations) == 2
    with pytest.raises(ValueError, match="round consumed"):
        runner.launch_review(config, {"role": "aegis-spec-review", "candidate": "changed"})


def test_authored_verdicts_without_sessions_cannot_pass(tmp_path):
    selected = case("review_enabled_current")
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    records(root, verdict="approved")
    grade = cap.score(root, selected, initial, [], core.PAYLOAD, [], "Both reviewers approved.")
    assert not next(c["passed"] for c in grade["checks"] if c["id"] == "two_real_review_sessions")
    assert not grade["passed"]


@pytest.mark.parametrize("name", ["diagrams_disabled", "diagrams_empty_types", "diagrams_skipped_design"])
def test_disabled_empty_and_skipped_diagrams_cannot_create_artifact(tmp_path, name):
    """REQ-FUNC-ee1d2096: configuration and design applicability control drawing."""
    selected = case(name)
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    records(root, "design")
    core.write(root / ".agentic/tasks/diagram_TASK-aaaaaaaa.md", "```mermaid\nflowchart LR\nA-->B\n```\n")
    grade = cap.score(root, selected, initial, [], core.PAYLOAD, [], "")
    assert not next(c["passed"] for c in grade["checks"] if c["id"] == "no_unrequested_diagrams")


def test_diagram_claim_without_file_or_link_is_not_generation(tmp_path):
    selected = case("diagrams_enabled_types")
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    records(root, "design")
    grade = cap.score(root, selected, initial, [], core.PAYLOAD, [], "I generated all requested diagrams.")
    assert not next(c["passed"] for c in grade["checks"] if c["id"] == "diagram_artifact_and_link")


def test_real_diagram_artifact_and_summary_are_observed(tmp_path):
    """REQ-UX-b0bd0225: generated content is shown after the actual summary."""
    selected = case("diagrams_enabled_types")
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    records(root, "design")
    p = root / core.TASK
    core.write(p, core.section(p.read_text("utf-8"), "Design", "Proposed API, worker and job store.\nDiagrams: [diagram_TASK-aaaaaaaa.md](diagram_TASK-aaaaaaaa.md)"))
    blocks = ["flowchart LR\nclassDef added fill:#eee\nclassDef changed fill:#ddd\nclassDef removed stroke-dasharray:4 3\napi[\"src/api.py\"]:::added --> worker[\"src/worker.py\"]:::added",
              "sequenceDiagram\nparticipant API\nparticipant Worker\nAPI->>Worker: enqueue name",
              "stateDiagram-v2\nqueued --> running\nrunning --> done\nrunning --> failed"]
    artifact = "\n\n".join("```mermaid\n" + b + "\n```" for b in blocks)
    core.write(root / ".agentic/tasks/diagram_TASK-aaaaaaaa.md", artifact)
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD))
    summary = host.call("run_command", {"program": "aegis", "args": ["summary", "TASK-aaaaaaaa"]})["stdout"].strip()
    grade = cap.score(root, selected, initial, host.events, core.PAYLOAD, [], summary + "\n\n" + artifact)
    assert grade["passed"], [c for c in grade["checks"] if not c["passed"]]


def test_context_update_requires_both_files_preservation_and_post_edit_proof(tmp_path):
    """REQ-FUNC-d60b322b: stale context cannot be hidden by earlier green proof."""
    selected = case("validate_stale_context")
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD))
    assert host.call("run_command", {"program": "aegis", "args": ["check", "--task", "TASK-aaaaaaaa", "--strict", "--run"]})["exit_code"] == 0
    records(root)
    core.write(root / ".agentic/context/project.md", "# Project\nTrim and lowercase names.\n\n" + initial["context_notes"])
    core.write(root / ".agentic/context/environment.md", "# Environment\nRun python verify.py.\n\n" + initial["context_notes"])
    grade = cap.score(root, selected, initial, host.events, core.PAYLOAD, [], "")
    checks = {c["id"]: c["passed"] for c in grade["checks"]}
    assert checks["project.md_updated"] and checks["environment.md_updated"]
    assert checks["project.md_unrelated_notes_preserved"] and checks["environment.md_unrelated_notes_preserved"]
    assert not checks["fresh_successful_proof"]
    assert host.call("run_command", {"program": "aegis", "args": ["check", "--task", "TASK-aaaaaaaa", "--strict", "--run"]})["exit_code"] == 0
    grade = cap.score(root, selected, initial, host.events, core.PAYLOAD, [], "")
    assert next(c["passed"] for c in grade["checks"] if c["id"] == "fresh_successful_proof")


def test_autopilot_fixture_keeps_policy_and_explicit_stop_distinct(tmp_path):
    """REQ-UX-b0bd0225: automatic transition and explicit stop are distinct cases."""
    for name, transition in [("autopilot_design_transition", True), ("autopilot_explicit_stage_stop", False)]:
        selected = case(name)
        root = tmp_path / name
        initial = cap.prepare(root, core.PAYLOAD, selected)
        assert cap.tomllib.loads((root / ".agentic/aegis.toml").read_text())["interaction"]["autopilot"] is True
        records(root, "build" if transition else "design")
        grade = cap.score(root, selected, initial, [], core.PAYLOAD, [], "")
        assert next(c["passed"] for c in grade["checks"] if c["id"] == "expected_stage")


@pytest.mark.parametrize("status,message,delay", [
    ("provider_error", "HTTP429 Too Many Requests", 60),
    ("provider_error", "429 Retry-After: 90", 90),
    ("provider_error", "429 insufficient_quota", None),
    ("provider_error", "429 weekly usage limit", None),
    ("completed", "incorrect semantic answer", None),
    ("run_timeout", "timeout", None),
])
def test_backoff_never_retries_semantic_failure_or_quota(status, message, delay):
    assert runner.retry_delay(status, message, 0) == delay

@pytest.mark.parametrize("name", ["specify_exact_serialization", "build_existing_contract", "deliver_requires_approval", "deliver_changed_after_proof", "adopt_existing_component"])
def test_stage_fixtures_prepare_without_claimed_model_execution(tmp_path, name):
    """@brief Each additional stage starts with real, parseable repository state."""
    selected = case(name)
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    parsed = core.load_aegis(core.PAYLOAD).parse_journal((root / core.TASK).read_text("utf-8"))
    # a payload without a deliver stage presents the validated task at the end of validate
    expected = (cap.stages.closing_stage(core.PAYLOAD) if selected["kind"] == "deliver"
                else selected["stage"])
    assert parsed["header"]["stage"] == expected == initial["fixture_stage"]
    grade = cap.score(root, selected, initial, [], core.PAYLOAD, [], "")
    assert not grade["passed"]


def test_build_host_rejects_executable_injection_and_executes_red_green(tmp_path):
    """@brief A real Build edit is bounded by AST, not by model assurances."""
    selected = case("build_existing_contract")
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, selected)
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD))
    for content in ["import os\nos.system('echo unsafe')", "def normalize_name(value):\n    return eval(value)\n"]:
        assert host.call("write_file", {"path": "src/normalize.py", "content": content})["denied"]
    assert host.call("run_command", {"program": "verify", "args": []})["exit_code"] != 0
    assert host.call("write_file", {"path": "src/normalize.py", "content": "def normalize_name(value):\n    return value.strip().lower()\n"})["written_chars"]
    assert host.call("run_command", {"program": "verify", "args": []})["exit_code"] == 0
    assert host.call("write_file", {"path": "verify.py", "content": "pass"})["denied"]
    assert host.call("write_file", {"path": "../outside.py", "content": "pass"})["denied"]


def test_requirement_scaffold_command_is_literal_and_bounded(tmp_path):
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, case("specify_exact_serialization"))
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD))
    assert host.call("run_command", {"program": "aegis", "args": ["req", "functional", "Serialize names"]})["exit_code"] == 0
    assert host.call("run_command", {"program": "aegis", "args": ["req", "../escape", "Invalid"]})["denied"]
    assert host.call("run_command", {"program": "aegis", "args": ["req", "--help"]})["exit_code"] == 0
    lookup = host.call("run_command", {"program": "aegis", "args": ["req", "func", "REQ-FUNC-1", "extra"]})
    assert lookup.get("capability_unavailable") is True and lookup.get("denied") is False
    # the evaluated CLI, not the host, decides which category names it accepts
    assert host.call("run_command", {"program": "aegis", "args": ["req", "func", "Trim names"]})["exit_code"] == 0

def test_review_reference_accepts_brief_and_keeps_identity_guards(tmp_path):
    """REQ-FUNC-cbff6478: text references select one canonical task without weakening binding."""
    root = tmp_path / "repo"
    initial = cap.prepare(root, core.PAYLOAD, case("review_enabled_current"))
    calls = []
    host = cap.CapabilityHost(root, initial, core.files(core.PAYLOAD),
        delegate=lambda a: calls.append(a) or {"synthetic_test_backend": True})
    arguments = {"role": "aegis-spec-review", "candidate": core.candidate(root),
        "task": "TASK-aaaaaaaa: independently inspect the accepted scope"}
    assert host.call("delegate_review", arguments)["synthetic_test_backend"]
    assert calls == [{**arguments, "task": "TASK-aaaaaaaa"}]
    assert host.events[-1]["arguments"]["task"] == arguments["task"]
    for reference in ["TASK-bbbbbbbb", "TASK-aaaaaaaa: compare TASK-bbbbbbbb", "not a task"]:
        assert "task reference" in host.call("delegate_review", {**arguments, "task": reference})["error"]
    assert "candidate digest" in host.call("delegate_review", {**arguments, "candidate": "stale"})["error"]
    assert len(calls) == 1


# END OF FILE
