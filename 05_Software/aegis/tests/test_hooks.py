#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_hooks.py
@brief Workflow support module for test_hooks.
@details Covers expected workflow behavior through focused pytest checks.
@details OS-aware case sensitivity of `guard_write_zone.matches` covered as
         of 0.3.0 (architecture-review follow-up).
@details T7 regression coverage (0.4.0) verifies that a governed project with
         no active run receives actionable start guidance while an active
         intake-stage run retains the existing write-zone denial.
@details T5 regression coverage (0.5.0) verifies that ``gh pr merge`` reaches
         delivery preflight like PR creation and other outward actions.
@details T6 regression coverage (0.6.0) verifies that the pre-tool secret scan
         honors repository-configured patterns without failing closed on
         missing configuration or invalid regular expressions.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 0.6.0
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys
from types import ModuleType

from aegis.cli import main as cli_main


# LOCAL HELPERS

# @brief Standalone hook scripts are the single runtime source of truth; tests
#        load them directly from the template so the executed code is covered.
HOOKS_DIR = Path(__file__).resolve().parents[1] / "template" / ".agentic" / "hooks"


def load_hook(module_name: str) -> ModuleType:
    """
    @brief      Load a standalone hook script as an importable module.
    @param[in]  module_name Hook file stem under the template hooks directory.
    @return     Imported module exposing the hook ``main`` callable.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    path = HOOKS_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"agentic_hook_{module_name}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard_module = load_hook("guard_write_zone")
guard_main = guard_module.main
secret_main = load_hook("secret_scan").main
delivery_main = load_hook("delivery_preflight").main


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
        cli_main(list(args))
    finally:
        os.chdir(cwd)


def run_hook(func, payload: dict, monkeypatch) -> str:
    """
    @brief      Run hook workflow behavior.
    @param[in]  func Input value used by the workflow helper.
    @param[in]  payload Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    func()
    return stdout.getvalue()


def apply_patch_payload(tmp_path: Path, target: str) -> dict:
    """
    @brief      Build a Codex ``apply_patch`` pre-tool payload for one file.
    @param[in]  tmp_path Working directory the hook should resolve against.
    @param[in]  target Repo-relative path the patch updates.
    @return     Pre-tool-use payload mimicking the Codex apply_patch envelope.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    command = f"*** Begin Patch\n*** Update File: {target}\n@@\n+change\n*** End Patch\n"
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "apply_patch",
        "cwd": str(tmp_path),
        "tool_input": {"command": command},
    }


def file_edit_payload(tmp_path: Path, tool_name: str, target: str) -> dict:
    """
    @brief      Build a file-edit pre-tool payload for one file.
    @param[in]  tmp_path Working directory the hook should resolve against.
    @param[in]  tool_name Adapter tool name (``Edit``, ``Write``, ``MultiEdit``, or
                the Qwen Code ``WriteFile``).
    @param[in]  target Repo-relative path the tool intends to edit.
    @return     Pre-tool-use payload mimicking an adapter file edit.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    tool_input: dict = {"file_path": target}
    if tool_name in {"Write", "WriteFile", "write_file"}:
        tool_input["content"] = "change\n"
    elif tool_name == "MultiEdit":
        tool_input["edits"] = [{"old_string": "a", "new_string": "b"}]
    else:
        tool_input["old_string"] = "a"
        tool_input["new_string"] = "b"
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "cwd": str(tmp_path),
        "tool_input": tool_input,
    }


def advance_to_implementation(tmp_path: Path) -> None:
    """
    @brief      Start a run and route it to the implementation stage.
    @param[in]  tmp_path Working directory hosting the workflow run.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")


# --- matches() OS-aware case sensitivity (architecture-review follow-up) -------


def test_matches_is_case_insensitive_on_windows(monkeypatch) -> None:
    """
    @brief      On Windows, `guard_write_zone.matches` is case-insensitive,
                matching that OS's own case-insensitive filesystem.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    monkeypatch.setattr(guard_module.os, "name", "nt")
    assert guard_module.matches("Src/App.py", "src/**")
    assert guard_module.matches("src/app.py", "SRC/**")


