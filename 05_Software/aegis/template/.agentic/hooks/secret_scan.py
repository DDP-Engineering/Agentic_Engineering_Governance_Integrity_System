#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file secret_scan.py
@brief Pre-tool hook enforcing configured secret scanning policy.
@details Uses only patterns validated under ``guardrails.secrets`` by the
         canonical parser. Missing or invalid policy is an actionable deny;
         disabled scanning carries no dormant built-in expressions.
@details Serializes the scanned tool input with ``ensure_ascii=False`` (0.4.0,
         code-review follow-up) so a configured pattern can match a secret that
         contains non-ASCII characters instead of comparing it against
         ``\\uXXXX`` escapes.
@details Scans only the values a call would *introduce* (2.1.0, lifecycle field
         test). It previously serialized the whole tool input, so a pattern as
         ordinary as ``(?i)secret`` denied reading ``secret_scan.py`` itself and
         ``(?i)token`` denied opening ``token_store.py`` - a file's name is not
         its content - and an edit was judged on the text it *removes*, so the
         one edit that deletes a hardcoded credential was denied while the file
         keeping it was left alone.
@details A match no longer denies a call that names only ``.agentic/workflow.toml``
         (2.1.0, lifecycle field test), matching the carve-out the configuration
         branch below already makes. The edit that narrows an over-broad pattern
         necessarily quotes that pattern, so the pattern denied its own removal
         and left the agent no way out. INV-7 still scans that file, so the
         change moves where an over-broad rule is corrected, not whether the
         configuration is covered.
"""

# IMPORTS

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# CONSTANTS

# @brief Repository-relative suffix of the file this hook's policy is loaded
#        from. A hook that cannot load it denies every call, including the edit
#        that would repair it.
WORKFLOW_CONFIG_SUFFIX = ".agentic/workflow.toml"

# @brief Tool-input keys that name a single target file across the supported
#        adapters. Only these are read; a patch envelope is deliberately not
#        parsed here, so a bulk patch never reaches the deadlock exception.
PATH_KEYS = ("file_path", "path", "filePath", "absolute_path", "notebook_path")

# @brief Tool-input keys holding the text an edit *replaces*. It is quoted from
#        what the file already contains, so a match there is a secret the call
#        is removing, not one it is adding.
REPLACED_TEXT_KEYS = ("old_string", "oldText", "old_str")

# PUBLIC API


def main() -> int:
    """
    @brief      Scan pre-tool input with the active configured expressions.
    @return     Zero after allowing the input or emitting a deny decision.
    @details    Configuration errors deny the operation before its content is
                evaluated so unknown policy never becomes an implicit allow.
    @exception  None
    """
    payload = json.load(sys.stdin)
    if payload.get("hook_event_name") != "PreToolUse":
        return 0
    cwd = Path(payload.get("cwd") or ".").resolve()
    try:
        from workflow_config_bootstrap import load_workflow_config

        policy = load_workflow_config(cwd).secrets
    except Exception as exc:
        if targets_workflow_config_only(payload.get("tool_input", {})):
            return 0
        return deny(str(exc))
    if policy.mode == "disabled":
        return 0
    tool_input = payload.get("tool_input", {})
    compiled_patterns = [re.compile(pattern) for pattern in policy.patterns]
    # `ensure_ascii=False` keeps non-ASCII characters literal. With the default
    # escaping a secret containing accented or non-Latin characters would be
    # serialized as `\uXXXX` escapes, and a pattern written to match the real
    # characters would never fire against that escaped text.
    text = json.dumps(introduced_input(tool_input), ensure_ascii=False)
    matched = next(
        (pattern for pattern in compiled_patterns if pattern.search(text)), None
    )
    if matched is not None:
        # Same carve-out as the configuration branch above, for the same
        # reason: correcting an over-broad pattern means quoting it, which
        # matches it. INV-7 still scans this file.
        if targets_workflow_config_only(tool_input):
            return 0
        return deny(
            f"Possible secret detected by configured pattern {matched.pattern}. "
            "If this is not a secret, narrow or remove that pattern under "
            "`[guardrails.secrets]` in .agentic/workflow.toml, or reword the "
            "text so it does not match."
        )
    return 0


def introduced_input(tool_input: object) -> object:
    """
    @brief      Reduce a tool input to the values the call would introduce.
    @param[in]  tool_input Adapter tool-input mapping.
    @return     The same mapping without the keys naming a target file or
                quoting the text an edit replaces; any non-mapping input
                unchanged.
    @details    Both dropped groups describe state that already exists rather
                than content the call writes. Scanning a path made the file's
                *name* enough to deny the call - ``secret_scan.py`` denied
                reading itself - and scanning replaced text denied the edit that
                deletes a hardcoded credential. Path policy is
                ``guardrails.protected_paths``, enforced by its own hooks.
    @exception  None
    """
    if not isinstance(tool_input, dict):
        return tool_input
    ignored = PATH_KEYS + REPLACED_TEXT_KEYS
    return {key: value for key, value in tool_input.items() if key not in ignored}


def targets_workflow_config_only(tool_input: object) -> bool:
    """
    @brief      Report whether the call names the workflow config and nothing else.
    @param[in]  tool_input Adapter tool-input mapping.
    @return     ``True`` only when at least one path was named and every one of
                them is `.agentic/workflow.toml`.
    @details    Used exclusively to break the config-typo deadlock: a malformed
                `workflow.toml` makes this hook deny every call, including the
                edit that would repair it, so the agent cannot recover from a
                typo without a human editing the file outside the session.
                Every other call is still denied on an internal failure.
    """
    if not isinstance(tool_input, dict):
        return False
    paths = [
        value
        for key in PATH_KEYS
        if isinstance(value := tool_input.get(key), str) and value
    ]
    if not paths:
        return False
    return all(
        item.replace("\\", "/").rstrip("/").endswith(WORKFLOW_CONFIG_SUFFIX)
        for item in paths
    )


def deny(message: str) -> int:
    """
    @brief      Emit the common pre-tool denial envelope.
    @param[in]  message Actionable policy or match reason.
    @return     Zero as required by adapter hook transports.
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
