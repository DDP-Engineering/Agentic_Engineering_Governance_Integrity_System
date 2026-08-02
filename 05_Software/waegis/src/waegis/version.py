#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file version.py
@brief Wizard version and compatible AEGIS payload version range (AD-11).
@details WAEGIS is versioned independently of the AEGIS payload it deploys. It
         pins a compatible payload version range so that a wizard build only
         drives payloads it understands. The range is inclusive of the minimum
         and exclusive of the maximum, mirroring ``>=MIN,<MAX`` semantics.
"""

# IMPORTS

from __future__ import annotations

import re

# CONSTANTS

# @brief Independent WAEGIS wizard version (SemVer).
WIZARD_VERSION = "1.2.0"

# @brief Inclusive lower bound of the compatible AEGIS payload version.
PAYLOAD_COMPAT_MIN = "2.0.0"

# @brief Exclusive upper bound of the compatible AEGIS payload version.
PAYLOAD_COMPAT_MAX = "3.0.0"

# @brief Human-readable compatibility specifier for reports and messages.
PAYLOAD_COMPAT_SPEC = ">=2.0.0,<3.0.0"


# HELPER FUNCTIONS


def _parse_version(text: str) -> tuple[int, ...]:
    """
    @brief      Parse a dotted numeric version string into a comparable tuple.
    @param[in]  text Version string such as ``"0.4.0"``; only the leading
                     dot-separated numeric fields are considered.
    @return     Tuple of integers for the numeric release fields.
    @exception  ValueError If no leading numeric field is present.
    """
    fields: list[int] = []
    for part in text.strip().split("."):
        match = re.match(r"[0-9]+", part)
        if match is None:
            break
        fields.append(int(match.group()))
    if not fields:
        raise ValueError(f"unparseable version: {text!r}")
    return tuple(fields)


# EXPORTED FUNCTIONS / PUBLIC API


def is_payload_compatible(payload_version: str) -> bool:
    """
    @brief      Report whether an AEGIS payload version is in the compatible
                range (AD-11): ``PAYLOAD_COMPAT_MIN <= v < PAYLOAD_COMPAT_MAX``.
    @param[in]  payload_version Dotted payload version string, e.g. ``"0.4.0"``.
    @return     ``True`` when the version lies within the supported range.
    @exception  ValueError If ``payload_version`` cannot be parsed.
    """
    value = _parse_version(payload_version)
    low = _parse_version(PAYLOAD_COMPAT_MIN)
    high = _parse_version(PAYLOAD_COMPAT_MAX)
    # Pad to equal length so "3" compares as (3, 0, 0), not below (3, 0, 0).
    width = max(len(value), len(low), len(high))

    def pad(fields: tuple[int, ...]) -> tuple[int, ...]:
        """
        @brief Pad one parsed version to the comparison width.
        """
        return fields + (0,) * (width - len(fields))

    return pad(low) <= pad(value) < pad(high)


# END OF FILE
