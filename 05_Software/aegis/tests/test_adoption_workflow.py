#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_adoption_workflow.py
@brief Adoption workflow CLI and invariant tests.
@details Covers local component scope checks and adoption status commands.
@author Eng. Dan Dumitru Pasare
@date 2026-06-22
@version 0.1.1
"""

# IMPORTS

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.invariants import blocking_failures, evaluate
from aegis.store import load_graph


# HELPER FUNCTIONS

def run_cli(tmp_path: Path, *args: str) -> None:
    """
    @brief      Run the workflow CLI from a temporary repository root.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  args Command-line arguments.
    @return     None.
    @exception  SystemExit Propagated from CLI commands that intentionally exit.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        main(list(args))
    finally:
        os.chdir(cwd)


def write_manifest(repo_root: Path, body: str) -> None:
    """
    @brief      Write a component manifest for a temporary repository.
    @param[in]  repo_root Temporary repository root.
    @param[in]  body TOML body to write into the manifest.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    agentic = repo_root / ".agentic"
    agentic.mkdir(exist_ok=True)
    (agentic / "components.toml").write_text(body, encoding="utf-8")


def write_billing_manifest(repo_root: Path, adoption_status: str) -> None:
    """
    @brief      Write a one-component billing manifest.
    @param[in]  repo_root Temporary repository root.
    @param[in]  adoption_status Adoption status for the billing component.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_manifest(
        repo_root,
        f"""
[components.billing]
paths = ["src/billing/**"]
tests = ["tests/billing/**"]
adoption_status = "{adoption_status}"
criticality = "high"
""",
    )


# TESTS

def test_adoption_scope_check_blocks_unadopted_component(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify scope-check exits one for unadopted mapped components.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "discovered")

    with pytest.raises(SystemExit) as excinfo:
        run_cli(tmp_path, "adoption", "scope-check", "src/billing/invoice.py")

    output = capsys.readouterr().out
    assert excinfo.value.code == 1
    assert "COMPONENT-BASELINE-MISSING" in output
    assert "billing" in output


def test_adoption_scope_check_passes_baseline_usable_component(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify scope-check exits zero for baseline usable components.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "baseline-usable")

    run_cli(tmp_path, "adoption", "scope-check", "src/billing/invoice.py")

    assert "OK: no component scope issues." in capsys.readouterr().out


def test_adoption_component_status_emits_json_with_components_and_bundles(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify component-status prints component and bundle JSON.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_manifest(
        tmp_path,
        """
[components.billing]
paths = ["src/billing/**"]
adoption_status = "baseline-usable"

[bundles.billing_workflow]
components = ["billing"]
reason = "Billing files are adopted together."
approved = true
adoption_status = "baseline-usable"
""",
    )

    run_cli(tmp_path, "adoption", "component-status")

    data = json.loads(capsys.readouterr().out)
    assert data["components"]["billing"]["adoption_status"] == "baseline-usable"
    assert data["bundles"]["billing_workflow"]["components"] == ["billing"]


def test_adoption_component_status_blocks_invalid_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify adoption status rejects invalid component manifests.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "ready")

    with pytest.raises(SystemExit) as excinfo:
        run_cli(tmp_path, "adoption", "component-status")

    output = capsys.readouterr().out
    assert excinfo.value.code == 1
    assert "COMPONENT-STATUS-INVALID" in output
    assert "billing" in output


def test_adoption_baseline_prints_markdown_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify baseline command prints concise Markdown summary.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "baseline-usable")

    run_cli(tmp_path, "adoption", "baseline")

    output = capsys.readouterr().out
    assert output.startswith("# Component Baseline")
    assert "billing" in output
    assert "baseline-usable" in output


def test_component_baseline_scope_invariant_blocks_unadopted_feature_scope(tmp_path: Path) -> None:
    """
    @brief      Verify feature runs block mapped unadopted component paths.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "discovered")
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Change invoice behavior")
    run_cli(tmp_path, "record-change", "--id", "CU-0001", "--path", "src/billing/invoice.py")

    graph = load_graph(tmp_path)
    failures = {item.id: item for item in blocking_failures(evaluate(tmp_path, graph))}

    assert "INV-9" in failures
    assert "COMPONENT-BASELINE-MISSING" in failures["INV-9"].message
    assert "billing" in failures["INV-9"].message


def test_component_baseline_scope_invariant_does_not_block_adoption_run(tmp_path: Path) -> None:
    """
    @brief      Verify adoption runs do not block on local baseline scope.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "discovered")
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    run_cli(tmp_path, "record-change", "--id", "CU-0001", "--path", "src/billing/invoice.py")

    graph = load_graph(tmp_path)
    results = {item.id: item for item in evaluate(tmp_path, graph)}

    assert results["INV-9"].holds
    assert "adoption runs" in results["INV-9"].message


def test_adoption_report_includes_baseline_for_adoption_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify adoption runs report component baseline status.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "baseline-usable")
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    capsys.readouterr()

    run_cli(tmp_path, "report")

    output = capsys.readouterr().out
    assert "## Adoption Baseline" in output
    assert "billing" in output
    assert "baseline-usable" in output


def test_report_includes_baseline_for_non_adoption_run_with_component_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify component manifests add baseline data to normal reports.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "baseline-usable")
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Change billing")
    capsys.readouterr()

    run_cli(tmp_path, "report")

    output = capsys.readouterr().out
    assert "## Adoption Baseline" in output
    assert "billing" in output
    assert "baseline-usable" in output


def test_adoption_report_lists_local_scope_findings_for_touched_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify report surfaces local component-scope findings.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_billing_manifest(tmp_path, "discovered")
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Change billing")
    run_cli(tmp_path, "record-change", "--id", "CU-0001", "--path", "src/billing/invoice.py")
    capsys.readouterr()

    run_cli(tmp_path, "report")

    output = capsys.readouterr().out
    assert "COMPONENT-BASELINE-MISSING" in output
    assert "src/billing/invoice.py" in output


def test_template_ships_adoption_report_readme() -> None:
    """
    @brief      Verify the template includes the adoption report directory guide.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    template_root = Path(__file__).resolve().parents[1] / "template"

    readme = template_root / ".agentic" / "reports" / "adoption" / "README.md"

    assert readme.exists()
    assert "adoption reports" in readme.read_text(encoding="utf-8").lower()


# END OF FILE
