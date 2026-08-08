#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file classify.py
@brief Pure three-way payload upgrade classification.
@details Compares baseline, repository, and new-payload hashes without reading
         files or granting write authority to non-managed dispositions.
"""

# IMPORTS

from __future__ import annotations

from enum import StrEnum

from .ownership import Disposition, permits_maintenance


# DATA MODELS / TYPEDEFINITIONS


class UpgradeAction(StrEnum):
    """@brief Deterministic action produced by the three-way classifier."""

    ADD = "add"
    REPLACE = "replace"
    REMOVE = "remove"
    UNCHANGED = "unchanged"
    CONVERGED = "converged"
    PRESERVE_LOCAL = "preserve-local"
    CONFLICT = "conflict"


class ConflictDecision(StrEnum):
    """@brief Path-specific operator resolution for a content conflict."""

    KEEP_LOCAL = "keep-local"
    TAKE_PAYLOAD = "take-payload"
    SIDECAR = "sidecar"


# EXPORTED FUNCTIONS / PUBLIC API


def classify_upgrade(
    baseline_hash: str | None,
    current_hash: str | None,
    payload_hash: str | None,
    disposition: Disposition | str = Disposition.MANAGED,
) -> UpgradeAction:
    """
    @brief Classify one V2-to-V2 path from three optional content hashes.
    @param[in] baseline_hash Hash installed by the current manifest.
    @param[in] current_hash Current repository hash, or None when absent.
    @param[in] payload_hash New payload hash, or None when removed upstream.
    @param[in] disposition Current maintenance authority.
    @return Pure upgrade action.
    """
    if not permits_maintenance(disposition):
        return UpgradeAction.PRESERVE_LOCAL
    if baseline_hash is None:
        if payload_hash is None:
            return UpgradeAction.UNCHANGED
        if current_hash is None:
            return UpgradeAction.ADD
        if current_hash == payload_hash:
            return UpgradeAction.CONVERGED
        return UpgradeAction.CONFLICT
    if payload_hash is None:
        if current_hash is None:
            return UpgradeAction.CONVERGED
        if current_hash == baseline_hash:
            return UpgradeAction.REMOVE
        return UpgradeAction.PRESERVE_LOCAL
    if current_hash is None:
        if payload_hash == baseline_hash:
            return UpgradeAction.PRESERVE_LOCAL
        return UpgradeAction.CONFLICT
    if current_hash == payload_hash:
        return UpgradeAction.CONVERGED if current_hash != baseline_hash else UpgradeAction.UNCHANGED
    if current_hash == baseline_hash:
        return UpgradeAction.REPLACE
    if payload_hash == baseline_hash:
        return UpgradeAction.PRESERVE_LOCAL
    return UpgradeAction.CONFLICT


def normalize_conflict_decision(value: str) -> ConflictDecision:
    """
    @brief Parse the V2 conflict vocabulary without global aliases.
    @param[in] value Exact operator/answers-file value.
    @return Normalized decision.
    @exception ValueError If the decision is not recognized.
    """
    normalized = "sidecar" if value == "write-sidecar" else value
    return ConflictDecision(normalized)


# END OF FILE
