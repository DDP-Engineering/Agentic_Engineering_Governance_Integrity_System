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
@brief WAEGIS and compatible AEGIS version contracts.
@details Keeps the release boundary small, explicit, and independent from the
         payload implementation. Only strict three-field semantic versions are
         accepted at mutation boundaries.
"""

# IMPORTS

from __future__ import annotations

import re

# CONSTANTS

WIZARD_VERSION = "3.0.0"
PAYLOAD_COMPAT_MIN = "3.0.0"
PAYLOAD_COMPAT_MAX = "4.0.0"
PAYLOAD_COMPAT_SPEC = ">=3.0.0,<4.0.0"
MANIFEST_VERSION = 2
ANSWERS_VERSION = 2

_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


# EXPORTED FUNCTIONS / PUBLIC API


def parse_semver(value: str) -> tuple[int, int, int, bool]:
    """
    @brief Parse a strict semantic version for compatibility comparison.
    @param[in] value Semantic version text.
    @return Major, minor, patch, and prerelease-presence tuple.
    @exception ValueError If the value is not strict SemVer.
    """
    match = _SEMVER.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid semantic version: {value!r}")
    return int(match[1]), int(match[2]), int(match[3]), match[4] is not None


def is_payload_compatible(payload_version: str) -> bool:
    """
    @brief Check the WAEGIS 3 to AEGIS 3 compatibility boundary.
    @param[in] payload_version Payload semantic version.
    @return True for stable AEGIS releases in ``>=3.0.0,<4.0.0``.
    """
    major, minor, patch, prerelease = parse_semver(payload_version)
    if prerelease:
        return False
    value = major, minor, patch
    lower = parse_semver(PAYLOAD_COMPAT_MIN)[:3]
    upper = parse_semver(PAYLOAD_COMPAT_MAX)[:3]
    return lower <= value < upper


# END OF FILE
