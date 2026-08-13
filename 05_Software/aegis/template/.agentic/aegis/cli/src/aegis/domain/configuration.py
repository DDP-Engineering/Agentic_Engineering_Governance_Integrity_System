#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file configuration.py @brief Define validated project configuration values."""

from __future__ import annotations

from dataclasses import dataclass

from aegis.domain.values import RepositoryPath, WorkingDirectory


@dataclass(frozen=True, slots=True)
class ValidationCommand:
    """@brief Define one named test, lint, or audit command guide."""

    category: str
    name: str
    command: tuple[str, ...]
    working_directory: WorkingDirectory


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """@brief Hold validated project paths, commands, and advisory policy."""

    requirements: RepositoryPath
    components: RepositoryPath
    test_roots: tuple[RepositoryPath, ...]
    adoptions: RepositoryPath
    runs: RepositoryPath
    commands: dict[str, ValidationCommand]
    risk_attention_threshold: str
    protected_scope_patterns: tuple[str, ...]


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
