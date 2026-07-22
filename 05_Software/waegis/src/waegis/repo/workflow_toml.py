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
@brief Strict schema-version-2 workflow.toml generator and validator.
@details Serves new, adopt, configure, repair, and doctor with one complete
         policy-neutral schema. Structural answers and repository policy are
         independent: every policy mode and every active rule set is supplied
         explicitly, rendered through targeted comment-preserving edits, then
         parsed and validated before the generated text can be saved.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 1.2.0
"""

# IMPORTS

from __future__ import annotations

import json
import re
import shlex
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..io.prompts import FieldSpec

# CONSTANTS

# @brief Glob characters forbidden in structural repository roots.
_ROOT_FORBIDDEN_CHARS = frozenset("*?[]")

SCHEMA_VERSION = 2
ALL_STAGES = (
    "intake",
    "alignment",
    "requirement",
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
COMPLETION_LEVELS = (
    "unknown",
    "discovered",
    "characterized",
    "baseline-usable",
    "baseline-strict",
)
POLICY_MODE_CHOICES: dict[str, tuple[str, ...]] = {
    "baseline_guard_mode": ("disabled", "enforce"),
    "coverage_mode": ("disabled", "enforce"),
    "source_changes_mode": ("unrestricted", "blocked"),
    "alignment_protected_scope_mode": ("disabled", "enforce"),
    "gates_mode": ("disabled", "enforce"),
    "secrets_mode": ("disabled", "enforce"),
    "protected_paths_mode": ("disabled", "enforce"),
    "working_tree_mode": ("unrestricted", "restricted"),
    "write_access_mode": ("unrestricted", "stage_restricted"),
    "scope_mode": ("unrestricted", "advisory", "enforce"),
    "delivery_mode": ("disabled", "enforce"),
}

# @brief Matches a `[section]` header line (owned sections are plain bare names).
_SECTION_RE = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*(?:#.*)?$")

# @brief Matches a `key = value` assignment line (bare keys, hyphens allowed —
#        e.g. `component-adoption`).
_KEY_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_-]+)\s*=\s*(?P<value>.*)$")

# DATA MODELS / TYPEDEFINITIONS


class WorkflowTomlError(ValueError):
    """
    @brief Base class for every error raised by the workflow.toml generator.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """


class BaseFileMismatchError(WorkflowTomlError):
    """
    @brief Raised when the base TOML text is unusable as a generation base.
    @details Covers a base that does not parse as TOML at all, and a base that
             parses but lacks a section/key this generator owns — emitting a
             workflow.toml with missing settings would be worse than failing.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """


class LanguagePresetError(WorkflowTomlError):
    """
    @brief Raised for an unknown language or an incomplete "other" answer.
    @details Enforces plan §7 invariant 6: ``"other"`` requires the caller to
             supply ``source_extensions`` and ``test_file_patterns`` explicitly.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """


class InvariantViolationError(WorkflowTomlError):
    """
    @brief Raised when a re-checked plan §7 invariant fails on parsed output.
    @details The never-save-invalid guard (invariant 5): raised instead of ever
             returning a silently-broken file. :attr:`invariant` names which
             invariant (1–4 for the re-checked properties; 5 for a round-trip
             failure — unparseable output or a generated value disagreeing
             with the intended answer).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    def __init__(self, invariant: int, message: str) -> None:
        """
        @brief      Construct the error for one failed invariant.
        @param[in]  invariant Plan §7 invariant number that failed (1–5).
        @param[in]  message What exactly disagreed.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        super().__init__(f"workflow.toml invariant {invariant} violated: {message}")
        self.invariant = invariant


@dataclass(frozen=True)
class LanguagePreset:
    """
    @brief One language preset: the [traceability] values a language supplies.
    @details ``language`` is written to ``[traceability].language`` verbatim;
             ``source_extensions`` / ``test_file_patterns`` feed the matching
             keys. Extending the preset table means adding one
             :data:`LANGUAGE_PRESETS` entry — no code changes.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    language: str
    source_extensions: tuple[str, ...]
    test_file_patterns: tuple[str, ...]


@dataclass(frozen=True)
class GateWarning:
    """
    @brief Structured warning for a gate configured empty (plan §7).
    @details Returned alongside the generated text; the calling step (T4.3)
             journals/prints it — this module never does.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    gate: str
    message: str


@dataclass(frozen=True)
class GeneratedWorkflow:
    """
    @brief Result of :func:`generate_workflow_toml`: text plus warning records.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    text: str
    warnings: tuple[GateWarning, ...] = ()


# @brief Language preset table (plan §7 invariant 6). Keys are the accepted
#        `language` answer values; "other" is deliberately absent — it has no
#        preset and requires explicit extensions/patterns (see
#        resolve_language_preset).
LANGUAGE_PRESETS: dict[str, LanguagePreset] = {
    "python": LanguagePreset(
        language="python",
        source_extensions=(".py",),
        test_file_patterns=("test_*.py", "*_test.py"),
    ),
    "typescript": LanguagePreset(
        language="typescript",
        source_extensions=(".ts", ".tsx"),
        test_file_patterns=("*.test.ts", "*.spec.ts", "*.test.tsx", "*.spec.tsx"),
    ),
    "javascript": LanguagePreset(
        language="javascript",
        source_extensions=(".js", ".jsx", ".mjs", ".cjs"),
        test_file_patterns=("*.test.js", "*.spec.js", "*.test.jsx", "*.spec.jsx"),
    ),
    "java": LanguagePreset(
        language="java",
        source_extensions=(".java",),
        test_file_patterns=("*Test.java", "*Tests.java", "*IT.java"),
    ),
    "csharp": LanguagePreset(
        language="csharp",
        source_extensions=(".cs",),
        test_file_patterns=("*Tests.cs", "*Test.cs"),
    ),
    "go": LanguagePreset(
        language="go",
        source_extensions=(".go",),
        test_file_patterns=("*_test.go",),
    ),
    "rust": LanguagePreset(
        language="rust",
        source_extensions=(".rs",),
        test_file_patterns=("*_test.rs", "test_*.rs"),
    ),
    "cpp": LanguagePreset(
        language="cpp",
        source_extensions=(".cpp", ".cxx", ".cc", ".c", ".hpp", ".hxx", ".h"),
        test_file_patterns=("test_*.cpp", "*_test.cpp", "*_tests.cpp"),
    ),
}

# @brief Every accepted `language` answer value: the preset keys plus "other".
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(LANGUAGE_PRESETS) | {"other"}

# HELPER FUNCTIONS


