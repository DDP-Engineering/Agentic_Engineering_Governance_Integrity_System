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
         noncommercial-safe, repository policy is delegated to shared Python
         hooks, and scaffolding excludes vitest dev artifacts.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

from waegis.payload.copier import copy_payload

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PACKAGE_ROOT / "template"
PI_DIR = TEMPLATE / ".pi"
EXTENSION = PI_DIR / "extensions" / "agentic-guard"

SKILL_NAMES = (
    "agentic-adoption",
    "agentic-development",
    "agentic-delivery",
    "regression-traceability",
    "documentation-audit",
    "python-codestyle-audit",
    "write-component-documentation",
)


# LOCAL HELPERS


def read_manifest() -> dict:
    """
    @brief      Read and parse the Pi package manifest.
    @return     Parsed ``template/.pi/package.json`` as a dictionary.
    @exception  None
    """
    return json.loads((PI_DIR / "package.json").read_text(encoding="utf-8"))


# TESTS


def test_pi_adapter_files_exist() -> None:
    """
    @brief      Handle the Pi adapter file presence workflow behavior.
    @return     None.
    @exception  None
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
    """
    manifest = read_manifest()
    assert manifest.get("private") is True
    assert "pi-package" in manifest.get("keywords", [])
    assert manifest.get("license") == "LicenseRef-PolyForm-Noncommercial-1.0.0"
    # A publish configuration would defeat the git/local-only distribution rule.
    assert "publishConfig" not in manifest


def test_manifest_declares_the_supported_node_floor() -> None:
    """
    @brief      Verify the manifest declares a Node engine floor.
    @return     None.
    @details    The adapters use `node:`-prefixed builtin imports,
                `import.meta.url`, `pathToFileURL`, and nullish coalescing, so
                they do have a real minimum. Leaving it undeclared meant an
                interpreter too old to parse them failed at hook launch — read
                by every host as a *non-blocking* hook error, letting the tool
                call through unguarded.
    @exception  None
    """
    engines = read_manifest().get("engines", {})
    assert "node" in engines, "the Node requirement must be declared, not implied"
    assert engines["node"] == ">=18"


def test_manifest_declares_extension_and_reuses_shared_skills() -> None:
    """
    @brief      Verify the manifest wires the extension and reuses engine skills.
    @return     None.
    @exception  None
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
    """
    for source in ("index.ts", "bridge.ts", "hook-bridge.ts"):
        text = (EXTENSION / source).read_text(encoding="utf-8")
        assert "PolyForm Noncommercial License 1.0.0" in text


def test_bridge_maps_pi_tools_to_python_hooks() -> None:
    """
    @brief      Verify the bridge references every shared Python guard hook.
    @return     None.
    @exception  None
    """
    bridge = (EXTENSION / "bridge.ts").read_text(encoding="utf-8")
    for hook in (
        "guard_read_path.py",
        "guard_write_zone.py",
        "guard_shell_write.py",
        "secret_scan.py",
        "delivery_preflight.py",
        "post_tool_evidence.py",
    ):
        assert hook in bridge
    # Every hook the bridge drives must actually exist in the engine.
    hooks_dir = TEMPLATE / ".agentic" / "hooks"
    for hook in (
        "guard_read_path.py",
        "guard_write_zone.py",
        "guard_shell_write.py",
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
    """
    target = tmp_path / "new-project"

    copy_payload(TEMPLATE, target, mode="new")

    assert (target / ".pi" / "package.json").exists()
    assert (target / ".pi" / "settings.json").exists()
    assert (target / ".pi" / "extensions" / "agentic-guard" / "index.ts").exists()
    assert (target / ".pi" / "extensions" / "agentic-guard" / "hook-bridge.ts").exists()
    assert (target / ".pi" / "tests" / "hook-bridge.test.ts").exists()
    # vitest dependencies must never land in a scaffolded project.
    assert not (target / ".pi" / "node_modules").exists()


# END OF FILE
