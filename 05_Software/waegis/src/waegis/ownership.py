#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file ownership.py
@brief Payload ownership and maintenance authority rules.
@details Classifies every shipped payload path before installation. Only the
         managed disposition grants repair or upgrade write authority.
"""

# IMPORTS

from __future__ import annotations

from enum import StrEnum


# DATA MODELS / TYPEDEFINITIONS


class Disposition(StrEnum):
    """@brief Per-file authority recorded by manifest schema 2."""

    MANAGED = "managed"
    GENERATED = "generated"
    SEEDED = "seeded"
    KEPT_LOCAL = "kept-local"
    SIDECAR = "sidecar"


# CONSTANTS

_SEEDED_EXACT = frozenset(
    {
        "CHANGELOG.md",
        ".agentic/components.toml",
        ".agentic/requirements/coverage_waivers.txt",
        ".agentic/knowledge/components/index.md",
    }
)
_SEEDED_SUFFIXES = ("/.gitkeep",)
_PROJECT_OWNED_PREFIXES = (
    ".agentic/requirements/",
    ".agentic/knowledge/",
    ".agentic/reports/",
    ".agentic/runs/",
    ".agentic/.workspace/",
)
_MANAGED_PROJECT_MATERIAL = frozenset(
    {
        ".agentic/requirements/README.md",
        ".agentic/requirements/spec_template.md",
        ".agentic/knowledge/components/component_template.md",
        ".agentic/reports/adoption/README.md",
        ".agentic/reports/adoption/adoption_report_template.md",
    }
)


# EXPORTED FUNCTIONS / PUBLIC API


def initial_disposition(path: str) -> Disposition:
    """
    @brief Return the initial ownership class for one canonical payload path.
    @param[in] path Canonical forward-slash payload path.
    @return Generated, seeded, or managed disposition.
    """
    if path == ".agentic/workflow.toml":
        return Disposition.GENERATED
    if path in _MANAGED_PROJECT_MATERIAL:
        return Disposition.MANAGED
    if path in _SEEDED_EXACT or path.endswith(_SEEDED_SUFFIXES):
        return Disposition.SEEDED
    if path.startswith(_PROJECT_OWNED_PREFIXES):
        return Disposition.SEEDED
    return Disposition.MANAGED


def permits_maintenance(disposition: Disposition | str) -> bool:
    """
    @brief Report whether repair/upgrade may write a path automatically.
    @param[in] disposition Manifest disposition.
    @return True only for managed files.
    """
    return Disposition(disposition) is Disposition.MANAGED


# END OF FILE