def normalize_roots(raw: Any) -> list[str]:
    """
    @brief      Validate/normalize a roots answer (source_roots / test_roots).
    @details    Accepts a comma-separated string (console input) or a sequence
                of strings (answers file / direct call). Each root must be a
                non-empty, repo-relative, forward-slash path with no glob
                characters, no ``.``/``..`` segments, and no duplicates —
                because ``<root>/**`` write-zone patterns are derived from it.
                Backslashes are normalized to forward slashes; a trailing
                slash is stripped.
    @param[in]  raw Candidate answer value.
    @return     The normalized root list (order preserved).
    @exception  ValueError If the answer is empty or any root is invalid; the
                message names the offending root. (Raised as plain
                ``ValueError`` so ``FieldSpec.normalize`` converts it to the
                prompt layer's ``ValidationError``.)
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if isinstance(raw, str):
        items = [part.strip() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, Sequence):
        items = [str(part).strip() for part in raw]
    else:
        raise ValueError("roots must be a comma-separated string or a list of strings")
    if not items:
        raise ValueError("at least one root is required")
    normalized: list[str] = []
    for item in items:
        root = item.replace("\\", "/").rstrip("/")
        if not root:
            raise ValueError("a root must not be empty")
        if _ROOT_FORBIDDEN_CHARS & set(root):
            raise ValueError(f"root {item!r} must not contain glob characters (*, ?, [, ])")
        if root.startswith("/") or root.startswith("~") or re.match(r"^[A-Za-z]:", root):
            raise ValueError(f"root {item!r} must be repo-relative, not absolute")
        if any(segment in (".", "..") for segment in root.split("/")):
            raise ValueError(f"root {item!r} must not contain '.' or '..' segments")
        if root in normalized:
            raise ValueError(f"root {item!r} is listed more than once")
        normalized.append(root)
    return normalized


def normalize_language(raw: Any) -> str:
    """
    @brief      Validate/normalize a language answer against the preset table.
    @param[in]  raw Candidate answer value.
    @return     The lowercased language key (a :data:`LANGUAGE_PRESETS` key or
                ``"other"``).
    @exception  ValueError If the value is not a supported language; the
                message lists the supported values.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if not isinstance(raw, str):
        raise ValueError("language must be a string")
    language = raw.strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language {raw!r}; supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
    return language


def normalize_gate_commands(raw: Any) -> list[str]:
    """
    @brief      Validate/normalize a gate command-list answer.
    @details    The shape is a list of commands, each command a non-empty argv
                list of non-empty strings (``[["uv", "run", "pytest", "-q"]]``).
                A flat list of strings is rejected as ambiguous (one command or
                several?) rather than guessed at. An empty list is valid —
                empty gates are permitted with a recorded warning (plan §7).
                A console/answers-file ``str`` (the only shape ``ConsoleAsker``
                can ever produce) is parsed as JSON first — without this, a
                real operator typing the prompt's own example text at the
                console could never configure a non-empty gate: every non-empty
                string used to fail validation outright and the console asker
                re-prompts forever on an invalid answer (found in T4.4 live
                verification).
    @param[in]  raw Candidate answer value.
    @return     Canonical list of non-empty command strings.
    @exception  ValueError If the value is not a supported command list.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.3.0
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "gate commands must be valid JSON containing command strings, "
                'e.g. ["uv run pytest -q"]'
            ) from exc
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("gate commands must be a list of command strings")
    commands: list[str] = []
    for command in raw:
        if isinstance(command, str):
            normalized = command.strip()
        elif isinstance(command, Sequence):
            argv = [str(part).strip() for part in command]
            if not argv or any(not part for part in argv):
                raise ValueError("a gate argv entry must contain non-empty strings")
            normalized = shlex.join(argv)
        else:
            raise ValueError("each gate command must be a string")
        if not normalized:
            raise ValueError("a gate command must not be empty")
        if normalized in commands:
            raise ValueError(f"gate command is listed more than once: {normalized!r}")
        commands.append(normalized)
    return commands


def normalize_bool(raw: Any) -> bool:
    """
    @brief      Validate/normalize a boolean answer (alignment_enabled).
    @param[in]  raw Candidate answer value: a bool, or a yes/no-style string.
    @return     The boolean value.
    @exception  ValueError If the value is not recognizably boolean.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in ("true", "yes", "y", "1"):
            return True
        if text in ("false", "no", "n", "0"):
            return False
    raise ValueError("expected a boolean (true/false, yes/no)")


def normalize_rule_list(raw: Any) -> list[str]:
    """
    @brief      Normalize an optional list of policy strings.
    @param[in]  raw JSON list text or a sequence of strings.
    @return     Unique stripped strings in input order.
    @exception  ValueError If the input is not a list of non-empty strings.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError('expected a JSON string list, e.g. ["src/**"]') from exc
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("expected a list of strings")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("policy list entries must be non-empty strings")
        value = item.strip()
        if value in values:
            raise ValueError(f"policy entry is listed more than once: {value!r}")
        values.append(value)
    return values


def normalize_stage_map(raw: Any) -> dict[str, list[str]]:
    """
    @brief      Normalize a complete stage-to-glob mapping.
    @param[in]  raw JSON object text or a mapping.
    @return     Complete stage mapping with normalized rule lists.
    @exception  ValueError If the mapping is malformed, incomplete, or unknown.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("expected a JSON object mapping every stage to a list") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("expected a mapping from stage names to glob lists")
    if set(raw) != set(ALL_STAGES):
        missing = sorted(set(ALL_STAGES) - set(raw))
        unknown = sorted(set(raw) - set(ALL_STAGES))
        raise ValueError(f"stage mapping must be exact; missing={missing}, unknown={unknown}")
    return {stage: normalize_rule_list(raw[stage]) for stage in ALL_STAGES}


def _mode_validator(key: str):  # type: ignore[no-untyped-def]
    """@brief Build a FieldSpec validator for one ratified policy mode."""

    def validate(raw: Any) -> str:
        """@brief Normalize and validate one policy-mode answer."""
        if not isinstance(raw, str):
            raise ValueError("policy mode must be a string")
        value = raw.strip()
        choices = POLICY_MODE_CHOICES[key]
        if value not in choices:
            raise ValueError(f"expected one of: {', '.join(choices)}")
        return value

    return validate


def normalize_completion_level(raw: Any) -> str:
    """@brief Normalize a component baseline completion threshold."""
    if not isinstance(raw, str) or raw.strip() not in COMPLETION_LEVELS:
        raise ValueError(f"expected one of: {', '.join(COMPLETION_LEVELS)}")
    return raw.strip()


