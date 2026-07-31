#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file repair.py
@brief Transactional repair of missing, modified, and generated managed files.
@details Missing payload files are restorable only when payload bytes match the
         original hash in the install manifest. Modified files require an
         explicit keep/take/sidecar decision. Generated configuration is
         regenerated from stored or supplied answers. Verification precedes
         the manifest-last commit, and every failure rolls back.
"""

# IMPORTS

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import IO, Any, Mapping

from ..consent import ConsentDecision, mutation_consent
from ..io.answers import AnswersFileError, load_answers_file
from ..io.envelope import EXIT_NEEDS_INPUT, EXIT_OK, EXIT_OPERATIONAL, EXIT_VALIDATION
from ..io.prompts import ConsoleAsker, FieldSpec
from ..payload.copier import ensure_executable
from ..payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    ManifestState,
    compute_drift,
    hash_file,
    load_manifest,
    resolve_managed_path,
    write_manifest,
)
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..repo.workflow_toml import generate_workflow_toml
from ..repowise import (
    INTEGRATION_RELATIVE_PATH,
    RepoWiseSettings,
    _integration_text,
)
from ..transaction import FileTransaction
from ..verification import smoke_reverify
from ..version import WIZARD_VERSION
from ._shared import (
    CommandOptions,
    PAYLOAD_VALIDATION_ERRORS,
    WORKFLOW_TOML_RELATIVE_PATH,
    emit_command_output,
    locate_validated_payload,
    recover_transactions_or_emit,
    render_pending_recovery,
    sidecar_relative_path,
)
from .configure import CONFIG_KEYS, stored_answers

# CONSTANTS

_DECISIONS = frozenset({"keep-local", "take-payload", "write-new"})
_CONTROL_KEYS = frozenset({"repair_conflicts", "run_smoke"})


# HELPER FUNCTIONS


def _render_repair_human(
    stream: IO[str],
    plan: Mapping[str, Any] | None,
    result: Mapping[str, Any] | None,
) -> None:
    """
    @brief Render repair's command-specific human plan/result lines.
    @details Deliberately repair-only (the shared core lives in
             :func:`waegis.commands._shared.emit_command_output`): the plan is
             summarized as restore/resolve/regenerate counts and the result as
             the repair verdict, which no other command emits.
    """
    if plan is not None:
        render_pending_recovery(stream, plan)
        stream.write(
            "Repair plan: "
            f"restore {len(plan.get('restore_missing', []))}, "
            f"resolve {len(plan.get('modified', []))}, "
            f"regenerate {len(plan.get('regenerate', []))}.\n"
        )
    if result is not None and result.get("repaired"):
        stream.write("Repair completed and verified.\n")


def _emit(
    stream: IO[str],
    *,
    as_json: bool,
    status: str,
    exit_code: int,
    plan: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
    messages: tuple[str, ...] = (),
) -> int:
    """
    @brief Emit repair output and return the standardized exit code.
    """
    return emit_command_output(
        stream,
        "repair",
        as_json=as_json,
        status=status,
        exit_code=exit_code,
        plan=plan,
        result=result,
        messages=messages,
        render_human=_render_repair_human,
    )


def _decision(raw: Any) -> str:
    """@brief Normalize one repair conflict decision."""
    value = str(raw).strip().lower()
    if value not in _DECISIONS:
        raise ValueError("choose one of: keep-local, take-payload, write-new")
    return value


def _configuration_answers(
    manifest_configuration: Mapping[str, Any], supplied: Mapping[str, Any]
) -> dict[str, Any]:
    """@brief Merge stored and explicitly supplied generator answers."""
    answers = stored_answers(manifest_configuration)
    answers.update({key: value for key, value in supplied.items() if key in CONFIG_KEYS})
    return answers


# EXPORTED FUNCTIONS / PUBLIC API


@dataclass(frozen=True)
class RepairContext:
    """@brief Resolved public boundary for repair command phases."""
    repo_path: Path
    options: CommandOptions


@dataclass(frozen=True)
class RepairResolved:
    """@brief Validated repair inputs before decision planning."""
    context: RepairContext
    pending: tuple[str, ...]
    recovered: tuple[str, ...]
    manifest: Any
    supplied: dict[str, Any]
    payload_root: Path
    inventory: Any
    drift: Any


@dataclass(frozen=True)
class RepairPlan:
    """@brief Fully resolved repair plan awaiting consent."""
    resolved: RepairResolved
    decisions: dict[str, str]
    asker: ConsoleAsker | None
    configuration_answers: dict[str, Any]
    regenerate: list[str]
    repowise_configuration: Any
    plan_data: dict[str, Any]
    unresolved: list[str]
    mutations: bool


@dataclass(frozen=True)
class RepairOutcome:
    """@brief Successful repair transaction awaiting final reporting."""
    plan: RepairPlan


@dataclass
class RepairApplyState:
    """@brief Mutable manifest state owned by one repair transaction."""
    skipped: set[str]
    files: dict[str, Any]
    configuration: dict[str, Any]
    generated_files: dict[str, Any]


def _repair_emit(context: RepairContext, **kwargs: Any) -> int:
    """@brief Bind repair output options for phase-local early returns."""
    return _emit(context.options.stream, as_json=context.options.as_json, **kwargs)


def _validate_repair(context: RepairContext) -> int | RepairResolved:
    """@brief Validate repository, recovery, manifest, answers, and payload."""
    options = context.options
    if not context.repo_path.is_dir():
        return _repair_emit(
            context, status="error", exit_code=EXIT_OPERATIONAL,
            messages=(f"--repo path does not exist or is not a directory: {context.repo_path}",),
        )
    recovery = recover_transactions_or_emit(
        context.repo_path, dry_run=options.dry_run, yes=options.yes,
        recovery_asker=ConsoleAsker(stdin=options.stdin, stdout=options.stream)
        if not options.non_interactive and options.stdin is not None else None,
        emit=lambda **kwargs: _repair_emit(context, **kwargs),
    )
    if isinstance(recovery, int):
        return recovery
    pending, recovered = recovery
    load = load_manifest(context.repo_path)
    if load.state is not ManifestState.VALID or load.manifest is None:
        return _repair_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("repair requires a valid current install manifest",),
        )
    supplied: dict[str, Any] = {}
    if options.answers_path is not None:
        try:
            supplied = load_answers_file(options.answers_path)
        except AnswersFileError as exc:
            return _repair_emit(
                context, status="failed", exit_code=EXIT_VALIDATION,
                messages=(str(exc),),
            )
    unknown = sorted(set(supplied) - CONFIG_KEYS - _CONTROL_KEYS)
    if unknown:
        return _repair_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("unrecognized answer key(s): " + ", ".join(unknown),),
        )
    try:
        payload_root, inventory, _payload_version = locate_validated_payload(options.payload)
    except PAYLOAD_VALIDATION_ERRORS as exc:
        return _repair_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )
    drift = compute_drift(context.repo_path, load.manifest)
    unavailable = _unavailable_missing(load.manifest, inventory, drift)
    if unavailable:
        return _repair_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            result={"unavailable": unavailable},
            messages=("payload bytes do not match recorded originals for: " + ", ".join(unavailable),),
        )
    return RepairResolved(
        context, tuple(pending), tuple(recovered), load.manifest, supplied,
        payload_root, inventory, drift,
    )


def _unavailable_missing(manifest: Any, inventory: Any, drift: Any) -> list[str]:
    """@brief Return missing paths whose original payload bytes are unavailable."""
    unavailable: list[str] = []
    for relative in drift.missing:
        source_entry = inventory.entries.get(relative)
        if source_entry is None or source_entry.sha256 != manifest.files[relative].sha256:
            unavailable.append(relative)
    return unavailable


def _resolve_repair_decisions(
    resolved: RepairResolved,
) -> int | tuple[dict[str, str], ConsoleAsker | None, list[str]]:
    """@brief Resolve modified-file decisions in original prompt order."""
    context = resolved.context
    raw_table = resolved.supplied.get("repair_conflicts", {})
    if not isinstance(raw_table, Mapping):
        return _repair_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("repair_conflicts must be a path-to-decision mapping",),
        )
    asker = (
        None if context.options.non_interactive or context.options.stdin is None
        else ConsoleAsker(
            stdin=context.options.stdin, stdout=context.options.stream
        )
    )
    decisions: dict[str, str] = {}
    try:
        for relative in resolved.drift.modified:
            if relative in raw_table:
                decisions[relative] = _decision(raw_table[relative])
            elif asker is not None:
                decisions[relative] = asker.ask_field(FieldSpec(
                    key=f"repair:{relative}",
                    description=f"Managed file {relative} was modified. "
                    "Choose keep-local, take-payload, or write-new.",
                    example="keep-local", default="keep-local",
                    validator=_decision,
                    choices=("keep-local", "take-payload", "write-new"),
                ))
    except ValueError as exc:
        return _repair_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )
    unresolved = [
        path for path in resolved.drift.modified if path not in decisions
    ]
    return decisions, asker, unresolved


def _validate_repair_decision_bytes(
    resolved: RepairResolved, decisions: Mapping[str, str],
) -> int | None:
    """@brief Validate payload bytes needed by take/write decisions."""
    unavailable: list[str] = []
    for relative, decision in decisions.items():
        if decision == "keep-local":
            continue
        source_entry = resolved.inventory.entries.get(relative)
        if source_entry is None or source_entry.sha256 != resolved.manifest.files[relative].sha256:
            unavailable.append(relative)
    if not unavailable:
        return None
    unique = sorted(set(unavailable))
    return _repair_emit(
        resolved.context, status="failed", exit_code=EXIT_VALIDATION,
        result={"unavailable": unique},
        messages=("payload bytes do not match recorded originals for: " + ", ".join(unique),),
    )


def _repair_generation(
    resolved: RepairResolved,
) -> tuple[dict[str, Any], list[str], Any, bool]:
    """@brief Resolve generated-file regeneration and completeness."""
    answers = _configuration_answers(
        resolved.manifest.configuration, resolved.supplied
    )
    generated_metadata = resolved.manifest.configuration.get("generated_files")
    regenerate: list[str] = []
    for relative in resolved.manifest.generated:
        target = resolve_managed_path(resolved.context.repo_path, relative)
        metadata = (
            generated_metadata.get(relative)
            if isinstance(generated_metadata, Mapping) else None
        )
        expected = metadata.get("sha256") if isinstance(metadata, Mapping) else None
        if not target.is_file() or not isinstance(expected, str) or hash_file(target).sha256 != expected:
            regenerate.append(relative)
    repowise = resolved.manifest.configuration.get("repowise")
    incomplete = _repair_generation_incomplete(regenerate, answers, repowise)
    return answers, regenerate, repowise, incomplete


def _repair_generation_incomplete(
    regenerate: list[str], answers: Mapping[str, Any], repowise: Any,
) -> bool:
    """@brief Check whether supported generated files have enough metadata."""
    supported = {WORKFLOW_TOML_RELATIVE_PATH, INTEGRATION_RELATIVE_PATH}
    workflow_keys = (
        "source_roots", "test_roots", "language", "gate_build_cmds",
        "gate_typecheck_cmds", "gate_lint_cmds", "gate_test_cmds",
        "gate_security_cmds", "alignment_enabled",
    )
    workflow_incomplete = (
        WORKFLOW_TOML_RELATIVE_PATH in regenerate
        and not all(key in answers for key in workflow_keys)
    )
    repowise_incomplete = (
        INTEGRATION_RELATIVE_PATH in regenerate
        and (
            not isinstance(repowise, Mapping)
            or repowise.get("source") not in {"disabled", "bundled", "external"}
            or repowise.get("enforcement") not in {"advisory", "required"}
        )
    )
    return bool(set(regenerate) - supported or workflow_incomplete or repowise_incomplete)


def _plan_repair(resolved: RepairResolved) -> int | RepairPlan:
    """@brief Resolve decisions, regeneration, and the frozen repair preview."""
    decision_result = _resolve_repair_decisions(resolved)
    if isinstance(decision_result, int):
        return decision_result
    decisions, asker, unresolved = decision_result
    invalid = _validate_repair_decision_bytes(resolved, decisions)
    if invalid is not None:
        return invalid
    answers, regenerate, repowise, incomplete = _repair_generation(resolved)
    if incomplete:
        return _repair_emit(
            resolved.context, status="needs-input", exit_code=EXIT_NEEDS_INPUT,
            result={"regenerate": regenerate},
            messages=("generated configuration metadata/answers are incomplete; run waegis configure",),
        )
    options = resolved.context.options
    plan_data = {
        "repo": str(resolved.context.repo_path),
        "restore_missing": list(resolved.drift.missing),
        "modified": [
            {"path": path, "decision": decisions.get(path)}
            for path in resolved.drift.modified
        ],
        "regenerate": regenerate,
        "recovered_transactions": list(resolved.recovered),
        "pending_recovery": list(resolved.pending) if options.dry_run else [],
    }
    mutations = bool(resolved.drift.missing or resolved.drift.modified or regenerate)
    return RepairPlan(
        resolved, decisions, asker, answers, regenerate, repowise,
        plan_data, unresolved, mutations,
    )


def _consent_repair(plan: RepairPlan) -> int | RepairPlan:
    """@brief Handle unresolved, dry-run, no-op, and explicit repair consent."""
    context = plan.resolved.context
    options = context.options
    if plan.unresolved:
        return _repair_emit(
            context, status="needs-input", exit_code=EXIT_NEEDS_INPUT,
            plan=plan.plan_data,
            messages=("modified files require explicit decisions: " + ", ".join(plan.unresolved),),
        )
    if options.dry_run:
        return _repair_emit(
            context, status="ok", exit_code=EXIT_OK, plan=plan.plan_data
        )
    if not plan.mutations:
        return _repair_emit(
            context, status="ok", exit_code=EXIT_OK, plan=plan.plan_data,
            result={"repaired": False, "no_op": True},
        )
    consent = mutation_consent(
        mutation_planned=True, yes=options.yes, asker=plan.asker,
        prompt="Apply this repair plan?",
    )
    if consent is ConsentDecision.APPROVED:
        return plan
    return _repair_emit(
        context, status="needs-input", exit_code=EXIT_NEEDS_INPUT,
        plan=plan.plan_data,
        messages=(
            "repair plan was not approved" if consent is ConsentDecision.DECLINED
            else "repair mutation requires explicit --yes or an interactive approval",
        ),
    )


def _repair_affected_paths(plan: RepairPlan) -> list[str]:
    """@brief Build the transaction path set for an approved repair."""
    affected = set(plan.resolved.drift.missing) | set(plan.regenerate) | {
        MANIFEST_RELATIVE_PATH
    }
    for path, decision in plan.decisions.items():
        if decision == "take-payload":
            affected.add(path)
        elif decision == "write-new":
            affected.add(sidecar_relative_path(path))
    return sorted(affected)


def _repair_apply_managed(plan: RepairPlan, state: RepairApplyState) -> None:
    """@brief Restore missing files and apply modified-file decisions."""
    repo_path = plan.resolved.context.repo_path
    payload_root = plan.resolved.payload_root
    for relative in plan.resolved.drift.missing:
        destination = resolve_managed_path(repo_path, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolve_managed_path(payload_root, relative), destination)
        ensure_executable(destination)
    for relative, decision in plan.decisions.items():
        if decision == "take-payload":
            destination = resolve_managed_path(repo_path, relative)
            shutil.copy2(resolve_managed_path(payload_root, relative), destination)
            ensure_executable(destination)
            state.skipped.discard(relative)
        else:
            state.files.pop(relative, None)
            state.skipped.add(relative)
            if decision == "write-new":
                sidecar = resolve_managed_path(
                    repo_path, sidecar_relative_path(relative)
                )
                sidecar.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(resolve_managed_path(payload_root, relative), sidecar)
                ensure_executable(sidecar)


def _repair_regenerate_workflow(
    plan: RepairPlan, state: RepairApplyState,
) -> None:
    """@brief Regenerate workflow.toml at its original transaction point."""
    if WORKFLOW_TOML_RELATIVE_PATH not in plan.regenerate:
        return
    repo_path = plan.resolved.context.repo_path
    workflow = resolve_managed_path(repo_path, WORKFLOW_TOML_RELATIVE_PATH)
    base = (
        workflow.read_text(encoding="utf-8") if workflow.is_file()
        else resolve_managed_path(
            plan.resolved.payload_root, WORKFLOW_TOML_RELATIVE_PATH
        ).read_text(encoding="utf-8")
    )
    generated = generate_workflow_toml(base, **plan.configuration_answers)
    temporary = workflow.with_name(workflow.name + ".waegis-tmp")
    temporary.write_text(generated.text, encoding="utf-8", newline="")
    os.replace(temporary, workflow)
    state.configuration["answers"] = {
        key: plan.configuration_answers[key]
        for key in sorted(plan.configuration_answers)
    }
    state.configuration["generator_version"] = WIZARD_VERSION
    state.generated_files[WORKFLOW_TOML_RELATIVE_PATH] = {
        "sha256": hash_file(workflow).sha256
    }


def _repair_regenerate_repowise(
    plan: RepairPlan, state: RepairApplyState,
) -> None:
    """@brief Regenerate the RepoWise integration at its original point."""
    if INTEGRATION_RELATIVE_PATH not in plan.regenerate:
        return
    if not isinstance(plan.repowise_configuration, Mapping):
        raise ValueError(
            "manifest repowise configuration must be a table to "
            "regenerate the integration policy"
        )
    raw = plan.repowise_configuration
    policy = resolve_managed_path(
        plan.resolved.context.repo_path, INTEGRATION_RELATIVE_PATH
    )
    settings = RepoWiseSettings(
        source=str(raw["source"]),
        profile=str(raw.get("profile", "deterministic")),
        ollama_url=str(raw.get("ollama_url", "http://127.0.0.1:11434")),
        model=str(raw.get("model", "")),
        embedding_model=str(raw.get("embedding_model", "")),
        enforcement=str(raw["enforcement"]),
    )
    temporary = policy.with_name(policy.name + ".waegis-tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(_integration_text(settings), encoding="utf-8", newline="")
    os.replace(temporary, policy)
    state.generated_files[INTEGRATION_RELATIVE_PATH] = {
        "sha256": hash_file(policy).sha256
    }


def _repair_verify_commit(
    plan: RepairPlan, state: RepairApplyState, transaction: FileTransaction,
) -> None:
    """@brief Verify repaired state, publish manifest last, and commit."""
    if plan.regenerate:
        state.configuration["generated_files"] = state.generated_files
    expected_manifest = replace(
        plan.resolved.manifest, files=state.files,
        skipped=tuple(sorted(state.skipped)), configuration=state.configuration,
    )
    expected_drift = compute_drift(
        plan.resolved.context.repo_path, expected_manifest
    )
    if expected_drift.modified or expected_drift.missing:
        raise RuntimeError(
            f"doctor-style drift verification failed: modified={expected_drift.modified}, "
            f"missing={expected_drift.missing}"
        )
    if bool(plan.resolved.supplied.get("run_smoke", True)):
        runner = plan.resolved.context.options.runner or SubprocessCommandRunner()
        smoke, smoke_ok = smoke_reverify(
            runner, plan.resolved.context.repo_path
        )
        if not smoke_ok:
            failures = "; ".join(
                item.detail for item in smoke if item.status == "fail"
            )
            raise RuntimeError(f"smoke verification failed: {failures}")
    transaction.mark("verified")
    write_manifest(plan.resolved.context.repo_path, expected_manifest)
    transaction.commit()


def _repair_apply_failure(
    plan: RepairPlan, transaction: FileTransaction | None, exc: BaseException,
) -> int:
    """@brief Roll back and report one repair apply failure."""
    rollback_error: Exception | None = None
    rolled_back = False
    committed = transaction is not None and transaction.phase == "committed"
    if transaction is not None and transaction.directory.exists() and not committed:
        try:
            transaction.rollback()
            rolled_back = True
        except Exception as rollback_exc:
            rollback_error = rollback_exc
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        if rollback_error is not None:
            exc.add_note(f"transaction rollback also failed: {rollback_error}")
        raise exc
    if committed:
        return _repair_emit(
            plan.resolved.context, status="error", exit_code=EXIT_OPERATIONAL,
            plan=plan.plan_data,
            result={"repaired": True, "rolled_back": False, "cleanup_pending": True},
            messages=("repair committed, but transaction cleanup failed; "
                      f"recovery will retry cleanup: {exc}",),
        )
    message = (
        "repair failed and rollback did not complete; authenticated recovery "
        f"state was retained: {rollback_error}"
        if rollback_error is not None
        else f"repair failed and was rolled back: {exc}"
    )
    return _repair_emit(
        plan.resolved.context,
        status="failed",
        exit_code=EXIT_VALIDATION,
        plan=plan.plan_data,
        result={"repaired": False, "rolled_back": rolled_back},
        messages=(message,),
    )


def _apply_repair(plan: RepairPlan) -> int | RepairOutcome:
    """@brief Apply the approved repair with unchanged transaction ordering."""
    manifest = plan.resolved.manifest
    configuration = dict(manifest.configuration)
    raw_generated = configuration.get("generated_files")
    state = RepairApplyState(
        set(manifest.skipped), dict(manifest.files), configuration,
        dict(raw_generated) if isinstance(raw_generated, Mapping) else {},
    )
    transaction: FileTransaction | None = None
    try:
        transaction = FileTransaction.begin(
            plan.resolved.context.repo_path, command="repair",
            paths=_repair_affected_paths(plan),
        )
        transaction.mark("applying")
        _repair_apply_managed(plan, state)
        _repair_regenerate_workflow(plan, state)
        _repair_regenerate_repowise(plan, state)
        _repair_verify_commit(plan, state, transaction)
    except BaseException as exc:
        return _repair_apply_failure(plan, transaction, exc)
    return RepairOutcome(plan)


def _report_repair(outcome: RepairOutcome) -> int:
    """@brief Emit the successful repair result."""
    return _repair_emit(
        outcome.plan.resolved.context, status="ok", exit_code=EXIT_OK,
        plan=outcome.plan.plan_data,
        result={"repaired": True, "no_op": False, "rolled_back": False},
    )


def _run_repair_phases(
    repo: str | os.PathLike[str],
    *,
    options: CommandOptions,
) -> int:
    """@brief Orchestrate validate, plan, consent, apply, and report phases."""
    normalized = replace(
        options, non_interactive=options.non_interactive or options.as_json
    )
    context = RepairContext(Path(repo).resolve(), normalized)
    resolved = _validate_repair(context)
    if isinstance(resolved, int):
        return resolved
    plan = _plan_repair(resolved)
    if isinstance(plan, int):
        return plan
    approved = _consent_repair(plan)
    if isinstance(approved, int):
        return approved
    outcome = _apply_repair(approved)
    if isinstance(outcome, int):
        return outcome
    return _report_repair(outcome)


def run_repair(
    repo: str | os.PathLike[str],
    *,
    stream: IO[str],
    answers_path: str | os.PathLike[str] | None = None,
    dry_run: bool = False,
    non_interactive: bool = False,
    yes: bool = False,
    as_json: bool = False,
    payload: str | os.PathLike[str] | None = None,
    stdin: IO[str] | None = None,
    runner: CommandRunner | None = None,
) -> int:
    """
    @brief      Run transactional repair through its five lifecycle phases.
    @details    Preserves the public CLI/test injection seam while packaging
                recurring arguments in :class:`CommandOptions`.
    @return     Standardized command exit code 0/1/2/3.
    """
    return _run_repair_phases(
        repo,
        options=CommandOptions(
            stream, stdin, runner, None, yes, dry_run, non_interactive,
            as_json, answers_path, payload,
        ),
    )


# END OF FILE
