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
@brief workflow.toml generator with write-zone invariants (plan §7, task T4.1).
@details The single generator serving both ``waegis new`` and ``waegis adopt``
         (only the answer *source* differs between the two modes). It takes the
         real template ``.agentic/workflow.toml`` text as its base, rewrites
         only the twelve keys the plan §7 answer table controls, and passes
         every other line through **byte-identical** — comments included.
@details **Rewrite strategy (documented decision).** ``tomllib`` is read-only
         and the stdlib has no comment-preserving TOML writer, so this module
         uses *targeted text substitution* (plan option (a)) rather than a
         structural re-emitter: a line scanner tracks the current ``[section]``
         and replaces only the value span of owned ``key = value`` assignments
         (bracket-balance consumption across lines, string-aware), leaving all
         other bytes untouched. Comments are therefore **preserved, not
         regenerated**. An owned key absent from the base raises
         :class:`BaseFileMismatchError` instead of silently emitting a file
         with missing settings.
@details **Never-save-invalid guard (plan §7 invariant 5).** The generated
         text is re-parsed with ``tomllib`` and invariants 1–4 are re-verified
         against the *parsed* result before :func:`generate_workflow_toml`
         returns; any disagreement raises :class:`InvariantViolationError`
         naming the failed invariant. :func:`verify_workflow_invariants`
         (invariants 1–3 on any parsed document) is public so ``waegis
         doctor`` (T6.1) reuses the exact same validator.
@details The module is pure text-in/text-out: the caller reads the base file
         and writes the result (T4.3's ``deploy.workflow-toml`` step, which
         also owns ``.gitkeep`` creation for missing roots — out of scope
         here). Empty gates are permitted but reported through the returned
         :class:`GateWarning` records (plan §7 "loud, recorded warning"); this
         module never prints or journals.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from ..io.prompts import FieldSpec

# CONSTANTS

# @brief Glob characters forbidden in configured roots (write-zone patterns
#        are derived from roots; a root that is itself a glob would corrupt
#        the derived `<root>/**` patterns).
_ROOT_FORBIDDEN_CHARS = frozenset("*?[]")

# @brief The write-zone pattern invariant 3 requires in [write_zones].implementation.
COMPONENT_DOCS_ZONE = ".agentic/knowledge/components/**"

# @brief The leading write-zone entry the base file's component-adoption list
#        starts with; preserved when the test-root globs are rewritten.
_AGENTIC_ZONE = ".agentic/**"

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


def normalize_gate_commands(raw: Any) -> list[list[str]]:
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
    @return     The normalized ``list[list[str]]``.
    @exception  ValueError If the value is not a list of argv lists, or a ``str``
                that is not valid JSON.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.2.0
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "gate commands must be valid JSON, a list of commands each a list of argv "
                'strings, e.g. [["uv", "run", "pytest", "-q"]]'
            ) from exc
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("gate commands must be a list of commands, each a list of argv strings")
    commands: list[list[str]] = []
    for command in raw:
        if isinstance(command, str) or not isinstance(command, Sequence):
            raise ValueError("each gate command must be a list of argv strings, e.g. [\"uv\", \"run\", \"pytest\", \"-q\"]")
        argv = [str(part) for part in command]
        if not argv or any(not part for part in argv):
            raise ValueError("a gate command must be a non-empty list of non-empty argv strings")
        commands.append(argv)
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


