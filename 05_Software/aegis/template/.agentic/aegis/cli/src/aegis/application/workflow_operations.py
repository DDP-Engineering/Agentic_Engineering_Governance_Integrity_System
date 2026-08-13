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

import json
import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aegis.application.operation_types import (
    OperationContext,
    OperationDefinition,
    revision_read_next_actions,
)
from aegis.application.product_operations import unavailable_operation
from aegis.application.resume_context import assemble_stage_resume_context
from aegis.application.stage_expectations import (
    evaluate_stage_expectations,
    summarize_red_before_green_state,
)
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
_CURSOR = re.compile(r"^(0|[1-9][0-9]*)$")
_DECISIONS = frozenset({"approved", "rejected", "exception_approved"})
_INTERACTION_MODES = frozenset({"checkpoint", "continuous"})
_EVIDENCE_KINDS = frozenset({"manual", "automated", "imported"})
_DISPOSITIONS = {"open", "resolved", "accepted", "waived", "not_applicable"}
_AUTOMATED_OUTCOMES = {
    "passed",
    "failed",
    "timed_out",
    "cancelled",
    "launch_error",
}
_PENDING_RECOVERY_FINDING_LIMIT = 10


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
    truncated: bool = False,
    details_ref: str | None = None,
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
        truncated=truncated,
        details_ref=details_ref,
    )


def _error(
    context: OperationContext,
    definition: OperationDefinition,
    error: UseCaseError,
    *,
    data: dict[str, Any] | None = None,
    next_actions: tuple[dict[str, Any], ...] = (),
) -> OperationResult:
    return OperationResult(
        product=context.product,
        product_version=context.product_version,
        operation=definition.operation,
        operation_id=context.operation_id,
        operation_status="error",
        message=error.summary,
        data=data or {},
        error=ProtocolError(
            code=error.code,
            summary=error.summary,
            field=error.field,
            path=error.path,
            retryable=error.retryable,
            details=error.details,
        ),
        next_actions=next_actions,
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
                next_actions=(
                    revision_read_next_actions(definition, inputs)
                    if error.code == "state_conflict"
                    else ()
                ),
            )
        except UseCaseError as error:
            return _error(
                context,
                definition,
                error,
                next_actions=(
                    revision_read_next_actions(definition, inputs)
                    if error.code == "state_conflict"
                    and (
                        error.field == "expected_revision"
                        or definition.machine_revision_policy.value.startswith(
                            ("required:", "conditional:")
                        )
                    )
                    else ()
                ),
            )

    execute.__name__ = f"execute_{handler.__name__.removeprefix('_')}"
    return execute


def _require_text(inputs: dict[str, Any], field: str) -> str:
    value = inputs.get(field)
    if not isinstance(value, str) or not value.strip():
        raise UseCaseError(
            "invalid_input", f"{field} must be non-empty text.", field=field
        )
    return value


def _page_offset(inputs: dict[str, Any], item_count: int) -> int:
    """
    @brief Validate one canonical integer list cursor as an item offset.
    @param[in] inputs Operation inputs that may contain a cursor token.
    @param[in] item_count Number of ordered items available to the operation.
    @return Zero for the first page or the validated cursor offset.
    @exception UseCaseError The cursor is malformed or beyond the item range.
    """
    cursor = inputs.get("cursor")
    if cursor is None:
        return 0
    if not isinstance(cursor, str) or _CURSOR.fullmatch(cursor) is None:
        raise UseCaseError(
            "invalid_input",
            "cursor must be a canonical non-negative integer offset.",
            field="cursor",
        )
    try:
        offset = int(cursor)
    except ValueError as error:
        raise UseCaseError(
            "invalid_input",
            "cursor must be a canonical non-negative integer offset.",
            field="cursor",
        ) from error
    if offset > item_count:
        raise UseCaseError(
            "invalid_input",
            "cursor exceeds the available item range.",
            field="cursor",
            details={"item_count": item_count},
        )
    return offset


def _require_active_stage(metadata: dict[str, Any]) -> None:
    """@brief Reject ordinary mutation outside the active current Stage."""
    if metadata.get("status") != "active":
        raise UseCaseError(
            "invalid_transition", "Current Stage mutations require an active Stage."
        )


def _validate_automated_evidence(entry: dict[str, Any]) -> None:
    """@brief Validate the complete truthful automated-evidence contract."""
    category = entry.get("category")
    if category not in {"tests", "lints", "audits"}:
        raise UseCaseError(
            "invalid_input",
            "Automated evidence category is invalid.",
            field="category",
            details={"allowed": ["audits", "lints", "tests"]},
        )
    _require_text(entry, "name")
    command = entry.get("command")
    selector = entry.get("selector")
    if command is not None and (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) and item.strip() for item in command)
    ):
        raise UseCaseError(
            "invalid_input",
            "Automated evidence command must be a non-empty argument list.",
            field="command",
        )
    if selector is not None and (not isinstance(selector, str) or not selector.strip()):
        raise UseCaseError(
            "invalid_input",
            "Automated evidence selector must be non-empty text.",
            field="selector",
        )
    if command is None and selector is None:
        raise UseCaseError(
            "invalid_input",
            "Automated evidence requires a command or selector.",
            field="command",
        )
    _require_text(entry, "working_directory")
    outcome = entry.get("outcome")
    if outcome not in _AUTOMATED_OUTCOMES:
        raise UseCaseError(
            "invalid_input", "Automated evidence outcome is invalid.", field="outcome"
        )
    if "exit_status" not in entry:
        raise UseCaseError(
            "invalid_input",
            "Automated evidence requires an exit status field.",
            field="exit_status",
        )
    exit_status = entry["exit_status"]
    if outcome == "passed" and (type(exit_status) is not int or exit_status != 0):
        raise UseCaseError(
            "invalid_input",
            "Passed automated evidence requires exit status zero.",
            field="exit_status",
        )
    if outcome == "failed" and (type(exit_status) is not int or exit_status == 0):
        raise UseCaseError(
            "invalid_input",
            "Failed automated evidence requires a nonzero exit status.",
            field="exit_status",
        )
    if outcome not in {"passed", "failed"} and exit_status is not None:
        raise UseCaseError(
            "invalid_input",
            "Incomplete execution outcomes require a null exit status.",
            field="exit_status",
        )
    _require_text(entry, "observed_result")
    tests = entry.get("tests")
    if tests is not None and (
        not isinstance(tests, list)
        or not tests
        or not all(isinstance(test, str) and test.strip() for test in tests)
    ):
        raise UseCaseError(
            "invalid_input",
            "Automated evidence tests must be a list of non-empty selectors.",
            field="tests",
        )
    if category == "tests" and tests is None:
        raise UseCaseError(
            "invalid_input",
            "Reported test evidence requires selected tests.",
            field="tests",
        )
    attachment = entry.get("attachment")
    if attachment is not None and (
        not isinstance(attachment, str) or not attachment.strip()
    ):
        raise UseCaseError(
            "invalid_input",
            "Automated evidence attachment must be a non-empty reference path.",
            field="attachment",
        )


def _current_test_fingerprints(
    context: OperationContext, workspace: Workspace
) -> dict[str, str]:
    """@return Exact-byte fingerprints for Git-visible configured tests."""
    fingerprints: dict[str, str] = {}
    for root in workspace.config.test_roots:
        for path in workspace.git_visible_files(str(root)):
            fingerprints[path] = context.hash_service.digest(workspace.read_bytes(path))
    return fingerprints


