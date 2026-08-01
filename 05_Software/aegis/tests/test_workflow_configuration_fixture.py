#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_workflow_configuration_fixture.py
@brief Verify the shared unrestricted workflow configuration fixture.
@details Locks the complete configuration shape so all consumers use one
         self-contained schema instead of reconstructing partial defaults.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tomllib

# CONSTANTS

EXPECTED_POLICY_MODES = {
    "alignment.protected_scope": "disabled",
    "components.baseline_guard": "disabled",
    "adoption.source_changes": "unrestricted",
    "gates.build": "disabled",
    "gates.typecheck": "disabled",
    "gates.lint": "disabled",
    "gates.test": "disabled",
    "gates.security": "disabled",
    "guardrails.secrets": "disabled",
    "guardrails.protected_paths": "disabled",
    "guardrails.working_tree": "unrestricted",
    "guardrails.write_access": "unrestricted",
    "guardrails.scope": "unrestricted",
    "guardrails.delivery": "disabled",
    "traceability.coverage": "disabled",
}

EXPECTED_STRUCTURAL_KEYS = {
    "source": {"roots"},
    "tests": {"roots"},
    "requirements": {"roots"},
    "documentation": {"roots", "component_template"},
    "components": {"manifest", "baseline_guard"},
    "knowledge": {"roots"},
    "reports": {"adoption_root"},
    "traceability": {"language", "source_extensions", "test_file_patterns", "coverage"},
    "adoption": {"allow_component_bundles", "max_bundle_components", "source_changes"},
    "alignment": {
        "enabled",
        "pause_on_open_questions",
        "risk_threshold",
        "allow_recommended_responses",
        "protected_scope",
    },
    "interface": {"stage_form_retention", "check_execution"},
    "gates": {"build", "typecheck", "lint", "test", "security"},
}

# LOCAL HELPERS


def _table(data: dict[str, object], dotted_path: str) -> dict[str, object]:
    """
    @brief      Resolve one dotted table path from parsed TOML.
    @param[in]  data Parsed TOML root table.
    @param[in]  dotted_path Dot-separated table path.
    @return     Resolved TOML table.
    """
    current = data
    for name in dotted_path.split("."):
        value = current[name]
        assert isinstance(value, dict)
        current = value
    return current


# TESTS


def test_unrestricted_workflow_fixture_has_complete_ratified_shape(
    unrestricted_workflow_toml: str,
) -> None:
    """
    @brief      Verify the shared fixture declares every ratified policy mode.
    @param[in]  unrestricted_workflow_toml Shared complete TOML fixture.
    @return     None.
    """
    data = tomllib.loads(unrestricted_workflow_toml)

    assert data["schema_version"] == 3
    for path, expected_keys in EXPECTED_STRUCTURAL_KEYS.items():
        assert set(_table(data, path)) == expected_keys
    for path, expected_mode in EXPECTED_POLICY_MODES.items():
        assert _table(data, path)["mode"] == expected_mode

    assert _table(data, "guardrails.secrets")["patterns"] == []
    assert _table(data, "guardrails.protected_paths")["patterns"] == []
    assert _table(data, "guardrails.protected_paths")["operations"] == []
    assert _table(data, "guardrails.working_tree")["blocked_patterns"] == []
    assert _table(data, "guardrails.scope")["allowed_roots"] == []
    assert _table(data, "guardrails.delivery")["command_patterns"] == []
    assert _table(data, "traceability.coverage")["coverable_roots"] == []
    assert _table(data, "traceability.coverage")["exclude"] == []
    assert _table(data, "alignment.protected_scope")["patterns"] == []
    for name in ("build", "typecheck", "lint", "test", "security"):
        assert _table(data, f"gates.{name}")["commands"] == []
    assert "stages" not in _table(data, "guardrails.write_access")
    assert "minimum_completion_level" not in _table(data, "components.baseline_guard")


def test_unrestricted_workflow_writer_installs_exact_shared_fixture(
    tmp_path: Path,
    unrestricted_workflow_toml: str,
    write_unrestricted_workflow_toml: Callable[[Path], Path],
) -> None:
    """
    @brief      Verify tests can install the shared fixture without rewriting it.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  unrestricted_workflow_toml Shared complete TOML fixture.
    @param[in]  write_unrestricted_workflow_toml Shared fixture writer.
    @return     None.
    """
    path = write_unrestricted_workflow_toml(tmp_path)

    assert path == tmp_path / ".agentic" / "workflow.toml"
    assert path.read_text(encoding="utf-8") == unrestricted_workflow_toml


# END OF FILE
