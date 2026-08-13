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
import re
import tomllib
from datetime import date, datetime, time
from typing import Any

from aegis.domain.configuration import ProjectConfig, ValidationCommand
from aegis.domain.values import RepositoryPath, ValueValidationError, WorkingDirectory


class ArtifactDecodeError(ValueError):
    """@brief Report a path-specific decoding or schema error."""

    def __init__(
        self, summary: str, *, path: str, code: str = "malformed_state"
    ) -> None:
        super().__init__(f"{path}: {summary}")
        self.summary = summary
        self.path = path
        self.code = code


_MARKDOWN_SCHEMAS = {
    "run": 1,
    "stage": 1,
    "component": 1,
    "specification": 1,
    "adoption": 1,
    "abandonment": 1,
}
_REQUIREMENT_ID = re.compile(r"^REQ-[0-9a-f]{32}$")
_DRIFT_REVIEW_VALUES = frozenset({"yes", "no", "uncertain"})


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


def _normalize_toml_temporal_values(value: Any) -> Any:
    """@brief Convert TOML temporal values to stable protocol strings."""
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            key: _normalize_toml_temporal_values(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_toml_temporal_values(item) for item in value]
    return value


def _load_toml(source: bytes | dict[str, Any], *, path: str) -> dict[str, Any]:
    if isinstance(source, dict):
        return _normalize_toml_temporal_values(source)
    try:
        return _normalize_toml_temporal_values(
            tomllib.loads(source.decode("utf-8-sig"))
        )
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


def _render_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return _toml_array(value)
    return _toml_string(str(value))


def _render_front_matter(
    metadata: dict[str, Any], *, tables: dict[str, list[dict[str, Any]]] | None = None
) -> list[str]:
    lines = ["+++"]
    for key, value in metadata.items():
        lines.append(f"{key} = {_render_toml_value(value)}")
    for name, entries in (tables or {}).items():
        for entry in entries:
            lines.extend(("", f"[[{name}]]"))
            for key, value in entry.items():
                lines.append(f"{key} = {_render_toml_value(value)}")
    lines.extend(("+++", ""))
    return lines


def _escape_section_content(value: Any) -> str:
    return "\n".join(
        "\\" + line if line.startswith("## ") else line
        for line in str(value).splitlines()
    )


def _unescape_section_content(value: str) -> str:
    return "\n".join(
        line[1:] if line.startswith("\\## ") else line
        for line in value.splitlines()
    ).strip("\n")


def _markdown_sections(body: str) -> tuple[str, dict[str, str]]:
    lines = body.strip().splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("Markdown artifact has no title")
    title = lines[0][2:].strip()
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[1:]:
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return title, {
        name: _unescape_section_content("\n".join(content))
        for name, content in sections.items()
    }


def _bullet_items(content: str, *, marker: str = "- ") -> list[str]:
    return [
        line[len(marker) :].replace("<br>", "\n")
        for line in content.splitlines()
        if line.startswith(marker)
    ]


def _render_bullets(values: list[Any], *, empty: str = "None") -> list[str]:
    if not values:
        return [f"- {empty}"]
    return [f"- {str(value).replace(chr(10), '<br>')}" for value in values]


def _table_cell(value: Any) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\n", "<br>")
    )


def _split_table_row(line: str) -> list[str]:
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in line.strip().strip("|"):
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "|":
            cells.append("".join(current).strip().replace("<br>", "\n"))
            current = []
        else:
            current.append(character)
    current.append("\\" if escaped else "")
    cells.append("".join(current).strip().replace("<br>", "\n"))
    return cells


def _table_rows(content: str) -> list[list[str]]:
    lines = [line for line in content.splitlines() if line.startswith("|")]
    return [_split_table_row(line) for line in lines[2:]] if len(lines) >= 2 else []


def _after_label(content: str, label: str, default: str = "None") -> str:
    prefix = f"- {label}:"
    for line in content.splitlines():
        if line.startswith(prefix):
            return (
                line[len(prefix) :]
                .strip()
                .replace("<br>", "\n")
                .replace("\\|", "|")
                .replace("\\\\", "\\")
            )
    return default


