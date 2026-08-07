#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file cli.py
@brief Stage-oriented, file-first AEGIS 2.1 command-line interface.
@details Exposes only ten grouped command families, two global options, stable
         concise/JSON response fields, and no AEGIS 1.x aliases or mutation
         flags.
"""

# IMPORTS

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from .check_execution import (
    prepare_check_evidence,
    record_check_evidence,
    run_checks_with_outcome,
)
from .components import (
    audit_scope_check,
    load_components,
)
from .config import (
    ConfigurationError,
    GATE_ORDER,
    WorkflowConfig,
    effective_config_dict,
    load_config,
)
from .evidence_forms import (
    apply_evidence_form,
    prepare_evidence_form,
    show_evidence,
)
from .errors import CommandInputError
from .gates import gate_failure_blockers, run_gates_with_outcome
from .invariants import blocking_failures, evaluate
from .models import Graph
from .persistence import PersistenceError
from .report import render_report, write_report
from .requirements import (
    audit_coverage,
    audit_traceability,
    impact,
    list_requirements,
    seed_coverage_waivers,
    show_requirement,
    uncovered_coverable_files,
)
from .repowise import (
    RepoWiseIntegrationError,
    effective_repowise_config,
    inspect_repowise,
)
from .requirement_store import (
    CATEGORY_IDENTITIES,
    RequirementValidationError,
    normalize_repository_path,
)
from .stage_forms import (
    StageOperationError,
    add_stage_item,
    apply_stage,
    bypassed_stages,
    close_stage,
    create_quick_check,
    next_command,
    prepare_stage,
    quick_scope_advisory,
    register_quick_checks,
    show_stage,
)
from .stage_context import build_stage_context
from .store import (
    RunResolutionError,
    abandon_run_id,
    add_waiver,
    init_graph,
    list_runs,
    load_graph,
    repo_root_from,
    resolve_run_id,
    write_current_run,
)
from .waiver_targets import (
    annotate_audit_issues,
    annotate_working_tree,
    collect_waiver_targets,
    waiver_record_statuses,
)
from .waivers import active_waiver, blocker_to_dict
from .verification import (
    quick_bypass_committed,
    read_validation_summary,
    run_verification,
    validation_summary_path,
)
from .working_tree import audit_working_tree

# CONSTANTS

TOP_LEVEL_COMMANDS = (
    "run",
    "stage",
    "requirement",
    "check",
    "evidence",
    "waive",
    "verify",
    "delivery",
    "adoption",
    "config",
)

# PUBLIC API


def main(argv: list[str] | None = None) -> None:
    """
    @brief      Run the AEGIS 2.1 grouped CLI.
    @param[in]  argv Optional argument vector for tests and embedding.
    @return     None.
    @exception  SystemExit For parser, policy, validation, or command failures.
    @exception  OSError If persistence or file I/O fails outside the handled
                policy exceptions.
    """
    normalized = _normalize_global_options(list(argv) if argv is not None else sys.argv[1:])
    parser = _build_parser()
    args = parser.parse_args(normalized)
    root = repo_root_from()
    graph: Graph | None = None
    try:
        if args.group == "config":
            payload = _config_command(root, args)
            _respond(payload, args.json)
            return

        config = load_config(root)
        if args.group == "run" and args.action == "list":
            _respond(_run_list(root), args.json)
            return

        if args.group == "run" and args.action == "start":
            abandoned_warning = _incomplete_run_warning(root)
            profile = "quick" if args.quick else "full"
            graph = init_graph(root, args.kind, "", profile=profile)
            artifact = prepare_stage(root, graph, config)
            details: dict[str, Any] = {
                "run_id": graph.run_id,
                "kind": graph.intent.kind,
            }
            if graph.profile == "quick":
                details["run_profile"] = graph.profile
            if abandoned_warning:
                details["warnings"] = [abandoned_warning]
            _respond(
                _payload(
                    graph,
                    artifact.relative_to(root).as_posix(),
                    next_command(graph, root),
                    **details,
                ),
                args.json,
            )
            return

        if args.group == "run" and args.action == "abandon":
            # Deliberately resolved without loading the graph: this is the
            # exit from a run that has gone wrong, and a run whose `graph.json`
            # is unreadable is the one that most needs it.
            _respond(_run_abandon(root, args), args.json)
            return

        if args.group == "run" and args.action == "select":
            run_id = resolve_run_id(root, args.run_id)
            graph = load_graph(root, run_id)
            if graph.outcome == "abandoned":
                raise CommandInputError(
                    f"run {run_id} was abandoned and cannot be selected. "
                    "Read it without selecting it using "
                    f"`aegis --run {run_id} run status`, list the others with "
                    "`aegis run list`, or start a new run with "
                    "`aegis run start <kind>`."
                )
            write_current_run(root, run_id)
            _respond(_run_status(root, graph), args.json)
            return

        if args.group == "requirement":
            # B20: reading the durable requirement store has nothing to do
            # with runs, so a stale or missing pointer must not wedge it. The
            # run is still resolved when it can be, because the response
            # envelope carries the stage and the next command.
            graph = _optional_active_graph(root, args.run)
            _respond(_requirement_command(root, graph, config, args), args.json)
            return

        graph = _load_active_graph(root, args.run)
        payload, exit_code = _dispatch(root, graph, config, args)
        if exit_code and payload.get("status") == "ok":
            payload["status"] = "failed"
        _respond(payload, args.json)
        if exit_code:
            raise SystemExit(exit_code)
    except (
        CommandInputError,
        ConfigurationError,
        PersistenceError,
        RepoWiseIntegrationError,
        RequirementValidationError,
        RunResolutionError,
        StageOperationError,
    ) as exc:
        stage = graph.stage if graph else "none"
        artifact = _active_artifact(graph)
        payload = {
            "status": "blocked",
            "stage": stage,
            "artifact": artifact,
            "next": next_command(graph, root) if graph else "aegis config validate",
            "error": str(exc),
        }
        if isinstance(exc, ConfigurationError):
            payload.update(exc.to_dict())
        _respond(payload, args.json)
        raise SystemExit(1) from None


# CLI CONSTRUCTION


def _build_parser() -> argparse.ArgumentParser:
    """
    @brief Build the complete hard-break AEGIS 2 parser.
    """
    parser = argparse.ArgumentParser(prog="aegis")
    parser.add_argument("--run", help="explicit run ID; selected run is the default")
    parser.add_argument("--json", action="store_true", help="emit stable JSON")
    groups = parser.add_subparsers(dest="group", required=True)

    run = groups.add_parser("run", help="create and navigate runs")
    run_sub = run.add_subparsers(dest="action", required=True)
    start = run_sub.add_parser("start")
    start.add_argument("kind", choices=("feature", "fix", "change", "adoption"))
    start.add_argument(
        "--quick",
        action="store_true",
        help="use the proportional four-stage profile for fix/change runs",
    )
    run_sub.add_parser("status")
    run_sub.add_parser("context")
    run_sub.add_parser("resume")
    run_sub.add_parser("list")
    select = run_sub.add_parser("select")
    select.add_argument("run_id")
    abandon = run_sub.add_parser("abandon")
    abandon.add_argument("--reason", required=True)

    stage = groups.add_parser("stage", help="operate the current stage forms")
    stage_sub = stage.add_subparsers(dest="action", required=True)
    for action in ("prepare", "show", "apply"):
        stage_sub.add_parser(action)
    stage_add = stage_sub.add_parser("add")
    stage_add.add_argument(
        "--category",
        choices=tuple(CATEGORY_IDENTITIES),
        default="functional",
        help="requirement category; ignored at the check stage",
    )
    stage_close = stage_sub.add_parser("close")
    stage_close.add_argument(
        "--approver",
        help="identity approving this stage; defaults to the git user",
    )

    requirement = groups.add_parser("requirement", help="read durable requirements")
    requirement_sub = requirement.add_subparsers(dest="action", required=True)
    requirement_sub.add_parser("list")
    requirement_show = requirement_sub.add_parser("show")
    requirement_show.add_argument("id")

    check = groups.add_parser("check", help="record deterministic check evidence")
    check_sub = check.add_subparsers(dest="action", required=True)
    check_sub.add_parser("create")
    check_sub.add_parser("register")
    check_sub.add_parser("prepare")
    check_sub.add_parser("record")
    check_run = check_sub.add_parser("run")
    check_run.add_argument("check_ids", nargs="*")

    evidence = groups.add_parser("evidence", help="manage manual evidence forms")
    evidence_sub = evidence.add_subparsers(dest="action", required=True)
    evidence_prepare = evidence_sub.add_parser("prepare")
    evidence_prepare.add_argument("evidence_action", choices=("add", "supersede"))
    evidence_sub.add_parser("apply")
    evidence_sub.add_parser("show")

    waive = groups.add_parser("waive", help="record exact run-local waivers")
    waive_sub = waive.add_subparsers(dest="action", required=True)
    waive_add = waive_sub.add_parser("add")
    waive_add.add_argument("blocker_id")
    waive_add.add_argument("--reason", required=True)
    waive_add.add_argument(
        "--approver",
        help="identity accepting this risk; defaults to the git user",
    )
    waive_sub.add_parser("list")

    verify = groups.add_parser("verify", help="run deterministic verification")
    verify_sub = verify.add_subparsers(dest="action", required=True)
    verify_sub.add_parser("run")
    verify_sub.add_parser("status")
    gates = verify_sub.add_parser("gates")
    gates.add_argument("gate_names", nargs="*", choices=GATE_ORDER)
    verify_sub.add_parser("invariants")
    verify_sub.add_parser("traceability")
    verify_sub.add_parser("coverage")
    verify_impact = verify_sub.add_parser("impact")
    verify_impact.add_argument("paths_file", nargs="?")
    verify_sub.add_parser("working-tree")

    delivery = groups.add_parser("delivery", help="inspect delivery handoff")
    delivery_sub = delivery.add_subparsers(dest="action", required=True)
    delivery_sub.add_parser("show")
    delivery_sub.add_parser("report")

    adoption = groups.add_parser("adoption", help="inspect adoption state")
    adoption_sub = adoption.add_subparsers(dest="action", required=True)
    adoption_sub.add_parser("component-status")
    scope = adoption_sub.add_parser("scope-check")
    scope.add_argument("paths", nargs="+")
    adoption_sub.add_parser("baseline")
    coverage_waivers = adoption_sub.add_parser("coverage-waivers")
    coverage_waivers.add_argument(
        "--write",
        action="store_true",
        help="append the listed paths to the coverage waiver file",
    )

    config = groups.add_parser("config", help="inspect workspace policy")
    config_sub = config.add_subparsers(dest="action", required=True)
    config_sub.add_parser("validate")
    config_sub.add_parser("show")
    return parser


# COMMAND ORCHESTRATION


def _dispatch(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """
    @brief Dispatch one parsed grouped command.
    """
    if args.group == "run":
        if args.action == "context":
            return build_stage_context(root, graph), 0
        return _run_status(root, graph), 0
    if args.group == "stage":
        return _stage_command(root, graph, config, args), 0
    if args.group == "check":
        return _check_command(root, graph, args)
    if args.group == "evidence":
        return _evidence_command(root, graph, args), 0
    if args.group == "waive":
        return _waive_command(root, graph, config, args), 0
    if args.group == "verify":
        return _verify_command(root, graph, config, args)
    if args.group == "delivery":
        if args.action == "report":
            path = write_report(root, graph, render_report(root, graph, config))
            return (
                _payload(
                    graph,
                    path.relative_to(root).as_posix(),
                    next_command(graph, root),
                    report=path.relative_to(root).as_posix(),
                ),
                0,
            )
        return _run_status(root, graph), 0
    return _adoption_command(root, graph, config, args)


def _stage_command(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    @brief Execute one stage lifecycle action.
    """
    if args.action == "prepare":
        artifact = prepare_stage(root, graph, config)
        return _payload(
            graph,
            artifact.relative_to(root).as_posix(),
            next_command(graph, root),
        )
    if args.action == "add":
        artifact = add_stage_item(root, graph, args.category)
        return _payload(
            graph,
            artifact.relative_to(root).as_posix(),
            "aegis stage apply",
        )
    if args.action == "show":
        shown = show_stage(root, graph)
        return _payload(
            graph,
            shown.get("artifact") or "none",
            next_command(graph, root),
            **shown,
        )
    if args.action == "apply":
        record = apply_stage(root, graph, config)
        return _payload(
            graph,
            record.artifact or "none",
            next_command(graph, root),
            revision=record.revision,
            digest=record.digest,
        )
    closing_stage = graph.stage
    approver = _resolve_approver(root, args.approver)
    graph, artifact = close_stage(root, graph, config, approver)
    details: dict[str, Any] = {
        "complete": graph.complete,
        "approver": approver,
        **_quick_run_details(graph),
    }
    if closing_stage == "implementation":
        advisory = quick_scope_advisory(graph, config)
        if advisory is not None:
            details["advisories"] = [advisory]
    return _payload(
        graph,
        artifact.relative_to(root).as_posix() if artifact else "none",
        next_command(graph, root),
        **details,
    )


