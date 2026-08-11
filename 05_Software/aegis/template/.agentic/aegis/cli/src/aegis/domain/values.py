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
@file    values.py
@brief   Define canonical repository values shared by AEGIS domain objects.
@details Keeps unsafe platform paths and unsupported enums out of durable state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath


class ValueValidationError(ValueError):
    """@brief Report one invalid domain value."""


@dataclass(frozen=True, slots=True)
class RepositoryPath:
    """@brief Store one canonical repository-relative forward-slash path."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.replace("\\", "/")
        parts = normalized.split("/")
        if (
            not normalized
            or normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or any(part in {"", ".", ".."} for part in parts)
            or str(PurePosixPath(normalized)) != normalized
        ):
            raise ValueValidationError(
                f"Repository path is not a safe canonical relative path: {self.value}"
            )
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        """@return The canonical serialized path."""
        return self.value


@dataclass(frozen=True, slots=True)
class WorkingDirectory:
    """@brief Store a command working directory, permitting repository root."""

    value: str

    def __post_init__(self) -> None:
        if self.value == ".":
            return
        object.__setattr__(self, "value", str(RepositoryPath(self.value)))

    def __str__(self) -> str:
        """@return The serialized repository-relative directory."""
        return self.value


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
