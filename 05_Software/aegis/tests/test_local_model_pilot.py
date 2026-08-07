#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_local_model_pilot.py
@brief Regression tests for the constrained local-model pilot harness.
@details Verifies requirement AEGIS-WP8-PILOT: untrusted model output has no
         shell authority and only the canonical bounded startup/recovery route
         may be executed by the local harness.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

# CONSTANTS

PILOT_PATH = Path(__file__).parents[1] / "tools" / "local_model_pilot.py"


# LOCAL HELPERS


def _load_pilot_module() -> ModuleType:
    """@brief Load the standalone stdlib pilot harness for focused tests."""
    specification = importlib.util.spec_from_file_location("local_model_pilot", PILOT_PATH)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _valid_tool_response(module: ModuleType) -> dict:
    """@brief Build one OpenAI-compatible response requesting the sole allowed tool."""
    return {
        "choices": [{
            "message": {
                "tool_calls": [{
                    "id": "call-1",
                    "function": {"name": module.BOOTSTRAP_TOOL_NAME, "arguments": "{}"},
                }],
            },
        }],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3},
    }


def _write_bootstrap_files(root: Path) -> list[str]:
    """@brief Create exactly the bounded files named by the synthetic context response."""
    paths = [
        "AGENTS.md",
        ".agentic/skills/agentic-development/SKILL.md",
        ".agentic/skills/agentic-development/reference/intake.md",
        ".agentic/runs/RUN-1/stages/intake/intake.toml",
    ]
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pilot input\n", encoding="utf-8")
    return paths


def _completed(command: list[str], stdout: str) -> subprocess.CompletedProcess[str]:
    """@brief Return a successful completed process using the supplied stdout."""
    return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


# TESTS


@pytest.mark.parametrize(
    "endpoint",
    ("https://127.0.0.1:1234/v1", "http://localhost:1234/v1", "http://192.168.1.4:1234/v1"),
)
def test_loopback_endpoint_validation_rejects_non_contract_urls(endpoint: str) -> None:
    """@brief AEGIS-WP8-PILOT permits only an explicit loopback http /v1 endpoint."""
    pilot = _load_pilot_module()
    with pytest.raises(ValueError):
        pilot.validate_loopback_endpoint(endpoint)


def test_loopback_endpoint_validation_accepts_documented_default() -> None:
    """@brief AEGIS-WP8-PILOT accepts the documented LM Studio loopback default."""
    pilot = _load_pilot_module()
    assert pilot.validate_loopback_endpoint("http://127.0.0.1:1234/v1/") == "http://127.0.0.1:1234/v1"


def test_invalid_model_tool_response_does_not_run_any_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief AEGIS-WP8-PILOT rejects untrusted output before the harness launches a process."""
    pilot = _load_pilot_module()
    monkeypatch.setattr(pilot, "_post_json", lambda *_args: ({"choices": []}, 21, 1))
    calls: list[list[str]] = []

    def execute(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return _completed(command, "")

    observation = pilot._run_model_session(
        "http://127.0.0.1:1234/v1",
        "prism-ml/bonsai-27b",
        tmp_path,
        "RUN-1",
        pilot.PilotProfile(32768, "enabled", 0.0, None),
        "startup",
        1.0,
        execute,
    )

    assert not observation.tool_request_valid
    assert observation.invalid_command_count == 1
    assert observation.failure == "model did not request exactly the one allowed bootstrap tool"
    assert calls == []


def test_bounded_bootstrap_runs_context_and_only_named_recovery(
    tmp_path: Path,
) -> None:
    """@brief AEGIS-WP8-PILOT runs no model-selected shell command during recovery."""
    pilot = _load_pilot_module()
    required_reads = _write_bootstrap_files(tmp_path)
    observation = pilot.SessionObservation("session", "recovery", "now", 1)
    calls: list[list[str]] = []
    context = {
        "required_reads": required_reads,
        "unavailable_current_artifact": {
            "recovery_command": "aegis stage prepare",
        },
    }

    def execute(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[-3:] == ["run", "context", "--json"]:
            return _completed(command, json.dumps(context))
        if command[-3:] == ["stage", "prepare", "--json"]:
            return _completed(command, "{}")
        raise AssertionError(command)

    returned = pilot._run_bounded_bootstrap(tmp_path, observation, execute)

    assert returned == context
    assert [command.action for command in observation.commands] == ["run context", "stage prepare"]
    assert observation.files_read == required_reads
    assert len(calls) == 2
    assert all("graph.json" not in path and "journal.jsonl" not in path for path in observation.files_read)


def test_valid_tool_response_has_no_argument_expansion() -> None:
    """@brief AEGIS-WP8-PILOT accepts only the exact zero-argument bootstrap tool call."""
    pilot = _load_pilot_module()
    response = _valid_tool_response(pilot)
    assert pilot._tool_request_is_valid(response)
    response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = '{"command":"Remove-Item"}'
    assert not pilot._tool_request_is_valid(response)


def test_main_refuses_to_overwrite_existing_pilot_evidence(tmp_path: Path) -> None:
    """@brief AEGIS-WP8-PILOT preserves the first observed attempt for later analysis."""
    pilot = _load_pilot_module()
    output = tmp_path / "pilot.json"
    output.write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        pilot.main(["--model", "prism-ml/bonsai-27b", "--output", str(output)])


def test_fresh_model_request_records_exact_transcript_and_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief AEGIS-WP8-PILOT proves each stage starts from one transcript-empty request."""
    pilot = _load_pilot_module()
    response = _valid_tool_response(pilot)
    monkeypatch.setattr(pilot, "_post_json", lambda *_args: (response, 42, 7))
    monkeypatch.setattr(pilot, "_run_bounded_bootstrap", lambda *_args: {})

    observation = pilot._run_model_session(
        "http://127.0.0.1:1234/v1",
        "prism-ml/bonsai-27b",
        tmp_path,
        "RUN-1",
        pilot.PilotProfile(32768, "enabled", 0.0, None),
        "stage:intake",
        1.0,
    )

    assert observation.outcome_class == "success"
    assert observation.fresh_transcript
    assert observation.prior_transcript_messages == 0
    assert len(observation.api_request["messages"]) == 1
    assert observation.api_request["model"] == "prism-ml/bonsai-27b"
    assert observation.api_request["temperature"] == 0.0
    assert observation.transcript_sha256