def _check_command(
    root: Path,
    graph: Graph,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """
    @brief Execute one external or managed check command.
    """
    if args.action == "create":
        path = create_quick_check(root, graph)
        return _payload(
            graph,
            path.relative_to(root).as_posix(),
            "aegis check register",
        ), 0
    if args.action == "register":
        checks = register_quick_checks(root, graph)
        return _payload(
            graph,
            "none",
            next_command(graph, root),
            checks=[asdict(item) for item in checks],
        ), 0
    if args.action == "prepare":
        path = prepare_check_evidence(root, graph)
        return _payload(
            graph,
            path.relative_to(root).as_posix(),
            "aegis check record",
        ), 0
    if args.action == "record":
        evidence = record_check_evidence(root, graph)
    else:
        outcome = run_checks_with_outcome(root, graph, args.check_ids)
        return (
            _payload(
                graph,
                "none",
                next_command(graph, root),
                evidence=[asdict(item) for item in outcome.evidence],
                execution_status=outcome.execution_status,
                executed_count=outcome.executed_count,
                **({"reason": outcome.reason} if outcome.reason else {}),
            ),
            1 if outcome.execution_status == "nothing-ran" else 0,
        )
    return _payload(
        graph,
        "none",
        next_command(graph, root),
        evidence=[asdict(item) for item in evidence],
    ), 0


def _evidence_command(
    root: Path,
    graph: Graph,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    @brief Execute one manual evidence form action.
    """
    if args.action == "prepare":
        path = prepare_evidence_form(root, graph, args.evidence_action)
        return _payload(
            graph,
            path.relative_to(root).as_posix(),
            "aegis evidence apply",
        )
    if args.action == "apply":
        result = apply_evidence_form(root, graph)
        return _payload(graph, "none", next_command(graph, root), result=result)
    result = show_evidence(root, graph)
    return _payload(
        graph,
        result["form"] or "none",
        next_command(graph, root),
        **result,
    )


def _waive_command(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    @brief List or record one exact human-approved run-local waiver.
    @param[in] root Repository root.
    @param[in,out] graph Active graph that owns the waiver record.
    @param[in] config Validated workflow policy used to discover blockers.
    @param[in] args Parsed waiver action and values.
    @return Stable waiver response payload.
    @exception CommandInputError If the reason/target is invalid or inactive.
    @exception ValueError If the target already gained an active waiver of the
               same state underneath this call.
    @exception GraphConflictError If the graph changed underneath this call.
    @exception PersistenceError If journal integrity prevents a complete record.
    @exception OSError If persistence fails.
    """
    expected_source_digest = getattr(graph, "_source_digest", None)
    targets = collect_waiver_targets(root, graph, config)
    if args.action == "list":
        history = waiver_record_statuses(graph, targets)
        return _payload(
            graph,
            "none",
            next_command(graph, root),
            active_waivers=[
                item for item in history if item["status"] == "active"
            ],
            # Called out beside the active list rather than left for the reader
            # to find in the history: a waiver that stops applying used to just
            # disappear from `active_waivers`, so the blocker it had covered
            # came back with nothing anywhere saying why.
            stale_waivers=[
                item for item in history if item["status"] == "stale"
            ],
            waiver_history=history,
            eligible_blockers=[
                blocker_to_dict(blocker, graph) for blocker in targets
            ],
        )

    reason = args.reason.strip()
    if not reason:
        raise CommandInputError("waiver reason must not be empty")
    blocker_id = args.blocker_id.strip()
    if not blocker_id:
        raise CommandInputError("waiver blocker ID must be one exact non-empty ID")
    target = next(
        (item for item in targets if item.id == blocker_id),
        None,
    )
    if target is None:
        raise CommandInputError(
            "blocker is not currently active or is not waivable: "
            f"{blocker_id}"
        )
    if active_waiver(graph, target) is not None:
        raise CommandInputError(
            f"blocker already has an active waiver: {blocker_id}"
        )
    waiver = add_waiver(
        root,
        graph,
        target.id,
        reason,
        target.state_digests,
        approver=_resolve_approver(root, args.approver),
        expected_source_digest=expected_source_digest,
    )
    return _payload(
        graph,
        "none",
        next_command(graph, root),
        waiver=asdict(waiver),
        blocker=blocker_to_dict(target, graph),
    )


def _verify_command(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """
    @brief Execute one deterministic verification action.
    """
    if args.action == "run":
        return _verify_run(root, graph, config)
    if args.action == "status":
        return _verify_status(root, graph)
    if args.action == "gates":
        return _verify_gates(root, graph, config, args)
    if args.action == "invariants":
        return _verify_invariants(root, graph, config)
    if args.action in {"traceability", "coverage"}:
        return _verify_audit(root, graph, config, args)
    if args.action == "impact":
        return _verify_impact(root, graph, config, args)
    return _verify_working_tree(root, graph, config)


def _verify_run(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
) -> tuple[dict[str, Any], int]:
    """@brief Execute the complete deterministic verification sequence."""
    summary, code = run_verification(root, graph, config)
    return (
        _payload(
            graph,
            validation_summary_path(root, graph).relative_to(root).as_posix(),
            next_command(graph, root),
            verification=summary,
        ),
        code,
    )


def _verify_status(root: Path, graph: Graph) -> tuple[dict[str, Any], int]:
    """
    @brief Report the durable validation summary without re-running it.
    @details The exit code mirrors `verify run`'s verdict on the summary being
             reported, so an agent polling this command to decide whether it
             may proceed gets the same answer the run itself gave. A summary
             written before 2.1.0 carries no `status`; it is reported as it
             always was rather than guessed at.
    """
    summary = read_validation_summary(root, graph)
    return (
        _payload(
            graph,
            validation_summary_path(root, graph).relative_to(root).as_posix(),
            next_command(graph, root),
            verification=summary,
        ),
        1 if summary.get("status") == "failed" else 0,
    )


def _verify_gates(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """@brief Execute the selected (or complete) gate set and report modes."""
    outcome = run_gates_with_outcome(
        root,
        graph.run_id,
        config,
        args.gate_names or None,
    )
    graph = load_graph(root, graph.run_id)
    modes = {
        name: getattr(config.gates, name).mode
        for name in (args.gate_names or GATE_ORDER)
    }
    waived_gates = [
        blocker_to_dict(blocker, graph)
        for blocker in gate_failure_blockers(
            graph,
            config,
            args.gate_names or None,
        )
        if active_waiver(graph, blocker) is not None
    ]
    details: dict[str, Any] = {
        "gates": modes,
        "execution_status": outcome.execution_status,
        "executed_count": outcome.executed_count,
    }
    if outcome.reason:
        details["reason"] = outcome.reason
    if waived_gates:
        details["waived_gates"] = waived_gates
    return (
        _payload(graph, "none", next_command(graph, root), **details),
        outcome.exit_code,
    )


def _verify_invariants(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
) -> tuple[dict[str, Any], int]:
    """@brief Evaluate every configured invariant and report blocking failures."""
    results = evaluate(root, graph, config)
    return (
        _payload(
            graph,
            "none",
            next_command(graph, root),
            invariants=[item.to_dict() for item in results],
        ),
        1 if blocking_failures(results) else 0,
    )


def _verify_audit(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """
    @brief Run the traceability or coverage audit, skipping quick runs.
    @details A disabled coverage policy used to return the same `issues: []`
             a clean enforced audit returns, so the one command an operator
             runs to review coverage could not tell "nothing wrong" from
             "switched off". It now reports the same `audit_status` shape the
             quick-run bypass already uses.
    """
    if graph.profile == "quick":
        return (
            _payload(
                graph,
                "none",
                next_command(graph, root),
                audit_status="not-applicable",
                issues=[
                    {
                        "status": "not-applicable",
                        "message": "Not applicable - quick run.",
                    }
                ],
            ),
            0,
        )
    if args.action == "coverage" and config.coverage.mode == "disabled":
        return (
            _payload(
                graph,
                "none",
                next_command(graph, root),
                audit_status="not-enforced",
                issues=[
                    {
                        "status": "not-enforced",
                        "message": (
                            "Not enforced - traceability.coverage.mode is "
                            "disabled."
                        ),
                    }
                ],
            ),
            0,
        )
    issues = (
        audit_traceability(root, config)
        if args.action == "traceability"
        else audit_coverage(root, config)
    )
    serialized, blockers = annotate_audit_issues(
        args.action,
        issues,
        graph,
    )
    return (
        _payload(
            graph,
            "none",
            next_command(graph, root),
            issues=serialized,
        ),
        1 if blockers else 0,
    )


def _verify_impact(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """@brief Report the change-impact set for the configured or given paths."""
    paths = _read_paths_file(root, args.paths_file) if args.paths_file else None
    report = impact(root, paths, config=config)
    return _payload(graph, "none", next_command(graph, root), impact=report), 0


def _verify_working_tree(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
) -> tuple[dict[str, Any], int]:
    """@brief Audit the working tree against the configured write policy."""
    report, blockers = annotate_working_tree(
        audit_working_tree(root, config, graph),
        graph,
        root,
    )
    return (
        _payload(graph, "none", next_command(graph, root), working_tree=report),
        1 if blockers else 0,
    )


def _adoption_command(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """
    @brief Preserve adoption inspection commands under the grouped surface.
    """
    manifest = load_components(root, config.component_manifest)
    if args.action == "component-status":
        components = {
            name: asdict(component)
            for name, component in sorted(manifest.components.items())
        }
        return (
            _payload(
                graph,
                config.component_manifest,
                next_command(graph, root),
                components=components,
            ),
            0,
        )
    if args.action == "scope-check":
        guard = config.component_baseline_guard
        issues = audit_scope_check(root, args.paths, config)
        return (
            _payload(
                graph,
                config.component_manifest,
                next_command(graph, root),
                enforcement=(
                    "not-enforced"
                    if guard.minimum_completion_level is None
                    else "enforced"
                ),
                minimum_completion_level=guard.minimum_completion_level,
                issues=[asdict(item) for item in issues],
            ),
            1 if any(item.blocking for item in issues) else 0,
        )
    if args.action == "coverage-waivers":
        return _adoption_coverage_waivers(root, graph, config, args), 0
    baseline = {
        "minimum_completion_level": (
            config.component_baseline_guard.minimum_completion_level
        ),
        "component_count": len(manifest.components),
        "report_root": config.adoption_report_root,
    }
    return (
        _payload(
            graph,
            config.component_manifest,
            next_command(graph, root),
            baseline=baseline,
        ),
        0,
    )


def _adoption_coverage_waivers(
    root: Path,
    graph: Graph,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    @brief Offer, and on request write, the legacy coverage-waiver seed set.
    @details Reports the modules the coverage policy finds uncovered and
             writes none of them without `--write`. The waiver file is
             documented for exactly this case but ships empty, so enabling
             `traceability.coverage.mode` after an adoption run used to mean
             transcribing one path per legacy module by hand at the moment the
             operator is trying to turn enforcement on. Disabled mode has no
             coverable roots to enumerate - the schema forbids them - so it
             says so rather than reporting an empty list as a clean answer.
    """
    uncovered = uncovered_coverable_files(root, config)
    details: dict[str, Any] = {
        "coverage_mode": config.coverage.mode,
        "uncovered": uncovered,
        "written": False,
    }
    if config.coverage.mode == "disabled":
        details["note"] = (
            "traceability.coverage.mode is disabled and has no coverable "
            "roots; seed this file after enabling coverage, before the first "
            "enforced audit."
        )
    if args.write and uncovered:
        details["written"] = True
        details["waiver_file"] = seed_coverage_waivers(
            root,
            config,
            uncovered,
            graph.run_id,
        )
    return _payload(
        graph,
        details.get("waiver_file", "none"),
        next_command(graph, root),
        coverage_waivers=details,
    )


def _config_command(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    """
    @brief Validate schema-3 policy and optional integration configuration.
    @details `next` used to be the literal `aegis run start feature`. Five
             documents order the agent to run `config validate` at the start of
             every skill, and the protocol trains it to obey `next` verbatim —
             so an agent bootstrapping a skill midway through a run was told by
             AEGIS itself to start a second run. It now reports the selected
             run's own next command, and falls back to starting a run only when
             there is genuinely no live run to continue.
    """
    config = load_config(root)
    data = effective_config_dict(config)
    integration = effective_repowise_config(root)
    inspection = inspect_repowise(root)
    graph = _optional_active_graph(root, getattr(args, "run", None))
    return {
        "status": "ok",
        "stage": graph.stage if graph and not graph.complete else "none",
        "artifact": ".agentic/workflow.toml",
        "next": (
            next_command(graph, root)
            if graph is not None and not graph.complete
            else "aegis run start feature"
        ),
        **(
            {
                "config": data,
                "integrations": {
                    "repowise": {
                        **integration,
                        "status": inspection.status,
                        "warnings": list(inspection.warnings),
                    }
                },
            }
            if args.action == "show"
            else {
                "schema_version": 3,
                "integration_schema_versions": {"repowise": 1},
            }
        ),
    }


# LOCAL HELPERS


def _run_status(root: Path, graph: Graph) -> dict[str, Any]:
    """
    @brief Build status/resume output from authoritative run state.
    @details An abandoned run reports exactly what it is: `complete: true`,
             `outcome: "abandoned"`, and `next: "none"` — the same shape a run
             that reached delivery reports, distinguished by `outcome`. The
             field is omitted entirely for every other run, so nothing changes
             for a run that ended normally or is still live.
    """
    shown = show_stage(root, graph) if not graph.complete else {}
    evidence = [
        {
            "id": item.id,
            "kind": item.kind,
            "result": item.result,
            "status": item.status,
            "check_id": item.check_id,
        }
        for item in graph.evidence
    ]
    return _payload(
        graph,
        shown.get("artifact") or "none",
        next_command(graph, root),
        run_id=graph.run_id,
        complete=graph.complete,
        readiness=shown,
        evidence=evidence,
        **({"outcome": graph.outcome} if graph.outcome else {}),
        **_quick_run_details(graph),
    )


def _run_list(root: Path) -> dict[str, Any]:
    """
    @brief Enumerate every run in the repository without resolving one.
    @param[in] root Repository root.
    @return Stable response carrying one row per discoverable run.
    @details Deliberately run-independent: this is the command an operator
             reaches for precisely when they do not know which run they have,
             so it must work with a missing, stale, or unreadable pointer.
    """
    runs = list_runs(root)
    selected = next((item["run_id"] for item in runs if item["selected"]), None)
    live = [
        item["run_id"]
        for item in runs
        if not item["complete"] and item["stage"] != "unreadable"
    ]
    if selected is not None:
        exact_next = "aegis run status"
    elif len(live) == 1:
        exact_next = f"aegis run select {live[0]}"
    else:
        exact_next = "aegis run start feature"
    return {
        "status": "ok",
        "stage": "none",
        "artifact": ".agentic/runs",
        "next": exact_next,
        "runs": runs,
    }


def _run_abandon(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    """
    @brief End a run without driving it through delivery.
    @param[in] root Repository root.
    @param[in] args Parsed action carrying the mandatory reason.
    @return Stable response naming the abandoned run, carrying `graph_error`
            when the run was ended without a readable graph.
    @details The run is addressed by ID, not by a loaded graph, so a corrupt
             or schema-invalid `graph.json` does not remove the only exit a run
             has. The response is assembled directly rather than through
             `_payload` for the same reason: there may be no graph to describe.
    @exception CommandInputError If the reason is empty.
    @exception RunResolutionError If no run is selected or the ID is unknown.
    @exception StageOperationError If a readable run has already ended.
    """
    reason = args.reason.strip()
    if not reason:
        raise CommandInputError("abandon reason must not be empty")
    run_id = resolve_run_id(root, args.run, verify_graph=False)
    row = abandon_run_id(root, run_id, reason)
    return {
        "status": "ok",
        "stage": row["stage"],
        "artifact": "none",
        "next": "aegis run start <kind>",
        "reason": reason,
        **row,
    }


def _requirement_command(
    root: Path,
    graph: Graph | None,
    config: WorkflowConfig,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """
    @brief Read the durable requirement register, with or without a run.
    @param[in] root Repository root.
    @param[in] graph Selected run, or `None` when none could be resolved.
    @param[in] config Validated workflow configuration.
    @param[in] args Parsed requirement action.
    @return Stable response carrying the requested requirement records.
    @exception RequirementValidationError If the register is malformed.
    """
    records = (
        [show_requirement(root, args.id, config)]
        if args.action == "show"
        else list_requirements(root, config=config)
    )
    artifact = (
        (records[0].source_file if records else None)
        if args.action == "show"
        else config.requirement_roots[0]
    )
    requirements = [item.to_dict() for item in records]
    if graph is None:
        return {
            "status": "ok",
            "stage": "none",
            "artifact": artifact or "none",
            "next": "aegis run list",
            "requirements": requirements,
        }
    return _payload(
        graph,
        artifact or "none",
        next_command(graph, root),
        requirements=requirements,
    )


def _incomplete_run_warning(root: Path) -> str | None:
    """
    @brief Warn when `run start` is about to leave a live run behind.
    @param[in] root Repository root.
    @return Warning text naming the run and how to recover or end it, or
            `None` when the worktree selects no live run.
    @details `run start` repoints the worktree silently. Nothing wedges — the
             run is recoverable — but only if the operator still knows the ID,
             which is exactly what they lose by not being told.
    @exception None All resolution failures mean there is nothing to warn about.
    """
    try:
        current = next(
            (item for item in list_runs(root) if item["selected"]),
            None,
        )
    except OSError:
        return None
    if current is None or current["complete"]:
        return None
    return (
        f"run {current['run_id']} is still incomplete at stage "
        f"{current['stage']} and is no longer selected. Return to it with "
        f"`aegis run select {current['run_id']}`, or end it with "
        f"`aegis --run {current['run_id']} run abandon --reason \"<text>\"`."
    )


def _resolve_approver(root: Path, explicit: str | None) -> str:
    """
    @brief Resolve the identity to attribute one approval to.
    @param[in] root Repository root, used as the git working directory.
    @param[in] explicit Value of `--approver`, when the operator gave one.
    @return The explicit value, else `Name <email>` from git, else "human".
    @details Approvals were recorded as the literal "human" and could not be
             attributed to anyone, which makes a waiver useless as evidence of
             who accepted a risk. Git already knows who is working, so it is
             the default; "human" survives as the fallback so a repository
             with no configured identity behaves exactly as before.
    @exception CommandInputError If `--approver` was given but is empty.
    """
    if explicit is not None:
        approver = explicit.strip()
        if not approver:
            raise CommandInputError("approver must not be empty")
        return approver
    name = _git_config_value(root, "user.name")
    email = _git_config_value(root, "user.email")
    if name and email:
        return f"{name} <{email}>"
    return name or email or "human"


def _git_config_value(root: Path, key: str) -> str:
    """
    @brief Read one git configuration value, tolerating every failure.
    @param[in] root Repository root used as the working directory.
    @param[in] key Configuration key to read.
    @return The trimmed value, or an empty string when git reports nothing.
    @exception None Git being absent, failing, or unset is not an error here.
    """
    try:
        completed = subprocess.run(
            ["git", "config", "--get", key],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _quick_run_details(graph: Graph) -> dict[str, Any]:
    """
    @brief Build quick-only status fields after human intake approval.
    @param[in] graph Active run graph.
    @return Empty mapping for full runs, otherwise profile and bypass state.
    """
    if graph.profile != "quick":
        return {}
    details: dict[str, Any] = {"run_profile": "quick"}
    if quick_bypass_committed(graph):
        details.update(
            {
                "bypass_status": "bypassed",
                "bypassed_stages": bypassed_stages(graph),
            }
        )
    return details


def _load_active_graph(root: Path, explicit: str | None) -> Graph:
    """@brief Resolve and load either the explicit or selected run."""
    run_id = resolve_run_id(root, explicit)
    return load_graph(root, run_id)


def _optional_active_graph(root: Path, explicit: str | None) -> Graph | None:
    """
    @brief Resolve the active run for a command that does not require one.
    @param[in] root Repository root.
    @param[in] explicit Value of the global `--run`, when given.
    @return The resolved graph, or `None` when no run resolves.
    @details Used only by read-only commands. Commands that mutate state keep
             going through :func:`_load_active_graph`, so an unresolvable run
             is still a hard failure wherever a run genuinely matters.
    @exception None Resolution failures are the answer, not an error.
    """
    try:
        return _load_active_graph(root, explicit)
    except (RunResolutionError, StageOperationError, PersistenceError, OSError):
        return None


def _payload(
    graph: Graph,
    artifact: str,
    exact_next: str,
    **details: Any,
) -> dict[str, Any]:
    """@brief Construct the stable command-response envelope."""
    return {
        "status": "ok",
        "stage": graph.stage,
        "artifact": artifact or "none",
        "next": exact_next,
        **details,
    }


def _respond(payload: dict[str, Any], json_output: bool) -> None:
    """
    @brief Emit stable JSON or concise line-oriented text.
    @details The non-`--json` surface used to serialize nested values on one
             line, which for `verify run` meant a large unwrapped JSON line —
             unreadable in a terminal, and so no different from `--json` except
             worse. Nested values are now indented under their key. Scalars keep
             their exact one-line `key: value` shape, which is what every
             existing reader parses.
    """
    if json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    if payload.get("execution_status") == "nothing-ran":
        print(f"NOTHING RAN: {payload.get('reason', 'No reason recorded.')}")
    for key in ("status", "stage", "artifact", "next"):
        print(f"{key}: {payload.get(key, 'none')}")
    for key, value in payload.items():
        if key in {"status", "stage", "artifact", "next"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            print(f"{key}: {value}")
            continue
        print(f"{key}:")
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        for line in rendered.splitlines():
            print(f"  {line}")


def _normalize_global_options(argv: list[str]) -> list[str]:
    """
    @brief      Accept the two global options before or after grouped commands.
    @param[in]  argv Raw argument vector.
    @return     Equivalent vector with global options moved before the group.
    """
    globals_: list[str] = []
    command: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--json":
            globals_.append(token)
        elif token == "--run":
            if index + 1 >= len(argv):
                command.append(token)
            else:
                globals_.extend((token, argv[index + 1]))
                index += 1
        elif token.startswith("--run="):
            globals_.append(token)
        else:
            command.append(token)
        index += 1
    return [*globals_, *command]


def _read_paths_file(root: Path, value: str) -> list[str]:
    """
    @brief Read newline-delimited impact paths from a repository file.
    @param[in] root Repository root.
    @param[in] value Parsed repository-relative paths-file value.
    @return Non-comment, non-empty paths from the referenced file.
    @exception CommandInputError If the file or one of its paths is invalid.
    @exception OSError If the paths file cannot be read.
    """
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise CommandInputError(
            "paths file must be repository-relative"
        ) from None
    if not path.is_file():
        raise CommandInputError(f"paths file does not exist: {value}")
    paths: list[str] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            paths.append(
                normalize_repository_path(stripped, allow_glob=False)
            )
        except ValueError as exc:
            raise CommandInputError(
                f"invalid path in {value} at line {line_number}: {exc}"
            ) from exc
    return paths


def _active_artifact(graph: Graph | None) -> str:
    """@brief Return the graph's currently recorded artifact for errors."""
    if not graph:
        return "none"
    record = graph.stage_records.get(graph.stage)
    return record.artifact if record and record.artifact else "none"


# END OF FILE
