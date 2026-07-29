#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_opencode_adapter.py
@brief Python-side parity checks for the OpenCode adapter under template/.opencode.
@details Verifies the OpenCode adapter files exist, the default workflow agent
         points behavior-changing work at the shared neutral workflow skills,
         the plugin maps OpenCode tool events to policy-neutral shared Python
         hooks, and the scaffolder copies the adapter.
@author Eng. Dan Dumitru Pasare
@date 2026-07-02
@version 0.4.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

from waegis.payload.copier import copy_payload

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PACKAGE_ROOT / "template"
OPENCODE_DIR = TEMPLATE / ".opencode"

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

WORKFLOW_AGENT = "aegis"


# TESTS


def test_opencode_adapter_files_exist() -> None:
    """
    @brief      Verify the OpenCode adapter file layout exists.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.2.0
    """
    assert (TEMPLATE / "opencode.json").exists()
    assert (OPENCODE_DIR / "README.md").exists()
    assert (OPENCODE_DIR / "agents" / f"{WORKFLOW_AGENT}.md").exists()
    assert (OPENCODE_DIR / "plugins" / "agentic-guard.mjs").exists()
    assert (OPENCODE_DIR / "tests" / "agentic-guard.test.mjs").exists()
    for name in COMMAND_NAMES:
        assert (OPENCODE_DIR / "commands" / f"{name}.md").exists()
    for name in SKILL_NAMES:
        assert (OPENCODE_DIR / "skills" / name / "SKILL.md").exists()


def test_opencode_config_has_no_repository_policy_duplication() -> None:
    """
    @brief      Verify project config avoids model locks and repository rules.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.3.0
    """
    config = json.loads((TEMPLATE / "opencode.json").read_text(encoding="utf-8"))

    assert config["$schema"] == "https://opencode.ai/config.json"
    assert config["default_agent"] == WORKFLOW_AGENT
    assert "model" not in config
    assert "provider" not in config
    assert ".agentic/documents/CLI_API_REFERENCE.md" in config["instructions"]
    assert config["permission"]["skill"]["*"] == "allow"
    assert config["permission"]["read"] == {"*": "allow"}
    assert config["permission"]["edit"] == {"*": "allow"}
    assert config["permission"]["bash"] == {"*": "allow"}


def test_opencode_default_agent_loads_aegis() -> None:
    """
    @brief      Verify the default OpenCode agent hardens workflow selection.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.1.0
    """
    text = (OPENCODE_DIR / "agents" / f"{WORKFLOW_AGENT}.md").read_text(encoding="utf-8")

    assert "mode: primary" in text
    assert "`skill` tool" in text
    assert "agentic-development" in text
    assert "AGENTS.md" in text
    assert ".agentic/skills/agentic-development/SKILL.md" in text
    assert "one workflow gate" in text
    assert "stage stop format" in text
    assert "$skill-name" in text


def test_opencode_skill_wrappers_reuse_shared_engine_skills() -> None:
    """
    @brief      Verify OpenCode skill wrappers point to shared neutral skills.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-25
    @version    0.1.0
    """
    for name in SKILL_NAMES:
        text = (OPENCODE_DIR / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {name}" in text
        assert "AGENTS.md" in text
        assert f".agentic/skills/{name}/SKILL.md" in text
        assert "OpenCode invocation" in text
        assert "project-specific application name" not in text


def test_opencode_commands_delegate_to_project_local_runner() -> None:
    """
    @brief      Verify command prompts use the local workflow runner.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.2.0
    """
    expected_targets = {
        "workflow-status": "run status",
        "workflow-preflight": "verify run",
        "workflow-report": "delivery report",
    }
    for command_name, workflow_command in expected_targets.items():
        text = (OPENCODE_DIR / "commands" / f"{command_name}.md").read_text(encoding="utf-8")
        assert f"agent: {WORKFLOW_AGENT}" in text
        assert ".agentic/tools/run_aegis.py" in text
        assert workflow_command in text


def test_opencode_plugin_maps_tools_to_shared_hooks() -> None:
    """
    @brief      Verify the plugin references every shared Python guard hook.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-25
    @version    0.1.0
    """
    plugin = (OPENCODE_DIR / "plugins" / "agentic-guard.mjs").read_text(encoding="utf-8")
    for hook in (
        "guard_read_path.py",
        "guard_write_zone.py",
        "guard_shell_write.py",
        "secret_scan.py",
        "delivery_preflight.py",
        "post_tool_evidence.py",
    ):
        assert hook in plugin
        assert (TEMPLATE / ".agentic" / "hooks" / hook).exists()
    for tool_name in ("write", "edit", "apply_patch", "bash", "read"):
        assert tool_name in plugin
    assert "tool.execute.before" in plugin
    assert "tool.execute.after" in plugin


def test_opencode_plugin_delegates_protected_reads_without_native_patterns() -> None:
    """
    @brief      Verify reads use the shared hook without native patterns.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-25
    @version    0.2.0
    """
    plugin = (OPENCODE_DIR / "plugins" / "agentic-guard.mjs").read_text(encoding="utf-8")
    assert "guard_read_path.py" in plugin
    assert "PROTECTED_READ_PATTERNS" not in plugin
    assert "protectedPathDeny" not in plugin


def test_scaffold_copies_opencode_adapter(tmp_path: Path) -> None:
    """
    @brief      Verify the scaffolder copies the OpenCode adapter files.
    @param[in]  tmp_path Temporary destination directory for the copied template.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-02
    @version    0.3.0
    """
    target = tmp_path / "new-project"

    copy_payload(TEMPLATE, target, mode="new")

    assert (target / "opencode.json").exists()
    assert (target / ".opencode" / "README.md").exists()
    assert (target / ".opencode" / "agents" / f"{WORKFLOW_AGENT}.md").exists()
    assert (target / ".opencode" / "plugins" / "agentic-guard.mjs").exists()
    assert (target / ".opencode" / "commands" / "workflow-status.md").exists()
    assert (target / ".opencode" / "skills" / "agentic-development" / "SKILL.md").exists()
    assert not (target / ".opencode" / "node_modules").exists()


# END OF FILE
