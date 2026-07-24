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
@details T4 coverage verifies that every JSON-configured adapter which runs the
         write-zone guard for edit tools also runs the secret scan on the same
         matcher.
@details WP5 coverage requires every adapter to delegate repository read,
         write, secret, and delivery decisions to configured Python hooks and
         rejects native repository denylists in adapter settings or plugins.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest

from aegis import __version__
from waegis.payload.copier import (
    OverwriteRefusedError,
    TargetDirectoryMissingError,
    copy_payload,
)

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PACKAGE_ROOT / "template"
EDIT_HOOK_CONFIGS = (
    Path(".claude/settings.json"),
    Path(".codex/hooks.json"),
    Path(".qwen/settings.json"),
)
READ_HOOK_CONFIGS = EDIT_HOOK_CONFIGS


# TESTS


def test_embedded_cli_package_version_matches_pyproject() -> None:
    """
    @brief      Enforce T13 version parity for the embedded AEGIS CLI package.
    @return     None.
    @exception  AssertionError If package and project metadata versions differ.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.1
    """
    pyproject_path = PACKAGE_ROOT / "template" / ".agentic" / "cli" / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert __version__ == "1.2.0"
    assert __version__ == pyproject["project"]["version"]


@pytest.mark.parametrize("config_relative_path", EDIT_HOOK_CONFIGS)
def test_edit_hook_configs_pair_write_zone_and_secret_scan(config_relative_path: Path) -> None:
    """
    @brief      Require secret scanning wherever edit tools run the write-zone guard.
    @param[in]  config_relative_path Adapter hook configuration below the template root.
    @return     None.
    @details    T4 regression coverage: Claude Code, Codex, and Qwen previously
                scanned only Bash input for secrets, while OpenCode and Pi also
                scanned full edit/write input. Pairing both hooks inside the
                same matcher prevents adapter drift and catches pasted secrets
                before a file write occurs.
    @exception  AssertionError If an edit matcher lacks the secret-scan hook or
                Codex lacks its Windows command twin.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    config_path = PACKAGE_ROOT / "template" / config_relative_path
    data = json.loads(config_path.read_text(encoding="utf-8"))
    edit_hook_groups = [
        group
        for group in data["hooks"]["PreToolUse"]
        if any(
            "guard_write_zone.py" in hook.get("command", "")
            or "guard_write_zone.py" in hook.get("commandWindows", "")
            for hook in group.get("hooks", [])
        )
    ]

    assert edit_hook_groups, f"{config_relative_path} has no edit write-zone hook group"
    for group in edit_hook_groups:
        secret_hooks = [
            hook
            for hook in group.get("hooks", [])
            if "secret_scan.py" in hook.get("command", "")
            or "secret_scan.py" in hook.get("commandWindows", "")
        ]
        assert secret_hooks, (
            f"{config_relative_path} matcher {group['matcher']!r} runs guard_write_zone.py "
            "without secret_scan.py"
        )
        if any("commandWindows" in hook for hook in group.get("hooks", [])):
            assert any("secret_scan.py" in hook.get("commandWindows", "") for hook in secret_hooks), (
                f"{config_relative_path} matcher {group['matcher']!r} lacks the Windows secret-scan command"
            )


def test_write_zone_hook_has_no_builtin_protected_path_policy() -> None:
    """
    @brief      Protected write paths come only from validated workflow policy.
    @return     None.
    @exception  AssertionError If the hook reintroduces a static denylist.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    guard_path = PACKAGE_ROOT / "template" / ".agentic" / "hooks" / "guard_write_zone.py"
    source = guard_path.read_text(encoding="utf-8")

    assert "PROTECTED_PATH_PATTERNS" not in source
    assert "config.protected_paths" in source
    assert "policy.patterns" in source


