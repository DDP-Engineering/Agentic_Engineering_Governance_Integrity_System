#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file workflow_toml.py
@brief Comment-preserving edits for WAEGIS-owned schema-3 fields.
@details Starts from the complete payload template, replaces only explicit
         owned assignments, and parses the result before it can be published.
"""

# IMPORTS

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping, Sequence


# CONSTANTS

_SECTION = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?$")
_KEY = re.compile(r"^(\s*)([A-Za-z0-9_-]+)\s*=.*$")
_ROOT_GLOB = frozenset("*?[]")
ALL_STAGES = (
    "intake",
    "alignment",
    "requirement",
    "design",
    "check",
    "implementation",
    "validation",
    "delivery",
    "adoption-intake",
    "adoption-alignment",
    "repo-discovery",
    "component-map",
    "component-adoption",
    "baseline-review",
    "adoption-delivery",
)


# DATA MODELS / TYPEDEFINITIONS


class WorkflowError(ValueError):
    """@brief Raised when owned edits cannot produce valid schema-3 TOML."""


@dataclass(frozen=True, slots=True)
class LanguagePreset:
    """@brief Traceability values selected by one language answer."""

    extensions: tuple[str, ...]
    tests: tuple[str, ...]


LANGUAGE_PRESETS: dict[str, LanguagePreset] = {
    "python": LanguagePreset((".py",), ("test_*.py", "*_test.py")),
    "javascript": LanguagePreset((".js", ".jsx", ".mjs", ".cjs"), ("*.test.js", "*.spec.js")),
    "typescript": LanguagePreset((".ts", ".tsx"), ("*.test.ts", "*.spec.ts", "*.test.tsx", "*.spec.tsx")),
    "java": LanguagePreset((".java",), ("*Test.java", "*Tests.java", "*IT.java")),
    "c": LanguagePreset((".c", ".h"), ("test_*.c", "*_test.c")),
    "cpp": LanguagePreset((".cpp", ".cc", ".cxx", ".hpp", ".h"), ("test_*.cpp", "*_test.cpp")),
    "rust": LanguagePreset((".rs",), ("*_test.rs", "test_*.rs")),
    "go": LanguagePreset((".go",), ("*_test.go",)),
}


# HELPER FUNCTIONS


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, Mapping):
        pairs = ", ".join(f"{json.dumps(str(key))} = {_toml_value(item)}" for key, item in value.items())
        return "{ " + pairs + " }"
    raise WorkflowError(f"unsupported TOML value: {value!r}")


def _inline_comment(line: str) -> str:
    """@brief Return an assignment's top-level inline comment, if present."""
    quote: str | None = None
    escaped = False
    depth = 0
    for index, char in enumerate(line):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\" and quote == '"':
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth = max(0, depth - 1)
        elif char == "#" and depth == 0:
            return " " + line[index:].lstrip()
    return ""


def _comparable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _comparable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_comparable(item) for item in value]
    return value


def _assignment_value(line: str) -> object:
    comment = _inline_comment(line)
    source = line[: -len(comment)] if comment else line
    try:
        parsed = tomllib.loads(source)
    except tomllib.TOMLDecodeError:
        return object()
    return next(iter(parsed.values())) if len(parsed) == 1 else object()


def _replace_key(text: str, section_name: str, key_name: str, value: object) -> str:
    lines = text.splitlines(keepends=True)
    section: str | None = None
    found = False
    newline = "\r\n" if "\r\n" in text else "\n"
    for index, line in enumerate(lines):
        section_match = _SECTION.match(line.rstrip("\r\n"))
        if section_match:
            section = section_match.group(1)
            continue
        key_match = _KEY.match(line.rstrip("\r\n"))
        if section == section_name and key_match and key_match.group(2) == key_name:
            if _comparable(_assignment_value(line.rstrip("\r\n"))) == _comparable(value):
                return text
            comment = _inline_comment(line.rstrip("\r\n"))
            lines[index] = f"{key_match.group(1)}{key_name} = {_toml_value(value)}{comment}{newline}"
            found = True
            break
    if not found:
        raise WorkflowError(f"payload workflow template is missing [{section_name}] {key_name}")
    return "".join(lines)


def _section_range(lines: list[str], section_name: str) -> tuple[int, int] | None:
    start: int | None = None
    for index, line in enumerate(lines):
        match = _SECTION.match(line.rstrip("\r\n"))
        if not match:
            continue
        if start is not None:
            return start, index
        if match.group(1) == section_name:
            start = index
    return (start, len(lines)) if start is not None else None


