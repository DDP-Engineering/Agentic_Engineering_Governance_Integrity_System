#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repo_workflow_toml.py
@brief Verify WAEGIS schema-version-3 workflow generation and validation.
@details Locks policy-neutral defaults, explicit restrictive modes, canonical
         gate encoding, comment preservation, and never-save-invalid behavior.
@author Eng. Dan Dumitru Pasare
@date 2026-07-22
@version 2.0.1
"""

# IMPORTS

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tomllib

import pytest

from waegis.commands.adopt import ADOPT_EXTRA_FIELD_SPECS
from waegis.io.prompts import ConsoleAsker, guard_answers
from waegis.repo.workflow_toml import (
    ALL_STAGES,
    BaseFileMismatchError,
    GATE_ORDER,
    InvariantViolationError,
    WORKFLOW_FIELD_SPECS,
    generate_workflow_toml,
    normalize_gate_commands,
    normalize_roots,
    normalize_stage_map,
    verify_workflow_invariants,
    verify_workflow_schema,
)

# CONSTANTS

REAL_TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "aegis"
    / "template"
    / ".agentic"
    / "workflow.toml"
)

# FIXTURES


@pytest.fixture(scope="module")
def base_text() -> str:
    """@brief Return the real AEGIS schema-version-3 template text."""
    return REAL_TEMPLATE.read_text(encoding="utf-8")


# HELPERS


def _generate(base_text: str, **overrides: object):  # type: ignore[no-untyped-def]
    """@brief Generate with explicit unrestricted policy answers by default."""
    answers: dict[str, object] = {
        "source_roots": ["src"],
        "test_roots": ["tests"],
        "language": "python",
        "gate_build_cmds": [],
        "gate_typecheck_cmds": [],
        "gate_lint_cmds": [],
        "gate_test_cmds": [],
        "gate_security_cmds": [],
        "alignment_enabled": True,
        "baseline_guard_mode": "disabled",
        "coverage_mode": "disabled",
        "source_changes_mode": "unrestricted",
        "alignment_protected_scope_mode": "disabled",
        "stage_form_retention": "discard",
        "check_execution": "external",
        "gate_build_mode": "disabled",
        "gate_typecheck_mode": "disabled",
        "gate_lint_mode": "disabled",
        "gate_test_mode": "disabled",
        "gate_security_mode": "disabled",
        "secrets_mode": "disabled",
        "protected_paths_mode": "disabled",
        "working_tree_mode": "unrestricted",
        "write_access_mode": "unrestricted",
        "scope_mode": "unrestricted",
        "delivery_mode": "disabled",
    }
    answers.update(overrides)
    return generate_workflow_toml(base_text, **answers)  # type: ignore[arg-type]


# TESTS


def test_real_template_is_complete_valid_schema_version_3(base_text: str) -> None:
    """@brief The shipped AEGIS template is the valid WAEGIS generation base."""
    document = tomllib.loads(base_text)
    verify_workflow_schema(document)
    assert document["schema_version"] == 3


def test_schema_rejection_diagnostic_is_version_neutral(base_text: str) -> None:
    """
    @brief      Keep schema guidance accurate when the wizard version changes.
    @return     None.
    @exception  AssertionError If the live diagnostic hardcodes an obsolete release.
    """
    document = tomllib.loads(base_text)
    document["schema_version"] = 2

    with pytest.raises(InvariantViolationError) as captured:
        verify_workflow_schema(document)

    message = str(captured.value)
    assert "WAEGIS 1.0" not in message
    assert "WAEGIS does not migrate schema 2" in message


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: document.__setitem__("unknown_policy", {}),
        lambda document: document["alignment"].__setitem__(
            "pause_on_open_questions", "yes"
        ),
        lambda document: document["guardrails"]["scope"].update(
            {"mode": "advisory", "allowed_roots": ["src", "./src"]}
        ),
        lambda document: document["guardrails"]["protected_paths"].update(
            {"mode": "enforce", "patterns": ["[broken"], "operations": ["write"]}
        ),
    ],
)
def test_schema_rejects_values_rejected_by_aegis_parser(
    base_text: str, mutation
) -> None:  # type: ignore[no-untyped-def]
    """@brief WAEGIS enforces the same closed types and normalized rules as AEGIS."""
    document = deepcopy(tomllib.loads(base_text))
    mutation(document)

    with pytest.raises(InvariantViolationError):
        verify_workflow_schema(document)


def test_enforced_baseline_requires_manifest_when_repo_root_is_known(
    base_text: str, tmp_path: Path
) -> None:
    """@brief Filesystem-aware validation rejects a missing enforced manifest."""
    document = tomllib.loads(base_text)
    document["components"]["baseline_guard"] = {
        "mode": "enforce",
        "minimum_completion_level": "baseline-usable",
    }

    with pytest.raises(InvariantViolationError, match="readable component manifest"):
        verify_workflow_schema(document, repo_root=tmp_path)


def test_default_generation_is_explicitly_policy_neutral(base_text: str) -> None:
    """@brief Structural answers do not infer any repository restrictions."""
    result = _generate(base_text, source_roots=["service"], test_roots=["checks"])
    document = tomllib.loads(result.text)

    assert document["source"]["roots"] == ["service"]
    assert document["tests"]["roots"] == ["checks"]
    assert document["traceability"]["coverage"]["coverable_roots"] == []
    assert document["guardrails"]["write_access"] == {"mode": "unrestricted"}
    assert document["guardrails"]["scope"]["allowed_roots"] == []
    assert document["guardrails"]["secrets"]["patterns"] == []
    assert result.warnings == ()
    verify_workflow_invariants(
        document, source_roots=["service"], test_roots=["checks"]
    )


def test_generator_preserves_unowned_comments_and_values(base_text: str) -> None:
    """@brief Targeted rewriting preserves comments and unowned structure."""
    marker = "# local operator note\n"
    customized = base_text.replace("[knowledge]\n", marker + "[knowledge]\n")

    result = _generate(customized)

    assert marker in result.text
    assert tomllib.loads(result.text)["reports"] == tomllib.loads(base_text)["reports"]


def test_gate_commands_are_emitted_as_canonical_strings(base_text: str) -> None:
    """@brief WAEGIS normalizes argv input into schema-3 gate commands."""
    result = _generate(
        base_text,
        gate_test_mode="enforce",
        gate_lint_mode="enforce",
        gate_test_cmds=[["uv", "run", "pytest", "-q"]],
        gate_lint_cmds=["ruff check ."],
    )
    gates = tomllib.loads(result.text)["gates"]

    assert gates["test"] == {
        "mode": "enforce",
        "commands": ["uv run pytest -q"],
    }
    assert gates["lint"] == {
        "mode": "enforce",
        "commands": ["ruff check ."],
    }
    assert normalize_gate_commands('["pytest -q"]') == ["pytest -q"]


def test_generator_supports_all_restrictive_policy_modes(base_text: str) -> None:
    """@brief Explicit rule answers generate every restrictive schema mode."""
    stage_map = {stage: [] for stage in ALL_STAGES}
    stage_map["implementation"] = ["src/**"]
    result = _generate(
        base_text,
        baseline_guard_mode="enforce",
        baseline_minimum_completion_level="baseline-usable",
        coverage_mode="enforce",
        coverage_roots=["src"],
        coverage_exclude=[],
        source_changes_mode="blocked",
        alignment_protected_scope_mode="enforce",
        alignment_protected_scope_patterns=["infra/**"],
        gate_test_mode="enforce",
        gate_test_cmds=["pytest -q"],
        secrets_mode="enforce",
        secret_patterns=["token-[0-9]+"],
        protected_paths_mode="enforce",
        protected_path_patterns=["private/**"],
        protected_path_operations=["read", "write"],
        working_tree_mode="restricted",
        working_tree_blocked_patterns=["dist/**"],
        write_access_mode="stage_restricted",
        write_access_stages=stage_map,
        scope_mode="enforce",
        scope_allowed_roots=["src"],
        delivery_mode="enforce",
        delivery_command_patterns=["git push"],
    )
    document = tomllib.loads(result.text)

    verify_workflow_schema(document)
    assert document["components"]["baseline_guard"]["mode"] == "enforce"
    assert document["guardrails"]["write_access"]["stages"]["validation"] == []
    assert document["guardrails"]["protected_paths"]["operations"] == ["read", "write"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"secrets_mode": "disabled", "secret_patterns": ["token"]},
        {"working_tree_mode": "restricted", "working_tree_blocked_patterns": []},
        {"coverage_mode": "enforce", "coverage_roots": []},
        {"scope_mode": "advisory", "scope_allowed_roots": []},
        {"gate_test_mode": "enforce", "gate_test_cmds": []},
    ],
)
def test_generator_rejects_inconsistent_policy_answers(
    base_text: str, overrides: dict[str, object]
) -> None:
    """@brief Never-save-invalid catches contradictory mode/rule answers."""
    with pytest.raises(InvariantViolationError):
        _generate(base_text, **overrides)


def test_invalid_base_is_rejected_before_generation() -> None:
    """@brief A malformed or obsolete base never becomes generated output."""
    with pytest.raises(BaseFileMismatchError):
        _generate("not = valid = toml")

    obsolete = "schema_version = 1\n"
    with pytest.raises(InvariantViolationError):
        _generate(obsolete)


def test_stage_map_requires_exact_supported_stage_set() -> None:
    """@brief Stage-restricted input cannot omit or invent stage names."""
    with pytest.raises(ValueError, match="stage mapping must be exact"):
        normalize_stage_map({"intake": []})

    complete = {stage: [] for stage in ALL_STAGES}
    assert tuple(normalize_stage_map(json.dumps(complete))) == ALL_STAGES


def test_structural_root_normalization_is_independent_from_policy() -> None:
    """@brief Root normalization remains strict without deriving guardrails."""
    assert normalize_roots(["src\\service/"]) == ["src/service"]
    with pytest.raises(ValueError):
        normalize_roots(["../outside"])
    with pytest.raises(ValueError):
        normalize_roots(["src", "./src"])


def test_questionnaire_exposes_every_policy_mode_and_rule_collection() -> None:
    """@brief New/adopt shared FieldSpecs make policy choices explicit."""
    keys = {spec.key for spec in WORKFLOW_FIELD_SPECS}
    required = {
        "baseline_guard_mode",
        "coverage_mode",
        "source_changes_mode",
        "alignment_protected_scope_mode",
        "stage_form_retention",
        "check_execution",
        "gate_build_mode",
        "gate_typecheck_mode",
        "gate_lint_mode",
        "gate_test_mode",
        "gate_security_mode",
        "secrets_mode",
        "protected_paths_mode",
        "working_tree_mode",
        "write_access_mode",
        "scope_mode",
        "delivery_mode",
        "secret_patterns",
        "protected_path_patterns",
        "protected_path_operations",
        "working_tree_blocked_patterns",
        "write_access_stages",
        "scope_allowed_roots",
        "coverage_roots",
        "coverage_exclude",
        "delivery_command_patterns",
    }
    assert required <= keys


def test_v1_answers_file_still_satisfies_the_interview_unchanged() -> None:
    """
    @brief      A V1-shaped ``--answers`` mapping (every key present, ship-open
                values) still satisfies :func:`guard_answers` against
                ``WORKFLOW_FIELD_SPECS`` after the consequence-style rendering
                change (0.9.0): keys, choices, validators, and defaults are
                untouched by adding ``FieldSpec.question``/rewriting
                ``description``.
    @return     None
    @exception  AssertionError If the fixture answers no longer validate, or if
                a normalized value silently changed.
    """
    answers: dict[str, object] = {
        "source_roots": ["src"],
        "test_roots": ["tests"],
        "language": "python",
        "alignment_enabled": True,
        "baseline_guard_mode": "disabled",
        "baseline_minimum_completion_level": "baseline-usable",
        "coverage_mode": "disabled",
        "coverage_roots": [],
        "coverage_exclude": [],
        "source_changes_mode": "unrestricted",
        "alignment_protected_scope_mode": "disabled",
        "alignment_protected_scope_patterns": [],
        "stage_form_retention": "discard",
        "check_execution": "external",
        "secrets_mode": "disabled",
        "secret_patterns": [],
        "protected_paths_mode": "disabled",
        "protected_path_patterns": [],
        "protected_path_operations": [],
        "working_tree_mode": "unrestricted",
        "working_tree_blocked_patterns": [],
        "write_access_mode": "unrestricted",
        "write_access_stages": {stage: [] for stage in ALL_STAGES},
        "scope_mode": "unrestricted",
        "scope_allowed_roots": [],
        "delivery_mode": "disabled",
        "delivery_command_patterns": [],
    }
    for name in GATE_ORDER:
        answers[f"gate_{name}_cmds"] = []
        answers[f"gate_{name}_mode"] = "disabled"
    normalized = guard_answers(WORKFLOW_FIELD_SPECS, answers)
    assert normalized["language"] == "python"
    assert normalized["source_roots"] == ["src"]
    assert normalized["write_access_stages"] == {stage: [] for stage in ALL_STAGES}
    assert normalized["gate_test_mode"] == "disabled"


def test_golden_question_rendering_for_representative_fields() -> None:
    """
    @brief      Golden transcript: rendering the interview text for six
                representative fields (one gate mode, ``secrets_mode``,
                ``write_access_mode``, ``language``, ``adoption_conflicts``,
                ``stage_form_retention``) through a scripted-stdin
                :class:`ConsoleAsker` shows the new question-line-plus-
                consequence rendering verbatim, with the operator taking every
                default (newline-only stdin).
    @return     None
    @exception  AssertionError If any expected question or consequence line is
                missing from the captured console output.
    """
    import io

    specs_by_key = {spec.key: spec for spec in WORKFLOW_FIELD_SPECS}
    adopt_specs_by_key = {spec.key: spec for spec in ADOPT_EXTRA_FIELD_SPECS}
    selected = [
        specs_by_key["gate_test_mode"],
        specs_by_key["secrets_mode"],
        specs_by_key["write_access_mode"],
        specs_by_key["language"],
        adopt_specs_by_key["adoption_conflicts"],
        specs_by_key["stage_form_retention"],
    ]
    stdin = io.StringIO("\n" * len(selected))
    stdout = io.StringIO()
    asker = ConsoleAsker(stdin=stdin, stdout=stdout)
    for spec in selected:
        asker.ask_field(spec)
    output = stdout.getvalue()

    assert "Enable the test gate? (e.g. disabled; default: disabled): " in output
    assert (
        "When enforced, verification runs the test commands below and a "
        "failure blocks validation until fixed or explicitly waived with a "
        "recorded reason. When disabled, reports honestly say 'disabled' — "
        "never 'passed'."
    ) in output

    assert "Scan for secrets before validation? (e.g. disabled; default: disabled): " in output
    assert (
        "When enforced, tool input matching the patterns below is blocked "
        "live during the session, and the working tree is scanned again at "
        "validation (waivable with a recorded reason). Disabled means no "
        "scanning."
    ) in output

    assert "Restrict which folders may be written during each stage? (e.g. unrestricted; default: unrestricted): " in output
    assert (
        "When stage_restricted, the agent hooks deny writes outside the "
        "folders allowed for the current stage below" in output
    )

    assert "Which language is this project mainly written in? (e.g. python; default: python): " in output
    assert "Selects which file extensions count as source code" in output

    assert (
        "Per-file conflict decisions for payload files that already exist and differ? "
        '(e.g. {"CLAUDE.md": "keep-local"}; default: {}): ' in output
    )
    assert "Nothing you own is ever silently overwritten" in output

    assert "Keep, version, or discard stage forms after import? (e.g. discard; default: discard): " in output
    assert (
        "versioned keeps every revision of a transient stage input form under "
        "the run folder (full audit trail); latest keeps only the newest; "
        "discard deletes the form after import (leanest repo)."
    ) in output


# END OF FILE
