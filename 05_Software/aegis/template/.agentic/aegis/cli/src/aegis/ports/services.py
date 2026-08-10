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
@brief   Declare injected clock, UUID, and exact-byte hash services.
@details Keeps nondeterministic and platform services outside application policy.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from datetime import datetime
from typing import Protocol

# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


class Clock(Protocol):
    """@brief Supply timezone-aware UTC time."""

    def now(self) -> datetime:
        """@return The current timezone-aware UTC datetime."""
        ...


class UUIDService(Protocol):
    """@brief Supply canonical UUIDv4 text."""

    def new_uuid(self) -> str:
        """@return A canonical lowercase UUIDv4 string."""
        ...


class HashService(Protocol):
    """@brief Hash exact bytes for revisions and deterministic summaries."""

    def digest(self, content: bytes) -> str:
        """@param[in] content Exact bytes. @return A prefixed SHA-256 digest."""
        ...


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
