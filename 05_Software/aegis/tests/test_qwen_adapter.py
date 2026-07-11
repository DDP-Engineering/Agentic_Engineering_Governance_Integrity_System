#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_qwen_adapter.py
@brief Python-side parity checks for the Qwen Code adapter under template/.qwen.
@details Verifies the Qwen adapter files exist, the settings keep AGENTS.md
         authoritative and wire the four shared Python guards, the reused skills
         resolve to the shared engine, the outward-delivery denies are present,
         and the scaffolder copies the adapter into a new project.
@author Eng. Dan Dumitru Pasare
@date 2026-07-01
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
QWEN_DIR = TEMPLATE / ".qwen"
HOOKS_DIR = TEMPLATE / ".agentic" / "hooks"
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

COMMAND_NAMES = (
    "workflow-status",
    "workflow-preflight",
    "workflow-report",
)

HOOK_SCRIPTS = (
    "guard_write_zone.py",
    "secret_scan.py",
    "delivery_preflight.py",
    "post_tool_evidence.py",
)


def load_scaffold_module():
    """
    @brief      Load the scaffolder module from the tools script by file path.
    @return     Imported ``create_project_from_template`` module object.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    spec = importlib.util.spec_from_file_location("create_project_from_template", SCAFFOLD_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_settings() -> dict:
    """
    @brief      Read and parse the Qwen Code project settings file.
    @return     Parsed ``template/.qwen/settings.json`` as a dictionary.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    return json.loads((QWEN_DIR / "settings.json").read_text(encoding="utf-8"))


def hook_commands(settings: dict) -> list[str]:
    """
    @brief      Collect every hook command string declared in the settings.
    @param[in]  settings Parsed Qwen settings mapping.
    @return     Flat list of the ``command`` fields across all hook events.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    commands: list[str] = []
    for entries in settings.get("hooks", {}).values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                command = hook.get("command")
                if isinstance(command, str):
                    commands.append(command)
    return commands


def test_qwen_adapter_files_exist() -> None:
    """
    @brief      Verify the Qwen adapter ships settings, skills, commands, and docs.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    assert (QWEN_DIR / "settings.json").exists()
    assert (QWEN_DIR / "README.md").exists()
    assert (TEMPLATE / "QWEN.md").exists()
    for name in SKILL_NAMES:
        assert (QWEN_DIR / "skills" / name / "SKILL.md").exists()
    for name in COMMAND_NAMES:
        assert (QWEN_DIR / "commands" / f"{name}.md").exists()


def test_settings_keep_agents_md_authoritative() -> None:
    """
    @brief      Verify the context file list loads AGENTS.md ahead of QWEN.md.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    settings = read_settings()
    file_names = settings.get("context", {}).get("fileName")
    assert isinstance(file_names, list)
    assert file_names[0] == "AGENTS.md"
    assert "QWEN.md" in file_names


def test_settings_wire_shared_python_guards() -> None:
    """
    @brief      Verify the four shared guard hooks are wired and present on disk.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    commands = " ".join(hook_commands(read_settings()))
    for script in HOOK_SCRIPTS:
        assert script in commands
        assert (HOOKS_DIR / script).exists()


def test_settings_deny_outward_delivery_and_secrets() -> None:
    """
    @brief      Verify the permission denies block publishing and secret files.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    denies = read_settings().get("permissions", {}).get("deny", [])
    assert "Bash(git push*)" in denies
    assert "Bash(gh pr create*)" in denies
    assert "Bash(git merge*)" in denies
    assert "Read(.env)" in denies


def test_write_guard_matcher_covers_qwen_write_tool() -> None:
    """
    @brief      Verify the write-zone matcher targets Qwen's ``WriteFile`` tool.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    pre_tool = read_settings()["hooks"]["PreToolUse"]
    write_entry = next(entry for entry in pre_tool if "guard_write_zone.py" in json.dumps(entry))
    assert "WriteFile" in write_entry["matcher"]


def test_skill_wrappers_reuse_shared_engine() -> None:
    """
    @brief      Verify each wrapper references the shared skill it adapts.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    for name in SKILL_NAMES:
        wrapper = (QWEN_DIR / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert f".agentic/skills/{name}/SKILL.md" in wrapper
        assert (TEMPLATE / ".agentic" / "skills" / name / "SKILL.md").exists()


def test_scaffold_copies_qwen_adapter(tmp_path: Path) -> None:
    """
    @brief      Verify the scaffolder copies the .qwen/ adapter into a project.
    @param[in]  tmp_path Temporary destination directory for the copied template.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    module = load_scaffold_module()
    target = tmp_path / "new-project"

    module.copy_template(target)

    assert (target / ".qwen" / "settings.json").exists()
    assert (target / ".qwen" / "README.md").exists()
    assert (target / "QWEN.md").exists()
    assert (target / ".qwen" / "skills" / "agentic-development" / "SKILL.md").exists()
    assert (target / ".qwen" / "commands" / "workflow-status.md").exists()
