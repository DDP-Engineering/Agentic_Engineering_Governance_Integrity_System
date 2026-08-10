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
@file    test_services.py
@brief   Verify deterministic clock, UUID, and hash service boundaries.
@details Covers the injected-service seam required by IP-01 and TA-TEST-001.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from datetime import UTC, datetime

from aegis.infrastructure.services import Sha256Service, SystemClock, Uuid4Service

# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


def test_sha256_service_hashes_exact_bytes_deterministically() -> None:
    """@brief Verify exact-byte hashing and the protocol digest prefix."""
    service = Sha256Service()

    assert service.digest(b"AEGIS\r\n") == (
        "sha256:29b0796df56aea9d7f95c57f6fa0df999e2e8448b0aaf3e5d7742bf793223aa9"
    )
    assert service.digest(b"AEGIS\r\n") == service.digest(b"AEGIS\r\n")


def test_clock_returns_timezone_aware_utc() -> None:
    """@brief Verify the real clock satisfies the canonical UTC boundary."""
    observed = SystemClock().now()

    assert isinstance(observed, datetime)
    assert observed.tzinfo is UTC


def test_uuid_service_returns_canonical_uuid4_text() -> None:
    """@brief Verify generated UUIDs retain their version and canonical form."""
    value = Uuid4Service().new_uuid()

    assert len(value) == 36
    assert value == value.lower()
    assert value[14] == "4"


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
