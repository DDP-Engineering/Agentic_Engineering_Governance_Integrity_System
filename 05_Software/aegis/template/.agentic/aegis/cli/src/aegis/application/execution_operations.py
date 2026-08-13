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
@file    execution_operations.py
@brief   List configured command guidance and caller-reported evidence.
@details This module is intentionally read-only and has no process-runner path.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aegis.application.operation_types import OperationContext, OperationDefinition
from aegis.application.workflow_operations import (
    UseCaseError,
    _done,
    _load_run,
    _selected_run_id,
    _workspace,
)
from aegis.domain.results import OperationResult


def _execution_list(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    """@brief Return command guides and recent caller-reported Stage evidence."""
    workspace = _workspace(context)
    run_id = _selected_run_id(workspace)
    run_meta, _, _, _ = _load_run(workspace, run_id)
    stage = inputs.get("stage") or run_meta["current_stage"]
    ordered_stages = (
        "intake",
        "alignment",
        "requirement",
        "design",
        "check",
        "implementation",
        "validation",
        "delivery",
    )
    if stage not in ordered_stages:
        raise UseCaseError("invalid_input", "Stage name is invalid.", field="stage")
    stage_number = 1 + ordered_stages.index(stage)
    stage_path = f"{workspace.config.runs}/{run_id}/{stage_number:02d}-{stage}.md"
    _, state, revision = workspace.load_document(stage_path)
    commands = [
        {
            "category": value.category,
            "name": value.name,
            "command": list(value.command),
            "working_directory": str(value.working_directory),
        }
        for _, value in sorted(workspace.config.commands.items())
    ]
    evidence = [
        item
        for item in state["evidence"]
        if item.get("kind") == "automated" and item.get("provenance") == "reported"
    ]
    return _done(
        context,
        definition,
        "Configured command guidance and reported evidence listed.",
        data={"commands": commands, "evidence": evidence[-20:]},
        run_id=run_id,
        stage=stage,
        revision=revision,
    )


HANDLERS: dict[str, Callable[..., OperationResult]] = {
    "execution.list": _execution_list,
}


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
