#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_components.py
@brief Component manifest support tests.
@details Covers the approved component and bundle contract for adoption runs.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aegis import components as component_module
from aegis.components import audit_components, component_for_path, has_usable_baseline, load_components
from aegis.config import load_config


# LOCAL HELPERS


def write_manifest(repo_root: Path, body: str) -> None:
    """
    @brief      Write a component manifest for a temporary repository.
    @param[in]  repo_root Temporary repository root.
    @param[in]  body TOML body to write into the manifest.
    @return     None.
    @exception  None
    """
    agentic = repo_root / ".agentic"
    agentic.mkdir(exist_ok=True)
    (agentic / "components.toml").write_text(body, encoding="utf-8")


# TESTS


def test_no_manifest_returns_empty_components_and_bundles(tmp_path: Path) -> None:
    """
    @brief      Verify a missing manifest loads as an empty contract.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    manifest = load_components(tmp_path, ".agentic/components.toml")

    assert manifest.components == {}
    assert manifest.bundles == {}


def test_one_component_resolves_repo_relative_path(tmp_path: Path) -> None:
    """
    @brief      Verify T11 keeps explicit component subtree globs working.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.billing]
paths = ["src/billing/**"]
tests = ["tests/billing/**"]
adoption_status = "baseline-usable"
criticality = "high"
""",
    )

    manifest = load_components(tmp_path, ".agentic/components.toml")
    component = component_for_path(manifest, "src/billing/invoice_api/routes.py")

    assert component is not None
    assert component.name == "billing"
    assert component.paths == ["src/billing/**"]
    assert component.tests == ["tests/billing/**"]
    assert component.criticality == "high"
    assert component.adoption_status == "baseline-usable"


def test_bare_component_directory_matches_its_subtree(tmp_path: Path) -> None:
    """
    @brief      Verify T11 treats a bare component directory as a tree root.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.module]
paths = ["src/module"]
adoption_status = "baseline-usable"
""",
    )

    component = component_for_path(
        load_components(tmp_path, ".agentic/components.toml"), "src/module/impl.py"
    )

    assert component is not None
    assert component.name == "module"


def test_bare_component_directory_does_not_match_sibling(tmp_path: Path) -> None:
    """
    @brief      Verify T11 does not extend a bare directory into sibling names.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.module]
paths = ["src/module"]
adoption_status = "baseline-usable"
""",
    )

    component = component_for_path(
        load_components(tmp_path, ".agentic/components.toml"), "src/module2/x.py"
    )

    assert component is None


def test_baseline_usable_satisfies_baseline_comparison() -> None:
    """
    @brief      Verify baseline-usable satisfies an explicit baseline minimum.
    @return     None.
    @exception  None
    """
    assert has_usable_baseline("baseline-usable", "baseline-usable")


def test_discovered_is_below_usable_baseline() -> None:
    """
    @brief      Verify discovered status is below an explicit usable baseline.
    @return     None.
    @exception  None
    """
    assert not has_usable_baseline("discovered", "baseline-usable")


def test_bundle_with_six_components_emits_bundle_too_large(tmp_path: Path) -> None:
    """
    @brief      Verify oversized bundles are reported.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.one]
paths = ["src/one/**"]
[components.two]
paths = ["src/two/**"]
[components.three]
paths = ["src/three/**"]
[components.four]
paths = ["src/four/**"]
[components.five]
paths = ["src/five/**"]
[components.six]
paths = ["src/six/**"]

[bundles.large]
components = ["one", "two", "three", "four", "five", "six"]
reason = "Temporary broad adoption slice."
approved = true
adoption_status = "baseline-usable"
""",
    )

    issues = audit_components(tmp_path, load_config(tmp_path))

    assert "COMPONENT-BUNDLE-TOO-LARGE" in {issue.code for issue in issues}


def test_approved_bundle_with_two_components_is_valid(tmp_path: Path) -> None:
    """
    @brief      Verify a small approved bundle passes component audit.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.invoice_model]
paths = ["src/billing/invoice_model.py"]
adoption_status = "baseline-usable"
[components.invoice_repository]
paths = ["src/billing/invoice_repository.py"]
adoption_status = "baseline-usable"

[bundles.billing_read_path]
components = ["invoice_model", "invoice_repository"]
reason = "These components form the invoice read workflow."
approved = true
adoption_status = "baseline-usable"
""",
    )

    assert audit_components(tmp_path, load_config(tmp_path)) == []


def test_invalid_component_status_emits_component_status_invalid(tmp_path: Path) -> None:
    """
    @brief      Verify invalid component adoption status values are reported.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.billing]
paths = ["src/billing/**"]
adoption_status = "ready"
""",
    )

    issues = audit_components(tmp_path, load_config(tmp_path))

    assert "COMPONENT-STATUS-INVALID" in {issue.code for issue in issues}


def test_audit_components_uses_configured_manifest_by_default(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Verify component audit uses configured manifest path by default.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir(exist_ok=True)
    replace_workflow_toml(
        'manifest = ".agentic/components.toml"',
        'manifest = ".agentic/custom-components.toml"',
    )
    (agentic / "custom-components.toml").write_text(
        """
