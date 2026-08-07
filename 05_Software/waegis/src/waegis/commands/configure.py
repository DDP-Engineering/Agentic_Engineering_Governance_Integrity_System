#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file configure.py
@brief Post-install, owned-field-only workflow configuration lifecycle.
@details Uses stored manifest answers first and repository-analysis proposals as
         fallbacks; when the manifest records no answers, the existing valid
         workflow file is read back for them, and a successful run stores the
         completed set. The current workflow file is the rewrite base, so comments
         and every non-owned field remain byte-for-byte unchanged. Writes are
         atomic, smoke/gate failures restore the prior file, and configuration
         metadata is written to the install manifest last.
@details Human and ``--json`` output are held to the same information: when
         configuration succeeds but RepoWise synchronization fails, both state
         the sync verdict, the concise error, the isolated log path, and the
         resume command. Only the rendering changed for this — the RepoWise
         result payload and how the lifecycle is invoked are untouched.
"""

# IMPORTS

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import IO, Any, Mapping

from ..consent import ConsentDecision, mutation_consent
from ..io.answers import AnswersFileError, load_answers_file
from ..io.envelope import EXIT_NEEDS_INPUT, EXIT_OK, EXIT_OPERATIONAL, EXIT_VALIDATION
from ..io.prompts import ConsoleAsker, PromptsError
from ..payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    ManifestState,
    hash_file,
    load_manifest,
    resolve_managed_path,
    write_manifest,
)
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..repo.analyze import RepoAnalysis, analyze_repo
from ..repo.workflow_toml import (
    GATE_ORDER,
    GENERATOR_ANSWER_KEYS,
    OTHER_LANGUAGE_FIELD_SPECS,
    WORKFLOW_FIELD_SPECS,
    WorkflowTomlError,
    derive_answers_from_workflow,
    generate_workflow_toml,
    normalize_stored_answers,
)
from ..repowise import REPOWISE_ANSWER_KEYS, RepoWiseError, lifecycle_repowise
from ..verification import smoke_reverify
from ..version import WIZARD_VERSION
from ..transaction import FileTransaction
from ._shared import (
    CommandOptions,
    PAYLOAD_VALIDATION_ERRORS,
    WORKFLOW_TOML_RELATIVE_PATH,
    emit_command_output,
    locate_validated_payload,
    recover_transactions_or_emit,
    render_pending_recovery,
)

# CONSTANTS

_CONTROL_KEYS = frozenset({"run_gates", "run_smoke"})

# @brief The durable answer allowlist, owned by the generator's own spec tables
#        so this command and the wizards that write the manifest can never
#        disagree about which answers are configuration.
CONFIG_KEYS = GENERATOR_ANSWER_KEYS


# HELPER FUNCTIONS


def _render_sync_failure(stream: IO[str], result: Mapping[str, Any]) -> None:
    """
    @brief      Render the split-result case: configuration applied, RepoWise
                synchronization failed.
    @details    This is the one outcome where the two output surfaces used to
                disagree. ``configured`` is true, so human mode printed
                "Configuration updated and verified." and stopped, while the
                ``--json`` result carried the sync verdict, the parsing error,
                the isolated log path, and the resume command. A human operator
                read that as an unqualified success. The same four facts are
                now printed here, so the surfaces are semantically equivalent.
                A successful (or deferred, or disabled) sync adds no lines at
                all: the configuration verdict already covers it.
                Read defensively — the synthesized payload for a raised
                RepoWise error carries ``error`` and no log or resume command,
                where a returned failure carries ``message``/``log``/
                ``resume_command``.
    @param[in]  stream Output stream.
    @param[in]  result The frozen result payload.
    @return     None
    @exception  None
    """
    repowise = result.get("repowise")
    if not isinstance(repowise, Mapping):
        return
    sync = repowise.get("sync")
    if not isinstance(sync, Mapping) or sync.get("ok", True):
        return
    stream.write(
        "RepoWise synchronization: FAILED (the AEGIS configuration itself is "
        "applied and verified).\n"
    )
    detail = sync.get("message") or sync.get("error") or "no error detail was reported"
    stream.write(f"  error:  {detail}\n")
    log = sync.get("log")
    stream.write(f"  log:    {log}\n" if log else "  log:    (none was written)\n")
    resume = sync.get("resume_command")
    if resume:
        stream.write(f"  resume: {resume}\n")


def _render_configure_human(
    stream: IO[str],
    plan: Mapping[str, Any] | None,
    result: Mapping[str, Any] | None,
) -> None:
    """
    @brief      Render configure's command-specific human plan/result lines.
    @details    Deliberately configure-only (the shared core lives in
                :func:`waegis.commands._shared.emit_command_output`): the plan
                is summarized as per-field before/after changes and the result
                as the configuration verdict, which no other command emits.
                A configured result whose RepoWise synchronization failed also
                renders the sync block (:func:`_render_sync_failure`), so human
                mode carries the same facts the JSON result does.
    @param[in]  stream Output stream.
    @param[in]  plan Optional frozen plan payload.
    @param[in]  result Optional frozen result payload.
    @return     None
    @exception  None
    """
    if plan is not None:
        render_pending_recovery(stream, plan)
        changes = plan.get("changes", [])
        stream.write(f"Configuration plan: {len(changes)} field change(s).\n")
        for change in changes:
            stream.write(f"  {change['field']}: {change['before']!r} -> {change['after']!r}\n")
    if result is not None and result.get("configured"):
        stream.write("Configuration updated and verified.\n")
        _render_sync_failure(stream, result)


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
    @brief      Emit configure output through the human or JSON surface.
    @return     ``exit_code``.
    """
    return emit_command_output(
        stream,
        "configure",
        as_json=as_json,
        status=status,
        exit_code=exit_code,
        plan=plan,
        result=result,
        messages=messages,
        render_human=_render_configure_human,
    )