def _reported_evidence_facts(
    context: OperationContext,
    workspace: Workspace,
    *,
    run_id: str,
    stage: str,
    entry: dict[str, Any],
    stage_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """@brief Add fingerprints and factual findings to reported evidence."""
    findings: list[dict[str, Any]] = []
    now = entry["time"]
    outcome = entry["outcome"]
    category = entry["category"]
    entry["engineering_conclusion"] = (
        outcome if outcome in {"passed", "failed"} else "unknown"
    )
    if category == "tests" and stage == "check" and outcome == "failed":
        entry["fingerprints"] = _current_test_fingerprints(context, workspace)
        entry["red_witness"] = bool(entry["fingerprints"])
    elif category == "tests" and stage in {"implementation", "validation"}:
        check_path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES['check']}"
        _, check_state, _ = workspace.load_document(check_path)
        red_fingerprints = [
            item["fingerprints"]
            for item in check_state.get("evidence", [])
            if isinstance(item, dict)
            and item.get("red_witness") is True
            and isinstance(item.get("fingerprints"), dict)
            and item["fingerprints"]
        ]
        if red_fingerprints:
            current = _current_test_fingerprints(context, workspace)
            changed = sorted(
                {
                    path
                    for recorded in red_fingerprints
                    for path in set(recorded) | set(current)
                    if current.get(path) != recorded.get(path)
                }
            )
            entry["red_fingerprint_comparison"] = {
                "changed_tests": changed,
                "current": current,
            }
            for path in changed:
                findings.append(
                    {
                        "code": "test_changed_after_red",
                        "severity": "warning",
                        "observation": f"{path} changed after red evidence.",
                        "consequence": (
                            "The developer decides whether the change is legitimate."
                        ),
                        "disposition": "open",
                        "time": now,
                        "artifact": path,
                    }
                )
    if outcome != "passed":
        conclusion = entry["engineering_conclusion"]
        findings.append(
            {
                "code": f"execution_{outcome}",
                "severity": "warning",
                "observation": f"{category}.{entry['name']} was reported as {outcome}.",
                "consequence": f"The recorded engineering conclusion is {conclusion}.",
                "disposition": "open",
                "time": now,
            }
        )
    return findings


def _delivery_recorded_state(
    workspace: Workspace,
    *,
    run_id: str,
    run_meta: dict[str, Any],
    run_state: dict[str, Any],
    delivery_meta: dict[str, Any],
    delivery_state: dict[str, Any],
) -> str:
    """@return A compact deterministic Delivery record from durable Stage state."""
    stage_records: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    summaries = {item["name"]: item for item in run_state["stages"]}
    for stage in _STAGES:
        if stage == "delivery":
            stage_records[stage] = (delivery_meta, delivery_state)
            continue
        stage_path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[stage]}"
        stage_metadata, state, _ = workspace.load_document(stage_path)
        stage_records[stage] = (stage_metadata, state)

    skipped_or_omitted = []
    waiver_escapes = []
    non_passing_executions = []
    green_test_evidence = []
    test_selections = []
    selections_by_label: dict[str, dict[str, Any]] = {}
    linked_selection_executions = []
    changed_tests: set[str] = set()
    fingerprint_comparison_performed = False
    open_finding_total = 0
    open_findings_by_severity: dict[str, int] = {}
    open_finding_stages: set[str] = set()
    for stage in _STAGES:
        stage_metadata, state = stage_records[stage]
        status = stage_metadata.get("status")
        escapes = [
            item for item in state.get("escapes", []) if isinstance(item, dict)
        ]
        if status in {"skipped", "omitted"}:
            if status == "skipped":
                skip = next(
                    (
                        item
                        for item in reversed(escapes)
                        if item.get("type") == "skip"
                    ),
                    {},
                )
                reason = (
                    skip.get("reason")
                    or summaries[stage].get("result")
                    or "not recorded"
                )
            else:
                reason = f"profile={run_meta['profile']}"
            skipped_or_omitted.append(
                {"stage": stage, "status": status, "reason": reason}
            )
        waiver_escapes.extend(
            {
                "stage": stage,
                "target": escape.get("target"),
                "reason": escape.get("reason"),
            }
            for escape in escapes
            if escape.get("type") == "waiver"
        )
        for evidence in state.get("evidence", []):
            if not isinstance(evidence, dict):
                continue
            if evidence.get("kind") == "trace_selection":
                label = evidence.get("label")
                selected_tests = []
                for selected in evidence.get("tests", []):
                    if not isinstance(selected, dict) or not isinstance(
                        selected.get("path"), str
                    ):
                        continue
                    selector = selected.get("selector")
                    suffix = (
                        f"::{selector}"
                        if isinstance(selector, str) and selector
                        else ""
                    )
                    selected_tests.append(
                        selected["path"] + suffix
                    )
                selection = {
                    "stage": stage,
                    "label": label,
                    "mode": evidence.get("mode"),
                    "tests": selected_tests,
                    "fallback_reasons": list(evidence.get("fallback_reasons", [])),
                    "full_suite_commands": list(
                        evidence.get("full_suite_commands", [])
                    ),
                    "executions": [],
                }
                test_selections.append(selection)
                if isinstance(label, str):
                    selections_by_label[label] = selection
            if (
                evidence.get("kind") == "automated"
                and evidence.get("outcome") != "passed"
            ):
                non_passing_executions.append(
                    {
                        "stage": stage,
                        "category": evidence.get("category"),
                        "name": evidence.get("name"),
                        "outcome": evidence.get("outcome"),
                    }
                )
            if (
                evidence.get("kind") == "automated"
                and evidence.get("category") == "tests"
                and evidence.get("outcome") == "passed"
            ):
                evidence_tests = [
                    test
                    for test in evidence.get("tests", [])
                    if isinstance(test, str)
                ]
                linked_selection = selections_by_label.get(evidence.get("selection"))
                if not evidence_tests and linked_selection is not None:
                    evidence_tests = list(linked_selection["tests"])
                green_test_evidence.append(
                    {
                        "stage": stage,
                        "name": evidence.get("name"),
                        "provenance": evidence.get("provenance", "unknown"),
                        "tests": evidence_tests,
                    }
                )
            if isinstance(evidence.get("selection"), str):
                linked_selection_executions.append(
                    (
                        evidence["selection"],
                        {
                            "stage": stage,
                            "name": evidence.get("name"),
                            "outcome": evidence.get("outcome"),
                            "mode": evidence.get("selection_mode"),
                            "fallback_reasons": list(
                                evidence.get("selection_fallback_reasons", [])
                            ),
                        },
                    )
                )
            comparison = evidence.get("red_fingerprint_comparison")
            if (
                evidence.get("kind") == "automated"
                and evidence.get("category") == "tests"
                and evidence.get("outcome") == "passed"
                and evidence.get("provenance") in {"executed", "reported"}
                and isinstance(comparison, dict)
            ):
                fingerprint_comparison_performed = True
                changed_tests.update(
                    item
                    for item in comparison.get("changed_tests", [])
                    if isinstance(item, str)
                )
        for finding in state.get("findings", []):
            if not isinstance(finding, dict) or finding.get("disposition") != "open":
                continue
            severity = finding["severity"]
            open_finding_total += 1
            open_findings_by_severity[severity] = (
                open_findings_by_severity.get(severity, 0) + 1
            )
            open_finding_stages.add(stage)

    for label, execution in linked_selection_executions:
        selection = selections_by_label.get(label)
        if selection is not None:
            selection["executions"].append(execution)

    check_meta, check_state = stage_records["check"]
    implementation_started_at = str(
        stage_records["implementation"][0].get("started_at", "")
    )
    raw_red_state = summarize_red_before_green_state(
        check_state, implementation_started_at=implementation_started_at
    )
    check_skipped = check_meta.get("status") == "skipped"
    later_executed_green = any(
        item["stage"] in {"implementation", "validation"}
        and item["provenance"] in {"executed", "reported"}
        for item in green_test_evidence
    )
    valid_witness = raw_red_state["valid_witness"] and not check_skipped
    approved_exception = raw_red_state["approved_exception"] and not check_skipped
    red_before_green = {
        "check_skipped": check_skipped,
        "recorded_witness": raw_red_state["valid_witness"],
        "valid_witness": valid_witness,
        "approved_exception": approved_exception,
        "later_executed_green": later_executed_green,
        "conclusion": (
            "witness_established"
            if valid_witness
            else "exception_approved"
            if approved_exception
            else "not_established"
        ),
    }
    check_changes = [
        {"code": finding.get("code"), "artifact": finding.get("artifact")}
        for finding in check_state.get("findings", [])
        if isinstance(finding, dict)
        and finding.get("code")
        in {"check_out_of_zone_change", "check_git_state_changed"}
    ]
    categories = (
        ("skipped_or_omitted_stages", skipped_or_omitted),
        ("waiver_escapes", waiver_escapes),
        ("non_passing_executions", non_passing_executions),
        ("green_test_evidence", green_test_evidence),
        ("test_selections", test_selections),
        ("check_changes", check_changes),
        ("changed_tests", sorted(changed_tests)),
        (
            "fingerprint_comparison",
            "performed" if fingerprint_comparison_performed else "not_performed",
        ),
        ("red_before_green", red_before_green),
        (
            "open_findings",
            {
                "total": open_finding_total,
                "by_severity": dict(sorted(open_findings_by_severity.items())),
                "stages": sorted(open_finding_stages),
            },
        ),
    )
    return "\n".join(
        f"- {name}: "
        + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for name, value in categories
    )