def _normalize_name_list(raw: Any, *, what: str) -> tuple[str, ...]:
    """
    @brief      Validate an explicit extensions/patterns list ("other" inputs).
    @param[in]  raw Candidate value: a sequence of non-empty strings.
    @param[in]  what Label used in error messages
                (``"source_extensions"``/``"test_file_patterns"``).
    @return     The values as a tuple of stripped strings.
    @exception  LanguagePresetError If the value is not a non-empty sequence of
                non-empty strings.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        raise LanguagePresetError(f"{what} must be a list of strings")
    items = tuple(str(part).strip() for part in raw)
    if not items or any(not part for part in items):
        raise LanguagePresetError(f"{what} must be a non-empty list of non-empty strings")
    return items


def _toml_string(value: str) -> str:
    """
    @brief      Render a Python string as a TOML basic string.
    @param[in]  value The string to render.
    @return     The double-quoted TOML representation with ``\\``, ``"`` and
                common control characters escaped.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _toml_value(value: Any) -> str:
    """
    @brief      Render one owned value (bool, string, or possibly-nested list).
    @param[in]  value The value to render.
    @return     The single-line TOML representation.
    @exception  WorkflowTomlError If the value's type is not one this generator
                emits.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _toml_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise WorkflowTomlError(f"cannot render value of type {type(value).__name__} as TOML")


def _line_ending(line: str) -> str:
    """
    @brief      Extract a line's newline sequence so a rewrite preserves it.
    @param[in]  line One line from ``splitlines(keepends=True)``.
    @return     ``"\\r\\n"``, ``"\\n"``, or ``""`` (final line without newline).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _scan_bracket_depth(fragment: str, depth: int) -> int:
    """
    @brief      Update array-bracket depth across one line of a TOML value.
    @details    String-aware: brackets inside basic (``"``) or literal (``'``)
                single-line strings are ignored, as is everything after a
                comment ``#`` outside a string. Multi-line (triple-quoted)
                strings are not supported — no owned value contains one.
    @param[in]  fragment The value text of one line.
    @param[in]  depth Bracket depth carried in from the previous line.
    @return     The bracket depth after this line.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    in_string: str | None = None
    escaped = False
    for char in fragment:
        if in_string is not None:
            if escaped:
                escaped = False
                continue
            if in_string == '"' and char == "\\":
                escaped = True
                continue
            if char == in_string:
                in_string = None
            continue
        if char in ('"', "'"):
            in_string = char
        elif char == "#":
            break
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
    return depth


def _apply_answers(base_text: str, owned: Mapping[tuple[str, str], Any]) -> str:
    """
    @brief      Rewrite only the owned ``(section, key)`` values in the base
                text, leaving every other line byte-identical.
    @details    The targeted-substitution strategy (module docstring): tracks
                the current ``[section]``, and for an owned key replaces its
                whole value span (consuming continuation lines of a multi-line
                array via :func:`_scan_bracket_depth`) with one generated
                ``key = value`` line, preserving the original indentation and
                line ending. Comments and untouched keys pass through
                unchanged.
    @param[in]  base_text The base workflow.toml text.
    @param[in]  owned Mapping of ``(section, key)`` to the new value.
    @return     The rewritten text.
    @exception  BaseFileMismatchError If any owned key was not found in the
                base text.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    lines = base_text.splitlines(keepends=True)
    output: list[str] = []
    replaced: set[tuple[str, str]] = set()
    section: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        section_match = _SECTION_RE.match(line)
        if section_match is not None:
            section = section_match.group("name").strip()
            output.append(line)
            index += 1
            continue
        key_match = _KEY_RE.match(line)
        target: tuple[str, str] | None = None
        if key_match is not None and section is not None:
            candidate = (section, key_match.group("key"))
            if candidate in owned:
                target = candidate
        if target is None:
            output.append(line)
            index += 1
            continue
        ending = _line_ending(line)
        depth = _scan_bracket_depth(key_match.group("value"), 0)
        index += 1
        while depth > 0 and index < len(lines):
            ending = _line_ending(lines[index])
            depth = _scan_bracket_depth(lines[index], depth)
            index += 1
        output.append(f"{key_match.group('indent')}{target[1]} = {_toml_value(owned[target])}{ending}")
        replaced.add(target)
    missing = sorted(set(owned) - replaced)
    if missing:
        detail = ", ".join(f"[{section}].{key}" for section, key in missing)
        raise BaseFileMismatchError(f"base workflow.toml is missing generator-owned key(s): {detail}")
    return "".join(output)


def _verify_unchanged_against_base(
    base_document: Mapping[str, Any],
    generated_document: Mapping[str, Any],
    owned: Mapping[tuple[str, str], Any],
) -> None:
    """
    @brief      Re-check invariant 4 (and the owned-value round trip) on the
                parsed output.
    @details    Every section and key of the base must exist in the output and
                vice versa; a non-owned key must equal the base value
                (invariant 4); an owned key must equal the intended answer — a
                disagreement there means the text rewrite and the intent
                diverged, which is exactly what the invariant-5 guard exists
                to catch.
    @param[in]  base_document Parsed base TOML.
    @param[in]  generated_document Parsed generated TOML.
    @param[in]  owned Mapping of ``(section, key)`` to the intended value.
    @return     None
    @exception  InvariantViolationError Invariant 4 for a drifted non-owned
                value or a structural change; invariant 5 for an owned value
                that does not match the intended answer.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if set(base_document) != set(generated_document):
        raise InvariantViolationError(4, "generated file's top-level sections differ from the base file's")
    for section, base_value in base_document.items():
        generated_value = generated_document[section]
        if not isinstance(base_value, Mapping):
            if generated_value != base_value:
                raise InvariantViolationError(4, f"top-level key {section!r} changed without an answer")
            continue
        if not isinstance(generated_value, Mapping) or set(base_value) != set(generated_value):
            raise InvariantViolationError(4, f"section [{section}] keys differ from the base file's")
        for key, base_entry in base_value.items():
            actual = generated_value[key]
            if (section, key) in owned:
                intended = owned[(section, key)]
                if actual != intended:
                    raise InvariantViolationError(
                        5,
                        f"[{section}].{key} round-trip disagreement: generated {actual!r}, intended {intended!r}",
                    )
            elif actual != base_entry:
                raise InvariantViolationError(4, f"[{section}].{key} changed without an answer")


def _empty_gate_warnings(gate_test_cmds: Sequence[Any], gate_lint_cmds: Sequence[Any]) -> tuple[GateWarning, ...]:
    """
    @brief      Build the structured empty-gate warnings (plan §7).
    @param[in]  gate_test_cmds Normalized [gates].test command list.
    @param[in]  gate_lint_cmds Normalized [gates].lint command list.
    @return     One :class:`GateWarning` per empty gate (possibly none).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    warnings: list[GateWarning] = []
    for gate, commands in (("test", gate_test_cmds), ("lint", gate_lint_cmds)):
        if not commands:
            warnings.append(
                GateWarning(
                    gate=gate,
                    message=f"gate '{gate}' is configured empty and will pass without checking anything",
                )
            )
    return tuple(warnings)


# PUBLIC API


