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
@file    repository.py
@brief   Define the application-facing repository discovery seam.
@details Keeps filesystem traversal in the infrastructure adapter.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InstalledRepository:
    """@brief Identify the repository root and required configuration marker."""

    root: Path
    config_path: Path


class RepositoryDiscoveryError(Exception):
    """@brief Report that a path is not inside an installed Git repository."""

    code = "repository_error"

    def __init__(self, summary: str, path: Path) -> None:
        super().__init__(summary)
        self.summary = summary
        self.path = path


class RepositoryDiscovery(Protocol):
    """@brief Resolve a path to one installed repository boundary."""

    def __call__(self, start: str | Path) -> InstalledRepository:
        """@return The installed repository or raise a bounded error."""
        ...


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
