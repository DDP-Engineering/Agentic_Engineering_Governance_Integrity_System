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
@file    workflow_operations.py
@brief   Implement configuration, Run, Stage, and embedded-entry use cases.
@details Each registry-bound executor performs one atomic protocol operation.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aegis.application.operation_types import OperationContext, OperationDefinition
from aegis.application.product_operations import unavailable_operation
from aegis.domain.results import OperationResult, ProtocolError
from aegis.ports.workspace import RepositoryMutation, Workspace, WorkspaceError

_STAGES = (
    "intake",
    "alignment",
    "requirement",
    "design",
    "check",
    "implementation",
    "validation",
    "delivery",
)
_STAGE_FILES = {
    stage: f"{index:02d}-{stage}.md" for index, stage in enumerate(_STAGES, start=1)
}
_RUN_ID = re.compile(r"^RUN-[0-9a-f]{32}$")
_DECISIONS = {"approved", "rejected", "exception_approved"}
_DISPOSITIONS = {"open", "resolved", "accepted", "waived", "not_applicable"}


class UseCaseError(ValueError):
    """@brief Describe invalid input or workflow state without adapter leakage."""

    def __init__(
        self,
        code: str,
        summary: str,
        *,
        field: str | None = None,
        path: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.field = field
        self.path = path
        self.retryable = retryable
        self.details = details or {}


def _time(context: OperationContext) -> str:
    return context.clock.now().isoformat().replace("+00:00", "Z")


def _identity(context: OperationContext, prefix: str) -> str:
    return f"{prefix}-{context.uuid_service.new_uuid().replace('-', '').lower()}"


def _workspace(context: OperationContext) -> Workspace:
    if context.workspace is None:
        raise UseCaseError(
            "repository_error", "This operation requires an installed repository."
        )
    return context.workspace


def _done(
    context: OperationContext,
    definition: OperationDefinition,
    message: str,
    *,
    data: dict[str, Any] | None = None,
    run_id: str | None = None,
    stage: str | None = None,
    revision: str | None = None,
    outcome: str | None = None,
    findings: tuple[dict[str, Any], ...] = (),
    artifacts: tuple[dict[str, Any], ...] = (),
    next_actions: tuple[dict[str, Any], ...] = (),
) -> OperationResult:
    return OperationResult(
        product=context.product,
        product_version=context.product_version,
        operation=definition.operation,
        operation_id=context.operation_id,
        operation_status="completed",
        message=message,
        data=data or {},
        run_id=run_id,
        stage=stage,
        revision=revision,
        outcome=outcome,
        findings=findings,
        artifacts=artifacts,
        next_actions=next_actions,
    )


def _error(
    context: OperationContext,
    definition: OperationDefinition,
    error: UseCaseError,
) -> OperationResult:
    return OperationResult(
        product=context.product,
        product_version=context.product_version,
        operation=definition.operation,
        operation_id=context.operation_id,
        operation_status="error",
        message=error.summary,
        error=ProtocolError(
            code=error.code,
            summary=error.summary,
            field=error.field,
            path=error.path,
            retryable=error.retryable,
            details=error.details,
        ),
    )


def _wrap(handler: Callable[..., OperationResult]) -> Callable[..., OperationResult]:
    def execute(
        context: OperationContext,
        definition: OperationDefinition,
        inputs: dict[str, Any],
    ) -> OperationResult:
        try:
            return handler(context, definition, inputs)
        except WorkspaceError as error:
            return _error(
                context,
                definition,
                UseCaseError(error.code, error.summary, path=error.path),
            )
        except UseCaseError as error:
            return _error(context, definition, error)

    execute.__name__ = f"execute_{handler.__name__.removeprefix('_')}"
    return execute


def _require_text(inputs: dict[str, Any], field: str) -> str:
    value = inputs.get(field)
    if not isinstance(value, str) or not value.strip():
        raise UseCaseError(
            "invalid_input", f"{field} must be non-empty text.", field=field
        )
    return value


def _run_path(workspace: Workspace, run_id: str) -> str:
    if not _RUN_ID.fullmatch(run_id):
        raise UseCaseError(
            "invalid_input", "Run identity is not canonical.", field="run"
        )
    return f"{workspace.config.runs}/{run_id}/run.md"


def _context_path(workspace: Workspace) -> str:
    return f"{workspace.config.runs}/context.toml"


def _context_bytes(run_id: str | None) -> bytes:
    selected = "" if run_id is None else run_id
    return (
        f'schema = 1\nartifact_type = "working_context"\nselected_run = "{selected}"\n'
    ).encode()


def _run_ids(workspace: Workspace) -> tuple[str, ...]:
    suffix = "/run.md"
    return tuple(
        path.split("/")[-2]
        for path in workspace.list_files(str(workspace.config.runs), suffix=suffix)
        if path.endswith(suffix) and _RUN_ID.fullmatch(path.split("/")[-2])
    )


def _load_run(
    workspace: Workspace, run_id: str
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    path = _run_path(workspace, run_id)
    metadata, state, revision = workspace.load_document(path)
    if metadata.get("artifact_type") != "run" or metadata.get("id") != run_id:
        raise UseCaseError(
            "malformed_state", "Run identity and path disagree.", path=path
        )
    return metadata, state, revision, path


def _selected_run_id(workspace: Workspace) -> str:
    pointer = workspace.read_optional(_context_path(workspace))
    if pointer is not None:
        try:
            data = tomllib.loads(pointer.decode("utf-8"))
            selected = data.get("selected_run", "")
            if selected:
                _load_run(workspace, selected)
                return selected
        except (UnicodeError, tomllib.TOMLDecodeError, WorkspaceError):
            raise UseCaseError(
                "malformed_state",
                "The selected Run pointer is malformed.",
                path=_context_path(workspace),
            )
    active: list[str] = []
    for run_id in _run_ids(workspace):
        metadata, _, _, _ = _load_run(workspace, run_id)
        if metadata.get("status") == "active":
            active.append(run_id)
    if len(active) == 1:
        return active[0]
    if not active:
        raise UseCaseError("not_found", "No active Run is available.", field="run")
    raise UseCaseError(
        "ambiguous_run",
        "Several active Runs exist; select one explicitly.",
        field="run",
        details={"candidates": active[:20]},
    )


def _load_current(
    workspace: Workspace,
) -> tuple[
    str,
    dict[str, Any],
    dict[str, Any],
    str,
    str,
    dict[str, Any],
    dict[str, Any],
    str,
    str,
]:
    run_id = _selected_run_id(workspace)
    run_meta, run_state, run_revision, run_path = _load_run(workspace, run_id)
    stage = run_meta["current_stage"]
    stage_path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[stage]}"
    stage_meta, stage_state, stage_revision = workspace.load_document(stage_path)
    if stage_meta.get("run_id") != run_id or stage_meta.get("stage") != stage:
        raise UseCaseError(
            "malformed_state",
            "Stage identity and Run pointer disagree.",
            path=stage_path,
        )
    return (
        run_id,
        run_meta,
        run_state,
        run_revision,
        run_path,
        stage_meta,
        stage_state,
        stage_revision,
        stage_path,
    )


def _event(time: str, actor: str, name: str, result: str) -> dict[str, str]:
    return {"time": time, "actor": actor, "event": name, "result": result}


def _artifact(
    path: str, action: str, revision: str | None, *, kind: str
) -> dict[str, Any]:
    return {
        "type": kind,
        "id": None,
        "path": path,
        "action": action,
        "revision": revision,
    }


def _save_stage_run(
    workspace: Workspace,
    *,
    stage_path: str,
    stage_meta: dict[str, Any],
    stage_state: dict[str, Any],
    stage_revision: str,
    run_path: str,
    run_meta: dict[str, Any],
    run_state: dict[str, Any],
    run_revision: str,
    expected_stage: str | None = None,
    extra: tuple[RepositoryMutation, ...] = (),
    extra_expected: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    expected = expected_stage or stage_revision
    expected_revisions = {stage_path: expected, run_path: run_revision}
    expected_revisions.update(extra_expected or {})
    return workspace.publish(
        extra
        + (
            RepositoryMutation(
                stage_path,
                workspace.render_document(stage_meta, stage_state, kind="stage"),
            ),
            RepositoryMutation(
                run_path,
                workspace.render_document(run_meta, run_state, kind="run"),
            ),
        ),
        expected_revisions=expected_revisions,
    )


def _config_show(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    del inputs
    workspace = _workspace(context)
    config = workspace.config
    data = {
        "paths": {
            "requirements": str(config.requirements),
            "components": str(config.components),
            "tests": [str(path) for path in config.test_roots],
            "adoptions": str(config.adoptions),
            "runs": str(config.runs),
        },
        "commands": {
            key: {
                "command": list(value.command),
                "working_directory": str(value.working_directory),
                "timeout_seconds": value.timeout_seconds,
            }
            for key, value in sorted(config.commands.items())
        },
        "policy": {
            "risk_attention_threshold": config.risk_attention_threshold,
            "protected_scope_patterns": list(config.protected_scope_patterns),
        },
    }
    path = ".agentic/config.toml"
    return _done(
        context,
        definition,
        "Project configuration loaded.",
        data=data,
        revision=workspace.revision(path),
        artifacts=(
            _artifact(path, "read", workspace.revision(path), kind="project_config"),
        ),
    )


def _config_validate(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    del inputs
    workspace = _workspace(context)
    findings: list[dict[str, Any]] = []
    configured = (
        str(workspace.config.requirements),
        str(workspace.config.components),
        *(str(path) for path in workspace.config.test_roots),
        str(workspace.config.adoptions),
        str(workspace.config.runs),
    )
    for path in configured:
        if not workspace.path_exists(path, directory=True):
            findings.append(
                {
                    "label": f"F{len(findings) + 1}",
                    "code": "configured_path_missing",
                    "severity": "info",
                    "summary": f"Configured path does not yet exist: {path}",
                    "disposition": "open",
                    "artifact": ".agentic/config.toml",
                }
            )
    return _done(
        context,
        definition,
        "Project configuration validation completed.",
        findings=tuple(findings),
        data={"finding_count": len(findings)},
    )


def _payload_verify(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    del inputs
    findings = _workspace(context).payload_findings()
    return _done(
        context,
        definition,
        "Payload verification completed.",
        findings=findings,
        data={"finding_count": len(findings)},
    )


def _run_create(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    choices = [
        field
        for field in ("ticket_text", "ticket_path")
        if inputs.get(field) is not None
    ]
    if len(choices) != 1:
        raise UseCaseError(
            "invalid_input",
            "Provide exactly one of ticket_text or ticket_path.",
            field="ticket_text",
        )
    ticket = (
        inputs["ticket_text"]
        if choices[0] == "ticket_text"
        else workspace.read_external_text(inputs["ticket_path"])
    )
    if not isinstance(ticket, str) or not ticket.strip():
        raise UseCaseError(
            "invalid_input", "Ticket text must not be empty.", field=choices[0]
        )
    profile = inputs.get("profile", "full")
    work_type = inputs.get("work_type", "change")
    if profile not in {"full", "short"}:
        raise UseCaseError("invalid_input", "Run profile is invalid.", field="profile")
    if work_type not in {"feature", "change", "quick_fix", "bug_fix"}:
        raise UseCaseError(
            "invalid_input", "Run work type is invalid.", field="work_type"
        )
    actor = inputs.get("actor", "operator")
    if not isinstance(actor, str) or not actor.strip():
        raise UseCaseError(
            "invalid_input", "actor must be non-empty text.", field="actor"
        )
    now = _time(context)
    for _ in range(8):
        run_id = _identity(context, "RUN")
        run_path = _run_path(workspace, run_id)
        if workspace.read_optional(run_path) is None:
            break
    else:
        raise UseCaseError(
            "state_conflict", "A collision-free Run identity could not be generated."
        )
    opening = workspace.git_snapshot()
    stages = []
    mutations: list[RepositoryMutation] = []
    run_dir = f"{workspace.config.runs}/{run_id}"
    for index, stage in enumerate(_STAGES, start=1):
        resource = workspace.load_instruction(stage)
        status = "active" if stage == "intake" else "pending"
        if stage == "design" and profile == "short":
            status = "omitted"
        metadata = {
            "schema": 1,
            "artifact_type": "stage",
            "run_id": run_id,
            "stage": stage,
            "sequence": index,
            "status": status,
            "started_at": now if status == "active" else "",
            "updated_at": now,
            "completed_at": "",
            "attachments": [],
        }
        state = {
            "instruction": resource["instruction"],
            "allowed_sections": resource["sections"],
            "sections": {section: "None" for section in resource["sections"]},
            "evidence": [],
            "findings": [],
            "decisions": [],
            "escapes": [],
            "attachments": [],
            "events": (
                [_event(now, actor, "stage_started", "Intake became active.")]
                if stage == "intake"
                else []
            ),
            "work_applied": False,
        }
        stage_path = f"{run_dir}/{_STAGE_FILES[stage]}"
        mutations.append(
            RepositoryMutation(
                stage_path, workspace.render_document(metadata, state, kind="stage")
            )
        )
        stages.append(
            {
                "sequence": index,
                "name": stage,
                "path": _STAGE_FILES[stage],
                "status": status,
                "updated_at": now,
                "result": "",
            }
        )
    run_meta = {
        "schema": 1,
        "artifact_type": "run",
        "id": run_id,
        "status": "active",
        "current_stage": "intake",
        "work_type": work_type,
        "profile": profile,
        "opened_at": now,
        "updated_at": now,
        "opened_branch": opening["branch"],
        "requirement_ids": [],
        "component_ids": [],
    }
    run_state = {
        "ticket_text": ticket,
        "intent": "Pending Intake restatement.",
        "scope": "Pending Alignment.",
        "execution_instruction": inputs.get("execution_instruction", "None"),
        "opening_repository_state": opening,
        "scope_changes": [],
        "stages": stages,
        "next_action": "Complete the Intake restatement.",
        "outcome": "Active",
        "events": [_event(now, actor, "run_opened", "Run created from ticket text.")],
    }
    mutations.extend(
        (
            RepositoryMutation(
                run_path, workspace.render_document(run_meta, run_state, kind="run")
            ),
            RepositoryMutation(_context_path(workspace), _context_bytes(run_id)),
        )
    )
    revisions = workspace.publish(tuple(mutations), expected_revisions={run_path: None})
    return _done(
        context,
        definition,
        "Run created and selected.",
        data={"profile": profile, "work_type": work_type},
        run_id=run_id,
        stage="intake",
        revision=revisions[run_path],
        artifacts=tuple(
            _artifact(
                item.path,
                "created",
                revisions[item.path],
                kind="run" if item.path == run_path else "stage",
            )
            for item in mutations
            if item.path != _context_path(workspace)
        ),
        next_actions=(
            {
                "operation": "stage.show",
                "arguments": {},
                "reason": "Read the Intake instruction and current state.",
            },
        ),
    )


def _run_list(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    del inputs
    workspace = _workspace(context)
    try:
        selected = _selected_run_id(workspace)
    except UseCaseError:
        selected = None
    items = []
    for run_id in _run_ids(workspace)[:20]:
        metadata, state, revision, _ = _load_run(workspace, run_id)
        items.append(
            {
                "id": run_id,
                "status": metadata["status"],
                "profile": metadata["profile"],
                "current_stage": metadata["current_stage"],
                "selected": run_id == selected,
                "revision": revision,
                "ticket_summary": state["ticket_text"][:120],
            }
        )
    has_more = len(_run_ids(workspace)) > 20
    return _done(
        context,
        definition,
        "Run summaries listed.",
        data={
            "items": items,
            "has_more": has_more,
            "next_cursor": "20" if has_more else None,
        },
        run_id=selected,
    )


def _run_select(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    run_id = _require_text(inputs, "run_id")
    metadata, _, revision, _ = _load_run(workspace, run_id)
    if metadata["status"] != "active":
        raise UseCaseError(
            "invalid_transition", "Only an active Run can be selected.", field="run_id"
        )
    pointer = _context_path(workspace)
    revisions = workspace.publish(
        (RepositoryMutation(pointer, _context_bytes(run_id)),),
        expected_revisions={pointer: workspace.revision(pointer)},
    )
    return _done(
        context,
        definition,
        "Run selected.",
        data={"selected_run": run_id},
        run_id=run_id,
        stage=metadata["current_stage"],
        revision=revision,
        artifacts=(
            _artifact(pointer, "updated", revisions[pointer], kind="working_context"),
        ),
    )


def _run_show(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    run_id = inputs.get("run") or _selected_run_id(workspace)
    metadata, state, revision, path = _load_run(workspace, run_id)
    return _done(
        context,
        definition,
        "Run state loaded.",
        data={"metadata": metadata, "state": state},
        run_id=run_id,
        stage=metadata["current_stage"],
        revision=revision,
        artifacts=(_artifact(path, "read", revision, kind="run"),),
    )


def _run_set_profile(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    profile = inputs.get("profile")
    if profile not in {"full", "short"}:
        raise UseCaseError("invalid_input", "Run profile is invalid.", field="profile")
    run_id, run_meta, run_state, run_revision, run_path, _, _, _, _ = _load_current(
        workspace
    )
    if run_meta["status"] != "active":
        raise UseCaseError(
            "invalid_transition", "A terminal Run cannot change profile."
        )
    design_path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES['design']}"
    design_meta, design_state, design_revision = workspace.load_document(design_path)
    if profile == "short" and design_meta["status"] not in {"pending", "omitted"}:
        raise UseCaseError(
            "invalid_transition", "Design work already exists and cannot be omitted."
        )
    now = _time(context)
    design_meta["status"] = "omitted" if profile == "short" else "pending"
    design_meta["updated_at"] = now
    design_state["events"].append(
        _event(
            now, "operator", "profile_changed", f"Design is {design_meta['status']}."
        )
    )
    run_meta["profile"] = profile
    run_meta["updated_at"] = now
    for summary in run_state["stages"]:
        if summary["name"] == "design":
            summary["status"] = design_meta["status"]
            summary["updated_at"] = now
    revisions = workspace.publish(
        (
            RepositoryMutation(
                design_path,
                workspace.render_document(design_meta, design_state, kind="stage"),
            ),
            RepositoryMutation(
                run_path, workspace.render_document(run_meta, run_state, kind="run")
            ),
        ),
        expected_revisions={
            design_path: design_revision,
            run_path: inputs.get("expected_revision", run_revision),
        },
    )
    return _done(
        context,
        definition,
        "Run profile updated.",
        data={"profile": profile},
        run_id=run_id,
        stage=run_meta["current_stage"],
        revision=revisions[run_path],
    )


def _stage_show(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    run_id = inputs.get("run") or _selected_run_id(workspace)
    run_meta, _, _, _ = _load_run(workspace, run_id)
    stage = inputs.get("stage") or run_meta["current_stage"]
    if stage not in _STAGES:
        raise UseCaseError("invalid_input", "Stage name is invalid.", field="stage")
    path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[stage]}"
    metadata, state, revision = workspace.load_document(path)
    return _done(
        context,
        definition,
        f"{stage.title()} Stage loaded.",
        data={
            "status": metadata["status"],
            "instruction": state["instruction"],
            "sections": state["sections"],
            "evidence": state["evidence"],
            "findings": state["findings"],
            "decisions": state["decisions"],
            "escapes": state["escapes"],
        },
        run_id=run_id,
        stage=stage,
        revision=revision,
        artifacts=(_artifact(path, "read", revision, kind="stage"),),
    )


def _stage_start(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    requested = inputs.get("stage_name")
    if requested not in _STAGES:
        raise UseCaseError(
            "invalid_input", "Stage name is invalid.", field="stage_name"
        )
    run_id, run_meta, run_state, run_revision, run_path, _, _, _, _ = _load_current(
        workspace
    )
    stage_path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[requested]}"
    stage_meta, stage_state, stage_revision = workspace.load_document(stage_path)
    if stage_meta["status"] != "pending":
        raise UseCaseError(
            "invalid_transition",
            "Only a pending included Stage can start.",
            field="stage_name",
        )
    requested_index = _STAGES.index(requested)
    earlier = {summary["name"]: summary["status"] for summary in run_state["stages"]}
    if any(
        earlier[name] not in {"completed", "skipped", "omitted"}
        for name in _STAGES[:requested_index]
    ):
        raise UseCaseError(
            "invalid_transition",
            "Earlier included Stage work is not complete.",
            field="stage_name",
        )
    now = _time(context)
    stage_meta.update(
        {
            "status": "active",
            "started_at": stage_meta["started_at"] or now,
            "updated_at": now,
        }
    )
    stage_state["events"].append(
        _event(now, "operator", "stage_started", f"{requested} became active.")
    )
    if requested == "check":
        stage_state["git_baseline"] = workspace.git_snapshot()
    if requested == "delivery":
        prior_findings = []
        prior_evidence = []
        for summary in run_state["stages"][:-1]:
            prior_path = f"{workspace.config.runs}/{run_id}/{summary['path']}"
            _, prior_state, _ = workspace.load_document(prior_path)
            prior_findings.extend(
                {"stage": summary["name"], **finding}
                for finding in prior_state.get("findings", [])
            )
            prior_evidence.extend(
                {"stage": summary["name"], **evidence}
                for evidence in prior_state.get("evidence", [])
            )
        stage_state["sections"]["requested_and_delivered_outcome"] = (
            f"Requested: {run_state['ticket_text']}\nDelivered assessment: pending."
        )
        stage_state["sections"]["evidence_summary"] = str(prior_evidence)
        stage_state["sections"]["findings_and_residual_risk"] = str(prior_findings)
        stage_state["sections"]["skips_waivers_and_omitted_stages"] = str(
            [
                {"stage": item["name"], "status": item["status"]}
                for item in run_state["stages"]
                if item["status"] in {"skipped", "omitted"}
            ]
        )
    run_meta.update({"current_stage": requested, "updated_at": now})
    for summary in run_state["stages"]:
        if summary["name"] == requested:
            summary.update({"status": "active", "updated_at": now})
    run_state["next_action"] = f"Complete the {requested} Stage instruction."
    revisions = workspace.publish(
        (
            RepositoryMutation(
                stage_path,
                workspace.render_document(stage_meta, stage_state, kind="stage"),
            ),
            RepositoryMutation(
                run_path, workspace.render_document(run_meta, run_state, kind="run")
            ),
        ),
        expected_revisions={stage_path: stage_revision, run_path: run_revision},
    )
    return _done(
        context,
        definition,
        f"{requested.title()} Stage started.",
        data={"status": "active"},
        run_id=run_id,
        stage=requested,
        revision=revisions[stage_path],
    )


def _stage_set_section(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    section = _require_text(inputs, "section")
    content = _require_text(inputs, "content")
    actor = _require_text(inputs, "actor") if "actor" in inputs else "operator"
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
    if stage_meta["status"] != "active":
        raise UseCaseError("invalid_transition", "The current Stage is not active.")
    if section not in stage_state["allowed_sections"]:
        raise UseCaseError(
            "invalid_input",
            "Section is not allowed for this Stage.",
            field="section",
            details={"allowed": stage_state["allowed_sections"]},
        )
    now = _time(context)
    stage_state["sections"][section] = content
    stage_state["events"].append(_event(now, actor, "section_replaced", section))
    stage_meta["updated_at"] = now
    run_meta["updated_at"] = now
    run_state["next_action"] = f"Continue {stage_meta['stage']} work."
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
        expected_stage=inputs.get("expected_revision"),
    )
    return _done(
        context,
        definition,
        "Stage section replaced.",
        data={"section": section},
        run_id=run_id,
        stage=stage_meta["stage"],
        revision=revisions[stage_path],
    )


def _stage_complete(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
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
    if stage_meta["status"] != "active":
        raise UseCaseError("invalid_transition", "Only an active Stage can complete.")
    stage = stage_meta["stage"]
    if stage == "delivery" and not any(
        item["value"] == "approved" and item["target"] == "delivery"
        for item in stage_state["decisions"]
    ):
        raise UseCaseError(
            "invalid_transition", "Delivery requires a recorded approval decision."
        )
    if stage == "delivery" and stage_state["sections"].get("terminal_result") not in {
        "achieved",
        "partially_achieved",
        "not_achieved",
    }:
        raise UseCaseError(
            "invalid_transition",
            (
                "Delivery requires achieved, partially_achieved, or "
                "not_achieved assessment."
            ),
        )
    now = _time(context)
    completion_findings: list[dict[str, Any]] = []
    if stage == "check" and stage_state.get("git_baseline"):
        baseline = stage_state["git_baseline"]
        current = workspace.git_snapshot()
        before_files = baseline.get("working_files", {})
        after_files = current.get("working_files", {})
        changed_paths = sorted(
            path
            for path in set(before_files) | set(after_files)
            if before_files.get(path) != after_files.get(path)
            and not any(
                path == str(root) or path.startswith(f"{root}/")
                for root in workspace.config.test_roots
            )
            and not path.startswith(".agentic/runs/")
            and not path.startswith(".agentic/.runtime/")
        )
        for changed_path in changed_paths:
            finding = {
                "label": (
                    f"F{len(stage_state['findings']) + len(completion_findings) + 1}"
                ),
                "code": "check_out_of_zone_change",
                "severity": "warning",
                "observation": (
                    f"Implementation path changed during Check: {changed_path}"
                ),
                "consequence": "The change requires developer review and attribution.",
                "disposition": "open",
                "time": now,
                "artifact": changed_path,
            }
            completion_findings.append(finding)
        if baseline.get("head") != current.get("head") or baseline.get(
            "entries"
        ) != current.get("entries"):
            finding_number = len(stage_state["findings"]) + len(completion_findings) + 1
            completion_findings.append(
                {
                    "label": f"F{finding_number}",
                    "code": "check_git_state_changed",
                    "severity": "warning",
                    "observation": (
                        "HEAD, index, or working-tree state changed during Check."
                    ),
                    "consequence": "The original comparison point may require review.",
                    "disposition": "open",
                    "time": now,
                    "artifact": stage_path,
                }
            )
        stage_state["git_completion"] = current
        stage_state["findings"].extend(completion_findings)
    stage_meta.update({"status": "completed", "updated_at": now, "completed_at": now})
    stage_state["events"].append(
        _event(now, "operator", "stage_completed", "Actual Stage state recorded.")
    )
    run_meta["updated_at"] = now
    for summary in run_state["stages"]:
        if summary["name"] == stage:
            summary.update(
                {"status": "completed", "updated_at": now, "result": "Recorded"}
            )
    extra: tuple[RepositoryMutation, ...] = ()
    if stage == "delivery":
        run_meta["status"] = "delivered"
        run_state["outcome"] = {
            "workflow": "delivered",
            "assessment": stage_state["sections"]["terminal_result"],
        }
        run_state["next_action"] = "Developer-owned Git action, if any."
        extra = (RepositoryMutation(_context_path(workspace), _context_bytes(None)),)
    else:
        run_state["next_action"] = "Start the next included Stage."
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
        expected_stage=inputs.get("expected_revision"),
        extra=extra,
    )
    finding_summaries = tuple(
        {
            "label": item["label"],
            "code": item["code"],
            "severity": item["severity"],
            "summary": item["observation"],
            "disposition": item["disposition"],
            "artifact": item["artifact"],
        }
        for item in completion_findings
    )
    return _done(
        context,
        definition,
        f"{stage.title()} Stage completed.",
        data={"status": "completed"},
        run_id=run_id,
        stage=stage,
        revision=revisions[stage_path],
        outcome="delivered" if stage == "delivery" else None,
        findings=finding_summaries,
    )


def _stage_skip(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
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
    if (
        stage
        not in {
            "alignment",
            "requirement",
            "design",
            "check",
            "implementation",
            "validation",
        }
        or stage_meta["status"] not in {"pending", "active"}
        or stage_state.get("work_applied")
    ):
        raise UseCaseError(
            "invalid_transition", "The current Stage cannot be skipped truthfully."
        )
    now = _time(context)
    escape = {
        "time": now,
        "type": "skip",
        "target": stage,
        "actor": actor,
        "reason": reason,
        "effect": "skipped",
    }
    stage_state["escapes"].append(escape)
    stage_state["events"].append(_event(now, actor, "stage_skipped", reason))
    stage_meta.update({"status": "skipped", "updated_at": now, "completed_at": now})
    run_meta["updated_at"] = now
    for summary in run_state["stages"]:
        if summary["name"] == stage:
            summary.update({"status": "skipped", "updated_at": now, "result": reason})
    run_state["next_action"] = "Start the next included Stage."
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
        expected_stage=inputs.get("expected_revision"),
    )
    return _done(
        context,
        definition,
        f"{stage.title()} Stage skipped with reason.",
        data={"status": "skipped", "reason": reason},
        run_id=run_id,
        stage=stage,
        revision=revisions[stage_path],
        outcome="skipped",
    )


def _stage_revisit(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    stage = inputs.get("stage_name")
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
    run_id = _selected_run_id(workspace)
    run_meta, run_state, run_revision, run_path = _load_run(workspace, run_id)
    stage_path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES.get(stage, '')}"
    if stage not in _STAGES:
        raise UseCaseError(
            "invalid_input", "Stage name is invalid.", field="stage_name"
        )
    stage_meta, stage_state, stage_revision = workspace.load_document(stage_path)
    if stage_meta["status"] not in {"completed", "skipped"}:
        raise UseCaseError(
            "invalid_transition",
            "Only completed or skipped Stage work can be revisited.",
        )
    now = _time(context)
    stage_meta.update({"status": "active", "updated_at": now, "completed_at": ""})
    stage_state["events"].append(_event(now, actor, "stage_revisited", reason))
    run_meta.update({"current_stage": stage, "updated_at": now})
    for summary in run_state["stages"]:
        if summary["name"] == stage:
            summary.update({"status": "active", "updated_at": now, "result": reason})
    run_state["next_action"] = f"Revisit {stage}: {reason}"
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
        expected_stage=inputs.get("expected_revision"),
    )
    return _done(
        context,
        definition,
        f"{stage.title()} Stage revisited.",
        data={"status": "active", "reason": reason},
        run_id=run_id,
        stage=stage,
        revision=revisions[stage_path],
    )


def _append_entry(
    context: OperationContext,
    definition: OperationDefinition,
    inputs: dict[str, Any],
    *,
    kind: str,
) -> OperationResult:
    workspace = _workspace(context)
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
    if stage_meta["status"] != "active":
        raise UseCaseError(
            "invalid_transition", "Entries require an active current Stage."
        )
    now = _time(context)
    entry = dict(inputs)
    entry.pop("expected_revision", None)
    if kind == "evidence":
        evidence_kind = entry.get("kind")
        if evidence_kind not in {"manual", "automated", "imported"}:
            raise UseCaseError(
                "invalid_input", "Evidence kind is invalid.", field="kind"
            )
        if evidence_kind == "manual":
            for field in ("actor", "procedure", "expected", "actual"):
                _require_text(entry, field)
        entry["label"] = f"E{len(stage_state['evidence']) + 1}"
    elif kind == "finding":
        for field in ("severity", "observation", "consequence"):
            _require_text(entry, field)
        entry.update(
            {"label": f"F{len(stage_state['findings']) + 1}", "disposition": "open"}
        )
    elif kind == "decision":
        value = entry.get("value")
        if value not in _DECISIONS:
            raise UseCaseError(
                "invalid_input", "Decision value is invalid.", field="value"
            )
        for field in ("actor", "target", "reason"):
            _require_text(entry, field)
        if value == "exception_approved" and not entry.get("alternative_confirmation"):
            raise UseCaseError(
                "invalid_input",
                "Approved exceptions require alternative confirmation.",
                field="alternative_confirmation",
            )
    entry["time"] = now
    collection = {
        "evidence": "evidence",
        "finding": "findings",
        "decision": "decisions",
    }[kind]
    stage_state[collection].append(entry)
    stage_state["events"].append(
        _event(
            now,
            entry.get("actor", "operator"),
            f"{kind}_added",
            entry.get("label", entry.get("target", kind)),
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
        expected_stage=inputs.get("expected_revision"),
    )
    return _done(
        context,
        definition,
        f"Stage {kind} appended.",
        data={"entry": entry},
        run_id=run_id,
        stage=stage_meta["stage"],
        revision=revisions[stage_path],
    )


def _evidence_add(
    c: OperationContext, d: OperationDefinition, i: dict[str, Any]
) -> OperationResult:
    return _append_entry(c, d, i, kind="evidence")


def _finding_add(
    c: OperationContext, d: OperationDefinition, i: dict[str, Any]
) -> OperationResult:
    return _append_entry(c, d, i, kind="finding")


def _decision_add(
    c: OperationContext, d: OperationDefinition, i: dict[str, Any]
) -> OperationResult:
    return _append_entry(c, d, i, kind="decision")


def _finding_disposition(
    context: OperationContext,
    definition: OperationDefinition,
    inputs: dict[str, Any],
    *,
    waive: bool,
) -> OperationResult:
    workspace = _workspace(context)
    label = _require_text(inputs, "finding")
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
    disposition = "waived" if waive else inputs.get("disposition")
    if disposition not in _DISPOSITIONS:
        raise UseCaseError(
            "invalid_input", "Finding disposition is invalid.", field="disposition"
        )
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
    finding = next(
        (item for item in stage_state["findings"] if item["label"] == label), None
    )
    if finding is None:
        raise UseCaseError(
            "not_found", "Finding label does not exist.", field="finding"
        )
    now = _time(context)
    finding["disposition"] = disposition
    finding.setdefault("disposition_history", []).append(
        {"time": now, "actor": actor, "reason": reason, "disposition": disposition}
    )
    if waive:
        stage_state["escapes"].append(
            {
                "time": now,
                "type": "waiver",
                "target": label,
                "actor": actor,
                "reason": reason,
                "effect": "waived",
            }
        )
    stage_state["events"].append(
        _event(now, actor, "finding_disposition_set", f"{label} -> {disposition}")
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
        expected_stage=inputs.get("expected_revision"),
    )
    return _done(
        context,
        definition,
        "Finding disposition recorded.",
        data={"finding": label, "disposition": disposition},
        run_id=run_id,
        stage=stage_meta["stage"],
        revision=revisions[stage_path],
        outcome=disposition,
    )


def _finding_set_disposition(
    c: OperationContext, d: OperationDefinition, i: dict[str, Any]
) -> OperationResult:
    return _finding_disposition(c, d, i, waive=False)


def _finding_waive(
    c: OperationContext, d: OperationDefinition, i: dict[str, Any]
) -> OperationResult:
    return _finding_disposition(c, d, i, waive=True)


def _attachment_add(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    source = _require_text(inputs, "source")
    purpose = _require_text(inputs, "purpose")
    content_type = _require_text(inputs, "content_type")
    content = workspace.read_external_bytes(source)
    suffix = Path(source).suffix.lower()
    if not suffix or not re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
        suffix = ".bin"
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
    attachment_id = _identity(context, "ATTACH")
    path = f"{workspace.config.runs}/{run_id}/{attachment_id}{suffix}"
    digest = context.hash_service.digest(content)
    now = _time(context)
    entry = {
        "id": attachment_id,
        "path": path,
        "content_type": content_type,
        "size": len(content),
        "sha256": digest,
        "purpose": purpose,
        "stage": stage_meta["stage"],
        "time": now,
    }
    stage_state["attachments"].append(entry)
    stage_state["events"].append(_event(now, "operator", "attachment_added", path))
    stage_meta["attachments"].append(path)
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
        expected_stage=inputs.get("expected_revision"),
        extra=(RepositoryMutation(path, content),),
    )
    return _done(
        context,
        definition,
        "Attachment imported and recorded.",
        data={"attachment": entry},
        run_id=run_id,
        stage=stage_meta["stage"],
        revision=revisions[stage_path],
        artifacts=(_artifact(path, "created", revisions[path], kind="attachment"),),
    )


def _scope_revise(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    before = _require_text(inputs, "before")
    after = _require_text(inputs, "after")
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
    affected = inputs.get("affected_work")
    if not isinstance(affected, list) or not all(
        isinstance(item, str) and item for item in affected
    ):
        raise UseCaseError(
            "invalid_input",
            "affected_work must be a list of names.",
            field="affected_work",
        )
    run_id = _selected_run_id(workspace)
    run_meta, run_state, run_revision, run_path = _load_run(workspace, run_id)
    now = _time(context)
    change = {
        "time": now,
        "before": before,
        "after": after,
        "actor": actor,
        "reason": reason,
        "affected_work": affected,
    }
    run_state["scope_changes"].append(change)
    run_state["scope"] = after
    run_state["events"].append(_event(now, actor, "scope_revised", reason))
    run_meta["updated_at"] = now
    revisions = workspace.publish(
        (
            RepositoryMutation(
                run_path, workspace.render_document(run_meta, run_state, kind="run")
            ),
        ),
        expected_revisions={run_path: inputs.get("expected_revision", run_revision)},
    )
    return _done(
        context,
        definition,
        "Run scope revised; affected work recorded.",
        data=change,
        run_id=run_id,
        stage=run_meta["current_stage"],
        revision=revisions[run_path],
    )


_HANDLERS: dict[str, Callable[..., OperationResult]] = {
    "config.show": _config_show,
    "config.validate": _config_validate,
    "payload.verify": _payload_verify,
    "run.create": _run_create,
    "run.select": _run_select,
    "run.list": _run_list,
    "run.show": _run_show,
    "run.set_profile": _run_set_profile,
    "scope.revise": _scope_revise,
    "stage.show": _stage_show,
    "stage.start": _stage_start,
    "stage.set_section": _stage_set_section,
    "stage.complete": _stage_complete,
    "stage.skip": _stage_skip,
    "stage.revisit": _stage_revisit,
    "evidence.add": _evidence_add,
    "finding.add": _finding_add,
    "finding.set_disposition": _finding_set_disposition,
    "finding.waive": _finding_waive,
    "decision.add": _decision_add,
    "attachment.add": _attachment_add,
}


def executor_for(operation: str) -> Callable[..., OperationResult]:
    """@brief Return one operation-specific wrapped executor or unavailable seam."""
    handler = _HANDLERS.get(operation)
    if handler is None:
        from aegis.application.project_operations import HANDLERS as project_handlers

        handler = project_handlers.get(operation)
    if handler is None:
        from aegis.application.execution_operations import (
            HANDLERS as execution_handlers,
        )

        handler = execution_handlers.get(operation)
    if handler is None:
        from aegis.application.lifecycle_operations import (
            HANDLERS as lifecycle_handlers,
        )

        handler = lifecycle_handlers.get(operation)
    return unavailable_operation if handler is None else _wrap(handler)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
