#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_probes_machine.py
@brief Machine probe tests (OS support matrix, architecture, disk) (T2.1).
@details OS/arch tests monkeypatch ``platform.system``/``platform.release``/
         ``platform.machine`` so results are identical on Windows and Linux
         CI; disk tests monkeypatch ``shutil.disk_usage``. No test reads real
         machine state.
"""

# IMPORTS

from __future__ import annotations

import shutil

import pytest

import waegis.probes.machine as machine
from waegis.io.reports import ProbeFinding, environment_report_json

# TESTS


def test_probe_os_support_ok_for_windows_11(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Windows release "10" or "11" (both seen for Windows 11
                depending on CPython build) is inside the support matrix.
    @return     None
    @exception  AssertionError If the status is not ``"ok"``.
    """
    monkeypatch.setattr(machine.platform, "system", lambda: "Windows")
    monkeypatch.setattr(machine.platform, "release", lambda: "11")

    finding = machine.probe_os_support()

    assert finding.name == "machine.os"
    assert finding.status == "ok"
    assert "Windows 11" in finding.detail
    assert finding.guidance is None


def test_probe_os_support_ok_for_ubuntu(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Linux is reported ``"ok"`` (kernel release cannot confirm the
                distro major version, so this probe does not overclaim).
    @return     None
    @exception  AssertionError If the status is not ``"ok"``.
    """
    monkeypatch.setattr(machine.platform, "system", lambda: "Linux")
    monkeypatch.setattr(machine.platform, "release", lambda: "5.15.0-91-generic")

    finding = machine.probe_os_support()

    assert finding.status == "ok"
    assert "Linux" in finding.detail


def test_probe_os_support_warns_outside_matrix_windows_7(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A Windows release below the supported line warns, never fails.
    @return     None
    @exception  AssertionError If the status is not exactly ``"warn"``.
    """
    monkeypatch.setattr(machine.platform, "system", lambda: "Windows")
    monkeypatch.setattr(machine.platform, "release", lambda: "7")

    finding = machine.probe_os_support()

    assert finding.status == "warn"
    assert finding.status != "fail"
    assert finding.guidance is not None


def test_probe_os_support_warns_for_unknown_os(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      An OS outside Windows/Linux (e.g. macOS) warns rather than
                crashing or hard-failing.
    @return     None
    @exception  AssertionError If the status is not ``"warn"`` or guidance is
                missing.
    """
    monkeypatch.setattr(machine.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(machine.platform, "release", lambda: "23.1.0")

    finding = machine.probe_os_support()

    assert finding.status == "warn"
    assert "Darwin" in finding.guidance


def test_probe_architecture_reports_detected_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      The architecture probe reports whatever ``platform.machine()``
                returns and is always ``"ok"`` (informational, not verified).
    @return     None
    @exception  AssertionError If the arch string is dropped or the status is
                not ``"ok"``.
    """
    monkeypatch.setattr(machine.platform, "machine", lambda: "AMD64")

    finding = machine.probe_architecture()

    assert finding.name == "machine.arch"
    assert finding.status == "ok"
    assert finding.detail == "AMD64"


def test_probe_disk_space_ok_above_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Free space at or above the caller's minimum reports ``"ok"``.
    @return     None
    @exception  AssertionError If the status is not ``"ok"``.
    """
    real_usage_type = type(shutil.disk_usage("."))
    fake_usage = real_usage_type(total=100 * 1024**3, used=50 * 1024**3, free=50 * 1024**3)
    monkeypatch.setattr(machine.shutil, "disk_usage", lambda path: fake_usage)

    finding = machine.probe_disk_space(".", minimum_bytes=1024**3)

    assert finding.name == "machine.disk"
    assert finding.status == "ok"
    assert finding.guidance is None


def test_probe_disk_space_fails_below_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Free space below the caller's minimum reports ``"fail"`` with
                remediation guidance (unlike ``machine.os``, this genuinely
                blocks deployment).
    @return     None
    @exception  AssertionError If the status is not ``"fail"`` or guidance is
                missing.
    """
    real_usage_type = type(shutil.disk_usage("."))
    fake_usage = real_usage_type(total=10 * 1024**3, used=int(9.9 * 1024**3), free=100 * 1024**2)
    monkeypatch.setattr(machine.shutil, "disk_usage", lambda path: fake_usage)

    finding = machine.probe_disk_space(".", minimum_bytes=1024**3)

    assert finding.status == "fail"
    assert finding.guidance is not None


def test_machine_findings_satisfy_probe_finding_and_round_trip_json() -> None:
    """
    @brief      Every machine-probe result satisfies the ``ProbeFinding``
                protocol and round-trips through ``environment_report_json``
                without error (io/reports.py consumes probe results directly).
    @return     None
    @exception  AssertionError If a finding fails the protocol check or a
                field is dropped by the JSON round trip.
    """
    findings = [
        machine.probe_os_support(),
        machine.probe_architecture(),
        machine.probe_disk_space(".", minimum_bytes=1),
    ]
    for finding in findings:
        assert isinstance(finding, ProbeFinding)

    import json

    payload = json.loads(environment_report_json(findings))
    assert len(payload["findings"]) == 3
    assert {entry["name"] for entry in payload["findings"]} == {
        "machine.os",
        "machine.arch",
        "machine.disk",
    }


# END OF FILE
