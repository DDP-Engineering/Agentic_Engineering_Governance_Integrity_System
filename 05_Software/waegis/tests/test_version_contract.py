#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_version_contract.py
@brief Tests the WAEGIS 3 and AEGIS 3 compatibility boundary.
@details Covers strict parsing, major-line limits, and package identity.
"""

import pytest

from waegis import __version__
from waegis.version import (
    MANIFEST_VERSION,
    PAYLOAD_COMPAT_SPEC,
    WIZARD_VERSION,
    is_payload_compatible,
    parse_semver,
)


def test_project_versions_are_final_owner_decisions() -> None:
    """@brief D4/D6 remain synchronized in the public package contract."""
    assert __version__ == WIZARD_VERSION == "3.0.0"
    assert PAYLOAD_COMPAT_SPEC == ">=3.0.0,<4.0.0"
    assert MANIFEST_VERSION == 2


@pytest.mark.parametrize(
    ("value", "expected"),
    [("3.0.0", True), ("3.9.99", True), ("2.99.99", False), ("4.0.0", False), ("3.1.0-rc.1", False)],
)
def test_payload_compatibility_is_one_stable_major(value: str, expected: bool) -> None:
    """@brief D6 accepts stable AEGIS 3 releases and no other major."""
    assert is_payload_compatible(value) is expected


@pytest.mark.parametrize("value", ["3", "3.0", "03.0.0", "3.0.x", "", "v3.0.0"])
def test_semver_parser_rejects_ambiguous_values(value: str) -> None:
    """@brief Mutation boundaries fail closed on non-SemVer versions."""
    with pytest.raises(ValueError):
        parse_semver(value)


# END OF FILE