# @brief The plan §7 answer table as FieldSpecs (keys are the frozen answer
#        names). Composes directly with ConsoleAsker/ScriptedAsker.ask_field
#        and guard_answers (T1.2); T4.3 drives the interview with these.
WORKFLOW_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        key="source_roots",
        description=(
            "Folders that hold your implementation code. The workflow uses them "
            "to know which files need requirement coverage and where the "
            "implementation stage may write."
        ),
        example="src, app",
        default=["src"],
        validator=normalize_roots,
    ),
    FieldSpec(
        key="test_roots",
        description=(
            "Folders that hold your tests. The workflow uses them to resolve "
            "linked tests and to know where the check stage may write."
        ),
        example="tests",
        default=["tests"],
        validator=normalize_roots,
    ),
    FieldSpec(
        key="language",
        description=(
            "Main programming language of the project. It selects which file "
            "extensions count as source code and how test files are recognized; "
            "choose 'other' to supply those directly."
        ),
        example="python",
        default="python",
        validator=normalize_language,
    ),
    FieldSpec(
        key="gate_test_cmds",
        description=(
            "Commands the workflow runs as the 'test' gate, each as a list of "
            "argv strings. An empty list is allowed but the gate then passes "
            "without checking anything."
        ),
        example='[["uv", "run", "pytest", "-q"]]',
        default=[],
        validator=normalize_gate_commands,
    ),
    FieldSpec(
        key="gate_lint_cmds",
        description=(
            "Commands the workflow runs as the 'lint' gate, each as a list of "
            "argv strings. An empty list is allowed but the gate then passes "
            "without checking anything."
        ),
        example='[["ruff", "check", "."]]',
        default=[],
        validator=normalize_gate_commands,
    ),
    FieldSpec(
        key="alignment_enabled",
        description=(
            "Whether the intent-alignment stage is recorded before requirement "
            "and spec work. Recommended on; turn off only if your process "
            "records intent elsewhere."
        ),
        example="true",
        default=True,
        validator=normalize_bool,
    ),
)

# @brief Explicit schema-version-2 policy answers. Empty rule collections are
#        still collected so disabled/unrestricted modes remain unambiguous.
WORKFLOW_FIELD_SPECS = (
    *WORKFLOW_FIELD_SPECS,
    FieldSpec(
        key="baseline_guard_mode",
        description="Component baseline guard mode.",
        example="disabled",
        default="disabled",
        validator=_mode_validator("baseline_guard_mode"),
    ),
    FieldSpec(
        key="baseline_minimum_completion_level",
        description="Minimum component completion level when the baseline guard is enforced.",
        example="baseline-usable",
        default="baseline-usable",
        validator=normalize_completion_level,
    ),
    FieldSpec(
        key="coverage_mode",
        description="Requirement coverage audit mode.",
        example="disabled",
        default="disabled",
        validator=_mode_validator("coverage_mode"),
    ),
    FieldSpec(
        key="coverage_roots",
        description="Coverable roots used only when coverage mode is enforce.",
        example='["src"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="coverage_exclude",
        description="Coverage exclusion globs used only when coverage is enforced.",
        example='["**/__init__.py"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="source_changes_mode",
        description="Adoption source-change policy mode.",
        example="unrestricted",
        default="unrestricted",
        validator=_mode_validator("source_changes_mode"),
    ),
    FieldSpec(
        key="alignment_protected_scope_mode",
        description="Alignment protected-scope mode.",
        example="disabled",
        default="disabled",
        validator=_mode_validator("alignment_protected_scope_mode"),
    ),
    FieldSpec(
        key="alignment_protected_scope_patterns",
        description="Protected alignment scope globs used only in enforce mode.",
        example='["infra/**"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="gates_mode",
        description="Validation gate execution mode.",
        example="disabled",
        default="disabled",
        validator=_mode_validator("gates_mode"),
    ),
    FieldSpec(
        key="secrets_mode",
        description="Secret scanning mode.",
        example="disabled",
        default="disabled",
        validator=_mode_validator("secrets_mode"),
    ),
    FieldSpec(
        key="secret_patterns",
        description="Python regular expressions used only when secret scanning is enforced.",
        example='["token-[0-9]+"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="protected_paths_mode",
        description="Protected repository path mode.",
        example="disabled",
        default="disabled",
        validator=_mode_validator("protected_paths_mode"),
    ),
    FieldSpec(
        key="protected_path_patterns",
        description="Protected repository path globs used only in enforce mode.",
        example='["private/**"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="protected_path_operations",
        description="Protected operations: read and/or write.",
        example='["read", "write"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="working_tree_mode",
        description="Working-tree blocker mode.",
        example="unrestricted",
        default="unrestricted",
        validator=_mode_validator("working_tree_mode"),
    ),
    FieldSpec(
        key="working_tree_blocked_patterns",
        description="Working-tree blocker globs used only in restricted mode.",
        example='["dist/**"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="write_access_mode",
        description="Write access policy mode.",
        example="unrestricted",
        default="unrestricted",
        validator=_mode_validator("write_access_mode"),
    ),
    FieldSpec(
        key="write_access_stages",
        description="Complete stage-to-glob JSON mapping for stage_restricted mode.",
        example='{"intake": [], "implementation": ["src/**"]}',
        default={stage: [] for stage in ALL_STAGES},
        validator=normalize_stage_map,
    ),
    FieldSpec(
        key="scope_mode",
        description="Repository scope checking mode.",
        example="unrestricted",
        default="unrestricted",
        validator=_mode_validator("scope_mode"),
    ),
    FieldSpec(
        key="scope_allowed_roots",
        description="Allowed roots used only in advisory or enforce scope mode.",
        example='["src"]',
        default=[],
        validator=normalize_rule_list,
    ),
    FieldSpec(
        key="delivery_mode",
        description="Outward-delivery preflight hook mode.",
        example="disabled",
        default="disabled",
        validator=_mode_validator("delivery_mode"),
    ),
    FieldSpec(
        key="delivery_command_patterns",
        description="Lowercase command fragments used only when delivery mode is enforce.",
        example='["git push"]',
        default=[],
        validator=normalize_rule_list,
    ),
)


