#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file reports.py
@brief Environment report and the blocking-point ("ask IT") report (T1.3, R7).
@details Two report shapes, each with a human renderer and a ``--json`` twin:

         - **Environment report**: renders probe-style findings. This task
           defines the rendering shape only; T2.1/T2.2 (probes) supply real
           findings later. Built against :class:`ProbeFinding`, a small
           structural protocol (``name, status, detail, guidance``) so probe
           result types do not need to inherit from anything here.
         - **Blocking-point report**: the plan's exact template (quoted from
           the analysis doc, plan §4/§12) for a step the wizard could not get
           past on its own: what was attempted (the exact command), what
           happened (the exact error), why the wizard needs it, a copyable
           "ask IT" request, and which alternative paths exist.

@details **``--json`` seam (frozen per plan §15 D13).**

         - Environment report: ``{findings: [{name, status, detail, guidance},
           ...]}``.
         - Blocking-point report: ``{step_id, title, attempted, what_happened,
           why, it_request, alternatives}`` — ``alternatives`` is a JSON array
           of strings.

         These field names are a public, frozen integration contract; changing
         them is a wizard MAJOR version bump.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import IO, Any, Protocol, Sequence, runtime_checkable

# DATA MODELS / TYPEDEFINITIONS


@runtime_checkable
class ProbeFinding(Protocol):
    """
    @brief Structural stub for one environment-probe result.
    @details Deliberately minimal so T2.1/T2.2 probe result types (e.g. a
             future ``ProbeResult``) satisfy this protocol without inheriting
             from it. ``status`` is a short machine-readable token (e.g.
             ``"ok"``, ``"warn"``, ``"fail"``); ``detail`` is the one-line
             human summary; ``guidance`` is optional fix-it text shown when the
             status is not healthy.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    name: str
    status: str
    detail: str
    guidance: str | None


@dataclass(frozen=True)
class ProbeFindingRecord:
    """
    @brief Concrete :class:`ProbeFinding` implementation for direct use and
           tests.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    name: str
    status: str
    detail: str
    guidance: str | None = None


@dataclass(frozen=True)
class BlockingPointReport:
    """
    @brief IT-forwardable report for a step the wizard could not complete
           itself (plan §4/§12, R7).
    @details Field order mirrors the plan's exact template: what was
             attempted, what happened, why the wizard needs it, the copyable
             ask-IT request text, and the alternative paths available.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    step_id: str
    title: str
    attempted: str
    what_happened: str
    why: str
    it_request: str
    alternatives: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the report to the frozen JSON-safe mapping.
        @return     Mapping keyed ``step_id, title, attempted, what_happened,
                    why, it_request, alternatives``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return {
            "step_id": self.step_id,
            "title": self.title,
            "attempted": self.attempted,
            "what_happened": self.what_happened,
            "why": self.why,
            "it_request": self.it_request,
            "alternatives": list(self.alternatives),
        }


# LOCAL HELPERS


def _finding_to_dict(finding: ProbeFinding) -> dict[str, Any]:
    """
    @brief      Serialize one probe finding to a JSON-safe mapping.
    @param[in]  finding Any object satisfying the :class:`ProbeFinding` protocol.
    @return     Mapping keyed ``name, status, detail, guidance``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return {
        "name": finding.name,
        "status": finding.status,
        "detail": finding.detail,
        "guidance": finding.guidance,
    }


# PUBLIC API


def render_environment_report(findings: Sequence[ProbeFinding], stream: IO[str]) -> None:
    """
    @brief      Render probe-style environment findings as a human-readable
                table.
    @details    One row per finding: name, status, and detail; a finding whose
                ``guidance`` is set gets an indented guidance line beneath its
                row so fix-it text is visible without a second pass.
    @param[in]  findings Probe findings to render, in the given order.
    @param[in]  stream Output stream (real console or injected buffer for tests).
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    stream.write("Environment report\n")
    stream.write("-------------------\n")
    for finding in findings:
        stream.write(f"[{finding.status}] {finding.name}: {finding.detail}\n")
        if finding.guidance:
            stream.write(f"    guidance: {finding.guidance}\n")


def environment_report_to_dict(findings: Sequence[ProbeFinding]) -> dict[str, Any]:
    """
    @brief      Serialize environment findings to the frozen JSON-safe mapping.
    @param[in]  findings Probe findings to serialize, in the given order.
    @return     Mapping ``{"findings": [{name, status, detail, guidance}, ...]}``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return {"findings": [_finding_to_dict(f) for f in findings]}


def environment_report_json(findings: Sequence[ProbeFinding]) -> str:
    """
    @brief      Serialize environment findings to the frozen ``--json`` shape.
    @param[in]  findings Probe findings to serialize, in the given order.
    @return     JSON text of :func:`environment_report_to_dict`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return json.dumps(environment_report_to_dict(findings), indent=2, ensure_ascii=False)


def render_blocking_point_report(report: BlockingPointReport, stream: IO[str]) -> None:
    """
    @brief      Render the blocking-point report in the plan's fixed field
                order (plan §4/§12, R7).
    @param[in]  report The :class:`BlockingPointReport` to render.
    @param[in]  stream Output stream (real console or injected buffer for tests).
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    stream.write(f"BLOCKED: {report.title} ({report.step_id})\n")
    stream.write(f"Attempted:    {report.attempted}\n")
    stream.write(f"What happened: {report.what_happened}\n")
    stream.write(f"Why needed:   {report.why}\n")
    stream.write("Ask IT (copy the text below):\n")
    stream.write(f"  {report.it_request}\n")
    stream.write("Alternatives:\n")
    if report.alternatives:
        for alternative in report.alternatives:
            stream.write(f"  - {alternative}\n")
    else:
        stream.write("  (none known)\n")


def blocking_point_report_json(report: BlockingPointReport) -> str:
    """
    @brief      Serialize a blocking-point report to the frozen ``--json`` shape.
    @param[in]  report The :class:`BlockingPointReport` to serialize.
    @return     JSON text of ``report.to_dict()``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


# END OF FILE