def _delivery_prior_stage_reference(
    *, run_id: str, record_name: str, record_count: int
) -> str:
    """@return One bounded prose reference to durable pre-Delivery Stage state."""
    root = f".agentic/runs/{run_id}/"
    if record_count == 0:
        return (
            f"No prior Stage {record_name} records were recorded; durable Stage "
            f"artifacts are under {root}"
        )
    return (
        f"{record_count} prior Stage {record_name} records are preserved in durable "
        f"Stage artifacts under {root}"
    )


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
    interaction_mode = metadata.get("interaction_mode", "checkpoint")
    if interaction_mode not in _INTERACTION_MODES:
        raise UseCaseError(
            "malformed_state",
            "Run interaction mode is invalid.",
            path=path,
            details={"allowed": sorted(_INTERACTION_MODES)},
        )
    metadata["interaction_mode"] = interaction_mode
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


def _load_selected_run_for_mutation(
    workspace: Workspace,
) -> tuple[str, dict[str, Any], dict[str, Any], str, str]:
    """
    @brief Load the selected non-terminal Run for mutation.
    @param[in] workspace Repository storage boundary.
    @return Run identity, decoded state, revision, and path.
    @exception UseCaseError The selected Run is delivered or abandoned.
    """
    run_id = _selected_run_id(workspace)
    run_meta, run_state, run_revision, run_path = _load_run(workspace, run_id)
    status = run_meta.get("status")
    if status in {"delivered", "abandoned"}:
        raise UseCaseError(
            "invalid_transition", f"A {status} Run cannot be mutated."
        )
    return run_id, run_meta, run_state, run_revision, run_path


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
    run_id, run_meta, run_state, run_revision, run_path = (
        _load_selected_run_for_mutation(workspace)
    )
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


def _run_actor(run_state: dict[str, Any]) -> str:
    """@return The durable Run actor or the legacy operator default."""
    actor = run_state.get("actor")
    return actor if isinstance(actor, str) and actor.strip() else "operator"


def _next_finding_label(findings: list[dict[str, Any]]) -> str:
    """@return The next unused canonical Stage-local finding label."""
    numbers = [
        int(label[1:])
        for item in findings
        if isinstance((label := item.get("label")), str)
        and re.fullmatch(r"F[1-9][0-9]*", label)
    ]
    return f"F{max(numbers, default=0) + 1}"


def _completion_finding_is_current(
    existing: dict[str, Any], candidate: dict[str, Any]
) -> bool:
    """@return Whether an unresolved equivalent expectation is already visible."""
    return (
        existing.get("code") == candidate.get("code")
        and existing.get("expectation") == candidate.get("expectation")
        and existing.get("disposition")
        in {"open", "accepted", "waived", "not_applicable"}
    )


