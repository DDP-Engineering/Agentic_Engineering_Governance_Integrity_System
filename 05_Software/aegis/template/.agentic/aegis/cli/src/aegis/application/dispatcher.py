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
@file    dispatcher.py
@brief   Resolve one registry operation and invoke one application use case.
@details Keeps flat command spelling and presentation outside dispatch policy.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aegis.application.operation_registry import find_operation, operations_for
from aegis.application.operation_types import (
    OperationContext,
    revision_read_next_actions,
)
from aegis.domain.results import OperationResult, ProtocolError
from aegis.ports.repository import RepositoryDiscovery, RepositoryDiscoveryError
from aegis.ports.services import Clock, HashService, UUIDService
from aegis.ports.workspace import WorkspaceFactory

# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """@brief Hold all replaceable services injected at composition."""

    clock: Clock
    uuid: UUIDService
    hashes: HashService
    repositories: RepositoryDiscovery
    workspaces: WorkspaceFactory


class Dispatcher:
    """@brief Dispatch one stable operation identifier through the registry."""

    def __init__(
        self,
        *,
        product: str,
        product_version: str,
        protocol_version: int,
        services: ApplicationServices,
    ) -> None:
        self._product = product
        self._product_version = product_version
        self._protocol_version = protocol_version
        self._services = services

    def _operation_id(self) -> str:
        value = self._services.uuid.new_uuid().replace("-", "").lower()
        return f"OP-{value}"

    def error_result(
        self,
        *,
        operation: str,
        code: str,
        summary: str,
        field: str | None = None,
        path: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
        next_actions: tuple[dict[str, Any], ...] = (),
    ) -> OperationResult:
        """@brief Construct one presentation-neutral error result."""
        return OperationResult(
            product=self._product,
            product_version=self._product_version,
            operation=operation,
            operation_id=self._operation_id(),
            operation_status="error",
            message=summary,
            error=ProtocolError(
                code=code,
                summary=summary,
                field=field,
                path=path,
                retryable=retryable,
                details={} if details is None else details,
            ),
            next_actions=next_actions,
        )

    def dispatch(
        self,
        operation: str,
        inputs: dict[str, Any],
        *,
        repository: Any | None = None,
        machine_mode: bool = False,
    ) -> OperationResult:
        """
        @brief Invoke exactly one registered use case.
        @param[in] operation Stable dotted operation identifier.
        @param[in] inputs Validated operation input values.
        @return One explicit application result.
        """
        entry = find_operation(operation, self._product)
        if entry is None:
            return self.error_result(
                operation=operation,
                code="invalid_input",
                summary="The requested operation is not in this product catalog.",
                field="command",
            )
        if (
            machine_mode
            and entry.machine_revision_policy.requires_explicit_revision
            and inputs.get("expected_revision") is None
        ):
            return self.error_result(
                operation=operation,
                code="invalid_input",
                summary=(
                    "This machine-mode mutation requires an explicit "
                    "expected revision."
                ),
                field="expected_revision",
                details={"policy": entry.machine_revision_policy.value},
                next_actions=revision_read_next_actions(entry, inputs),
            )

        operation_id = self._operation_id()
        context = OperationContext(
            product=self._product,
            product_version=self._product_version,
            protocol_version=self._protocol_version,
            operation_id=operation_id,
            clock=self._services.clock,
            uuid_service=self._services.uuid,
            hash_service=self._services.hashes,
            workspace=(
                None
                if repository is None
                else self._services.workspaces(repository.root)
            ),
            catalog=operations_for(self._product),
            machine_mode=machine_mode,
        )
        return entry.executor(context, entry, inputs)

    def resolve_repository(
        self, start: str, *, operation: str
    ) -> tuple[Any | None, OperationResult | None]:
        """@brief Resolve one installed repository or a structured error."""
        try:
            return self._services.repositories(start), None
        except RepositoryDiscoveryError as error:
            return None, self.error_result(
                operation=operation,
                code=error.code,
                summary=error.summary,
                field="repo",
                path=str(error.path),
            )

    def validate_repository(
        self,
        start: str,
        *,
        operation: str,
    ) -> OperationResult | None:
        """@brief Validate an explicitly supplied repository location."""
        _, error = self.resolve_repository(start, operation=operation)
        return error


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
