#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_requirements_traceability.py
@brief Workflow support module for test_requirements_traceability.
@details Covers expected workflow behavior through focused pytest checks.
@author Eng. Dan Dumitru Pasare
@date 2026-06-20
@version 0.1.1
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.requirements import (
    audit_coverage,
    audit_registry,
    audit_traceability,
    impact,
    load_all_requirements,
    resolve_test,
    sync_registry,
)
from aegis.config import load_config
from aegis.invariants import blocking_failures, evaluate
from aegis.store import load_graph

# CONSTANTS

HEADER = """| ID | Status | Priority | Requirement | Rationale | Related Components | Verification Method | Linked Tests | Created On | Last Updated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""


# LOCAL HELPERS


def run_cli(tmp_path: Path, *args: str) -> None:
    """
    @brief      Run CLI workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  args Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        main(list(args))
    finally:
        os.chdir(cwd)


def write_config(tmp_path: Path) -> None:
    """
    @brief      Write config workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    (agentic / "workflow.toml").write_text(
        """
[source]
roots = ["src"]

[tests]
roots = ["tests"]

[requirements]
roots = [".agentic/requirements"]

[traceability]
language = "python"
source_extensions = [".py"]
coverable_roots = ["src"]
coverable_exclude = ["__init__.py"]
test_file_patterns = ["test_*.py"]
""",
        encoding="utf-8",
    )
    (agentic / "requirements").mkdir()


def write_tested_module(tmp_path: Path) -> None:
    """
    @brief      Write tested module workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_calculator.py").write_text(
        'def test_add():\n    """REQ-FUNC-001"""\n    assert True\n',
        encoding="utf-8",
    )


def write_register(
    tmp_path: Path,
    linked_test: str = "tests/test_calculator.py::test_add",
    status: str = "Active",
) -> None:
    """
    @brief      Write register workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  linked_test Input value used by the workflow helper.
    @param[in]  status Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    register = tmp_path / ".agentic" / "requirements" / "functional.md"
    register.write_text(
        "# Functional Requirements\n\n"
        + HEADER
        + f"| REQ-FUNC-001 | {status} | Must | Addition returns a sum. | Demo coverage. | `src/calculator.py` | Automated test | `{linked_test}` | 2026-06-17 10:00 | 2026-06-17 10:00 |\n",
        encoding="utf-8",
    )
    (tmp_path / ".agentic" / "requirements" / "coverage_waivers.txt").write_text("", encoding="utf-8")


# TESTS


def test_parse_register_and_resolve_python_test(tmp_path: Path) -> None:
    """
    @brief      Handle test parse register and resolve python test workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path)
    rows = load_all_requirements(tmp_path)
    assert rows[0].req_id == "REQ-FUNC-001"
    assert rows[0].file_components() == ["src/calculator.py"]
    assert resolve_test(tmp_path, "tests/test_calculator.py::test_add", load_config(tmp_path))[0]
    assert audit_traceability(tmp_path) == []


def test_traceability_detects_missing_linked_test(tmp_path: Path) -> None:
    """
    @brief      Handle test traceability detects missing linked test workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path, "tests/test_calculator.py::test_missing")
    issues = audit_traceability(tmp_path)
    assert [issue.code for issue in issues] == ["REQ-LINK-MISSING", "REQ-NO-VERIFICATION"]


def test_coverage_detects_missing_requirement_and_waiver_states(tmp_path: Path) -> None:
    """
    @brief      Handle test coverage detects missing requirement and waiver states workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    (tmp_path / ".agentic" / "requirements" / "functional.md").write_text("# Functional Requirements\n\n" + HEADER, encoding="utf-8")
    waiver = tmp_path / ".agentic" / "requirements" / "coverage_waivers.txt"
    waiver.write_text("", encoding="utf-8")
    assert [issue.code for issue in audit_coverage(tmp_path)] == ["REQ-COVERAGE-MISSING"]

    waiver.write_text("src/calculator.py\n", encoding="utf-8")
    assert audit_coverage(tmp_path) == []

    write_register(tmp_path)
    waiver.write_text("src/calculator.py\n", encoding="utf-8")
    assert [issue.code for issue in audit_coverage(tmp_path)] == ["REQ-COVERAGE-STALE-WAIVER"]


def test_impact_maps_changed_file_to_requirement_and_test(tmp_path: Path) -> None:
    """
    @brief      Handle test impact maps changed file to requirement and test workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path)
    report = impact(tmp_path, ["src/calculator.py"])
    assert report[0]["file"] == "src/calculator.py"
    assert report[0]["uncovered"] is False
    assert report[0]["requirements"][0]["req_id"] == "REQ-FUNC-001"
    assert report[0]["linked_tests"] == ["tests/test_calculator.py::test_add"]


def test_registry_sync_and_audit(tmp_path: Path) -> None:
    """
    @brief      Handle test registry sync and audit workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path)
    assert audit_registry(tmp_path)
    result = sync_registry(tmp_path)
    assert result["requirement_count"] == 1
    assert result["check_count"] == 1
    assert audit_registry(tmp_path) == []


def test_registry_sync_writes_component_registry(tmp_path: Path) -> None:
    """
    @brief      Verify registry sync writes component adoption metadata.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path)
    (tmp_path / ".agentic" / "components.toml").write_text(
        """
[components.billing]
paths = ["src/billing/**"]
tests = ["tests/billing/**"]
adoption_status = "baseline-usable"
criticality = "high"