def resolve_language_preset(
    language: str,
    *,
    source_extensions: Sequence[str] | None = None,
    test_file_patterns: Sequence[str] | None = None,
) -> LanguagePreset:
    """
    @brief      Resolve the effective [traceability] values for a language
                answer (plan §7 invariant 6).
    @details    A preset language takes its table entry, with explicit
                ``source_extensions``/``test_file_patterns`` overriding the
                preset when supplied (the escape hatch for e.g. colocated-test
                repos, plan §15 D12). ``"other"`` has no preset and requires
                both to be supplied explicitly.
    @param[in]  language A :data:`SUPPORTED_LANGUAGES` value (normalized via
                :func:`normalize_language` first if it came from raw input).
    @param[in]  source_extensions Explicit override / "other" requirement.
    @param[in]  test_file_patterns Explicit override / "other" requirement.
    @return     The effective :class:`LanguagePreset`.
    @exception  LanguagePresetError If the language is unsupported, or
                ``"other"`` is chosen without both explicit lists, or an
                explicit list is malformed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    try:
        language = normalize_language(language)
    except ValueError as exc:
        raise LanguagePresetError(str(exc)) from exc
    if language == "other":
        if source_extensions is None or test_file_patterns is None:
            raise LanguagePresetError(
                "language 'other' requires explicit source_extensions and test_file_patterns"
            )
        return LanguagePreset(
            language="other",
            source_extensions=_normalize_name_list(source_extensions, what="source_extensions"),
            test_file_patterns=_normalize_name_list(test_file_patterns, what="test_file_patterns"),
        )
    preset = LANGUAGE_PRESETS[language]
    if source_extensions is not None:
        preset = replace(preset, source_extensions=_normalize_name_list(source_extensions, what="source_extensions"))
    if test_file_patterns is not None:
        preset = replace(preset, test_file_patterns=_normalize_name_list(test_file_patterns, what="test_file_patterns"))
    return preset


# SCHEMA-VERSION-2 PUBLIC API


def _schema_closed(
    table: Mapping[str, Any], dotted_path: str, allowed: tuple[str, ...]
) -> None:
    """@brief Reject keys outside one closed schema table."""
    unknown = [key for key in table if key not in allowed]
    if unknown:
        key_path = f"{dotted_path}.{unknown[0]}" if dotted_path else unknown[0]
        raise InvariantViolationError(1, f"{key_path} is not part of schema version 2")


def _schema_table(
    document: Mapping[str, Any],
    dotted_path: str,
    allowed: tuple[str, ...],
    *,
    conditional: tuple[str, ...] = (),
) -> Mapping[str, Any]:
    """@brief Resolve and validate one required closed TOML table."""
    current: Any = document
    for name in dotted_path.split("."):
        if not isinstance(current, Mapping) or not isinstance(current.get(name), Mapping):
            raise InvariantViolationError(1, f"required table [{dotted_path}] is missing")
        current = current[name]
    _schema_closed(current, dotted_path, allowed)
    for key in allowed:
        if key not in conditional and key not in current:
            raise InvariantViolationError(1, f"{dotted_path}.{key} is missing")
    return current


def _schema_list(table: Mapping[str, Any], key: str, key_path: str) -> list[str]:
    """@brief Resolve a required list of strings from one schema table."""
    if key not in table:
        raise InvariantViolationError(1, f"{key_path} is missing")
    value = table[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InvariantViolationError(1, f"{key_path} must be a list of strings")
    result: list[str] = []
    for item in value:
        normalized = item.strip()
        if not normalized:
            raise InvariantViolationError(1, f"{key_path} contains an empty string")
        if normalized in result:
            raise InvariantViolationError(1, f"{key_path} contains duplicate values")
        result.append(normalized)
    return result


def _schema_string(table: Mapping[str, Any], key: str, key_path: str) -> str:
    """@brief Resolve one required non-empty string."""
    if key not in table or not isinstance(table[key], str):
        raise InvariantViolationError(1, f"{key_path} must be a non-empty string")
    value = table[key].strip()
    if not value:
        raise InvariantViolationError(1, f"{key_path} must be a non-empty string")
    return value


def _schema_boolean(table: Mapping[str, Any], key: str, key_path: str) -> bool:
    """@brief Resolve one required exact TOML Boolean."""
    if key not in table or type(table[key]) is not bool:
        raise InvariantViolationError(1, f"{key_path} must be a TOML Boolean")
    return bool(table[key])


def _schema_integer(table: Mapping[str, Any], key: str, key_path: str) -> int:
    """@brief Resolve one required exact TOML integer."""
    if key not in table or type(table[key]) is not int:
        raise InvariantViolationError(1, f"{key_path} must be a TOML integer")
    return int(table[key])


def _schema_choice(
    table: Mapping[str, Any], key: str, key_path: str, choices: tuple[str, ...]
) -> str:
    """@brief Resolve one required string from a closed choice set."""
    value = _schema_string(table, key, key_path)
    if value not in choices:
        raise InvariantViolationError(
            1, f"{key_path} must be one of {', '.join(choices)}"
        )
    return value


def _schema_mode(
    table: Mapping[str, Any], key_path: str, choices: tuple[str, ...]
) -> str:
    """@brief Resolve one required policy mode from a schema table."""
    return _schema_choice(table, "mode", f"{key_path}.mode", choices)


def _schema_normalize_path(
    value: str, key_path: str, *, allow_glob: bool = False
) -> str:
    """@brief Normalize one repository-relative path or glob."""
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = re.sub(r"/{2,}", "/", normalized).rstrip("/")
    if (
        not normalized
        or normalized.startswith(("/", "~"))
        or re.match(r"^[A-Za-z]:", normalized)
        or ".." in normalized.split("/")
    ):
        raise InvariantViolationError(
            1, f"{key_path} requires repository-relative paths without '..'"
        )
    if not allow_glob and any(character in normalized for character in "*?[]"):
        raise InvariantViolationError(1, f"{key_path} does not accept glob characters")
    return normalized


def _schema_validate_glob(value: str, key_path: str) -> None:
    """@brief Require balanced, non-nested bracket expressions in one glob."""
    depth = 0
    for character in value:
        if character == "[":
            if depth:
                raise InvariantViolationError(1, f"{key_path} contains a malformed glob")
            depth = 1
        elif character == "]":
            if not depth:
                raise InvariantViolationError(1, f"{key_path} contains a malformed glob")
            depth = 0
    if depth:
        raise InvariantViolationError(1, f"{key_path} contains a malformed glob")


def _schema_path(
    table: Mapping[str, Any], key: str, key_path: str, *, allow_glob: bool = False
) -> str:
    """@brief Resolve and normalize one repository-relative path or glob."""
    value = _schema_normalize_path(
        _schema_string(table, key, key_path), key_path, allow_glob=allow_glob
    )
    if allow_glob:
        _schema_validate_glob(value, key_path)
    return value


def _schema_paths(
    table: Mapping[str, Any],
    key: str,
    key_path: str,
    *,
    non_empty: bool,
    allow_glob: bool = False,
) -> list[str]:
    """@brief Resolve unique normalized repository paths or globs."""
    values = _schema_list(table, key, key_path)
    if non_empty and not values:
        raise InvariantViolationError(1, f"{key_path} must not be empty")
    result: list[str] = []
    for raw in values:
        normalized = _schema_normalize_path(raw, key_path, allow_glob=allow_glob)
        if allow_glob:
            _schema_validate_glob(normalized, key_path)
        if normalized in result:
            kind = "globs" if allow_glob else "paths"
            raise InvariantViolationError(
                1, f"{key_path} requires unique normalized repository {kind}"
            )
        result.append(normalized)
    return result


def _schema_rules(
    key_path: str,
    mode: str,
    rules: Sequence[str],
    *,
    unrestricted: tuple[str, ...] = ("disabled", "unrestricted"),
) -> None:
    """@brief Enforce empty-versus-non-empty rule semantics for one mode."""
    if mode in unrestricted and rules:
        raise InvariantViolationError(1, f"{key_path} must have empty rules in {mode} mode")
    if mode not in unrestricted and not rules:
        raise InvariantViolationError(1, f"{key_path} requires rules in {mode} mode")


def verify_workflow_schema(
    document: Mapping[str, Any], *, repo_root: Path | None = None
) -> None:
    """
    @brief      Validate the complete policy-neutral workflow schema version 2.
    @param[in]  document Parsed workflow.toml mapping.
    @param[in]  repo_root Optional repository root for filesystem-dependent
                baseline-manifest validation.
    @return     None.
    @exception  InvariantViolationError If the schema or policy is invalid.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    top_level = (
        "schema_version",
        "source",
        "tests",
        "requirements",
        "documentation",
        "components",
        "knowledge",
        "reports",
        "traceability",
        "adoption",
        "alignment",
        "gates",
        "guardrails",
    )
    _schema_closed(document, "", top_level)
    if type(document.get("schema_version")) is not int or document.get("schema_version") != SCHEMA_VERSION:
        raise InvariantViolationError(1, "schema_version must be integer 2")

    source = _schema_table(document, "source", ("roots",))
    tests = _schema_table(document, "tests", ("roots",))
    requirements = _schema_table(document, "requirements", ("roots",))
    documentation = _schema_table(
        document, "documentation", ("roots", "component_template")
    )
    components = _schema_table(
        document, "components", ("manifest", "baseline_guard")
    )
    knowledge = _schema_table(document, "knowledge", ("roots",))
    reports = _schema_table(document, "reports", ("adoption_root",))
    traceability = _schema_table(
        document,
        "traceability",
        ("language", "source_extensions", "test_file_patterns", "coverage"),
    )
    adoption = _schema_table(
        document,
        "adoption",
        ("allow_component_bundles", "max_bundle_components", "source_changes"),
    )
    alignment = _schema_table(
        document,
        "alignment",
        (
            "enabled",
            "pause_on_open_questions",
            "risk_threshold",
            "allow_recommended_responses",
            "protected_scope",
        ),
    )
    _schema_paths(source, "roots", "source.roots", non_empty=True)
    _schema_paths(tests, "roots", "tests.roots", non_empty=True)
    _schema_paths(requirements, "roots", "requirements.roots", non_empty=True)
    _schema_paths(documentation, "roots", "documentation.roots", non_empty=True)
    _schema_path(
        documentation,
        "component_template",
        "documentation.component_template",
    )
    component_manifest = _schema_path(components, "manifest", "components.manifest")
    _schema_paths(knowledge, "roots", "knowledge.roots", non_empty=True)
    _schema_path(reports, "adoption_root", "reports.adoption_root")

    _schema_string(traceability, "language", "traceability.language")
    if not _schema_list(traceability, "source_extensions", "traceability.source_extensions"):
        raise InvariantViolationError(1, "traceability.source_extensions must not be empty")
    _schema_paths(
        traceability,
        "test_file_patterns",
        "traceability.test_file_patterns",
        non_empty=True,
        allow_glob=True,
    )

    coverage = _schema_table(
        document,
        "traceability.coverage",
        ("mode", "coverable_roots", "exclude"),
    )
    coverage_mode = _schema_mode(coverage, "traceability.coverage", ("disabled", "enforce"))
    coverage_roots = _schema_paths(
        coverage,
        "coverable_roots",
        "traceability.coverage.coverable_roots",
        non_empty=False,
    )
    coverage_exclude = _schema_paths(
        coverage,
        "exclude",
        "traceability.coverage.exclude",
        non_empty=False,
        allow_glob=True,
    )
    if coverage_mode == "disabled" and (coverage_roots or coverage_exclude):
        raise InvariantViolationError(1, "disabled coverage requires empty roots and excludes")
    if coverage_mode == "enforce" and not coverage_roots:
        raise InvariantViolationError(1, "enforced coverage requires coverable roots")

    baseline = _schema_table(
        document,
        "components.baseline_guard",
        ("mode", "minimum_completion_level"),
        conditional=("minimum_completion_level",),
    )
    baseline_mode = _schema_mode(baseline, "components.baseline_guard", ("disabled", "enforce"))
    if baseline_mode == "disabled" and "minimum_completion_level" in baseline:
        raise InvariantViolationError(1, "disabled baseline guard must omit minimum_completion_level")
    if baseline_mode == "enforce":
        if "minimum_completion_level" not in baseline:
            raise InvariantViolationError(
                1, "enforced baseline guard requires a valid completion level"
            )
        _schema_choice(
            baseline,
            "minimum_completion_level",
            "components.baseline_guard.minimum_completion_level",
            COMPLETION_LEVELS,
        )
        if repo_root is not None:
            root = repo_root.resolve()
            manifest_path = (root / component_manifest).resolve()
            try:
                manifest_path.relative_to(root)
            except ValueError as exc:
                raise InvariantViolationError(
                    1, "components.manifest must stay inside the repository"
                ) from exc
            if not manifest_path.is_file():
                raise InvariantViolationError(
                    1, "enforced baseline guard requires a readable component manifest"
                )
            try:
                manifest_document = tomllib.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
            except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
                raise InvariantViolationError(
                    1, "components.manifest must be valid readable TOML"
                ) from exc
            if not isinstance(manifest_document, dict):
                raise InvariantViolationError(1, "components.manifest must be a TOML table")

    _schema_boolean(
        adoption, "allow_component_bundles", "adoption.allow_component_bundles"
    )
    max_bundle_components = _schema_integer(
        adoption, "max_bundle_components", "adoption.max_bundle_components"
    )
    if max_bundle_components <= 0:
        raise InvariantViolationError(
            1, "adoption.max_bundle_components must be greater than zero"
        )
    source_changes = _schema_table(document, "adoption.source_changes", ("mode",))
    _schema_mode(source_changes, "adoption.source_changes", ("unrestricted", "blocked"))

    alignment_enabled = _schema_boolean(alignment, "enabled", "alignment.enabled")
    _schema_boolean(
        alignment,
        "pause_on_open_questions",
        "alignment.pause_on_open_questions",
    )
    _schema_choice(
        alignment,
        "risk_threshold",
        "alignment.risk_threshold",
        ("low", "medium", "high"),
    )
    _schema_boolean(
        alignment,
        "allow_recommended_responses",
        "alignment.allow_recommended_responses",
    )
    protected_scope = _schema_table(
        document, "alignment.protected_scope", ("mode", "patterns")
    )
    alignment_scope_mode = _schema_mode(
        protected_scope, "alignment.protected_scope", ("disabled", "enforce")
    )
    alignment_patterns = _schema_paths(
        protected_scope,
        "patterns",
        "alignment.protected_scope.patterns",
        non_empty=False,
        allow_glob=True,
    )
    _schema_rules("alignment.protected_scope", alignment_scope_mode, alignment_patterns)
    if alignment_scope_mode == "enforce" and not alignment_enabled:
        raise InvariantViolationError(1, "protected alignment scope requires alignment.enabled = true")

    gates = _schema_table(document, "gates", ("mode", "test", "lint"))
    gates_mode = _schema_mode(gates, "gates", ("disabled", "enforce"))
    gate_test = _schema_list(gates, "test", "gates.test")
    gate_lint = _schema_list(gates, "lint", "gates.lint")
    if gates_mode == "disabled" and (gate_test or gate_lint):
        raise InvariantViolationError(1, "disabled gates require empty command lists")
    if gates_mode == "enforce" and not (gate_test or gate_lint):
        raise InvariantViolationError(1, "enforced gates require at least one command")

    _schema_table(
        document,
        "guardrails",
        ("secrets", "protected_paths", "working_tree", "write_access", "scope", "delivery"),
    )
    secrets = _schema_table(document, "guardrails.secrets", ("mode", "patterns"))
    secrets_mode = _schema_mode(secrets, "guardrails.secrets", ("disabled", "enforce"))
    secret_patterns = _schema_list(secrets, "patterns", "guardrails.secrets.patterns")
    _schema_rules("guardrails.secrets", secrets_mode, secret_patterns)
    for pattern in secret_patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise InvariantViolationError(1, f"invalid secret regex {pattern!r}: {exc}") from exc

    protected = _schema_table(
        document, "guardrails.protected_paths", ("mode", "patterns", "operations")
    )
    protected_mode = _schema_mode(
        protected, "guardrails.protected_paths", ("disabled", "enforce")
    )
    protected_patterns = _schema_paths(
        protected,
        "patterns",
        "guardrails.protected_paths.patterns",
        non_empty=False,
        allow_glob=True,
    )
    operations = _schema_list(
        protected, "operations", "guardrails.protected_paths.operations"
    )
    if any(operation not in {"read", "write"} for operation in operations):
        raise InvariantViolationError(1, "protected path operations accept only read and write")
    if protected_mode == "disabled" and (protected_patterns or operations):
        raise InvariantViolationError(1, "disabled protected paths require empty rules")
    if protected_mode == "enforce" and (not protected_patterns or not operations):
        raise InvariantViolationError(1, "enforced protected paths require patterns and operations")

    working_tree = _schema_table(
        document, "guardrails.working_tree", ("mode", "blocked_patterns")
    )
    working_mode = _schema_mode(
        working_tree, "guardrails.working_tree", ("unrestricted", "restricted")
    )
    blocked = _schema_paths(
        working_tree,
        "blocked_patterns",
        "guardrails.working_tree.blocked_patterns",
        non_empty=False,
        allow_glob=True,
    )
    _schema_rules("guardrails.working_tree", working_mode, blocked)

    write_access = _schema_table(
        document,
        "guardrails.write_access",
        ("mode", "stages"),
        conditional=("stages",),
    )
    write_mode = _schema_mode(
        write_access, "guardrails.write_access", ("unrestricted", "stage_restricted")
    )
    stages = write_access.get("stages")
    if write_mode == "unrestricted" and stages is not None:
        raise InvariantViolationError(1, "unrestricted write access must omit stages")
    if write_mode == "stage_restricted":
        if not isinstance(stages, Mapping) or set(stages) != set(ALL_STAGES):
            raise InvariantViolationError(1, "stage_restricted write access requires every stage")
        _schema_closed(stages, "guardrails.write_access.stages", ALL_STAGES)
        for stage in ALL_STAGES:
            _schema_paths(
                stages,
                stage,
                f"guardrails.write_access.stages.{stage}",
                non_empty=False,
                allow_glob=True,
            )

    scope = _schema_table(
        document, "guardrails.scope", ("mode", "allowed_roots")
    )
    scope_mode = _schema_mode(
        scope, "guardrails.scope", ("unrestricted", "advisory", "enforce")
    )
    scope_roots = _schema_paths(
        scope,
        "allowed_roots",
        "guardrails.scope.allowed_roots",
        non_empty=False,
    )
    _schema_rules("guardrails.scope", scope_mode, scope_roots)

    delivery = _schema_table(
        document, "guardrails.delivery", ("mode", "command_patterns")
    )
    delivery_mode = _schema_mode(delivery, "guardrails.delivery", ("disabled", "enforce"))
    delivery_patterns = _schema_list(
        delivery, "command_patterns", "guardrails.delivery.command_patterns"
    )
    normalized_delivery_patterns: list[str] = []
    for pattern in delivery_patterns:
        normalized = " ".join(pattern.lower().split())
        if normalized in normalized_delivery_patterns:
            raise InvariantViolationError(
                1, "guardrails.delivery.command_patterns contains normalized duplicates"
            )
        normalized_delivery_patterns.append(normalized)
    _schema_rules("guardrails.delivery", delivery_mode, normalized_delivery_patterns)


