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
@file    operation_types.py
@brief   Define the data contracts consumed by operation declarations.
@details Keeps handlers independent from the registry that binds them.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from aegis.domain.results import OperationResult
from aegis.ports.services import Clock, HashService, UUIDService
from aegis.ports.workspace import Workspace

# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


class MachineRevisionPolicy(StrEnum):
    """@brief Classify the caller revision contract for one machine operation."""

    EXEMPT_READ_ONLY = "exempt:read_only"
    EXEMPT_CREATE = "exempt:create"
    EXEMPT_WORKING_CONTEXT = "exempt:working_context"
    EXEMPT_SEPARATE_PLAN_PROTOCOL = "exempt:separate_plan_protocol"
    REQUIRED_RUN = "required:run"
    CONDITIONAL_RUN = "conditional:run"
    REQUIRED_STAGE = "required:stage"
    REQUIRED_REQUIREMENT = "required:requirement"
    REQUIRED_COMPONENT = "required:component"
    REQUIRED_ADOPTION = "required:adoption"

    @property
    def requires_explicit_revision(self) -> bool:
        """@return Whether every machine invocation requires a caller token."""
        return self.value.startswith("required:")


@dataclass(frozen=True, slots=True)
class ArgumentDefinition:
    """@brief Declare one CLI and help input in registry-ready form."""

    name: str
    flags: tuple[str, ...]
    display_name: str
    description: str
    required: bool = False
    choices: tuple[str, ...] = ()
    metavar: str | None = None

    @property
    def positional(self) -> bool:
        """@return Whether argparse should treat this as a positional input."""
        return not self.flags[0].startswith("-")

    def help_entry(self) -> dict[str, str]:
        """@return The bounded public help representation of this input."""
        return {"name": self.display_name, "description": self.description}


@dataclass(frozen=True, slots=True)
class DataFieldDefinition:
    """@brief Describe one accepted field inside machine input data."""

    name: str
    type_name: str
    description: str
    required: bool = True
    choices: tuple[str, ...] = ()

    def help_entry(self) -> dict[str, Any]:
        """@return One deterministic public machine-data field description."""
        entry: dict[str, Any] = {
            "name": self.name,
            "type": self.type_name,
            "required": self.required,
            "description": self.description,
        }
        if self.choices:
            entry["choices"] = list(self.choices)
        return entry


@dataclass(frozen=True, slots=True)
class MachineInputDefinition:
    """@brief Describe one operation-specific machine input envelope."""

    data_fields: tuple[DataFieldDefinition, ...]
    constraints: tuple[str, ...] = ()

    def help_entry(self, operation: str) -> dict[str, Any]:
        """
        @brief Render the complete bounded request shape for one operation.
        @param[in] operation Stable operation identifier placed in the envelope.
        @return JSON-compatible help metadata for one structured request.
        """
        return {
            "source": "Use --input <path> for UTF-8 JSON or --input - for stdin.",
            "envelope": {
                "schema": "aegis.machine.input",
                "schema_version": 1,
                "operation": operation,
                "data": "Object containing the data_fields below.",
            },
            "data_fields": [field.help_entry() for field in self.data_fields],
            "constraints": list(self.constraints),
        }


@dataclass(frozen=True, slots=True)
class OperationContext:
    """@brief Supply one executor with product and deterministic services."""

    product: str
    product_version: str
    protocol_version: int
    operation_id: str
    clock: Clock
    uuid_service: UUIDService
    hash_service: HashService
    workspace: Workspace | None
    catalog: tuple[OperationDefinition, ...]
    machine_mode: bool


class OperationExecutor(Protocol):
    """@brief Describe the single executor signature used by dispatch."""

    def __call__(
        self,
        context: OperationContext,
        definition: OperationDefinition,
        inputs: dict[str, Any],
    ) -> OperationResult:
        """@return One presentation-neutral result."""
        ...


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    """@brief Describe one stable operation, its inputs, help, and executor."""

    operation: str
    purpose: str
    result: str
    example: str
    products: frozenset[str]
    arguments: tuple[ArgumentDefinition, ...]
    executor: OperationExecutor
    machine_revision_policy: MachineRevisionPolicy
    machine_input: MachineInputDefinition | None = None
    implemented: bool = False

    @property
    def command(self) -> str:
        """@return The mechanically derived canonical CLI token."""
        return self.operation.replace(".", "-").replace("_", "-")

    @property
    def required_arguments(self) -> tuple[str, ...]:
        """@return Ordered public names of required inputs."""
        arguments = tuple(arg.display_name for arg in self.arguments if arg.required)
        if self.machine_revision_policy.requires_explicit_revision:
            return (*arguments, "--expected-revision <sha256>")
        return arguments

    @property
    def optional_arguments(self) -> tuple[str, ...]:
        """@return Ordered public names of optional inputs."""
        return tuple(arg.display_name for arg in self.arguments if not arg.required)

    @property
    def revision_read_operation(self) -> str | None:
        """@return Read operation that yields this mutation's revision token."""
        target = self.machine_revision_policy.value.rpartition(":")[2]
        return {
            "run": "run.show",
            "stage": "stage.show",
            "requirement": "requirement.show",
            "component": "component.show",
            "adoption": "adoption.show",
        }.get(target)

    def required_help_entries(self) -> list[dict[str, str]]:
        """@return Required argument help derived from arguments and policy."""
        entries = [
            argument.help_entry() for argument in self.arguments if argument.required
        ]
        if self.machine_revision_policy.requires_explicit_revision:
            entries.append(
                {
                    "name": "--expected-revision <sha256>",
                    "description": (
                        "Use the revision returned by "
                        f"{self.revision_read_operation} before this mutation."
                    ),
                }
            )
        return entries


# -----------------------------------------------------------------------------
# EXPORTED FUNCTIONS / PUBLIC API
# -----------------------------------------------------------------------------


def revision_read_next_actions(
    definition: OperationDefinition, inputs: dict[str, Any]
) -> tuple[dict[str, Any], ...]:
    """
    @brief Build the corrective read for one revision-governed operation.
    @param[in] definition Operation whose revision must be refreshed.
    @param[in] inputs Validated inputs carrying any selected artifact identity.
    @return Zero or one read action that obtains the current artifact revision.
    """
    target = definition.machine_revision_policy.value.rpartition(":")[2]
    read_operation = definition.revision_read_operation
    if read_operation is None:
        return ()
    arguments: dict[str, Any] = {}
    if target in {"requirement", "component", "adoption"} and inputs.get(target):
        arguments[target] = inputs[target]
    elif target == "stage" and definition.operation in {
        "stage.start",
        "stage.revisit",
    }:
        arguments["stage"] = inputs.get("stage_name")
    return (
        {
            "operation": read_operation,
            "arguments": arguments,
            "reason": f"Read the current {target.title()} revision before retrying.",
        },
    )


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
