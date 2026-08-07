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
import ipaddress
import json
import os
from pathlib import Path
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
BOOTSTRAP_TOOL_NAME = "run_bounded_aegis_bootstrap"
ALLOWED_AEGIS_ACTIONS = frozenset({"run start", "run context", "stage prepare", "stage show"})


# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class PilotProfile:
    """@brief One requested local-model context profile."""

    context_window: int
    thinking: str
    temperature: float
    seed: int | None


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


def _post_json(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> tuple[dict[str, Any], int, int]:
    """
    @brief      POST one JSON request and preserve reported API output exactly.
    @return     Parsed response, response bytes, and elapsed milliseconds.
    @exception  RuntimeError If the local endpoint cannot return JSON successfully.
    """
    request = Request(
        f"{endpoint}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
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
) -> SessionObservation:
    """@brief Run one fresh model session and the resulting fixed bootstrap tool action."""
    prompt = _model_prompt(repo_root, run_id, profile)
    observation = SessionObservation(
        session_id=str(uuid4()),
        scenario=scenario,
        started_at=_utc_now(),
        prompt_bytes=len(prompt.encode("utf-8")),
    )
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": _tool_definition(),
        "tool_choice": "required",
        "temperature": profile.temperature,
    }
    if profile.seed is not None:
        payload["seed"] = profile.seed
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
        context = _run_bounded_bootstrap(repo_root, observation, execute)
        tool_message = {
            "role": "tool",
            "tool_call_id": response["choices"][0]["message"]["tool_calls"][0].get("id", "pilot-tool-call"),
            "content": json.dumps({"context": context, "bootstrap_complete": True}, ensure_ascii=False),
        }
        continuation = {
            **payload,
            "messages": [
                *payload["messages"],
                response["choices"][0]["message"],
                tool_message,
                {
                    "role": "user",
                    "content": "The bounded bootstrap is complete. Do not call tools. Reply exactly: BOOTSTRAP COMPLETE.",
                },
            ],
            "max_tokens": 512,
        }
        continuation.pop("tools")
        continuation.pop("tool_choice")
        final_response, final_bytes, final_latency = _post_json(endpoint, continuation, timeout_seconds)
        observation.response_bytes += final_bytes
        observation.latency_ms += final_latency
        observation.response_evidence.append(_safe_response_evidence(final_response))
        final_usage = final_response.get("usage")
        if isinstance(final_usage, dict):
            observation.model_usage = {"initial": usage, "continuation": final_usage}
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        observation.failure = str(exc)
    observation.correctness = {
        "fresh_session": True,
        "allowed_tool_requested": observation.tool_request_valid,
        "forbidden_recovery_reads": any(
            path.endswith("graph.json") or path.endswith("journal.jsonl") for path in observation.files_read
        ),
        "named_recovery_executed": bool(observation.commands),
        "score": sum((
            observation.tool_request_valid,
            not any(path.endswith("graph.json") or path.endswith("journal.jsonl") for path in observation.files_read),
            observation.failure is None,
        )),
        "out_of": 3,
    }
    return observation


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
        "schema_version": 1,
        "started_at": _utc_now(),
        "endpoint": endpoint,
        "model": model,
        "runner": "LM Studio OpenAI-compatible API",
        "model_build": "not exposed by the configured /v1/models response",
        "tokenizer": "not exposed by the configured /v1/models or completion responses",
        "template_version": _template_version(template_root),
        "profiles": [],
        "safety": {
            "model_output_is_untrusted": True,
            "tool_permissions": [BOOTSTRAP_TOOL_NAME],
            "harness_allowlisted_actions": sorted(ALLOWED_AEGIS_ACTIONS),
            "network_scope": "single configured loopback OpenAI-compatible endpoint",
        },
    }
    with tempfile.TemporaryDirectory(prefix="aegis-local-model-pilot-") as temporary:
        temporary_root = Path(temporary)
        for profile in profiles:
            profile_result: dict[str, Any] = {"profile": asdict(profile), "trials": []}
            for kind, quick, label in (("change", False, "full-change"), ("fix", True, "quick-fix")):
                repo_root = temporary_root / f"{label}-{profile.context_window}"
                _new_disposable_repository(template_root, repo_root)
                run_id = _start_trial_run(repo_root, kind, quick)
                startup = _run_model_session(endpoint, model, repo_root, run_id, profile, "startup", timeout_seconds)
                artifact = repo_root / ".agentic" / "runs" / run_id / "stages" / "intake" / "intake.toml"
                if artifact.is_file():
                    artifact.unlink()
                recovery = _run_model_session(endpoint, model, repo_root, run_id, profile, "recovery", timeout_seconds)
                profile_result["trials"].append({
                    "label": label,
                    "run_id": run_id,
                    "run_start": {
                        "kind": kind,
                        "quick": quick,
                        "setup_action": "harness-owned run start before fresh sessions",
                    },
                    "sessions": [asdict(startup), asdict(recovery)],
                })
            result["profiles"].append(profile_result)
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
    args = parser.parse_args(argv)
    contexts = tuple(args.contexts or DEFAULT_CONTEXT_PROFILES)
    if any(context <= 0 for context in contexts):
        parser.error("context profiles must be positive")
    if args.output.exists():
        parser.error(f"refusing to overwrite existing pilot evidence: {args.output}")
    profiles = tuple(PilotProfile(context, args.thinking, args.temperature, args.seed) for context in contexts)
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
