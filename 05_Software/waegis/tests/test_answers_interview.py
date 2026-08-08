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

import io
import json
from pathlib import Path

import pytest

from waegis.analyze import Proposal, RepositoryAnalysis
from waegis.answers import AnswersError, load_answers, parse_answers
from waegis.interview import SAFE_POLICY_DEFAULTS, InterviewError, collect_install_answers
from waegis.prompts import ConsoleAsker, FieldSpec


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


def _complete_safe_answers() -> dict[str, object]:
    return {
        **SAFE_POLICY_DEFAULTS,
        "language": "python",
        "source_roots": ["src"],
        "test_roots": ["tests"],
    }


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


def test_live_required_list_reasks_after_empty_answer() -> None:
    """@brief R6 a live invalid conditional list preserves the interview."""
    supplied = _complete_safe_answers()
    supplied["gate_test_mode"] = "enforce"
    supplied.pop("gate_test_commands")
    responses = iter(("", "python -m pytest"))
    asker = ConsoleAsker(io.StringIO(), lambda _prompt: next(responses))

    answers, missing = collect_install_answers(supplied, None, asker, non_interactive=False)

    assert missing == ()
    assert answers["gate_test_commands"] == ["python -m pytest"]


@pytest.mark.parametrize("invalid", ["many", "0"])
def test_live_quick_max_paths_reasks_after_invalid_answer(invalid: str) -> None:
    """@brief R6 live conversion and positive-range failures re-ask."""
    supplied = _complete_safe_answers()
    supplied["quick_changed_paths_mode"] = "advise"
    supplied.pop("quick_max_paths")
    responses = iter((invalid, "7"))
    asker = ConsoleAsker(io.StringIO(), lambda _prompt: next(responses))

    answers, missing = collect_install_answers(supplied, None, asker, non_interactive=False)

    assert missing == ()
    assert answers["quick_max_paths"] == 7


@pytest.mark.parametrize(
    ("key", "value"),
    [("gate_test_commands", []), ("quick_max_paths", 0)],
)
def test_supplied_invalid_conditional_answer_remains_hard_error(key: str, value: object) -> None:
    """@brief R6 supplied invalid values never fall back to live prompting."""
    supplied = _complete_safe_answers()
    if key == "gate_test_commands":
        supplied["gate_test_mode"] = "enforce"
    else:
        supplied["quick_changed_paths_mode"] = "advise"
    supplied[key] = value
    asker = ScriptedAsker(["python -m pytest", "7"])

    with pytest.raises(InterviewError):
        collect_install_answers(supplied, None, asker, non_interactive=False)

    assert key not in [field.key for field in asker.fields]


# END OF FILE
