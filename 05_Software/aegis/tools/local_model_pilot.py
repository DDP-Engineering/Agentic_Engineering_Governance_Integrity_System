#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file local_model_pilot.py
@brief Run bounded fresh-session AEGIS trials through a local OpenAI API.
@details Creates disposable copies of the generic AEGIS payload, gives each
         model session exactly one bootstrap tool, and records observed API and
         command telemetry. Model text is never interpreted as shell input.
"""

# IMPORTS

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

# CONSTANTS

DEFAULT_ENDPOINT = "http://127.0.0.1:1234/v1"
DEFAULT_CONTEXT_PROFILES = (32768, 131072)
MAX_RESPONSE_EVIDENCE_BYTES = 32768
MAX_COMPLETION_TOKENS = 1024
BOOTSTRAP_TOOL_NAME = "run_bounded_aegis_bootstrap"
FULL_WORKFLOW_STAGES = ("intake", "alignment", "requirement", "design", "check", "implementation", "validation", "delivery")
QUICK_WORKFLOW_STAGES = ("intake", "implementation", "validation", "delivery")
ALLOWED_AEGIS_ACTIONS = frozenset({
    "run start", "run context", "stage prepare", "stage show", "stage add", "stage apply", "stage close",
    "check create", "check register", "check prepare", "check record", "check run", "verify run",
    "delivery report",
})


# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class PilotProfile:
    """@brief One requested local-model context profile."""

    context_window: int
    thinking: str
    temperature: float
    seed: int | None
    context_claim: str = "harness-enforced budget"


@dataclass
class CommandObservation:
    """@brief One harness-owned AEGIS command observation."""

    action: str
    argv: list[str]
    exit_code: int
    stdout_bytes: int
    stderr_bytes: int
    latency_ms: int
    stdout_evidence: str
    stderr_evidence: str


@dataclass
class SessionObservation:
    """@brief Raw, non-inferred evidence from one fresh model session."""

    session_id: str
    scenario: str
    started_at: str
    prompt_bytes: int
    transcript_sha256: str = ""
    fresh_transcript: bool = True
    prior_transcript_messages: int = 0
    api_request: dict[str, Any] = field(default_factory=dict)
    request_serialization: dict[str, Any] = field(default_factory=dict)
    context_budget: dict[str, Any] = field(default_factory=dict)
    preflight_validation: dict[str, Any] = field(default_factory=dict)
    response_bytes: int | None = None
    latency_ms: int | None = None
    model_usage: dict[str, Any] | None = None
    tool_request_valid: bool = False
    invalid_command_count: int = 0
    response_evidence: list[dict[str, Any]] = field(default_factory=list)
    commands: list[CommandObservation] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    bootstrap_bytes: int | None = None
    bootstrap_context_bytes: int | None = None
    stage_apply_attempts: int = 0
    stage_close_attempts: int = 0
    route_backs: int = 0
    waivers: list[str] = field(default_factory=list)
    human_interventions: list[str] = field(default_factory=list)
    final_evidence_state: str = "not executed; bootstrap-only pilot"
    final_invariant_state: str = "not executed; bootstrap-only pilot"
    correctness: dict[str, Any] = field(default_factory=dict)
    failure: str | None = None
    outcome_class: str = "abandoned-attempt"


# LOCAL HELPERS


def _utc_now() -> str:
    """@brief Return a stable ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def validate_loopback_endpoint(endpoint: str) -> str:
    """
    @brief      Validate the single local OpenAI-compatible API base URL.
    @param[in]  endpoint Candidate endpoint URL.
    @return     Normalized endpoint without a trailing slash.
    @exception  ValueError If the endpoint is non-loopback or not rooted at /v1.
    """
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or not parsed.hostname or parsed.query or parsed.fragment:
        raise ValueError("endpoint must be an http loopback OpenAI-compatible base URL")
    try:
        is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError as exc:
        raise ValueError("endpoint hostname must be a loopback IP address") from exc
    if not is_loopback or parsed.path.rstrip("/") != "/v1":
        raise ValueError("endpoint must be a loopback address with the /v1 base path")
    return endpoint.rstrip("/")


def _safe_response_evidence(payload: Any) -> dict[str, Any]:
    """@brief Bound the persisted API response evidence without parsing its text as instructions."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(encoded) <= MAX_RESPONSE_EVIDENCE_BYTES:
        return {"truncated": False, "payload": payload}
    return {
        "truncated": True,
        "response_bytes": len(encoded),
        "prefix_utf8": encoded[:MAX_RESPONSE_EVIDENCE_BYTES].decode("utf-8", errors="replace"),
    }


def _bounded_text(text: str) -> str:
    """@brief Preserve command output evidence without allowing an unbounded artifact."""
    encoded = text.encode("utf-8")
    if len(encoded) <= MAX_RESPONSE_EVIDENCE_BYTES:
        return text
    return encoded[:MAX_RESPONSE_EVIDENCE_BYTES].decode("utf-8", errors="replace")


def _serialize_request_payload(payload: dict[str, Any]) -> bytes:
    """@brief Serialize the exact request payload with one stable UTF-8 representation."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _context_budget(payload: dict[str, Any], context_window: int) -> tuple[dict[str, Any], bytes]:
    """
    @brief Calculate a tokenizer-independent conservative request budget.
    @details UTF-8 byte count is an upper bound on input tokens because each
             tokenizer token consumes at least one encoded byte. It is
             deliberately conservative and is not a claim about LM Studio's
             native context-window enforcement.
    """
    serialized = _serialize_request_payload(payload)
    output_allowance = payload.get("max_tokens")
    if not isinstance(output_allowance, int) or output_allowance < 0:
        raise ValueError("pilot request requires a non-negative integer max_tokens")
    input_upper_bound = len(serialized)
    combined_upper_bound = input_upper_bound + output_allowance
    return {
        "schema": "utf8-byte-input-upper-bound-plus-max-tokens-v1",
        "input_measurement": "serialized exact request UTF-8 byte count",
        "input_token_upper_bound": input_upper_bound,
        "requested_output_max_tokens": output_allowance,
        "combined_token_upper_bound": combined_upper_bound,
        "context_window_budget": context_window,
        "within_budget": combined_upper_bound <= context_window,
        "native_context_enforcement": "not claimed; preflight is harness-enforced only",
    }, serialized