def _analysis_defaults(analysis: RepoAnalysis | None) -> dict[str, Any]:
    """
    @brief      Convert read-only repository proposals into field defaults.
    @return     Proposed configuration mapping.
    """
    if analysis is None:
        return {}
    return {
        "source_roots": [item.path for item in analysis.source_roots],
        "test_roots": [item.path for item in analysis.test_roots],
        "language": analysis.language or "python",
        **{
            f"gate_{name}_cmds": [
                list(item.argv)
                for item in getattr(analysis, f"gate_{name}_cmds")
                if item.argv and not item.needs_review
            ]
            for name in GATE_ORDER
        },
    }


def stored_answers(configuration: Mapping[str, Any]) -> dict[str, Any]:
    """
    @brief      Extract allowlisted generator answers from manifest metadata.
    @return     Stored answer mapping, possibly empty.
    """
    raw = configuration.get("answers")
    if not isinstance(raw, Mapping):
        return {}
    return normalize_stored_answers({str(key): value for key, value in raw.items()})


def _recovered_answers(repo: Path, configuration: Mapping[str, Any]) -> dict[str, Any]:
    """
    @brief      The effective stored-answer set, reconstructing what the
                manifest does not record.
    @details    Installs written before adoption persisted its answers carry an
                empty ``configuration``, which used to leave configure with
                nothing but repository proposals: a run that only meant to
                change one field had to restate the entire workflow, and a run
                that could not propose a source root failed outright. The
                generated workflow.toml is itself a complete record of the
                answers that produced it, so it is read back as the base layer.
                Anything the manifest does record still wins — it is the more
                explicit statement of intent, and this layer only fills gaps.
                A successful configure then writes the completed set back, so
                the reconstruction happens once.
    @param[in]  repo Repository root.
    @param[in]  configuration The manifest's configuration metadata.
    @return     Stored answers over reconstructed ones, possibly empty.
    @exception  None
    """
    stored = stored_answers(configuration)
    workflow_path = resolve_managed_path(repo, WORKFLOW_TOML_RELATIVE_PATH)
    try:
        text = workflow_path.read_text(encoding="utf-8")
    except OSError:
        return stored
    return {**derive_answers_from_workflow(text), **stored}