def verify_workflow_invariants(
    document: Mapping[str, Any],
    *,
    source_roots: Sequence[str] | None = None,
    test_roots: Sequence[str] | None = None,
    repo_root: Path | None = None,
) -> None:
    """
    @brief      Compatibility entry point for complete schema validation.
    @details    Source/test roots are accepted for existing callers, but schema
                version 2 no longer derives write or coverage policy from them.
    @param[in]  document Parsed workflow.toml mapping.
    @param[in]  source_roots Optional expected structural source roots.
    @param[in]  test_roots Optional expected structural test roots.
    @param[in]  repo_root Optional repository root for filesystem-dependent
                baseline-manifest validation.
    @return     None.
    @exception  InvariantViolationError If schema validation fails.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    1.1.0
    """
    verify_workflow_schema(document, repo_root=repo_root)
    if source_roots is not None and list(document["source"]["roots"]) != list(source_roots):
        raise InvariantViolationError(1, "[source].roots differs from the selected answers")
    if test_roots is not None and list(document["tests"]["roots"]) != list(test_roots):
        raise InvariantViolationError(1, "[tests].roots differs from the selected answers")


def _insert_key(text: str, section: str, key: str, value: Any) -> str:
    """@brief Insert a conditional key at the end of an existing TOML table."""
    lines = text.splitlines(keepends=True)
    header = f"[{section}]"
    start = next((index for index, line in enumerate(lines) if line.strip() == header), None)
    if start is None:
        raise BaseFileMismatchError(f"base workflow.toml is missing [{section}]")
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].lstrip().startswith("[")),
        len(lines),
    )
    ending = "\r\n" if "\r\n" in text else "\n"
    lines.insert(end, f"{key} = {_toml_value(value)}{ending}")
    return "".join(lines)


