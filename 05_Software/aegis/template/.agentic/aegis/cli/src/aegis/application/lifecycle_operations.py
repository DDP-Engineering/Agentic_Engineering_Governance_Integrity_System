#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    lifecycle_operations.py
@brief   Implement Run abandonment and bounded Adoption lifecycle use cases.
@details Preserves unreadable Run bytes and current-only project knowledge.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from typing import Any

from aegis.application.operation_types import OperationContext, OperationDefinition
from aegis.application.workflow_operations import (
    UseCaseError,
    _artifact,
    _context_bytes,
    _context_path,
    _done,
    _event,
    _identity,
    _load_current,
    _load_run,
    _observe_run_changes,
    _page_offset,
    _require_text,
    _run_ids,
    _run_path,
    _time,
    _workspace,
)
from aegis.domain.results import OperationResult
from aegis.domain.values import RepositoryPath, ValueValidationError
from aegis.ports.workspace import RepositoryMutation, Workspace, WorkspaceError

_ADOPTION_ID = re.compile(r"^ADOPT-[0-9a-f]{32}$")
_ADOPTION_SECTIONS = {
    "scope",
    "observed_implementation",
    "observed_tests",
    "derived_project_artifacts",
    "traceability_established",
    "unresolved_gaps",
    "resume_state",
}


