#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Define the local copy of the common AEGIS machine response contract."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProtocolError:
    """Describe one bounded operator-facing error."""

    code: str
    summary: str
    field: str | None = None
    path: str | None = None
    retryable: bool = False
    details: dict[str, Any] = dataclass_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the stable machine representation."""
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
    """Carry presentation-neutral WAEGIS operation output."""

    operation: str
    operation_id: str
    operation_status: str
    message: str
    data: dict[str, Any] = dataclass_field(default_factory=dict)
    findings: tuple[dict[str, Any], ...] = ()
    artifacts: tuple[dict[str, Any], ...] = ()
    next_actions: tuple[dict[str, Any], ...] = ()
    error: ProtocolError | None = None
    revision: str | None = None
    outcome: str | None = None
    truncated: bool = False
    details_ref: str | None = None

    def to_envelope(self, schema_version: int) -> dict[str, Any]:
        """Build the common versioned response envelope in canonical order."""
        from waegis.version import WIZARD_VERSION

        return {
            "schema": "aegis.machine.response",
            "schema_version": schema_version,
            "product": "WAEGIS",
            "product_version": WIZARD_VERSION,
            "operation": self.operation,
            "operation_id": self.operation_id,
            "operation_status": self.operation_status,
            "run_id": None,
            "stage": None,
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
