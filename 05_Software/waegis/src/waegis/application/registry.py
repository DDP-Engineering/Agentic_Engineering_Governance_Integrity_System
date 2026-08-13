#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Declare the single WAEGIS command, help, schema, and dispatch registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    """Describe one complete flat CLI operation."""

    operation: str
    purpose: str
    arguments: tuple[str, ...] = ()
    optional_arguments: tuple[str, ...] = ()

    @property
    def command(self) -> str:
        """Derive the canonical flat token."""
        return self.operation.replace(".", "-").replace("_", "-")


OPERATIONS = (
    OperationDefinition("help.show", "Show WAEGIS operations."),
    OperationDefinition("version.show", "Show WAEGIS version."),
    OperationDefinition(
        "plan.show",
        "Review one exact lifecycle plan without action bodies.",
        ("plan",),
        ("offset", "limit"),
    ),
    OperationDefinition(
        "repository_init.plan",
        "Preview local Git initialization.",
        ("target", "output"),
    ),
    OperationDefinition(
        "repository_init.apply",
        "Apply authorized local Git initialization.",
        ("target", "plan", "confirm_digest"),
    ),
    OperationDefinition(
        "install.plan", "Preview AEGIS installation.", ("target", "output")
    ),
    OperationDefinition(
        "install.apply",
        "Apply an authorized AEGIS installation.",
        ("target", "plan", "confirm_digest"),
    ),
    OperationDefinition(
        "upgrade.plan",
        "Preview manifest-owned payload replacement.",
        ("target", "output"),
    ),
    OperationDefinition(
        "upgrade.apply",
        "Apply authorized payload replacement.",
        ("target", "plan", "confirm_digest"),
    ),
    OperationDefinition(
        "remove.plan", "Preview manifest-owned payload removal.", ("target", "output")
    ),
    OperationDefinition(
        "remove.apply",
        "Apply authorized payload removal.",
        ("target", "plan", "confirm_digest"),
    ),
)


def operation_by_name(name: str) -> OperationDefinition | None:
    """Resolve an operation identifier or canonical command token."""
    return next(
        (entry for entry in OPERATIONS if name in {entry.operation, entry.command}),
        None,
    )
