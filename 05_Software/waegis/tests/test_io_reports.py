#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_io_reports.py
@brief Environment and blocking-point report tests for the WAEGIS io layer (T1.3).
@details Strictly offline, output captured via injected ``io.StringIO``
         streams: the environment report over a fixed mixed pass/fail finding
         set, and the blocking-point report's human render (all five required
         fields, stable order) plus its ``--json`` twin (same fields, stable
         keys).
"""

# IMPORTS

from __future__ import annotations

import io
import json

from waegis.io.reports import (
    BlockingPointReport,
    ProbeFindingRecord,
    blocking_point_report_json,
    environment_report_json,
    environment_report_to_dict,
    render_blocking_point_report,
    render_environment_report,
)

# LOCAL HELPERS


def _sample_findings() -> list[ProbeFindingRecord]:
    """
    @brief      A fixed mixed pass/fail set of probe findings for tests.
    @return     Three findings: one healthy, one warning, one failing (with
                guidance).
    """
    return [
        ProbeFindingRecord(name="python", status="ok", detail="3.11.6 found", guidance=None),
        ProbeFindingRecord(name="git", status="warn", detail="1.8.3 found, >= 2.30 recommended", guidance=None),
        ProbeFindingRecord(
            name="proxy",
            status="fail",
            detail="direct HTTPS connect blocked",
            guidance="ask IT to allowlist the forge host",
        ),
    ]


def _sample_blocking_report() -> BlockingPointReport:
    """
    @brief      A fixed blocking-point report for tests.
    @return     A report for a step blocked by a corporate proxy.
    """
    return BlockingPointReport(
        step_id="net.proxy",
        title="Reachability check",
        attempted="git ls-remote https://git.example.com/aegis-template.git",
        what_happened="fatal: unable to access 'https://git.example.com/': "
        "Failed to connect to git.example.com port 443: Connection timed out",
        why="the wizard needs outbound HTTPS to clone the payload repository",
        it_request="Please allowlist outbound HTTPS to git.example.com:443 for this workstation.",
        alternatives=("use --payload PATH with a local copy", "clone manually and re-run waegis adopt"),
    )


# TESTS


def test_environment_report_renders_mixed_findings() -> None:
    """
    @brief      The environment report renders a fixed mixed pass/fail/warn
                finding set, including the guidance line for the failing entry.
    @return     None
    @exception  AssertionError If a finding's name/status/detail/guidance is
                missing from the rendered text.
    """
    stream = io.StringIO()
    render_environment_report(_sample_findings(), stream)
    text = stream.getvalue()

    assert "[ok] python: 3.11.6 found" in text
    assert "[warn] git: 1.8.3 found, >= 2.30 recommended" in text
    assert "[fail] proxy: direct HTTPS connect blocked" in text
    assert "guidance: ask IT to allowlist the forge host" in text


def test_environment_report_json_shape() -> None:
    """
    @brief      ``environment_report_json``/``environment_report_to_dict``
                expose the frozen ``{findings: [{name, status, detail,
                guidance}]}`` shape.
    @return     None
    @exception  AssertionError If a key is missing or a value mismatches.
    """
    findings = _sample_findings()
    as_dict = environment_report_to_dict(findings)
    assert set(as_dict) == {"findings"}
    assert len(as_dict["findings"]) == 3
    assert set(as_dict["findings"][0]) == {"name", "status", "detail", "guidance"}
    assert as_dict["findings"][2]["guidance"] == "ask IT to allowlist the forge host"

    payload = json.loads(environment_report_json(findings))
    assert payload == as_dict


def test_blocking_point_report_human_output_has_all_fields_in_order() -> None:
    """
    @brief      The human-readable blocking-point render contains all five
                required fields (attempted, what happened, why, ask-IT text,
                alternatives) in a stable order.
    @return     None
    @exception  AssertionError If a field is missing or out of order.
    """
    report = _sample_blocking_report()
    stream = io.StringIO()
    render_blocking_point_report(report, stream)
    text = stream.getvalue()

    order = [
        text.index(report.attempted),
        text.index(report.what_happened.splitlines()[0]),
        text.index(report.why),
        text.index(report.it_request),
        text.index(report.alternatives[0]),
    ]
    assert order == sorted(order)
    for alternative in report.alternatives:
        assert alternative in text


def test_blocking_point_report_json_shape() -> None:
    """
    @brief      ``blocking_point_report_json`` exposes the frozen ``{step_id,
                title, attempted, what_happened, why, it_request,
                alternatives}`` shape under stable keys.
    @return     None
    @exception  AssertionError If a key is missing or a value mismatches.
    """
    report = _sample_blocking_report()
    payload = json.loads(blocking_point_report_json(report))

    assert set(payload) == {
        "step_id",
        "title",
        "attempted",
        "what_happened",
        "why",
        "it_request",
        "alternatives",
    }
    assert payload["step_id"] == "net.proxy"
    assert payload["attempted"] == report.attempted
    assert payload["alternatives"] == list(report.alternatives)


def test_blocking_point_report_without_alternatives_says_so() -> None:
    """
    @brief      A report with no known alternatives renders an explicit
                "(none known)" line rather than an empty section.
    @return     None
    @exception  AssertionError If the placeholder text is absent.
    """
    report = BlockingPointReport(
        step_id="prereq.git",
        title="Git prerequisite",
        attempted="git --version",
        what_happened="'git' is not recognized as an internal or external command",
        why="the wizard needs git to initialize the target repository",
        it_request="Please install Git for Windows for this workstation.",
    )
    stream = io.StringIO()
    render_blocking_point_report(report, stream)
    assert "(none known)" in stream.getvalue()


# END OF FILE