def _model_request_payload(model: str, repo_root: Path, run_id: str, profile: PilotProfile) -> dict[str, Any]:
    """@brief Build the complete fixed API request for one fresh stage transcript."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": _model_prompt(repo_root, run_id, profile)}],
        "tools": _tool_definition(),
        "tool_choice": "required",
        "temperature": profile.temperature,
        "max_tokens": MAX_COMPLETION_TOKENS,
    }
    if profile.seed is not None:
        payload["seed"] = profile.seed
    return payload


def _request_preflight(
    model: str,
    repo_root: Path,
    run_id: str,
    profile: PilotProfile,
    scenario: str,
) -> dict[str, Any]:
    """@brief Record one exact, non-network request preflight for a planned stage."""
    payload = _model_request_payload(model, repo_root, run_id, profile)
    budget, serialized = _context_budget(payload, profile.context_window)
    return {
        "scenario": scenario,
        "run_id": run_id,
        "api_request": json.loads(serialized),
        "request_serialization": {
            "encoding": "utf-8",
            "exact_json": serialized.decode("utf-8"),
            "sha256": hashlib.sha256(serialized).hexdigest(),
            "bytes": len(serialized),
        },
        "context_budget": budget,
    }


def _post_json(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> tuple[dict[str, Any], int, int]:
    """
    @brief      POST one JSON request and preserve reported API output exactly.
    @return     Parsed response, response bytes, and elapsed milliseconds.
    @exception  RuntimeError If the local endpoint cannot return JSON successfully.
    """
    request = Request(
        f"{endpoint}/chat/completions",
        data=_serialize_request_payload(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read()[:MAX_RESPONSE_EVIDENCE_BYTES].decode("utf-8", errors="replace")
        raise RuntimeError(f"local endpoint returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"local endpoint connection failed: {exc.reason}") from exc
    elapsed = round((time.perf_counter() - started) * 1000)
    try:
        return json.loads(raw), len(raw), elapsed
    except json.JSONDecodeError as exc:
        raise RuntimeError("local endpoint returned non-JSON content") from exc


def _get_json(endpoint: str, resource: str, timeout_seconds: float) -> tuple[dict[str, Any], int, int]:
    """@brief Read one known OpenAI-compatible endpoint without discovery scanning."""
    request = Request(f"{endpoint}/{resource.lstrip('/')}", method="GET")
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read()[:MAX_RESPONSE_EVIDENCE_BYTES].decode("utf-8", errors="replace")
        raise RuntimeError(f"local endpoint returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"local endpoint connection failed: {exc.reason}") from exc
    elapsed = round((time.perf_counter() - started) * 1000)
    try:
        return json.loads(raw), len(raw), elapsed
    except json.JSONDecodeError as exc:
        raise RuntimeError("local endpoint returned non-JSON content") from exc


def _tool_definition() -> list[dict[str, Any]]:
    """@brief Return the sole tool exposed to untrusted model output."""
    return [{
        "type": "function",
        "function": {
            "name": BOOTSTRAP_TOOL_NAME,
            "description": "Run the fixed bounded AEGIS startup/recovery sequence.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    }]


def _tool_request_is_valid(response: dict[str, Any]) -> bool:
    """@brief Accept only exactly one zero-argument request for the fixed bootstrap tool."""
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        return False
    message = choices[0].get("message")
    calls = message.get("tool_calls") if isinstance(message, dict) else None
    if not isinstance(calls, list) or len(calls) != 1:
        return False
    function = calls[0].get("function") if isinstance(calls[0], dict) else None
    if not isinstance(function, dict) or function.get("name") != BOOTSTRAP_TOOL_NAME:
        return False
    try:
        return json.loads(function.get("arguments", "")) == {}
    except json.JSONDecodeError:
        return False


def _run_aegis(
    repo_root: Path,
    arguments: list[str],
    execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[CommandObservation, str]:
    """
    @brief      Run one explicitly allowlisted AEGIS command from the harness.
    @param[in]  repo_root Disposable repository owning the embedded CLI.
    @param[in]  arguments Fixed AEGIS argument sequence selected by the harness.
    @return     Observation and stdout text.
    @exception  ValueError If the harness attempts a non-allowlisted action.
    """
    action = " ".join(arguments[:2])
    if action not in ALLOWED_AEGIS_ACTIONS:
        raise ValueError(f"pilot harness action is not allowlisted: {action}")
    cli_source = repo_root / ".agentic" / "cli" / "src"
    environment = {**os.environ, "PYTHONPATH": str(cli_source)}
    command = [sys.executable, "-B", "-m", "aegis", *arguments]
    started = time.perf_counter()
    completed = execute(
        command,
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = round((time.perf_counter() - started) * 1000)
    observation = CommandObservation(
        action=action,
        argv=command,
        exit_code=completed.returncode,
        stdout_bytes=len(completed.stdout.encode("utf-8")),
        stderr_bytes=len(completed.stderr.encode("utf-8")),
        latency_ms=elapsed,
        stdout_evidence=_bounded_text(completed.stdout),
        stderr_evidence=_bounded_text(completed.stderr),
    )
    return observation, completed.stdout


def _new_disposable_repository(template_root: Path, destination: Path) -> None:
    """@brief Copy the generic payload into a new, empty disposable pilot repository."""
    if destination.exists():
        raise ValueError(f"disposable pilot repository already exists: {destination}")
    shutil.copytree(template_root, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


def _parse_context(output: str) -> dict[str, Any]:
    """@brief Parse a successful JSON context response from the fixed CLI command."""
    try:
        context = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("aegis run context did not emit JSON") from exc
    if context.get("status") not in (None, "ok"):
        raise RuntimeError(f"aegis run context failed: {context}")
    return context


def _run_bounded_bootstrap(
    repo_root: Path,
    observation: SessionObservation,
    execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """
    @brief Run the canonical context/recovery sequence using only fixed commands.
    @details `stage prepare` runs only when the context explicitly names it as
             recovery, preserving applied forms and the normal fresh-session contract.
    """
    context_command, output = _run_aegis(repo_root, ["run", "context", "--json"], execute)
    observation.commands.append(context_command)
    if context_command.exit_code:
        raise RuntimeError(f"aegis run context failed with exit code {context_command.exit_code}")
    context = _parse_context(output)
    required_reads = context.get("required_reads")
    if not isinstance(required_reads, list) or not all(isinstance(item, str) for item in required_reads):
        raise RuntimeError("aegis run context returned invalid required_reads")
    forbidden = [path for path in required_reads if path.endswith("graph.json") or path.endswith("journal.jsonl")]
    if forbidden:
        raise RuntimeError(f"aegis context exposed forbidden recovery inputs: {forbidden}")
    for relative_path in required_reads:
        source = repo_root / relative_path
        if not source.is_file():
            raise RuntimeError(f"declared bootstrap input is not readable: {relative_path}")
        source.read_bytes()
        observation.files_read.append(relative_path)
    context_bytes = len(output.encode("utf-8"))
    observation.bootstrap_context_bytes = context_bytes
    observation.bootstrap_bytes = context_bytes + sum(
        len((repo_root / relative_path).read_bytes()) for relative_path in required_reads
    )
    unavailable = context.get("unavailable_current_artifact")
    recovery = unavailable.get("recovery_command") if isinstance(unavailable, dict) else None
    if recovery == "aegis stage prepare":
        prepare_command, _ = _run_aegis(repo_root, ["stage", "prepare", "--json"], execute)
        observation.commands.append(prepare_command)
        if prepare_command.exit_code:
            raise RuntimeError(f"aegis stage prepare failed with exit code {prepare_command.exit_code}")
    elif recovery == "aegis stage show":
        show_command, _ = _run_aegis(repo_root, ["stage", "show", "--json"], execute)
        observation.commands.append(show_command)
        if show_command.exit_code:
            raise RuntimeError(f"aegis stage show failed with exit code {show_command.exit_code}")
    elif recovery is not None:
        raise RuntimeError(f"unsupported bounded recovery command: {recovery}")
    return context


def _start_trial_run(
    repo_root: Path,
    kind: str,
    quick: bool,
    execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    """@brief Start one fixed full or quick trial run and return its AEGIS run ID."""
    command, output = _run_aegis(
        repo_root,
        ["run", "start", kind, *( ["--quick"] if quick else []), "--json"],
        execute,
    )
    if command.exit_code:
        raise RuntimeError(f"aegis run start failed with exit code {command.exit_code}")
    try:
        run_id = json.loads(output)["run_id"]
    except (KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError("aegis run start did not return a run ID") from exc
    if not isinstance(run_id, str):
        raise RuntimeError("aegis run start returned a non-string run ID")
    return run_id


def _prepare_trial(
    template_root: Path,
    destination: Path,
    kind: str,
    quick: bool,
) -> tuple[list[CommandObservation], str]:
    """@brief Create one local disposable run before any model-network activity."""
    _new_disposable_repository(template_root, destination)
    setup = _initialize_fixture_repository(destination)
    return setup, _start_trial_run(destination, kind, quick)


def _command_json(
    repo_root: Path,
    arguments: list[str],
    observation: SessionObservation | None = None,
    *,
    allow_failure: bool = False,
) -> dict[str, Any]:
    """@brief Run one fixed AEGIS command and retain its complete bounded observation."""
    command, output = _run_aegis(repo_root, [*arguments, "--json"])
    if observation is not None:
        observation.commands.append(command)
    if command.exit_code and not allow_failure:
        raise RuntimeError(f"aegis {' '.join(arguments)} failed with exit code {command.exit_code}")
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"aegis {' '.join(arguments)} did not emit JSON") from exc


def _replace_exact(path: Path, replacements: dict[str, str]) -> None:
    """@brief Apply one fixed, auditable set of substitutions to a disposable form."""
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise RuntimeError(f"expected one form value {old!r} in {path}")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")


def _initialize_fixture_repository(repo_root: Path) -> list[CommandObservation]:
    """@brief Create a deterministic stale-state fixture and its local Git baseline."""
    source = repo_root / "src" / "pilot_state.py"
    check = repo_root / "tests" / "check_pilot_state.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    check.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("STATE = 'stale'\n", encoding="utf-8", newline="\n")
    check.write_text(
        "from pathlib import Path\nimport sys\n\n"
        "def test_pilot_state() -> None:\n"
        "    assert \"repaired\" in Path(\"src/pilot_state.py\").read_text(encoding=\"utf-8\")\n\n"
        "if __name__ == \"__main__\":\n"
        "    try:\n"
        "        test_pilot_state()\n"
        "    except AssertionError:\n"
        "        sys.exit(1)\n",
        encoding="utf-8",
        newline="\n",
    )
    workflow = repo_root / ".agentic" / "workflow.toml"
    _replace_exact(workflow, {'check_execution = "external"': 'check_execution = "managed"'})
    observations: list[CommandObservation] = []
    for command in (
        ["git", "init", "--quiet", "--initial-branch=main"],
        ["git", "config", "user.name", "AEGIS Pilot"],
        ["git", "config", "user.email", "aegis-pilot@example.invalid"],
        ["git", "add", "."],
        ["git", "commit", "--quiet", "-m", "pilot baseline"],
    ):
        started = time.perf_counter()
        completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False)
        observations.append(CommandObservation(
            action="fixture " + command[0], argv=command, exit_code=completed.returncode,
            stdout_bytes=len(completed.stdout.encode("utf-8")), stderr_bytes=len(completed.stderr.encode("utf-8")),
            latency_ms=round((time.perf_counter() - started) * 1000),
            stdout_evidence=_bounded_text(completed.stdout), stderr_evidence=_bounded_text(completed.stderr),
        ))
        if completed.returncode:
            raise RuntimeError(f"fixture command failed: {' '.join(command)}")
    return observations


def _form_path(repo_root: Path, run_id: str, stage: str) -> Path:
    """@brief Resolve the single generated form for a known non-collection pilot stage."""
    return repo_root / ".agentic" / "runs" / run_id / "stages" / stage / f"{stage}.toml"


def _evidence_id(payload: dict[str, Any]) -> str:
    """@brief Extract exactly one CLI-created evidence ID from a managed check result."""
    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != 1 or not isinstance(evidence[0], dict):
        raise RuntimeError("managed check did not return exactly one evidence record")
    identifier = evidence[0].get("id")
    if not isinstance(identifier, str) or not identifier:
        raise RuntimeError("managed check evidence has no ID")
    return identifier


def _required_artifact(payload: dict[str, Any], command: str) -> str:
    """@brief Extract a required artifact or turn a failed command into evidence."""
    artifact = payload.get("artifact")
    if isinstance(artifact, str) and artifact:
        return artifact
    detail = payload.get("error") or payload.get("status") or "no diagnostic output"
    raise RuntimeError(f"{command} returned no artifact: {detail}")


def _fresh_stage_session(
    endpoint: str,
    model: str,
    repo_root: Path,
    run_id: str,
    profile: PilotProfile,
    stage: str,
    timeout_seconds: float,
    preflight: dict[str, Any] | None = None,
) -> SessionObservation:
    """@brief Execute one transcript-empty model request for exactly one current stage."""
    return _run_model_session(
        endpoint, model, repo_root, run_id, profile, f"stage:{stage}", timeout_seconds, preflight=preflight
    )


def _apply_and_close(repo_root: Path, session: SessionObservation) -> dict[str, Any]:
    """@brief Import one fixed form and record the standing-authorized human gate."""
    _command_json(repo_root, ["stage", "apply"], session)
    session.stage_apply_attempts += 1
    closed = _command_json(
        repo_root, ["stage", "close", "--approver", "AEGIS Pilot <aegis-pilot@example.invalid>"], session
    )
    session.stage_close_attempts += 1
    session.human_interventions.append("standing user-authorized fixed approval at stage close")
    return closed


def _run_full_change_workflow(
    endpoint: str,
    model: str,
    repo_root: Path,
    profile: PilotProfile,
    timeout_seconds: float,
    setup: list[CommandObservation] | None = None,
    run_id: str | None = None,
    preflights: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """@brief Complete a fixed full change workflow with one fresh model request per stage."""
    if setup is None or run_id is None:
        setup = _initialize_fixture_repository(repo_root)
        started = _command_json(repo_root, ["run", "start", "change"])
        run_id = str(started["run_id"])
    sessions: list[SessionObservation] = []
    requirement_id = ""
    check_id = ""
    green_evidence = ""
    verification_path = ""
    try:
        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "intake", timeout_seconds, (preflights or {}).get("stage:intake"))
        sessions.append(session)
        _replace_exact(_form_path(repo_root, run_id, "intake"), {'statement = ""': 'statement = "Repair pilot state"'})
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "alignment", timeout_seconds, (preflights or {}).get("stage:alignment"))
        sessions.append(session)
        _replace_exact(_form_path(repo_root, run_id, "alignment"), {
            'understanding = ""': 'understanding = "The fixture starts stale and must become repaired"',
            "in_scope = []": 'in_scope = ["src/pilot_state.py"]',
            "acceptance_criteria = []": 'acceptance_criteria = ["check_pilot_state exits zero after repair"]',
            "planned_paths = []": 'planned_paths = ["src/pilot_state.py", "tests/check_pilot_state.py"]',
        })
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "requirement", timeout_seconds, (preflights or {}).get("stage:requirement"))
        sessions.append(session)
        requirement_forms = sorted((repo_root / ".agentic" / "runs" / run_id / "stages" / "requirement").glob("requirement-*.toml"))
        if len(requirement_forms) != 1:
            raise RuntimeError("prepared requirement stage did not contain exactly one form")
        requirement_form = requirement_forms[0]
        requirement_text = requirement_form.read_text(encoding="utf-8")
        identifier = re.search(r'^id = "([^"]+)"$', requirement_text, flags=re.MULTILINE)
        if identifier is None:
            raise RuntimeError("requirement form did not contain an ID")
        requirement_id = identifier.group(1)
        _replace_exact(requirement_form, {
            'requirement = ""': 'requirement = "The pilot state shall report repaired after the bounded change"',
            'rationale = ""': 'rationale = "The controlled check needs one observable contract"',
            'verification = ""': 'verification = "python tests/check_pilot_state.py"',
            "affected_paths = []": 'affected_paths = ["src/pilot_state.py"]',
            "linked_tests = []": 'linked_tests = ["tests/check_pilot_state.py::test_pilot_state"]',
        })
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "design", timeout_seconds, (preflights or {}).get("stage:design"))
        sessions.append(session)
        design = _form_path(repo_root, run_id, "design")
        _replace_exact(design, {
            "cited_requirement_ids = []": f'cited_requirement_ids = ["{requirement_id}"]',
            'selected_option = ""': 'selected_option = "Replace stale state with repaired state"',
        })
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "check", timeout_seconds, (preflights or {}).get("stage:check"))
        sessions.append(session)
        check_forms = sorted((repo_root / ".agentic" / "runs" / run_id / "stages" / "check").glob("check-*.toml"))
        if len(check_forms) != 1:
            raise RuntimeError("prepared check stage did not contain exactly one form")
        check_form = check_forms[0]
        check_text = check_form.read_text(encoding="utf-8")
        identifier = re.search(r'^id = "([^"]+)"$', check_text, flags=re.MULTILINE)
        if identifier is None:
            raise RuntimeError("check form did not contain an ID")
        check_id = identifier.group(1)
        _replace_exact(check_form, {
            "cites_requirement = []": f'cites_requirement = ["{requirement_id}"]',
            'command = ""': 'command = "python tests/check_pilot_state.py"',
            'path = ""': 'path = "tests/check_pilot_state.py"',
            "concerns = []": 'concerns = ["stale state is not accepted"]',
        })
        _command_json(repo_root, ["stage", "apply"], session)
        session.stage_apply_attempts += 1
        red = _command_json(repo_root, ["check", "run", check_id], session)
        if red.get("execution_status") != "fail":
            raise RuntimeError("full pilot did not observe required red check evidence")
        _command_json(repo_root, ["stage", "close", "--approver", "AEGIS Pilot <aegis-pilot@example.invalid>"], session)
        session.stage_close_attempts += 1
        session.human_interventions.append("standing user-authorized fixed approval at stage close")

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "implementation", timeout_seconds, (preflights or {}).get("stage:implementation"))
        sessions.append(session)
        (repo_root / "src" / "pilot_state.py").write_text("STATE = 'repaired'\n", encoding="utf-8", newline="\n")
        green = _command_json(repo_root, ["check", "run", check_id], session)
        if green.get("execution_status") != "pass":
            raise RuntimeError("full pilot did not observe required green check evidence")
        green_evidence = _evidence_id(green)
        _replace_exact(_form_path(repo_root, run_id, "implementation"), {
            "changed_paths = []": 'changed_paths = ["src/pilot_state.py"]',
            "documentation_effects = []": 'documentation_effects = ["none"]',
            "linked_check_evidence = []": f'linked_check_evidence = ["{green_evidence}"]',
        })
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "validation", timeout_seconds, (preflights or {}).get("stage:validation"))
        sessions.append(session)
        verified = _command_json(repo_root, ["verify", "run"], session, allow_failure=True)
        verification_path = _required_artifact(verified, "verify run")
        _replace_exact(_form_path(repo_root, run_id, "validation"), {
            "deterministic_verification = []": f'deterministic_verification = ["{verification_path}"]',
            'diff_review = "pending"': 'diff_review = "pass"',
            'documentation_review = "pending"': 'documentation_review = "not-applicable"',
            'style_review = "pending"': 'style_review = "pass"',
            "manual_evidence = []": f'manual_evidence = ["{green_evidence}"]',
        })
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "delivery", timeout_seconds, (preflights or {}).get("stage:delivery"))
        sessions.append(session)
        final_verification = _command_json(repo_root, ["verify", "run"], session)
        verification_path = str(final_verification["artifact"])
        reported = _command_json(repo_root, ["delivery", "report"], session)
        report_path = str(reported["artifact"])
        _replace_exact(_form_path(repo_root, run_id, "delivery"), {
            'preflight_reference = ""': f'preflight_reference = "{verification_path}"',
            'report = ""': f'report = "{report_path}"',
            'decision = "pending"': 'decision = "approved"',
        })
        completed = _apply_and_close(repo_root, session)
        session.final_evidence_state = "managed red and green check evidence plus final verification"
        session.final_invariant_state = "final verification passed after validation activated requirements"
        return {"label": "full-change", "run_id": run_id, "setup_commands": [asdict(item) for item in setup], "sessions": [asdict(item) for item in sessions], "complete": completed.get("complete") is True, "outcome_class": "success"}
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        return {"label": "full-change", "run_id": run_id, "setup_commands": [asdict(item) for item in setup], "sessions": [asdict(item) for item in sessions], "complete": False, "outcome_class": _outcome_class(exc), "failure": str(exc)}


def _run_quick_fix_workflow(
    endpoint: str,
    model: str,
    repo_root: Path,
    profile: PilotProfile,
    timeout_seconds: float,
    setup: list[CommandObservation] | None = None,
    run_id: str | None = None,
    preflights: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """@brief Complete a fixed quick fix with registered managed red/green evidence."""
    if setup is None or run_id is None:
        setup = _initialize_fixture_repository(repo_root)
        started = _command_json(repo_root, ["run", "start", "fix", "--quick"])
        run_id = str(started["run_id"])
    sessions: list[SessionObservation] = []
    check_id = ""
    green_evidence = ""
    verification_path = ""
    try:
        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "intake", timeout_seconds, (preflights or {}).get("stage:intake"))
        sessions.append(session)
        _replace_exact(_form_path(repo_root, run_id, "intake"), {'statement = ""': 'statement = "Repair quick pilot state"'})
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "implementation", timeout_seconds, (preflights or {}).get("stage:implementation"))
        sessions.append(session)
        created = _command_json(repo_root, ["check", "create"], session)
        definition = repo_root / str(created["artifact"])
        check_text = definition.read_text(encoding="utf-8")
        identifier = re.search(r'^id = "([^"]+)"$', check_text, flags=re.MULTILINE)
        if identifier is None:
            raise RuntimeError("quick check definition did not contain an ID")
        check_id = identifier.group(1)
        _replace_exact(definition, {
            'command = ""': 'command = "python tests/check_pilot_state.py"',
            "concerns = []": 'concerns = ["stale state is not accepted"]',
        })
        _command_json(repo_root, ["check", "register"], session)
        red = _command_json(repo_root, ["check", "run", check_id], session)
        if red.get("execution_status") != "fail":
            raise RuntimeError("quick pilot did not observe required red check evidence")
        (repo_root / "src" / "pilot_state.py").write_text("STATE = 'repaired'\n", encoding="utf-8", newline="\n")
        green = _command_json(repo_root, ["check", "run", check_id], session)
        if green.get("execution_status") != "pass":
            raise RuntimeError("quick pilot did not observe required green check evidence")
        green_evidence = _evidence_id(green)
        _replace_exact(_form_path(repo_root, run_id, "implementation"), {
            "changed_paths = []": 'changed_paths = ["src/pilot_state.py"]',
            "documentation_effects = []": 'documentation_effects = ["none"]',
            "linked_check_evidence = []": f'linked_check_evidence = ["{green_evidence}"]',
        })
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "validation", timeout_seconds, (preflights or {}).get("stage:validation"))
        sessions.append(session)
        verified = _command_json(repo_root, ["verify", "run"], session)
        verification_path = str(verified["artifact"])
        _replace_exact(_form_path(repo_root, run_id, "validation"), {
            "deterministic_verification = []": f'deterministic_verification = ["{verification_path}"]',
            'diff_review = "pending"': 'diff_review = "pass"',
            'documentation_review = "pending"': 'documentation_review = "not-applicable"',
            'style_review = "pending"': 'style_review = "pass"',
            "manual_evidence = []": f'manual_evidence = ["{green_evidence}"]',
        })
        _apply_and_close(repo_root, session)

        session = _fresh_stage_session(endpoint, model, repo_root, run_id, profile, "delivery", timeout_seconds, (preflights or {}).get("stage:delivery"))
        sessions.append(session)
        final_verification = _command_json(repo_root, ["verify", "run"], session)
        verification_path = str(final_verification["artifact"])
        reported = _command_json(repo_root, ["delivery", "report"], session)
        report_path = str(reported["artifact"])
        _replace_exact(_form_path(repo_root, run_id, "delivery"), {
            'preflight_reference = ""': f'preflight_reference = "{verification_path}"',
            'report = ""': f'report = "{report_path}"',
            'decision = "pending"': 'decision = "approved"',
        })
        completed = _apply_and_close(repo_root, session)
        session.final_evidence_state = "managed red and green quick-check evidence plus final verification"
        session.final_invariant_state = "final verification passed with declared quick not-applicable invariants"
        return {"label": "quick-fix", "run_id": run_id, "setup_commands": [asdict(item) for item in setup], "sessions": [asdict(item) for item in sessions], "complete": completed.get("complete") is True, "outcome_class": "success"}
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        return {"label": "quick-fix", "run_id": run_id, "setup_commands": [asdict(item) for item in setup], "sessions": [asdict(item) for item in sessions], "complete": False, "outcome_class": _outcome_class(exc), "failure": str(exc)}


def _model_prompt(repo_root: Path, run_id: str, profile: PilotProfile) -> str:
    """@brief Build the sole initial prompt for one fresh, transcript-free session."""
    return (
        "Repository path: " + str(repo_root) + "\n"
        "AEGIS run ID: " + run_id + "\n"
        "Model context profile: " + str(profile.context_window) + "\n"
        "Follow repository AGENTS.md. This is a fresh session with no prior transcript. "
        "Do not propose or execute shell commands. Invoke the only available tool now."
    )


def _run_model_session(
    endpoint: str,
    model: str,
    repo_root: Path,
    run_id: str,
    profile: PilotProfile,
    scenario: str,
    timeout_seconds: float,
    execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    preflight: dict[str, Any] | None = None,
) -> SessionObservation:
    """@brief Run one fresh model session and the resulting fixed bootstrap tool action."""
    prompt = _model_prompt(repo_root, run_id, profile)
    observation = SessionObservation(
        session_id=str(uuid4()),
        scenario=scenario,
        started_at=_utc_now(),
        prompt_bytes=len(prompt.encode("utf-8")),
        transcript_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    )
    payload = _model_request_payload(model, repo_root, run_id, profile)
    observation.api_request = json.loads(_serialize_request_payload(payload))
    budget, serialized = _context_budget(payload, profile.context_window)
    observation.request_serialization = {
        "encoding": "utf-8",
        "exact_json": serialized.decode("utf-8"),
        "sha256": hashlib.sha256(serialized).hexdigest(),
        "bytes": len(serialized),
    }
    observation.context_budget = budget
    if preflight is not None:
        expected = preflight.get("request_serialization", {}).get("exact_json")
        observation.preflight_validation = {
            "planned_before_network": True,
            "serialized_request_matches_preflight": expected == observation.request_serialization["exact_json"],
            "actual_payload_revalidated": True,
        }
    else:
        observation.preflight_validation = {
            "planned_before_network": False,
            "serialized_request_matches_preflight": None,
            "actual_payload_revalidated": True,
        }
    if not budget["within_budget"]:
        observation.failure = (
            "harness context budget rejected request before network call: "
            f"{budget['combined_token_upper_bound']} > {budget['context_window_budget']}"
        )
        observation.outcome_class = "budget-rejected"
        observation.correctness = {
            "fresh_session": True,
            "allowed_tool_requested": False,
            "forbidden_recovery_reads": False,
            "named_recovery_executed": False,
            "budget_rejected_pre_network": True,
            "score": 1,
            "out_of": 4,
        }
        return observation
    try:
        response, response_bytes, latency_ms = _post_json(endpoint, payload, timeout_seconds)
        observation.response_bytes = response_bytes
        observation.latency_ms = latency_ms
        usage = response.get("usage")
        observation.model_usage = usage if isinstance(usage, dict) else None
        observation.response_evidence.append(_safe_response_evidence(response))
        if not _tool_request_is_valid(response):
            observation.invalid_command_count = 1
            observation.failure = "model did not request exactly the one allowed bootstrap tool"
            observation.outcome_class = "tool-rejection"
            observation.correctness = {
                "fresh_session": True,
                "allowed_tool_requested": False,
                "forbidden_recovery_reads": False,
                "named_recovery_executed": False,
                "score": 1,
                "out_of": 3,
            }
            return observation
        observation.tool_request_valid = True
        _run_bounded_bootstrap(repo_root, observation, execute)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        observation.failure = str(exc)
        observation.outcome_class = _outcome_class(exc)
    observation.correctness = {
        "fresh_session": True,
        "allowed_tool_requested": observation.tool_request_valid,
        "forbidden_recovery_reads": any(
            path.endswith("graph.json") or path.endswith("journal.jsonl") for path in observation.files_read
        ),
        "named_recovery_executed": bool(observation.commands),
        "budget_rejected_pre_network": False,
        "budget_within_harness_limit": observation.context_budget["within_budget"],
        "score": sum((
            observation.tool_request_valid,
            not any(path.endswith("graph.json") or path.endswith("journal.jsonl") for path in observation.files_read),
            observation.failure is None,
            observation.context_budget["within_budget"],
        )),
        "out_of": 4,
    }
    if observation.failure is None:
        observation.outcome_class = "success"
    return observation


def _outcome_class(error: BaseException) -> str:
    """@brief Classify observed harness failures without converting them to success."""
    text = str(error).lower()
    if "timed out" in text:
        return "timeout"
    if "http" in text or "connection" in text or "non-json" in text:
        return "api-error"
    if "exit code" in text:
        return "command-failure"
    return "abandoned-attempt"


def _attempt_lineage(previous_attempts: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """@brief Retain prior evidence links while keeping lineage separate from this result."""
    chain: list[dict[str, Any]] = []
    follows_prior_failures = False
    for path in previous_attempts:
        if not path.is_file():
            continue
        raw = path.read_bytes()
        chain.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "preserved": True})
        try:
            prior = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for profile in prior.get("profiles", []):
            for trial in profile.get("trials", []) if isinstance(profile, dict) else []:
                if isinstance(trial, dict) and trial.get("outcome_class") != "success":
                    follows_prior_failures = True
    return chain, {
        "has_prior_attempts": bool(chain),
        "prior_attempt_count": len(chain),
        "follows_prior_failures": follows_prior_failures,
        "retry_is_lineage_only": True,
    }


def _current_attempt_outcome(result: dict[str, Any]) -> str:
    """@brief Classify only the current run's observed trial outcomes."""
    if result.get("outcome_class") == "budget-rejected":
        return "budget-rejected"
    outcomes = [
        trial.get("outcome_class")
        for profile in result["profiles"]
        for trial in profile["trials"]
        if isinstance(trial, dict)
    ]
    if outcomes and all(outcome == "success" for outcome in outcomes):
        return "success"
    return next((outcome for outcome in outcomes if outcome != "success"), "abandoned-attempt")