def test_matches_is_case_sensitive_on_non_windows(monkeypatch) -> None:
    """
    @brief      On a non-Windows host (0.2.0), `guard_write_zone.matches` is
                case-sensitive, matching the real, case-sensitive filesystem
                on Ubuntu/Linux, mirroring `aegis.paths.matches_pattern`.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    monkeypatch.setattr(guard_module.os, "name", "posix")
    assert not guard_module.matches("Src/App.py", "src/**")
    assert not guard_module.matches("src/app.py", "SRC/**")
    assert guard_module.matches("src/app.py", "src/**")


# --- Codex apply_patch payloads -------------------------------------------------


def test_guard_write_zone_no_active_run_denial_says_so(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Without an active run, the denial names the missing run.
    @param[in]  tmp_path Working directory hosting no workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T7 regression test (analysis-review follow-up, 2026-07-20): with
                hooks installed but no run started, the stage fell back to
                ``intake`` and every non-``.agentic`` edit was denied with
                "Edit outside 'intake' write zone" — technically correct but
                misleading. The denial (still a denial) now states that no run
                is active and how to start one, so a fresh agent's first
                blocked edit points at the actual next step.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    (tmp_path / ".agentic").mkdir()
    payload = file_edit_payload(tmp_path, "Edit", "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    decision = json.loads(output)["hookSpecificOutput"]
    reason = decision["permissionDecisionReason"]
    assert decision["permissionDecision"] == "deny"
    assert "No active AEGIS run" in reason
    assert ".agentic\\tools\\run.ps1 start --kind feature" in reason
    assert "bash .agentic/tools/run.sh start --kind feature" in reason
    assert "then retry. Blocked:" in reason
    assert "src/app.py" in reason


def test_guard_write_zone_no_run_bookkeeping_edit_stays_allowed(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Without an active run, `.agentic` edits stay allowed as before.
    @param[in]  tmp_path Working directory hosting no workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T7 changes only denial text; the existing bookkeeping allowance
                remains unchanged.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    (tmp_path / ".agentic").mkdir()
    payload = file_edit_payload(tmp_path, "Edit", ".agentic/notes.md")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_active_intake_denial_message_unchanged(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      With an active intake-stage run, the stage denial is unchanged.
    @param[in]  tmp_path Working directory hosting the workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T7 must not replace stage-specific guidance when a readable
                active run already exists.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    (tmp_path / ".agentic").mkdir()
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    payload = file_edit_payload(tmp_path, "Edit", "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "deny" in output
    assert "Edit outside 'intake' write zone" in output
    assert "No active AEGIS run" not in output


def test_guard_write_zone_denies_implementation_test_edit(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Handle test guard write zone denies implementation test edit workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    advance_to_implementation(tmp_path)
    payload = apply_patch_payload(tmp_path, "tests/test_app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output


def test_guard_write_zone_allows_implementation_source_edit(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Handle test guard write zone allows implementation source edit workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    advance_to_implementation(tmp_path)
    payload = apply_patch_payload(tmp_path, "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_allows_requirement_register_edit(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Handle test guard write zone allows requirement register edit workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    payload = apply_patch_payload(tmp_path, ".agentic/requirements/functional.md")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_allows_alignment_state_edit(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Verify alignment allows workflow state edits.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(tmp_path, "next")
    payload = apply_patch_payload(tmp_path, ".agentic/runs/RUN-1/note.md")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_repo_wide_allows_normal_repo_file(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Handle test guard write zone repo wide allows normal repo file workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "change", "--statement", "Maintain docs")
    run_cli(
        tmp_path,
        "set-access-mode",
        "repo-wide",
        "--reason",
        "Human-approved broad maintenance",
    )
    payload = apply_patch_payload(tmp_path, "README.md")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_repo_wide_blocks_protected_path(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Handle test guard write zone repo wide blocks protected path workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "change", "--statement", "Maintain docs")
    run_cli(
        tmp_path,
        "set-access-mode",
        "repo-wide",
        "--reason",
        "Human-approved broad maintenance",
    )
    payload = apply_patch_payload(tmp_path, ".git/config")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output
    assert ".git/config" in output


# --- Claude Code file-edit payloads --------------------------------------------


def test_guard_write_zone_denies_claude_test_edit_during_implementation(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Block a Claude ``Edit`` of a test file during implementation.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    advance_to_implementation(tmp_path)
    payload = file_edit_payload(tmp_path, "Edit", "tests/test_app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output
    assert "tests/test_app.py" in output


def test_guard_write_zone_allows_claude_source_write_during_implementation(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Allow a Claude ``Write`` of a source file during implementation.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    advance_to_implementation(tmp_path)
    payload = file_edit_payload(tmp_path, "Write", "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_denies_claude_source_edit_during_check(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Block a Claude source ``Write`` while the run is at the check gate.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "Add discounts")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    run_cli(tmp_path, "next")
    payload = file_edit_payload(tmp_path, "Write", "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output


def test_guard_write_zone_repo_wide_blocks_claude_multiedit_protected_path(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Block a Claude ``MultiEdit`` of a key file even in repo-wide mode.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    run_cli(tmp_path, "start", "--kind", "change", "--statement", "Maintain docs")
    run_cli(
        tmp_path,
        "set-access-mode",
        "repo-wide",
        "--reason",
        "Human-approved broad maintenance",
    )
    payload = file_edit_payload(tmp_path, "MultiEdit", "deploy/id_rsa")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output


# --- Qwen Code file-write payloads ---------------------------------------------


def test_guard_write_zone_denies_qwen_test_write_during_implementation(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Block a Qwen ``WriteFile`` of a test file during implementation.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    advance_to_implementation(tmp_path)
    payload = file_edit_payload(tmp_path, "WriteFile", "tests/test_app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output
    assert "tests/test_app.py" in output


def test_guard_write_zone_allows_qwen_source_write_during_implementation(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Allow a Qwen ``WriteFile`` of a source file during implementation.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-01
    @version    0.1.0
    """
    advance_to_implementation(tmp_path)
    payload = file_edit_payload(tmp_path, "WriteFile", "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


# --- Secret scan and delivery preflight ----------------------------------------


def test_secret_scan_denies_configured_pattern(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Deny tool input matching a repository-configured secret pattern.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T6 regression test: custom ``[secrets].patterns`` previously
                protected INV-7 and working-tree audit only; the PreToolUse hook
                ignored them.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    (agentic / "workflow.toml").write_text(
        "[secrets]\npatterns = ['ACME_TOKEN_[0-9]{8}']\n",
        encoding="utf-8",
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "echo ACME_TOKEN_12345678"},
    }
    output = run_hook(secret_main, payload, monkeypatch)
    assert "Possible secret" in output


def test_secret_scan_ignores_invalid_configured_regex(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Ignore an invalid configured regex without blocking benign input.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T6 keeps the hook fail-open for bad user configuration; the
                invalid expression is neither allowed to crash nor treated as
                a match-all denial.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    agentic = tmp_path / ".agentic"
    agentic.mkdir()
    (agentic / "workflow.toml").write_text(
        "[secrets]\npatterns = ['[invalid']\n",
        encoding="utf-8",
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "echo safe"},
    }
    output = run_hook(secret_main, payload, monkeypatch)
    assert output == ""


def test_secret_scan_missing_workflow_uses_builtin_patterns(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Preserve built-in secret detection when workflow config is absent.
    @param[in]  tmp_path Repository root without ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T6 configuration loading must not change the legacy no-config
                behavior.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "echo sk-abcdefghijklmnopqrstuvwxyz123456"},
    }
    output = run_hook(secret_main, payload, monkeypatch)
    assert "Possible secret" in output


def test_delivery_preflight_ignores_non_delivery_command(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Leave ordinary shell commands untouched by delivery preflight.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "git status"},
    }
    output = run_hook(delivery_main, payload, monkeypatch)
    assert output == ""


def test_delivery_preflight_denies_push_without_launcher(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Deny a publish command when the workflow launcher is absent.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "git push origin main"},
    }
    output = run_hook(delivery_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output


def test_delivery_preflight_denies_gh_pr_merge_without_launcher(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      Route GitHub PR merges through delivery preflight.
    @param[in]  tmp_path Working directory without a workflow launcher.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T5 regression test for ``gh pr merge --squash 12``: the command
                previously bypassed ``DELIVERY_PATTERNS`` even though PR create,
                Git push, and Git merge were intercepted.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "gh pr merge --squash 12"},
    }
    output = run_hook(delivery_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output


# END OF FILE