def _json_or_text(value: str) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _scope_change_row(change: dict[str, Any]) -> str:
    actor_reason = f"{change.get('actor', '')}; {change.get('reason', '')}"
    affected = ", ".join(change.get("affected_work", []))
    return (
        f"| {_table_cell(change.get('time', ''))} "
        f"| {_table_cell(change.get('before', ''))} "
        f"| {_table_cell(change.get('after', ''))} "
        f"| {_table_cell(actor_reason)} | {_table_cell(affected)} |"
    )


def render_markdown_document(
    metadata: dict[str, Any], state: dict[str, Any], *, kind: str
) -> bytes:
    """@brief Render machine front matter plus bounded human-readable state."""
    front = dict(metadata)
    if kind == "run":
        tables = {
            "stages": [
                {
                    key: stage.get(key, "")
                    for key in ("sequence", "name", "path", "status", "updated_at")
                }
                for stage in state.get("stages", [])
            ]
        }
        lines = _render_front_matter(front, tables=tables)
        lines.extend(_render_run_body(metadata, state))
    elif kind == "component":
        front.pop("requirement_ids", None)
        tables = {
            "test_links": [
                {"path": link.get("path", ""), "selector": link.get("selector", "")}
                for link in state.get("test_links", [])
            ]
        }
        lines = _render_front_matter(front, tables=tables)
        lines.extend(_render_component_body(metadata, state))
    elif kind == "specification":
        lines = _render_front_matter(front)
        lines.extend(_render_specification_body(metadata, state))
    elif kind == "stage":
        front["state_json"] = json.dumps(
            state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        lines = _render_front_matter(front)
        lines.extend(_render_stage_body(metadata, state))
    elif kind == "adoption":
        front["state_json"] = json.dumps(
            state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        lines = _render_front_matter(front)
        lines.extend(_render_project_body(metadata, state, "Adoption"))
    elif kind == "abandonment":
        front["state_json"] = json.dumps(
            state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        lines = _render_front_matter(front)
        lines.extend(_render_project_body(metadata, state, "Exceptional abandonment"))
    else:
        front["state_json"] = json.dumps(
            state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        lines = _render_front_matter(front)
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
        metadata = _normalize_toml_temporal_values(tomllib.loads(text[4:end]))
        body = text[end + 5 :]
        kind = metadata.get("artifact_type")
        supported_schema = _MARKDOWN_SCHEMAS.get(kind)
        if supported_schema is None:
            raise ArtifactDecodeError(
                "unsupported Markdown artifact type",
                path=path,
                code="unsupported_schema",
            )
        schema = metadata.get("schema")
        if type(schema) is not int or schema != supported_schema:
            raise ArtifactDecodeError(
                f"unsupported {kind} schema",
                path=path,
                code="unsupported_schema",
            )
        if kind == "run":
            stages = metadata.pop("stages", [])
            state = _parse_run_body(body, stages=stages)
        elif kind == "component":
            test_links = metadata.pop("test_links", [])
            legacy_requirement_ids = metadata.pop("requirement_ids", None)
            state = _parse_component_body(body, test_links=test_links, path=path)
            requirement_ids = [
                link["requirement_id"] for link in state["requirement_links"]
            ]
            if legacy_requirement_ids is not None and legacy_requirement_ids != (
                requirement_ids
            ):
                raise ArtifactDecodeError(
                    "legacy Component Requirement IDs disagree with atomic links",
                    path=path,
                )
            metadata["requirement_ids"] = requirement_ids
        elif kind == "specification":
            state = _parse_specification_body(body)
        else:
            state_value = metadata.pop("state_json")
            state = json.loads(state_value)
            if not isinstance(state, dict):
                raise ArtifactDecodeError(
                    "state_json must contain an object", path=path
                )
        return metadata, state, body
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
    title = state.get("title") or str(ticket).splitlines()[0][:100]
    opening = state.get("opening_repository_state", {})
    baseline = f"{opening.get('branch', 'unknown')} @ {opening.get('head', 'unknown')}"
    classifications = opening.get("classifications", {})
    preexisting = json.dumps(classifications, ensure_ascii=False, sort_keys=True)
    baseline_index = opening.get("index_revision") or "none"
    baseline_dirty = json.dumps(
        opening.get("dirty_paths", []), ensure_ascii=False, sort_keys=True
    )
    first_observed = json.dumps(
        state.get("changes_first_observed", []), ensure_ascii=False
    )
    adopted = json.dumps(state.get("changes_adopted", []), ensure_ascii=False)
    uncertain = json.dumps(state.get("uncertain_authorship", []), ensure_ascii=False)
    attribution_findings = json.dumps(
        state.get("attribution_findings", []), ensure_ascii=False, sort_keys=True
    )
    lines = [
        f"# {metadata.get('id', 'Run')} - {title}",
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
        f"- Included: {_table_cell(state.get('scope', 'None'))}",
        f"- Excluded: {_table_cell(state.get('excluded_scope', 'None'))}",
        f"- Open questions: {_table_cell(state.get('open_questions', 'None'))}",
        "",
        "## Execution instruction",
        "",
        f"- Actor: {_table_cell(state.get('actor', 'operator'))}",
        (
            "- Developer instruction affecting interaction: "
            f"{_table_cell(state.get('execution_instruction', 'None'))}"
        ),
        "",
        "## Scope-change log",
        "",
        (
            "| Time (UTC) | Previous interpretation | New interpretation "
            "| Actor and reason | Affected artifacts |"
        ),
        "|---|---|---|---|---|",
    ]
    lines.extend(_scope_change_row(change) for change in state.get("scope_changes", []))
    lines.extend(
        (
            "",
            "## Stage summary",
            "",
            "| Stage | Status | Result | Updated |",
            "|---|---|---|---|",
        )
    )
    lines.extend(
        (
            f"| {str(stage.get('name', '')).replace('_', ' ').title()} "
            f"| {_table_cell(stage.get('status', ''))} "
            f"| {_table_cell(stage.get('result', ''))} "
            f"| {_table_cell(stage.get('updated_at', ''))} |"
        )
        for stage in state.get("stages", [])
    )
    lines.extend(
        (
            "",
        "",
        "## Change attribution",
        "",
        f"- Baseline branch and revision: {_table_cell(baseline)}",
        (
            "- Pre-existing working changes: "
            f"{_table_cell(preexisting)}"
        ),
        f"- Baseline index revision: {_table_cell(baseline_index)}",
        f"- Baseline dirty-path revisions: {_table_cell(baseline_dirty)}",
        (
            "- Changes first observed during this Run: "
            f"{_table_cell(first_observed)}"
        ),
        f"- Changes adopted into scope: {_table_cell(adopted)}",
        f"- Uncertain authorship: {_table_cell(uncertain)}",
        f"- Attribution uncertainty findings: {_table_cell(attribution_findings)}",
        "",
        "## Current handoff",
        "",
        f"- Current Stage: `{metadata.get('current_stage', 'none')}`",
        f"- Durable context: {_table_cell(state.get('durable_context', 'None'))}",
        f"- Next action: {_table_cell(state.get('next_action', 'None'))}",
        f"- Blockers: {_table_cell(state.get('blockers', 'None'))}",
        "",
        "## Terminal outcome",
        "",
        _escape_section_content(
            json.dumps(state.get("outcome"), ensure_ascii=False)
            if isinstance(state.get("outcome"), (dict, list))
            else state.get("outcome", "Active")
        ),
        "",
        "## Run event history",
        "",
        "| Time (UTC) | Actor | Event | Result |",
        "|---|---|---|---|",
        )
    )
    lines.extend(
        (
            f"| {_table_cell(event.get('time', ''))} "
            f"| {_table_cell(event.get('actor', ''))} "
            f"| {_table_cell(event.get('event', ''))} "
            f"| {_table_cell(event.get('result', ''))} |"
        )
        for event in state.get("events", [])
    )
    return lines


def _parse_run_body(body: str, *, stages: list[dict[str, Any]]) -> dict[str, Any]:
    title, sections = _markdown_sections(body)
    ticket = sections["Ticket input"]
    if ticket.startswith("```text\n") and ticket.endswith("\n```"):
        ticket = ticket[8:-4]
    scope = sections.get("Current scope", "")
    execution = sections.get("Execution instruction", "")
    attribution = sections.get("Change attribution", "")
    handoff = sections.get("Current handoff", "")
    scope_changes = []
    for row in _table_rows(sections.get("Scope-change log", "")):
        actor, separator, reason = row[3].partition(";")
        scope_changes.append(
            {
                "time": row[0],
                "before": row[1],
                "after": row[2],
                "actor": actor.strip(),
                "reason": reason.strip() if separator else "",
                "affected_work": [
                    item.strip() for item in row[4].split(",") if item.strip()
                ],
            }
        )
    baseline = _after_label(attribution, "Baseline branch and revision")
    branch, separator, head = baseline.partition(" @ ")
    classifications = _json_or_text(
        _after_label(attribution, "Pre-existing working changes", "{}")
    )
    index_revision = _after_label(attribution, "Baseline index revision", "none")
    dirty_paths = _json_or_text(
        _after_label(attribution, "Baseline dirty-path revisions", "[]")
    )
    stage_results = {
        row[0].lower().replace(" ", "_"): row[2]
        for row in _table_rows(sections.get("Stage summary", ""))
    }
    for stage in stages:
        stage["result"] = stage_results.get(stage.get("name", ""), "")
    return {
        "title": title.split(" - ", 1)[1] if " - " in title else title,
        "ticket_text": ticket,
        "intent": sections.get("Intent", "None"),
        "scope": _after_label(scope, "Included"),
        "excluded_scope": _after_label(scope, "Excluded"),
        "open_questions": _after_label(scope, "Open questions"),
        "actor": _after_label(execution, "Actor", "operator"),
        "execution_instruction": _after_label(
            execution, "Developer instruction affecting interaction"
        ),
        "opening_repository_state": {
            "branch": branch,
            "head": head if separator else "unknown",
            "classifications": (
                classifications if isinstance(classifications, dict) else {}
            ),
            "index_revision": None if index_revision == "none" else index_revision,
            "dirty_paths": dirty_paths if isinstance(dirty_paths, list) else [],
        },
        "changes_first_observed": _json_or_text(
            _after_label(attribution, "Changes first observed during this Run", "[]")
        ),
        "changes_adopted": _json_or_text(
            _after_label(attribution, "Changes adopted into scope", "[]")
        ),
        "uncertain_authorship": _json_or_text(
            _after_label(attribution, "Uncertain authorship", "[]")
        ),
        "attribution_findings": _json_or_text(
            _after_label(attribution, "Attribution uncertainty findings", "[]")
        ),
        "scope_changes": scope_changes,
        "stages": stages,
        "durable_context": _after_label(handoff, "Durable context"),
        "next_action": _after_label(handoff, "Next action"),
        "blockers": _after_label(handoff, "Blockers"),
        "outcome": _json_or_text(sections.get("Terminal outcome", "Active")),
        "events": [
            {"time": row[0], "actor": row[1], "event": row[2], "result": row[3]}
            for row in _table_rows(sections.get("Run event history", ""))
        ],
    }


def _render_component_body(
    metadata: dict[str, Any], state: dict[str, Any]
) -> list[str]:
    file_roles = {
        item.get("path", ""): item.get("role", "Role not recorded.")
        for item in state.get("file_roles", [])
        if isinstance(item, dict)
    }
    lines = [
        f"# {metadata.get('name', metadata.get('id', 'Component'))}",
        "",
        "## Purpose and boundary",
        "",
        _escape_section_content(state.get("purpose_boundary", "None")),
        "",
        "## Interfaces",
        "",
        _escape_section_content(state.get("interfaces", "None")),
        "",
        "## Behaviors and requirements",
        "",
    ]
    requirement_links = state.get("requirement_links", [])
    for link in requirement_links:
        lines.append(
            f"- `{link.get('requirement_id', '')}` - "
            f"{str(link.get('behavior', '')).replace(chr(10), '<br>')}"
        )
    lines.extend(
        f"- `(gap)` - {str(behavior).replace(chr(10), '<br>')}"
        for behavior in state.get("unlinked_behaviors", [])
    )
    if not requirement_links and not state.get("unlinked_behaviors"):
        lines.append("- None")
    lines.extend(("", "## File roles", ""))
    lines.extend(
        f"- `{path}` - {file_roles.get(path, 'Role not recorded.')}"
        for path in metadata.get("files", [])
    )
    if not metadata.get("files"):
        lines.append("- None")
    file_digests = state.get("file_digests", {})
    lines.extend(("", "## File digests", ""))
    if isinstance(file_digests, dict):
        lines.extend(
            f"- `{path}` - `{file_digests[path]}`" for path in sorted(file_digests)
        )
    if not isinstance(file_digests, dict) or not file_digests:
        lines.append("- None")
    lines.extend(("", "## Tests", ""))
    lines.extend(
        (
            f"- `{link.get('path', '')}"
            f"{('::' + link.get('selector', '')) if link.get('selector') else ''}` "
            f"- {link.get('description', 'Linked project test.')}"
        )
        for link in state.get("test_links", [])
    )
    if not state.get("test_links"):
        lines.append("- None")
    lines.extend(("", "## Dependencies", ""))
    lines.extend(_render_bullets(state.get("dependencies", [])))
    lines.extend(("", "## Known gaps", ""))
    lines.extend(_render_bullets(state.get("known_gaps", [])))
    review = state.get("drift_review", {})
    lines.extend(
        (
            "",
            "## Drift review",
            "",
            f"- Behavior current: {review.get('behavior', 'uncertain')}",
            f"- Interfaces current: {review.get('interfaces', 'uncertain')}",
            f"- Dependencies current: {review.get('dependencies', 'uncertain')}",
            f"- File membership current: {review.get('files', 'uncertain')}",
            f"- Review finding: {review.get('finding', 'none')}",
        )
    )
    return lines


def _parse_component_body(
    body: str, *, test_links: list[dict[str, Any]], path: str
) -> dict[str, Any]:
    _, sections = _markdown_sections(body)
    behavior_lines = _bullet_items(sections.get("Behaviors and requirements", ""))
    requirement_links = []
    unlinked_behaviors = []
    seen_requirements = set()
    for item in behavior_lines:
        if item == "None":
            continue
        identity, separator, behavior = item.partition("` - ")
        if identity.startswith("`REQ-") and separator:
            requirement_id = identity[1:]
            if (
                not _REQUIREMENT_ID.fullmatch(requirement_id)
                or not behavior.strip()
                or requirement_id in seen_requirements
            ):
                raise ArtifactDecodeError(
                    "Component Requirement link is malformed or duplicated",
                    path=path,
                )
            seen_requirements.add(requirement_id)
            requirement_links.append(
                {"requirement_id": requirement_id, "behavior": behavior}
            )
        elif item.startswith("`(gap)` - "):
            unlinked_behaviors.append(item.removeprefix("`(gap)` - "))
        else:
            raise ArtifactDecodeError(
                "Component behavior entry is malformed", path=path
            )
    file_roles = []
    for item in _bullet_items(sections.get("File roles", "")):
        path, separator, role = item.partition("` - ")
        if path.startswith("`") and separator:
            file_roles.append({"path": path[1:], "role": role})
    file_digests = {}
    for item in _bullet_items(sections.get("File digests", "")):
        path, separator, digest = item.partition("` - `")
        if path.startswith("`") and separator and digest.endswith("`"):
            file_digests[path[1:]] = digest[:-1]
    dependencies = _bullet_items(sections.get("Dependencies", ""))
    known_gaps = _bullet_items(sections.get("Known gaps", ""))
    test_descriptions = []
    for item in _bullet_items(sections.get("Tests", "")):
        _, separator, description = item.partition("` - ")
        if separator:
            test_descriptions.append(description)
    for index, link in enumerate(test_links):
        link["description"] = (
            test_descriptions[index]
            if index < len(test_descriptions)
            else "Linked project test."
        )
    review_section = sections.get("Drift review", "")
    review_labels = {
        "Behavior current",
        "Interfaces current",
        "Dependencies current",
        "File membership current",
        "Review finding",
    }
    for item in _bullet_items(review_section):
        label, separator, _ = item.partition(": ")
        if not separator or label not in review_labels:
            raise ArtifactDecodeError(
                "Component drift review entry is unknown or malformed", path=path
            )
    drift_review = {
        "behavior": _after_label(review_section, "Behavior current", "uncertain"),
        "interfaces": _after_label(
            review_section, "Interfaces current", "uncertain"
        ),
        "dependencies": _after_label(
            review_section, "Dependencies current", "uncertain"
        ),
        "files": _after_label(
            review_section, "File membership current", "uncertain"
        ),
        "finding": _after_label(review_section, "Review finding", "none"),
    }
    if any(
        drift_review[axis] not in _DRIFT_REVIEW_VALUES
        for axis in ("behavior", "interfaces", "dependencies", "files")
    ) or not drift_review["finding"].strip():
        raise ArtifactDecodeError(
            "Component drift review value is invalid", path=path
        )
    return {
        "purpose_boundary": sections.get("Purpose and boundary", "None"),
        "interfaces": sections.get("Interfaces", "None"),
        "requirement_links": requirement_links,
        "unlinked_behaviors": unlinked_behaviors,
        "file_roles": file_roles,
        "file_digests": file_digests,
        "dependencies": [] if dependencies == ["None"] else dependencies,
        "test_links": test_links,
        "known_gaps": [] if known_gaps == ["None"] else known_gaps,
        "drift_review": drift_review,
    }


def _render_specification_body(
    metadata: dict[str, Any], state: dict[str, Any]
) -> list[str]:
    lines = [
        f"# Specification - {state.get('title', metadata.get('requirement_id', ''))}",
        "",
        "## Purpose",
        "",
        _escape_section_content(state.get("purpose", "None")),
        "",
        "## Contract",
        "",
        _escape_section_content(state.get("contract", "None")),
        "",
        "## Inputs and outputs",
        "",
        _escape_section_content(state.get("inputs_outputs", "None")),
        "",
        "## Rules and invariants",
        "",
    ]
    lines.extend(_render_bullets(state.get("rules", [])))
    lines.extend(
        (
            "",
            "## Error behavior",
            "",
            _escape_section_content(state.get("error_behavior", "None")),
            "",
            "## Examples",
            "",
            _escape_section_content(state.get("examples", "None")),
            "",
            "## Open details",
            "",
            _escape_section_content(state.get("open_details", "None")),
        )
    )
    return lines


def _parse_specification_body(body: str) -> dict[str, Any]:
    title, sections = _markdown_sections(body)
    rules = _bullet_items(sections.get("Rules and invariants", ""))
    return {
        "title": title.removeprefix("Specification - "),
        "purpose": sections.get("Purpose", "None"),
        "contract": sections.get("Contract", "None"),
        "inputs_outputs": sections.get("Inputs and outputs", "None"),
        "rules": [] if rules == ["None"] else rules,
        "error_behavior": sections.get("Error behavior", "None"),
        "examples": sections.get("Examples", "None"),
        "open_details": sections.get("Open details", "None"),
    }


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
    sections = state.get("sections", {})
    if metadata.get("stage") == "delivery" and "recorded_state" in sections:
        lines.extend(
            (
                "## Recorded State",
                "",
                str(sections["recorded_state"]),
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