[components.billing]
paths = ["src/billing/**"]
adoption_status = "ready"
""",
        encoding="utf-8",
    )

    issues = audit_components(tmp_path, load_config(tmp_path))

    assert "COMPONENT-STATUS-INVALID" in {issue.code for issue in issues}


def test_local_scope_blocks_component_below_minimum_baseline(tmp_path: Path) -> None:
    """
    @brief      Verify local scope audit blocks behavior work in unadopted components.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.billing]
paths = ["src/billing/**"]
adoption_status = "discovered"
""",
    )

    issues = component_module.audit_local_scope(
        tmp_path,
        ["src/billing/invoice.py"],
        load_config(tmp_path),
        "baseline-usable",
    )

    assert [issue.code for issue in issues] == ["COMPONENT-BASELINE-MISSING"]
    assert issues[0].name == "billing"
    assert issues[0].path == "src/billing/invoice.py"


def test_local_scope_allows_component_with_usable_baseline(tmp_path: Path) -> None:
    """
    @brief      Verify local scope audit allows components with usable baselines.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.billing]
paths = ["src/billing/**"]
adoption_status = "baseline-usable"
""",
    )

    issues = component_module.audit_local_scope(
        tmp_path,
        ["src/billing/invoice.py"],
        load_config(tmp_path),
        "baseline-usable",
    )

    assert issues == []


def test_local_scope_allows_approved_bundle_with_usable_bundle_baseline(tmp_path: Path) -> None:
    """
    @brief      Verify a usable approved bundle can satisfy local scope baseline checks.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.invoice_model]
paths = ["src/billing/invoice_model.py"]
adoption_status = "discovered"
[components.invoice_repository]
paths = ["src/billing/invoice_repository.py"]
adoption_status = "discovered"

[bundles.billing_read_path]
components = ["invoice_model", "invoice_repository"]
reason = "These components form the invoice read workflow."
approved = true
adoption_status = "baseline-usable"
""",
    )

    issues = component_module.audit_local_scope(
        tmp_path,
        ["src/billing/invoice_model.py", "src/billing/invoice_repository.py"],
        load_config(tmp_path),
        "baseline-usable",
    )

    assert issues == []


def test_local_scope_blocks_approved_bundle_when_bundle_and_component_baselines_are_missing(tmp_path: Path) -> None:
    """
    @brief      Verify approved bundles still block when no referenced baseline is usable.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    write_manifest(
        tmp_path,
        """
[components.invoice_model]
paths = ["src/billing/invoice_model.py"]
adoption_status = "discovered"
[components.invoice_repository]
paths = ["src/billing/invoice_repository.py"]
adoption_status = "baseline-usable"

[bundles.billing_read_path]
components = ["invoice_model", "invoice_repository"]
reason = "These components form the invoice read workflow."
approved = true
adoption_status = "discovered"
""",
    )

    issues = component_module.audit_local_scope(
        tmp_path,
        ["src/billing/invoice_model.py", "src/billing/invoice_repository.py"],
        load_config(tmp_path),
        "baseline-usable",
    )

    assert [issue.code for issue in issues] == ["COMPONENT-BASELINE-MISSING"]
    assert issues[0].name == "invoice_model"


def test_config_reads_adoption_component_knowledge_and_report_settings(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Verify workflow config parses adoption component settings.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir(exist_ok=True)
    replace_workflow_toml("allow_component_bundles = true", "allow_component_bundles = false")
    replace_workflow_toml("max_bundle_components = 5", "max_bundle_components = 2")
    replace_workflow_toml(
        '[components.baseline_guard]\nmode = "disabled"',
        '[components.baseline_guard]\nmode = "enforce"\nminimum_completion_level = "baseline-strict"',
    )
    replace_workflow_toml(
        'manifest = ".agentic/components.toml"',
        'manifest = ".agentic/custom-components.toml"',
    )
    replace_workflow_toml(
        'roots = [".agentic/knowledge"]',
        'roots = [".agentic/custom-knowledge", "docs/architecture"]',
    )
    replace_workflow_toml(
        'adoption_root = ".agentic/reports/adoption"',
        'adoption_root = ".agentic/custom-reports/adoption"',
    )
    (agentic / "custom-components.toml").write_text("[components]\n", encoding="utf-8")

    cfg = load_config(tmp_path)

    assert cfg.component_manifest == ".agentic/custom-components.toml"
    assert cfg.component_baseline_guard.minimum_completion_level == "baseline-strict"
    assert not cfg.adoption_allow_component_bundles
    assert cfg.adoption_max_bundle_components == 2
    assert cfg.adoption_source_changes.mode == "unrestricted"
    assert cfg.knowledge_roots == (".agentic/custom-knowledge", "docs/architecture")
    assert cfg.adoption_report_root == ".agentic/custom-reports/adoption"


# END OF FILE
