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
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import pytest

import waegis
from waegis import version

# TESTS


def test_wizard_version_is_exported() -> None:
    """
    @brief      The package exposes the released wizard version (AD-11).
    @return     None
    @exception  AssertionError On a version mismatch.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.2.0
    """
    assert version.WIZARD_VERSION == "0.2.0"
    assert waegis.__version__ == version.WIZARD_VERSION


@pytest.mark.parametrize(
    ("payload_version", "expected"),
    [
        ("0.4.0", True),
        ("0.4.1", True),
        ("0.9.9", True),
        ("0.3.9", False),
        ("1.0.0", True),
        ("1.2.0", True),
        ("2.0.0", False),
    ],
)
def test_payload_compat_range(payload_version: str, expected: bool) -> None:
    """
    @brief      Payload compatibility respects ``>=0.4.0,<2.0`` (AD-11).
    @param[in]  payload_version Payload version under test.
    @param[in]  expected Expected compatibility verdict.
    @return     None
    @exception  AssertionError If the verdict does not match.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.1
    """
    assert version.is_payload_compatible(payload_version) is expected


def test_payload_compat_rejects_unparseable() -> None:
    """
    @brief      An unparseable payload version raises ``ValueError``.
    @return     None
    @exception  AssertionError If ``ValueError`` is not raised.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    with pytest.raises(ValueError):
        version.is_payload_compatible("not-a-version")

# END OF FILE
