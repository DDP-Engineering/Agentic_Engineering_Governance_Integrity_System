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
@brief Verify WAEGIS schema-version-2 workflow generation and validation.
@details Locks policy-neutral defaults, explicit restrictive modes, canonical
         gate encoding, comment preservation, and never-save-invalid behavior.
@author Eng. Dan Dumitru Pasare
@date 2026-07-22
@version 1.1.0
"""

# IMPORTS

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tomllib

import pytest

from waegis.repo.workflow_toml import (
    ALL_STAGES,
    BaseFileMismatchError,
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
    """@brief Return the real AEGIS schema-version-2 template text."""
    return REAL_TEMPLATE.read_text(encoding="utf-8")


# HELPERS


def _generate(base_text: str, **overrides: object):  # type: ignore[no-untyped-def]
    """@brief Generate with explicit unrestricted policy answers by default."""
    answers: dict[str, object] = {
        "source_roots": ["src"],
        "test_roots": ["tests"],
        "language": "python",
        "gate_test_cmds": [],
        "gate_lint_cmds": [],
        "alignment_enabled": True,
        "baseline_guard_mode": "disabled",
        "coverage_mode": "disabled",
        "source_changes_mode": "unrestricted",
        "alignment_protected_scope_mode": "disabled",
        "gates_mode": "disabled",
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


def test_real_template_is_complete_valid_schema_version_2(base_text: str) -> None:
    """@brief The shipped AEGIS template is the valid WAEGIS generation base."""
    document = tomllib.loads(base_text)
    verify_workflow_schema(document)
    assert document["schema_version"] == 2


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
    """@brief WAEGIS accepts legacy argv input but emits schema-2 strings."""
    result = _generate(
        base_text,
        gates_mode="enforce",
        gate_test_cmds=[["uv", "run", "pytest", "-q"]],
        gate_lint_cmds=["ruff check ."],
    )
    gates = tomllib.loads(result.text)["gates"]

    assert gates["mode"] == "enforce"
    assert gates["test"] == ["uv run pytest -q"]
    assert gates["lint"] == ["ruff check ."]
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
        gates_mode="enforce",
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
        {"gates_mode": "enforce", "gate_test_cmds": [], "gate_lint_cmds": []},
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
        "gates_mode",
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


# END OF FILE