def _set_optional_key(text: str, section_name: str, key_name: str, value: object | None) -> str:
    """@brief Set or remove one WAEGIS-owned conditional assignment."""
    lines = text.splitlines(keepends=True)
    bounds = _section_range(lines, section_name)
    if bounds is None:
        raise WorkflowError(f"payload workflow template is missing [{section_name}]")
    start, end = bounds
    for index in range(start + 1, end):
        match = _KEY.match(lines[index].rstrip("\r\n"))
        if match and match.group(2) == key_name:
            if value is None:
                del lines[index]
                return "".join(lines)
            if _comparable(_assignment_value(lines[index].rstrip("\r\n"))) == _comparable(value):
                return text
            comment = _inline_comment(lines[index].rstrip("\r\n"))
            newline = "\r\n" if "\r\n" in text else "\n"
            lines[index] = f"{match.group(1)}{key_name} = {_toml_value(value)}{comment}{newline}"
            return "".join(lines)
    if value is None:
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    insert_at = start + 1
    while insert_at < end and not _KEY.match(lines[insert_at].rstrip("\r\n")):
        insert_at += 1
    while insert_at < end and _KEY.match(lines[insert_at].rstrip("\r\n")):
        insert_at += 1
    lines.insert(insert_at, f"{key_name} = {_toml_value(value)}{newline}")
    return "".join(lines)


def _replace_optional_table(text: str, section_name: str, values: Mapping[str, object] | None) -> str:
    """@brief Replace, add, or remove a fully WAEGIS-owned optional table."""
    lines = text.splitlines(keepends=True)
    bounds = _section_range(lines, section_name)
    newline = "\r\n" if "\r\n" in text else "\n"
    try:
        table: object = tomllib.loads(text)
        for part in section_name.split("."):
            table = table[part] if isinstance(table, dict) else None
    except (KeyError, TypeError, tomllib.TOMLDecodeError):
        table = None
    if values is None and bounds is None:
        return text
    if values is not None and bounds is not None and _comparable(table) == _comparable(values):
        return text
    if bounds is not None:
        start, end = bounds
        del lines[start:end]
        while start < len(lines) and start > 0 and not lines[start - 1].strip() and not lines[start].strip():
            del lines[start]
    if values is None:
        return "".join(lines)
    block = [f"[{section_name}]{newline}"]
    block.extend(f"{key} = {_toml_value(value)}{newline}" for key, value in values.items())
    block.append(newline)
    if lines and lines[-1].strip():
        lines.append(newline)
    lines.extend(block)
    return "".join(lines)