def _resolve_answers(
    supplied: Mapping[str, Any],
    stored: Mapping[str, Any],
    proposals: Mapping[str, Any],
    *,
    non_interactive: bool,
    asker: ConsoleAsker | None,
) -> dict[str, Any]:
    """
    @brief      Resolve and normalize configuration answers by precedence.
    @return     Complete normalized generator answer mapping.
    @exception  PromptsError If a required/invalid value is encountered.
    """
    resolved: dict[str, Any] = {}
    # Answers-file failures are collected rather than raised one at a time.
    # A hand-written policy set routinely trips several fields at once, and
    # fixing them one per invocation turned one edit into a sequence of
    # re-runs. Interactive answers still fail immediately: the asker re-prompts
    # the operator on the spot, so there is nothing to batch.
    rejected: list[str] = []
    for spec in WORKFLOW_FIELD_SPECS:
        default = stored.get(spec.key, proposals.get(spec.key, spec.default))
        dynamic = replace(spec, default=default)
        if spec.key in supplied:
            try:
                resolved[spec.key] = dynamic.normalize(supplied[spec.key])
            except (PromptsError, ValueError) as exc:
                rejected.append(f"{spec.key}: {exc}")
                resolved[spec.key] = default
        elif non_interactive:
            resolved[spec.key] = dynamic.normalize(default)
        else:
            if asker is None:
                raise PromptsError(
                    f"missing required answer: {spec.key} "
                    "(no interactive console is available)"
                )
            resolved[spec.key] = asker.ask_field(dynamic)
    if rejected:
        raise PromptsError(
            f"{len(rejected)} supplied answer(s) were rejected:\n  - "
            + "\n  - ".join(rejected)
        )
    if resolved["language"] == "other":
        for spec in OTHER_LANGUAGE_FIELD_SPECS:
            default = stored.get(spec.key)
            dynamic = replace(spec, default=default)
            if spec.key in supplied:
                resolved[spec.key] = dynamic.normalize(supplied[spec.key])
            elif non_interactive:
                if default is None:
                    raise PromptsError(f"missing required answer: {spec.key}")
                resolved[spec.key] = dynamic.normalize(default)
            else:
                if asker is None:
                    raise PromptsError(
                        f"missing required answer: {spec.key} "
                        "(no interactive console is available)"
                    )
                resolved[spec.key] = asker.ask_field(dynamic)
    return resolved


def _run_selected_gates(runner: CommandRunner, repo: Path, answers: Mapping[str, Any]) -> list[str]:
    """
    @brief      Run configured gate commands when ``run_gates`` was selected.
    @return     Failure messages; empty means all selected gates passed.
    """
    if not answers.get("run_gates", False):
        return []
    failures: list[str] = []
    for gate in (
        "gate_build_cmds",
        "gate_typecheck_cmds",
        "gate_lint_cmds",
        "gate_test_cmds",
        "gate_security_cmds",
    ):
        for command in answers.get(gate, []):
            result = runner.run(tuple(command), timeout=600.0, cwd=repo)
            if not result.ok():
                failures.append(f"{gate}: {' '.join(command)} -> exit {result.exit_code}")
    return failures


# EXPORTED FUNCTIONS / PUBLIC API


@dataclass(frozen=True)
class ConfigureContext:
    """@brief Resolved public boundary for configure command phases."""
    repo_path: Path
    options: CommandOptions


@dataclass(frozen=True)
class ConfigureResolved:
    """@brief Validated configure inputs before answer planning."""
    context: ConfigureContext
    pending: tuple[str, ...]
    recovered: tuple[str, ...]
    manifest: Any
    supplied: dict[str, Any]
    payload_root: Path
    runner: CommandRunner
    analysis: RepoAnalysis | None
    asker: ConsoleAsker | None
    stored: dict[str, Any]


@dataclass(frozen=True)
class ConfigurePlan:
    """@brief Fully rendered configuration plan awaiting consent."""
    resolved: ConfigureResolved
    answers: dict[str, Any]
    controls: dict[str, bool]
    workflow_path: Path
    generated: Any
    content_changed: bool
    plan_data: dict[str, Any]
    repowise_requested: bool


@dataclass(frozen=True)
class ConfigureOutcome:
    """@brief Applied AEGIS configuration awaiting RepoWise/reporting."""
    plan: ConfigurePlan


def _configure_emit(context: ConfigureContext, **kwargs: Any) -> int:
    """@brief Bind configure output options for phase-local early returns."""
    return _emit(
        context.options.stream, as_json=context.options.as_json, **kwargs
    )


