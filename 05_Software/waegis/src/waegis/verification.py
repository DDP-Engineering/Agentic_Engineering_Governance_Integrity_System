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
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import json
import os
from pathlib import Path

from .io.reports import ProbeFindingRecord
from .probes.runner import CommandRunner

# CONSTANTS

HOOK_FILES: tuple[str, ...] = (
    "delivery_preflight.py",
    "guard_write_zone.py",
    "post_tool_evidence.py",
    "secret_scan.py",
)

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
    @version    0.2.0
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

    status_argv = wrapper_invocation(repo, "status")
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
