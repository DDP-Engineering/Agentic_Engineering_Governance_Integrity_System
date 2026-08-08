#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_analysis_workflow.py
@brief Tests read-only analysis and comment-preserving workflow generation.
@details Uses local repository evidence and the real AEGIS schema-3 template.
"""

import subprocess
import tomllib
from pathlib import Path

from waegis.analyze import analyze_repository
from waegis.interview import SAFE_POLICY_DEFAULTS
from waegis.locate import resolve_payload
from waegis.runner import CommandRunner
from waegis.workflow_toml import ALL_STAGES, generate_workflow


def _git(repo: Path, *args: str) -> None:
    subprocess.run(("git", "-C", str(repo), *args), check=True, capture_output=True)


def test_analysis_proposes_only_present_evidence(tmp_path: Path) -> None:
    """@brief Adoption proposals include provenance and exclude AEGIS infrastructure."""
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / ".agentic").mkdir()
    (repo / "src" / "app.py").write_text("pass\n", encoding="utf-8")
    (repo / "tests" / "test_app.py").write_text("pass\n", encoding="utf-8")
    (repo / ".agentic" / "foreign.js").write_text("// ignore\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    _git(repo, "init")
    analysis = analyze_repository(repo, CommandRunner())
    assert analysis.language.value == "python"
    assert analysis.source_roots.value == ["src"]
    assert analysis.test_roots.value == ["tests"]
    assert analysis.gates["test"][0].value == ["python", "-m", "pytest"]
    assert analysis.file_count == 3


def test_workflow_generation_changes_only_owned_basic_lines() -> None:
    """@brief R2/R5 preserve comments and advanced fields while changing basics."""
    payload, _, _ = resolve_payload()
    base = (payload / ".agentic" / "workflow.toml").read_text(encoding="utf-8")
    answers = dict(SAFE_POLICY_DEFAULTS)
    answers.update({"language": "typescript", "source_roots": ["web/src"], "test_roots": ["web/tests"]})
    generated = generate_workflow(base, answers)
    value = tomllib.loads(generated)
    assert value["source"]["roots"] == ["web/src"]
    assert value["tests"]["roots"] == ["web/tests"]
    assert value["traceability"]["language"] == "typescript"
    assert value["gates"]["test"].get("impacted_command") is None
    assert "# Optional argv-only prefix" in generated
    assert '[requirements]\nroots = [".agentic/requirements"]' in generated


def test_workflow_generation_applies_restrictive_policy_and_optional_tables() -> None:
    """@brief R2/R5 every interviewed field maps to valid schema-3 TOML."""
    payload, _, _ = resolve_payload()
    base = (payload / ".agentic" / "workflow.toml").read_text(encoding="utf-8")
    answers = dict(SAFE_POLICY_DEFAULTS)
    answers.update(
        {
            "language": "python",
            "source_roots": ["src"],
            "test_roots": ["tests"],
            "alignment_protected_scope_mode": "enforce",
            "alignment_protected_scope_patterns": ["infra/**"],
            "gate_test_mode": "enforce",
            "gate_test_commands": ["python -m pytest"],
            "protected_paths_mode": "enforce",
            "protected_paths_patterns": ["private/**"],
            "protected_paths_operations": ["read", "write"],
            "write_access_mode": "stage_restricted",
            "write_access_stages": {
                stage: ["src/**"] if stage == "implementation" else []
                for stage in ALL_STAGES
            },
            "coverage_mode": "enforce",
            "coverage_roots": ["src"],
            "baseline_guard_mode": "enforce",
            "minimum_completion_level": "baseline-usable",
            "quick_changed_paths_mode": "advise",
            "quick_max_paths": 7,
        }
    )
    generated = generate_workflow(base, answers)
    value = tomllib.loads(generated)
    assert value["gates"]["test"]["commands"] == ["python -m pytest"]
    assert value["guardrails"]["write_access"]["stages"]["implementation"] == ["src/**"]
    assert value["components"]["baseline_guard"]["minimum_completion_level"] == "baseline-usable"
    assert value["quick"]["changed_paths"] == {"mode": "advise", "max_paths": 7}

    disabled = dict(answers)
    disabled.update(
        {
            "write_access_mode": "unrestricted",
            "quick_changed_paths_mode": "disabled",
            "baseline_guard_mode": "disabled",
        }
    )
    removed = generate_workflow(generated, disabled)
    parsed = tomllib.loads(removed)
    assert "stages" not in parsed["guardrails"]["write_access"]
    assert "quick" not in parsed
    assert "minimum_completion_level" not in parsed["components"]["baseline_guard"]


# END OF FILE
