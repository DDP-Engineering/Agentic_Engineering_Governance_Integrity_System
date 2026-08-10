#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    human_presenter.py
@brief   Render concise human-readable operation results.
@details Presents the same result values consumed by the JSON presenter.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import json

from aegis.domain.results import OperationResult

# -----------------------------------------------------------------------------
# EXPORTED FUNCTIONS / PUBLIC API
# -----------------------------------------------------------------------------


def render_human(result: OperationResult) -> str:
    """
    @brief Render stable semantic labels without duplicating application policy.
    @param[in] result Presentation-neutral operation result.
    @return Plain text ending without a newline.
    """
    lines = [
        result.message,
        f"Operation: {result.operation}",
        f"Status: {result.operation_status}",
        f"Product: {result.product} {result.product_version}",
    ]
    if result.outcome is not None:
        lines.append(f"Outcome: {result.outcome}")
    for key, value in result.data.items():
        if key == "operations" and isinstance(value, list):
            lines.append("operations:")
            for operation in value:
                availability = (
                    "available" if operation.get("implemented") else "unavailable"
                )
                lines.append(
                    f"  - {operation.get('command', 'unknown')}: "
                    f"{operation.get('operation', 'unknown')} ({availability})"
                )
            continue
        rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"{key}: {rendered}")
    for finding in result.findings:
        lines.append(f"Finding: {finding.get('code', 'unknown')}")
    for artifact in result.artifacts:
        lines.append(f"Artifact: {artifact.get('path', 'unknown')}")
    if result.error is not None:
        lines.append(f"Error: {result.error.code}: {result.error.summary}")
    for action in result.next_actions[:3]:
        lines.append(f"Next: {action.get('operation', 'unknown')}")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
