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
@details OS-aware case sensitivity of the hook's shared path matcher is covered
         for configured write and read policies.
@details WP2 coverage verifies canonical workspace-state errors for restricted
         writes, run-independent unrestricted writes, and non-destructive
         post-tool warnings when no valid run is selected.
@details T5 regression coverage (0.5.0) verifies that ``gh pr merge`` reaches
         delivery preflight like PR creation and other outward actions.
@details WP5 coverage verifies that write, read, secret, and delivery hooks
         consume only the canonical schema-version-3 configuration and deny
         pre-tool operations when that policy cannot be validated.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType

import pytest

from aegis import paths as paths_module
from aegis.store import init_graph, save_graph


# LOCAL HELPERS

# @brief Standalone hook scripts are the single runtime source of truth; tests
#        load them directly from the template so the executed code is covered.
HOOKS_DIR = Path(__file__).resolve().parents[1] / "template" / ".agentic" / "hooks"
CLI_SOURCE_DIR = HOOKS_DIR.parent / "cli" / "src"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


def load_hook(module_name: str) -> ModuleType:
    """
    @brief      Load a standalone hook script as an importable module.
    @param[in]  module_name Hook file stem under the template hooks directory.
    @return     Imported module exposing the hook ``main`` callable.
    @exception  None
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
read_main = load_hook("guard_read_path").main
secret_main = load_hook("secret_scan").main
delivery_main = load_hook("delivery_preflight").main
post_evidence_main = load_hook("post_tool_evidence").main
shell_write_module = load_hook("guard_shell_write")
shell_write_main = shell_write_module.main
config_bootstrap = load_hook("workflow_config_bootstrap")


def test_workflow_config_bootstrap_uses_canonical_parser() -> None:
    """
    @brief      The shared hook bootstrap imports the delivered strict parser.
    @return     None.
    """
    template_root = HOOKS_DIR.parents[1]

    config = config_bootstrap.load_workflow_config(template_root)

    assert config.schema_version == 3
    assert config.write_access.mode == "unrestricted"
    payload = config_bootstrap.configuration_error_payload(RuntimeError("missing parser"))
    assert payload["code"] == "CONFIG-BOOTSTRAP-FAILED"


def configure_stage_restricted_guardrails(tmp_path: Path) -> None:
    """
    @brief      Enable the historical stage-zone test policy explicitly.
    @param[in]  tmp_path Temporary repository containing the shared fixture.
    @return     None.
    @details    WP2 removes hook fallbacks. Tests that exercise stage behavior
                therefore opt into complete stage-restricted and protected-path
                policies before starting a run.
    """
    path = tmp_path / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    if 'mode = "stage_restricted"' in text:
        return
    text = text.replace(
        '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
        '[guardrails.protected_paths]\nmode = "enforce"\n'
        'patterns = [".git/**", "**/*.key", "**/id_rsa"]\n'
        'operations = ["write"]',
    )
    text = text.replace(
        '[guardrails.write_access]\nmode = "unrestricted"',
        '[guardrails.write_access]\nmode = "stage_restricted"\n\n'
        '[guardrails.write_access.stages]\n'
        'intake = [".agentic/**"]\n'
        'alignment = [".agentic/**"]\n'
        'requirement = [".agentic/requirements/**"]\n'
        'design = [".agentic/**"]\n'
        'check = ["tests/**", "test/**"]\n'
        'implementation = ["src/**", "app/**", "lib/**", ".agentic/knowledge/components/**"]\n'
        'validation = []\n'
        'delivery = [".agentic/**"]\n'
        'adoption-intake = [".agentic/**"]\n'
        'adoption-alignment = [".agentic/**"]\n'
        'repo-discovery = [".agentic/**"]\n'
        'component-map = [".agentic/**"]\n'
        'component-adoption = [".agentic/**"]\n'
        'baseline-review = []\n'
        'adoption-delivery = [".agentic/**"]',
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def prepare_run(
    tmp_path: Path,
    stage: str,
    *,
    kind: str = "feature",
    access_mode: str = "standard",
) -> None:
    """
    @brief Create a selected schema-3 run at the stage needed by a hook test.
    @param[in] tmp_path Temporary repository root.
    @param[in] stage Stage whose write policy is under test.
    @param[in] kind Intent kind for stage-specific policy.
    @param[in] access_mode Captured run access mode.
    @return None.
    """
    configure_stage_restricted_guardrails(tmp_path)
    graph = init_graph(tmp_path, kind, "Hook policy probe")
    graph.stage = stage  # type: ignore[assignment]
    graph.access_mode = access_mode  # type: ignore[assignment]
    save_graph(tmp_path, graph)


def replace_workflow_fragment(tmp_path: Path, old: str, new: str) -> None:
    """
    @brief      Replace one unique policy fragment in the shared configuration.
    @param[in]  tmp_path Temporary repository containing ``workflow.toml``.
    @param[in]  old Exact existing fragment.
    @param[in]  new Exact replacement fragment.
    @return     None.
    @exception  AssertionError If the expected fragment is not unique.
    """
    path = tmp_path / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def run_hook(func, payload: dict, monkeypatch) -> str:
    """
    @brief      Run hook workflow behavior.
    @param[in]  func Input value used by the workflow helper.
    @param[in]  payload Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    cwd_value = payload.get("cwd")
    if isinstance(cwd_value, str):
        install_hook_runtime(Path(cwd_value))
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    func()
    return stdout.getvalue()


