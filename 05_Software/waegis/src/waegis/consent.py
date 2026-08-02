#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file consent.py
@brief Shared fail-closed mutation approval contract.
@details Mutating public entry points use this helper after validation and plan
         construction but before journals, transactions, branches, or writes.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class ConfirmationAsker(Protocol):
    """@brief Minimal interactive confirmation seam."""

    def confirm(self, prompt: str, *, default: bool = True) -> bool:
        """@brief Return the operator's answer."""
        ...


class ConsentDecision(Enum):
    """@brief Terminal result of one mutation approval request."""

    APPROVED = "approved"
    DECLINED = "declined"
    NEEDS_INPUT = "needs-input"


def mutation_consent(
    *,
    mutation_planned: bool,
    yes: bool,
    asker: ConfirmationAsker | None,
    prompt: str,
) -> ConsentDecision:
    """
    @brief Resolve approval without mutating or inventing an affirmative answer.
    @param[in] mutation_planned Whether the displayed plan contains a write.
    @param[in] yes Explicit caller approval for that displayed plan.
    @param[in] asker Real interactive asker, or None when prompting is forbidden.
    @param[in] prompt Mutation-specific confirmation text.
    @return Approved, declined, or needs-input.
    @exception None
    """
    if not mutation_planned:
        return ConsentDecision.APPROVED
    if yes:
        return ConsentDecision.APPROVED
    if asker is None:
        return ConsentDecision.NEEDS_INPUT
    return ConsentDecision.APPROVED if asker.confirm(prompt, default=False) else ConsentDecision.DECLINED


# END OF FILE