def _run_abandon(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
    pointer_path = _context_path(workspace)
    pointer = workspace.read_optional(pointer_path)
    selected = ""
    if pointer is not None:
        try:
            selected = tomllib.loads(pointer.decode("utf-8"))["selected_run"]
        except (UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as error:
            raise UseCaseError(
                "malformed_state",
                "Selected Run pointer is malformed.",
                path=pointer_path,
            ) from error
    if not selected:
        active = []
        for run_id in _run_ids(workspace):
            try:
                metadata, _, _, _ = _load_run(workspace, run_id)
            except (UseCaseError, WorkspaceError):
                continue
            if metadata.get("status") == "active":
                active.append(run_id)
        if len(active) != 1:
            raise UseCaseError(
                "ambiguous_run",
                "Select exactly one active Run before abandonment.",
                details={"candidates": active[:20]},
            )
        selected = active[0]
    now = _time(context)
    try:
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
        if run_id != selected or run_meta["status"] != "active":
            raise UseCaseError(
                "invalid_transition", "Only the selected active Run can be abandoned."
            )
        if context.machine_mode and inputs.get("expected_revision") is None:
            raise UseCaseError(
                "invalid_input",
                "This machine-mode mutation requires an explicit expected revision.",
                field="expected_revision",
                details={"policy": definition.machine_revision_policy.value},
            )
        stage_state["events"].append(_event(now, actor, "run_abandoned", reason))
        stage_meta["updated_at"] = now
        run_meta.update({"status": "abandoned", "updated_at": now})
        run_state["outcome"] = {
            "workflow": "abandoned",
            "reason": reason,
            "actor": actor,
            "time": now,
        }
        run_state["next_action"] = "None; this Run is terminal."
        run_state["events"].append(_event(now, actor, "run_abandoned", reason))
        _observe_run_changes(workspace, run_state, observed_at=now)
        revisions = workspace.publish(
            (
                RepositoryMutation(
                    stage_path,
                    workspace.render_document(stage_meta, stage_state, kind="stage"),
                ),
                RepositoryMutation(
                    run_path, workspace.render_document(run_meta, run_state, kind="run")
                ),
                RepositoryMutation(pointer_path, _context_bytes(None)),
            ),
            expected_revisions={
                stage_path: stage_revision,
                run_path: inputs.get("expected_revision", run_revision),
                pointer_path: workspace.revision(pointer_path),
            },
        )
        return _done(
            context,
            definition,
            "Run abandoned with reason; existing work and evidence preserved.",
            data={"exceptional": False, "reason": reason},
            run_id=run_id,
            stage=stage_meta["stage"],
            revision=revisions[run_path],
            outcome="abandoned",
        )
    except (WorkspaceError, UseCaseError) as load_error:
        recoverable = load_error.code == "malformed_state" or (
            isinstance(load_error, WorkspaceError) and load_error.code == "not_found"
        )
        if not recoverable:
            raise
        run_id = selected
        run_path = _run_path(workspace, run_id)
        recorded_error = load_error
        unreadable_path = run_path
        last_known_state = "unknown"
        if load_error.path:
            try:
                unreadable_path = str(RepositoryPath(load_error.path))
            except ValueValidationError:
                pass
        run_summary_updated = False
        run_revision = None
        run_mutation = None
        try:
            run_meta, run_state, run_revision, run_path = _load_run(
                workspace, run_id
            )
        except (UseCaseError, WorkspaceError) as run_load_error:
            recorded_error = run_load_error
            if run_load_error.path:
                try:
                    unreadable_path = str(RepositoryPath(run_load_error.path))
                except ValueValidationError:
                    pass
        else:
            if run_meta.get("status") != "active":
                raise UseCaseError(
                    "invalid_transition",
                    "Only the selected active Run can be abandoned.",
                )
            last_known_state = f"active at {run_meta['current_stage']}"
            run_meta.update({"status": "abandoned", "updated_at": now})
            run_state["outcome"] = {
                "workflow": "abandoned",
                "reason": reason,
                "actor": actor,
                "time": now,
            }
            run_state["next_action"] = "None; this Run is terminal."
            run_state["events"].append(
                _event(now, actor, "run_abandoned", reason)
            )
            _observe_run_changes(workspace, run_state, observed_at=now)
            run_mutation = RepositoryMutation(
                run_path,
                workspace.render_document(run_meta, run_state, kind="run"),
            )
            run_summary_updated = True
        exceptional_path = f"{workspace.config.runs}/ABANDON-{run_id}.md"
        metadata = {
            "schema": 1,
            "artifact_type": "abandonment",
            "run_id": run_id,
            "recorded_at": now,
            "actor": actor,
        }
        state = {
            "reason": reason,
            "normal_update_failure": str(recorded_error),
            "last_known_state": last_known_state,
            "unreadable_paths": [unreadable_path],
            "diagnostics": "Original bytes were preserved.",
            "outcome": "abandoned",
        }
        mutations = [
            RepositoryMutation(
                exceptional_path,
                workspace.render_document(metadata, state, kind="abandonment"),
            ),
            RepositoryMutation(pointer_path, _context_bytes(None)),
        ]
        expected_revisions = {
            exceptional_path: None,
            pointer_path: workspace.revision(pointer_path),
        }
        if run_mutation is not None:
            mutations.insert(0, run_mutation)
            expected_revisions[run_path] = inputs.get(
                "expected_revision", run_revision
            )
        revisions = workspace.publish(
            tuple(mutations),
            expected_revisions=expected_revisions,
        )
        return _done(
            context,
            definition,
            "Exceptional abandonment recorded while preserving unreadable state.",
            data={
                "exceptional": True,
                "reason": reason,
                "unreadable_paths": [unreadable_path],
                "run_summary_updated": run_summary_updated,
                "last_known_state": last_known_state,
            },
            run_id=run_id,
            revision=revisions.get(run_path) if run_summary_updated else None,
            outcome="abandoned",
            artifacts=(
                _artifact(
                    exceptional_path,
                    "created",
                    revisions[exceptional_path],
                    kind="abandonment",
                ),
            ),
        )


def _adoption_path(workspace: Workspace, adoption_id: str) -> str:
    if not _ADOPTION_ID.fullmatch(adoption_id):
        raise UseCaseError(
            "invalid_input", "Adoption identity is not canonical.", field="adoption"
        )
    return f"{workspace.config.adoptions}/{adoption_id}.md"


def _load_adoption(
    workspace: Workspace, adoption_id: str
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    path = _adoption_path(workspace, adoption_id)
    metadata, state, revision = workspace.load_document(path)
    if metadata.get("artifact_type") != "adoption" or metadata.get("id") != adoption_id:
        raise UseCaseError(
            "malformed_state", "Adoption identity and path disagree.", path=path
        )
    return metadata, state, revision, path


def _adoption_create(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    scope = _require_text(inputs, "scope")
    actor = _require_text(inputs, "actor")
    for field in ("observed_implementation", "observed_tests", "unresolved_gaps"):
        if not isinstance(inputs.get(field), list):
            raise UseCaseError("invalid_input", f"{field} must be a list.", field=field)
    for _ in range(8):
        adoption_id = _identity(context, "ADOPT")
        path = _adoption_path(workspace, adoption_id)
        if workspace.read_optional(path) is None:
            break
    else:
        raise UseCaseError(
            "state_conflict",
            "A collision-free Adoption identity could not be generated.",
        )
    now = _time(context)
    metadata = {
        "schema": 1,
        "artifact_type": "adoption",
        "id": adoption_id,
        "status": "active",
        "component_id": inputs.get("component_id", ""),
        "opened_at": now,
        "updated_at": now,
        "requirement_ids": [],
    }
    state = {
        "scope": scope,
        "observed_implementation": inputs["observed_implementation"],
        "observed_tests": inputs["observed_tests"],
        "derived_project_artifacts": [],
        "traceability_established": [],
        "unresolved_gaps": inputs["unresolved_gaps"],
        "resume_state": {
            "completed_discovery": [],
            "current_artifacts": [],
            "current_gaps": inputs["unresolved_gaps"],
            "next_action": "Continue bounded observation.",
        },
        "events": [_event(now, actor, "adoption_opened", scope)],
    }
    revisions = workspace.publish(
        (
            RepositoryMutation(
                path, workspace.render_document(metadata, state, kind="adoption")
            ),
        ),
        expected_revisions={path: None},
    )
    return _done(
        context,
        definition,
        "Adoption journal created.",
        data={"id": adoption_id},
        revision=revisions[path],
        outcome="active",
        artifacts=(_artifact(path, "created", revisions[path], kind="adoption"),),
    )


def _adoption_list(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    """@brief List stable bounded Adoption resume summaries without mutation."""
    workspace = _workspace(context)
    root = str(workspace.config.adoptions)
    paths = tuple(
        path
        for path in workspace.list_files(root, suffix=".md")
        if _ADOPTION_ID.fullmatch(path.rsplit("/", 1)[-1].removesuffix(".md"))
    )
    offset = _page_offset(inputs, len(paths))
    items = []
    for path in paths[offset : offset + 20]:
        adoption_id = path.rsplit("/", 1)[-1].removesuffix(".md")
        try:
            metadata, state, revision, _ = _load_adoption(workspace, adoption_id)
        except (UseCaseError, WorkspaceError):
            items.append(
                {
                    "id": adoption_id,
                    "status": "unreadable",
                    "component_id": "",
                    "path": path,
                    "revision": workspace.revision(path),
                    "resume_state": {
                        "completed_discovery_count": 0,
                        "current_artifact_count": 0,
                        "current_gap_count": 0,
                        "next_action": "Repair or restore this Adoption journal.",
                    },
                }
            )
            continue
        resume = state.get("resume_state", {})
        if not isinstance(resume, dict):
            resume = {}

        def item_count(name: str) -> int:
            value = resume.get(name, [])
            return len(value) if isinstance(value, list) else 0

        next_action = resume.get("next_action", "")
        items.append(
            {
                "id": adoption_id,
                "status": metadata.get("status"),
                "component_id": metadata.get("component_id", ""),
                "path": path,
                "revision": revision,
                "resume_state": {
                    "completed_discovery_count": item_count("completed_discovery"),
                    "current_artifact_count": item_count("current_artifacts"),
                    "current_gap_count": item_count("current_gaps"),
                    "next_action": (
                        next_action[:120] if isinstance(next_action, str) else ""
                    ),
                },
            }
        )
    next_offset = offset + 20
    has_more = len(paths) > next_offset
    return _done(
        context,
        definition,
        "Adoption resume summaries listed.",
        data={
            "items": items,
            "has_more": has_more,
            "next_cursor": str(next_offset) if has_more else None,
        },
    )


def _adoption_show(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    metadata, state, revision, path = _load_adoption(
        workspace, _require_text(inputs, "adoption")
    )
    return _done(
        context,
        definition,
        "Adoption resume state loaded.",
        data={"metadata": metadata, "state": state},
        revision=revision,
        outcome=metadata["status"],
        artifacts=(_artifact(path, "read", revision, kind="adoption"),),
    )


def _adoption_set_section(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    adoption_id = _require_text(inputs, "adoption")
    section = _require_text(inputs, "section")
    actor = _require_text(inputs, "actor")
    if section not in _ADOPTION_SECTIONS:
        raise UseCaseError(
            "invalid_input",
            "Adoption section is not allowed.",
            field="section",
            details={"allowed": sorted(_ADOPTION_SECTIONS)},
        )
    if "content" not in inputs:
        raise UseCaseError(
            "invalid_input", "Adoption section content is required.", field="content"
        )
    metadata, state, revision, path = _load_adoption(workspace, adoption_id)
    if metadata["status"] != "active":
        raise UseCaseError(
            "invalid_transition", "Only an active Adoption can be updated."
        )
    now = _time(context)
    state[section] = inputs["content"]
    state["events"].append(_event(now, actor, "adoption_section_replaced", section))
    metadata["updated_at"] = now
    revisions = workspace.publish(
        (
            RepositoryMutation(
                path, workspace.render_document(metadata, state, kind="adoption")
            ),
        ),
        expected_revisions={path: inputs.get("expected_revision", revision)},
    )
    return _done(
        context,
        definition,
        "Adoption section replaced.",
        data={"id": adoption_id, "section": section},
        revision=revisions[path],
        outcome="active",
    )


def _adoption_complete(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    adoption_id = _require_text(inputs, "adoption")
    metadata, state, revision, path = _load_adoption(workspace, adoption_id)
    if metadata["status"] != "active":
        raise UseCaseError(
            "invalid_transition", "Only an active Adoption can complete."
        )
    now = _time(context)
    metadata.update({"status": "completed", "updated_at": now})
    state["events"].append(
        _event(
            now,
            "operator",
            "adoption_completed",
            f"{len(state['unresolved_gaps'])} gaps remain visible.",
        )
    )
    revisions = workspace.publish(
        (
            RepositoryMutation(
                path, workspace.render_document(metadata, state, kind="adoption")
            ),
        ),
        expected_revisions={path: inputs.get("expected_revision", revision)},
    )
    return _done(
        context,
        definition,
        "Adoption completed with remaining gaps visible.",
        data={"id": adoption_id, "remaining_gaps": state["unresolved_gaps"]},
        revision=revisions[path],
        outcome="completed",
    )


def _adoption_abandon(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    adoption_id = _require_text(inputs, "adoption")
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
    metadata, state, revision, path = _load_adoption(workspace, adoption_id)
    if metadata["status"] != "active":
        raise UseCaseError(
            "invalid_transition", "Only an active Adoption can be abandoned."
        )
    now = _time(context)
    metadata.update({"status": "abandoned", "updated_at": now})
    state["events"].append(_event(now, actor, "adoption_abandoned", reason))
    state["abandonment_reason"] = reason
    revisions = workspace.publish(
        (
            RepositoryMutation(
                path, workspace.render_document(metadata, state, kind="adoption")
            ),
        ),
        expected_revisions={path: inputs.get("expected_revision", revision)},
    )
    return _done(
        context,
        definition,
        "Adoption abandoned; observed work and gaps preserved.",
        data={"id": adoption_id, "reason": reason},
        revision=revisions[path],
        outcome="abandoned",
    )


HANDLERS: dict[str, Callable[..., OperationResult]] = {
    "run.abandon": _run_abandon,
    "adoption.create": _adoption_create,
    "adoption.list": _adoption_list,
    "adoption.show": _adoption_show,
    "adoption.set_section": _adoption_set_section,
    "adoption.complete": _adoption_complete,
    "adoption.abandon": _adoption_abandon,
}


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
