#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file verification.py
@brief Shared AEGIS wrapper resolution and lifecycle smoke verification.
@details New, adopt, configure, repair, doctor, and upgrade use this module so
         wrapper invocation and health semantics cannot drift between commands.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

import json
import os
from pathlib import Path

from .io.reports import ProbeFindingRecord
from .probes.runner import CommandRunner

# CONSTANTS

# @brief Every guard the payload ships under ``.agentic/hooks/``, checked for
#        presence by the `verify.hooks-present` wizard step and by
#        `waegis doctor`. A hook missing from this tuple is a hook whose absence
#        from an install is never noticed: both callers report success over the
#        names listed here, so an uncopied file simply is not looked for.
#        `guard_read_path.py` was missing until 0.3.0, having arrived with the
#        protected-read policy without this list being updated alongside it.
#        `tests/test_commands_new_steps.py` derives the expected set from the
#        real template so the next hook added cannot repeat that.
#        `workflow_config_bootstrap.py` is deliberately absent: it is the shared
#        config loader the hooks import, not a hook the adapters dispatch.
HOOK_FILES: tuple[str, ...] = (
    "delivery_preflight.py",
    "guard_read_path.py",
    "guard_shell_write.py",
    "guard_write_zone.py",
    "post_tool_evidence.py",
    "secret_scan.py",
)

# @brief Adapter configurations whose host parses with a strict deserializer
#        that rejects the *entire file* on an unknown top-level key, mapped to
#        the exact key set that host accepts.
# @details Checking that an adapter directory exists says nothing about whether
#          its host can load the config inside it. Codex deserializes
#          `.codex/hooks.json` with `deny_unknown_fields` and names the accepted
#          set in its own parse error ("expected `description` or `hooks`"); a
#          file it rejects registers **no hooks at all**, so every guard is
#          silently absent for the session — tool calls are not blocked, they
#          are never inspected. That is the same fail-open shape as a missing
#          Node.js runtime, and like it, no hook can report it because no hook
#          ran. `waegis doctor`'s `runnability.adapter-configs` check exists to
#          give it the visible signal it otherwise lacks.
#          Only strictly-parsed configs belong here: hosts that tolerate unknown
#          keys (Claude Code, Qwen Code, Pi) cannot fail this way, and asserting
#          an invented key set for them would break on the next feature they add.
STRICT_ADAPTER_CONFIG_KEYS: dict[str, frozenset[str]] = {
    ".codex/hooks.json": frozenset({"description", "hooks"}),
}

# @brief Adapter hook configurations whose host binds per-hook trust to the
#        file's content hash, so rewriting the file silently revokes it.
# @details Codex registers a hook from `.codex/hooks.json` but runs it only once
#          it has been reviewed, and it records that review against the file's
#          hash. Any rewrite — including a byte-correct AEGIS payload upgrade —
#          returns every hook in the file to "Modified since last trusted -
#          review required" and stops it running until the operator re-reviews
#          it in the `/hooks` panel. The upgrade therefore *succeeds* while
#          leaving enforcement off, with no error anywhere; the only signal is
#          a line in a settings panel nobody has a reason to open. `waegis
#          upgrade` names the affected files so the re-review is not silent.
HASH_TRUSTED_HOOK_CONFIGS: tuple[str, ...] = (".codex/hooks.json",)

SMOKE_TIMEOUT_SECONDS = 120.0
NO_ACTIVE_RUN_MARKER = "RUN-POINTER-MISSING"


# EXPORTED FUNCTIONS / PUBLIC API


def wrapper_invocation(target: Path, *cli_args: str) -> tuple[str, ...]:
    """
    @brief      Build the platform-specific AEGIS wrapper argv.
    @param[in]  target Repository root.
    @param[in]  cli_args Arguments forwarded to the embedded CLI.
    @return     Complete subprocess argv.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    if os.name == "nt":
        script = target / ".agentic" / "tools" / "run.ps1"
        return ("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *cli_args)
    script = target / ".agentic" / "tools" / "run.sh"
    return ("bash", str(script), *cli_args)


def smoke_reverify(
    runner: CommandRunner,
    repo: Path,
) -> tuple[tuple[ProbeFindingRecord, ...], bool]:
    """
    @brief      Run the shared CLI-help and coherent-status smoke checks.
    @param[in]  runner Injectable command runner.
    @param[in]  repo Repository root.
    @return     ``(findings, ok)``.
    @exception  None Subprocess failures become findings.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    1.0.0
    """
    findings: list[ProbeFindingRecord] = []
    ok = True
    help_argv = wrapper_invocation(repo, "--help")
    help_result = runner.run(help_argv, timeout=SMOKE_TIMEOUT_SECONDS, cwd=repo)
    if help_result.ok():
        findings.append(ProbeFindingRecord("verify.cli-smoke", "ok", f"'{' '.join(help_argv)}' exited 0"))
    else:
        ok = False
        detail = help_result.combined_output().strip() if help_result.found else "the wrapper executable was not found"
        findings.append(
            ProbeFindingRecord(
                "verify.cli-smoke",
                "fail",
                f"'{' '.join(help_argv)}' failed: {detail or 'no output'}",
                guidance="confirm a supported AEGIS runtime is available, then retry",
            )
        )

    status_argv = wrapper_invocation(repo, "run", "status", "--json")
    status_result = runner.run(status_argv, timeout=SMOKE_TIMEOUT_SECONDS, cwd=repo)
    healthy = False
    if status_result.ok():
        try:
            json.loads(status_result.stdout)
            healthy = True
        except json.JSONDecodeError:
            healthy = False
    elif NO_ACTIVE_RUN_MARKER in status_result.combined_output():
        healthy = True
    if healthy:
        findings.append(
            ProbeFindingRecord(
                "verify.workflow-smoke",
                "ok",
                f"'{' '.join(status_argv)}' responded coherently",
            )
        )
    else:
        ok = False
        detail = status_result.combined_output().strip() if status_result.found else "the wrapper executable was not found"
        findings.append(
            ProbeFindingRecord(
                "verify.workflow-smoke",
                "fail",
                f"'{' '.join(status_argv)}' did not respond as expected: {detail or 'no output'}",
                guidance="run the wrapper manually inside the repo and inspect the error",
            )
        )
    return tuple(findings), ok


# END OF FILE
