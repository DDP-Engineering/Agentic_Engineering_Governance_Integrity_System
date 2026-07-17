#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_io_console.py
@brief Console renderer tests for the WAEGIS io layer (T1.3).
@details Strictly offline, output captured via injected ``io.StringIO``
         streams: plan-preview render (fields/order + ``--json`` round trip),
         live step-status render (ASCII default, forced glyph set, event
         order), and the Windows-console-safety encoding fallback (a
         restrictive-encoding stream must never raise ``UnicodeEncodeError``).
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json

from waegis.engine import (
    Automation,
    Phase,
    RunSummary,
    StepFinished,
    StepResult,
    StepStarted,
    StepStatus,
    build_plan,
    run,
)
from waegis.io.console import (
    ASCII_MARKERS,
    GLYPH_MARKERS,
    LiveStatusRenderer,
    plan_preview_json,
    render_plan_preview,
    run_summary_json,
    run_summary_to_dict,
    step_result_json,
)

from _toy_catalog import build_toy_catalog, make_ctx

# LOCAL HELPERS


class _Cp1252Stream(io.StringIO):
    """
    @brief      ``io.StringIO`` that reports a restrictive ``cp1252`` encoding.
    @details    ``StringIO.write`` itself never rejects any ``str``, so the
                encoding-fallback contract is exercised by having renderers
                check ``.encoding`` proactively (as the console module does)
                rather than relying on a write-time exception.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """

    encoding = "cp1252"


# TESTS


def test_render_plan_preview_lists_all_fields_in_order() -> None:
    """
    @brief      The plan-preview table renders every step, in plan order, with
                id/title/phase/automation/change columns.
    @return     None
    @exception  AssertionError If a step id/field is missing or out of order.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = make_ctx()
    catalog = build_toy_catalog()
    plan = build_plan("test", False, catalog.plan_for(ctx), ctx)

    stream = io.StringIO()
    render_plan_preview(plan, stream)
    text = stream.getvalue()

    ids_in_order = [step.id for step in plan.steps]
    assert ids_in_order == ["toy.a", "toy.b", "toy.c"]
    last_index = -1
    for step in plan.steps:
        index = text.index(step.id)
        assert index > last_index
        last_index = index
        assert step.title in text
        assert step.phase.value in text
        assert step.automation.value in text
        assert step.change_summary in text
    assert "3 step(s) planned." in text


def test_plan_preview_json_round_trips_with_documented_keys() -> None:
    """
    @brief      ``plan_preview_json`` round-trips through ``json.loads`` with
                the frozen field names (mode, dry_run, steps[id/title/why/
                phase/automation/change_summary]).
    @return     None
    @exception  AssertionError If a documented key is missing or the value
                does not match the source plan.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = make_ctx()
    catalog = build_toy_catalog()
    plan = build_plan("test", True, catalog.plan_for(ctx), ctx)

    payload = json.loads(plan_preview_json(plan))

    assert payload["mode"] == "test"
    assert payload["dry_run"] is True
    assert [s["id"] for s in payload["steps"]] == ["toy.a", "toy.b", "toy.c"]
    first = payload["steps"][0]
    assert set(first) == {"id", "title", "why", "phase", "automation", "change_summary"}
    assert first["phase"] == Phase.P0_MACHINE.value
    assert first["automation"] == Automation.AUTO.value


