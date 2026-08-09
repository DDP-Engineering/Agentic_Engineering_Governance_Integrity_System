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
         authoritative, delegate repository policy to shared Python hooks,
         reuse shared skills, and contain no adapter-native denylist.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

from waegis.copier import enumerate_payload
from waegis_support import materialize_inventory

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PACKAGE_ROOT / "template"
QWEN_DIR = TEMPLATE / ".qwen"
HOOKS_DIR = TEMPLATE / ".agentic" / "hooks"

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
    "guard_read_path.py",
    "guard_write_zone.py",
    "secret_scan.py",
    "delivery_preflight.py",
    "post_tool_evidence.py",
)


# LOCAL HELPERS


def read_settings() -> dict:
    """
    @brief      Read and parse the Qwen Code project settings file.
    @return     Parsed ``template/.qwen/settings.json`` as a dictionary.
    @exception  None
    """
    return json.loads((QWEN_DIR / "settings.json").read_text(encoding="utf-8"))


def hook_commands(settings: dict) -> list[str]:
    """
    @brief      Collect every hook command string declared in the settings.
    @param[in]  settings Parsed Qwen settings mapping.
    @return     Flat list of the ``command`` fields across all hook events.
    @exception  None
    """
    commands: list[str] = []
    for entries in settings.get("hooks", {}).values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                command = hook.get("command")
                if isinstance(command, str):
                    commands.append(command)
    return commands


# TESTS


def test_qwen_adapter_files_exist() -> None:
    """
    @brief      Verify the Qwen adapter ships settings, skills, commands, and docs.
    @return     None.
    @exception  None
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
    """
    settings = read_settings()
    file_names = settings.get("context", {}).get("fileName")
    assert isinstance(file_names, list)
    assert file_names[0] == "AGENTS.md"
    assert "QWEN.md" in file_names


def test_settings_wire_shared_python_guards() -> None:
    """
    @brief      Verify the shared guard hooks are wired and present on disk.
    @return     None.
    @exception  None
    """
    commands = " ".join(hook_commands(read_settings()))
    for script in HOOK_SCRIPTS:
        assert script in commands
        assert (HOOKS_DIR / script).exists()


def test_settings_delegate_policy_without_native_denies() -> None:
    """
    @brief      Verify repository policy is delegated entirely to Python hooks.
    @return     None.
    @exception  None
    """
    settings = read_settings()
    assert "permissions" not in settings
    commands = " ".join(hook_commands(settings))
    assert "guard_read_path.py" in commands
    assert "secret_scan.py" in commands
    assert "delivery_preflight.py" in commands


def test_write_guard_matcher_covers_qwen_write_tool() -> None:
    """
    @brief      Verify the write-zone matcher targets Qwen's ``WriteFile`` tool.
    @return     None.
    @exception  None
    """
    pre_tool = read_settings()["hooks"]["PreToolUse"]
    write_entry = next(entry for entry in pre_tool if "guard_write_zone.py" in json.dumps(entry))
    assert "WriteFile" in write_entry["matcher"]


def test_hook_matchers_cover_friendly_and_raw_qwen_tool_names() -> None:
    """
    @brief      Verify T8 hooks cover friendly aliases and raw Qwen tool ids.
    @return     None.
    @exception  None
    """
    settings = read_settings()
    pre_tool = settings["hooks"]["PreToolUse"]
    post_tool = settings["hooks"]["PostToolUse"]
    read_entry = next(entry for entry in pre_tool if "guard_read_path.py" in json.dumps(entry))
    write_entry = next(entry for entry in pre_tool if "guard_write_zone.py" in json.dumps(entry))
    shell_entry = next(entry for entry in pre_tool if "delivery_preflight.py" in json.dumps(entry))
    evidence_entry = next(entry for entry in post_tool if "post_tool_evidence.py" in json.dumps(entry))
    write_hook_names = {hook["name"] for hook in write_entry["hooks"]}

    # Every Qwen tool that returns file content or file names, by canonical id
    # and by the display aliases older versions emit. Grep, glob, and directory
    # listing are covered as well as the single-file read: a protected-read
    # policy that only intercepted `read_file` was bypassable by asking the same
    # host for the same bytes through its search tool. Asserted as a set so the
    # alternation may be reordered or extended without editing this test.
    read_matchers = set(read_entry["matcher"].split("|"))
    assert {
        "Read",
        "ReadFile",
        "read_file",
        "read_many_files",
        "grep_search",
        "Grep",
        "search_file_content",
        "glob",
        "Glob",
        "list_directory",
    } <= read_matchers
    assert write_entry["matcher"] == "Edit|WriteFile|write_file|replace|NotebookEdit"
    assert write_hook_names == {"agentic-guard-write-zone", "agentic-edit-secret-scan"}
    assert shell_entry["matcher"] == "Bash|run_shell_command"
    assert set(evidence_entry["matcher"].split("|")) == {
        "Bash",
        "run_shell_command",
        "Edit",
        "WriteFile",
        "write_file",
        "replace",
        "NotebookEdit",
    }


def test_skill_wrappers_reuse_shared_engine() -> None:
    """
    @brief      Verify each wrapper references the shared skill it adapts.
    @return     None.
    @exception  None
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
    """
    target = tmp_path / "new-project"

    inventory = enumerate_payload(TEMPLATE)
    materialize_inventory(TEMPLATE, target, inventory.records)

    assert (target / ".qwen" / "settings.json").exists()
    assert (target / ".qwen" / "README.md").exists()
    assert (target / "QWEN.md").exists()
    assert (target / ".qwen" / "skills" / "agentic-development" / "SKILL.md").exists()
    assert (target / ".qwen" / "commands" / "workflow-status.md").exists()


# END OF FILE
