#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file answers.py
@brief Closed versioned WAEGIS 3 answers-file parsing.
@details Accepts JSON or TOML, rejects unknown keys, and keeps path-specific
         conflict/migration consent outside persisted configuration answers.
"""

# IMPORTS

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Mapping

from .classify import normalize_conflict_decision
from .manifest import canonical_path
from .version import ANSWERS_VERSION


# CONSTANTS

KNOWN_ANSWER_KEYS = frozenset(
    {
        "language",
        "source_roots",
        "test_roots",
        "source_extensions",
        "test_file_patterns",
        "alignment_enabled",
        "alignment_protected_scope_mode",
        "alignment_protected_scope_patterns",
        "stage_form_retention",
        "check_execution",
        "gate_build_mode",
        "gate_build_commands",
        "gate_typecheck_mode",
        "gate_typecheck_commands",
        "gate_lint_mode",
        "gate_lint_commands",
        "gate_test_mode",
        "gate_test_commands",
        "gate_security_mode",
        "gate_security_commands",
        "secrets_mode",
        "secrets_patterns",
        "protected_paths_mode",
        "protected_paths_patterns",
        "protected_paths_operations",
        "working_tree_mode",
        "working_tree_blocked_patterns",
        "write_access_mode",
        "write_access_stages",
        "scope_mode",
        "scope_allowed_roots",
        "delivery_mode",
        "delivery_command_patterns",
        "coverage_mode",
        "coverage_roots",
        "coverage_exclude",
        "baseline_guard_mode",
        "minimum_completion_level",
        "adoption_source_changes_mode",
        "quick_changed_paths_mode",
        "quick_max_paths",
        "conflicts",
        "migration_v1",
    }
)
OPERATION_ANSWER_KEYS = frozenset({"conflicts", "migration_v1"})


# DATA MODELS / TYPEDEFINITIONS


class AnswersError(ValueError):
    """@brief Raised for malformed, unknown, or unsafe answer data."""


# EXPORTED FUNCTIONS / PUBLIC API


def parse_answers(value: object) -> dict[str, object]:
    """
    @brief Parse the closed top-level answers schema.
    @param[in] value Decoded JSON/TOML value.
    @return Validated answer mapping.
    @exception AnswersError If schema, keys, or conflicts are invalid.
    """
    if not isinstance(value, dict) or set(value) != {"answers_version", "answers"}:
        raise AnswersError("answers file must contain only answers_version and answers")
    if value["answers_version"] != ANSWERS_VERSION:
        raise AnswersError(f"unsupported answers version: {value['answers_version']!r}")
    raw = value["answers"]
    if not isinstance(raw, dict):
        raise AnswersError("answers must be an object/table")
    unknown = set(raw) - KNOWN_ANSWER_KEYS
    if unknown:
        raise AnswersError(f"unknown answer keys: {sorted(unknown)}")
    answers = dict(raw)
    conflicts = answers.get("conflicts", {})
    if not isinstance(conflicts, dict):
        raise AnswersError("conflicts must map exact paths to decisions")
    normalized_conflicts: dict[str, str] = {}
    folded: set[str] = set()
    for raw_path, raw_decision in conflicts.items():
        try:
            path = canonical_path(raw_path)
            decision = normalize_conflict_decision(raw_decision).value
        except (TypeError, ValueError) as exc:
            raise AnswersError(f"invalid conflict answer for {raw_path!r}") from exc
        if path.casefold() in folded:
            raise AnswersError(f"case-colliding conflict path: {path}")
        folded.add(path.casefold())
        normalized_conflicts[path] = decision
    if "conflicts" in answers:
        answers["conflicts"] = normalized_conflicts
    if "migration_v1" in answers and not isinstance(answers["migration_v1"], bool):
        raise AnswersError("migration_v1 must be boolean")
    return answers


def load_answers(path: Path | None) -> dict[str, object]:
    """@brief Load JSON/TOML answers, or return an empty mapping when absent."""
    if path is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text) if path.suffix.casefold() == ".json" else tomllib.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise AnswersError(f"cannot read answers file {path}: {exc}") from exc
    return parse_answers(value)


def configuration_answers(answers: Mapping[str, object]) -> dict[str, object]:
    """@brief Remove operation-only consent/conflict values from persistence."""
    return {key: value for key, value in answers.items() if key not in OPERATION_ANSWER_KEYS}


# END OF FILE
