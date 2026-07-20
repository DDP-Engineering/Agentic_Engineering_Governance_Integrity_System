#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_engine_runner.py
@brief Runner control-flow tests for the WAEGIS engine (T1.1).
@details Exercises the hard engine behaviours (plan §4): a full green run;
         detect-and-skip on re-run (R6); an act failure surfacing ``on_fail`` and
         stopping the run (R5); ``verify`` always following ``act`` (R5); an
         assisted step not acting without confirmation; and ``--dry-run``
         mutating nothing. Strictly offline; no journal or filesystem needed.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from waegis.engine import (
    PlanReady,
    RunFinished,
    RunStarted,
    StepActed,
    StepStarted,
    StepStatus,
    StepVerified,
    run,
)

from _toy_catalog import (
    RecordingSink,
    ScriptAsker,
    act_counts,
    build_toy_catalog,
    call_order,
    make_ctx,
)

# LOCAL HELPERS


def _statuses(summary) -> dict[str, StepStatus]:
    """
    @brief      Map each step id in a summary to its terminal status.
    @param[in]  summary The :class:`RunSummary` to read.
    @return     Mapping of step id to :class:`StepStatus`.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return {r.step_id: r.status for r in summary.results}


# TESTS


def test_full_green_run() -> None:
    """
    @brief      Every step of the toy catalog runs and verifies green once.
    @return     None
    @exception  AssertionError On any non-green step or wrong act count.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = make_ctx()
    summary = run(build_toy_catalog(), ctx)

    assert summary.ok is True
    assert summary.stopped_at is None
    assert _statuses(summary) == {
        "toy.a": StepStatus.DONE,
        "toy.b": StepStatus.DONE,
        "toy.c": StepStatus.DONE,
    }
    assert act_counts(ctx) == {"toy.a": 1, "toy.b": 1, "toy.c": 1}
    # Non-secret answers/artifacts were recorded onto the results.
    result_a = summary.results[0]
    assert result_a.answers == {"toy.a_key": "value"}
    assert result_a.artifacts == ["toy.a.artifact"]


def test_detect_skip_on_rerun() -> None:
    """
    @brief      Re-running against the same context detects every step green and
                skips it, without acting again (R6).
    @return     None
    @exception  AssertionError If a step re-acts or is not skipped.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    catalog = build_toy_catalog()
    ctx = make_ctx()

    run(catalog, ctx)
    summary = run(catalog, ctx)

    assert summary.ok is True
    assert set(_statuses(summary).values()) == {StepStatus.SKIPPED}
    # act ran exactly once per step across both runs.
    assert act_counts(ctx) == {"toy.a": 1, "toy.b": 1, "toy.c": 1}


def test_act_failure_surfaces_on_fail_and_stops() -> None:
    """
    @brief      A raising ``act`` yields a FAILED result carrying ``on_fail``
                guidance and stops the run before later steps (R5).
    @return     None
    @exception  AssertionError If the failure is not surfaced or the run continues.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = make_ctx()
    summary = run(build_toy_catalog(fail_step="toy.a", fail_mode="act"), ctx)

    assert summary.ok is False
    assert summary.stopped_at == "toy.a"
    # Only the failing step produced a result; downstream steps never ran.
    assert [r.step_id for r in summary.results] == ["toy.a"]
    failed = summary.results[0]
    assert failed.status is StepStatus.FAILED
    assert failed.error is not None and "boom" in failed.error
    assert failed.failure is not None
    assert failed.failure.diagnosis == "toy.a failed"
    assert "toy.b" not in act_counts(ctx)


def test_verify_failure_stops_run() -> None:
    """
    @brief      A false ``verify`` (after a completed ``act``) fails the step and
                stops the run.
    @return     None
    @exception  AssertionError If a false verify does not fail/stop.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = make_ctx()
    summary = run(build_toy_catalog(fail_step="toy.b", fail_mode="verify"), ctx)

    assert summary.ok is False
    assert summary.stopped_at == "toy.b"
    statuses = _statuses(summary)
    assert statuses["toy.a"] is StepStatus.DONE
    assert statuses["toy.b"] is StepStatus.FAILED
    assert "toy.c" not in statuses


def test_verify_always_called_after_act() -> None:
    """
    @brief      For an acting step, ``verify`` is invoked after ``act`` — checked
                via the call order and the emitted events (R5).
    @return     None
    @exception  AssertionError If verify does not follow act.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    sink = RecordingSink()
    ctx = make_ctx(sink=sink)
    run(build_toy_catalog(), ctx)

    order = call_order(ctx)
    for step_id in ("toy.a", "toy.b", "toy.c"):
        assert order.index((step_id, "act")) < order.index((step_id, "verify"))

    # Every StepActed precedes its matching StepVerified in the event stream.
    acted = [e.step_id for e in sink.events if isinstance(e, StepActed)]
    verified = [e.step_id for e in sink.events if isinstance(e, StepVerified)]
    assert acted == verified == ["toy.a", "toy.b", "toy.c"]
    for step_id in ("toy.a", "toy.b", "toy.c"):
        act_idx = next(i for i, e in enumerate(sink.events) if isinstance(e, StepActed) and e.step_id == step_id)
        ver_idx = next(i for i, e in enumerate(sink.events) if isinstance(e, StepVerified) and e.step_id == step_id)
        assert act_idx < ver_idx


def test_assisted_step_without_confirmation_does_not_act() -> None:
    """
    @brief      An assisted step whose confirmation is refused does not act and
                stops the run as DECLINED.
    @return     None
    @exception  AssertionError If the step acts or the run does not stop.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    # First confirm approves the plan; second (for the assisted toy.b) refuses.
    asker = ScriptAsker(confirms=[True, False])
    ctx = make_ctx(asker=asker)
    summary = run(build_toy_catalog(), ctx)

    statuses = _statuses(summary)
    assert statuses["toy.a"] is StepStatus.DONE
    assert statuses["toy.b"] is StepStatus.DECLINED
    assert "toy.c" not in statuses
    assert summary.ok is False
    assert summary.stopped_at == "toy.b"
    assert "toy.b" not in act_counts(ctx)


def test_plan_rejected_runs_nothing() -> None:
    """
    @brief      Declining the plan-preview gate runs no step.
    @return     None
    @exception  AssertionError If any step acts or the run reports ok.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    asker = ScriptAsker(confirms=[False])
    ctx = make_ctx(asker=asker)
    summary = run(build_toy_catalog(), ctx)

    assert summary.ok is False
    assert summary.results == []
    assert act_counts(ctx) == {}


def test_dry_run_mutates_nothing() -> None:
    """
    @brief      ``dry_run`` stops after the preview: no step acts, and only the
                preview lifecycle events are emitted.
    @return     None
    @exception  AssertionError If any step acts or a step event is emitted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    sink = RecordingSink()
    ctx = make_ctx(sink=sink)
    summary = run(build_toy_catalog(), ctx, dry_run=True)

    assert summary.ok is True
    assert summary.dry_run is True
    assert summary.results == []
    assert act_counts(ctx) == {}
    # Preview emitted, but no step ever started.
    assert len(sink.of_type(RunStarted)) == 1
    assert len(sink.of_type(PlanReady)) == 1
    assert len(sink.of_type(RunFinished)) == 1
    assert sink.of_type(StepStarted) == []


# END OF FILE