def _validate_configure(context: ConfigureContext) -> int | ConfigureResolved:
    """@brief Validate repository, recovery, manifest, answers, and payload."""
    options = context.options
    if not context.repo_path.is_dir():
        return _configure_emit(
            context, status="error", exit_code=EXIT_OPERATIONAL,
            messages=(f"--repo path does not exist or is not a directory: {context.repo_path}",),
        )
    recovery = recover_transactions_or_emit(
        context.repo_path, dry_run=options.dry_run, yes=options.yes,
        recovery_asker=ConsoleAsker(stdin=options.stdin, stdout=options.stream)
        if not options.non_interactive and options.stdin is not None else None,
        emit=lambda **kwargs: _configure_emit(context, **kwargs),
    )
    if isinstance(recovery, int):
        return recovery
    pending, recovered = recovery
    load = load_manifest(context.repo_path)
    if load.state is not ManifestState.VALID or load.manifest is None:
        return _configure_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("a valid current install manifest is required before configuration",),
        )
    supplied: dict[str, Any] = {}
    if options.answers_path is not None:
        try:
            supplied = load_answers_file(options.answers_path)
        except AnswersFileError as exc:
            return _configure_emit(
                context, status="failed", exit_code=EXIT_VALIDATION,
                messages=(str(exc),),
            )
    unknown = sorted(set(supplied) - CONFIG_KEYS - _CONTROL_KEYS - REPOWISE_ANSWER_KEYS)
    if unknown:
        return _configure_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("unrecognized answer key(s): " + ", ".join(unknown),),
        )
    try:
        payload_root, _inventory, _payload_version = locate_validated_payload(options.payload)
    except PAYLOAD_VALIDATION_ERRORS as exc:
        return _configure_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )
    return _resolve_configure_environment(
        context, tuple(pending), tuple(recovered), load.manifest,
        supplied, payload_root,
    )


def _resolve_configure_environment(
    context: ConfigureContext, pending: tuple[str, ...],
    recovered: tuple[str, ...], manifest: Any,
    supplied: dict[str, Any], payload_root: Path,
) -> ConfigureResolved:
    """@brief Resolve runner, analysis, asker, and stored configuration."""
    options = context.options
    runner = options.runner or SubprocessCommandRunner()
    try:
        analysis = analyze_repo(context.repo_path, runner=runner)
    except Exception as exc:  # noqa: BLE001 - proposals are optional
        analysis = None
        if not options.as_json:
            # Human mode only: --json must stay a single parseable envelope.
            options.stream.write(
                f"warning: repository analysis failed ({exc}); "
                "analysis-derived defaults will be empty\n"
            )
    asker = (
        None if options.non_interactive or options.stdin is None
        else ConsoleAsker(stdin=options.stdin, stdout=options.stream)
    )
    return ConfigureResolved(
        context, pending, recovered, manifest, supplied, payload_root, runner,
        analysis, asker,
        _recovered_answers(context.repo_path, manifest.configuration),
    )


def _plan_configure(resolved: ConfigureResolved) -> int | ConfigurePlan:
    """@brief Resolve answers and build the frozen configuration preview."""
    context = resolved.context
    options = context.options
    try:
        answers = _resolve_answers(
            resolved.supplied, resolved.stored,
            _analysis_defaults(resolved.analysis),
            non_interactive=options.non_interactive, asker=resolved.asker,
        )
        controls = {
            "run_gates": bool(resolved.supplied.get("run_gates", False)),
            "run_smoke": bool(resolved.supplied.get("run_smoke", True)),
        }
        workflow_path = resolve_managed_path(
            context.repo_path, WORKFLOW_TOML_RELATIVE_PATH
        )
        base_text = (
            workflow_path.read_text(encoding="utf-8") if workflow_path.is_file()
            else resolve_managed_path(
                resolved.payload_root, WORKFLOW_TOML_RELATIVE_PATH
            ).read_text(encoding="utf-8")
        )
        generated = generate_workflow_toml(base_text, **answers)
    except (PromptsError, WorkflowTomlError, ValueError, OSError) as exc:
        return _configure_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )
    changes = [
        {"field": key, "before": resolved.stored.get(key), "after": answers[key]}
        for key in sorted(answers) if resolved.stored.get(key) != answers[key]
    ]
    content_changed = (
        not workflow_path.is_file()
        or workflow_path.read_text(encoding="utf-8") != generated.text
    )
    plan_data = _configure_plan_data(
        resolved, changes, content_changed, controls, generated
    )
    return ConfigurePlan(
        resolved, answers, controls, workflow_path, generated, content_changed,
        plan_data, bool(plan_data["repowise_requested"]),
    )