@pytest.mark.parametrize("config_relative_path", READ_HOOK_CONFIGS)
def test_json_adapter_configs_delegate_reads_to_shared_hook(
    config_relative_path: Path,
) -> None:
    """
    @brief      Require JSON-configured adapters to use the Python read guard.
    @param[in]  config_relative_path Adapter hook configuration below template.
    @return     None.
    @exception  AssertionError If configured reads bypass shared policy.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    data = json.loads(
        (PACKAGE_ROOT / "template" / config_relative_path).read_text(encoding="utf-8")
    )
    read_groups = [
        group
        for group in data["hooks"]["PreToolUse"]
        if any(
            "guard_read_path.py" in hook.get("command", "")
            or "guard_read_path.py" in hook.get("commandWindows", "")
            for hook in group.get("hooks", [])
        )
    ]

    assert read_groups


def test_adapters_contain_no_native_repository_denylist() -> None:
    """
    @brief      Adapter assets delegate policy without static path/command rules.
    @return     None.
    @exception  AssertionError If a duplicate repository denylist remains.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    template = PACKAGE_ROOT / "template"
    for relative in (Path(".claude/settings.json"), Path(".qwen/settings.json")):
        data = json.loads((template / relative).read_text(encoding="utf-8"))
        assert "permissions" not in data

    opencode = json.loads((template / "opencode.json").read_text(encoding="utf-8"))
    assert opencode["permission"]["read"] == {"*": "allow"}
    assert opencode["permission"]["edit"] == {"*": "allow"}
    assert opencode["permission"]["bash"] == {"*": "allow"}

    codex = (template / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "**/*.env" not in codex
    assert '".git" = "read"' not in codex
    assert 'filesystem.":workspace_roots"' not in codex

    for relative in (
        Path(".pi/extensions/agentic-guard/bridge.ts"),
        Path(".opencode/plugins/agentic-guard.mjs"),
    ):
        source = (template / relative).read_text(encoding="utf-8")
        assert "PROTECTED_READ_PATTERNS" not in source
        assert "protectedPathDeny" not in source
        assert "guard_read_path.py" in source

    hook_sources = "\n".join(
        (template / ".agentic" / "hooks" / name).read_text(encoding="utf-8")
        for name in ("guard_write_zone.py", "secret_scan.py", "delivery_preflight.py")
    )
    assert "REPO_WIDE_ZONES" not in hook_sources
    assert "DELIVERY_PATTERNS" not in hook_sources
    assert "PATTERNS = [" not in hook_sources


def test_scaffold_copies_template_to_new_project(tmp_path: Path) -> None:
    """
    @brief      Handle test scaffold copies template to new project workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.4.0
    """
    target = tmp_path / "new-project"

    result = copy_payload(TEMPLATE_ROOT, target, mode="new")

    assert result.copied
    assert (target / "AGENTS.md").exists()
    assert (target / "CHANGELOG.md").exists()
    assert (target / ".agentic" / "documents" / "PROMPT_CHEATSHEET.md").exists()
    assert (target / ".agentic" / "workflow.toml").exists()
    gitignore_lines = (target / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".agentic/.workspace/" in gitignore_lines
    # Rollback journals hold verbatim backups of files a deployment command is
    # about to overwrite; tracking them would publish the operator's own
    # pre-change content on the next `git add -A`.
    assert ".agentic/.waegis-transactions/" in gitignore_lines
    assert not (target / ".agentic" / ".workspace").exists()
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
    assert (target / ".agentic" / "hooks" / "guard_read_path.py").exists()
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
    @version    0.2.0
    """
    target = tmp_path / "new-project"

    copy_payload(TEMPLATE_ROOT, target, mode="new")

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
    @version    0.2.0
    """
    target = tmp_path / "new-project"
    target.mkdir()
    (target / "AGENTS.md").write_text("existing\n", encoding="utf-8")

    with pytest.raises(OverwriteRefusedError, match="Refusing to overwrite"):
        copy_payload(TEMPLATE_ROOT, target, mode="new")


def test_scaffold_existing_repo_requires_existing_target(tmp_path: Path) -> None:
    """
    @brief      Ensure existing-repository adoption does not create typo paths.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-23
    @version    0.3.0
    """
    target = tmp_path / "missing-existing-repo"

    with pytest.raises(TargetDirectoryMissingError):
        copy_payload(
            TEMPLATE_ROOT,
            target,
            mode="adopt",
            require_existing_target=True,
        )


def test_scaffold_dry_run_does_not_write_files(tmp_path: Path) -> None:
    """
    @brief      Ensure dry-run previews adoption files without changing target.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-23
    @version    0.3.0
    """
    target = tmp_path / "existing-repo"
    target.mkdir()

    result = copy_payload(
        TEMPLATE_ROOT,
        target,
        mode="adopt",
        dry_run=True,
        require_existing_target=True,
    )

    assert result.copied
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
    @version    0.2.0
    """
    target = tmp_path / "new-project"

    result = copy_payload(TEMPLATE_ROOT, target, mode="new")

    manifest_file = target / ".agentic" / "install-manifest.json"
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 1
    assert manifest["product"] == "aegis"
    assert manifest["mode"] == "new"
    # Every copied payload file is recorded; the manifest never lists itself.
    assert len(manifest["files"]) == len(result.copied)
    assert ".agentic/install-manifest.json" not in manifest["files"]
    assert ".agentic/install-manifest.json" not in result.copied


def test_scaffold_dry_run_writes_no_manifest(tmp_path: Path) -> None:
    """
    @brief      A dry-run preview writes nothing, including no install
                manifest.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.2.0
    """
    target = tmp_path / "existing-repo"
    target.mkdir()

    result = copy_payload(
        TEMPLATE_ROOT,
        target,
        mode="adopt",
        dry_run=True,
        require_existing_target=True,
    )

    assert result.copied
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
    @version    0.2.0
    """
    template = tmp_path / "template"
    target = tmp_path / "new-project"
    (template / "pkg" / "__pycache__").mkdir(parents=True)
    (template / "pkg" / "__pycache__" / "module.pyc").write_bytes(b"cache")
    (template / ".pytest_cache").mkdir()
    (template / ".pytest_cache" / "README.md").write_text("cache\n", encoding="utf-8")
    (template / "src").mkdir()
    (template / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

    result = copy_payload(template, target, mode="new")

    assert result.copied == ("src/app.py",)
    assert (target / "src" / "app.py").exists()
    assert not (target / "pkg" / "__pycache__").exists()
    assert not (target / ".pytest_cache").exists()


# END OF FILE
