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
@file    resume_context.py
@brief   Assemble one bounded deterministic Stage resume read model.
@details Selects only Run-referenced project knowledge and configured Stage tools.
"""

from __future__ import annotations

import json
import re
from typing import Any

from aegis.ports.workspace import Workspace, WorkspaceError

_REQUIREMENT_ID = re.compile(r"REQ-[0-9a-f]{32}")
_COMPONENT_ID = re.compile(r"COMP-[0-9a-f]{32}")
_REFERENCE_SCAN_LIMIT = 256
_COMPONENT_SCAN_LIMIT = 256

_BUDGETS: dict[str, dict[str, int]] = {
    "full": {
        "run_text_characters": 3000,
        "instruction_characters": 12000,
        "section_characters": 3000,
        "artifact_text_characters": 2000,
        "rules_characters": 8000,
        "stage_entries": 40,
        "run_events": 40,
        "scope_changes": 20,
        "requirements": 16,
        "components": 12,
        "affected_files": 64,
        "tests": 64,
        "commands": 24,
        "test_roots": 16,
        "protected_scope_patterns": 32,
        "findings": 32,
        "sections": 32,
        "artifact_files": 64,
        "artifact_tests": 64,
        "artifact_relationships": 32,
        "specification_rules": 20,
        "opening_paths_per_state": 40,
        "command_arguments": 32,
        "command_argument_characters": 512,
    },
    "short": {
        "run_text_characters": 1500,
        "instruction_characters": 8000,
        "section_characters": 1500,
        "artifact_text_characters": 1000,
        "rules_characters": 4000,
        "stage_entries": 20,
        "run_events": 20,
        "scope_changes": 10,
        "requirements": 8,
        "components": 6,
        "affected_files": 32,
        "tests": 32,
        "commands": 12,
        "test_roots": 16,
        "protected_scope_patterns": 16,
        "findings": 16,
        "sections": 32,
        "artifact_files": 32,
        "artifact_tests": 32,
        "artifact_relationships": 20,
        "specification_rules": 12,
        "opening_paths_per_state": 20,
        "command_arguments": 24,
        "command_argument_characters": 256,
    },
}


def _bounded_text(value: Any, limit: int) -> dict[str, Any]:
    """@return Text cut at a stable boundary with exact omission accounting."""
    text = "" if value is None else str(value)
    total = len(text)
    if total <= limit:
        content = text
    else:
        boundary = max(text.rfind("\n", 0, limit + 1), text.rfind(" ", 0, limit + 1))
        content = text[: boundary if boundary >= max(1, limit // 2) else limit]
    returned = len(content)
    return {
        "content": content,
        "total_characters": total,
        "returned_characters": returned,
        "omitted_characters": total - returned,
        "truncated": returned < total,
    }


def _bounded_collection(items: list[Any], limit: int) -> dict[str, Any]:
    """@return A deterministic prefix with exact item omission accounting."""
    returned = items[:limit]
    return {
        "items": returned,
        "total_count": len(items),
        "returned_count": len(returned),
        "omitted_count": len(items) - len(returned),
        "truncated": len(returned) < len(items),
    }


def _latest_collection(items: list[Any], limit: int) -> dict[str, Any]:
    """@return The latest persisted entries with exact earlier omission counts."""
    returned = items[-limit:] if limit else []
    return {
        "items": returned,
        "total_count": len(items),
        "returned_count": len(returned),
        "omitted_count": len(items) - len(returned),
        "truncated": len(returned) < len(items),
    }


def _bounded_records(
    items: list[Any], count_limit: int, text_limit: int
) -> dict[str, Any]:
    """@return Structured entries as bounded deterministic JSON text."""
    records = [
        _bounded_text(
            json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            text_limit,
        )
        for item in items
    ]
    return _latest_collection(records, count_limit)


def _contains_truncation(value: Any) -> bool:
    """@return Whether any bounded value explicitly reports truncation."""
    if isinstance(value, dict):
        if value.get("truncated") is True:
            return True
        return any(_contains_truncation(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_truncation(item) for item in value)
    return False


def _identities(value: Any, pattern: re.Pattern[str]) -> set[str]:
    """@return Canonical identities explicitly present in durable state."""
    if isinstance(value, str):
        return set(pattern.findall(value))
    if isinstance(value, dict):
        found: set[str] = set()
        for key, item in value.items():
            found.update(_identities(key, pattern))
            found.update(_identities(item, pattern))
        return found
    if isinstance(value, (list, tuple)):
        found = set()
        for item in value:
            found.update(_identities(item, pattern))
        return found
    return set()


def _finding(
    code: str,
    observation: str,
    consequence: str,
    *,
    path: str,
) -> dict[str, Any]:
    """@return One stable advisory resume-context finding."""
    return {
        "code": code,
        "severity": "warning",
        "observation": observation,
        "consequence": consequence,
        "path": path,
    }


def _load_requirement(
    workspace: Workspace,
    requirement_id: str,
    findings: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    """@return One referenced Requirement or an explicit unavailable state."""
    path = f"{workspace.config.requirements}/{requirement_id}.toml"
    try:
        data, _ = workspace.load_toml(path)
        if (
            data.get("schema") != 1
            or data.get("artifact_type") != "requirement"
            or data.get("id") != requirement_id
            or not isinstance(data.get("impacted_files", []), list)
            or not all(isinstance(item, str) for item in data.get("impacted_files", []))
            or not isinstance(data.get("tests", []), list)
            or not all(isinstance(item, dict) for item in data.get("tests", []))
        ):
            raise WorkspaceError(
                "malformed_state",
                "Requirement identity or schema disagrees.",
                path=path,
            )
        return data, path
    except WorkspaceError as error:
        code = (
            "resume_reference_missing"
            if error.code == "not_found"
            else "resume_reference_unreadable"
        )
        findings.append(
            _finding(
                code,
                f"Referenced Requirement {requirement_id} could not be loaded.",
                "Resume context preserves the broken reference and does not invent it.",
                path=path,
            )
        )
        return None, path


def _load_component(
    workspace: Workspace,
    component_id: str,
    findings: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    """@return One referenced Component or an explicit unavailable state."""
    path = f"{workspace.config.components}/{component_id}.md"
    try:
        metadata, state, _ = workspace.load_document(path)
        if (
            metadata.get("schema") != 1
            or metadata.get("artifact_type") != "component"
            or metadata.get("id") != component_id
            or not isinstance(metadata.get("files", []), list)
            or not all(isinstance(item, str) for item in metadata.get("files", []))
            or not isinstance(metadata.get("requirement_ids", []), list)
            or not all(
                isinstance(item, str) for item in metadata.get("requirement_ids", [])
            )
            or not isinstance(state.get("test_links", []), list)
            or not all(isinstance(item, dict) for item in state.get("test_links", []))
        ):
            raise WorkspaceError(
                "malformed_state", "Component identity or schema disagrees.", path=path
            )
        return metadata, state, path
    except WorkspaceError as error:
        code = (
            "resume_reference_missing"
            if error.code == "not_found"
            else "resume_reference_unreadable"
        )
        findings.append(
            _finding(
                code,
                f"Referenced Component {component_id} could not be loaded.",
                "Resume context preserves the broken reference and does not invent it.",
                path=path,
            )
        )
        return None, None, path


def _specification_context(
    workspace: Workspace,
    requirement_id: str,
    path: str,
    text_limit: int,
    rules_limit: int,
    findings: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """@return One bounded optional Specification with truthful failures."""
    if not path:
        return None
    try:
        metadata, state, _ = workspace.load_document(path)
        if (
            metadata.get("schema") != 1
            or metadata.get("artifact_type") != "specification"
            or metadata.get("requirement_id") != requirement_id
            or not isinstance(state.get("rules", []), list)
        ):
            raise WorkspaceError(
                "malformed_state",
                "Specification identity or schema disagrees.",
                path=path,
            )
    except WorkspaceError as error:
        code = (
            "resume_reference_missing"
            if error.code == "not_found"
            else "resume_reference_unreadable"
        )
        findings.append(
            _finding(
                code,
                f"Referenced Specification for {requirement_id} could not be loaded.",
                "The Specification is unavailable and no replacement was fabricated.",
                path=path,
            )
        )
        return {"path": path, "state": "unavailable"}
    rules = [
        _bounded_text(item, text_limit)
        for item in sorted(str(item) for item in state.get("rules", []))
    ]
    return {
        "path": path,
        "state": "available",
        "status": metadata.get("status"),
        "title": _bounded_text(state.get("title", ""), text_limit),
        "purpose": _bounded_text(state.get("purpose", ""), text_limit),
        "contract": _bounded_text(state.get("contract", ""), text_limit),
        "inputs_outputs": _bounded_text(state.get("inputs_outputs", ""), text_limit),
        "rules": _bounded_collection(rules, rules_limit),
        "error_behavior": _bounded_text(state.get("error_behavior", ""), text_limit),
        "examples": _bounded_text(state.get("examples", ""), text_limit),
        "open_details": _bounded_text(state.get("open_details", ""), text_limit),
    }


def _requirement_context(
    workspace: Workspace,
    requirement_id: str,
    loaded: tuple[dict[str, Any] | None, str],
    budget: dict[str, int],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """@return One bounded Requirement context entry."""
    text_limit = budget["artifact_text_characters"]
    data, path = loaded
    if data is None:
        return {"id": requirement_id, "path": path, "state": "unavailable"}
    tests = []
    for test in sorted(
        data.get("tests", []),
        key=lambda item: (str(item.get("path", "")), str(item.get("selector", ""))),
    ):
        tests.append(
            {
                "path": test.get("path", ""),
                "selector": test.get("selector", ""),
                "purposes": _bounded_collection(
                    sorted(str(item) for item in test.get("purposes", [])),
                    budget["artifact_relationships"],
                ),
                "covered_files": _bounded_collection(
                    sorted(str(item) for item in test.get("covered_files", [])),
                    budget["artifact_files"],
                ),
            }
        )
    return {
        "id": requirement_id,
        "path": path,
        "state": "available",
        "title": _bounded_text(data.get("title", ""), text_limit),
        "status": data.get("status"),
        "priority": data.get("priority"),
        "behavior": _bounded_text(data.get("behavior", ""), text_limit),
        "confirmation": _bounded_text(data.get("confirmation", ""), text_limit),
        "verification_kind": data.get("verification_kind"),
        "manual_method": _bounded_text(data.get("manual_method", ""), text_limit),
        "impacted_files": _bounded_collection(
            sorted(str(item) for item in data.get("impacted_files", [])),
            budget["artifact_files"],
        ),
        "tests": _bounded_collection(tests, budget["artifact_tests"]),
        "rationale": _bounded_text(data.get("rationale", ""), text_limit),
        "specification": _specification_context(
            workspace,
            requirement_id,
            str(data.get("specification", "")),
            text_limit,
            budget["specification_rules"],
            findings,
        ),
    }


def _component_context(
    component_id: str,
    loaded: tuple[dict[str, Any] | None, dict[str, Any] | None, str],
    budget: dict[str, int],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """@return One bounded Component context entry."""
    text_limit = budget["artifact_text_characters"]
    metadata, state, path = loaded
    if metadata is None or state is None:
        return {"id": component_id, "path": path, "state": "unavailable"}
    drift = state.get("drift_review", {})
    if any(
        drift.get(field) != "yes"
        for field in ("behavior", "interfaces", "dependencies", "files")
    ):
        findings.append(
            _finding(
                "resume_reference_stale",
                f"Referenced Component {component_id} has incomplete drift review.",
                "The Component is included but its currency remains uncertain.",
                path=path,
            )
        )
    test_links = [
        {
            "path": item.get("path", ""),
            "selector": item.get("selector", ""),
            "description": _bounded_text(item.get("description", ""), text_limit),
        }
        for item in sorted(
            state.get("test_links", []),
            key=lambda item: (str(item.get("path", "")), str(item.get("selector", ""))),
        )
    ]
    return {
        "id": component_id,
        "path": path,
        "state": "available",
        "name": _bounded_text(metadata.get("name", ""), text_limit),
        "status": metadata.get("status"),
        "purpose_boundary": _bounded_text(
            state.get("purpose_boundary", ""), text_limit
        ),
        "interfaces": _bounded_text(state.get("interfaces", ""), text_limit),
        "behaviors": _bounded_collection(
            [
                _bounded_text(item, text_limit)
                for item in sorted(str(item) for item in state.get("behaviors", []))
            ],
            budget["artifact_relationships"],
        ),
        "files": _bounded_collection(
            sorted(str(item) for item in metadata.get("files", [])),
            budget["artifact_files"],
        ),
        "file_roles": _bounded_collection(
            [
                {
                    "path": item.get("path", ""),
                    "role": _bounded_text(item.get("role", ""), text_limit),
                }
                for item in sorted(
                    state.get("file_roles", []),
                    key=lambda item: str(item.get("path", "")),
                )
            ],
            budget["artifact_files"],
        ),
        "requirement_ids": _bounded_collection(
            sorted(str(item) for item in metadata.get("requirement_ids", [])),
            budget["artifact_relationships"],
        ),
        "test_links": _bounded_collection(test_links, budget["artifact_tests"]),
        "dependencies": _bounded_collection(
            [
                _bounded_text(item, text_limit)
                for item in sorted(str(item) for item in state.get("dependencies", []))
            ],
            budget["artifact_relationships"],
        ),
        "known_gaps": _bounded_collection(
            [
                _bounded_text(item, text_limit)
                for item in sorted(str(item) for item in state.get("known_gaps", []))
            ],
            budget["artifact_relationships"],
        ),
        "drift_review": drift,
    }


def _project_rules(
    workspace: Workspace,
    limit: int,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """@return Optional bounded project rules without fallback fabrication."""
    path = ".agentic/rules.md"
    try:
        if workspace.read_optional(path) is None:
            return {
                "path": path,
                "state": "absent",
                "content": _bounded_text("", limit),
            }
        text = workspace.read_text(path)
        return {
            "path": path,
            "state": "present",
            "content": _bounded_text(text, limit),
        }
    except WorkspaceError:
        findings.append(
            _finding(
                "resume_reference_unreadable",
                "Optional project rules could not be read safely as UTF-8 text.",
                "Only shipped workflow rules are available for this resume.",
                path=path,
            )
        )
        return {
            "path": path,
            "state": "unreadable",
            "content": _bounded_text("", limit),
        }


def _redacted_command(arguments: tuple[str, ...]) -> list[str]:
    """@return Command arguments with common inline or following secrets redacted."""
    sensitive = re.compile(r"(?i)(password|passwd|secret|token|api[-_]?key)")
    redacted: list[str] = []
    hide_next = False
    for argument in arguments:
        if hide_next:
            redacted.append("<redacted>")
            hide_next = False
            continue
        if argument.startswith("sk-"):
            redacted.append("<redacted>")
            continue
        name, separator, _ = argument.partition("=")
        if separator and sensitive.search(name):
            redacted.append(f"{name}=<redacted>")
            continue
        redacted.append(argument)
        if argument.startswith("-") and sensitive.search(argument):
            hide_next = True
    return redacted


def _tool_context(
    workspace: Workspace, stage: str, budget: dict[str, int]
) -> dict[str, Any]:
    """@return Only configured validation commands applicable to the target Stage."""
    categories: set[str]
    if stage in {"check", "implementation"}:
        categories = {"tests"}
    elif stage in {"validation", "delivery"}:
        categories = {"tests", "lints", "audits"}
    else:
        categories = set()
    commands = [
        {
            "category": command.category,
            "name": command.name,
            "command": _bounded_collection(
                [
                    _bounded_text(argument, budget["command_argument_characters"])
                    for argument in _redacted_command(command.command)
                ],
                budget["command_arguments"],
            ),
            "working_directory": str(command.working_directory),
            "timeout_seconds": command.timeout_seconds,
        }
        for _, command in sorted(workspace.config.commands.items())
        if command.category in categories
    ]
    return {
        "test_roots": _bounded_collection(
            sorted(str(path) for path in workspace.config.test_roots),
            budget["test_roots"],
        ),
        "commands": _bounded_collection(commands, budget["commands"]),
        "risk": {
            "attention_threshold": workspace.config.risk_attention_threshold,
            "protected_scope_patterns": _bounded_collection(
                sorted(workspace.config.protected_scope_patterns),
                budget["protected_scope_patterns"],
            ),
        },
    }


def _run_summary(
    run_meta: dict[str, Any], run_state: dict[str, Any], budget: dict[str, int]
) -> dict[str, Any]:
    """@return Bounded current Run state needed to resume without chat history."""
    limit = budget["run_text_characters"]
    opening = run_state.get("opening_repository_state", {})
    classifications = opening.get("classifications", {})
    path_limit = budget["opening_paths_per_state"]
    return {
        "id": run_meta.get("id"),
        "status": run_meta.get("status"),
        "profile": run_meta.get("profile"),
        "work_type": run_meta.get("work_type"),
        "current_stage": run_meta.get("current_stage"),
        "ticket_text": _bounded_text(run_state.get("ticket_text", ""), limit),
        "intent": _bounded_text(run_state.get("intent", ""), limit),
        "scope": _bounded_text(run_state.get("scope", ""), limit),
        "excluded_scope": _bounded_text(run_state.get("excluded_scope", ""), limit),
        "open_questions": _bounded_text(run_state.get("open_questions", ""), limit),
        "execution_instruction": _bounded_text(
            run_state.get("execution_instruction", ""), limit
        ),
        "opening_repository_state": {
            "branch": opening.get("branch"),
            "head": opening.get("head"),
            "staged": _bounded_collection(
                sorted(
                    classifications.get("staged", []),
                    key=lambda item: json.dumps(item, sort_keys=True),
                ),
                path_limit,
            ),
            "unstaged": _bounded_collection(
                sorted(
                    classifications.get("unstaged", []),
                    key=lambda item: json.dumps(item, sort_keys=True),
                ),
                path_limit,
            ),
            "untracked": _bounded_collection(
                sorted(classifications.get("untracked", [])), path_limit
            ),
            "renamed": _bounded_collection(
                sorted(
                    classifications.get("renamed", []),
                    key=lambda item: json.dumps(item, sort_keys=True),
                ),
                path_limit,
            ),
            "deleted": _bounded_collection(
                sorted(
                    classifications.get("deleted", []),
                    key=lambda item: json.dumps(item, sort_keys=True),
                ),
                path_limit,
            ),
        },
        "change_attribution": {
            "first_observed": _bounded_records(
                list(run_state.get("changes_first_observed", [])),
                path_limit,
                limit,
            ),
            "adopted": _bounded_records(
                list(run_state.get("changes_adopted", [])), path_limit, limit
            ),
            "uncertain_authorship": _bounded_records(
                list(run_state.get("uncertain_authorship", [])), path_limit, limit
            ),
            "findings": _bounded_records(
                list(run_state.get("attribution_findings", [])), path_limit, limit
            ),
        },
        "scope_changes": _bounded_records(
            list(run_state.get("scope_changes", [])),
            budget["scope_changes"],
            limit,
        ),
        "stages": _bounded_records(list(run_state.get("stages", [])), 8, limit),
        "durable_context": _bounded_text(run_state.get("durable_context", ""), limit),
        "next_action": _bounded_text(run_state.get("next_action", ""), limit),
        "blockers": _bounded_text(run_state.get("blockers", ""), limit),
        "outcome": _bounded_text(run_state.get("outcome", ""), limit),
        "events": _bounded_records(
            list(run_state.get("events", [])), budget["run_events"], limit
        ),
    }


def _stage_context(
    stage_meta: dict[str, Any],
    stage_state: dict[str, Any],
    revision: str,
    budget: dict[str, int],
) -> dict[str, Any]:
    """@return Bounded exact Stage state with deterministic section ordering."""
    allowed = list(stage_state.get("allowed_sections", []))
    sections = stage_state.get("sections", {})
    names = allowed + sorted(name for name in sections if name not in allowed)
    section_items = [
        {
            "name": name,
            "content": _bounded_text(
                sections.get(name, "None"), budget["section_characters"]
            ),
        }
        for name in names
    ]
    entry_limit = budget["stage_entries"]
    return {
        "status": stage_meta.get("status"),
        "revision": revision,
        "started_at": stage_meta.get("started_at"),
        "updated_at": stage_meta.get("updated_at"),
        "completed_at": stage_meta.get("completed_at"),
        "sections": _bounded_collection(section_items, budget["sections"]),
        "evidence": _bounded_records(
            list(stage_state.get("evidence", [])),
            entry_limit,
            budget["artifact_text_characters"],
        ),
        "findings": _bounded_records(
            list(stage_state.get("findings", [])),
            entry_limit,
            budget["artifact_text_characters"],
        ),
        "decisions": _bounded_records(
            list(stage_state.get("decisions", [])),
            entry_limit,
            budget["artifact_text_characters"],
        ),
        "escapes": _bounded_records(
            list(stage_state.get("escapes", [])),
            entry_limit,
            budget["artifact_text_characters"],
        ),
        "attachments": _bounded_records(
            list(stage_state.get("attachments", [])),
            entry_limit,
            budget["artifact_text_characters"],
        ),
        "events": _bounded_records(
            list(stage_state.get("events", [])),
            entry_limit,
            budget["artifact_text_characters"],
        ),
        "work_applied": bool(stage_state.get("work_applied", False)),
    }


def _deduplicate_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """@return Findings in stable first-observed order without duplicates."""
    result = []
    seen: set[tuple[Any, ...]] = set()
    for finding in findings:
        key = (finding.get("code"), finding.get("path"), finding.get("observation"))
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result


def assemble_stage_resume_context(
    workspace: Workspace,
    *,
    run_id: str,
    run_meta: dict[str, Any],
    run_state: dict[str, Any],
    stage: str,
    stage_meta: dict[str, Any],
    stage_state: dict[str, Any],
    stage_revision: str,
    selected_run: bool,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], bool]:
    """
    @brief Assemble one self-contained, deterministic, read-only resume context.
    @return Data, bounded context findings, and aggregate truncation state.
    """
    profile = str(run_meta.get("profile", "full"))
    budget = dict(_BUDGETS.get(profile, _BUDGETS["full"]))
    findings: list[dict[str, Any]] = []
    durable = (run_meta, run_state, stage_meta, stage_state)
    requirement_ids = set(run_meta.get("requirement_ids", []))
    requirement_ids.update(_identities(durable, _REQUIREMENT_ID))
    component_ids = set(run_meta.get("component_ids", []))
    component_ids.update(_identities(durable, _COMPONENT_ID))

    requirement_loads: dict[str, tuple[dict[str, Any] | None, str]] = {}
    for requirement_id in sorted(requirement_ids)[:_REFERENCE_SCAN_LIMIT]:
        requirement_loads[requirement_id] = _load_requirement(
            workspace, requirement_id, findings
        )
    affected_seed = {
        str(path)
        for data, _ in requirement_loads.values()
        if data is not None
        for path in data.get("impacted_files", [])
    }

    component_loads: dict[
        str, tuple[dict[str, Any] | None, dict[str, Any] | None, str]
    ] = {}
    for component_id in sorted(component_ids)[:_REFERENCE_SCAN_LIMIT]:
        component_loads[component_id] = _load_component(
            workspace, component_id, findings
        )
    component_paths = list(
        workspace.list_files(str(workspace.config.components), suffix=".md")
    )
    scanned_paths = component_paths[:_COMPONENT_SCAN_LIMIT]
    for path in scanned_paths:
        component_id = path.rsplit("/", 1)[-1].removesuffix(".md")
        if component_id in component_loads or not _COMPONENT_ID.fullmatch(component_id):
            continue
        try:
            metadata, state, _ = workspace.load_document(path)
        except WorkspaceError:
            continue
        linked_requirements = set(metadata.get("requirement_ids", []))
        files = set(metadata.get("files", []))
        if linked_requirements.intersection(requirement_ids) or files.intersection(
            affected_seed
        ):
            component_ids.add(component_id)
            component_loads[component_id] = (metadata, state, path)

    for metadata, _, _ in component_loads.values():
        if metadata is not None:
            requirement_ids.update(metadata.get("requirement_ids", []))
    for requirement_id in sorted(requirement_ids)[:_REFERENCE_SCAN_LIMIT]:
        if requirement_id not in requirement_loads:
            requirement_loads[requirement_id] = _load_requirement(
                workspace, requirement_id, findings
            )

    requirement_contexts = [
        _requirement_context(
            workspace,
            requirement_id,
            requirement_loads.get(
                requirement_id,
                (None, f"{workspace.config.requirements}/{requirement_id}.toml"),
            ),
            budget,
            findings,
        )
        for requirement_id in sorted(requirement_ids)[: budget["requirements"]]
    ]
    component_contexts = [
        _component_context(
            component_id,
            component_loads.get(
                component_id,
                (
                    None,
                    None,
                    f"{workspace.config.components}/{component_id}.md",
                ),
            ),
            budget,
            findings,
        )
        for component_id in sorted(component_ids)[: budget["components"]]
    ]

    affected_files = {
        str(path)
        for item in requirement_contexts
        if item.get("state") == "available"
        for path in item["impacted_files"]["items"]
    }
    affected_files.update(
        str(path)
        for item in component_contexts
        if item.get("state") == "available"
        for path in item["files"]["items"]
    )
    tests: dict[tuple[str, str], dict[str, Any]] = {}
    for item in requirement_contexts:
        for test in item.get("tests", {}).get("items", []):
            tests[(str(test["path"]), str(test["selector"]))] = {
                "path": test["path"],
                "selector": test["selector"],
                "source": "requirement",
            }
    for item in component_contexts:
        for test in item.get("test_links", {}).get("items", []):
            tests.setdefault(
                (str(test["path"]), str(test["selector"])),
                {
                    "path": test["path"],
                    "selector": test["selector"],
                    "source": "component",
                },
            )
    for path in sorted(affected_files):
        try:
            exists = workspace.path_exists(path)
        except WorkspaceError:
            exists = False
        if not exists:
            findings.append(
                _finding(
                    "resume_trace_missing_path",
                    f"Referenced affected file does not exist: {path}",
                    "The affected-file context remains incomplete.",
                    path=path,
                )
            )
    for path, _ in sorted(tests):
        try:
            exists = workspace.path_exists(path)
        except WorkspaceError:
            exists = False
        if not exists:
            findings.append(
                _finding(
                    "resume_trace_missing_path",
                    f"Referenced test does not exist: {path}",
                    "The linked-test context remains incomplete.",
                    path=path,
                )
            )
        roots = tuple(str(root) for root in workspace.config.test_roots)
        if not any(path == root or path.startswith(f"{root}/") for root in roots):
            findings.append(
                _finding(
                    "resume_trace_outside_test_root",
                    f"Referenced test is outside configured test roots: {path}",
                    "The test remains visible but configured coverage is uncertain.",
                    path=path,
                )
            )

    rules = _project_rules(workspace, budget["rules_characters"], findings)
    findings = _deduplicate_findings(findings)
    finding_context = _bounded_collection(findings, budget["findings"])
    requirements = {
        "items": requirement_contexts,
        "total_count": len(requirement_ids),
        "returned_count": len(requirement_contexts),
        "omitted_count": len(requirement_ids) - len(requirement_contexts),
        "truncated": len(requirement_contexts) < len(requirement_ids),
    }
    components = {
        "items": component_contexts,
        "total_count": len(component_ids),
        "returned_count": len(component_contexts),
        "omitted_count": len(component_ids) - len(component_contexts),
        "truncated": len(component_contexts) < len(component_ids),
    }
    stage_context = _stage_context(stage_meta, stage_state, stage_revision, budget)
    data = {
        "schema": "aegis.stage.resume_context",
        "schema_version": 1,
        "profile": profile,
        "budget": budget,
        "target": {
            "run_id": run_id,
            "stage": stage,
            "current_stage": run_meta.get("current_stage"),
            "selected_run": selected_run,
            "current_stage_target": stage == run_meta.get("current_stage"),
        },
        "status": stage_meta.get("status"),
        "instruction": _bounded_text(
            stage_state.get("instruction", ""), budget["instruction_characters"]
        ),
        "sections": stage_context["sections"],
        "evidence": stage_context["evidence"],
        "findings": stage_context["findings"],
        "decisions": stage_context["decisions"],
        "escapes": stage_context["escapes"],
        "run_summary": _run_summary(run_meta, run_state, budget),
        "stage_state": stage_context,
        "project_knowledge": {
            "requirements": requirements,
            "components": components,
            "omitted_requirement_ids": _bounded_collection(
                sorted(requirement_ids)[budget["requirements"] :],
                budget["artifact_relationships"],
            ),
            "omitted_component_ids": _bounded_collection(
                sorted(component_ids)[budget["components"] :],
                budget["artifact_relationships"],
            ),
            "affected_files": _bounded_collection(
                sorted(affected_files), budget["affected_files"]
            ),
            "tests": _bounded_collection(
                [tests[key] for key in sorted(tests)], budget["tests"]
            ),
            "component_discovery": {
                "source_root": str(workspace.config.components),
                "total_count": len(component_paths),
                "scanned_count": len(scanned_paths),
                "omitted_count": len(component_paths) - len(scanned_paths),
                "truncated": len(scanned_paths) < len(component_paths),
            },
        },
        "project_rules": rules,
        "tool_context": _tool_context(workspace, stage, budget),
        "context_findings": finding_context,
    }
    truncated = _contains_truncation(data)
    return data, tuple(finding_context["items"]), truncated


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