[bundles.billing_workflow]
components = ["billing"]
reason = "Billing files are adopted together."
approved = true
adoption_status = "baseline-usable"
""",
        encoding="utf-8",
    )

    result = sync_registry(tmp_path)
    components_path = tmp_path / ".agentic" / "registry" / "components.json"
    data = json.loads(components_path.read_text(encoding="utf-8"))

    assert result["component_count"] == 1
    assert components_path.exists()
    assert data["generated_from"] == ".agentic/components.toml"
    assert data["minimum_baseline"] == "baseline-usable"
    assert data["components"]["billing"]["name"] == "billing"
    assert data["components"]["billing"]["paths"] == ["src/billing/**"]
    assert data["components"]["billing"]["tests"] == ["tests/billing/**"]
    assert data["components"]["billing"]["adoption_status"] == "baseline-usable"
    assert data["bundles"]["billing_workflow"]["components"] == ["billing"]


def test_registry_sync_blocks_invalid_component_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify registry sync rejects invalid component manifests.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path)
    (tmp_path / ".agentic" / "components.toml").write_text(
        """
[components.billing]
paths = ["src/billing/**"]
adoption_status = "ready"
""",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as excinfo:
        run_cli(tmp_path, "registry", "sync")

    output = capsys.readouterr().out
    assert excinfo.value.code == 1
    assert "COMPONENT-STATUS-INVALID" in output


def test_registry_audit_reports_missing_component_registry_when_registry_exists(tmp_path: Path) -> None:
    """
    @brief      Verify registry audit requires component registry cache.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_config(tmp_path)
    registry = tmp_path / ".agentic" / "registry"
    registry.mkdir()
    for name in ["requirements.json", "checks.json", "features.json"]:
        (registry / name).write_text("{}\n", encoding="utf-8")

    issues = audit_registry(tmp_path)

    assert [(issue.code, issue.message) for issue in issues] == [
        ("REGISTRY-MISSING", "components registry cache is missing; run registry sync")
    ]


def test_delivery_preflight_blocks_invalid_component_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify delivery preflight rejects invalid component manifests.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path)
    (tmp_path / ".agentic" / "components.toml").write_text(
        """
[components.billing]
paths = ["src/billing/**"]
adoption_status = "ready"
""",
        encoding="utf-8",
    )
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "ready")

    with pytest.raises(SystemExit) as excinfo:
        run_cli(tmp_path, "delivery-preflight")

    output = capsys.readouterr().out
    assert excinfo.value.code == 1
    assert "COMPONENT-STATUS-INVALID" in output


def test_delivery_preflight_includes_traceability_gates(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """
    @brief      Handle test delivery preflight includes traceability gates workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path)
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")
    with pytest.raises(SystemExit) as exc:
        run_cli(tmp_path, "delivery-preflight")
    assert exc.value.code == 1
    assert "REGISTRY-MISSING" in capsys.readouterr().out

    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "preflight evidence")
    run_cli(tmp_path, "registry", "sync")
    capsys.readouterr()
    run_cli(tmp_path, "delivery-preflight")
    assert "Delivery preflight passed" in capsys.readouterr().out


def test_requirement_activate_updates_row_and_linked_tests(tmp_path: Path) -> None:
    """
    @brief      Handle test requirement activate updates row and linked tests workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path, "-", "Planned")
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")

    run_cli(
        tmp_path,
        "requirement",
        "activate",
        "--id",
        "REQ-FUNC-001",
        "--linked-test",
        "tests/test_calculator.py::test_add",
        "--verification",
        "Automated test",
    )

    row = load_all_requirements(tmp_path)[0]

    assert row.status == "Active"
    assert row.linked_tests == ["tests/test_calculator.py::test_add"]
    assert row.verification == "Automated test"
    assert audit_traceability(tmp_path) == []


def test_green_requirement_linked_check_requires_active_requirement(tmp_path: Path) -> None:
    """
    @brief      Handle test green requirement linked check requires active requirement workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    write_config(tmp_path)
    write_tested_module(tmp_path)
    write_register(tmp_path, "tests/test_calculator.py::test_add", "Planned")
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")
    run_cli(
        tmp_path,
        "add-spec",
        "--id",
        "S-0001",
        "--tag",
        "behavior",
        "--statement",
        "Addition returns a sum.",
        "--status",
        "accepted",
    )
    run_cli(
        tmp_path,
        "add-check",
        "--id",
        "C-0001",
        "--cites-spec",
        "S-0001",
        "--cites-requirement",
        "REQ-FUNC-001",
    )
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "fail",
        "--summary",
        "Red first",
        "--check-id",
        "C-0001",
    )
    run_cli(
        tmp_path,
        "record-evidence",
        "--kind",
        "test-run",
        "--result",
        "pass",
        "--summary",
        "Green after implementation",
        "--check-id",
        "C-0001",
    )

    graph = load_graph(tmp_path)
    failures = {item.id for item in blocking_failures(evaluate(tmp_path, graph))}

    assert "INV-8" in failures

    run_cli(
        tmp_path,
        "requirement",
        "activate",
        "--id",
        "REQ-FUNC-001",
        "--linked-test",
        "tests/test_calculator.py::test_add",
        "--verification",
        "Automated test",
    )
    graph = load_graph(tmp_path)

    assert blocking_failures(evaluate(tmp_path, graph)) == []


# END OF FILE
