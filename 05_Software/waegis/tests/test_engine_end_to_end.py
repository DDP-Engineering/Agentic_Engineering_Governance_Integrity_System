#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_engine_end_to_end.py
@brief M1 milestone acceptance: engine + prompts + console renderer, end to end.
@details Wires the toy 3-step catalog (T1.1) through the console renderer
         (T1.3): the plan preview is rendered and emitted as ``--json``, the
         live status renderer consumes the runner's event stream, and the run
         is journaled. Proves the plan §13 M1 acceptance criterion: the toy
         catalog runs to completion both interactively (``ScriptedAsker`` +
         console renderer) and via an answers file, and a second run against
         the same journal detects-and-skips every step. Strictly offline.
@details Live-renderer assertions padded for the 0.2.0 marker-alignment
         change in ``io/console.py`` (``LiveStatusRenderer``).
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path

from waegis.engine import Journal, StepStatus, build_plan, run
from waegis.io.answers import load_answers_file
from waegis.io.console import (
    LiveStatusRenderer,
    plan_preview_json,
    render_plan_preview,
    run_summary_json,
)
from waegis.io.prompts import ScriptedAsker

from _toy_catalog import act_counts, build_toy_catalog, make_ctx

# LOCAL HELPERS


def _statuses(summary) -> dict[str, StepStatus]:
    """
    @brief      Map each step id in a run summary to its terminal status.
    @param[in]  summary The :class:`~waegis.engine.runner.RunSummary` to read.
    @return     Mapping of step id to :class:`~waegis.engine.step.StepStatus`.
    """
    return {r.step_id: r.status for r in summary.results}


# TESTS


def test_toy_catalog_runs_to_completion_interactively_via_console_renderer(tmp_path: Path) -> None:
    """
    @brief      The toy catalog runs to completion with a ``ScriptedAsker``
                (interactive-shaped: plan approval + the assisted step's
                confirmation) rendered through the live console renderer and
                the plan-preview ``--json`` emitter, then journals green.
    @param[in]  tmp_path Pytest-provided temporary directory for the journal.
    @return     None
    @exception  AssertionError If the run does not complete green or the
                renderer/journal output is malformed.
    """
    catalog = build_toy_catalog()
    ctx = make_ctx()
    plan = build_plan(ctx.mode, False, catalog.plan_for(ctx), ctx)

    preview_stream = io.StringIO()
    render_plan_preview(plan, preview_stream)
    assert "toy.a" in preview_stream.getvalue()

    preview_payload = json.loads(plan_preview_json(plan))
    assert [s["id"] for s in preview_payload["steps"]] == ["toy.a", "toy.b", "toy.c"]

    live_stream = io.StringIO()
    ctx.asker = ScriptedAsker(confirms=[True, True])  # plan approval, then toy.b
    ctx.events = LiveStatusRenderer(live_stream)
    journal = Journal.begin(mode="test-interactive", wizard_version="0.1.0", home=tmp_path)

    summary = run(catalog, ctx, journal=journal)

    assert summary.ok is True
    assert _statuses(summary) == {
        "toy.a": StepStatus.DONE,
        "toy.b": StepStatus.DONE,
        "toy.c": StepStatus.DONE,
    }
    rendered = live_stream.getvalue()
    assert "[OK]   Toy A: done" in rendered
    assert "[OK]   Toy B: done" in rendered
    assert "[OK]   Toy C: done" in rendered
    assert set(journal.green_step_ids()) == {"toy.a", "toy.b", "toy.c"}


def test_toy_catalog_runs_to_completion_via_answers_file(tmp_path: Path) -> None:
    """
    @brief      The toy catalog runs to completion when the assisted step's
                confirmation is supplied via ``--answers FILE`` (loaded through
                ``io/answers.py``) instead of an interactive prompt.
    @param[in]  tmp_path Pytest-provided temporary directory for the answers
                file and journal.
    @return     None
    @exception  AssertionError If the run does not complete green.
    """
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps({"confirm_b": True}), encoding="utf-8")
    answers = load_answers_file(answers_path)

    catalog = build_toy_catalog()
    ctx = make_ctx()
    ctx.asker = ScriptedAsker(confirms=[True, bool(answers["confirm_b"])])
    journal = Journal.begin(mode="test-answers-file", wizard_version="0.1.0", home=tmp_path)

    summary = run(catalog, ctx, journal=journal)

    assert summary.ok is True
    assert _statuses(summary) == {
        "toy.a": StepStatus.DONE,
        "toy.b": StepStatus.DONE,
        "toy.c": StepStatus.DONE,
    }
    payload = json.loads(run_summary_json(summary))
    assert payload["ok"] is True
    assert [r["id"] for r in payload["results"]] == ["toy.a", "toy.b", "toy.c"]


def test_second_run_against_same_journal_detects_and_skips_every_step(tmp_path: Path) -> None:
    """
    @brief      M1 acceptance: after a completed run, re-running the same
                catalog against the same context/journal detects every step
                already green and skips it — no step re-acts.
    @param[in]  tmp_path Pytest-provided temporary directory for the journal.
    @return     None
    @exception  AssertionError If any step is not skipped or re-acts.
    """
    catalog = build_toy_catalog()
    ctx = make_ctx()
    ctx.asker = ScriptedAsker(confirms=[True, True])
    live_stream = io.StringIO()
    ctx.events = LiveStatusRenderer(live_stream)
    journal = Journal.begin(mode="test-resume", wizard_version="0.1.0", home=tmp_path)

    first = run(catalog, ctx, journal=journal)
    assert first.ok is True

    counts_after_first = act_counts(ctx)
    assert counts_after_first == {"toy.a": 1, "toy.b": 1, "toy.c": 1}

    second = run(catalog, ctx, journal=journal)

    assert second.ok is True
    assert set(_statuses(second).values()) == {StepStatus.SKIPPED}
    # No step acted again on the second, detect-and-skip run.
    assert act_counts(ctx) == counts_after_first
    assert set(journal.green_step_ids()) == {"toy.a", "toy.b", "toy.c"}
    rendered = live_stream.getvalue()
    assert rendered.count("[SKIP]") == 3


# END OF FILE
