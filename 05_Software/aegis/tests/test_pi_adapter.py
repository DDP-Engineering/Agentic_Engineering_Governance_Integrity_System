#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_pi_adapter.py
@brief Python-side parity checks for the Pi adapter package under template/.pi.
@details Verifies the Pi adapter files exist, the package manifest is valid and
         noncommercial-safe, the reused skills resolve to the shared engine, and
         the scaffolder copies the adapter while excluding vitest dev artifacts.
@author Eng. Dan Dumitru Pasare
@date 2026-06-20
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
TEMPLATE = PACKAGE_ROOT / "template"
PI_DIR = TEMPLATE / ".pi"
EXTENSION = PI_DIR / "extensions" / "agentic-guard"
SCAFFOLD_SCRIPT = REPO_ROOT / "02_Tools" / "create_project_from_template.py"

SKILL_NAMES = (
    "agentic-adoption",
    "agentic-development",
    "agentic-delivery",
    "regression-traceability",
    "documentation-audit",
    "python-codestyle-audit",
    "write-component-documentation",
)


def load_scaffold_module():
    """
    @brief      Load the scaffolder module from the tools script by file path.
    @return     Imported ``create_project_from_template`` module object.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    spec = importlib.util.spec_from_file_location("create_project_from_template", SCAFFOLD_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_manifest() -> dict:
    """
    @brief      Read and parse the Pi package manifest.
    @return     Parsed ``template/.pi/package.json`` as a dictionary.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return json.loads((PI_DIR / "package.json").read_text(encoding="utf-8"))


def test_pi_adapter_files_exist() -> None:
    """
    @brief      Handle the Pi adapter file presence workflow behavior.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    assert (PI_DIR / "package.json").exists()
    assert (PI_DIR / "settings.json").exists()
    assert (PI_DIR / "README.md").exists()
    assert (EXTENSION / "index.ts").exists()
    assert (EXTENSION / "bridge.ts").exists()
    assert (EXTENSION / "hook-bridge.ts").exists()
    assert (PI_DIR / "tests" / "hook-bridge.test.ts").exists()


def test_manifest_is_noncommercial_safe() -> None:
    """
    @brief      Verify the manifest keeps the package off public npm.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    manifest = read_manifest()
    assert manifest.get("private") is True
    assert "pi-package" in manifest.get("keywords", [])
    assert manifest.get("license") == "LicenseRef-PolyForm-Noncommercial-1.0.0"
    # A publish configuration would defeat the git/local-only distribution rule.
    assert "publishConfig" not in manifest


def test_manifest_declares_extension_and_reuses_shared_skills() -> None:
    """
    @brief      Verify the manifest wires the extension and reuses engine skills.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    manifest = read_manifest()
    pi_key = manifest.get("pi", {})
    assert pi_key.get("extensions") == ["./extensions"]
    # Skills point up at the shared engine; they are not duplicated under .pi/.
    assert pi_key.get("skills") == ["../.agentic/skills"]
    assert not (PI_DIR / "skills").exists()


def test_reused_skill_paths_resolve_to_shared_engine() -> None:
    """
    @brief      Verify the manifest skills path resolves to the six SKILL.md files.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    manifest = read_manifest()
    rel = manifest["pi"]["skills"][0]
    skills_dir = (PI_DIR / rel).resolve()
    assert skills_dir == (TEMPLATE / ".agentic" / "skills").resolve()
    for name in SKILL_NAMES:
        assert (skills_dir / name / "SKILL.md").exists()


def test_extension_sources_carry_license_header() -> None:
    """
    @brief      Verify each new TypeScript source carries the license header.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    for source in ("index.ts", "bridge.ts", "hook-bridge.ts"):
        text = (EXTENSION / source).read_text(encoding="utf-8")
        assert "PolyForm Noncommercial License 1.0.0" in text


def test_bridge_maps_pi_tools_to_python_hooks() -> None:
    """
    @brief      Verify the bridge references the four shared Python guard hooks.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    bridge = (EXTENSION / "bridge.ts").read_text(encoding="utf-8")
    for hook in (
        "guard_write_zone.py",
        "secret_scan.py",
        "delivery_preflight.py",
        "post_tool_evidence.py",
    ):
        assert hook in bridge
    # The four hooks the bridge drives must actually exist in the engine.
    hooks_dir = TEMPLATE / ".agentic" / "hooks"
    for hook in (
        "guard_write_zone.py",
        "secret_scan.py",
        "delivery_preflight.py",
        "post_tool_evidence.py",
    ):
        assert (hooks_dir / hook).exists()


def test_scaffold_copies_pi_adapter_and_skips_node_modules(tmp_path: Path) -> None:
    """
    @brief      Verify the scaffolder copies .pi/ but excludes vitest artifacts.
    @param[in]  tmp_path Temporary destination directory for the copied template.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    module = load_scaffold_module()
    target = tmp_path / "new-project"

    module.copy_template(target)

    assert (target / ".pi" / "package.json").exists()
    assert (target / ".pi" / "settings.json").exists()
    assert (target / ".pi" / "extensions" / "agentic-guard" / "index.ts").exists()
    assert (target / ".pi" / "extensions" / "agentic-guard" / "hook-bridge.ts").exists()
    assert (target / ".pi" / "tests" / "hook-bridge.test.ts").exists()
    # vitest dependencies must never land in a scaffolded project.
    assert not (target / ".pi" / "node_modules").exists()
