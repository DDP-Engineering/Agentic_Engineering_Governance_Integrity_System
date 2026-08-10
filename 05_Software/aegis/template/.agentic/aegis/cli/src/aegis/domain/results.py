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
@file    results.py
@brief   Define presentation-neutral operation results and structured errors.
@details Models every required field of the version 1 machine envelope.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any

# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProtocolError:
    """@brief Describe one bounded operational error."""

    code: str
    summary: str
    field: str | None = None
    path: str | None = None
    retryable: bool = False
    details: dict[str, Any] = dataclass_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """@return The stable machine representation of this error."""
        return {
            "code": self.code,
            "summary": self.summary,
            "field": self.field,
            "path": self.path,
            "retryable": self.retryable,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class OperationResult:
    """@brief Carry one use-case result across both presenters."""

    product: str
    product_version: str
    operation: str
    operation_id: str
    operation_status: str
    message: str
    data: dict[str, Any] = dataclass_field(default_factory=dict)
    run_id: str | None = None
    stage: str | None = None
    revision: str | None = None
    outcome: str | None = None
    findings: tuple[dict[str, Any], ...] = ()
    artifacts: tuple[dict[str, Any], ...] = ()
    next_actions: tuple[dict[str, Any], ...] = ()
    error: ProtocolError | None = None
    truncated: bool = False
    details_ref: str | None = None

    def to_envelope(self, schema_version: int) -> dict[str, Any]:
        """
        @brief Build the deterministic machine response envelope.
        @param[in] schema_version Requested supported protocol version.
        @return All required fields in protocol order.
        """
        return {
            "schema": "aegis.machine.response",
            "schema_version": schema_version,
            "product": self.product,
            "product_version": self.product_version,
            "operation": self.operation,
            "operation_id": self.operation_id,
            "operation_status": self.operation_status,
            "run_id": self.run_id,
            "stage": self.stage,
            "revision": self.revision,
            "outcome": self.outcome,
            "message": self.message,
            "data": self.data,
            "findings": list(self.findings),
            "artifacts": list(self.artifacts),
            "next_actions": list(self.next_actions[:3]),
            "error": None if self.error is None else self.error.to_dict(),
            "truncated": self.truncated or len(self.next_actions) > 3,
            "details_ref": self.details_ref,
        }


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
