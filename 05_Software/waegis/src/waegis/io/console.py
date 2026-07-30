#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file console.py
@brief Console renderer: plan preview table, live step status, ``--json`` twins.
@details Plain-ASCII-safe console frontend (plan §5, T1.3): a plan-preview table
         renderer the operator approves before any mutation, and a live
         :class:`~waegis.engine.step.EventSink` implementation that renders each
         step's ``pending -> running -> detected-skip/done/failed`` transition as
         the runner's event stream arrives. Neither renderer imports from
         ``engine/`` for anything but reading result/event/plan data — the engine
         never imports this module (T1.1 boundary).
@details **Encoding and glyph policy.** The default marker set is plain ASCII
         (``[OK]``/``[FAIL]``/``[SKIP]``/``[..]``) so a Windows ``cmd.exe`` or
         PowerShell host without a UTF-8 code page never sees mojibake. A richer
         glyph set is used only when a caller explicitly opts in via
         ``use_glyphs=True`` (plan §5: "explicitly told the terminal supports
         it"); even then, every write is checked against the target stream's
         reported encoding (``sys.stdout.encoding`` or equivalent) and silently
         falls back to the ASCII glyph for that call if it would not encode, so
         a live render can never raise ``UnicodeEncodeError``.
@details **``--json`` seam (plan §5, frozen per §15 D13).** The plan-preview and
         step-result JSON emitters serialize the existing frozen ``to_dict()``
         shapes from ``engine/plan.py`` and ``engine/step.py`` verbatim:

         - Plan preview: ``{mode, dry_run, steps: [{id, title, why, phase,
           automation, change_summary}, ...]}``.
         - Step result: ``{id, status, detected, acted, verified, started_at,
           finished_at, answers, artifacts, messages, failure, error}``.
         - Run summary (new field-name contract introduced here, since
           ``RunSummary`` itself has no ``to_dict``): ``{mode, dry_run, ok,
           stopped_at, results: [<step result>, ...]}``.

         These field names are a public, frozen integration contract (the
         WADORE seam); changing them is a wizard MAJOR version bump.
@details **Layout (added 0.2.0).** Markers are left-padded to their set's
         widest entry (``_ASCII_MARKER_WIDTH``/``_GLYPH_MARKER_WIDTH``) so
         step titles line up in one column regardless of status, and
         ``LiveStatusRenderer`` prints a centered ``=== <phase> ===`` banner
         whenever the run enters a new :class:`~waegis.engine.step.Phase`, so
         the live log reads as grouped sections rather than one
         undifferentiated stream of lines.
@author Eng. Dan Dumitru Pasare
@date 2026-07-18
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import json
from typing import IO, Any

from ..engine.plan import Plan
from ..engine.runner import RunSummary
from ..engine.step import EngineEvent, Phase, StepFinished, StepResult, StepStarted, StepStatus

# CONSTANTS

# @brief Default plain-ASCII marker set (Windows-console safe). Keys are the
#        renderer's own transition vocabulary, not ``StepStatus`` values, since
#        "running" has no dedicated engine status (it is the in-flight window
#        between ``StepStarted`` and ``StepFinished``).
ASCII_MARKERS: dict[str, str] = {
    "pending": "[..]",
    "running": "[..]",
    "done": "[OK]",
    "skip": "[SKIP]",
    "fail": "[FAIL]",
}

# @brief Richer glyph marker set, used only when a caller opts in explicitly
#        (``use_glyphs=True``) and the target stream's encoding accepts it.
GLYPH_MARKERS: dict[str, str] = {
    "pending": "○",  # ○
    "running": "…",  # …
    "done": "✓",  # ✓
    "skip": "⏭",  # ⏭
    "fail": "✗",  # ✗
}

# @brief Column width every marker is left-padded to so step titles line up
#        under one another regardless of which marker (``[..]``/``[OK]``/
#        ``[SKIP]``/``[FAIL]``) is printed. Computed per marker set, since the
#        glyph set's entries are all one display column wide and padding them
#        to the ASCII width would misalign rather than help.
_ASCII_MARKER_WIDTH = max(len(marker) for marker in ASCII_MARKERS.values())
_GLYPH_MARKER_WIDTH = max(len(marker) for marker in GLYPH_MARKERS.values())

# @brief Map an engine ``StepStatus`` to a marker key above.
_STATUS_MARKER_KEY: dict[StepStatus, str] = {
    StepStatus.PENDING: "pending",
    StepStatus.DONE: "done",
    StepStatus.SKIPPED: "skip",
    StepStatus.FAILED: "fail",
    StepStatus.DECLINED: "fail",
    StepStatus.BLOCKED: "fail",
    StepStatus.NOT_APPLICABLE: "skip",
}

# @brief Plan-preview table column headers, in render order.
_PLAN_COLUMNS: tuple[str, ...] = ("ID", "TITLE", "PHASE", "AUTOMATION", "CHANGE")


# HELPER FUNCTIONS


def _stream_encoding(stream: IO[str]) -> str:
    """
    @brief      Resolve the encoding a stream reports, defaulting to UTF-8.
    @param[in]  stream Target output stream (real console or injected buffer).
    @return     The stream's ``encoding`` attribute, or ``"utf-8"`` if absent
                or falsy (e.g. an ``io.StringIO`` in tests).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return getattr(stream, "encoding", None) or "utf-8"


def _encodable(text: str, encoding: str) -> bool:
    """
    @brief      Report whether ``text`` can be encoded with ``encoding``.
    @param[in]  text Candidate text (typically a marker glyph).
    @param[in]  encoding Target codec name.
    @return     ``True`` when encoding succeeds; ``False`` on any encoding
                failure or unknown codec name.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _column_widths(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[int]:
    """
    @brief      Compute per-column widths from header and cell content.
    @details    Sized from actual content rather than terminal width, so
                rendered output (and its tests) is deterministic regardless of
                the host console's reported size.
    @param[in]  headers Column header labels.
    @param[in]  rows Row cell tuples, one per plan/step entry.
    @return     Column widths, one per header, each at least the header length.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    return widths


def _write_table(stream: IO[str], headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    """
    @brief      Render a simple fixed-width, space-padded ASCII table.
    @param[in]  stream Output stream the table is written to.
    @param[in]  headers Column header labels.
    @param[in]  rows Row cell tuples.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    widths = _column_widths(headers, rows)

    def _line(cells: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(width) for cell, width in zip(cells, widths))

    stream.write(_line(headers) + "\n")
    stream.write("-" * (sum(widths) + 2 * (len(widths) - 1)) + "\n")
    for row in rows:
        stream.write(_line(row) + "\n")


# PUBLIC API


def render_plan_preview(plan: Plan, stream: IO[str]) -> None:
    """
    @brief      Render the ordered plan-preview table ("terraform plan" style,
                plan §4 item 4).
    @details    One row per planned step: id, title, phase, automation kind, and
                the change each will make. This is what the operator approves
                before any mutation; ``--dry-run`` stops right after this render.
    @param[in]  plan The :class:`~waegis.engine.plan.Plan` to render.
    @param[in]  stream Output stream (real console or injected buffer for tests).
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.2.0
    """
    stream.write(f"WAEGIS plan preview - mode={plan.mode} dry_run={plan.dry_run}\n")
    rows = [
        (
            step.id,
            step.title,
            step.phase.value,
            step.automation.value,
            step.change_summary,
        )
        for step in plan.steps
    ]
    _write_table(stream, _PLAN_COLUMNS, rows)
    for mutation in plan.additional_mutations:
        stream.write(f"Additional mutation: {mutation}\n")
    stream.write(f"{len(plan.steps)} step(s) planned.\n\n")


def plan_preview_json(plan: Plan) -> str:
    """
    @brief      Serialize a plan preview to the frozen ``--json`` shape.
    @param[in]  plan The :class:`~waegis.engine.plan.Plan` to serialize.
    @return     JSON text of ``plan.to_dict()`` (see module docstring for the
                field-name contract).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)


def step_result_json(result: StepResult) -> str:
    """
    @brief      Serialize one step result to the frozen ``--json`` shape.
    @param[in]  result The :class:`~waegis.engine.step.StepResult` to serialize.
    @return     JSON text of ``result.to_dict()``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def run_summary_to_dict(summary: RunSummary) -> dict[str, Any]:
    """
    @brief      Serialize a whole run's outcome to a JSON-safe mapping.
    @param[in]  summary The :class:`~waegis.engine.runner.RunSummary` to
                serialize.
    @return     Mapping keyed ``mode, dry_run, ok, stopped_at, results`` (see
                module docstring for the field-name contract).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return {
        "mode": summary.mode,
        "dry_run": summary.dry_run,
        "ok": summary.ok,
        "stopped_at": summary.stopped_at,
        "results": [r.to_dict() for r in summary.results],
    }


def run_summary_json(summary: RunSummary) -> str:
    """
    @brief      Serialize a whole run's outcome to the frozen ``--json`` shape.
    @param[in]  summary The :class:`~waegis.engine.runner.RunSummary` to
                serialize.
    @return     JSON text of :func:`run_summary_to_dict`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return json.dumps(run_summary_to_dict(summary), indent=2, ensure_ascii=False)


class LiveStatusRenderer:
    """
    @brief Live :class:`~waegis.engine.step.EventSink` that renders each step's
           status transition as the runner's event stream arrives.
    @details Writes one line on ``StepStarted`` (the ``running`` transition) and
             one line on ``StepFinished`` (the terminal ``detected-skip / done /
             failed`` transition), using the plain-ASCII marker set by default.
             Passing ``use_glyphs=True`` switches to the richer glyph set
             without changing which events are rendered or their order; a
             per-write encoding check falls back to the ASCII glyph for that
             call if the target stream cannot encode it, so this renderer never
             raises ``UnicodeEncodeError``.
    @details Tracks the active :class:`~waegis.engine.step.Phase` and prints a
             ``_phase_banner`` line ahead of the first ``StepStarted`` of each
             new phase (added 0.2.0), so the output reads as grouped sections.
             No leading blank line is added before a banner: this renderer's
             only current caller (``_ConsoleRunSink``) already writes one
             after every finished step's messages.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-18
    @version 0.2.0
    """

    def __init__(self, stream: IO[str], *, use_glyphs: bool = False) -> None:
        """
        @brief      Construct a live status renderer over an output stream.
        @param[in]  stream Output stream (real console or injected buffer).
        @param[in]  use_glyphs When true, prefer the richer glyph marker set;
                    still falls back per-call to ASCII if unencodable.
        @return     None
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-18
        @version    0.2.0
        """
        self._stream = stream
        self._use_glyphs = use_glyphs
        self._titles: dict[str, str] = {}
        self._current_phase: Phase | None = None

    def _marker(self, key: str) -> str:
        """
        @brief      Resolve the padded marker text for one transition key.
        @details    Uses the glyph set only when ``use_glyphs`` is set and the
                    target stream's encoding can represent it; otherwise (or on
                    an unencodable glyph) falls back to the ASCII marker. Either
                    way the result is left-padded to that set's widest marker,
                    so the step title starting after it lines up in the same
                    column on every printed line.
        @param[in]  key One of ``pending, running, done, skip, fail``.
        @return     The padded marker text to print.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-18
        @version    0.2.0
        """
        if self._use_glyphs:
            glyph = GLYPH_MARKERS[key]
            if _encodable(glyph, _stream_encoding(self._stream)):
                return glyph.ljust(_GLYPH_MARKER_WIDTH)
        return ASCII_MARKERS[key].ljust(_ASCII_MARKER_WIDTH)

    def _phase_banner(self, phase: Phase) -> str:
        """
        @brief      Build the section banner printed when the run enters a new
                    phase, so the step log reads as grouped sections rather
                    than one undifferentiated wall of lines.
        @param[in]  phase The phase the run just entered.
        @return     The centered ``=== <phase> ===``-style banner line
                    (newline-terminated, no leading blank line — the caller
                    is responsible for spacing before it, if any).
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-18
        @version    0.1.0
        """
        label = f" {phase.value} "
        return f"{label:=^60}\n"

    def emit(self, event: EngineEvent) -> None:
        """
        @brief      Render one engine event, if it carries a step transition.
        @details    On ``StepStarted``, additionally prints a phase banner
                    first if the event's phase differs from the last one
                    rendered (see :meth:`_phase_banner`).
        @param[in]  event The emitted :class:`~waegis.engine.step.EngineEvent`.
        @return     None
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-18
        @version    0.2.0
        """
        if isinstance(event, StepStarted):
            self._titles[event.step_id] = event.title
            if event.phase != self._current_phase:
                # No leading blank line here: this renderer's only current
                # caller (``_ConsoleRunSink``) already writes one after every
                # finished step's messages, so adding another would double
                # the gap before each new phase banner.
                self._stream.write(self._phase_banner(event.phase))
                self._current_phase = event.phase
            self._stream.write(f"{self._marker('running')} {event.title}\n")
            return
        if isinstance(event, StepFinished):
            title = self._titles.get(event.result.step_id, event.result.step_id)
            key = _STATUS_MARKER_KEY.get(event.result.status, "pending")
            self._stream.write(f"{self._marker(key)} {title}: {event.result.status.value}\n")


# END OF FILE
