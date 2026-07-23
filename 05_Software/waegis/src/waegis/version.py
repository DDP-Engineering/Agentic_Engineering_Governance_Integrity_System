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
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.1
"""

# IMPORTS

from __future__ import annotations

# CONSTANTS

# @brief Independent WAEGIS wizard version (SemVer).
WIZARD_VERSION = "0.3.0"

# @brief Inclusive lower bound of the compatible AEGIS payload version.
PAYLOAD_COMPAT_MIN = "0.4.0"

# @brief Exclusive upper bound of the compatible AEGIS payload version.
PAYLOAD_COMPAT_MAX = "2.0.0"

# @brief Human-readable compatibility specifier for reports and messages.
PAYLOAD_COMPAT_SPEC = ">=0.4.0,<2.0"


# HELPER FUNCTIONS


def _parse_version(text: str) -> tuple[int, ...]:
    """
    @brief      Parse a dotted numeric version string into a comparable tuple.
    @param[in]  text Version string such as ``"0.4.0"``; only the leading
                     dot-separated numeric fields are considered.
    @return     Tuple of integers for the numeric release fields.
    @exception  ValueError If no leading numeric field is present.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    fields: list[int] = []
    for part in text.strip().split("."):
        digits = ""
        for char in part:
            if char.isdigit():
                digits += char
            else:
                break
        if digits == "":
            break
        fields.append(int(digits))
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    value = _parse_version(payload_version)
    return _parse_version(PAYLOAD_COMPAT_MIN) <= value < _parse_version(PAYLOAD_COMPAT_MAX)


# END OF FILE