def _append_stage_table(text: str, stages: Mapping[str, Sequence[str]]) -> str:
    """@brief Append the conditional complete write-access stage table."""
    ending = "\r\n" if "\r\n" in text else "\n"
    suffix = "" if text.endswith(("\n", "\r")) else ending
    rendered = ["[guardrails.write_access.stages]"]
    rendered.extend(f"{stage} = {_toml_value(list(stages[stage]))}" for stage in ALL_STAGES)
    return text + suffix + ending + ending.join(rendered) + ending


def generate_workflow_toml(
    base_toml_text: str,
    *,
    source_roots: Sequence[str] | str,
    test_roots: Sequence[str] | str,
    language: str,
    gate_test_cmds: Sequence[Any],
    gate_lint_cmds: Sequence[Any],
    alignment_enabled: bool | str,
    source_extensions: Sequence[str] | None = None,
    test_file_patterns: Sequence[str] | None = None,
    baseline_guard_mode: str = "disabled",
    baseline_minimum_completion_level: str = "baseline-usable",
    coverage_mode: str = "disabled",
    coverage_roots: Sequence[str] = (),
    coverage_exclude: Sequence[str] = (),
    source_changes_mode: str = "unrestricted",
    alignment_protected_scope_mode: str = "disabled",
    alignment_protected_scope_patterns: Sequence[str] = (),
    gates_mode: str,
    secrets_mode: str = "disabled",
    secret_patterns: Sequence[str] = (),
    protected_paths_mode: str = "disabled",
    protected_path_patterns: Sequence[str] = (),
    protected_path_operations: Sequence[str] = (),
    working_tree_mode: str = "unrestricted",
    working_tree_blocked_patterns: Sequence[str] = (),
    write_access_mode: str = "unrestricted",
    write_access_stages: Mapping[str, Sequence[str]] | None = None,
    scope_mode: str = "unrestricted",
    scope_allowed_roots: Sequence[str] = (),
    delivery_mode: str = "disabled",
    delivery_command_patterns: Sequence[str] = (),
) -> GeneratedWorkflow:
    """
    @brief      Generate a complete schema-version-2 workflow configuration.
    @details    Structural answers never imply repository policy. Every policy
                mode and rule collection is emitted explicitly, and the
                generated text is parsed and validated before it is returned.
    @return     Generated text plus applicable gate warnings.
    @exception  WorkflowTomlError If the base or generated schema is invalid.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    1.1.0
    """
    roots = normalize_roots(source_roots)
    tests = normalize_roots(test_roots)
    preset = resolve_language_preset(
        language,
        source_extensions=source_extensions,
        test_file_patterns=test_file_patterns,
    )
    test_cmds = normalize_gate_commands(gate_test_cmds)
    lint_cmds = normalize_gate_commands(gate_lint_cmds)
    alignment = normalize_bool(alignment_enabled)
    modes = {
        "baseline_guard_mode": baseline_guard_mode,
        "coverage_mode": coverage_mode,
        "source_changes_mode": source_changes_mode,
        "alignment_protected_scope_mode": alignment_protected_scope_mode,
        "gates_mode": gates_mode,
        "secrets_mode": secrets_mode,
        "protected_paths_mode": protected_paths_mode,
        "working_tree_mode": working_tree_mode,
        "write_access_mode": write_access_mode,
        "scope_mode": scope_mode,
        "delivery_mode": delivery_mode,
    }
    for key, mode in modes.items():
        _mode_validator(key)(mode)

    normalized_rules = {
        "coverage_roots": normalize_rule_list(coverage_roots),
        "coverage_exclude": normalize_rule_list(coverage_exclude),
        "alignment_protected_scope_patterns": normalize_rule_list(alignment_protected_scope_patterns),
        "secret_patterns": normalize_rule_list(secret_patterns),
        "protected_path_patterns": normalize_rule_list(protected_path_patterns),
        "protected_path_operations": normalize_rule_list(protected_path_operations),
        "working_tree_blocked_patterns": normalize_rule_list(working_tree_blocked_patterns),
        "scope_allowed_roots": normalize_rule_list(scope_allowed_roots),
        "delivery_command_patterns": normalize_rule_list(delivery_command_patterns),
    }

    try:
        base_document = tomllib.loads(base_toml_text)
    except tomllib.TOMLDecodeError as exc:
        raise BaseFileMismatchError(f"base workflow.toml text is not valid TOML: {exc}") from exc
    verify_workflow_schema(base_document)

    owned: dict[tuple[str, str], Any] = {
        ("source", "roots"): roots,
        ("tests", "roots"): tests,
        ("traceability", "language"): preset.language,
        ("traceability", "source_extensions"): list(preset.source_extensions),
        ("traceability", "test_file_patterns"): list(preset.test_file_patterns),
        ("components.baseline_guard", "mode"): baseline_guard_mode,
        ("traceability.coverage", "mode"): coverage_mode,
        ("traceability.coverage", "coverable_roots"): normalized_rules["coverage_roots"],
        ("traceability.coverage", "exclude"): normalized_rules["coverage_exclude"],
        ("adoption.source_changes", "mode"): source_changes_mode,
        ("alignment", "enabled"): alignment,
        ("alignment.protected_scope", "mode"): alignment_protected_scope_mode,
        ("alignment.protected_scope", "patterns"): normalized_rules["alignment_protected_scope_patterns"],
        ("gates", "mode"): gates_mode,
        ("gates", "test"): test_cmds,
        ("gates", "lint"): lint_cmds,
        ("guardrails.secrets", "mode"): secrets_mode,
        ("guardrails.secrets", "patterns"): normalized_rules["secret_patterns"],
        ("guardrails.protected_paths", "mode"): protected_paths_mode,
        ("guardrails.protected_paths", "patterns"): normalized_rules["protected_path_patterns"],
        ("guardrails.protected_paths", "operations"): normalized_rules["protected_path_operations"],
        ("guardrails.working_tree", "mode"): working_tree_mode,
        ("guardrails.working_tree", "blocked_patterns"): normalized_rules["working_tree_blocked_patterns"],
        ("guardrails.write_access", "mode"): write_access_mode,
        ("guardrails.scope", "mode"): scope_mode,
        ("guardrails.scope", "allowed_roots"): normalized_rules["scope_allowed_roots"],
        ("guardrails.delivery", "mode"): delivery_mode,
        ("guardrails.delivery", "command_patterns"): normalized_rules["delivery_command_patterns"],
    }
    generated_text = _apply_answers(base_toml_text, owned)
    if baseline_guard_mode == "enforce":
        generated_text = _insert_key(
            generated_text,
            "components.baseline_guard",
            "minimum_completion_level",
            normalize_completion_level(baseline_minimum_completion_level),
        )
    if write_access_mode == "stage_restricted":
        if write_access_stages is None:
            raise ValueError("stage_restricted write access requires a complete stage mapping")
        generated_text = _append_stage_table(
            generated_text, normalize_stage_map(write_access_stages)
        )

    try:
        generated_document = tomllib.loads(generated_text)
    except tomllib.TOMLDecodeError as exc:
        raise InvariantViolationError(5, f"generated text failed to re-parse as TOML: {exc}") from exc
    verify_workflow_invariants(
        generated_document,
        source_roots=roots,
        test_roots=tests,
    )
    return GeneratedWorkflow(
        text=generated_text,
        warnings=(
            _empty_gate_warnings(test_cmds, lint_cmds)
            if gates_mode == "enforce"
            else ()
        ),
    )


# END OF FILE
