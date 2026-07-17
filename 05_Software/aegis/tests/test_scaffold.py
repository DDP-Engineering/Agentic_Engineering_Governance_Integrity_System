#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_scaffold.py
@brief Workflow support module for test_scaffold.
@details Covers expected workflow behavior through focused pytest checks.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.4.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

import importlib.util


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
SCRIPT_PATH = REPO_ROOT / "02_Tools" / "create_project_from_template.py"


def load_scaffold_module():
    """
    @brief      Load scaffold module workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.3.0
    """
    spec = importlib.util.spec_from_file_location("create_project_from_template", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scaffold_copies_template_to_new_project(tmp_path: Path) -> None:
    """
    @brief      Handle test scaffold copies template to new project workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    module = load_scaffold_module()
    target = tmp_path / "new-project"

    copied = module.copy_template(target)

    assert copied
    assert (target / "AGENTS.md").exists()
    assert (target / "CHANGELOG.md").exists()
    assert (target / ".agentic" / "documents" / "PROMPT_CHEATSHEET.md").exists()
    assert (target / ".agentic" / "documents" / "WORKFLOW_CHEATSHEET.svg").exists()
    assert (target / ".agentic" / "workflow.toml").exists()
    assert (target / ".agentic" / "components.toml").exists()
    assert (target / ".codex" / "config.toml").exists()
    assert (target / "opencode.json").exists()
    assert (target / ".opencode" / "README.md").exists()
    assert (target / ".opencode" / "plugins" / "agentic-guard.mjs").exists()
    assert (target / ".opencode" / "commands" / "workflow-status.md").exists()
    assert (target / ".opencode" / "skills" / "agentic-development" / "SKILL.md").exists()
    assert (target / ".codex" / "skills" / "agentic-development" / "SKILL.md").exists()
    assert (target / ".codex" / "skills" / "agentic-adoption" / "SKILL.md").exists()
    assert (target / ".codex" / "skills" / "write-component-documentation" / "SKILL.md").exists()
    assert (target / ".agentic" / "skills" / "agentic-development" / "SKILL.md").exists()
    assert (target / ".agentic" / "skills" / "agentic-adoption" / "SKILL.md").exists()
    assert (target / ".agentic" / "skills" / "write-component-documentation" / "SKILL.md").exists()
    assert (target / "CLAUDE.md").exists()
    assert (target / ".claude" / "settings.json").exists()
    assert (target / ".claude" / "README.md").exists()
    assert (target / ".claude" / "agents" / "README.md").exists()
    assert (target / ".claude" / "skills" / "agentic-development" / "SKILL.md").exists()
    assert (target / ".claude" / "skills" / "agentic-delivery" / "SKILL.md").exists()
    assert (target / ".claude" / "skills" / "regression-traceability" / "SKILL.md").exists()
    assert (target / ".claude" / "skills" / "write-component-documentation" / "SKILL.md").exists()
    assert (target / ".claude" / "skills" / "documentation-audit" / "SKILL.md").exists()
    assert (target / ".claude" / "skills" / "python-codestyle-audit" / "SKILL.md").exists()
    assert (target / ".agentic" / "cli" / "pyproject.toml").exists()
    assert (target / ".agentic" / "cli" / "src" / "aegis" / "cli.py").exists()
    assert (target / ".agentic" / "tools" / "run_aegis.py").exists()
    assert (target / ".agentic" / "tools" / "run.ps1").exists()
    assert (target / ".agentic" / "tools" / "run.sh").exists()
    assert (target / ".agentic" / "tools" / "run_hook.mjs").exists()
    assert (target / ".agentic" / "tools" / "install.ps1").exists()
    assert (target / ".agentic" / "tools" / "install.sh").exists()
    assert (target / ".agentic" / "hooks" / "guard_write_zone.py").exists()
    assert (target / ".agentic" / "LICENSE.txt").exists()
    assert (target / ".agentic" / "knowledge" / "components" / "component_template.md").exists()
    assert (target / ".agentic" / "knowledge" / "components" / "index.md").exists()
    assert (target / ".agentic" / "reports" / "adoption" / "README.md").exists()
    assert not (target / "05_SoftwareDocu").exists()


def test_scaffold_ships_polyform_license_in_agentic(tmp_path: Path) -> None:
    """
    @brief      Ensure scaffolds are self-contained: agentic headers point at a
                bundled PolyForm LICENSE.txt under the .agentic folder.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-21
    @version    0.1.0
    """
    module = load_scaffold_module()
    target = tmp_path / "new-project"

    module.copy_template(target)

    license_path = target / ".agentic" / "LICENSE.txt"
    assert license_path.exists()
    license_text = license_path.read_text(encoding="utf-8")
    assert license_text.startswith("PolyForm Noncommercial License 1.0.0")

    # Headers must reference the bundled copy, not a bare/missing root LICENSE.txt.
    claude_md = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "the LICENSE.txt in the .agentic folder" in claude_md
    assert "See the LICENSE.txt file for full license details." not in claude_md


def test_scaffold_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    """
    @brief      Handle test scaffold refuses to overwrite existing file workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    module = load_scaffold_module()
    target = tmp_path / "new-project"
    target.mkdir()
    (target / "AGENTS.md").write_text("existing\n", encoding="utf-8")

    try:
        module.copy_template(target)
    except SystemExit as exc:
        assert "Refusing to overwrite" in str(exc)
    else:
        raise AssertionError("copy_template should reject existing files without force")


def test_scaffold_existing_repo_requires_existing_target(tmp_path: Path) -> None:
    """
    @brief      Ensure existing-repository adoption does not create typo paths.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-23
    @version    0.2.0
    """
    module = load_scaffold_module()
    target = tmp_path / "missing-existing-repo"

    try:
        module.copy_template(target, require_existing_target=True)
    except SystemExit as exc:
        assert "Existing repository directory not found" in str(exc)
    else:
        raise AssertionError("copy_template should require an existing repo when requested")


def test_scaffold_dry_run_does_not_write_files(tmp_path: Path) -> None:
    """
    @brief      Ensure dry-run previews adoption files without changing target.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-23
    @version    0.2.0
    """
    module = load_scaffold_module()
    target = tmp_path / "existing-repo"
    target.mkdir()

    copied = module.copy_template(target, dry_run=True, require_existing_target=True)

    assert copied
    assert target.exists()
    assert not (target / ".agentic").exists()
    assert list(target.iterdir()) == []


def test_scaffold_writes_install_manifest(tmp_path: Path) -> None:
    """
    @brief      Since T3.2 a real (non-dry-run) copy also writes the WAEGIS
                install manifest at <target>/.agentic/install-manifest.json.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    module = load_scaffold_module()
    target = tmp_path / "new-project"

    copied = module.copy_template(target)

    manifest_file = target / ".agentic" / "install-manifest.json"
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 1
    assert manifest["product"] == "aegis"
    assert manifest["mode"] == "new"
    # Every copied payload file is recorded; the manifest never lists itself.
    assert len(manifest["files"]) == len(copied)
    assert ".agentic/install-manifest.json" not in manifest["files"]
    assert manifest_file not in copied


def test_scaffold_dry_run_writes_no_manifest(tmp_path: Path) -> None:
    """
    @brief      A dry-run preview writes nothing, including no install
                manifest.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    module = load_scaffold_module()
    target = tmp_path / "existing-repo"
    target.mkdir()

    copied = module.copy_template(target, dry_run=True, require_existing_target=True)

    assert copied
    assert not (target / ".agentic" / "install-manifest.json").exists()
    assert list(target.iterdir()) == []


def test_scaffold_skips_generated_artifacts(tmp_path: Path) -> None:
    """
    @brief      Handle test scaffold skips generated artifacts workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    module = load_scaffold_module()
    template = tmp_path / "template"
    target = tmp_path / "new-project"
    (template / "pkg" / "__pycache__").mkdir(parents=True)
    (template / "pkg" / "__pycache__" / "module.pyc").write_bytes(b"cache")
    (template / ".pytest_cache").mkdir()
    (template / ".pytest_cache" / "README.md").write_text("cache\n", encoding="utf-8")
    (template / "src").mkdir()
    (template / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

    original = module.TEMPLATE_ROOT
    try:
        module.TEMPLATE_ROOT = template
        copied = module.copy_template(target)
    finally:
        module.TEMPLATE_ROOT = original

    assert copied == [target / "src" / "app.py"]
    assert (target / "src" / "app.py").exists()
    assert not (target / "pkg" / "__pycache__").exists()
    assert not (target / ".pytest_cache").exists()
