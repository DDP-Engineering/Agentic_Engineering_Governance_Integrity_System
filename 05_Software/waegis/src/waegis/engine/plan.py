#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file plan.py
@brief Plan-preview data model for wizard runs ("terraform plan" style, §4).
@details Pure data only: an ordered, immutable description of the steps a run
         will execute and what each will change, approved by the operator once
         before any mutation. Contains no formatting — the console frontend
         (T1.3) and the GUI (M8) render these structures; ``to_dict`` provides
         the JSON/`--json` seam.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .step import Automation, EngineContext, Phase, StepSpec

# PUBLIC API


@dataclass(frozen=True)
class PlannedStep:
    """
    @brief One row of a plan preview: the operator-facing summary of a step.
    @details Snapshots the static contract fields plus the ``change_summary``
             the step computed for the current context, so the preview can be
             rendered (or serialized) without re-invoking any step callable.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    id: str
    title: str
    why: str
    phase: Phase
    automation: Automation
    change_summary: str

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the planned step to a JSON-safe mapping.
        @return     Mapping keyed ``id, title, why, phase, automation,
                    change_summary``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return {
            "id": self.id,
            "title": self.title,
            "why": self.why,
            "phase": self.phase.value,
            "automation": self.automation.value,
            "change_summary": self.change_summary,
        }


@dataclass(frozen=True)
class Plan:
    """
    @brief Ordered, immutable preview of a run approved before any mutation.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    mode: str
    dry_run: bool
    steps: tuple[PlannedStep, ...]

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the plan to a JSON-safe mapping.
        @return     Mapping keyed ``mode, dry_run, steps``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return {
            "mode": self.mode,
            "dry_run": self.dry_run,
            "steps": [step.to_dict() for step in self.steps],
        }


def build_plan(mode: str, dry_run: bool, steps: list[StepSpec], ctx: EngineContext) -> Plan:
    """
    @brief      Build a :class:`Plan` preview from the ordered, applicable steps.
    @param[in]  mode Wizard mode label carried into the preview.
    @param[in]  dry_run Whether the run will stop after the preview.
    @param[in]  steps Ordered, already ``applies``-filtered step specs.
    @param[in]  ctx Engine context used to compute each step's change summary.
    @return     The immutable :class:`Plan` for the run.
    @exception  Exception Propagates any error raised by a step's
                ``change_summary`` callable.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    planned = tuple(
        PlannedStep(
            id=spec.id,
            title=spec.title,
            why=spec.why,
            phase=spec.phase,
            automation=spec.automation,
            change_summary=spec.change_summary(ctx),
        )
        for spec in steps
    )
    return Plan(mode=mode, dry_run=dry_run, steps=planned)


# END OF FILE
