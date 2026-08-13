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
@file    json_presenter.py
@brief   Render one compact version 1 machine response object.
@details Emits no prompt, ANSI sequence, progress text, or exception detail.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import json

from aegis.domain.results import OperationResult

# -----------------------------------------------------------------------------
# EXPORTED FUNCTIONS / PUBLIC API
# -----------------------------------------------------------------------------


def render_json(result: OperationResult, schema_version: int) -> str:
    """
    @brief Render the complete machine envelope without its framing LF.
    @param[in] result Presentation-neutral operation result.
    @param[in] schema_version Supported response schema version.
    @return One compact JSON object as Unicode text.
    """
    return json.dumps(
        result.to_envelope(schema_version),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    )


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
