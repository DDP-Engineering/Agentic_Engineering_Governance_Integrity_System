#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    project_operations.py
@brief   Implement current project knowledge and computed trace use cases.
@details Replaces or deletes obsolete project knowledge while Run evidence stays.
"""

from __future__ import annotations

import re
from collections import defaultdict
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
    _page_offset,
    _require_active_stage,
    _require_text,
    _save_stage_run,
    _time,
    _workspace,
)
from aegis.domain.results import OperationResult
from aegis.ports.workspace import RepositoryMutation, Workspace, WorkspaceError

_REQ_ID = re.compile(r"^REQ-[0-9a-f]{32}$")
_COMP_ID = re.compile(r"^COMP-[0-9a-f]{32}$")
_PURPOSES = {"happy_path", "boundary", "edge", "negative", "failure_path"}


def _path(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or value.startswith("/")
        or re.match(r"^[A-Za-z]:", value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise UseCaseError(
            "invalid_input", f"{field} contains an unsafe repository path.", field=field
        )
    return value


def _requirement_path(workspace: Workspace, requirement_id: str) -> str:
    if not _REQ_ID.fullmatch(requirement_id):
        raise UseCaseError(
            "invalid_input",
            "Requirement identity is not canonical.",
            field="requirement",
        )
    return f"{workspace.config.requirements}/{requirement_id}.toml"


def _specification_path(workspace: Workspace, requirement_id: str) -> str:
    return f"{workspace.config.requirements}/SPEC-{requirement_id[4:]}.md"


def _component_path(workspace: Workspace, component_id: str) -> str:
    if not _COMP_ID.fullmatch(component_id):
        raise UseCaseError(
            "invalid_input", "Component identity is not canonical.", field="component"
        )
    return f"{workspace.config.components}/{component_id}.md"


def _validate_requirement_input(
    inputs: dict[str, Any], *, requirement_id: str, now: str, specification: str = ""
) -> dict[str, Any]:
    if any(
        key in inputs for key in ("ticket", "ticket_id", "run", "run_id", "provenance")
    ):
        raise UseCaseError(
            "invalid_input",
            "Project Requirements cannot contain ticket or Run provenance.",
        )
    title = _require_text(inputs, "title")
    behavior = _require_text(inputs, "behavior")
    confirmation = _require_text(inputs, "confirmation")
    status = inputs.get("status")
    priority = inputs.get("priority")
    verification = inputs.get("verification_kind")
    if status not in {"draft", "active"}:
        raise UseCaseError(
            "invalid_input", "Requirement status is invalid.", field="status"
        )
    if priority not in {"Must", "Should", "Could"}:
        raise UseCaseError(
            "invalid_input", "Requirement priority is invalid.", field="priority"
        )
    if verification not in {"automated", "manual"}:
        raise UseCaseError(
            "invalid_input", "verification_kind is invalid.", field="verification_kind"
        )
    impacted = inputs.get("impacted_files")
    if not isinstance(impacted, list) or not impacted:
        raise UseCaseError(
            "invalid_input",
            "impacted_files must be a non-empty list.",
            field="impacted_files",
        )
    impacted_files = [_path(value, "impacted_files") for value in impacted]
    tests = inputs.get("tests", [])
    if not isinstance(tests, list):
        raise UseCaseError("invalid_input", "tests must be a list.", field="tests")
    normalized_tests = []
    for test in tests:
        if not isinstance(test, dict):
            raise UseCaseError(
                "invalid_input", "Each test link must be an object.", field="tests"
            )
        purposes = test.get("purposes")
        covered = test.get("covered_files")
        if (
            not isinstance(purposes, list)
            or not purposes
            or not set(purposes) <= _PURPOSES
            or not isinstance(covered, list)
            or not covered
        ):
            raise UseCaseError(
                "invalid_input",
                "Test purposes or covered files are invalid.",
                field="tests",
            )
        normalized_tests.append(
            {
                "path": _path(test.get("path"), "tests.path"),
                "selector": test.get("selector", ""),
                "purposes": purposes,
                "covered_files": [
                    _path(value, "tests.covered_files") for value in covered
                ],
            }
        )
    manual_method = inputs.get("manual_method", "")
    if verification == "automated" and (
        not normalized_tests
        or not any("happy_path" in test["purposes"] for test in normalized_tests)
    ):
        raise UseCaseError(
            "invalid_input",
            "Automated Requirements need a happy-path real test link.",
            field="tests",
        )
    if verification == "manual" and (
        not isinstance(manual_method, str) or not manual_method.strip()
    ):
        raise UseCaseError(
            "invalid_input",
            "Manual Requirements need a concrete manual_method.",
            field="manual_method",
        )
    return {
        "schema": 1,
        "artifact_type": "requirement",
        "id": requirement_id,
        "title": title,
        "status": status,
        "priority": priority,
        "behavior": behavior,
        "confirmation": confirmation,
        "verification_kind": verification,
        "manual_method": manual_method,
        "impacted_files": impacted_files,
        "specification": specification,
        "rationale": inputs.get("rationale", ""),
        "updated_at": now,
        "tests": normalized_tests,
    }


def _record_project_change(
    context: OperationContext,
    workspace: Workspace,
    *,
    action: str,
    target: str,
    mutations: tuple[RepositoryMutation, ...],
    expected: dict[str, str | None],
) -> tuple[dict[str, str | None], str, str, str]:
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
    _require_active_stage(stage_meta)
    now = _time(context)
    stage_state["events"].append(_event(now, "operator", action, target))
    stage_state["work_applied"] = True
    stage_meta["updated_at"] = now
    run_meta["updated_at"] = now
    if action.startswith("requirement_"):
        linked = run_meta.setdefault("requirement_ids", [])
        if action == "requirement_deleted":
            run_meta["requirement_ids"] = [item for item in linked if item != target]
        elif target not in linked:
            linked.append(target)
    elif action.startswith("component_"):
        linked = run_meta.setdefault("component_ids", [])
        if action == "component_deleted":
            run_meta["component_ids"] = [item for item in linked if item != target]
        elif target not in linked:
            linked.append(target)
    elif action == "specification_set":
        specification_name = target.rsplit("/", 1)[-1]
        requirement_id = "REQ-" + specification_name.removeprefix("SPEC-").removesuffix(
            ".md"
        )
        linked = run_meta.setdefault("requirement_ids", [])
        if requirement_id not in linked:
            linked.append(requirement_id)
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
        extra=mutations,
        extra_expected=expected,
    )
    return revisions, run_id, stage_meta["stage"], stage_path


def _requirement_create(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    for _ in range(8):
        requirement_id = _identity(context, "REQ")
        path = _requirement_path(workspace, requirement_id)
        if workspace.read_optional(path) is None:
            break
    else:
        raise UseCaseError(
            "state_conflict",
            "A collision-free Requirement identity could not be generated.",
        )
    data = _validate_requirement_input(
        inputs, requirement_id=requirement_id, now=_time(context)
    )
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="requirement_created",
        target=requirement_id,
        mutations=(RepositoryMutation(path, workspace.render_requirement(data)),),
        expected={path: None},
    )
    return _done(
        context,
        definition,
        "Requirement created and recorded in the Run.",
        data={"id": requirement_id},
        run_id=run_id,
        stage=stage,
        revision=revisions[path],
        artifacts=(_artifact(path, "created", revisions[path], kind="requirement"),),
    )


def _load_requirement(
    workspace: Workspace, requirement_id: str
) -> tuple[dict[str, Any], str, str]:
    path = _requirement_path(workspace, requirement_id)
    data, revision = workspace.load_toml(path)
    if (
        data.get("schema") != 1
        or data.get("artifact_type") != "requirement"
        or data.get("id") != requirement_id
    ):
        raise UseCaseError(
            "malformed_state", "Requirement identity and schema disagree.", path=path
        )
    return data, revision, path


def _requirement_update(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    requirement_id = _require_text(inputs, "requirement")
    current, revision, path = _load_requirement(workspace, requirement_id)
    data = _validate_requirement_input(
        inputs,
        requirement_id=requirement_id,
        now=_time(context),
        specification=current.get("specification", ""),
    )
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="requirement_updated",
        target=requirement_id,
        mutations=(RepositoryMutation(path, workspace.render_requirement(data)),),
        expected={path: inputs.get("expected_revision", revision)},
    )
    return _done(
        context,
        definition,
        "Requirement current content replaced.",
        data={"id": requirement_id},
        run_id=run_id,
        stage=stage,
        revision=revisions[path],
        artifacts=(_artifact(path, "updated", revisions[path], kind="requirement"),),
    )


def _requirement_show(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    requirement_id = _require_text(inputs, "requirement")
    data, revision, path = _load_requirement(workspace, requirement_id)
    return _done(
        context,
        definition,
        "Requirement loaded.",
        data=data,
        revision=revision,
        artifacts=(_artifact(path, "read", revision, kind="requirement"),),
    )


def _requirement_list(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    paths = [
        path
        for path in workspace.list_files(
            str(workspace.config.requirements), suffix=".toml"
        )
        if "/REQ-" in path
    ]
    offset = _page_offset(inputs, len(paths))
    items = []
    for path in paths[offset : offset + 20]:
        data, revision = workspace.load_toml(path)
        items.append(
            {
                "id": data.get("id"),
                "title": data.get("title"),
                "status": data.get("status"),
                "priority": data.get("priority"),
                "revision": revision,
            }
        )
    return _done(
        context,
        definition,
        "Requirement summaries listed.",
        data={
            "items": items,
            "has_more": len(paths) > offset + 20,
            "next_cursor": (
                str(offset + 20) if len(paths) > offset + 20 else None
            ),
        },
    )


def _test_in_roots(workspace: Workspace, path: str) -> bool:
    return any(
        path == str(root) or path.startswith(f"{root}/")
        for root in workspace.config.test_roots
    )


def _test_link_problem(workspace: Workspace, path: Any, selector: Any) -> str | None:
    """@brief Explain why one linked test cannot be selected safely."""
    try:
        canonical = _path(path, "tests.path")
    except UseCaseError:
        return f"Linked test path is unsafe: {path!r}."
    if not _test_in_roots(workspace, canonical):
        return f"Linked test is outside configured test roots: {canonical}."
    try:
        if workspace.read_optional(canonical) is None:
            return f"Linked test does not exist: {canonical}."
    except WorkspaceError:
        return f"Linked test path is unsafe or unreadable: {canonical}."
    if (
        not isinstance(selector, str)
        or selector != selector.strip()
        or selector.startswith("-")
        or any(ord(character) < 32 or ord(character) == 127 for character in selector)
    ):
        return f"Linked test has an unsafe selector: {selector!r}."
    return None


def _requirement_findings(
    workspace: Workspace, data: dict[str, Any], path: str
) -> list[dict[str, Any]]:
    findings = []

    def add(code: str, summary: str) -> None:
        findings.append(
            {
                "label": f"F{len(findings) + 1}",
                "code": code,
                "severity": "warning",
                "summary": summary,
                "disposition": "open",
                "artifact": path,
            }
        )

    if data.get("verification_kind") == "automated" and not any(
        "happy_path" in test.get("purposes", []) for test in data.get("tests", [])
    ):
        add("missing_happy_path", "Automated Requirement has no happy-path test.")
    if (
        data.get("verification_kind") == "manual"
        and not str(data.get("manual_method", "")).strip()
    ):
        add("missing_manual_method", "Manual Requirement has no concrete method.")
    for impacted in data.get("impacted_files", []):
        if workspace.read_optional(impacted) is None:
            add("missing_impacted_file", f"Impacted file does not exist: {impacted}")
    for test in data.get("tests", []):
        test_path = test.get("path", "")
        if not _test_in_roots(workspace, test_path):
            add(
                "test_outside_root",
                f"Linked test is outside configured roots: {test_path}",
            )
        elif workspace.read_optional(test_path) is None:
            add("missing_test", f"Linked test does not exist: {test_path}")
    if data.get("verification_kind") == "automated":
        impacted = set(data.get("impacted_files", []))
        covered = {
            covered_path
            for test in data.get("tests", [])
            for covered_path in test.get("covered_files", [])
        }
        for missing in sorted(impacted - covered):
            add(
                "incomplete_coverage",
                f"Impacted file has no linked test coverage: {missing}",
            )
        for diverged in sorted(covered - impacted):
            add(
                "diverged_coverage",
                f"Test coverage names a non-impacted file: {diverged}",
            )
    return findings


def _requirement_validate(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    data, revision, path = _load_requirement(
        workspace, _require_text(inputs, "requirement")
    )
    findings = tuple(_requirement_findings(workspace, data, path))
    return _done(
        context,
        definition,
        "Requirement validation completed.",
        data={"finding_count": len(findings)},
        revision=revision,
        findings=findings,
    )


def _specification_set(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    requirement_id = _require_text(inputs, "requirement")
    requirement, requirement_revision, requirement_path = _load_requirement(
        workspace, requirement_id
    )
    for field in (
        "title",
        "purpose",
        "contract",
        "inputs_outputs",
        "error_behavior",
        "examples",
        "open_details",
    ):
        _require_text(inputs, field)
    if inputs.get("status") not in {"draft", "active"} or not isinstance(
        inputs.get("rules"), list
    ):
        raise UseCaseError(
            "invalid_input", "Specification status or rules are invalid."
        )
    now = _time(context)
    path = _specification_path(workspace, requirement_id)
    metadata = {
        "schema": 1,
        "artifact_type": "specification",
        "requirement_id": requirement_id,
        "status": inputs["status"],
        "updated_at": now,
    }
    state = {
        field: inputs[field]
        for field in (
            "title",
            "purpose",
            "contract",
            "inputs_outputs",
            "rules",
            "error_behavior",
            "examples",
            "open_details",
        )
    }
    requirement["specification"] = path
    requirement["updated_at"] = now
    existing = workspace.revision(path)
    mutations = (
        RepositoryMutation(
            path, workspace.render_document(metadata, state, kind="specification")
        ),
        RepositoryMutation(requirement_path, workspace.render_requirement(requirement)),
    )
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="specification_set",
        target=path,
        mutations=mutations,
        expected={
            path: existing,
            requirement_path: inputs.get("expected_revision", requirement_revision),
        },
    )
    return _done(
        context,
        definition,
        "Specification current content set.",
        data={"requirement_id": requirement_id, "path": path},
        run_id=run_id,
        stage=stage,
        revision=revisions[path],
        artifacts=(
            _artifact(
                path,
                "created" if existing is None else "updated",
                revisions[path],
                kind="specification",
            ),
        ),
    )


def _specification_delete(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    requirement_id = _require_text(inputs, "requirement")
    requirement, requirement_revision, requirement_path = _load_requirement(
        workspace, requirement_id
    )
    path = requirement.get("specification") or _specification_path(
        workspace, requirement_id
    )
    spec_revision = workspace.revision(path)
    if spec_revision is None:
        raise UseCaseError(
            "not_found", "Requirement has no Specification.", field="requirement"
        )
    requirement["specification"] = ""
    requirement["updated_at"] = _time(context)
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="specification_deleted",
        target=path,
        mutations=(
            RepositoryMutation(path, None),
            RepositoryMutation(
                requirement_path, workspace.render_requirement(requirement)
            ),
        ),
        expected={
            path: spec_revision,
            requirement_path: inputs.get("expected_revision", requirement_revision),
        },
    )
    return _done(
        context,
        definition,
        "Specification deleted and Requirement link cleared.",
        data={"requirement_id": requirement_id},
        run_id=run_id,
        stage=stage,
        artifacts=(_artifact(path, "deleted", None, kind="specification"),),
    )


def _component_input(
    inputs: dict[str, Any], *, component_id: str, now: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = _require_text(inputs, "name")
    if inputs.get("status") not in {"draft", "active"}:
        raise UseCaseError(
            "invalid_input", "Component status is invalid.", field="status"
        )
    files = inputs.get("files")
    file_roles = inputs.get("file_roles")
    requirements = inputs.get("requirement_ids")
    links = inputs.get("test_links")
    if (
        not isinstance(files, list)
        or not files
        or not isinstance(file_roles, list)
        or not isinstance(requirements, list)
        or not isinstance(links, list)
    ):
        raise UseCaseError(
            "invalid_input",
            (
                "Component files, file roles, Requirement IDs, and test links "
                "must be lists."
            ),
        )
    normalized_files = [_path(value, "files") for value in files]
    normalized_roles = []
    for role in file_roles:
        if not isinstance(role, dict):
            raise UseCaseError(
                "invalid_input", "Component file role is invalid.", field="file_roles"
            )
        normalized_roles.append(
            {
                "path": _path(role.get("path"), "file_roles.path"),
                "role": _require_text(role, "role"),
            }
        )
    if {item["path"] for item in normalized_roles} != set(normalized_files):
        raise UseCaseError(
            "invalid_input",
            "Component file roles must describe every Component file exactly.",
            field="file_roles",
        )
    if not all(_REQ_ID.fullmatch(value) for value in requirements):
        raise UseCaseError(
            "invalid_input",
            "Component Requirement identity is invalid.",
            field="requirement_ids",
        )
    normalized_links = []
    for link in links:
        if not isinstance(link, dict):
            raise UseCaseError(
                "invalid_input", "Component test link is invalid.", field="test_links"
            )
        normalized_links.append(
            {
                "path": _path(link.get("path"), "test_links.path"),
                "selector": link.get("selector", ""),
                "description": _require_text(link, "description"),
            }
        )
    for field in ("purpose_boundary", "interfaces"):
        _require_text(inputs, field)
    metadata = {
        "schema": 1,
        "artifact_type": "component",
        "id": component_id,
        "status": inputs["status"],
        "name": name,
        "files": normalized_files,
        "requirement_ids": requirements,
        "reviewed_at": now,
    }
    state = {
        "purpose_boundary": inputs["purpose_boundary"],
        "interfaces": inputs["interfaces"],
        "behaviors": inputs.get("behaviors", []),
        "file_roles": normalized_roles,
        "dependencies": inputs.get("dependencies", []),
        "test_links": normalized_links,
        "known_gaps": inputs.get("known_gaps", []),
        "drift_review": inputs.get("drift_review", {}),
    }
    return metadata, state


def _component_create(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    for _ in range(8):
        component_id = _identity(context, "COMP")
        path = _component_path(workspace, component_id)
        if workspace.read_optional(path) is None:
            break
    else:
        raise UseCaseError(
            "state_conflict",
            "A collision-free Component identity could not be generated.",
        )
    metadata, state = _component_input(
        inputs, component_id=component_id, now=_time(context)
    )
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="component_created",
        target=component_id,
        mutations=(
            RepositoryMutation(
                path, workspace.render_document(metadata, state, kind="component")
            ),
        ),
        expected={path: None},
    )
    return _done(
        context,
        definition,
        "Component created and recorded in the Run.",
        data={"id": component_id},
        run_id=run_id,
        stage=stage,
        revision=revisions[path],
        artifacts=(_artifact(path, "created", revisions[path], kind="component"),),
    )


def _load_component(
    workspace: Workspace, component_id: str
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    path = _component_path(workspace, component_id)
    metadata, state, revision = workspace.load_document(path)
    if (
        metadata.get("artifact_type") != "component"
        or metadata.get("id") != component_id
    ):
        raise UseCaseError(
            "malformed_state", "Component identity and schema disagree.", path=path
        )
    return metadata, state, revision, path


def _component_update(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    component_id = _require_text(inputs, "component")
    _, _, revision, path = _load_component(workspace, component_id)
    metadata, state = _component_input(
        inputs, component_id=component_id, now=_time(context)
    )
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="component_updated",
        target=component_id,
        mutations=(
            RepositoryMutation(
                path, workspace.render_document(metadata, state, kind="component")
            ),
        ),
        expected={path: inputs.get("expected_revision", revision)},
    )
    return _done(
        context,
        definition,
        "Component current content replaced.",
        data={"id": component_id},
        run_id=run_id,
        stage=stage,
        revision=revisions[path],
    )


def _component_show(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    metadata, state, revision, path = _load_component(
        workspace, _require_text(inputs, "component")
    )
    return _done(
        context,
        definition,
        "Component context loaded.",
        data={"metadata": metadata, "state": state},
        revision=revision,
        artifacts=(_artifact(path, "read", revision, kind="component"),),
    )


def _component_list(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    paths = workspace.list_files(str(workspace.config.components), suffix=".md")
    offset = _page_offset(inputs, len(paths))
    items = []
    for path in paths[offset : offset + 20]:
        metadata, state, revision = workspace.load_document(path)
        items.append(
            {
                "id": metadata.get("id"),
                "name": metadata.get("name"),
                "status": metadata.get("status"),
                "files": metadata.get("files", []),
                "known_gaps": state.get("known_gaps", []),
                "revision": revision,
            }
        )
    return _done(
        context,
        definition,
        "Component summaries listed.",
        data={
            "items": items,
            "has_more": len(paths) > offset + 20,
            "next_cursor": (
                str(offset + 20) if len(paths) > offset + 20 else None
            ),
        },
    )


def _component_findings(
    workspace: Workspace, metadata: dict[str, Any], state: dict[str, Any], path: str
) -> list[dict[str, Any]]:
    findings = []

    def add(code: str, summary: str) -> None:
        findings.append(
            {
                "label": f"F{len(findings) + 1}",
                "code": code,
                "severity": "warning",
                "summary": summary,
                "disposition": "open",
                "artifact": path,
            }
        )

    for file_path in metadata.get("files", []):
        if workspace.read_optional(file_path) is None:
            add("missing_component_file", f"Component file does not exist: {file_path}")
    for requirement_id in metadata.get("requirement_ids", []):
        try:
            _load_requirement(workspace, requirement_id)
        except (UseCaseError, WorkspaceError):
            add(
                "missing_requirement",
                f"Component Requirement does not exist: {requirement_id}",
            )
    for link in state.get("test_links", []):
        if (
            not _test_in_roots(workspace, link["path"])
            or workspace.read_optional(link["path"]) is None
        ):
            add(
                "missing_component_test",
                f"Component test link is invalid: {link['path']}",
            )
    review = state.get("drift_review", {})
    if any(
        review.get(key) not in {"yes", "not_applicable"}
        for key in ("behavior", "interfaces", "dependencies", "files")
    ):
        add("component_drift", "Component drift review is incomplete or uncertain.")
    return findings


def _component_validate(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    metadata, state, revision, path = _load_component(
        workspace, _require_text(inputs, "component")
    )
    findings = tuple(_component_findings(workspace, metadata, state, path))
    return _done(
        context,
        definition,
        "Component validation completed.",
        data={"finding_count": len(findings)},
        revision=revision,
        findings=findings,
    )


def _component_find(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    query = _path(_require_text(inputs, "path"), "path")
    items = []
    for path in workspace.list_files(str(workspace.config.components), suffix=".md"):
        metadata, _, revision = workspace.load_document(path)
        exact = query in metadata.get("files", [])
        related = any(
            file.startswith(f"{query}/") or query.startswith(f"{file}/")
            for file in metadata.get("files", [])
        )
        if exact or related:
            items.append(
                {
                    "id": metadata["id"],
                    "name": metadata["name"],
                    "relationship": "exact" if exact else "related",
                    "revision": revision,
                }
            )
    uncertainty = (
        "none"
        if len(items) == 1 and items[0]["relationship"] == "exact"
        else "no unique exact Component relationship"
    )
    return _done(
        context,
        definition,
        "Component relationship lookup completed.",
        data={"items": items[:20], "uncertainty": uncertainty},
    )


def _component_delete(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    component_id = _require_text(inputs, "component")
    _, _, revision, path = _load_component(workspace, component_id)
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="component_deleted",
        target=component_id,
        mutations=(RepositoryMutation(path, None),),
        expected={path: inputs.get("expected_revision", revision)},
    )
    return _done(
        context,
        definition,
        "Component document deleted; project files preserved.",
        data={"id": component_id},
        run_id=run_id,
        stage=stage,
        artifacts=(_artifact(path, "deleted", revisions[path], kind="component"),),
    )


def _requirement_delete(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    requirement_id = _require_text(inputs, "requirement")
    requirement, revision, path = _load_requirement(workspace, requirement_id)
    mutations = [RepositoryMutation(path, None)]
    expected: dict[str, str | None] = {path: inputs.get("expected_revision", revision)}
    specification = requirement.get("specification")
    if specification:
        spec_revision = workspace.revision(specification)
        if spec_revision is not None:
            mutations.append(RepositoryMutation(specification, None))
            expected[specification] = spec_revision
    for component_path in workspace.list_files(
        str(workspace.config.components), suffix=".md"
    ):
        metadata, state, component_revision = workspace.load_document(component_path)
        if requirement_id in metadata.get("requirement_ids", []):
            metadata["requirement_ids"] = [
                value
                for value in metadata["requirement_ids"]
                if value != requirement_id
            ]
            mutations.append(
                RepositoryMutation(
                    component_path,
                    workspace.render_document(metadata, state, kind="component"),
                )
            )
            expected[component_path] = component_revision
    revisions, run_id, stage, _ = _record_project_change(
        context,
        workspace,
        action="requirement_deleted",
        target=requirement_id,
        mutations=tuple(mutations),
        expected=expected,
    )
    return _done(
        context,
        definition,
        (
            "Requirement, Specification, and current documentation links "
            "deleted; source and tests preserved."
        ),
        data={"id": requirement_id},
        run_id=run_id,
        stage=stage,
        artifacts=tuple(
            _artifact(
                item.path,
                "deleted" if item.content is None else "updated",
                revisions[item.path],
                kind="requirement",
            )
            for item in mutations
        ),
    )


def _all_requirements(workspace: Workspace) -> list[tuple[str, dict[str, Any], str]]:
    result = []
    for path in workspace.list_files(
        str(workspace.config.requirements), suffix=".toml"
    ):
        if "/REQ-" in path:
            data, revision = workspace.load_toml(path)
            result.append((path, data, revision))
    return result


def _trace_validate(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    del inputs
    workspace = _workspace(context)
    findings: list[dict[str, Any]] = []

    def add(code: str, summary: str, artifact: str) -> None:
        findings.append(
            {
                "label": f"F{len(findings) + 1}",
                "code": code,
                "severity": "warning",
                "summary": summary,
                "disposition": "open",
                "artifact": artifact,
            }
        )

    identities: dict[str, list[str]] = defaultdict(list)
    for path, data, _ in _all_requirements(workspace):
        identity = data.get("id", "")
        identities[identity].append(path)
        if path.rsplit("/", 1)[-1] != f"{identity}.toml":
            add(
                "identity_path_mismatch",
                f"Requirement identity does not match filename: {identity}",
                path,
            )
        for finding in _requirement_findings(workspace, data, path):
            add(finding["code"], finding["summary"], path)
    memberships: dict[str, list[str]] = defaultdict(list)
    for path in workspace.list_files(str(workspace.config.components), suffix=".md"):
        metadata, state, _ = workspace.load_document(path)
        identities[metadata.get("id", "")].append(path)
        for file_path in metadata.get("files", []):
            memberships[file_path].append(metadata["id"])
        for finding in _component_findings(workspace, metadata, state, path):
            add(finding["code"], finding["summary"], path)
    for identity, paths in identities.items():
        if identity and len(paths) > 1:
            add(
                "duplicate_identity",
                f"Identity appears in more than one artifact: {identity}",
                paths[0],
            )
    for file_path, components in memberships.items():
        if len(components) > 1:
            add(
                "component_membership_conflict",
                f"File belongs to multiple Components: {file_path}",
                file_path,
            )
    return _done(
        context,
        definition,
        "Trace validation completed without modifying project knowledge.",
        data={"finding_count": len(findings)},
        findings=tuple(findings),
    )


def _trace_impacted(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    changed = inputs.get("changed_files")
    changed_tests = inputs.get("changed_tests", [])
    if (
        not isinstance(changed, list)
        or not all(isinstance(item, str) for item in changed)
        or not isinstance(changed_tests, list)
    ):
        raise UseCaseError(
            "invalid_input", "changed_files and changed_tests must be path lists."
        )
    changed = [_path(item, "changed_files") for item in changed]
    selected: dict[tuple[str, str], set[str]] = defaultdict(set)
    covered: set[str] = set()
    incomplete: list[str] = []
    incomplete_files: set[str] = set()
    for _, requirement, _ in _all_requirements(workspace):
        impacted = set(requirement.get("impacted_files", [])).intersection(changed)
        for file_path in impacted:
            links = [
                test
                for test in requirement.get("tests", [])
                if file_path in test.get("covered_files", [])
            ]
            if not links:
                incomplete.append(
                    f"{requirement['id']} has no complete test coverage "
                    f"for {file_path}."
                )
                incomplete_files.add(file_path)
            for test in links:
                problem = _test_link_problem(
                    workspace, test.get("path"), test.get("selector", "")
                )
                if problem is not None:
                    incomplete.append(problem)
                    incomplete_files.add(file_path)
                    continue
                covered.add(file_path)
                selected[(test["path"], test.get("selector", ""))].add(
                    f"{requirement['id']} covers {file_path}"
                )
    for test_path in changed_tests:
        canonical = _path(test_path, "changed_tests")
        selected[(canonical, "")].add("Test was created or changed by the Run.")
    fallback = incomplete + [
        f"No complete test coverage for {file_path}."
        for file_path in changed
        if file_path not in covered
        and file_path not in incomplete_files
    ]
    tests = [
        {"path": path, "selector": selector, "reasons": sorted(reasons)}
        for (path, selector), reasons in sorted(selected.items())
    ]
    mode = "full" if fallback else "impacted"
    data = {
        "label": f"SEL-{context.operation_id[3:11]}",
        "mode": mode,
        "tests": tests,
        "fallback_reasons": fallback,
        "full_suite_commands": sorted(
            key for key in workspace.config.commands if key.startswith("tests.")
        )
        if fallback
        else [],
    }
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
    _require_active_stage(stage_meta)
    now = _time(context)
    stage_state["evidence"].append(
        {
            "label": f"E{len(stage_state['evidence']) + 1}",
            "kind": "trace_selection",
            "time": now,
            **data,
        }
    )
    stage_state["events"].append(_event(now, "operator", "trace_impacted", mode))
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
        f"Impacted selection recorded using {mode} mode.",
        data=data,
        run_id=run_id,
        stage=stage_meta["stage"],
        revision=revisions[stage_path],
    )


HANDLERS: dict[str, Callable[..., OperationResult]] = {
    "requirement.create": _requirement_create,
    "requirement.update": _requirement_update,
    "requirement.delete": _requirement_delete,
    "requirement.show": _requirement_show,
    "requirement.list": _requirement_list,
    "requirement.validate": _requirement_validate,
    "specification.set": _specification_set,
    "specification.delete": _specification_delete,
    "component.create": _component_create,
    "component.update": _component_update,
    "component.delete": _component_delete,
    "component.show": _component_show,
    "component.list": _component_list,
    "component.validate": _component_validate,
    "component.find": _component_find,
    "trace.validate": _trace_validate,
    "trace.impacted": _trace_impacted,
}


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
