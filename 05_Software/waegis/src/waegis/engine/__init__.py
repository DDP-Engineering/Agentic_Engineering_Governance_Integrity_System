#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file __init__.py
@brief Public surface of the WAEGIS step engine (plan §4).
@details Re-exports the step contract, catalog, plan-preview model, journal, and
         runner so both wizard journeys import a single stable name (T1.1). The
         engine imports only the standard library and itself.
"""

# IMPORTS

from __future__ import annotations

from .catalog import Catalog
from .journal import (
    JOURNAL_VERSION,
    STATUS_COMPLETED,
    STATUS_DECLINED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_STOPPED,
    Journal,
    utc_now_iso,
    waegis_home,
)
from .plan import Plan, PlannedStep, build_plan
from .runner import RunSummary, run
from .step import (
    GREEN_STATUSES,
    Asker,
    Automation,
    CatalogError,
    EngineContext,
    EngineError,
    EngineEvent,
    EventSink,
    NullSink,
    Note,
    Phase,
    PlanApproved,
    PlanReady,
    PlanRejected,
    Remediation,
    RunFinished,
    RunStarted,
    StepActed,
    StepContractError,
    StepDetected,
    StepFinished,
    StepResult,
    StepSpec,
    StepStarted,
    StepStatus,
    StepVerified,
)

# CONSTANTS

# @brief Public engine names, stable for both wizard journeys and frontends.
__all__ = [
    # contract
    "Asker",
    "Automation",
    "EngineContext",
    "EngineError",
    "CatalogError",
    "StepContractError",
    "GREEN_STATUSES",
    "NullSink",
    "Phase",
    "Remediation",
    "StepResult",
    "StepSpec",
    "StepStatus",
    # events
    "EngineEvent",
    "EventSink",
    "Note",
    "PlanApproved",
    "PlanReady",
    "PlanRejected",
    "RunFinished",
    "RunStarted",
    "StepActed",
    "StepDetected",
    "StepFinished",
    "StepStarted",
    "StepVerified",
    # catalog / plan
    "Catalog",
    "Plan",
    "PlannedStep",
    "build_plan",
    # journal
    "Journal",
    "JOURNAL_VERSION",
    "STATUS_COMPLETED",
    "STATUS_DECLINED",
    "STATUS_FAILED",
    "STATUS_IN_PROGRESS",
    "STATUS_STOPPED",
    "utc_now_iso",
    "waegis_home",
    # runner
    "RunSummary",
    "run",
]

# END OF FILE
