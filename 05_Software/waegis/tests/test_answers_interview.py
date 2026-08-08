#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_answers_interview.py
@brief Tests closed answers and install interview resolution.
@details Covers unknown keys, exact conflict paths, non-interactive missing
         aggregation, proposal provenance defaults, and custom-language needs.
"""

import json
from pathlib import Path

import pytest

from waegis.analyze import Proposal, RepositoryAnalysis
from waegis.answers import AnswersError, load_answers, parse_answers
from waegis.interview import collect_install_answers
from waegis.prompts import FieldSpec


class ScriptedAsker:
    """@brief Deterministic prompt fixture that records rendered fields."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = answers
        self.fields: list[FieldSpec] = []

    def ask(self, field: FieldSpec) -> str:
        self.fields.append(field)
        return self.answers.pop(0) if self.answers else field.default


def _analysis(tmp_path: Path) -> RepositoryAnalysis:
    return RepositoryAnalysis(
        tmp_path,
        "git",
        3,
        Proposal("python", "3 matching source files"),
        Proposal(["src"], "src exists"),
        Proposal(["tests"], "tests exists"),
        {},
    )


def test_json_answers_schema_and_conflicts_are_closed(tmp_path: Path) -> None:
    """@brief R1/R6 reject unknown and unsafe answers before planning."""
    path = tmp_path / "answers.json"
    path.write_text(
        json.dumps(
            {
                "answers_version": 2,
                "answers": {
                    "language": "python",
                    "source_roots": ["src"],
                    "test_roots": ["tests"],
                    "conflicts": {"AGENTS.md": "write-sidecar"},
                },
            }
        ),
        encoding="utf-8",
    )
    assert load_answers(path)["conflicts"] == {"AGENTS.md": "sidecar"}
    value = json.loads(path.read_text(encoding="utf-8"))
    value["answers"]["mystery"] = True
    with pytest.raises(AnswersError, match="unknown"):
        parse_answers(value)


def test_noninteractive_reports_all_required_basics() -> None:
    """@brief JSON/non-interactive mode never turns proposals into consent."""
    answers, missing = collect_install_answers({}, None, None, non_interactive=True)
    assert missing == ("language", "source_roots", "test_roots")
    assert answers["secrets_mode"] == "disabled"


def test_interactive_enter_accepts_displayed_proposals_with_provenance(tmp_path: Path) -> None:
    """@brief R6 Enter selects proposal-backed defaults and safe policy modes."""
    asker = ScriptedAsker([])
    answers, missing = collect_install_answers({}, _analysis(tmp_path), asker, non_interactive=False)
    assert missing == ()
    assert answers["language"] == "python"
    assert answers["source_roots"] == ["src"]
    assert answers["test_roots"] == ["tests"]
    assert "3 matching source files" in asker.fields[0].description
    assert answers["gate_test_mode"] == "disabled"
    keys = [field.key for field in asker.fields]
    assert keys[:5] == [
        "language",
        "source_roots",
        "test_roots",
        "alignment_enabled",
        "alignment_protected_scope_mode",
    ]
    assert "gate_test_commands" not in keys
    assert "quick_max_paths" not in keys
    assert "write_access_stages.intake" not in keys


def test_other_language_requires_extensions_and_patterns() -> None:
    """@brief Custom traceability never guesses file conventions."""
    _, missing = collect_install_answers(
        {"language": "other", "source_roots": ["src"], "test_roots": ["tests"]},
        None,
        None,
        non_interactive=True,
    )
    assert missing == ("source_extensions", "test_file_patterns")


def test_enabled_features_aggregate_every_missing_dependent_rule() -> None:
    """@brief R6 non-interactive mode reports all enabled conditional needs."""
    _, missing = collect_install_answers(
        {
            "language": "python",
            "source_roots": ["src"],
            "test_roots": ["tests"],
            "gate_test_mode": "enforce",
            "protected_paths_mode": "enforce",
            "write_access_mode": "stage_restricted",
            "coverage_mode": "enforce",
            "quick_changed_paths_mode": "advise",
        },
        None,
        None,
        non_interactive=True,
    )
    assert missing == (
        "coverage_exclude",
        "coverage_roots",
        "gate_test_commands",
        "protected_paths_operations",
        "protected_paths_patterns",
        "quick_max_paths",
        "write_access_stages",
    )


# END OF FILE