def install_hook_runtime(repo_root: Path) -> None:
    """
    @brief      Install the canonical parser/store package in a hook fixture.
    @param[in]  repo_root Temporary repository used by a standalone hook.
    @return     None.
    @details    Delivered projects contain `.agentic/cli/src/aegis`; temporary
                hook repositories reproduce that runtime boundary so the hook
                bootstrap is exercised instead of importing test-process state.
    """
    destination = repo_root / ".agentic" / "cli" / "src"
    if not (destination / "aegis").is_dir():
        shutil.copytree(CLI_SOURCE_DIR, destination, dirs_exist_ok=True)


def apply_patch_payload(tmp_path: Path, target: str) -> dict:
    """
    @brief      Build a Codex ``apply_patch`` pre-tool payload for one file.
    @param[in]  tmp_path Working directory the hook should resolve against.
    @param[in]  target Repo-relative path the patch updates.
    @return     Pre-tool-use payload mimicking the Codex apply_patch envelope.
    @exception  None
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
    """
    prepare_run(tmp_path, "implementation")


# --- Shared path-policy matching -----------------------------------------------


def test_matches_is_case_insensitive_on_windows(monkeypatch) -> None:
    """
    @brief      On Windows, `guard_write_zone.matches` is case-insensitive,
                matching that OS's own case-insensitive filesystem.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     None.
    @exception  None
    """
    monkeypatch.setattr(paths_module.os, "name", "nt")
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
    """
    monkeypatch.setattr(paths_module.os, "name", "posix")
    assert not guard_module.matches("Src/App.py", "src/**")
    assert not guard_module.matches("src/app.py", "SRC/**")
    assert guard_module.matches("src/app.py", "src/**")


# --- Codex apply_patch payloads -------------------------------------------------


def test_guard_write_zone_stage_restricted_missing_run_uses_resolver_error(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Stage-restricted writes require a valid local run selection.
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
    """
    configure_stage_restricted_guardrails(tmp_path)
    payload = file_edit_payload(tmp_path, "Edit", "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    decision = json.loads(output)["hookSpecificOutput"]
    reason = decision["permissionDecisionReason"]
    assert decision["permissionDecision"] == "deny"
    assert reason.startswith("RUN-POINTER-MISSING:")
    assert "--run <existing-run-id>" in reason
    assert ".agentic/.workspace/state/current_run" in reason


def test_guard_write_zone_unrestricted_policy_needs_no_run(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Unrestricted policy authorizes writes without resolving a run.
    @param[in]  tmp_path Working directory hosting no workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    T7 changes only denial text; the existing bookkeeping allowance
                remains unchanged.
    @exception  None
    """
    payload = file_edit_payload(tmp_path, "Edit", "src/app.py")
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
    """
    (tmp_path / ".agentic").mkdir(exist_ok=True)
    prepare_run(tmp_path, "intake")
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
    """
    advance_to_implementation(tmp_path)
    payload = apply_patch_payload(tmp_path, "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_allows_requirement_snapshot_edit(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Verify the requirement stage allows canonical snapshot edits.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    prepare_run(tmp_path, "requirement")
    payload = apply_patch_payload(
        tmp_path,
        ".agentic/requirements/functional/"
        "REQ-FUNC-6f3a61e8-84fc-438a-9b0b-53554cd04789.toml",
    )
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


def test_guard_write_zone_allows_alignment_state_edit(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Verify alignment allows workflow state edits.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     None.
    @exception  None
    """
    prepare_run(tmp_path, "alignment")
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
    """
    prepare_run(tmp_path, "intake", kind="change", access_mode="repo-wide")
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
    """
    prepare_run(tmp_path, "intake", kind="change", access_mode="repo-wide")
    payload = apply_patch_payload(tmp_path, ".git/config")
    output = run_hook(guard_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output
    assert ".git/config" in output


@pytest.mark.parametrize("envelope_key", ["command", "cmd", "script", "patch", "input"])
def test_guard_write_zone_reads_patch_envelope_from_any_key(
    tmp_path: Path,
    monkeypatch,
    envelope_key: str,
) -> None:
    """
    @brief      Verify the patch envelope is honored under every accepted key.
    @param[in]  tmp_path Working directory the hook resolves against.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @param[in]  envelope_key Argument key carrying the patch text.
    @return     None.
    @details    Regression guard. The extractor read `command` alone, so a host
                sending the patch under any other name yielded no paths — and a
                write-zone guard that extracts no paths finds nothing to block,
                which is an allow. The OpenCode adapter hedged across these same
                keys on its own side, but that only covered calls routed through
                it; this is the shared implementation every adapter feeds.
    @exception  None
    """
    prepare_run(tmp_path, "intake", kind="change", access_mode="repo-wide")
    payload = apply_patch_payload(tmp_path, ".git/config")
    payload["tool_input"] = {envelope_key: payload["tool_input"]["command"]}

    output = run_hook(guard_main, payload, monkeypatch)

    assert "permissionDecision" in output
    assert "deny" in output
    assert ".git/config" in output


def test_guard_write_zone_reports_a_path_once_across_duplicate_keys(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    @brief      Verify a path carried by two keys is reported a single time.
    @param[in]  tmp_path Working directory the hook resolves against.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Reading every envelope key rather than the first match means the
                same patch can be seen twice. Deduplication keeps one violation
                from being reported as two.
    @exception  None
    """
    prepare_run(tmp_path, "intake", kind="change", access_mode="repo-wide")
    payload = apply_patch_payload(tmp_path, ".git/config")
    command = payload["tool_input"]["command"]
    payload["tool_input"] = {"command": command, "patch": command}

    output = run_hook(guard_main, payload, monkeypatch)

    assert "deny" in output
    assert output.count(".git/config") == 1


# --- Claude Code file-edit payloads --------------------------------------------


def test_guard_write_zone_denies_claude_test_edit_during_implementation(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Block a Claude ``Edit`` of a test file during implementation.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
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
    """
    prepare_run(tmp_path, "check")
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
    """
    prepare_run(tmp_path, "intake", kind="change", access_mode="repo-wide")
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
    """
    advance_to_implementation(tmp_path)
    payload = file_edit_payload(tmp_path, "WriteFile", "src/app.py")
    output = run_hook(guard_main, payload, monkeypatch)
    assert output == ""


# --- Workspace-local post-tool evidence ---------------------------------------


def test_post_tool_evidence_warns_without_valid_workspace_pointer(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Missing local state emits a structured non-destructive warning.
    @param[in]  tmp_path Repository without an active-run pointer.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "tool_use_id": "tool-1",
        "tool_response": {},
        "cwd": str(tmp_path),
    }

    output = run_hook(post_evidence_main, payload, monkeypatch)

    warning = json.loads(output)
    assert warning["warning"]["code"] == "RUN-POINTER-MISSING"
    assert warning["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert not (tmp_path / ".agentic" / "runs").exists()


def test_post_tool_evidence_appends_only_to_selected_run(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A valid workspace selection receives the tool journal entry.
    @param[in]  tmp_path Repository with an active run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    prepare_run(tmp_path, "intake")
    run_id = (tmp_path / ".agentic" / ".workspace" / "state" / "current_run").read_text(encoding="utf-8").strip()
    journal = tmp_path / ".agentic" / "runs" / run_id / "journal.jsonl"
    before = journal.read_text(encoding="utf-8")
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "tool_use_id": "tool-2",
        "tool_response": {"ok": True},
        "cwd": str(tmp_path),
    }

    output = run_hook(post_evidence_main, payload, monkeypatch)

    assert output == ""
    appended = journal.read_text(encoding="utf-8")[len(before) :]
    entry = json.loads(appended)
    assert entry["event"] == "agentic.tool"
    assert entry["data"]["tool_use_id"] == "tool-2"


# --- Configured read policy ----------------------------------------------------


def test_guard_read_path_denies_configured_protected_read(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Deny a read matched by the canonical protected-path policy.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
        '[guardrails.protected_paths]\nmode = "enforce"\n'
        'patterns = ["credentials/**"]\noperations = ["read"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "cwd": str(tmp_path),
        "tool_input": {"file_path": "credentials/service.json"},
    }

    output = run_hook(read_main, payload, monkeypatch)

    assert "permissionDecision" in output
    assert "credentials/service.json" in output


def enforce_protected_read(tmp_path: Path) -> None:
    """
    @brief      Turn on an enforced protected-read policy over ``credentials``.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @return     None.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
        '[guardrails.protected_paths]\nmode = "enforce"\n'
        'patterns = ["credentials/**"]\noperations = ["read"]',
    )


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        # Claude Code
        ("Grep", {"path": "credentials/service.json"}),
        ("Glob", {"pattern": "credentials/**"}),
        # Qwen Code, canonical ids and the display aliases older builds emit
        ("grep_search", {"path": "credentials/service.json"}),
        ("search_file_content", {"path": "credentials/service.json"}),
        ("glob", {"pattern": "credentials/**"}),
        ("list_directory", {"path": "credentials/tokens"}),
        ("read_many_files", {"paths": ["README.md", "credentials/service.json"]}),
        # OpenCode
        ("grep", {"path": "credentials/service.json"}),
        ("list", {"path": "credentials/tokens"}),
        # Pi
        ("find", {"pattern": "credentials/**"}),
        ("ls", {"path": "credentials/tokens"}),
    ],
)
def test_guard_read_path_blocks_protected_path_through_search_tools(
    tmp_path: Path,
    monkeypatch,
    tool_name: str,
    tool_input: dict,
) -> None:
    """
    @brief      Deny a protected path targeted through a search or list tool.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @param[in]  tool_name Adapter tool identifier under test.
    @param[in]  tool_input Arguments naming the protected path.
    @return     None.
    @details    Regression guard for the protected-read bypass. The policy was
                enforced only for the single canonical read tool, so on every
                adapter the same bytes could be obtained by asking the host's
                grep instead — and the file names by asking its glob or listing
                tool. Each case here is one host's real tool identifier,
                verified against that host's shipped build.
    @exception  None
    """
    enforce_protected_read(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "cwd": str(tmp_path),
        "tool_input": tool_input,
    }

    output = run_hook(read_main, payload, monkeypatch)

    assert "permissionDecision" in output
    assert "deny" in output
    assert "credentials" in output


def test_guard_read_path_directory_listing_follows_pattern_shape(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A ``dir/**`` pattern covers a directory's contents, ``dir`` also
                covers the directory itself.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Pins the distinction so listing behavior stays predictable, and
                so nobody "fixes" it by loosening the shared matcher — which
                every scope, working-tree, component, and hook check also uses.
                An operator who wants the directory entry itself protected
                writes the bare directory; `credentials/**` deliberately names
                only what is inside it.
    @exception  None
    """
    enforce_protected_read(tmp_path)
    listing = {
        "hook_event_name": "PreToolUse",
        "tool_name": "list_directory",
        "cwd": str(tmp_path),
        "tool_input": {"path": "credentials"},
    }

    # `credentials/**` names the contents, so the directory entry is not itself
    # a protected path.
    assert run_hook(read_main, listing, monkeypatch) == ""

    replace_workflow_fragment(
        tmp_path,
        'patterns = ["credentials/**"]',
        'patterns = ["credentials"]',
    )

    assert "deny" in run_hook(read_main, listing, monkeypatch)


def test_guard_read_path_allows_unscoped_search(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Allow a repository-wide search that names no path.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    The documented limit of this guard, pinned so it stays a
                deliberate choice. A search with no scope argument means the
                whole repository; denying it would make any enforced
                protected-read policy unusable, since no pre-tool hook on any
                supported host can redact a result set. The guard blocks a
                protected path from being *targeted*, not every search that
                might incidentally touch one.
    @exception  None
    """
    enforce_protected_read(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Grep",
        "cwd": str(tmp_path),
        "tool_input": {"pattern": "password"},
    }

    assert run_hook(read_main, payload, monkeypatch) == ""


def test_guard_read_path_does_not_treat_grep_regex_as_a_path(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A grep content regex is never interpreted as a path.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    ``pattern`` means a content regex for grep and a path glob for
                glob, so it is read only for the glob-style tools. Reading it
                for grep would compare arbitrary regex text against the
                protected patterns and block a legitimate search whose regex
                happened to look like a protected path.
    @exception  None
    """
    enforce_protected_read(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Grep",
        "cwd": str(tmp_path),
        "tool_input": {"pattern": "credentials/.*", "path": "src"},
    }

    assert run_hook(read_main, payload, monkeypatch) == ""


def test_guard_read_path_still_denies_a_read_naming_no_file(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A content read carrying no path stays a denial.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Only the search tools gained the permissive empty-target branch.
                A read tool cannot operate without a target, so a payload
                without one is malformed and must not become an allow.
    @exception  None
    """
    enforce_protected_read(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "cwd": str(tmp_path),
        "tool_input": {},
    }

    output = run_hook(read_main, payload, monkeypatch)

    assert "deny" in output


def test_guard_read_path_tool_sets_are_disjoint_and_classify_every_name() -> None:
    """
    @brief      Verify the read and search tool sets stay a clean partition.
    @return     None.
    @details    The two sets drive different empty-target behavior — a read
                naming no file is denied, an unscoped search is allowed — so a
                name appearing in both would make that behavior depend on set
                iteration order. `GLOB_PATTERN_TOOLS` must also be a subset of
                the search tools, since it only refines how their ``pattern``
                argument is read.
    @exception  None
    """
    read_module = load_hook("guard_read_path")

    assert not (read_module.CONTENT_READ_TOOLS & read_module.SEARCH_TOOLS)
    assert read_module.GLOB_PATTERN_TOOLS <= read_module.SEARCH_TOOLS
    # A grep-style tool must never be treated as glob-style: its `pattern` is a
    # content regex, not a path.
    assert not (
        {"Grep", "grep", "grep_search", "search_file_content"} & read_module.GLOB_PATTERN_TOOLS
    )


def test_claude_and_qwen_matchers_cover_every_search_tool() -> None:
    """
    @brief      Verify the two settings-driven adapters route their search tools.
    @return     None.
    @details    The Python guard can only refuse a call an adapter actually
                sends it. Claude Code and Qwen Code select hooks by a matcher
                string in JSON settings, so their coverage is a config fact that
                no guard-level test can establish. OpenCode and Pi dispatch in
                code and are covered by their own adapter suites. Codex has no
                distinct read tool — it reads through `shell`, already matched
                by the Bash entry, which does not enforce protected-read
                policy. That limitation is explicit in the shipped hook README.
    @exception  None
    """
    template = Path(__file__).resolve().parents[1] / "template"

    claude = json.loads((template / ".claude" / "settings.json").read_text(encoding="utf-8"))
    claude_read = next(
        entry
        for entry in claude["hooks"]["PreToolUse"]
        if "guard_read_path.py" in json.dumps(entry)
    )
    assert {"Read", "Grep", "Glob"} <= set(claude_read["matcher"].split("|"))

    qwen = json.loads((template / ".qwen" / "settings.json").read_text(encoding="utf-8"))
    qwen_read = next(
        entry
        for entry in qwen["hooks"]["PreToolUse"]
        if "guard_read_path.py" in json.dumps(entry)
    )
    qwen_matchers = set(qwen_read["matcher"].split("|"))
    assert {"read_file", "grep_search", "glob", "list_directory"} <= qwen_matchers


def test_guard_read_path_disabled_allows_former_builtin_secret_name(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      Disabled policy carries no hidden secret/key filename denylist.
    @param[in]  tmp_path Repository root containing unrestricted policy.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "ReadFile",
        "cwd": str(tmp_path),
        "tool_input": {"path": "local.env"},
    }

    assert run_hook(read_main, payload, monkeypatch) == ""


def test_guard_read_path_invalid_configuration_denies(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Unknown read policy is an actionable deny instead of fallback.
    @param[in]  tmp_path Repository root containing malformed TOML.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    (tmp_path / ".agentic" / "workflow.toml").write_text("not = [valid", encoding="utf-8")
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "read",
        "cwd": str(tmp_path),
        "tool_input": {"path": "README.md"},
    }

    output = run_hook(read_main, payload, monkeypatch)

    assert "CONFIG-TOML-INVALID" in output
    assert "permissionDecision" in output


# --- Secret scan and delivery preflight ----------------------------------------


def test_secret_scan_denies_configured_pattern(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Deny tool input matching a repository-configured secret pattern.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    The hook compiles only patterns accepted by ``aegis.config``.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
        '[guardrails.secrets]\nmode = "enforce"\npatterns = ["ACME_TOKEN_[0-9]{8}"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "echo ACME_TOKEN_12345678"},
    }
    output = run_hook(secret_main, payload, monkeypatch)
    assert "Possible secret" in output


def enforce_broad_secret_patterns(tmp_path: Path) -> None:
    """
    @brief      Enable the pattern set a real deployment ships with.
    @param[in]  tmp_path Temporary repository containing ``workflow.toml``.
    @return     None.
    @details    These four are what the deployment wizard writes when an
                operator switches secret scanning on, so they are what the
                false positives below are measured against.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
        '[guardrails.secrets]\nmode = "enforce"\npatterns = '
        '["(?i)api[_-]?key", "(?i)secret", "(?i)password", "(?i)token"]',
    )


def test_secret_scan_ignores_the_target_path(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A file's name is not scanned as if it were its content.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Regression test (lifecycle field test, 2026-08-06, batch 2): the
                whole serialized tool input was scanned, so `(?i)token` denied
                opening `token_store.py` and `(?i)secret` denied reading this
                hook's own source. Path policy is `guardrails.protected_paths`,
                enforced by the read and write guards.
    @exception  None
    """
    enforce_broad_secret_patterns(tmp_path)
    named = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "cwd": str(tmp_path),
        "tool_input": {"file_path": "src/app/token_store.py"},
    }
    own_source = {
        **named,
        "tool_input": {"file_path": ".agentic/hooks/secret_scan.py"},
    }

    assert run_hook(secret_main, named, monkeypatch) == ""
    assert run_hook(secret_main, own_source, monkeypatch) == ""


def test_secret_scan_ignores_text_an_edit_removes(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      An edit is judged on what it writes, not what it deletes.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Regression test (lifecycle field test, 2026-08-06, batch 2): the
                replaced text is quoted from what the file already holds, so the
                one edit that deletes a hardcoded credential was denied while
                the file keeping it was left alone. The same edit reversed still
                denies.
    @exception  None
    """
    enforce_broad_secret_patterns(tmp_path)
    removal = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "cwd": str(tmp_path),
        "tool_input": {
            "file_path": "src/app/config.py",
            "old_string": 'BACKEND_PASSWORD = "hunter2-live"',
            "new_string": "BACKEND_CREDENTIAL = _keyring_lookup()",
        },
    }
    introduction = {
        **removal,
        "tool_input": {
            "file_path": "src/app/config.py",
            "old_string": "BACKEND_CREDENTIAL = _keyring_lookup()",
            "new_string": 'BACKEND_PASSWORD = "hunter2-live"',
        },
    }

    assert run_hook(secret_main, removal, monkeypatch) == ""
    assert "Possible secret" in run_hook(secret_main, introduction, monkeypatch)


def test_secret_scan_allows_narrowing_its_own_patterns(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A match cannot deny the edit that corrects the pattern.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Regression test (lifecycle field test, 2026-08-06, batch 2):
                narrowing an over-broad pattern means quoting it, and the
                pattern then matched its own removal. With the only remedy
                denied, an agent stopped by a false positive had nowhere to go.
                The hook already makes this carve-out when the configuration
                fails to load; a match is the same deadlock.
    @exception  None
    """
    enforce_broad_secret_patterns(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "cwd": str(tmp_path),
        "tool_input": {
            "file_path": ".agentic/workflow.toml",
            "old_string": 'patterns = ["(?i)api[_-]?key", "(?i)secret", '
            '"(?i)password", "(?i)token"]',
            "new_string": 'patterns = ["(?i)api[_-]?key"]',
        },
    }

    assert run_hook(secret_main, payload, monkeypatch) == ""


def test_secret_scan_denial_names_the_pattern_and_the_way_out(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A denial says which pattern fired and what to do about it.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Regression test (lifecycle field test, 2026-08-06, batch 2):
                `Possible secret detected by configured workflow policy.` was
                the whole diagnostic, so an agent writing a requirement about
                token handling could not tell a real credential from a match on
                the word, and the message named no remedy. The matched text
                itself stays out of the message.
    @exception  None
    """
    enforce_broad_secret_patterns(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "cwd": str(tmp_path),
        "tool_input": {
            "file_path": ".agentic/requirements/specs/REQ-0042.md",
            "content": "The API token is read from the operating system keyring.\n",
        },
    }

    output = run_hook(secret_main, payload, monkeypatch)

    assert "(?i)token" in output
    assert "workflow.toml" in output
    assert "operating system keyring" not in output


def test_secret_scan_invalid_configured_regex_denies(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Deny when the canonical parser rejects an invalid regex.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
        '[guardrails.secrets]\nmode = "enforce"\npatterns = ["[invalid"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "echo safe"},
    }
    output = run_hook(secret_main, payload, monkeypatch)
    assert "CONFIG-RULE-INVALID" in output
    assert "permissionDecision" in output


def test_secret_scan_missing_workflow_denies_without_builtin_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      Missing workflow policy denies instead of using built-in rules.
    @param[in]  tmp_path Repository root without ``workflow.toml``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    (tmp_path / ".agentic" / "workflow.toml").unlink()
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "echo sk-abcdefghijklmnopqrstuvwxyz123456"},
    }
    output = run_hook(secret_main, payload, monkeypatch)
    assert "CONFIG-MISSING" in output
    assert "permissionDecision" in output


def test_secret_scan_disabled_has_no_builtin_patterns(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Disabled scanning allows text formerly matched by Python defaults.
    @param[in]  tmp_path Repository root containing unrestricted policy.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "echo sk-abcdefghijklmnopqrstuvwxyz123456"},
    }

    assert run_hook(secret_main, payload, monkeypatch) == ""


def test_delivery_preflight_ignores_non_delivery_command(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Leave ordinary shell commands untouched by delivery preflight.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.delivery]\nmode = "disabled"\ncommand_patterns = []',
        '[guardrails.delivery]\nmode = "enforce"\ncommand_patterns = ["git push"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "git status"},
    }
    output = run_hook(delivery_main, payload, monkeypatch)
    assert output == ""


def test_delivery_preflight_disabled_ignores_former_builtin_command(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      Disabled delivery policy carries no built-in command fragments.
    @param[in]  tmp_path Repository root containing unrestricted policy.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "git push origin main"},
    }

    assert run_hook(delivery_main, payload, monkeypatch) == ""


def test_delivery_preflight_denies_configured_push_without_launcher(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      Deny a publish command when the workflow launcher is absent.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.delivery]\nmode = "disabled"\ncommand_patterns = []',
        '[guardrails.delivery]\nmode = "enforce"\ncommand_patterns = ["git push"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "git push origin main"},
    }
    output = run_hook(delivery_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output


def test_qwen_delivery_preflight_denies_configured_push_without_launcher(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      Apply delivery preflight to Qwen's raw shell tool identifier.
    @param[in]  tmp_path Working directory without a workflow launcher.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.delivery]\nmode = "disabled"\ncommand_patterns = []',
        '[guardrails.delivery]\nmode = "enforce"\ncommand_patterns = ["git push"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "run_shell_command",
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
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.delivery]\nmode = "disabled"\ncommand_patterns = []',
        '[guardrails.delivery]\nmode = "enforce"\ncommand_patterns = ["gh pr merge"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "gh pr merge --squash 12"},
    }
    output = run_hook(delivery_main, payload, monkeypatch)
    assert "permissionDecision" in output
    assert "deny" in output


