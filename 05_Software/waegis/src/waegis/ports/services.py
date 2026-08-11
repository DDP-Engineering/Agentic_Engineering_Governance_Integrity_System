#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Define narrow service ports used by lifecycle application code."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class GitInitializer(Protocol):
    """Initialize one local repository without any outward action."""

    def initialize(self, target: Path) -> None:
        """Run local Git initialization."""
        ...
