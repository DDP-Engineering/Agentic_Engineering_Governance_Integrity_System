#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    execution_operations.py
@brief   Execute configured commands and record evidence/test integrity.
@details Keeps project outcomes separate from AEGIS protocol completion.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aegis.application.operation_types import OperationContext, OperationDefinition
from aegis.application.workflow_operations import (
    UseCaseError,
    _artifact,
    _done,
    _event,
    _identity,
    _load_current,
    _load_run,
    _save_stage_run,
    _selected_run_id,
    _time,
    _workspace,
)
from aegis.domain.results import OperationResult
from aegis.ports.workspace import RepositoryMutation, Workspace

_OUTPUT_LIMIT = 8192


def _selection_arguments(
    workspace: Workspace,
    run_id: str,
    run_state: dict[str, Any],
    command: tuple[str, ...],
    label: str,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Resolve one durable trace selection into framework-ready arguments."""
    selection = None
    for summary in run_state["stages"]:
        path = f"{workspace.config.runs}/{run_id}/{summary['path']}"
        _, state, _ = workspace.load_document(path)
        selection = next(
            (
                item
                for item in state.get("evidence", [])
                if item.get("kind") == "trace_selection" and item.get("label") == label
            ),
            None,
        )
        if selection is not None:
            break
    if selection is None:
        raise UseCaseError(
            "not_found", "Impacted selection label does not exist.", field="selection"
        )
    if selection.get("mode") == "full":
        return (), selection
    executable = " ".join(command).lower()
    arguments: list[str] = []
    for test in selection.get("tests", []):
        path = test["path"]
        selector = test.get("selector", "")
        if "pytest" in executable:
            arguments.append(f"{path}::{selector}" if selector else path)
        elif "unittest" in executable:
            module = path.removesuffix(".py").replace("/", ".")
            arguments.append(f"{module}.{selector}" if selector else module)
        else:
            arguments.append(selector or path)
    return tuple(arguments), selection


def _fingerprints(context: OperationContext, workspace: Workspace) -> dict[str, str]:
    result = {}
    for root in workspace.config.test_roots:
        for path in workspace.list_files(str(root)):
            result[path] = context.hash_service.digest(workspace.read_bytes(path))
    return result


def _finding_summary(finding: dict[str, Any], stage_path: str) -> dict[str, Any]:
    return {
        "label": finding["label"],
        "code": finding["code"],
        "severity": finding["severity"],
        "summary": finding["observation"],
        "disposition": finding["disposition"],
        "artifact": stage_path,
    }


def _execution_run(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    category = inputs.get("category")
    name = inputs.get("name")
    if (
        category not in {"tests", "lints", "audits"}
        or not isinstance(name, str)
        or not name
    ):
        raise UseCaseError("invalid_input", "Execution category or name is invalid.")
    (
        run_id,
        run_meta,
        run_state,
        run_revision,
        run_path,
        stage_meta,
        stage_state,
        stage_revision,
        stage_path,
    ) = _load_current(workspace)
    stage = stage_meta["stage"]
    if category == "tests" and stage not in {"check", "implementation", "validation"}:
        raise UseCaseError(
            "invalid_transition",
            "Tests execute only during Check, Implementation, or Validation.",
        )
    if category in {"lints", "audits"} and stage != "validation":
        raise UseCaseError(
            "invalid_transition", "Lints and audits execute only during Validation."
        )
    configured = workspace.config.commands.get(f"{category}.{name}")
    if configured is None:
        raise UseCaseError("not_found", "Configured validation command does not exist.")
    selection_label = inputs.get("selection")
    additional_arguments: tuple[str, ...] = ()
    selection = None
    if selection_label is not None:
        if category != "tests" or not isinstance(selection_label, str):
            raise UseCaseError(
                "invalid_input",
                "Only test execution can consume a selection label.",
                field="selection",
            )
        additional_arguments, selection = _selection_arguments(
            workspace,
            run_id,
            run_state,
            configured.command,
            selection_label,
        )
    command, result = workspace.execute_command(
        category,
        name,
        additional_arguments=additional_arguments,
    )
    now = _time(context)
    stdout_tail = result.stdout[-4096:].decode("utf-8", "replace")
    stderr_tail = result.stderr[-4096:].decode("utf-8", "replace")
    evidence = {
        "label": f"E{len(stage_state['evidence']) + 1}",
        "kind": "automated",
        "time": now,
        "category": category,
        "name": name,
        "command": list(command.command + additional_arguments),
        "working_directory": str(command.working_directory),
        "timeout_seconds": command.timeout_seconds,
        "outcome": result.outcome,
        "engineering_conclusion": result.engineering_conclusion,
        "exit_status": result.exit_status,
        "duration_seconds": round(result.duration_seconds, 6),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "reason": result.reason,
        "selection": selection_label,
        "selection_mode": None if selection is None else selection.get("mode"),
        "attachment": None,
    }
    findings: list[dict[str, Any]] = []
    if category == "tests" and stage == "check" and result.outcome == "failed":
        evidence["fingerprints"] = _fingerprints(context, workspace)
        evidence["red_witness"] = True
    elif category == "tests" and stage in {"implementation", "validation"}:
        check_path = f"{workspace.config.runs}/{run_id}/05-check.md"
        _, check_state, _ = workspace.load_document(check_path)
        red = next(
            (
                item
                for item in reversed(check_state["evidence"])
                if item.get("red_witness")
            ),
            None,
        )
        if red is not None:
            current = _fingerprints(context, workspace)
            changed = sorted(
                path
                for path in set(red.get("fingerprints", {})) | set(current)
                if current.get(path) != red.get("fingerprints", {}).get(path)
            )
            evidence["red_fingerprint_comparison"] = {
                "changed_tests": changed,
                "current": current,
            }
            for changed_path in changed:
                findings.append(
                    {
                        "label": f"F{len(stage_state['findings']) + len(findings) + 1}",
                        "code": "test_changed_after_red",
                        "severity": "warning",
                        "observation": f"{changed_path} changed after red evidence.",
                        "consequence": (
                            "The developer must judge whether the correction "
                            "is legitimate."
                        ),
                        "disposition": "open",
                        "time": now,
                    }
                )
    if result.outcome != "passed":
        findings.append(
            {
                "label": f"F{len(stage_state['findings']) + len(findings) + 1}",
                "code": f"execution_{result.outcome}",
                "severity": "warning",
                "observation": f"{category}.{name} recorded {result.outcome}.",
                "consequence": (
                    "Engineering conclusion is failed only for a completed "
                    "failing status; otherwise it is unknown."
                ),
                "disposition": "open",
                "time": now,
            }
        )
    extra: list[RepositoryMutation] = []
    artifacts: list[dict[str, Any]] = []
    if len(result.stdout) + len(result.stderr) > _OUTPUT_LIMIT:
        attachment_id = _identity(context, "ATTACH")
        attachment_path = f"{workspace.config.runs}/{run_id}/{attachment_id}.log"
        content = b"STDOUT\n" + result.stdout + b"\nSTDERR\n" + result.stderr
        evidence["attachment"] = {
            "path": attachment_path,
            "size": len(content),
            "sha256": context.hash_service.digest(content),
        }
        extra.append(RepositoryMutation(attachment_path, content))
    stage_state["evidence"].append(evidence)
    stage_state["findings"].extend(findings)
    stage_state["events"].append(
        _event(
            now,
            "operator",
            "execution_recorded",
            f"{category}.{name} -> {result.outcome}",
        )
    )
    stage_meta["updated_at"] = now
    run_meta["updated_at"] = now
    revisions = _save_stage_run(
        workspace,
        stage_path=stage_path,
        stage_meta=stage_meta,
        stage_state=stage_state,
        stage_revision=stage_revision,
        run_path=run_path,
        run_meta=run_meta,
        run_state=run_state,
        run_revision=run_revision,
        extra=tuple(extra),
        extra_expected={item.path: None for item in extra},
    )
    for item in extra:
        artifacts.append(
            _artifact(item.path, "created", revisions[item.path], kind="attachment")
        )
    return _done(
        context,
        definition,
        f"{category}.{name} execution outcome recorded: {result.outcome}.",
        data={
            "category": category,
            "name": name,
            "exit_status": result.exit_status,
            "evidence_label": evidence["label"],
            "engineering_conclusion": result.engineering_conclusion,
        },
        run_id=run_id,
        stage=stage,
        revision=revisions[stage_path],
        outcome=result.outcome,
        findings=tuple(_finding_summary(item, stage_path) for item in findings),
        artifacts=tuple(artifacts),
        next_actions=(
            {
                "operation": "stage.show",
                "arguments": {},
                "reason": "Review the recorded evidence and findings.",
            },
        ),
    )


def _execution_list(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    run_id = _selected_run_id(workspace)
    run_meta, _, _, _ = _load_run(workspace, run_id)
    stage = inputs.get("stage") or run_meta["current_stage"]
    if stage not in {
        "intake",
        "alignment",
        "requirement",
        "design",
        "check",
        "implementation",
        "validation",
        "delivery",
    }:
        raise UseCaseError("invalid_input", "Stage name is invalid.", field="stage")
    ordered_stages = [
        "intake",
        "alignment",
        "requirement",
        "design",
        "check",
        "implementation",
        "validation",
        "delivery",
    ]
    stage_number = 1 + ordered_stages.index(stage)
    stage_path = f"{workspace.config.runs}/{run_id}/{stage_number:02d}-{stage}.md"
    _, state, revision = workspace.load_document(stage_path)
    commands = [
        {
            "category": value.category,
            "name": value.name,
            "command": list(value.command),
            "working_directory": str(value.working_directory),
            "timeout_seconds": value.timeout_seconds,
        }
        for _, value in sorted(workspace.config.commands.items())
    ]
    executions = [item for item in state["evidence"] if item.get("kind") == "automated"]
    return _done(
        context,
        definition,
        "Configured commands and recorded executions listed.",
        data={"commands": commands, "executions": executions[-20:]},
        run_id=run_id,
        stage=stage,
        revision=revision,
    )


HANDLERS: dict[str, Callable[..., OperationResult]] = {
    "execution.run": _execution_run,
    "execution.list": _execution_list,
}


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
