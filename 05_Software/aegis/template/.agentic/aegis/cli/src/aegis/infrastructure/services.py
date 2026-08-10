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
@file    services.py
@brief   Implement standard-library clock, UUID, and SHA-256 services.
@details Supplies replaceable outer adapters for deterministic application tests.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------


class SystemClock:
    """@brief Return timezone-aware UTC system time."""

    def now(self) -> datetime:
        """@return The current timezone-aware UTC datetime."""
        return datetime.now(UTC)


class Uuid4Service:
    """@brief Generate UUIDv4 values through the operating-system RNG."""

    def new_uuid(self) -> str:
        """@return One canonical lowercase UUIDv4 string."""
        return str(uuid4())


class Sha256Service:
    """@brief Hash exact bytes using SHA-256."""

    def digest(self, content: bytes) -> str:
        """
        @param[in] content Exact bytes without normalization.
        @return Lowercase SHA-256 with the protocol prefix.
        """
        return f"sha256:{sha256(content).hexdigest()}"


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
