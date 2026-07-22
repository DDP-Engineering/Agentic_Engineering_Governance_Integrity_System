#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file guard_read_path.py
@brief Pre-tool hook enforcing configured protected-read policy.
@details Loads the canonical schema-version-2 workflow model and applies only
         ``guardrails.protected_paths`` patterns configured for ``read``.
         The hook contains no native repository denylist or fallback policy.
@author Eng. Dan Dumitru Pasare
@date 2026-07-22
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import sys

# PUBLIC API


def main() -> int:
    """
    @brief      Evaluate one adapter read against validated repository policy.
    @return     Zero after allowing the read or emitting a deny decision.
    @exception  None Configuration and path failures become hook denials.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    payload = json.load(sys.stdin)
    if payload.get("hook_event_name") != "PreToolUse":
        return 0
    cwd = Path(payload.get("cwd") or ".").resolve()
    try:
        from workflow_config_bootstrap import find_repository_root, load_workflow_config

        repo_root = find_repository_root(cwd)
        config = load_workflow_config(repo_root)
        policy = config.protected_paths
        if policy.mode == "disabled" or "read" not in policy.operations:
            return 0

        target = extract_target_path(payload.get("tool_input", {}))
        if target is None:
            return deny("Protected-read policy could not determine the requested path.")

        from aegis.paths import matches_pattern, relative_to_root

        relative_path = relative_to_root(target, repo_root)
        if any(matches_pattern(relative_path, pattern) for pattern in policy.patterns):
            return deny(f"Reading configured protected path is blocked: {relative_path}")
    except Exception as exc:
        return deny(str(exc))
    return 0


def extract_target_path(tool_input: object) -> str | None:
    """
    @brief      Extract a read path from supported adapter argument shapes.
    @param[in]  tool_input Adapter tool input mapping.
    @return     Non-empty path string, or ``None`` when absent.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "filePath", "path", "filename"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def deny(message: str) -> int:
    """
    @brief      Emit the common pre-tool denial envelope.
    @param[in]  message Actionable reason shown to the agent.
    @return     Zero as required by adapter hook transports.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": message,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