def verify_workflow_invariants(
    document: Mapping[str, Any],
    *,
    source_roots: Sequence[str],
    test_roots: Sequence[str],
) -> None:
    """
    @brief      Verify plan §7 invariants 1–3 on a parsed workflow.toml
                document.
    @details    Public on purpose: ``waegis doctor`` (T6.1) re-runs exactly
                this validator against an installed repo's workflow.toml
                (typically passing the document's own ``[source].roots`` /
                ``[tests].roots`` as the expected roots). Invariants —
                1: every source root appears as ``<root>/**`` in
                ``[write_zones].implementation`` and verbatim in
                ``[traceability].coverable_roots``; 2: every test root appears
                as ``<root>/**`` in ``[write_zones].check`` and in
                ``[write_zones].component-adoption``; 3:
                ``[write_zones].implementation`` contains
                ``.agentic/knowledge/components/**``.
    @param[in]  document Parsed TOML document (``tomllib`` output shape).
    @param[in]  source_roots Expected implementation roots.
    @param[in]  test_roots Expected test roots.
    @return     None
    @exception  InvariantViolationError Naming the failed invariant (1–3); a
                missing section/key is reported under the invariant that
                needs it.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """

    def _entry(section: str, key: str, invariant: int) -> Any:
        """
        @brief      Fetch document[section][key] or fail the given invariant.
        @param[in]  section TOML section name.
        @param[in]  key Key within the section.
        @param[in]  invariant Invariant number to report on absence.
        @return     The value at ``document[section][key]``.
        @exception  InvariantViolationError If the section or key is absent.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        table = document.get(section)
        if not isinstance(table, Mapping) or key not in table:
            raise InvariantViolationError(invariant, f"[{section}].{key} is missing")
        return table[key]

    implementation = _entry("write_zones", "implementation", 1)
    coverable = _entry("traceability", "coverable_roots", 1)
    for root in source_roots:
        if f"{root}/**" not in implementation:
            raise InvariantViolationError(1, f"{root}/** missing from [write_zones].implementation")
        if root not in coverable:
            raise InvariantViolationError(1, f"{root!r} missing from [traceability].coverable_roots")
    check = _entry("write_zones", "check", 2)
    component_adoption = _entry("write_zones", "component-adoption", 2)
    for root in test_roots:
        if f"{root}/**" not in check:
            raise InvariantViolationError(2, f"{root}/** missing from [write_zones].check")
        if f"{root}/**" not in component_adoption:
            raise InvariantViolationError(2, f"{root}/** missing from [write_zones].component-adoption")
    if COMPONENT_DOCS_ZONE not in implementation:
        raise InvariantViolationError(3, f"{COMPONENT_DOCS_ZONE} missing from [write_zones].implementation")


def generate_workflow_toml(
    base_toml_text: str,
    *,
    source_roots: Sequence[str] | str,
    test_roots: Sequence[str] | str,
    language: str,
    gate_test_cmds: Sequence[Sequence[str]],
    gate_lint_cmds: Sequence[Sequence[str]],
    alignment_enabled: bool | str,
    source_extensions: Sequence[str] | None = None,
    test_file_patterns: Sequence[str] | None = None,
) -> GeneratedWorkflow:
    """
    @brief      Generate a workflow.toml from the template base text and the
                plan §7 answers, enforcing every §7 invariant before returning.
    @details    Pure text-in/text-out: the caller reads the base file (the
                template's ``.agentic/workflow.toml``) and writes the result.
                The answers are normalized with the same validators the
                :data:`WORKFLOW_FIELD_SPECS` use, so scripted/adopt-mode
                callers get identical validation to the interactive interview.
                Only the twelve generator-owned keys are rewritten (targeted
                text substitution — see module docstring); every other line,
                comments included, passes through byte-identical (invariant 4).
                The result is re-parsed with ``tomllib`` and invariants 1–4
                re-verified against the parsed document before returning
                (invariant 5, the never-save-invalid guard). Empty gates are
                permitted and reported via :class:`GateWarning` records that
                the calling step journals (this module never prints).
    @param[in]  base_toml_text The base workflow.toml text to rewrite.
    @param[in]  source_roots Implementation roots (list, or comma-separated
                string).
    @param[in]  test_roots Test roots (list, or comma-separated string).
    @param[in]  language A :data:`SUPPORTED_LANGUAGES` value.
    @param[in]  gate_test_cmds ``[gates].test`` commands (list of argv lists).
    @param[in]  gate_lint_cmds ``[gates].lint`` commands (list of argv lists).
    @param[in]  alignment_enabled ``[alignment].enabled`` (bool or yes/no
                string).
    @param[in]  source_extensions Explicit ``[traceability].source_extensions``
                (required for language ``"other"``, optional override
                otherwise).
    @param[in]  test_file_patterns Explicit
                ``[traceability].test_file_patterns`` (required for language
                ``"other"``, optional override otherwise).
    @return     A :class:`GeneratedWorkflow` with the generated text and any
                empty-gate warnings.
    @exception  ValueError If an answer fails validation (roots, gates,
                boolean).
    @exception  LanguagePresetError If the language is unsupported or
                ``"other"`` lacks explicit extensions/patterns (invariant 6).
    @exception  BaseFileMismatchError If the base text does not parse as TOML
                or lacks a generator-owned key.
    @exception  InvariantViolationError If the re-parsed output violates an
                invariant (never-save-invalid guard, invariant 5).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
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

    try:
        base_document = tomllib.loads(base_toml_text)
    except tomllib.TOMLDecodeError as exc:
        raise BaseFileMismatchError(f"base workflow.toml text is not valid TOML: {exc}") from exc

    owned: dict[tuple[str, str], Any] = {
        ("source", "roots"): roots,
        ("tests", "roots"): tests,
        ("traceability", "language"): preset.language,
        ("traceability", "source_extensions"): list(preset.source_extensions),
        ("traceability", "coverable_roots"): roots,
        ("traceability", "test_file_patterns"): list(preset.test_file_patterns),
        ("gates", "test"): test_cmds,
        ("gates", "lint"): lint_cmds,
        ("alignment", "enabled"): alignment,
        ("write_zones", "check"): [f"{root}/**" for root in tests],
        ("write_zones", "implementation"): [f"{root}/**" for root in roots] + [COMPONENT_DOCS_ZONE],
        ("write_zones", "component-adoption"): [_AGENTIC_ZONE] + [f"{root}/**" for root in tests],
    }

    generated_text = _apply_answers(base_toml_text, owned)

    try:
        generated_document = tomllib.loads(generated_text)
    except tomllib.TOMLDecodeError as exc:
        raise InvariantViolationError(5, f"generated text failed to re-parse as TOML: {exc}") from exc
    verify_workflow_invariants(generated_document, source_roots=roots, test_roots=tests)
    _verify_unchanged_against_base(base_document, generated_document, owned)

    return GeneratedWorkflow(
        text=generated_text,
        warnings=_empty_gate_warnings(test_cmds, lint_cmds),
    )


# END OF FILE
