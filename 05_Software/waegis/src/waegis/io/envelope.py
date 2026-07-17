#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file envelope.py
@brief Single-document JSON command envelope and standardized exit codes.
@details Every ``--json`` path uses this writer exactly once. Commands place
         command-specific data in ``plan`` and ``result``; validation and
         operational failures use the same shape as success.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
from typing import IO, Any, Iterable, Mapping

# CONSTANTS

SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_NEEDS_INPUT = 1
EXIT_VALIDATION = 2
EXIT_OPERATIONAL = 3
VALID_STATUSES = frozenset({"ok", "warning", "needs-input", "failed", "error"})


# EXPORTED FUNCTIONS / PUBLIC API


def command_envelope(
    command: str,
    *,
    status: str,
    exit_code: int,
    plan: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
    messages: Iterable[str] = (),
) -> dict[str, Any]:
    """
    @brief      Build one validated JSON command envelope.
    @param[in]  command Public command name.
    @param[in]  status Command status token.
    @param[in]  exit_code Standardized process exit code.
    @param[in]  plan Optional resolved/preview plan.
    @param[in]  result Optional command-specific result mapping.
    @param[in]  messages Human-readable notes/errors.
    @return     JSON-safe envelope mapping.
    @exception  ValueError If status or exit code is outside the contract.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid command status: {status!r}")
    if exit_code not in {EXIT_OK, EXIT_NEEDS_INPUT, EXIT_VALIDATION, EXIT_OPERATIONAL}:
        raise ValueError(f"invalid command exit code: {exit_code!r}")
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "plan": dict(plan) if plan is not None else None,
        "result": dict(result or {}),
        "messages": list(messages),
    }


def write_envelope(
    stream: IO[str],
    command: str,
    *,
    status: str,
    exit_code: int,
    plan: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
    messages: Iterable[str] = (),
) -> int:
    """
    @brief      Emit exactly one JSON envelope and return its exit code.
    @param[in]  stream Output stream.
    @param[in]  command Public command name.
    @param[in]  status Status token.
    @param[in]  exit_code Standardized exit code.
    @param[in]  plan Optional plan mapping.
    @param[in]  result Optional result mapping.
    @param[in]  messages Notes/errors.
    @return     ``exit_code``.
    @exception  ValueError On an invalid contract value.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    payload = command_envelope(
        command,
        status=status,
        exit_code=exit_code,
        plan=plan,
        result=result,
        messages=messages,
    )
    stream.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return exit_code


# END OF FILE
