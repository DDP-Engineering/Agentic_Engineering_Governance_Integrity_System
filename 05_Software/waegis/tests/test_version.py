#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_version.py
@brief Tests for the WAEGIS version and payload compatibility range (AD-11).
@details Verifies the wizard version constant and the inclusive-min /
         exclusive-max payload compatibility check. Runs offline.
"""

# IMPORTS

from __future__ import annotations

import pytest

from waegis import version

# TESTS


@pytest.mark.parametrize(
    ("payload_version", "expected"),
    [
        ("1.9.9", False),
        ("2.0.0", True),
        ("2.0.1", True),
        ("2.9.9", True),
        ("3.0.0", False),
    ],
)
def test_payload_compat_range(payload_version: str, expected: bool) -> None:
    """
    @brief      Payload compatibility respects ``>=2.0.0,<3.0.0``.
    @param[in]  payload_version Payload version under test.
    @param[in]  expected Expected compatibility verdict.
    @return     None
    @exception  AssertionError If the verdict does not match.
    """
    assert version.is_payload_compatible(payload_version) is expected


def test_payload_compat_rejects_unparseable() -> None:
    """
    @brief      An unparseable payload version raises ``ValueError``.
    @return     None
    @exception  AssertionError If ``ValueError`` is not raised.
    """
    with pytest.raises(ValueError):
        version.is_payload_compatible("not-a-version")

# END OF FILE