# PUBLIC API


def run_pilot(
    *,
    endpoint: str,
    model: str,
    template_root: Path,
    profiles: tuple[PilotProfile, ...],
    timeout_seconds: float,
) -> dict[str, Any]:
    """
    @brief      Execute full/quick startup and recovery scenarios in disposable repositories.
    @return     Machine-readable observations without inferred token telemetry.
    """
    endpoint = validate_loopback_endpoint(endpoint)
    if not model.strip():
        raise ValueError("model must not be empty")
    if not template_root.is_dir():
        raise ValueError(f"template root does not exist: {template_root}")
    result: dict[str, Any] = {
        "schema_version": 3,
        "started_at": _utc_now(),
        "endpoint": endpoint,
        "model": model,
        "provider_coverage": {
            "scope": "Bonsai-only user override",
            "covered": [model],
            "not_equivalent_to": ["original Qwen/Codex/Claude provider matrix"],
        },
        "discovery": {
            "request": {"method": "GET", "url": f"{endpoint}/models", "headers": {}},
            "attempted": False,
            "reason": "awaiting deterministic request preflight",
        },
        "runner": "LM Studio OpenAI-compatible API",
        "model_build": "not exposed by the configured /v1/models response",
        "tokenizer": "not exposed by the configured /v1/models or completion responses",
        "template_version": _template_version(template_root),
        "profiles": [],
        "preflight": {
            "completed_before_network": False,
            "all_requests_within_budget": False,
            "planned_request_count": 0,
        },
        "safety": {
            "model_output_is_untrusted": True,
            "tool_permissions": [BOOTSTRAP_TOOL_NAME],
            "harness_allowlisted_actions": sorted(ALLOWED_AEGIS_ACTIONS),
            "network_scope": "single configured loopback OpenAI-compatible endpoint",
        },
    }
    with tempfile.TemporaryDirectory(prefix="aegis-local-model-pilot-") as temporary:
        temporary_root = Path(temporary)
        prepared_trials: list[dict[str, Any]] = []
        for profile in profiles:
            profile_result: dict[str, Any] = {
                "profile": asdict(profile),
                "context_verification": profile.context_claim,
                "thinking_verification": "user-configured; response reasoning evidence retained when present",
                "planned_requests": [],
                "trials": [],
            }
            full_root = temporary_root / f"full-change-{profile.context_window}"
            full_setup, full_run_id = _prepare_trial(template_root, full_root, "change", False)
            full_preflights = {
                f"stage:{stage}": _request_preflight(model, full_root, full_run_id, profile, f"stage:{stage}")
                for stage in FULL_WORKFLOW_STAGES
            }
            quick_root = temporary_root / f"quick-fix-{profile.context_window}"
            quick_setup, quick_run_id = _prepare_trial(template_root, quick_root, "fix", True)
            quick_preflights = {
                f"stage:{stage}": _request_preflight(model, quick_root, quick_run_id, profile, f"stage:{stage}")
                for stage in QUICK_WORKFLOW_STAGES
            }
            profile_result["planned_requests"] = [*full_preflights.values(), *quick_preflights.values()]
            result["profiles"].append(profile_result)
            prepared_trials.append({
                "profile": profile,
                "full_root": full_root,
                "full_setup": full_setup,
                "full_run_id": full_run_id,
                "full_preflights": full_preflights,
                "quick_root": quick_root,
                "quick_setup": quick_setup,
                "quick_run_id": quick_run_id,
                "quick_preflights": quick_preflights,
            })
        planned_requests = [
            request
            for profile_result in result["profiles"]
            for request in profile_result["planned_requests"]
        ]
        result["preflight"] = {
            "completed_before_network": True,
            "all_requests_within_budget": all(request["context_budget"]["within_budget"] for request in planned_requests),
            "planned_request_count": len(planned_requests),
        }
        if not result["preflight"]["all_requests_within_budget"]:
            result["outcome_class"] = "budget-rejected"
            result["outcome_code"] = "budget_rejected"
            result["discovery"] = {
                "request": {"method": "GET", "url": f"{endpoint}/models", "headers": {}},
                "attempted": False,
                "reason": "planned request exceeded the harness context budget before network access",
            }
            result["finished_at"] = _utc_now()
            return result
        models_response, models_bytes, models_latency = _get_json(endpoint, "models", timeout_seconds)
        result["discovery"] = {
            "request": {"method": "GET", "url": f"{endpoint}/models", "headers": {}},
            "attempted": True,
            "response_bytes": models_bytes,
            "latency_ms": models_latency,
            "response": models_response,
        }
        for profile_result, prepared in zip(result["profiles"], prepared_trials, strict=True):
            profile = prepared["profile"]
            profile_result["trials"].append(_run_full_change_workflow(
                endpoint, model, prepared["full_root"], profile, timeout_seconds,
                prepared["full_setup"], prepared["full_run_id"], prepared["full_preflights"],
            ))
            profile_result["trials"].append(_run_quick_fix_workflow(
                endpoint, model, prepared["quick_root"], profile, timeout_seconds,
                prepared["quick_setup"], prepared["quick_run_id"], prepared["quick_preflights"],
            ))
    result["finished_at"] = _utc_now()
    return result