def _configure_plan_data(
    resolved: ConfigureResolved, changes: list[dict[str, Any]],
    content_changed: bool, controls: Mapping[str, bool], generated: Any,
) -> dict[str, Any]:
    """@brief Build the byte-compatible configure plan mapping."""
    options = resolved.context.options
    requested = REPOWISE_ANSWER_KEYS.intersection(resolved.supplied)
    return {
        "repo": str(resolved.context.repo_path), "changes": changes,
        "workflow_content_changed": content_changed,
        "warnings": [warning.message for warning in generated.warnings],
        "recovered_transactions": list(resolved.recovered),
        "pending_recovery": list(resolved.pending) if options.dry_run else [],
        **controls, "repowise_requested": bool(requested),
        "repowise": {key: resolved.supplied[key] for key in sorted(requested)},
    }


def _consent_configure(plan: ConfigurePlan) -> int | ConfigurePlan:
    """@brief Handle dry-run, no-op, and explicit configuration consent."""
    context = plan.resolved.context
    options = context.options
    if options.dry_run:
        return _configure_emit(
            context, status="ok", exit_code=EXIT_OK, plan=plan.plan_data
        )
    if not plan.content_changed and not plan.plan_data["changes"] and not plan.repowise_requested:
        return _configure_emit(
            context, status="ok", exit_code=EXIT_OK, plan=plan.plan_data,
            result={"configured": False, "no_op": True},
        )
    consent = mutation_consent(
        mutation_planned=True, yes=options.yes, asker=plan.resolved.asker,
        prompt="Apply this configuration plan?",
    )
    if consent is ConsentDecision.APPROVED:
        return plan
    return _configure_emit(
        context, status="needs-input", exit_code=EXIT_NEEDS_INPUT,
        plan=plan.plan_data,
        messages=(
            "configuration plan was not approved"
            if consent is ConsentDecision.DECLINED
            else "configuration mutation requires explicit --yes or an interactive approval",
        ),
    )


def _write_configured_workflow(
    plan: ConfigurePlan, transaction: FileTransaction, temporary: Path,
) -> None:
    """@brief Write, verify, and journal the configured workflow before manifest."""
    repo_path = plan.resolved.context.repo_path
    transaction.mark("applying")
    plan.workflow_path.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(plan.generated.text, encoding="utf-8", newline="")
    os.replace(temporary, plan.workflow_path)
    failures = _run_selected_gates(
        plan.resolved.runner, repo_path, {**plan.answers, **plan.controls}
    )
    smoke: tuple[Any, ...] = ()
    smoke_ok = True
    if plan.controls["run_smoke"]:
        smoke, smoke_ok = smoke_reverify(plan.resolved.runner, repo_path)
        failures.extend(
            f"{item.name}: {item.detail}" for item in smoke if item.status == "fail"
        )
    if not smoke_ok or failures:
        raise RuntimeError("; ".join(failures))


def _commit_configure_manifest(
    plan: ConfigurePlan, transaction: FileTransaction,
) -> None:
    """@brief Publish configuration metadata last and commit the transaction."""
    manifest = plan.resolved.manifest
    configuration = dict(manifest.configuration)
    raw_generated = configuration.get("generated_files")
    generated_files = dict(raw_generated) if isinstance(raw_generated, Mapping) else {}
    generated_files[WORKFLOW_TOML_RELATIVE_PATH] = {
        "sha256": hash_file(plan.workflow_path).sha256
    }
    configuration["answers"] = normalize_stored_answers(plan.answers)
    configuration["generator_version"] = WIZARD_VERSION
    configuration["generated_files"] = generated_files
    generated_paths = tuple(
        sorted(set(manifest.generated) | {WORKFLOW_TOML_RELATIVE_PATH})
    )
    transaction.mark("verified")
    write_manifest(
        plan.resolved.context.repo_path,
        replace(manifest, generated=generated_paths, configuration=configuration),
    )
    transaction.commit()


