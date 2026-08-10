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
from typing import Any, Protocol

from aegis.domain.results import OperationResult
from aegis.ports.services import HashService

# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


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
class OperationContext:
    """@brief Supply one executor with product and deterministic services."""

    product: str
    product_version: str
    protocol_version: int
    operation_id: str
    hash_service: HashService
    catalog: tuple[OperationDefinition, ...]


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
    implemented: bool = False

    @property
    def command(self) -> str:
        """@return The mechanically derived canonical CLI token."""
        return self.operation.replace(".", "-").replace("_", "-")

    @property
    def required_arguments(self) -> tuple[str, ...]:
        """@return Ordered public names of required inputs."""
        return tuple(arg.display_name for arg in self.arguments if arg.required)

    @property
    def optional_arguments(self) -> tuple[str, ...]:
        """@return Ordered public names of optional inputs."""
        return tuple(arg.display_name for arg in self.arguments if not arg.required)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
