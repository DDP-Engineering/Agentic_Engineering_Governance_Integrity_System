#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file runner.py
@brief Step engine runner: plan build, preview gate, detect/act/verify loop (§4).
@details Executes a :class:`~waegis.engine.catalog.Catalog` against an
         :class:`~waegis.engine.step.EngineContext`. The runner builds the
         ordered, applicable plan and emits it for preview; ``--dry-run`` stops
         there. After the operator approves the plan it runs each step:
         ``detect`` (skip if already green), an assisted-step confirmation where
         required, ``act``, then the required ``verify``. A failed or declined
         step stops the run and surfaces ``on_fail``. The runner never prints —
         it reports through the injected event sink — and journals each step
         when a journal is supplied. A resume seed is only a hint: every
         previously green step runs its current read-only ``detect`` again.
         Damage or configuration drift therefore cannot be hidden by a stale
         checkpoint.
"""

# IMPORTS

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from ..consent import ConfirmationAsker, ConsentDecision, mutation_consent
from .catalog import Catalog
from .journal import (
    STATUS_COMPLETED,
    STATUS_DECLINED,
    STATUS_FAILED,
    STATUS_STOPPED,
    Journal,
    utc_now_iso,
)
from .plan import build_plan
from .step import (
    Automation,
    EngineContext,
    PlanApproved,
    PlanReady,
    PlanRejected,
    Remediation,
    RunFinished,
    RunStarted,
    StepActed,
    StepDetected,
    StepFinished,
    StepResult,
    StepSpec,
    StepStarted,
    StepStatus,
    StepVerified,
)

# CONSTANTS

# @brief Prompt shown at the plan-preview approval gate.
_APPROVAL_PROMPT = "Apply this plan?"
_CONTEXT_ASKER = object()


# DATA MODELS / TYPEDEFINITIONS


@dataclass
class RunSummary:
    """
    @brief Outcome of one engine run.
    @details ``ok`` is true only when every planned step reached a green outcome.
             ``stopped_at`` names the step a failure/decline/block stopped the run
             at, or ``None`` for a completed or dry run.
    """

    mode: str
    dry_run: bool
    results: list[StepResult] = field(default_factory=list)
    ok: bool = True
    stopped_at: str | None = None


# LOCAL HELPERS


def _resolve_resume(resume: "Journal | Iterable[str] | None") -> set[str]:
    """
    @brief      Normalize the resume argument to a set of green step ids to seed.
    @param[in]  resume A loaded :class:`Journal`, an iterable of step ids, or
                ``None``.
    @return     Set of step ids to treat as already green.
    @exception  None
    """
    if resume is None:
        return set()
    if isinstance(resume, Journal):
        return set(resume.green_step_ids())
    return set(resume)


def _safe_on_fail(spec: StepSpec, ctx: EngineContext) -> Remediation:
    """
    @brief      Invoke a step's ``on_fail`` without letting it break the run.
    @param[in]  spec The failing step.
    @param[in]  ctx Active engine context.
    @return     The step's :class:`Remediation`, or a neutral one if ``on_fail``
                raised or returned a non-remediation value.
    @exception  None
    """
    try:
        remediation = spec.on_fail(ctx)
    except Exception as exc:  # noqa: BLE001 - on_fail must never abort the run
        return Remediation(
            diagnosis=f"step {spec.id!r} failed and its guidance could not be produced",
            remediation=f"{type(exc).__name__}: {exc}",
            it_request=None,
        )
    if isinstance(remediation, Remediation):
        return remediation
    return Remediation(
        diagnosis=f"step {spec.id!r} failed",
        remediation=str(remediation),
        it_request=None,
    )


def _error_text(exc: BaseException) -> str:
    """
    @brief      One-line summary of an exception for the journal ``error`` field.
    @param[in]  exc The caught exception.
    @return     ``"<ExceptionType>: <message>"``.
    @exception  None
    """
    return f"{type(exc).__name__}: {exc}"


def _run_step(spec: StepSpec, ctx: EngineContext) -> StepResult:
    """
    @brief      Execute one step's detect/act/verify cycle and build its result.
    @details    Emits the per-step lifecycle events and activates the result on
                the context so the step's recording helpers append to it. A green
                ``detect`` skips ``act``; an assisted step whose confirmation is
                refused is ``DECLINED`` without acting; ``verify`` is always run
                after a completed ``act``; any callable raising is captured as a
                ``FAILED`` result with remediation.
    @param[in]  spec The step to run.
    @param[in]  ctx Active engine context.
    @return     The terminal :class:`StepResult` for the step.
    @exception  None
    """
    result = StepResult(step_id=spec.id, started_at=utc_now_iso())
    ctx._begin(result)
    try:
        ctx.events.emit(StepStarted(spec.id, spec.title, spec.phase, spec.automation))

        # detect: strictly read-only, decides skip-if-already-green.
        try:
            satisfied = bool(spec.detect(ctx))
        except Exception as exc:  # noqa: BLE001
            result.error = _error_text(exc)
            result.status = StepStatus.FAILED
            result.failure = _safe_on_fail(spec, ctx)
            return result
        result.detected = satisfied
        ctx.events.emit(StepDetected(spec.id, satisfied))
        if satisfied:
            result.status = StepStatus.SKIPPED
            return result

        # assisted steps require an explicit per-step confirmation before act.
        if spec.automation is Automation.ASSISTED:
            if not ctx.asker.confirm(f"Proceed with '{spec.title}'?", default=True):
                result.status = StepStatus.DECLINED
                result.messages.append("operator declined this step")
                return result

        # act: perform (or guide, for manual steps). A raised act is a failure.
        try:
            spec.act(ctx)
        except Exception as exc:  # noqa: BLE001
            result.error = _error_text(exc)
            result.status = StepStatus.FAILED
            result.failure = _safe_on_fail(spec, ctx)
            return result
        result.acted = True
        ctx.events.emit(StepActed(spec.id))

        # verify: required machine-checkable postcondition, always after act.
        try:
            verified = bool(spec.verify(ctx))
        except Exception as exc:  # noqa: BLE001
            result.error = _error_text(exc)
            result.status = StepStatus.FAILED
            result.failure = _safe_on_fail(spec, ctx)
            return result
        result.verified = verified
        ctx.events.emit(StepVerified(spec.id, verified))
        if verified:
            result.status = StepStatus.DONE
        else:
            result.status = StepStatus.FAILED
            result.failure = _safe_on_fail(spec, ctx)
        return result
    finally:
        result.finished_at = utc_now_iso()
        ctx._end()
        ctx.events.emit(StepFinished(result))


def _finish(
    ctx: EngineContext,
    journal: Journal | None,
    summary: RunSummary,
    status: str,
    stopped_at: str | None,
) -> RunSummary:
    """
    @brief      Finalize the journal (if any) and emit the terminal run event.
    @param[in]  ctx Active engine context.
    @param[in]  journal Optional journal to finalize.
    @param[in]  summary The run summary to emit.
    @param[in]  status Terminal run status literal for the journal.
    @param[in]  stopped_at Step id a stop occurred at, if any.
    @return     The same ``summary`` (for call-site convenience).
    @exception  OSError If a supplied journal cannot be written.
    """
    if journal is not None:
        journal.finalize(status=status, stopped_at_step=stopped_at)
    ctx.events.emit(RunFinished(summary))
    return summary


# PUBLIC API


def run(
    catalog: Catalog,
    ctx: EngineContext,
    *,
    dry_run: bool = False,
    journal: Journal | None = None,
    resume: "Journal | Iterable[str] | None" = None,
    yes: bool = False,
    approval_asker: ConfirmationAsker | None | object = _CONTEXT_ASKER,
    journal_factory: Callable[[], Journal] | None = None,
    additional_mutations: tuple[str, ...] = (),
) -> RunSummary:
    """
    @brief      Execute a catalog: plan preview, approval gate, then the per-step
                detect/act/verify loop (plan §4).
    @details    Builds the ordered, ``applies``-filtered plan and emits it. In
                dry-run mode the run stops after the preview and mutates nothing.
                Otherwise the operator approves the plan once (an assisted step is
                additionally confirmed individually), then each step runs in
                order; a step already green via ``detect`` — or seeded green via
                ``resume`` — is skipped, and the first failed or declined step
                stops the run with its ``on_fail`` guidance. Each step is
                journaled as it completes when a journal is supplied.
    @param[in]  catalog The step catalog to run.
    @param[in]  ctx Engine context (mode, asker, event sink, shared state).
    @param[in]  dry_run When true, stop after emitting the plan preview.
    @param[in]  journal Optional journal to checkpoint each step into.
    @param[in]  resume Optional loaded journal or iterable of green step ids to
                seed as already complete.
    @param[in]  yes When true, auto-approve the plan without prompting (still
                subject to the same mutation-consent policy).
    @param[in]  approval_asker Confirmation asker used for the plan-approval
                prompt; the sentinel default uses ``ctx.asker``, and ``None``
                disables prompting outright.
    @param[in]  journal_factory Optional factory invoked to lazily create a
                journal once a mutation is actually planned, when the caller
                did not already supply one.
    @param[in]  additional_mutations Extra mutation descriptions, beyond the
                steps themselves, to include in the plan preview and the
                mutation-consent decision.
    @return     The :class:`RunSummary` for the run.
    @exception  OSError If a supplied journal cannot be written.
    """
    seeded = _resolve_resume(resume)
    steps = catalog.plan_for(ctx)
    plan_ids = {spec.id for spec in steps}
    step_ids = tuple(spec.id for spec in steps)

    ctx.events.emit(RunStarted(ctx.mode, dry_run, step_ids))
    plan = build_plan(
        ctx.mode,
        dry_run,
        steps,
        ctx,
        additional_mutations=additional_mutations,
    )
    ctx.events.emit(PlanReady(plan))

    # Dry run: preview only, no approval prompt, no mutation, no journal writes.
    if dry_run:
        summary = RunSummary(mode=ctx.mode, dry_run=True, results=[], ok=True)
        ctx.events.emit(RunFinished(summary))
        return summary

    # Read-only detects make genuinely green reruns no-op plans.
    mutation_planned = bool(additional_mutations)
    for spec in steps:
        try:
            if not bool(spec.detect(ctx)):
                mutation_planned = True
                break
        except Exception:  # noqa: BLE001 - the normal run reports the typed step failure
            mutation_planned = True
            break

    consent = mutation_consent(
        mutation_planned=mutation_planned,
        yes=yes,
        asker=ctx.asker if approval_asker is _CONTEXT_ASKER else approval_asker,  # type: ignore[arg-type]
        prompt=_APPROVAL_PROMPT,
    )
    if consent is not ConsentDecision.APPROVED:
        ctx.events.emit(PlanRejected())
        summary = RunSummary(mode=ctx.mode, dry_run=False, results=[], ok=False)
        # A caller-supplied journal must still be finalized so its on-disk
        # document does not stay "in_progress" after the operator declines.
        return _finish(ctx, journal, summary, STATUS_STOPPED, None)
    ctx.events.emit(PlanApproved())
    if mutation_planned and journal is None and journal_factory is not None:
        journal = journal_factory()

    green: set[str] = set()
    results: list[StepResult] = []
    stopped_at: str | None = None
    final_status = STATUS_COMPLETED

    for spec in steps:
        # Precondition guard. Preconditions filtered out by applies() (absent
        # from the plan) count as satisfied-by-absence, so one catalog serves
        # both modes; a real unmet precondition blocks and stops the run.
        missing = [p for p in spec.preconditions if p in plan_ids and p not in green]
        if missing:
            now = utc_now_iso()
            result = StepResult(
                step_id=spec.id,
                status=StepStatus.BLOCKED,
                started_at=now,
                finished_at=now,
            )
            result.messages.append("blocked: unsatisfied preconditions: " + ", ".join(missing))
            results.append(result)
            if journal is not None:
                journal.record(result)
            ctx.events.emit(StepFinished(result))
            stopped_at = spec.id
            final_status = STATUS_STOPPED
            break

        result = _run_step(spec, ctx)
        if spec.id in seeded and result.detected:
            result.messages.append("prior green checkpoint re-detected against current state")
        results.append(result)
        if journal is not None:
            journal.record(result)

        if result.is_green():
            green.add(spec.id)
            continue

        # First non-green step stops the run and surfaces its on_fail guidance.
        stopped_at = spec.id
        final_status = STATUS_DECLINED if result.status is StepStatus.DECLINED else STATUS_FAILED
        break

    ok = final_status == STATUS_COMPLETED and stopped_at is None
    summary = RunSummary(mode=ctx.mode, dry_run=False, results=results, ok=ok, stopped_at=stopped_at)
    return _finish(ctx, journal, summary, final_status, stopped_at)


# END OF FILE