def _template_version(template_root: Path) -> str | None:
    """@brief Read the embedded payload version without parsing unrelated project state."""
    init_path = template_root / ".agentic" / "cli" / "src" / "aegis" / "__init__.py"
    if not init_path.is_file():
        return None
    for line in init_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__ = "):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def main(argv: list[str] | None = None) -> int:
    """@brief Parse pilot arguments, run the experiment, and write its JSON evidence."""
    parser = argparse.ArgumentParser(description="Run constrained local-model AEGIS pilot trials.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", required=True)
    parser.add_argument("--template-root", type=Path, default=Path(__file__).parents[1] / "template")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-profile", type=int, action="append", dest="contexts")
    parser.add_argument("--thinking", default="enabled")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--previous-attempt", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    contexts = tuple(args.contexts or DEFAULT_CONTEXT_PROFILES)
    if any(context <= 0 for context in contexts):
        parser.error("context profiles must be positive")
    if args.output.exists():
        parser.error(f"refusing to overwrite existing pilot evidence: {args.output}")
    profiles = tuple(
        PilotProfile(
            context,
            args.thinking,
            args.temperature,
            args.seed,
            (
                "harness-enforced workflow budget; server context not API-verified"
                if context == 32768
                else "user-configured server profile; not API-verified by the OpenAI-compatible API"
            ),
        )
        for context in contexts
    )
    try:
        result = run_pilot(
            endpoint=args.endpoint,
            model=args.model,
            template_root=args.template_root.resolve(),
            profiles=profiles,
            timeout_seconds=args.timeout_seconds,
        )
    except ValueError as exc:
        parser.error(str(exc))
    result["attempt_chain"], result["attempt_lineage"] = _attempt_lineage(args.previous_attempt)
    result["attempt_outcome_class"] = _current_attempt_outcome(result)
    result["outcome_classes_supported"] = [
        "timeout", "retry", "abandoned-attempt", "api-error", "tool-rejection", "command-failure",
        "budget-rejected", "success",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