def _string_list(value: object, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise WorkflowError(f"{field} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WorkflowError(f"{field} entries must be non-empty strings")
        normalized = item.strip()
        if normalized not in result:
            result.append(normalized)
    if not allow_empty and not result:
        raise WorkflowError(f"{field} must not be empty")
    return tuple(result)


def _mode(answers: Mapping[str, object], key: str, choices: tuple[str, ...]) -> str:
    value = answers.get(key)
    if not isinstance(value, str) or value not in choices:
        raise WorkflowError(f"{key} must be one of: {', '.join(choices)}")
    return value


# EXPORTED FUNCTIONS / PUBLIC API


def normalize_roots(value: object, field: str) -> tuple[str, ...]:
    """
    @brief Validate non-glob, relative repository roots.
    @param[in] value Sequence of path strings.
    @param[in] field Field name for diagnostics.
    @return Deduplicated canonical roots.
    """
    if not isinstance(value, (list, tuple)) or not value:
        raise WorkflowError(f"{field} must be a non-empty list")
    roots: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise WorkflowError(f"{field} entries must be non-empty strings")
        normalized = item.replace("\\", "/").strip("/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts or any(char in normalized for char in _ROOT_GLOB):
            raise WorkflowError(f"{field} contains an unsafe root: {item!r}")
        if normalized not in roots:
            roots.append(normalized)
    return tuple(roots)


def workflow_answers(text: str) -> dict[str, object]:
    """@brief Read the complete WAEGIS-owned answer surface from valid TOML."""
    try:
        value = tomllib.loads(text)
        answers: dict[str, object] = {
            "language": value["traceability"]["language"],
            "source_roots": value["source"]["roots"],
            "test_roots": value["tests"]["roots"],
            "alignment_enabled": value["alignment"]["enabled"],
            "alignment_protected_scope_mode": value["alignment"]["protected_scope"]["mode"],
            "alignment_protected_scope_patterns": value["alignment"]["protected_scope"]["patterns"],
            "stage_form_retention": value["interface"]["stage_form_retention"],
            "check_execution": value["interface"]["check_execution"],
            "coverage_mode": value["traceability"]["coverage"]["mode"],
            "coverage_roots": value["traceability"]["coverage"]["coverable_roots"],
            "coverage_exclude": value["traceability"]["coverage"]["exclude"],
            "baseline_guard_mode": value["components"]["baseline_guard"]["mode"],
            "minimum_completion_level": value["components"]["baseline_guard"].get(
                "minimum_completion_level", "baseline-usable"
            ),
            "adoption_source_changes_mode": value["adoption"]["source_changes"]["mode"],
            "secrets_mode": value["guardrails"]["secrets"]["mode"],
            "secrets_patterns": value["guardrails"]["secrets"]["patterns"],
            "protected_paths_mode": value["guardrails"]["protected_paths"]["mode"],
            "protected_paths_patterns": value["guardrails"]["protected_paths"]["patterns"],
            "protected_paths_operations": value["guardrails"]["protected_paths"]["operations"],
            "working_tree_mode": value["guardrails"]["working_tree"]["mode"],
            "working_tree_blocked_patterns": value["guardrails"]["working_tree"]["blocked_patterns"],
            "write_access_mode": value["guardrails"]["write_access"]["mode"],
            "write_access_stages": value["guardrails"]["write_access"].get("stages", {}),
            "scope_mode": value["guardrails"]["scope"]["mode"],
            "scope_allowed_roots": value["guardrails"]["scope"]["allowed_roots"],
            "delivery_mode": value["guardrails"]["delivery"]["mode"],
            "delivery_command_patterns": value["guardrails"]["delivery"]["command_patterns"],
        }
        for gate in ("build", "typecheck", "lint", "test", "security"):
            answers[f"gate_{gate}_mode"] = value["gates"][gate]["mode"]
            answers[f"gate_{gate}_commands"] = value["gates"][gate]["commands"]
        quick = value.get("quick", {}).get("changed_paths")
        answers["quick_changed_paths_mode"] = quick["mode"] if quick else "disabled"
        answers["quick_max_paths"] = quick["max_paths"] if quick else 10
        answers["source_extensions"] = value["traceability"]["source_extensions"]
        answers["test_file_patterns"] = value["traceability"]["test_file_patterns"]
    except (KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise WorkflowError(f"cannot read WAEGIS-owned fields from workflow TOML: {exc}") from exc
    return answers


def generate_workflow(base_text: str, answers: Mapping[str, object]) -> str:
    """
    @brief Apply basic WAEGIS-owned answers to the complete payload template.
    @param[in] base_text Complete schema-3 payload workflow text.
    @param[in] answers Normalized install/configure answers.
    @return Valid UTF-8 TOML text with original unowned bytes preserved.
    @exception WorkflowError If answers or output are invalid.
    """
    try:
        parsed = tomllib.loads(base_text)
    except tomllib.TOMLDecodeError as exc:
        raise WorkflowError(f"payload workflow template is invalid: {exc}") from exc
    if parsed.get("schema_version") != 3:
        raise WorkflowError("payload workflow template must use schema_version = 3")
    language = answers.get("language")
    if language == "other":
        extensions = tuple(answers.get("source_extensions", ()))
        patterns = tuple(answers.get("test_file_patterns", ()))
        if not extensions or not patterns:
            raise WorkflowError("language 'other' requires source_extensions and test_file_patterns")
    elif isinstance(language, str) and language in LANGUAGE_PRESETS:
        preset = LANGUAGE_PRESETS[language]
        extensions = tuple(answers.get("source_extensions", preset.extensions))
        patterns = tuple(answers.get("test_file_patterns", preset.tests))
    else:
        raise WorkflowError(f"unsupported language: {language!r}")
    source_roots = normalize_roots(answers.get("source_roots"), "source_roots")
    test_roots = normalize_roots(answers.get("test_roots"), "test_roots")
    generated = base_text
    owned_values: list[tuple[str, str, object]] = [
        ("source", "roots", source_roots),
        ("tests", "roots", test_roots),
        ("traceability", "language", language),
        ("traceability", "source_extensions", extensions),
        ("traceability", "test_file_patterns", patterns),
        ("alignment", "enabled", answers.get("alignment_enabled")),
        (
            "alignment.protected_scope",
            "mode",
            _mode(answers, "alignment_protected_scope_mode", ("disabled", "enforce")),
        ),
        (
            "alignment.protected_scope",
            "patterns",
            _string_list(answers.get("alignment_protected_scope_patterns"), "alignment_protected_scope_patterns"),
        ),
        (
            "interface",
            "stage_form_retention",
            _mode(answers, "stage_form_retention", ("versioned", "latest", "discard")),
        ),
        ("interface", "check_execution", _mode(answers, "check_execution", ("external", "managed"))),
        ("traceability.coverage", "mode", _mode(answers, "coverage_mode", ("disabled", "enforce"))),
        ("traceability.coverage", "coverable_roots", _string_list(answers.get("coverage_roots"), "coverage_roots")),
        ("traceability.coverage", "exclude", _string_list(answers.get("coverage_exclude"), "coverage_exclude")),
        ("components.baseline_guard", "mode", _mode(answers, "baseline_guard_mode", ("disabled", "enforce"))),
        (
            "adoption.source_changes",
            "mode",
            _mode(answers, "adoption_source_changes_mode", ("unrestricted", "blocked")),
        ),
        ("guardrails.secrets", "mode", _mode(answers, "secrets_mode", ("disabled", "enforce"))),
        ("guardrails.secrets", "patterns", _string_list(answers.get("secrets_patterns"), "secrets_patterns")),
        (
            "guardrails.protected_paths",
            "mode",
            _mode(answers, "protected_paths_mode", ("disabled", "enforce")),
        ),
        (
            "guardrails.protected_paths",
            "patterns",
            _string_list(answers.get("protected_paths_patterns"), "protected_paths_patterns"),
        ),
        (
            "guardrails.protected_paths",
            "operations",
            _string_list(answers.get("protected_paths_operations"), "protected_paths_operations"),
        ),
        (
            "guardrails.working_tree",
            "mode",
            _mode(answers, "working_tree_mode", ("unrestricted", "restricted")),
        ),
        (
            "guardrails.working_tree",
            "blocked_patterns",
            _string_list(answers.get("working_tree_blocked_patterns"), "working_tree_blocked_patterns"),
        ),
        (
            "guardrails.write_access",
            "mode",
            _mode(answers, "write_access_mode", ("unrestricted", "stage_restricted")),
        ),
        (
            "guardrails.scope",
            "mode",
            _mode(answers, "scope_mode", ("unrestricted", "advisory", "enforce")),
        ),
        (
            "guardrails.scope",
            "allowed_roots",
            _string_list(answers.get("scope_allowed_roots"), "scope_allowed_roots"),
        ),
        ("guardrails.delivery", "mode", _mode(answers, "delivery_mode", ("disabled", "enforce"))),
        (
            "guardrails.delivery",
            "command_patterns",
            _string_list(answers.get("delivery_command_patterns"), "delivery_command_patterns"),
        ),
    ]
    for gate in ("build", "typecheck", "lint", "test", "security"):
        owned_values.extend(
            (
                (f"gates.{gate}", "mode", _mode(answers, f"gate_{gate}_mode", ("disabled", "enforce"))),
                (
                    f"gates.{gate}",
                    "commands",
                    _string_list(answers.get(f"gate_{gate}_commands"), f"gate_{gate}_commands"),
                ),
            )
        )
    if not isinstance(answers.get("alignment_enabled"), bool):
        raise WorkflowError("alignment_enabled must be boolean")
    for section, key, value in owned_values:
        generated = _replace_key(generated, section, key, value)
    baseline_mode = answers["baseline_guard_mode"]
    minimum = answers.get("minimum_completion_level") if baseline_mode == "enforce" else None
    if minimum is not None and minimum not in (
        "unknown",
        "discovered",
        "characterized",
        "baseline-usable",
        "baseline-strict",
    ):
        raise WorkflowError("minimum_completion_level is invalid")
    generated = _set_optional_key(generated, "components.baseline_guard", "minimum_completion_level", minimum)
    write_mode = answers["write_access_mode"]
    if write_mode == "stage_restricted":
        stages = answers.get("write_access_stages")
        if not isinstance(stages, Mapping) or set(stages) != set(ALL_STAGES):
            raise WorkflowError("write_access_stages must contain every supported stage")
        stage_values = {stage: _string_list(stages[stage], f"write_access_stages.{stage}") for stage in ALL_STAGES}
        generated = _replace_optional_table(generated, "guardrails.write_access.stages", stage_values)
    else:
        generated = _replace_optional_table(generated, "guardrails.write_access.stages", None)
    quick_mode = answers["quick_changed_paths_mode"]
    if quick_mode == "advise":
        maximum = answers.get("quick_max_paths")
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
            raise WorkflowError("quick_max_paths must be a positive integer")
        generated = _replace_optional_table(
            generated,
            "quick.changed_paths",
            {"mode": "advise", "max_paths": maximum},
        )
    elif quick_mode == "disabled":
        generated = _replace_optional_table(generated, "quick.changed_paths", None)
    else:
        raise WorkflowError("quick_changed_paths_mode must be disabled or advise")
    try:
        output = tomllib.loads(generated)
    except tomllib.TOMLDecodeError as exc:
        raise WorkflowError(f"generated workflow TOML is invalid: {exc}") from exc
    if output["source"]["roots"] != list(source_roots) or output["tests"]["roots"] != list(test_roots):
        raise WorkflowError("generated workflow roots do not match normalized answers")
    if quick_mode == "disabled" and "quick" in output:
        raise WorkflowError("disabled quick policy must omit its active table")
    return generated


# END OF FILE
