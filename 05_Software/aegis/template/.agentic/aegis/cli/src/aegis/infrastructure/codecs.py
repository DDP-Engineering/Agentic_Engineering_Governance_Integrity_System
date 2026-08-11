#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    codecs.py
@brief   Decode and canonically render AEGIS TOML and bounded text artifacts.
@details Uses only schema-specific shapes rather than a general TOML writer.
"""

from __future__ import annotations

import json
import tomllib
from typing import Any

from aegis.domain.configuration import ProjectConfig, ValidationCommand
from aegis.domain.values import RepositoryPath, ValueValidationError, WorkingDirectory


class ArtifactDecodeError(ValueError):
    """@brief Report a path-specific decoding or schema error."""

    def __init__(self, summary: str, *, path: str) -> None:
        super().__init__(f"{path}: {summary}")
        self.summary = summary
        self.path = path


def decode_general_text(content: bytes, *, path: str) -> str:
    """@brief Decode permitted repository text and normalize line endings."""
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    elif content.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    else:
        try:
            return content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            encoding = "cp1252"
    try:
        return content.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError as error:
        raise ArtifactDecodeError("text cannot be decoded safely", path=path) from error


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_array(values: tuple[str, ...] | list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _load_toml(source: bytes | dict[str, Any], *, path: str) -> dict[str, Any]:
    if isinstance(source, dict):
        return source
    try:
        return tomllib.loads(source.decode("utf-8-sig"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ArtifactDecodeError("invalid UTF-8 TOML", path=path) from error


def parse_project_config(source: bytes | dict[str, Any], *, path: str) -> ProjectConfig:
    """@brief Parse and validate the version 1 project configuration."""
    data = _load_toml(source, path=path)
    try:
        if data.get("schema") != 1:
            raise ArtifactDecodeError("unsupported project_config schema", path=path)
        if data.get("artifact_type") != "project_config":
            raise ArtifactDecodeError("artifact_type must be project_config", path=path)
        paths = data["paths"]
        test_roots = tuple(RepositoryPath(value) for value in paths["tests"])
        if not test_roots:
            raise ArtifactDecodeError("at least one test root is required", path=path)
        commands: dict[str, ValidationCommand] = {}
        validation = data.get("validation", {})
        for category in ("tests", "lints", "audits"):
            collection = validation.get(category, {})
            if not isinstance(collection, dict):
                raise ArtifactDecodeError(
                    f"validation.{category} must be a table", path=path
                )
            for name, raw in collection.items():
                command = raw["command"]
                timeout = raw["timeout_seconds"]
                if (
                    not isinstance(command, list)
                    or not command
                    or not all(isinstance(item, str) and item for item in command)
                    or not isinstance(timeout, int)
                    or isinstance(timeout, bool)
                    or timeout < 0
                ):
                    raise ArtifactDecodeError(
                        f"invalid validation command {category}.{name}", path=path
                    )
                key = f"{category}.{name}"
                commands[key] = ValidationCommand(
                    category=category,
                    name=name,
                    command=tuple(command),
                    working_directory=WorkingDirectory(raw["working_directory"]),
                    timeout_seconds=timeout,
                )
        policy = data.get("policy", {})
        patterns = policy.get("protected_scope_patterns", [])
        if not isinstance(patterns, list) or not all(
            isinstance(pattern, str) for pattern in patterns
        ):
            raise ArtifactDecodeError(
                "protected_scope_patterns must be strings", path=path
            )
        return ProjectConfig(
            requirements=RepositoryPath(paths["requirements"]),
            components=RepositoryPath(paths["components"]),
            test_roots=test_roots,
            adoptions=RepositoryPath(paths["adoptions"]),
            runs=RepositoryPath(paths["runs"]),
            commands=commands,
            risk_attention_threshold=policy.get("risk_attention_threshold", "medium"),
            protected_scope_patterns=tuple(patterns),
        )
    except ArtifactDecodeError:
        raise
    except (KeyError, TypeError, ValueError, ValueValidationError) as error:
        raise ArtifactDecodeError(
            "malformed project configuration", path=path
        ) from error


def render_project_config(config: ProjectConfig) -> bytes:
    """@brief Render one deterministic UTF-8/LF project configuration."""
    lines = [
        "schema = 1",
        'artifact_type = "project_config"',
        "",
        "[paths]",
        f"requirements = {_toml_string(str(config.requirements))}",
        f"components = {_toml_string(str(config.components))}",
        f"tests = {_toml_array([str(path) for path in config.test_roots])}",
        f"adoptions = {_toml_string(str(config.adoptions))}",
        f"runs = {_toml_string(str(config.runs))}",
    ]
    for key in sorted(config.commands):
        command = config.commands[key]
        lines.extend(
            (
                "",
                f"[validation.{command.category}.{command.name}]",
                f"command = {_toml_array(list(command.command))}",
                f"working_directory = {_toml_string(str(command.working_directory))}",
                f"timeout_seconds = {command.timeout_seconds}",
            )
        )
    lines.extend(
        (
            "",
            "[policy]",
            (
                "risk_attention_threshold = "
                f"{_toml_string(config.risk_attention_threshold)}"
            ),
            "protected_scope_patterns = "
            + _toml_array(list(config.protected_scope_patterns)),
            "",
        )
    )
    return "\n".join(lines).encode("utf-8")


def render_markdown_document(
    metadata: dict[str, Any], state: dict[str, Any], *, kind: str
) -> bytes:
    """@brief Render machine front matter plus bounded human-readable state."""
    front = dict(metadata)
    front["state_json"] = json.dumps(
        state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    lines = ["+++"]
    for key, value in front.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        elif isinstance(value, list):
            rendered = _toml_array(value)
        else:
            rendered = _toml_string(str(value))
        lines.append(f"{key} = {rendered}")
    lines.extend(("+++", ""))
    if kind == "run":
        lines.extend(_render_run_body(metadata, state))
    elif kind == "stage":
        lines.extend(_render_stage_body(metadata, state))
    elif kind == "component":
        lines.extend(_render_project_body(metadata, state, "Component"))
    elif kind == "specification":
        lines.extend(_render_project_body(metadata, state, "Specification"))
    elif kind == "adoption":
        lines.extend(_render_project_body(metadata, state, "Adoption"))
    elif kind == "abandonment":
        lines.extend(_render_project_body(metadata, state, "Exceptional abandonment"))
    else:
        lines.extend(
            (
                f"# {kind.replace('_', ' ').title()}",
                "",
                "```json",
                json.dumps(state, ensure_ascii=False, indent=2),
                "```",
            )
        )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def parse_markdown_document(
    content: bytes, *, path: str
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """@brief Parse bounded TOML front matter without rewriting original bytes."""
    try:
        text = content.decode("utf-8-sig").replace("\r\n", "\n")
        if not text.startswith("+++\n"):
            raise ArtifactDecodeError("missing TOML front matter", path=path)
        end = text.find("\n+++\n", 4)
        if end < 0:
            raise ArtifactDecodeError("unterminated TOML front matter", path=path)
        metadata = tomllib.loads(text[4:end])
        state_value = metadata.pop("state_json")
        state = json.loads(state_value)
        if not isinstance(state, dict):
            raise ArtifactDecodeError("state_json must contain an object", path=path)
        return metadata, state, text[end + 5 :]
    except ArtifactDecodeError:
        raise
    except (
        UnicodeDecodeError,
        tomllib.TOMLDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as error:
        raise ArtifactDecodeError("malformed Markdown artifact", path=path) from error


def render_requirement(data: dict[str, Any]) -> bytes:
    """@brief Render one current Requirement as deterministic TOML."""
    lines = [
        "schema = 1",
        'artifact_type = "requirement"',
        f"id = {_toml_string(data['id'])}",
        f"title = {_toml_string(data['title'])}",
        f"status = {_toml_string(data['status'])}",
        f"priority = {_toml_string(data['priority'])}",
        f"behavior = {_toml_string(data['behavior'])}",
        f"confirmation = {_toml_string(data['confirmation'])}",
        f"verification_kind = {_toml_string(data['verification_kind'])}",
        f"manual_method = {_toml_string(data.get('manual_method', ''))}",
        f"impacted_files = {_toml_array(data['impacted_files'])}",
        f"specification = {_toml_string(data.get('specification', ''))}",
        f"rationale = {_toml_string(data.get('rationale', ''))}",
        f"updated_at = {_toml_string(data['updated_at'])}",
    ]
    for test in data.get("tests", []):
        lines.extend(
            (
                "",
                "[[tests]]",
                f"path = {_toml_string(test['path'])}",
                f"selector = {_toml_string(test.get('selector', ''))}",
                f"purposes = {_toml_array(test['purposes'])}",
                f"covered_files = {_toml_array(test['covered_files'])}",
            )
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _render_run_body(metadata: dict[str, Any], state: dict[str, Any]) -> list[str]:
    ticket = state.get("ticket_text", "")
    lines = [
        f"# {metadata.get('id', 'Run')}",
        "",
        "## Ticket input",
        "",
        "```text",
        str(ticket),
        "```",
        "",
        "## Intent",
        "",
        str(state.get("intent", "None")),
        "",
        "## Current scope",
        "",
        str(state.get("scope", "None")),
        "",
        "## Change attribution",
        "",
        "```json",
        json.dumps(
            state.get("opening_repository_state", {}), ensure_ascii=False, indent=2
        ),
        "```",
        "",
        "## Current handoff",
        "",
        str(state.get("next_action", "None")),
        "",
        "## Terminal outcome",
        "",
        str(state.get("outcome", "Active")),
        "",
        "## Run event history",
        "",
    ]
    lines.extend(
        (
            f"- {event.get('time')} {event.get('actor')}: "
            f"{event.get('event')} - {event.get('result')}"
        )
        for event in state.get("events", [])
    )
    return lines


def _render_stage_body(metadata: dict[str, Any], state: dict[str, Any]) -> list[str]:
    title = str(metadata.get("stage", "stage")).replace("_", " ").title()
    lines = [
        f"# {metadata.get('sequence', '')} - {title}",
        "",
        "## Stage instruction",
        "",
        str(state.get("instruction", "")),
        "",
    ]
    for section in state.get("allowed_sections", []):
        lines.extend(
            (
                f"## {section.replace('_', ' ').title()}",
                "",
                str(state.get("sections", {}).get(section, "None")),
                "",
            )
        )
    for heading, key in (
        ("Evidence", "evidence"),
        ("Findings", "findings"),
        ("Decisions", "decisions"),
        ("Escapes", "escapes"),
        ("Attachments", "attachments"),
        ("Event history", "events"),
    ):
        lines.extend(
            (
                f"## {heading}",
                "",
                "```json",
                json.dumps(state.get(key, []), ensure_ascii=False, indent=2),
                "```",
                "",
            )
        )
    return lines


def _render_project_body(
    metadata: dict[str, Any], state: dict[str, Any], title: str
) -> list[str]:
    name = metadata.get("id") or metadata.get("requirement_id") or ""
    return [
        f"# {title} {name}".rstrip(),
        "",
        "```json",
        json.dumps(state, ensure_ascii=False, indent=2),
        "```",
    ]


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