def test_delivery_preflight_invalid_configuration_denies(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Delivery commands are denied when repository policy is unknown.
    @param[in]  tmp_path Repository root containing no workflow configuration.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    """
    (tmp_path / ".agentic" / "workflow.toml").unlink()
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "git status"},
    }

    output = run_hook(delivery_main, payload, monkeypatch)

    assert "CONFIG-MISSING" in output
    assert "permissionDecision" in output


# --- Shell write-zone guard ----------------------------------------------------


def shell_payload(tmp_path: Path, command: str, tool_name: str = "Bash") -> dict:
    """
    @brief      Build a shell pre-tool payload for one command.
    @param[in]  tmp_path Working directory the hook should resolve against.
    @param[in]  command Shell command line under inspection.
    @param[in]  tool_name Shell tool identifier (``Bash`` or ``run_shell_command``).
    @return     Pre-tool-use payload mimicking a shell invocation.
    @exception  None
    """
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "cwd": str(tmp_path),
        "tool_input": {"command": command},
    }


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("echo hi > out.txt", ["out.txt"]),
        ("echo hi>out.txt", ["out.txt"]),
        ("echo hi >| out.txt", ["out.txt"]),
        ("echo hi >> logs/app.log", ["logs/app.log"]),
        ("printf '%s' x > a/b/c.txt", ["a/b/c.txt"]),
        ("cat a | tee src/x.txt", ["src/x.txt"]),
        ("cat a | tee -a logs/x.txt", ["logs/x.txt"]),
        ("cp template.py deploy/config.py", ["deploy/config.py"]),
        ("cp -t deploy template.py", ["deploy"]),
        ("mv old.py src/new.py", ["src/new.py"]),
        ("sed -i 's/a/b/' src/app.py", ["src/app.py"]),
        ("sed -i.bak 's/a/b/' src/app.py", ["src/app.py"]),
        ("dd if=/dev/zero of=disk.img bs=1M", ["disk.img"]),
        ("echo x > /dev/null", ["/dev/null"]),
        # No write target: reads, fd duplication, and a redirection that lives
        # entirely inside quotes must all yield nothing.
        ("cat src/app.py", []),
        ("grep -r foo src/", []),
        ("echo x 2>&1", []),
        ('echo "a > b"', []),
        ("sed 's/a/b/' src/app.py", []),
    ],
)
def test_extract_write_targets_recognizes_common_forms(command: str, expected: list) -> None:
    """
    @brief      The best-effort extractor finds the obvious shell write forms
                and ignores reads, fd duplication, and quoted operators.
    @param[in]  command Shell command line under test.
    @param[in]  expected Write targets the extractor should report.
    @return     None.
    @exception  None
    """
    assert shell_write_module.extract_write_targets(command) == expected


def test_write_guard_extracts_patch_moves_and_notebook_targets() -> None:
    """@brief Cover write destinations carried by patch moves and notebooks."""
    assert guard_module.extract_patch_paths(
        "*** Begin Patch\n*** Update File: src/old.py\n*** Move to: secrets/new.py\n*** End Patch"
    ) == ["src/old.py", "secrets/new.py"]
    assert guard_module.extract_target_paths(
        {"notebook_path": "notebooks/analysis.ipynb"}
    ) == ["notebooks/analysis.ipynb"]


def test_write_guard_denies_notebook_edit_outside_active_zone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A write-capable tool name cannot bypass target enforcement."""
    advance_to_implementation(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "NotebookEdit",
        "cwd": str(tmp_path),
        "tool_input": {"notebook_path": "tests/analysis.ipynb"},
    }
    assert "deny" in run_hook(guard_main, payload, monkeypatch)


def test_secret_scan_removes_nested_replaced_text_only() -> None:
    """@brief A MultiEdit may remove a secret without reintroducing it."""
    introduced = load_hook("secret_scan").introduced_input(
        {
            "edits": [
                {
                    "old_string": "TOKEN=secret",
                    "new_string": "TOKEN=redacted",
                }
            ]
        }
    )
    assert introduced == {"edits": [{"new_string": "TOKEN=redacted"}]}


def test_workflow_config_carve_out_rejects_nested_lookalike() -> None:
    """@brief Only the root workflow policy receives deadlock recovery."""
    secret_module = load_hook("secret_scan")
    assert secret_module.targets_workflow_config_only(
        {"file_path": ".agentic/workflow.toml"}
    )
    assert not secret_module.targets_workflow_config_only(
        {"file_path": "docs/.agentic/workflow.toml"}
    )


def test_delivery_pattern_matches_git_global_flags() -> None:
    """@brief Git global options cannot bypass a configured push preflight."""
    delivery_module = load_hook("delivery_preflight")
    assert delivery_module._matches_command_pattern(
        "git -c core.pager=cat push origin main", "git push"
    )
    assert delivery_module._matches_command_pattern(
        "git --no-pager push origin main", "git push"
    )
    assert not delivery_module._matches_command_pattern(
        "echo git push", "git push"
    )


def test_guard_shell_write_denies_out_of_zone_redirect(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A shell redirection into another stage's zone is denied.
    @param[in]  tmp_path Working directory hosting the workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    At implementation the test tree is out of the write zone, so a
                ``> tests/...`` redirection is blocked exactly as an editor edit
                of the same path would be.
    @exception  None
    """
    advance_to_implementation(tmp_path)
    output = run_hook(shell_write_main, shell_payload(tmp_path, "echo x > tests/test_app.py"), monkeypatch)
    assert "deny" in output
    assert "tests/test_app.py" in output


@pytest.mark.parametrize(
    "command",
    (
        "echo x>tests/test_app.py",
        "echo x >| tests/test_app.py",
        "cp -t tests src/app.py",
    ),
)
def test_guard_shell_write_denies_equivalent_unspaced_and_flag_forms(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    """@brief Equivalent shell syntax cannot bypass the established zone."""
    advance_to_implementation(tmp_path)
    output = run_hook(
        shell_write_main,
        shell_payload(tmp_path, command),
        monkeypatch,
    )
    assert "deny" in output


def test_guard_shell_write_allows_in_zone_redirect(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A shell redirection into the active zone is allowed.
    @param[in]  tmp_path Working directory hosting the workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    advance_to_implementation(tmp_path)
    output = run_hook(shell_write_main, shell_payload(tmp_path, "echo x > src/app.py"), monkeypatch)
    assert output == ""


def test_guard_shell_write_ignores_targets_outside_the_repository(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A shell write to a path outside the workspace is not governed.
    @param[in]  tmp_path Working directory hosting the workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    ``/dev/null`` and other external paths are not repository
                write-zone concerns, so an in-zone command redirecting there is
                left untouched even at a stage whose zone would reject it as a
                repository path.
    @exception  None
    """
    advance_to_implementation(tmp_path)
    output = run_hook(shell_write_main, shell_payload(tmp_path, "pytest -q > /dev/null 2>&1"), monkeypatch)
    assert output == ""


def test_guard_shell_write_allows_non_writing_command_without_a_run(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A read-only shell command is allowed and forces no run selection.
    @param[in]  tmp_path Working directory with stage-restricted policy, no run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Repository policy and run state are consulted only once an
                in-repository write target is found, so a command that writes
                nothing never triggers the missing-run denial that a real shell
                write would.
    @exception  None
    """
    configure_stage_restricted_guardrails(tmp_path)
    output = run_hook(shell_write_main, shell_payload(tmp_path, "git status && ls -la src/"), monkeypatch)
    assert output == ""


def test_guard_shell_write_missing_run_uses_resolver_error(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A stage-restricted shell write with no active run is denied with
                the canonical resolver error.
    @param[in]  tmp_path Working directory with stage-restricted policy, no run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    configure_stage_restricted_guardrails(tmp_path)
    output = run_hook(shell_write_main, shell_payload(tmp_path, "echo x > src/app.py"), monkeypatch)
    reason = json.loads(output)["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason.startswith("RUN-POINTER-MISSING:")


def test_guard_shell_write_repo_wide_blocks_protected_path(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      A protected path is blocked from a shell write even in repo-wide
                mode.
    @param[in]  tmp_path Working directory hosting the workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    prepare_run(tmp_path, "intake", kind="change", access_mode="repo-wide")
    output = run_hook(shell_write_main, shell_payload(tmp_path, "cp key.pem deploy/id_rsa"), monkeypatch)
    assert "deny" in output
    assert "deploy/id_rsa" in output


def test_guard_shell_write_unrestricted_policy_allows_repo_write(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Under unrestricted write policy a shell repository write is
                allowed without resolving a run.
    @param[in]  tmp_path Working directory with the default unrestricted policy.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    output = run_hook(shell_write_main, shell_payload(tmp_path, "echo x > src/app.py"), monkeypatch)
    assert output == ""


def test_guard_shell_write_applies_to_qwen_shell_tool(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      The guard inspects Qwen's ``run_shell_command`` tool as well.
    @param[in]  tmp_path Working directory hosting the workflow run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    advance_to_implementation(tmp_path)
    payload = shell_payload(tmp_path, "echo x > tests/test_app.py", tool_name="run_shell_command")
    output = run_hook(shell_write_main, payload, monkeypatch)
    assert "deny" in output


# --- W5: a malformed workflow.toml must not lock out its own repair -------------


def break_workflow_config(tmp_path: Path) -> None:
    """
    @brief      Corrupt the shared configuration the way a typo would.
    @param[in]  tmp_path Repository root containing ``workflow.toml``.
    @return     None.
    @exception  None
    """
    (tmp_path / ".agentic" / "workflow.toml").write_text(
        "not = [valid", encoding="utf-8"
    )


def test_guard_write_zone_allows_repairing_the_broken_config(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A config failure still permits editing the config itself.
    @param[in]  tmp_path Repository root whose ``workflow.toml`` is malformed.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Regression test (W5, 2026-08-04): every hook denies on an
                internal failure, so a malformed `workflow.toml` denied writes
                to every path *including itself*. The agent could not repair
                the file causing the denial - a hard deadlock produced by a
                typo, whose only exit was a human editing it outside the
                session.
    @exception  None
    """
    break_workflow_config(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "cwd": str(tmp_path),
        "tool_input": {"file_path": ".agentic/workflow.toml"},
    }

    assert run_hook(guard_main, payload, monkeypatch) == ""


def test_guard_write_zone_still_denies_other_paths_when_config_is_broken(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      The deadlock exception is scoped to the config file alone.
    @param[in]  tmp_path Repository root whose ``workflow.toml`` is malformed.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    break_workflow_config(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "cwd": str(tmp_path),
        "tool_input": {"file_path": "src/app.py"},
    }

    output = run_hook(guard_main, payload, monkeypatch)

    assert "CONFIG-TOML-INVALID" in output
    assert "permissionDecision" in output


def test_guard_shell_write_allows_repairing_the_broken_config(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A shell write to the broken config is permitted, others are not.
    @param[in]  tmp_path Repository root whose ``workflow.toml`` is malformed.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    break_workflow_config(tmp_path)

    allowed = run_hook(
        shell_write_main,
        shell_payload(tmp_path, "echo fixed > .agentic/workflow.toml"),
        monkeypatch,
    )
    denied = run_hook(
        shell_write_main,
        shell_payload(tmp_path, "echo x > src/app.py"),
        monkeypatch,
    )

    assert allowed == ""
    assert "permissionDecision" in denied


def test_secret_scan_allows_repairing_the_broken_config(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      The secret scan does not block the config repair either.
    @param[in]  tmp_path Repository root whose ``workflow.toml`` is malformed.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    break_workflow_config(tmp_path)

    allowed = run_hook(
        secret_main,
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": str(tmp_path),
            "tool_input": {"file_path": ".agentic/workflow.toml"},
        },
        monkeypatch,
    )
    denied = run_hook(
        secret_main,
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": str(tmp_path),
            "tool_input": {"file_path": "src/app.py"},
        },
        monkeypatch,
    )

    assert allowed == ""
    assert "permissionDecision" in denied


def test_guard_read_path_allows_reading_the_broken_config(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      The read guard permits reading the config it failed to load.
    @param[in]  tmp_path Repository root whose ``workflow.toml`` is malformed.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Without this the agent could not even *read* the file it had to
                repair, which is the half of W5 that made the deadlock total.
    @exception  None
    """
    break_workflow_config(tmp_path)
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "cwd": str(tmp_path),
        "tool_input": {"file_path": ".agentic/workflow.toml"},
    }

    assert run_hook(read_main, payload, monkeypatch) == ""


# --- B15: out-of-repository reads are not a protected-path concern --------------


def test_guard_read_path_ignores_targets_outside_the_repository(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A read outside the workspace is allowed, not denied.
    @param[in]  tmp_path Repository root with protected-read policy enforced.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Regression test (B15, 2026-08-04): `relative_to_root` raised
                "Path escapes workspace root" for any out-of-repo target and the
                blanket handler turned that into a deny, so reading a scratch
                file or a sibling checkout was blocked with a containment
                message for a policy that only governs repository globs. The
                sibling shell-write guard already ignores escapes.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
        '[guardrails.protected_paths]\nmode = "enforce"\n'
        'patterns = [".env"]\noperations = ["read", "write"]',
    )
    outside = tmp_path.parent / "outside-scratch.txt"
    outside.write_text("scratch\n", encoding="utf-8")
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "cwd": str(tmp_path),
        "tool_input": {"file_path": str(outside)},
    }

    assert run_hook(read_main, payload, monkeypatch) == ""


def test_guard_read_path_still_denies_configured_pattern_inside_repository(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      Ignoring escapes does not weaken the in-repository policy.
    @param[in]  tmp_path Repository root with protected-read policy enforced.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @exception  None
    """
    replace_workflow_fragment(
        tmp_path,
        '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
        '[guardrails.protected_paths]\nmode = "enforce"\n'
        'patterns = [".env"]\noperations = ["read", "write"]',
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "cwd": str(tmp_path),
        "tool_input": {"file_path": ".env"},
    }

    output = run_hook(read_main, payload, monkeypatch)

    assert "Reading configured protected path is blocked: .env" in output


# --- B14: evidence recording is advisory and must never block the host ----------


def test_post_tool_evidence_warns_instead_of_failing_on_a_broken_journal(
    tmp_path: Path, monkeypatch
) -> None:
    """
    @brief      A truncated journal produces a warning, not a blocking error.
    @param[in]  tmp_path Repository with an active run.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    Regression test (B14, 2026-08-04): `append_journal` was called
                outside the hook's guarded block, so a journal left without a
                trailing newline by a killed process raised `PersistenceError`
                out of `main` on *every* tool call. The transport maps any
                non-zero exit to a blocking failure, wedging the session until
                the journal was hand-repaired - while the module docstring
                promises a non-destructive structured warning.
    @exception  None
    """
    prepare_run(tmp_path, "intake")
    run_id = (
        tmp_path / ".agentic" / ".workspace" / "state" / "current_run"
    ).read_text(encoding="utf-8").strip()
    journal = tmp_path / ".agentic" / "runs" / run_id / "journal.jsonl"
    journal.write_text(
        journal.read_text(encoding="utf-8") + '{"partial": ',
        encoding="utf-8",
        newline="\n",
    )
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "tool_use_id": "tool-3",
        "tool_response": {"ok": True},
        "cwd": str(tmp_path),
    }

    output = run_hook(post_evidence_main, payload, monkeypatch)

    warning = json.loads(output)
    assert warning["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "incomplete record" in warning["warning"]["message"]


# END OF FILE