def _configure_apply_failure(
    plan: ConfigurePlan, temporary: Path,
    transaction: FileTransaction | None, exc: BaseException,
) -> int:
    """@brief Clean up, roll back, and report one configure apply failure."""
    cleanup_error: Exception | None = None
    if temporary.exists():
        try:
            temporary.unlink()
        except OSError as unlink_exc:
            cleanup_error = unlink_exc
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
        for note_error in (cleanup_error, rollback_error):
            if note_error is not None:
                exc.add_note(f"transaction cleanup/rollback also failed: {note_error}")
        raise exc
    if committed:
        return _configure_emit(
            plan.resolved.context, status="error", exit_code=EXIT_OPERATIONAL,
            plan=plan.plan_data,
            result={"configured": True, "rolled_back": False, "cleanup_pending": True},
            messages=("configuration committed, but transaction cleanup failed; "
                      f"recovery will retry cleanup: {exc}",),
        )
    message = (
        "configuration failed and rollback did not complete; authenticated "
        f"recovery state was retained: {rollback_error}"
        if rollback_error is not None
        else f"configuration verification failed; rolled back: {exc}"
    )
    return _configure_emit(
        plan.resolved.context, status="failed", exit_code=EXIT_VALIDATION,
        plan=plan.plan_data,
        result={"configured": False, "rolled_back": rolled_back},
        messages=(message,),
    )


def _apply_configure(plan: ConfigurePlan) -> int | ConfigureOutcome:
    """@brief Apply the approved configuration with unchanged rollback ordering."""
    context = plan.resolved.context
    temporary = plan.workflow_path.with_name(plan.workflow_path.name + ".waegis-tmp")
    transaction: FileTransaction | None = None
    try:
        transaction = FileTransaction.begin(
            context.repo_path, command="configure",
            paths=(WORKFLOW_TOML_RELATIVE_PATH, MANIFEST_RELATIVE_PATH),
        )
        _write_configured_workflow(plan, transaction, temporary)
        _commit_configure_manifest(plan, transaction)
    except BaseException as exc:
        return _configure_apply_failure(plan, temporary, transaction, exc)
    return ConfigureOutcome(plan)


def _report_configure(outcome: ConfigureOutcome) -> int:
    """@brief Run RepoWise post-processing and emit the configure outcome."""
    plan = outcome.plan
    resolved = plan.resolved
    context = resolved.context
    options = context.options
    repowise_result: dict[str, Any] | None = None
    repowise_error: str | None = None
    if plan.repowise_requested:
        try:
            repowise_result = lifecycle_repowise(
                context.repo_path, resolved.supplied, lifecycle="configure",
                interactive=not options.non_interactive, asker=resolved.asker,
                stream=None if options.as_json else options.stream, yes=options.yes,
            )
        except (OSError, RepoWiseError) as exc:
            repowise_error = str(exc)
    if repowise_error or (repowise_result and not repowise_result["sync"]["ok"]):
        return _configure_emit(
            context, status="error", exit_code=EXIT_OPERATIONAL,
            plan=plan.plan_data,
            result={
                "configured": True, "no_op": False, "rolled_back": False,
                "aegis": {"ok": True},
                "repowise": repowise_result or {
                    "aegis": "ok", "sync": {"ok": False, "error": repowise_error}
                },
            },
            messages=((repowise_error,) if repowise_error else ()),
        )
    warning_messages = tuple(warning.message for warning in plan.generated.warnings)
    return _configure_emit(
        context, status="warning" if warning_messages else "ok",
        exit_code=EXIT_NEEDS_INPUT if warning_messages else EXIT_OK,
        plan=plan.plan_data,
        result={
            "configured": True, "no_op": False, "rolled_back": False,
            "aegis": {"ok": True}, "repowise": repowise_result,
        },
        messages=warning_messages,
    )


def _run_configure_phases(
    repo: str | os.PathLike[str],
    *,
    options: CommandOptions,
) -> int:
    """@brief Orchestrate validate, plan, consent, apply, and report phases."""
    normalized = replace(
        options, non_interactive=options.non_interactive or options.as_json
    )
    context = ConfigureContext(Path(repo).resolve(), normalized)
    resolved = _validate_configure(context)
    if isinstance(resolved, int):
        return resolved
    plan = _plan_configure(resolved)
    if isinstance(plan, int):
        return plan
    approved = _consent_configure(plan)
    if isinstance(approved, int):
        return approved
    outcome = _apply_configure(approved)
    if isinstance(outcome, int):
        return outcome
    return _report_configure(outcome)


def run_configure(
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
    @brief      Run transactional configuration through its lifecycle phases.
    @details    Preserves the public CLI/test injection seam while packaging
                recurring arguments in :class:`CommandOptions`.
    @return     Standardized command exit code 0/1/2/3.
    """
    return _run_configure_phases(
        repo,
        options=CommandOptions(
            stream, stdin, runner, None, yes, dry_run, non_interactive,
            as_json, answers_path, payload,
        ),
    )


# END OF FILE