def test_context_budget_accepts_request_one_token_under_harness_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief AEGIS-WP8-PILOT permits a request only when its conservative budget fits."""
    pilot = _load_pilot_module()
    monkeypatch.setattr(pilot, "_post_json", lambda *_args: (_valid_tool_response(pilot), 42, 7))
    monkeypatch.setattr(pilot, "_run_bounded_bootstrap", lambda *_args: {})
    initial_profile = pilot.PilotProfile(2000, "enabled", 0.0, None)
    initial = pilot._run_model_session(
        "http://127.0.0.1:1234/v1", "prism-ml/bonsai-27b", tmp_path, "RUN-1", initial_profile,
        "stage:intake", 1.0,
    )
    profile = pilot.PilotProfile(initial.context_budget["combined_token_upper_bound"] + 1, "enabled", 0.0, None)
    observation = pilot._run_model_session(
        "http://127.0.0.1:1234/v1", "prism-ml/bonsai-27b", tmp_path, "RUN-1", profile,
        "stage:intake", 1.0,
    )

    assert observation.outcome_class == "success"
    assert observation.context_budget["within_budget"]
    assert observation.context_budget["context_window_budget"] - observation.context_budget["combined_token_upper_bound"] == 1


def test_context_budget_rejects_before_network_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """@brief AEGIS-WP8-PILOT does not contact LM Studio after an over-budget preflight."""
    pilot = _load_pilot_module()
    calls = 0

    def post_json(*_args: object) -> tuple[dict, int, int]:
        nonlocal calls
        calls += 1
        raise AssertionError("budget-rejected request reached the network")

    monkeypatch.setattr(pilot, "_post_json", post_json)
    observation = pilot._run_model_session(
        "http://127.0.0.1:1234/v1", "prism-ml/bonsai-27b", tmp_path, "RUN-1",
        pilot.PilotProfile(1, "enabled", 0.0, None), "stage:intake", 1.0,
    )

    assert calls == 0
    assert observation.outcome_class == "budget-rejected"
    assert observation.context_budget["within_budget"] is False
    assert observation.correctness["budget_rejected_pre_network"] is True


def test_context_budget_records_exact_payload_and_output_allowance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief AEGIS-WP8-PILOT records the bytes and options used by the guard and API."""
    pilot = _load_pilot_module()
    monkeypatch.setattr(pilot, "_post_json", lambda *_args: (_valid_tool_response(pilot), 42, 7))
    monkeypatch.setattr(pilot, "_run_bounded_bootstrap", lambda *_args: {})
    observation = pilot._run_model_session(
        "http://127.0.0.1:1234/v1", "prism-ml/bonsai-27b", tmp_path, "RUN-1",
        pilot.PilotProfile(32768, "enabled", 0.0, None), "stage:intake", 1.0,
    )

    serialized = observation.request_serialization["exact_json"].encode("utf-8")
    assert observation.api_request["max_tokens"] == pilot.MAX_COMPLETION_TOKENS
    assert observation.context_budget["requested_output_max_tokens"] == pilot.MAX_COMPLETION_TOKENS
    assert observation.context_budget["input_token_upper_bound"] == len(serialized)
    assert observation.request_serialization["bytes"] == len(serialized)
    assert json.loads(observation.request_serialization["exact_json"]) == observation.api_request
    assert observation.correctness["budget_within_harness_limit"] is True
    assert observation.correctness["score"] == observation.correctness["out_of"] == 4


