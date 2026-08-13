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
@file    product_operations.py
@brief   Implement bounded help and version application use cases.
@details Produces protocol-ready values without selecting presentation wording.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

from typing import Any

from aegis.application.operation_types import OperationContext, OperationDefinition
from aegis.domain.results import OperationResult, ProtocolError

# -----------------------------------------------------------------------------
# EXPORTED FUNCTIONS / PUBLIC API
# -----------------------------------------------------------------------------


def show_help(
    context: OperationContext,
    definition: OperationDefinition,
    inputs: dict[str, Any],
) -> OperationResult:
    """@brief Return fixed catalog or one exact operation's help metadata."""
    requested_operation = inputs.get("operation")
    if requested_operation is not None:
        entry = next(
            (
                candidate
                for candidate in context.catalog
                if requested_operation in {candidate.operation, candidate.command}
            ),
            None,
        )
        if entry is None:
            return OperationResult(
                product=context.product,
                product_version=context.product_version,
                operation=definition.operation,
                operation_id=context.operation_id,
                operation_status="error",
                message="The requested operation is not in this product catalog.",
                error=ProtocolError(
                    code="not_found",
                    summary="The requested operation does not exist.",
                    field="operation",
                    details={"operation": requested_operation},
                ),
            )
        data = {
            "operation": entry.operation,
            "command": entry.command,
            "purpose": entry.purpose,
            "required_arguments": entry.required_help_entries(),
            "optional_arguments": [
                argument.help_entry()
                for argument in entry.arguments
                if not argument.required
            ],
            "result": entry.result,
            "example": entry.example,
            "implemented": entry.implemented,
        }
        if entry.machine_revision_policy.requires_explicit_revision:
            data["revision"] = {
                "policy": entry.machine_revision_policy.value,
                "read_operation": entry.revision_read_operation,
            }
        if entry.machine_input is not None:
            data["machine_input"] = entry.machine_input.help_entry(entry.operation)
        return OperationResult(
            product=context.product,
            product_version=context.product_version,
            operation=definition.operation,
            operation_id=context.operation_id,
            operation_status="completed",
            message=f"Help for {entry.operation}.",
            data=data,
        )

    catalog = [
        {
            "operation": entry.operation,
            "command": entry.command,
            "implemented": entry.implemented,
        }
        for entry in context.catalog
    ]
    return OperationResult(
        product=context.product,
        product_version=context.product_version,
        operation=definition.operation,
        operation_id=context.operation_id,
        operation_status="completed",
        message=f"{context.product} exposes {len(catalog)} canonical operations.",
        data={"operations": catalog},
    )


def show_version(
    context: OperationContext,
    definition: OperationDefinition,
    inputs: dict[str, Any],
) -> OperationResult:
    """@brief Return product, protocol, catalog digest, and capabilities."""
    del inputs
    catalog = context.catalog
    canonical_catalog = "\n".join(entry.operation for entry in catalog).encode("utf-8")
    implemented = [entry.operation for entry in catalog if entry.implemented]
    unavailable = [entry.operation for entry in catalog if not entry.implemented]
    return OperationResult(
        product=context.product,
        product_version=context.product_version,
        operation=definition.operation,
        operation_id=context.operation_id,
        operation_status="completed",
        message=(
            f"{context.product} {context.product_version} uses protocol version "
            f"{context.protocol_version}."
        ),
        data={
            "protocol_version": context.protocol_version,
            "catalog_digest": context.hash_service.digest(canonical_catalog),
            "capabilities": {
                "implemented": implemented,
                "unavailable": unavailable,
            },
        },
    )


def unavailable_operation(
    context: OperationContext,
    definition: OperationDefinition,
    inputs: dict[str, Any],
) -> OperationResult:
    """@brief Report one valid declared operation as unavailable."""
    del inputs
    return OperationResult(
        product=context.product,
        product_version=context.product_version,
        operation=definition.operation,
        operation_id=context.operation_id,
        operation_status="error",
        message=f"{definition.operation} is not implemented in this installed version.",
        error=ProtocolError(
            code="capability_unavailable",
            summary="The operation is declared but is not yet available.",
            field="operation",
            retryable=False,
            details={"operation": definition.operation},
        ),
    )


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
