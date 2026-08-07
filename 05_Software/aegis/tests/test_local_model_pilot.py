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


# END OF FILE
