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

# @brief Adapter configs whose host parses with a strict deserializer that
#        rejects the *whole file* on an unknown top-level key, mapped to the
#        exact key set that host accepts.
# @details Codex deserializes `.codex/hooks.json` with `deny_unknown_fields`;
#          its own parse error names the accepted set verbatim ("expected
#          `description` or `hooks`"). A rejected hooks file registers no hooks
#          at all, so an unknown key here does not degrade enforcement, it
#          removes it: tool calls are not blocked, they are never inspected.
#          That is why this is a guard-presence contract and not style policing.
STRICT_HOST_CONFIG_KEYS: dict[Path, frozenset[str]] = {
    Path(".codex/hooks.json"): frozenset({"description", "hooks"}),
}

# @brief Adapter configs whose host tolerates unknown top-level keys, so the
#        `_`-prefixed annotation convention is safe to use in them.
TOLERANT_HOST_CONFIGS = (
    Path(".claude/settings.json"),
    Path(".qwen/settings.json"),
    Path(".pi/settings.json"),
    Path(".pi/package.json"),
)


# TESTS


def test_embedded_cli_package_version_matches_pyproject() -> None:
    """
    @brief      Enforce T13 version parity for the embedded AEGIS CLI package.
    @return     None.
    @exception  AssertionError If package and project metadata versions differ.
    """
    pyproject_path = PACKAGE_ROOT / "template" / ".agentic" / "cli" / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

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


@pytest.mark.parametrize("config_relative_path", sorted(STRICT_HOST_CONFIG_KEYS))
def test_strict_host_configs_use_only_supported_top_level_keys(config_relative_path: Path) -> None:
    """
    @brief      Keep strictly-parsed adapter configs within the key set their
                host actually accepts.
    @param[in]  config_relative_path Adapter configuration below the template root.
    @return     None.
    @details    Regression coverage for a shipped payload whose
                `.codex/hooks.json` carried `_legal` and `_comment*` annotation
                keys. Codex rejected the file outright and registered zero
                hooks, so the read, write-zone, secret, shell-write, delivery,
                and evidence guards were all silently absent under that host
                while the file remained valid JSON and every other test passed.
                Valid JSON is not a loadable host config; only the host's own
                key set decides that.
    @exception  AssertionError If the config carries a key its host rejects.
    """
    allowed = STRICT_HOST_CONFIG_KEYS[config_relative_path]
    data = json.loads((PACKAGE_ROOT / "template" / config_relative_path).read_text(encoding="utf-8"))
    unsupported = sorted(set(data) - allowed)

    assert not unsupported, (
        f"{config_relative_path} carries top-level key(s) {unsupported} that its host rejects; "
        f"it accepts only {sorted(allowed)}. An unknown key makes the host discard the whole "
        "file, which registers no hooks at all and leaves every guard silently absent."
    )


@pytest.mark.parametrize("config_relative_path", TOLERANT_HOST_CONFIGS)
def test_tolerant_host_config_annotations_stay_underscore_prefixed(config_relative_path: Path) -> None:
    """
    @brief      Keep annotation keys recognizable in configs whose host ignores
                unknown top-level keys.
    @param[in]  config_relative_path Adapter configuration below the template root.
    @return     None.
    @details    These hosts tolerate extra keys, so annotations are safe here —
                but only while they stay visibly annotations. An un-prefixed
                comment key is indistinguishable from a misspelled real setting,
                which a tolerant host silently ignores rather than reporting.
                Configs whose host is strict are covered by
                :func:`test_strict_host_configs_use_only_supported_top_level_keys`
                instead, where annotations are not permitted at all.
    @exception  AssertionError If a `_`-prefixed annotation convention is broken.
    """
    config_path = PACKAGE_ROOT / "template" / config_relative_path
    data = json.loads(config_path.read_text(encoding="utf-8"))

    assert config_relative_path not in STRICT_HOST_CONFIG_KEYS, (
        f"{config_relative_path} is listed as both strict and tolerant; a config has exactly one host parser"
    )
    for key, value in data.items():
        if isinstance(value, str) and key.lower().lstrip("_").startswith(("comment", "legal", "note")):
            assert key.startswith("_"), (
                f"{config_relative_path} annotation key {key!r} is not `_`-prefixed; "
                "a tolerant host cannot distinguish it from a misspelled setting"
            )


def test_adapters_contain_no_native_repository_denylist() -> None:
    """
    @brief      Adapter assets delegate policy without static path/command rules.
    @return     None.
    @exception  AssertionError If a duplicate repository denylist remains.
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
    assert (target / ".codex" / "hooks.json").exists()
    assert (target / ".codex" / "README.md").exists()
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
    """
    template = tmp_path / "template"
    target = tmp_path / "new-project"
    excluded_files = (
        template / "pkg" / "__pycache__" / "module.pyc",
        template / "pkg" / "optimized.pyo",
        template / ".pytest_cache" / "README.md",
        template / ".mypy_cache" / "state.json",
        template / ".ruff_cache" / "state",
        template / ".hypothesis" / "examples",
        template / ".tox" / "state",
        template / ".nox" / "state",
        template / ".uv_cache" / "archive.bin",
        template / ".coverage",
        template / "coverage.xml",
        template / "htmlcov" / "index.html",
    )
    for path in excluded_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"generated")
    (template / "src").mkdir()
    (template / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

    result = copy_payload(template, target, mode="new")

    assert result.copied == ("src/app.py",)
    assert (target / "src" / "app.py").exists()
    for path in excluded_files:
        assert not (target / path.relative_to(template)).exists()


# END OF FILE