def test_attempt_outcome_is_not_retry_lineage(tmp_path: Path) -> None:
    """@brief AEGIS-WP8-PILOT keeps historical failures distinct from current success."""
    pilot = _load_pilot_module()
    previous = tmp_path / "previous.json"
    previous.write_text(
        json.dumps({"profiles": [{"trials": [{"outcome_class": "timeout"}]}]}), encoding="utf-8"
    )
    chain, lineage = pilot._attempt_lineage([previous])
    current = pilot._current_attempt_outcome({
        "profiles": [{"trials": [{"outcome_class": "success"}, {"outcome_class": "success"}]}],
    })

    assert chain[0]["preserved"]
    assert lineage == {
        "has_prior_attempts": True,
        "prior_attempt_count": 1,
        "follows_prior_failures": True,
        "retry_is_lineage_only": True,
    }
    assert current == "success"


def test_run_pilot_rejects_over_budget_before_discovery_or_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief AEGIS-WP8-PILOT performs no network operation when planning exceeds budget."""
    pilot = _load_pilot_module()
    events: list[str] = []

    def get_json(*_args: object) -> tuple[dict, int, int]:
        events.append("GET")
        raise AssertionError("over-budget pilot reached model discovery")

    def post_json(*_args: object) -> tuple[dict, int, int]:
        events.append("POST")
        raise AssertionError("over-budget pilot reached a completion request")

    monkeypatch.setattr(pilot, "_get_json", get_json)
    monkeypatch.setattr(pilot, "_post_json", post_json)
    result = pilot.run_pilot(
        endpoint="http://127.0.0.1:1234/v1",
        model="prism-ml/bonsai-27b",
        template_root=PILOT_PATH.parents[1] / "template",
        profiles=(pilot.PilotProfile(1, "enabled", 0.0, None),),
        timeout_seconds=1.0,
    )

    assert events == []
    assert result["outcome_class"] == "budget-rejected"
    assert result["outcome_code"] == "budget_rejected"
    assert result["discovery"]["attempted"] is False
    assert result["preflight"] == {
        "completed_before_network": True,
        "all_requests_within_budget": False,
        "planned_request_count": 12,
    }


def test_run_pilot_discovers_then_posts_preflighted_under_budget_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief AEGIS-WP8-PILOT posts only after exact planned requests fit the guard."""
    pilot = _load_pilot_module()
    events: list[str] = []
    posted_serializations: list[str] = []

    def get_json(*_args: object) -> tuple[dict, int, int]:
        events.append("GET")
        return {"data": [{"id": "prism-ml/bonsai-27b"}]}, 45, 3

    def post_json(_endpoint: str, payload: dict, _timeout: float) -> tuple[dict, int, int]:
        events.append("POST")
        posted_serializations.append(pilot._serialize_request_payload(payload).decode("utf-8"))
        return _valid_tool_response(pilot), 42, 7

    monkeypatch.setattr(pilot, "_get_json", get_json)
    monkeypatch.setattr(pilot, "_post_json", post_json)
    result = pilot.run_pilot(
        endpoint="http://127.0.0.1:1234/v1",
        model="prism-ml/bonsai-27b",
        template_root=PILOT_PATH.parents[1] / "template",
        profiles=(pilot.PilotProfile(32768, "enabled", 0.0, None),),
        timeout_seconds=1.0,
    )

    planned = result["profiles"][0]["planned_requests"]
    sessions = [
        session
        for trial in result["profiles"][0]["trials"]
        for session in trial["sessions"]
    ]
    assert events[0] == "GET"
    assert events.count("GET") == 1
    assert events.count("POST") == len(planned) == len(sessions) == 12
    assert posted_serializations == [request["request_serialization"]["exact_json"] for request in planned]
    assert result["discovery"]["attempted"] is True
    assert result["preflight"]["all_requests_within_budget"] is True
    assert all(session["preflight_validation"]["serialized_request_matches_preflight"] for session in sessions)
    assert all(session["context_budget"] == request["context_budget"] for session, request in zip(sessions, planned, strict=True))


# END OF FILE
