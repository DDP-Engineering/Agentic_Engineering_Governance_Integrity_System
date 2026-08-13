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

import tomllib
from dataclasses import dataclass, replace
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
# LOCAL HELPERS
# -----------------------------------------------------------------------------


def _selected_run_id(workspace: Any) -> str | None:
    """@return Readable selected Run identity without raising protocol errors."""
    try:
        pointer = workspace.read_optional(f"{workspace.config.runs}/context.toml")
    except Exception:
        return None
    if pointer is not None:
        try:
            data = tomllib.loads(pointer.decode("utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError):
            return None
        selected = data.get("selected_run")
        if isinstance(selected, str) and selected:
            return selected
    active: list[str] = []
    for path in workspace.list_files(str(workspace.config.runs), suffix="run.md"):
        try:
            metadata, _, _ = workspace.load_document(path)
        except Exception:
            continue
        run_id = metadata.get("id")
        if (
            metadata.get("artifact_type") == "run"
            and metadata.get("status") == "active"
            and isinstance(run_id, str)
            and path == f"{workspace.config.runs}/{run_id}/run.md"
        ):
            active.append(run_id)
    return active[0] if len(active) == 1 else None


def _target_revision(
    workspace: Any,
    definition: Any,
    inputs: dict[str, Any],
) -> str | None:
    """@return Current explicit artifact revision when its target is readable."""
    target = definition.machine_revision_policy.value.rpartition(":")[2]
    identity = inputs.get(target)
    if not isinstance(identity, str) or not identity:
        return None
    roots_and_suffixes = {
        "requirement": (workspace.config.requirements, ".toml"),
        "component": (workspace.config.components, ".md"),
        "adoption": (workspace.config.adoptions, ".md"),
    }
    location = roots_and_suffixes.get(target)
    if location is None:
        return None
    root, suffix = location
    return workspace.revision(f"{root}/{identity}{suffix}")


def _resolved_error_context(
    workspace: Any,
    definition: Any,
    inputs: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    """@return Best readable explicit-target or selected workflow context."""
    explicit_run = inputs.get("run") or inputs.get("run_id")
    selected_run = _selected_run_id(workspace)
    run_candidates = tuple(
        candidate
        for index, candidate in enumerate((explicit_run, selected_run))
        if isinstance(candidate, str)
        and candidate
        and candidate not in (explicit_run, selected_run)[:index]
    )
    for run_id in run_candidates:
        try:
            run_path = f"{workspace.config.runs}/{run_id}/run.md"
            run_meta, run_state, run_revision = workspace.load_document(run_path)
            if run_meta.get("artifact_type") != "run" or run_meta.get("id") != run_id:
                continue
            current_stage = run_meta.get("current_stage")
            explicit_stage = inputs.get("stage_name") or inputs.get("stage")
            stage_candidates = tuple(
                candidate
                for index, candidate in enumerate((explicit_stage, current_stage))
                if isinstance(candidate, str)
                and candidate
                and candidate not in (explicit_stage, current_stage)[:index]
            )
            for stage in stage_candidates:
                summary = next(
                    (
                        item
                        for item in run_state.get("stages", [])
                        if item.get("name") == stage
                        and isinstance(item.get("path"), str)
                    ),
                    None,
                )
                if summary is None:
                    continue
                stage_path = f"{workspace.config.runs}/{run_id}/{summary['path']}"
                stage_meta, _, stage_revision = workspace.load_document(stage_path)
                if (
                    stage_meta.get("run_id") != run_id
                    or stage_meta.get("stage") != stage
                ):
                    continue
                revision_target = definition.machine_revision_policy.value.rpartition(
                    ":"
                )[2]
                revision = {
                    "run": run_revision,
                    "stage": stage_revision,
                }.get(revision_target)
                revision = revision or _target_revision(
                    workspace, definition, inputs
                )
                return run_id, stage, revision or stage_revision
            return run_id, None, run_revision
        except Exception:
            continue
    return None, None, None


def _enrich_error_context(
    result: OperationResult,
    workspace: Any | None,
    definition: Any,
    inputs: dict[str, Any],
) -> OperationResult:
    """@return Error with best-effort read-only context, or the original result."""
    if workspace is None or result.operation_status != "error":
        return result
    try:
        run_id, stage, revision = _resolved_error_context(
            workspace, definition, inputs
        )
    except Exception:
        return result
    if run_id is None and stage is None and revision is None:
        return result
    return replace(
        result,
        run_id=run_id,
        stage=stage,
        revision=revision,
    )

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
        missing_revision = (
            machine_mode
            and entry.machine_revision_policy.requires_explicit_revision
            and inputs.get("expected_revision") is None
        )
        if missing_revision:
            result = self.error_result(
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
            try:
                workspace = (
                    None
                    if repository is None
                    else self._services.workspaces(repository.root)
                )
            except Exception:
                workspace = None
            return _enrich_error_context(result, workspace, entry, inputs)

        workspace = (
            None
            if repository is None
            else self._services.workspaces(repository.root)
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
            workspace=workspace,
            catalog=operations_for(self._product),
            machine_mode=machine_mode,
        )
        result = entry.executor(context, entry, inputs)
        return _enrich_error_context(result, workspace, entry, inputs)

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