def test_live_status_renderer_uses_ascii_markers_by_default() -> None:
    """
    @brief      Each ``StepStarted``/``StepFinished`` event renders exactly one
                line, in order, using the plain-ASCII marker set by default.
    @return     None
    @exception  AssertionError If a marker/line is wrong or events are dropped.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    stream = io.StringIO()
    renderer = LiveStatusRenderer(stream)
    ctx = make_ctx(sink=renderer)
    run(build_toy_catalog(), ctx)
    lines = [line for line in stream.getvalue().splitlines() if line]

    # StepStarted + StepFinished per step, in step order.
    assert len(lines) == 6
    assert lines[0] == f"{ASCII_MARKERS['running']} Toy A"
    assert lines[1] == f"{ASCII_MARKERS['done']} Toy A: done"
    assert lines[2] == f"{ASCII_MARKERS['running']} Toy B"
    assert lines[3] == f"{ASCII_MARKERS['done']} Toy B: done"
    for line in lines:
        assert "[" in line  # plain-ASCII markers only, never a glyph.


def test_forced_glyph_flag_switches_markers_not_data() -> None:
    """
    @brief      ``use_glyphs=True`` switches the rendered markers to the glyph
                set while the underlying event data (step ids/statuses) is
                unchanged.
    @return     None
    @exception  AssertionError If the glyph marker is not used, or a status is
                different from the ASCII-rendered run.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ascii_stream = io.StringIO()
    glyph_stream = io.StringIO()
    ascii_renderer = LiveStatusRenderer(ascii_stream)
    glyph_renderer = LiveStatusRenderer(glyph_stream, use_glyphs=True)
    run(build_toy_catalog(), make_ctx(sink=ascii_renderer))
    run(build_toy_catalog(), make_ctx(sink=glyph_renderer))

    ascii_lines = [line for line in ascii_stream.getvalue().splitlines() if line]
    glyph_lines = [line for line in glyph_stream.getvalue().splitlines() if line]

    assert ascii_lines[1] == f"{ASCII_MARKERS['done']} Toy A: done"
    assert glyph_lines[1] == f"{GLYPH_MARKERS['done']} Toy A: done"
    # Same step/status data underneath, only the marker glyph differs.
    ascii_status = ascii_lines[1].split(": ")[-1]
    glyph_status = glyph_lines[1].split(": ")[-1]
    assert ascii_status == glyph_status == "done"


def test_live_status_renderer_encoding_fallback_never_raises() -> None:
    """
    @brief      A stream reporting a restrictive encoding (``cp1252``) with
                ``use_glyphs=True`` never raises ``UnicodeEncodeError`` and
                still renders the expected marker/text via the ASCII fallback.
    @return     None
    @exception  AssertionError If rendering raises or omits the expected text.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    stream = _Cp1252Stream()
    renderer = LiveStatusRenderer(stream, use_glyphs=True)
    ctx = make_ctx(sink=renderer)
    run(build_toy_catalog(), ctx)  # must not raise UnicodeEncodeError

    text = stream.getvalue()
    assert ASCII_MARKERS["done"] in text
    assert "Toy A: done" in text
    assert GLYPH_MARKERS["done"] not in text


def test_step_result_json_matches_documented_keys() -> None:
    """
    @brief      ``step_result_json`` serializes the frozen ``StepResult``
                field-name contract.
    @return     None
    @exception  AssertionError If a key is missing or the id/status is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = StepResult(step_id="toy.a", status=StepStatus.DONE, detected=False, acted=True, verified=True)
    payload = json.loads(step_result_json(result))
    assert payload["id"] == "toy.a"
    assert payload["status"] == "done"
    assert set(payload) == {
        "id",
        "status",
        "detected",
        "acted",
        "verified",
        "started_at",
        "finished_at",
        "answers",
        "artifacts",
        "messages",
        "failure",
        "error",
    }


def test_run_summary_json_matches_documented_keys() -> None:
    """
    @brief      ``run_summary_json``/``run_summary_to_dict`` expose the new
                ``mode, dry_run, ok, stopped_at, results`` contract.
    @return     None
    @exception  AssertionError If a key is missing or a nested result is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = StepResult(step_id="toy.a", status=StepStatus.DONE)
    summary = RunSummary(mode="new", dry_run=False, results=[result], ok=True, stopped_at=None)

    as_dict = run_summary_to_dict(summary)
    assert set(as_dict) == {"mode", "dry_run", "ok", "stopped_at", "results"}
    assert as_dict["results"][0]["id"] == "toy.a"

    payload = json.loads(run_summary_json(summary))
    assert payload == as_dict


def test_unrecognized_events_are_ignored() -> None:
    """
    @brief      An event carrying no rendered transition (e.g. a bare
                ``StepStarted``/``StepFinished`` fed out of engine order) still
                renders deterministically without raising.
    @return     None
    @exception  AssertionError If rendering raises.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    stream = io.StringIO()
    renderer = LiveStatusRenderer(stream)
    renderer.emit(StepStarted("x", "X title", Phase.P0_MACHINE, Automation.AUTO))
    renderer.emit(StepFinished(StepResult(step_id="x", status=StepStatus.FAILED)))
    text = stream.getvalue()
    assert "X title" in text
    assert ASCII_MARKERS["fail"] in text


# END OF FILE