def _designated_stage_references(
    workspace: Workspace,
    *,
    run_meta: dict[str, Any],
    stage_meta: dict[str, Any],
    stage_state: dict[str, Any],
) -> tuple[tuple[str, bool], ...]:
    """@return Designated artifact paths and whether each resolves safely."""
    paths: list[str] = []
    paths.extend(
        f"{workspace.config.requirements}/{identity}.toml"
        for identity in run_meta.get("requirement_ids", [])
        if isinstance(identity, str)
    )
    paths.extend(
        f"{workspace.config.components}/{identity}.md"
        for identity in run_meta.get("component_ids", [])
        if isinstance(identity, str)
    )
    paths.extend(
        path for path in stage_meta.get("attachments", []) if isinstance(path, str)
    )
    paths.extend(
        item["path"]
        for item in stage_state.get("attachments", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    )
    for item in stage_state.get("evidence", []):
        if not isinstance(item, dict):
            continue
        attachment = item.get("attachment")
        if isinstance(attachment, str):
            paths.append(attachment)
        elif isinstance(attachment, dict) and isinstance(attachment.get("path"), str):
            paths.append(attachment["path"])
    results = []
    for path in dict.fromkeys(paths):
        try:
            exists = workspace.path_exists(path)
        except (ValueError, WorkspaceError):
            exists = False
        results.append((path, exists))
    return tuple(results)


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


def _classification_states(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    """@brief Return deterministic observed Git states keyed by repository path."""
    states: dict[str, list[str]] = {}
    for area in ("staged", "unstaged", "untracked", "deleted"):
        for item in snapshot.get("classifications", {}).get(area, []):
            path = item if isinstance(item, str) else item.get("path", "")
            if path:
                states.setdefault(path, []).append(area)
    for item in snapshot.get("classifications", {}).get("renamed", []):
        for path in (item.get("from", ""), item.get("to", "")):
            if path:
                states.setdefault(path, []).append("renamed")
    return {path: sorted(set(values)) for path, values in sorted(states.items())}


def _attribution_path(path: str) -> bool:
    """@brief Exclude AEGIS-owned mutable runtime state from project attribution."""
    return not path.startswith(".agentic/runs/") and not path.startswith(
        ".agentic/.runtime/"
    )


def _dirty_baseline(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """@brief Retain only opening dirty-path state needed for later uncertainty."""
    states = _classification_states(snapshot)
    files = snapshot.get("working_files", {})
    return [
        {"path": path, "state": state, "revision": files.get(path)}
        for path, state in states.items()
    ]


def _observe_run_changes(
    workspace: Workspace, run_state: dict[str, Any], *, observed_at: str
) -> None:
    """@brief Record only post-baseline observations without claiming authorship."""
    opening = run_state.get("opening_repository_state", {})
    current = workspace.git_snapshot()
    opening_dirty = {item["path"]: item for item in opening.get("dirty_paths", [])}
    current_files = current.get("working_files", {})
    current_states = _classification_states(current)
    existing = {
        item.get("path")
        for item in run_state.get("changes_first_observed", [])
        if isinstance(item, dict)
    }
    uncertain = {
        item.get("path")
        for item in run_state.get("uncertain_authorship", [])
        if isinstance(item, dict) and item.get("path")
    }
    changed = sorted(
        path
        for path in current_states
        if _attribution_path(path) and path not in opening_dirty
    )
    for path in changed:
        if path in existing:
            continue
        run_state["changes_first_observed"].append(
            {
                "path": path,
                "state": current_states.get(path, ["absent"]),
                "observed_at": observed_at,
            }
        )
        existing.add(path)
        if path not in uncertain:
            run_state["uncertain_authorship"].append(
                {
                    "path": path,
                    "reason": (
                        "Observed after the opening baseline; authorship is unknown."
                    ),
                    "observed_at": observed_at,
                    "observed_state": current_states.get(path, ["absent"]),
                }
            )
            uncertain.add(path)
    for path, before in sorted(opening_dirty.items()):
        before_state = {"state": before["state"], "revision": before.get("revision")}
        after = {
            "state": current_states.get(path, ["clean"]),
            "revision": current_files.get(path),
        }
        if before_state == after:
            continue
        if any(
            item.get("code") == "preexisting_worktree_changed"
            and item.get("path") == path
            and item.get("before") == before_state
            and item.get("after") == after
            for item in run_state.get("attribution_findings", [])
        ):
            continue
        run_state.setdefault("attribution_findings", []).append(
            {
                "code": "preexisting_worktree_changed",
                "severity": "warning",
                "path": path,
                "observed_at": observed_at,
                "before": before_state,
                "after": after,
                "observation": (
                    "A pre-existing working change changed after Run opening."
                ),
                "consequence": (
                    "Authorship remains uncertain; the path is not Run-produced."
                ),
            }
        )
    transitions = {
        "branch": (opening.get("branch"), current.get("branch")),
        "head": (opening.get("head"), current.get("head")),
        "index_revision": (
            opening.get("index_revision"),
            current.get("index_revision"),
        ),
    }
    for kind, (before, after) in transitions.items():
        if before == after:
            continue
        marker = f"repository_{kind}_changed"
        if any(
            item.get("code") == marker
            for item in run_state.get("attribution_findings", [])
        ):
            continue
        run_state.setdefault("attribution_findings", []).append(
            {
                "code": marker,
                "severity": "warning",
                "observed_at": observed_at,
                "before": before,
                "after": after,
                "observation": f"Repository {kind} changed after the opening baseline.",
                "consequence": (
                    "Change attribution remains uncertain and requires review."
                ),
            }
        )


def _adopt_explicitly_scoped_paths(
    run_state: dict[str, Any], change: dict[str, Any]
) -> None:
    """@brief Adopt only already observed paths named by a scope revision."""
    observed = {
        item.get("path")
        for item in run_state.get("changes_first_observed", [])
        if isinstance(item, dict)
    }
    adopted = {
        item.get("path")
        for item in run_state.get("changes_adopted", [])
        if isinstance(item, dict)
    }
    scope_change = len(run_state.get("scope_changes", []))
    for path in sorted(set(change["affected_work"]) & observed):
        if path not in adopted:
            run_state["changes_adopted"].append(
                {"path": path, "scope_change": scope_change, "reason": change["reason"]}
            )
            adopted.add(path)


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
    _observe_run_changes(workspace, run_state, observed_at=stage_meta["updated_at"])
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
    pending_paths, pending_count = workspace.pending_recovery_paths(
        limit=_PENDING_RECOVERY_FINDING_LIMIT
    )
    for path in pending_paths:
        findings.append(
            {
                "label": f"F{len(findings) + 1}",
                "code": "pending_recovery_transaction",
                "severity": "info",
                "summary": (
                    "Pending interrupted publication recovery material is present."
                ),
                "disposition": "open",
                "artifact": path,
            }
        )
    configured = (
        str(workspace.config.requirements),
        str(workspace.config.components),
        *(str(path) for path in workspace.config.test_roots),
        str(workspace.config.adoptions),
        str(workspace.config.runs),
    )
    for path in configured:
        if not workspace.path_exists(path, directory=True, recover=False):
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
        data={
            "finding_count": len(findings),
            "pending_recovery_count": pending_count,
            "reported_pending_recovery_count": len(pending_paths),
        },
        truncated=pending_count > len(pending_paths),
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
    interaction_mode = inputs.get("interaction_mode", "checkpoint")
    if interaction_mode not in _INTERACTION_MODES:
        raise UseCaseError(
            "invalid_input",
            "Run interaction mode is invalid.",
            field="interaction_mode",
            details={"allowed": sorted(_INTERACTION_MODES)},
        )
    execution_instruction = inputs.get("execution_instruction")
    if interaction_mode == "continuous" and (
        not isinstance(execution_instruction, str)
        or not execution_instruction.strip()
    ):
        raise UseCaseError(
            "invalid_input",
            "Continuous interaction requires a non-empty execution_instruction.",
            field="execution_instruction",
        )
    if execution_instruction is None:
        execution_instruction = "None"
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
    snapshot = workspace.git_snapshot()
    opening = {
        "branch": snapshot["branch"],
        "head": snapshot["head"],
        "classifications": snapshot["classifications"],
        "index_revision": snapshot["index_revision"],
        "dirty_paths": _dirty_baseline(snapshot),
    }
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
            "common_findings": resource["common_findings"],
            "recovery_actions": resource["recovery_actions"],
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
        "interaction_mode": interaction_mode,
        "opened_at": now,
        "updated_at": now,
        "opened_branch": opening["branch"],
        "requirement_ids": [],
        "component_ids": [],
    }
    run_state = {
        "title": ticket.splitlines()[0][:100],
        "ticket_text": ticket,
        "intent": "Pending Intake restatement.",
        "scope": "Pending Alignment.",
        "excluded_scope": "None",
        "open_questions": "None",
        "actor": actor,
        "execution_instruction": execution_instruction,
        "opening_repository_state": opening,
        "changes_first_observed": [],
        "changes_adopted": [],
        "uncertain_authorship": [],
        "attribution_findings": [],
        "scope_changes": [],
        "stages": stages,
        "durable_context": "Run created; Intake is active.",
        "next_action": "Complete the Intake restatement.",
        "blockers": "None",
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
        data={
            "profile": profile,
            "work_type": work_type,
            "interaction_mode": interaction_mode,
        },
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
    workspace = _workspace(context)
    try:
        selected = _selected_run_id(workspace)
    except UseCaseError:
        selected = None
    run_ids = _run_ids(workspace)
    offset = _page_offset(inputs, len(run_ids))
    items = []
    for run_id in run_ids[offset : offset + 20]:
        try:
            metadata, state, revision, _ = _load_run(workspace, run_id)
        except (UseCaseError, WorkspaceError) as error:
            items.append(
                {
                    "id": run_id,
                    "status": "unreadable",
                    "path": error.path or _run_path(workspace, run_id),
                    "selected": run_id == selected,
                }
            )
            continue
        items.append(
            {
                "id": run_id,
                "status": metadata["status"],
                "profile": metadata["profile"],
                "interaction_mode": metadata["interaction_mode"],
                "current_stage": metadata["current_stage"],
                "selected": run_id == selected,
                "revision": revision,
                "ticket_summary": state["ticket_text"][:120],
            }
        )
    next_offset = offset + 20
    has_more = len(run_ids) > next_offset
    return _done(
        context,
        definition,
        "Run summaries listed.",
        data={
            "items": items,
            "has_more": has_more,
            "next_cursor": str(next_offset) if has_more else None,
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
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
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
    before_profile = run_meta["profile"]
    event_result = (
        f"Profile changed from {before_profile} to {profile}. Reason: {reason}"
    )
    design_meta["status"] = "omitted" if profile == "short" else "pending"
    design_meta["updated_at"] = now
    design_state["events"].append(
        _event(now, actor, "profile_changed", event_result)
    )
    run_meta["profile"] = profile
    run_meta["updated_at"] = now
    run_state["events"].append(_event(now, actor, "profile_changed", event_result))
    for summary in run_state["stages"]:
        if summary["name"] == "design":
            summary["status"] = design_meta["status"]
            summary["updated_at"] = now
    _observe_run_changes(workspace, run_state, observed_at=now)
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


def _next_pending_stage(run_state: dict[str, Any]) -> str | None:
    """@return The first included pending Stage in canonical Run order."""
    return next(
        (
            str(item.get("name"))
            for item in run_state.get("stages", [])
            if item.get("status") == "pending"
        ),
        None,
    )


def _checkpoint_entry_summary(entry: dict[str, Any], *, kind: str) -> str:
    """@return One concise evidence or finding summary for a Stage checkpoint."""
    label = str(entry.get("label") or entry.get("name") or kind.title())
    if kind == "evidence":
        detail = (
            entry.get("observed_result")
            or entry.get("actual")
            or entry.get("outcome")
            or entry.get("kind")
            or "recorded"
        )
    else:
        detail = (
            entry.get("observation")
            or entry.get("summary")
            or entry.get("code")
            or "recorded"
        )
    return f"{label}: {detail}"


def _checkpoint_data(
    *,
    run_meta: dict[str, Any],
    run_state: dict[str, Any],
    stage: str,
    stage_meta: dict[str, Any],
    stage_state: dict[str, Any],
    stage_path: str,
    run_path: str,
    next_stage_revision: str | None,
) -> dict[str, Any]:
    """
    @brief Project one concise Stage handoff without creating workflow state.
    @return Structured checkpoint summary and human choices for host presentation.
    """
    interaction_mode = run_meta.get("interaction_mode", "checkpoint")
    next_stage = _next_pending_stage(run_state)
    sections = stage_state.get("sections", {})
    outcome = sections.get("outputs_and_handoff")
    if not isinstance(outcome, str) or not outcome.strip() or outcome == "None":
        outcome = (
            sections.get("requested_and_delivered_outcome")
            if stage == "delivery"
            else None
        )
    if not isinstance(outcome, str) or not outcome.strip() or outcome == "None":
        outcome = f"{stage.title()} Stage {stage_meta.get('status', 'recorded')}."

    observed_paths = [
        item.get("path")
        for item in run_state.get("changes_first_observed", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    attachment_paths = [
        item.get("path")
        for item in stage_state.get("attachments", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    changed_artifacts = list(
        dict.fromkeys((run_path, stage_path, *observed_paths, *attachment_paths))
    )
    evidence = [
        _checkpoint_entry_summary(item, kind="evidence")
        for item in stage_state.get("evidence", [])
        if isinstance(item, dict)
    ]
    findings = [
        _checkpoint_entry_summary(item, kind="finding")
        for item in stage_state.get("findings", [])
        if isinstance(item, dict)
    ]
    if stage == "delivery":
        proposed_handoff = "Approve and close the AEGIS Run."
    elif next_stage is not None:
        proposed_handoff = f"Start the {next_stage.title()} Stage."
    else:
        proposed_handoff = "Review the Run state before another operation."
    summary = {
        "outcome": outcome,
        "changed_artifacts": changed_artifacts,
        "evidence": {"count": len(evidence), "items": evidence[:5]},
        "findings": {"count": len(findings), "items": findings[:5]},
        "open_questions": run_state.get("open_questions", "None"),
        "proposed_handoff": proposed_handoff,
    }
    choices: list[dict[str, Any]] = []
    if interaction_mode == "checkpoint":
        if stage == "delivery":
            choices.append(
                {
                    "id": "approve_and_close",
                    "label": "Approve and close.",
                    "mutates_workflow_state": True,
                    "operations": ["decision.add", "stage.complete"],
                    "arguments": {
                        "decision.add": {
                            "value": "approved",
                            "target": "delivery",
                            "approval_source": "developer",
                        }
                    },
                }
            )
        elif next_stage is not None:
            arguments: dict[str, Any] = {"stage_name": next_stage}
            if next_stage_revision is not None:
                arguments["expected_revision"] = next_stage_revision
            choices.append(
                {
                    "id": "continue",
                    "label": "Continue to the proposed next Stage.",
                    "mutates_workflow_state": True,
                    "operation": "stage.start",
                    "arguments": arguments,
                }
            )
        choices.extend(
            (
                {
                    "id": "review",
                    "label": "Review or expand the Stage result.",
                    "mutates_workflow_state": False,
                    "operation": None,
                },
                {
                    "id": "revise",
                    "label": "Revise or reimplement the current or an earlier Stage.",
                    "mutates_workflow_state": True,
                    "operations": ["stage.set_section", "stage.revisit"],
                },
                {
                    "id": "park",
                    "label": "Park the Run.",
                    "mutates_workflow_state": False,
                    "operation": None,
                },
            )
        )
    return {
        "required": interaction_mode == "checkpoint",
        "interaction_mode": interaction_mode,
        "summary": summary,
        "choices": choices,
    }


def _stage_show_next_actions(
    *,
    run_id: str,
    run_meta: dict[str, Any],
    run_state: dict[str, Any],
    stage: str,
    stage_meta: dict[str, Any],
    stage_state: dict[str, Any],
    stage_revision: str,
    next_stage_revision: str | None,
) -> tuple[dict[str, Any], ...]:
    """
    @brief Derive one deterministic atomic continuation for a Stage resume read.
    @param[in] run_id Identity of the inspected Run.
    @param[in] run_meta Current Run metadata.
    @param[in] run_state Current Run state.
    @param[in] stage Name of the inspected Stage.
    @param[in] stage_meta Current inspected Stage metadata.
    @param[in] stage_state Current inspected Stage state.
    @param[in] stage_revision Current inspected Stage revision.
    @param[in] next_stage_revision First later pending Stage revision, when applicable.
    @return Exactly one bounded next action derived from the persisted statuses.
    """
    if run_meta.get("status") != "active":
        return (
            {
                "operation": "run.show",
                "arguments": {"run": run_id},
                "reason": "Read the terminal Run state.",
            },
        )

    current_stage = str(run_meta.get("current_stage", ""))
    if stage != current_stage:
        return (
            {
                "operation": "stage.show",
                "arguments": {"run": run_id, "stage_name": current_stage},
                "reason": "Resume the Run's current Stage.",
            },
        )

    status = stage_meta.get("status")
    interaction_mode = run_meta.get("interaction_mode", "checkpoint")
    if status == "active":
        if (
            stage == "delivery"
            and interaction_mode == "checkpoint"
            and stage_state.get("sections", {}).get("terminal_result")
            in {"achieved", "partially_achieved", "not_achieved"}
        ):
            return ()
        sections = stage_state.get("sections", {})
        allowed_sections = stage_state.get("allowed_sections", [])
        next_section = (
            "restated_ask"
            if stage == "intake"
            and "restated_ask" in allowed_sections
            and sections.get("restated_ask") == "None"
            else next(
                (
                    section
                    for section in allowed_sections
                    if sections.get(section) == "None"
                ),
                None,
            )
        )
        if next_section is not None:
            return (
                {
                    "operation": "stage.set_section",
                    "arguments": {"section": next_section},
                    "reason": f"Record the next {stage.title()} Stage section.",
                },
            )
        return (
            {
                "operation": "stage.complete",
                "arguments": {},
                "reason": f"Evaluate and complete the active {stage.title()} Stage.",
            },
        )

    if status == "pending":
        return (
            {
                "operation": "stage.start",
                "arguments": {
                    "stage_name": stage,
                    "expected_revision": stage_revision,
                },
                "reason": f"Start the pending {stage.title()} Stage.",
            },
        )

    next_stage = _next_pending_stage(run_state)
    if next_stage is not None:
        if interaction_mode == "checkpoint":
            return ()
        return (
            {
                "operation": "stage.start",
                "arguments": {
                    "stage_name": next_stage,
                    "expected_revision": next_stage_revision,
                },
                "reason": f"Start the pending {next_stage.title()} Stage.",
            },
        )
    return (
        {
            "operation": "run.show",
            "arguments": {"run": run_id},
            "reason": "Read the Run state before choosing another operation.",
        },
    )


def _stage_show(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    run_id = inputs.get("run") or _selected_run_id(workspace)
    run_meta, run_state, run_revision, run_path = _load_run(workspace, run_id)
    stage = inputs.get("stage_name") or run_meta["current_stage"]
    if stage not in _STAGES:
        raise UseCaseError("invalid_input", "Stage name is invalid.", field="stage")
    path = f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[stage]}"
    metadata, state, revision = workspace.load_document(path)
    if metadata.get("run_id") != run_id or metadata.get("stage") != stage:
        raise UseCaseError(
            "malformed_state",
            "Stage identity and requested Run or Stage disagree.",
            path=path,
        )
    try:
        selected_run = _selected_run_id(workspace) == run_id
    except UseCaseError:
        selected_run = False
    data, findings, truncated = assemble_stage_resume_context(
        workspace,
        run_id=run_id,
        run_meta=run_meta,
        run_state=run_state,
        stage=stage,
        stage_meta=metadata,
        stage_state=state,
        stage_revision=revision,
        selected_run=selected_run,
    )
    next_stage = _next_pending_stage(run_state)
    next_stage_revision = (
        workspace.revision(
            f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[next_stage]}"
        )
        if stage == run_meta.get("current_stage")
        and metadata.get("status") not in {"active", "pending"}
        and next_stage is not None
        else None
    )
    is_completed_handoff = (
        stage == run_meta.get("current_stage")
        and metadata.get("status") in {"completed", "skipped"}
        and run_meta.get("status") == "active"
    )
    is_delivery_checkpoint = (
        stage == "delivery"
        and stage == run_meta.get("current_stage")
        and metadata.get("status") == "active"
        and state.get("sections", {}).get("terminal_result")
        in {"achieved", "partially_achieved", "not_achieved"}
    )
    if is_completed_handoff or is_delivery_checkpoint:
        data["checkpoint"] = _checkpoint_data(
            run_meta=run_meta,
            run_state=run_state,
            stage=stage,
            stage_meta=metadata,
            stage_state=state,
            stage_path=path,
            run_path=run_path,
            next_stage_revision=next_stage_revision,
        )
    return _done(
        context,
        definition,
        f"{stage.title()} Stage loaded.",
        data=data,
        run_id=run_id,
        stage=stage,
        revision=revision,
        findings=findings,
        artifacts=(
            _artifact(run_path, "read", run_revision, kind="run"),
            _artifact(path, "read", revision, kind="stage"),
        ),
        next_actions=_stage_show_next_actions(
            run_id=run_id,
            run_meta=run_meta,
            run_state=run_state,
            stage=stage,
            stage_meta=metadata,
            stage_state=state,
            stage_revision=revision,
            next_stage_revision=next_stage_revision,
        ),
        truncated=truncated,
        details_ref=path if truncated else None,
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
    actor = _run_actor(run_state)
    stage_meta.update(
        {
            "status": "active",
            "started_at": stage_meta["started_at"] or now,
            "updated_at": now,
        }
    )
    stage_state["events"].append(
        _event(now, actor, "stage_started", f"{requested} became active.")
    )
    if requested == "check":
        stage_state["git_baseline"] = workspace.git_snapshot()
    if requested == "delivery":
        prior_finding_count = 0
        prior_evidence_count = 0
        for summary in run_state["stages"][:-1]:
            prior_path = f"{workspace.config.runs}/{run_id}/{summary['path']}"
            _, prior_state, _ = workspace.load_document(prior_path)
            prior_finding_count += len(prior_state.get("findings", []))
            prior_evidence_count += len(prior_state.get("evidence", []))
        stage_state["sections"]["requested_and_delivered_outcome"] = (
            f"Requested: {run_state['ticket_text']}\nDelivered assessment: pending."
        )
        stage_state["sections"]["evidence_summary"] = (
            _delivery_prior_stage_reference(
                run_id=run_id,
                record_name="evidence",
                record_count=prior_evidence_count,
            )
        )
        stage_state["sections"]["findings_and_residual_risk"] = (
            _delivery_prior_stage_reference(
                run_id=run_id,
                record_name="finding",
                record_count=prior_finding_count,
            )
        )
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
    run_state["events"].append(
        _event(now, actor, "stage_started", f"{requested} became active.")
    )
    run_state["next_action"] = f"Complete the {requested} Stage instruction."
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
        ),
        expected_revisions={
            stage_path: inputs.get("expected_revision", stage_revision),
            run_path: run_revision,
        },
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
    if stage_meta["stage"] == "intake" and section == "restated_ask":
        run_state["intent"] = content
    if stage_meta["stage"] == "alignment" and section == "agreed_scope":
        run_state["scope"] = content
    if section == "outputs_and_handoff":
        run_state["durable_context"] = content
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
    expected_revision = inputs.get("expected_revision")
    if expected_revision is not None and expected_revision != stage_revision:
        raise UseCaseError(
            "state_conflict",
            "The expected Stage revision is stale.",
            field="expected_revision",
            path=stage_path,
            details={"expected": expected_revision, "current": stage_revision},
        )
    stage = stage_meta["stage"]
    latest_delivery_decision = next(
        (
            item
            for item in reversed(stage_state["decisions"])
            if item["target"] == "delivery"
        ),
        None,
    )
    interaction_mode = run_meta.get("interaction_mode", "checkpoint")
    valid_delivery_approval = latest_delivery_decision is not None and (
        latest_delivery_decision.get("value") == "approved"
        and (
            latest_delivery_decision.get("approval_source") == "developer"
            or (
                latest_delivery_decision.get("approval_source")
                == "continuous_delegation"
                and interaction_mode == "continuous"
            )
        )
    )
    if stage == "delivery" and not valid_delivery_approval:
        checkpoint = _checkpoint_data(
            run_meta=run_meta,
            run_state=run_state,
            stage=stage,
            stage_meta=stage_meta,
            stage_state=stage_state,
            stage_path=stage_path,
            run_path=run_path,
            next_stage_revision=None,
        )
        return _error(
            context,
            definition,
            UseCaseError(
                "invalid_transition",
                (
                    'Delivery requires the latest decision.add with target "delivery" '
                    "to have value approved and an authorized approval_source."
                ),
            ),
            data={"checkpoint": checkpoint},
            next_actions=(
                (
                    {
                        "operation": "decision.add",
                        "arguments": {
                            "value": "approved",
                            "target": "delivery",
                            "approval_source": "continuous_delegation",
                        },
                        "reason": (
                            "Record delegated approval under the Run's explicit "
                            "continuous instruction."
                        ),
                    },
                )
                if interaction_mode == "continuous"
                else ()
            ),
        )
    if stage == "delivery" and stage_state["sections"].get("terminal_result") not in {
        "achieved",
        "partially_achieved",
        "not_achieved",
    }:
        return _error(
            context,
            definition,
            UseCaseError(
                "invalid_transition",
                (
                    "Delivery requires stage.set_section with section "
                    '"terminal_result" set to achieved, partially_achieved, or '
                    "not_achieved."
                ),
            ),
            next_actions=(
                {
                    "operation": "stage.set_section",
                    "arguments": {"section": "terminal_result"},
                    "reason": (
                        "Set content to exactly one of achieved, partially_achieved, "
                        "or not_achieved; the caller must choose the truthful "
                        "assessment."
                    ),
                },
            ),
        )
    now = _time(context)
    completion_findings: list[dict[str, Any]] = []
    expectation_evaluation = evaluate_stage_expectations(
        stage=stage,
        profile=run_meta["profile"],
        state=stage_state,
        designated_references=_designated_stage_references(
            workspace,
            run_meta=run_meta,
            stage_meta=stage_meta,
            stage_state=stage_state,
        ),
        continuous_delegation=(
            run_meta.get("interaction_mode", "checkpoint") == "continuous"
        ),
    )
    expectation_findings = expectation_evaluation.findings
    for evaluated in expectation_findings:
        if any(
            _completion_finding_is_current(existing, evaluated)
            for existing in stage_state["findings"]
        ):
            continue
        completion_findings.append(
            {
                "label": _next_finding_label(
                    stage_state["findings"] + completion_findings
                ),
                **evaluated,
                "time": now,
                "artifact": stage_path,
            }
        )
    if stage == "check" and stage_state.get("git_baseline"):
        baseline = stage_state["git_baseline"]
        current = workspace.git_snapshot()
        before_files = baseline.get("working_files", {})
        after_files = current.get("working_files", {})
        before_states = _classification_states(baseline)
        after_states = _classification_states(current)
        changed_paths = sorted(
            path
            for path in (
                set(before_files)
                | set(after_files)
                | set(before_states)
                | set(after_states)
            )
            if (
                before_files.get(path) != after_files.get(path)
                or before_states.get(path, []) != after_states.get(path, [])
            )
            and not any(
                path == str(root) or path.startswith(f"{root}/")
                for root in workspace.config.test_roots
            )
            and _attribution_path(path)
        )
        for changed_path in changed_paths:
            finding = {
                "label": _next_finding_label(
                    stage_state["findings"] + completion_findings
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
            completion_findings.append(
                {
                    "label": _next_finding_label(
                        stage_state["findings"] + completion_findings
                    ),
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
    if stage == "delivery":
        stage_state["sections"]["recorded_state"] = _delivery_recorded_state(
            workspace,
            run_id=run_id,
            run_meta=run_meta,
            run_state=run_state,
            delivery_meta=stage_meta,
            delivery_state=stage_state,
        )
    stage_meta.update({"status": "completed", "updated_at": now, "completed_at": now})
    actor = _run_actor(run_state)
    stage_state["events"].append(
        _event(now, actor, "stage_completed", "Actual Stage state recorded.")
    )
    run_meta["updated_at"] = now
    for summary in run_state["stages"]:
        if summary["name"] == stage:
            summary.update(
                {"status": "completed", "updated_at": now, "result": "Recorded"}
            )
    run_state["events"].append(
        _event(now, actor, "stage_completed", f"{stage} completed.")
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
        run_state["next_action"] = (
            "Wait for the developer's checkpoint choice."
            if run_meta.get("interaction_mode", "checkpoint") == "checkpoint"
            else "Start the next included Stage."
        )
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
        expected_stage=expected_revision,
        extra=extra,
    )
    next_stage = _next_pending_stage(run_state)
    next_stage_revision = (
        workspace.revision(
            f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[next_stage]}"
        )
        if next_stage is not None
        else None
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
    data = {
        "status": "completed",
        "profile": run_meta["profile"],
        "interaction_mode": run_meta.get("interaction_mode", "checkpoint"),
        "evaluated_expectation_count": (
            expectation_evaluation.evaluated_expectation_count
        ),
    }
    if stage != "delivery":
        data["checkpoint"] = _checkpoint_data(
            run_meta=run_meta,
            run_state=run_state,
            stage=stage,
            stage_meta=stage_meta,
            stage_state=stage_state,
            stage_path=stage_path,
            run_path=run_path,
            next_stage_revision=next_stage_revision,
        )
    return _done(
        context,
        definition,
        f"{stage.title()} Stage completed.",
        data=data,
        run_id=run_id,
        stage=stage,
        revision=revisions[stage_path],
        outcome="delivered" if stage == "delivery" else None,
        findings=finding_summaries,
        artifacts=(
            _artifact(stage_path, "updated", revisions[stage_path], kind="stage"),
            _artifact(run_path, "updated", revisions[run_path], kind="run"),
        ),
        next_actions=(
            _stage_show_next_actions(
                run_id=run_id,
                run_meta=run_meta,
                run_state=run_state,
                stage=stage,
                stage_meta=stage_meta,
                stage_state=stage_state,
                stage_revision=revisions[stage_path] or stage_revision,
                next_stage_revision=next_stage_revision,
            )
            if stage != "delivery"
            else ()
        ),
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
    run_state["events"].append(_event(now, actor, "stage_skipped", reason))
    run_state["next_action"] = (
        "Wait for the developer's checkpoint choice."
        if run_meta.get("interaction_mode", "checkpoint") == "checkpoint"
        else "Start the next included Stage."
    )
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
    next_stage = _next_pending_stage(run_state)
    next_stage_revision = (
        workspace.revision(
            f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[next_stage]}"
        )
        if next_stage is not None
        else None
    )
    checkpoint = _checkpoint_data(
        run_meta=run_meta,
        run_state=run_state,
        stage=stage,
        stage_meta=stage_meta,
        stage_state=stage_state,
        stage_path=stage_path,
        run_path=run_path,
        next_stage_revision=next_stage_revision,
    )
    return _done(
        context,
        definition,
        f"{stage.title()} Stage skipped with reason.",
        data={
            "status": "skipped",
            "reason": reason,
            "interaction_mode": run_meta.get("interaction_mode", "checkpoint"),
            "checkpoint": checkpoint,
        },
        run_id=run_id,
        stage=stage,
        revision=revisions[stage_path],
        outcome="skipped",
        next_actions=_stage_show_next_actions(
            run_id=run_id,
            run_meta=run_meta,
            run_state=run_state,
            stage=stage,
            stage_meta=stage_meta,
            stage_state=stage_state,
            stage_revision=revisions[stage_path] or stage_revision,
            next_stage_revision=next_stage_revision,
        ),
    )


def _stage_revisit(
    context: OperationContext, definition: OperationDefinition, inputs: dict[str, Any]
) -> OperationResult:
    workspace = _workspace(context)
    stage = inputs.get("stage_name")
    actor = _require_text(inputs, "actor")
    reason = _require_text(inputs, "reason")
    run_id, run_meta, run_state, run_revision, run_path = (
        _load_selected_run_for_mutation(workspace)
    )
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
    extra: tuple[RepositoryMutation, ...] = ()
    extra_expected: dict[str, str | None] = {}
    previous_stage = run_meta["current_stage"]
    if (
        previous_stage != stage
        and previous_stage in _STAGES
        and _STAGES.index(previous_stage) > _STAGES.index(stage)
    ):
        previous_path = (
            f"{workspace.config.runs}/{run_id}/{_STAGE_FILES[previous_stage]}"
        )
        previous_meta, previous_state, previous_revision = workspace.load_document(
            previous_path
        )
        if previous_meta.get("status") == "active":
            previous_meta.update({"status": "pending", "updated_at": now})
            previous_state["events"].append(
                _event(
                    now,
                    actor,
                    "stage_returned_to_pending",
                    f"{previous_stage.title()} returned to pending because "
                    f"{stage.title()} was revisited.",
                )
            )
            for summary in run_state["stages"]:
                if summary["name"] == previous_stage:
                    summary.update({"status": "pending", "updated_at": now})
            extra = (
                RepositoryMutation(
                    previous_path,
                    workspace.render_document(
                        previous_meta, previous_state, kind="stage"
                    ),
                ),
            )
            extra_expected = {previous_path: previous_revision}
    stage_meta.update({"status": "active", "updated_at": now, "completed_at": ""})
    stage_state["events"].append(_event(now, actor, "stage_revisited", reason))
    run_meta.update({"current_stage": stage, "updated_at": now})
    for summary in run_state["stages"]:
        if summary["name"] == stage:
            summary.update({"status": "active", "updated_at": now, "result": reason})
    run_state["events"].append(_event(now, actor, "stage_revisited", reason))
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
        extra=extra,
        extra_expected=extra_expected,
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
    _require_active_stage(stage_meta)
    now = _time(context)
    entry = dict(inputs)
    entry_findings: list[dict[str, Any]] = []
    entry.pop("expected_revision", None)
    if kind == "evidence":
        for reserved in (
            "red_witness",
            "fingerprints",
            "red_fingerprint_comparison",
            "provenance",
        ):
            entry.pop(reserved, None)
        evidence_kind = entry.get("kind")
        if evidence_kind not in _EVIDENCE_KINDS:
            raise UseCaseError(
                "invalid_input",
                "Evidence kind is invalid.",
                field="kind",
                details={"allowed": sorted(_EVIDENCE_KINDS)},
            )
        if evidence_kind == "manual":
            for field in ("actor", "procedure", "expected", "actual"):
                _require_text(entry, field)
        elif evidence_kind == "automated":
            _validate_automated_evidence(entry)
        entry["provenance"] = "reported"
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
                "invalid_input",
                "Decision value is invalid.",
                field="value",
                details={"allowed": sorted(_DECISIONS)},
            )
        for field in ("actor", "target", "reason"):
            _require_text(entry, field)
        if value == "exception_approved" and not entry.get("alternative_confirmation"):
            raise UseCaseError(
                "invalid_input",
                "Approved exceptions require alternative confirmation.",
                field="alternative_confirmation",
            )
        if value == "approved" and entry.get("target") == "delivery":
            approval_source = entry.get("approval_source")
            if approval_source not in {"developer", "continuous_delegation"}:
                raise UseCaseError(
                    "invalid_input",
                    "Approved Delivery requires a valid approval_source.",
                    field="approval_source",
                    details={
                        "allowed": ["continuous_delegation", "developer"]
                    },
                )
            if (
                approval_source == "continuous_delegation"
                and run_meta.get("interaction_mode", "checkpoint") != "continuous"
            ):
                raise UseCaseError(
                    "invalid_transition",
                    (
                        "Agent-recorded Delivery approval requires explicit "
                        "continuous Run delegation."
                    ),
                    field="approval_source",
                )
    entry["time"] = now
    if kind == "evidence" and entry.get("kind") == "automated":
        entry_findings = _reported_evidence_facts(
            context,
            workspace,
            run_id=run_id,
            stage=stage_meta["stage"],
            entry=entry,
            stage_state=stage_state,
        )
        for index, finding in enumerate(entry_findings):
            finding["label"] = _next_finding_label(
                stage_state["findings"] + entry_findings[:index]
            )
            finding.setdefault("artifact", stage_path)
    collection = {
        "evidence": "evidence",
        "finding": "findings",
        "decision": "decisions",
    }[kind]
    stage_state[collection].append(entry)
    stage_state["findings"].extend(entry_findings)
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
    finding_summaries = tuple(
        {
            "label": finding["label"],
            "code": finding["code"],
            "severity": finding["severity"],
            "summary": finding["observation"],
            "disposition": finding["disposition"],
            "artifact": finding["artifact"],
        }
        for finding in entry_findings
    )
    return _done(
        context,
        definition,
        f"Stage {kind} appended.",
        data={"entry": entry},
        run_id=run_id,
        stage=stage_meta["stage"],
        revision=revisions[stage_path],
        outcome=entry.get("outcome") if kind == "evidence" else None,
        findings=finding_summaries,
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
    _require_active_stage(stage_meta)
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
    content = workspace.read_external_bytes(source)
    suffix = Path(source).suffix.lower()
    if not suffix or not re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
        suffix = ".bin"
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
    stage_state["events"].append(
        _event(now, _run_actor(run_state), "attachment_added", path)
    )
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
    _observe_run_changes(workspace, run_state, observed_at=now)
    _adopt_explicitly_scoped_paths(run_state, change)
    affected_stages = [
        item["name"]
        for item in run_state.get("stages", [])
        if item.get("status") in {"completed", "skipped"}
    ]
    requirement_ids = list(run_meta.get("requirement_ids", []))
    component_ids = list(run_meta.get("component_ids", []))
    finding = {
        "code": "scope_revision_affected_work",
        "severity": "warning",
        "observation": (
            "Scope revision affected_work="
            f"{json.dumps(affected, ensure_ascii=False)}; completed or skipped "
            f"Stages={json.dumps(affected_stages, ensure_ascii=False)}; Run "
            f"requirement_ids={json.dumps(requirement_ids, ensure_ascii=False)}; "
            f"Run component_ids={json.dumps(component_ids, ensure_ascii=False)}."
        ),
        "consequence": (
            "Prior work may require review against the revised scope; existing "
            "Stage status and artifacts remain unchanged."
        ),
        "completed_or_skipped_stages": affected_stages,
        "requirement_ids": requirement_ids,
        "component_ids": component_ids,
        "affected_work": list(affected),
        "scope_before": before,
        "scope_after": after,
        "reason": reason,
        "actor": actor,
        "label": _next_finding_label(stage_state["findings"]),
        "disposition": "open",
        "time": now,
    }
    stage_state["findings"].append(finding)
    stage_state["events"].append(
        _event(now, actor, "scope_revision_impact_recorded", finding["label"])
    )
    stage_meta["updated_at"] = now
    run_state["scope"] = after
    run_state["events"].append(_event(now, actor, "scope_revised", reason))
    run_meta["updated_at"] = now
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
        expected_revisions={
            stage_path: stage_revision,
            run_path: inputs.get("expected_revision", run_revision),
        },
    )
    return _done(
        context,
        definition,
        "Run scope revised; affected work recorded.",
        data=change,
        run_id=run_id,
        stage=run_meta["current_stage"],
        revision=revisions[run_path],
        findings=(finding,),
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
