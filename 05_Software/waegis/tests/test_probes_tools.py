#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_probes_tools.py
@brief Tool probe tests: python (fallback order), git, node, uv (T2.1).
@details Strictly offline: every case uses :class:`FakeCommandRunner` from
         ``_fake_command_runner.py``, never a real subprocess. Covers, for
         each probe family, version-compliant / too-old / not-found /
         unparseable-output outcomes, the documented python fallback order
         (``py -3`` -> ``python3`` -> ``python``), and that Windows/Ubuntu
         install guidance differs and each names a concrete command.
@details ``probe_node`` (added 0.1.1, architecture-review follow-up) is
         warn-not-block like ``uv``, but unlike ``uv`` its absence is a
         ``"warn"`` (visible, since hooks depend on it) rather than a mere
         ``"info"`` (uv is a pure performance optional).
"""

# IMPORTS

from __future__ import annotations

import json

import pytest

import waegis.probes.tools as tools
from waegis.io.reports import ProbeFinding, environment_report_json

from _fake_command_runner import FakeCommandRunner, failing_result, not_found_result, ok_result

# TESTS

# --- python probe -----------------------------------------------------------


def test_probe_python_ok_via_py_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A compliant version reported by ``py -3`` is accepted directly
                (first candidate in the fallback order).
    @return     None
    @exception  AssertionError If status is not ``"ok"`` or the wrong
                candidate is credited.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner(
        {("py", "-3", "--version"): ok_result(stdout="Python 3.11.9\n")}
    )

    finding = tools.probe_python(runner)

    assert finding.name == "prereq.python"
    assert finding.status == "ok"
    assert "py -3" in finding.detail
    assert "3.11.9" in finding.detail
    assert runner.calls == [("py", "-3", "--version")]


def test_probe_python_falls_back_through_candidates_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      When ``py -3`` is not found and ``python3`` exits non-zero, the
                probe falls through to ``python`` (documented fallback order).
    @return     None
    @exception  AssertionError If the fallback order is not followed or the
                wrong candidate's version is reported.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner(
        {
            ("py", "-3", "--version"): not_found_result(),
            ("python3", "--version"): failing_result(exit_code=1, stderr="not registered"),
            ("python", "--version"): ok_result(stdout="Python 3.12.1\n"),
        }
    )

    finding = tools.probe_python(runner)

    assert finding.status == "ok"
    assert "3.12.1" in finding.detail
    assert runner.calls == [
        ("py", "-3", "--version"),
        ("python3", "--version"),
        ("python", "--version"),
    ]


def test_probe_python_fails_when_found_version_too_old(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A found interpreter below 3.11 fails with install guidance.
    @return     None
    @exception  AssertionError If status is not ``"fail"`` or guidance absent.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner(
        {
            ("py", "-3", "--version"): not_found_result(),
            ("python3", "--version"): ok_result(stdout="Python 3.9.2\n"),
        }
    )

    finding = tools.probe_python(runner)

    assert finding.status == "fail"
    assert "3.9.2" in finding.detail
    assert finding.guidance is not None
    assert "apt-get" in finding.guidance


def test_probe_python_fails_when_no_candidate_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      No candidate found at all fails with install guidance, naming
                every candidate tried.
    @return     None
    @exception  AssertionError If status is not ``"fail"`` or candidates are
                not named.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner({})

    finding = tools.probe_python(runner)

    assert finding.status == "fail"
    assert "py -3" in finding.detail
    assert "python3" in finding.detail
    assert "python" in finding.detail
    assert finding.guidance is not None


def test_probe_python_degrades_to_warning_on_unparseable_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A found, zero-exit candidate with unparseable ``--version``
                output degrades to a ``"warn"`` finding rather than crashing.
    @return     None
    @exception  AssertionError If status is not exactly ``"warn"`` or the
                function raises.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner({("py", "-3", "--version"): ok_result(stdout="py launcher 3.x\n")})

    finding = tools.probe_python(runner)

    assert finding.status == "warn"
    assert finding.guidance is not None


def test_probe_python_reads_version_from_stderr_when_stdout_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Version text landing on stderr (legacy interpreter behavior)
                is still parsed via ``combined_output``.
    @return     None
    @exception  AssertionError If the version on stderr is missed.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner(
        {("py", "-3", "--version"): ok_result(stdout="", stderr="Python 3.11.2\n")}
    )

    finding = tools.probe_python(runner)

    assert finding.status == "ok"
    assert "3.11.2" in finding.detail


# --- git probe ---------------------------------------------------------------


def test_probe_git_ok_with_real_world_windows_version_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      The git probe parses the real ``git version 2.43.0.windows.1``
                output shape and accepts it (>= 2.30).
    @return     None
    @exception  AssertionError If status is not ``"ok"``.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner(
        {("git", "--version"): ok_result(stdout="git version 2.43.0.windows.1\n")}
    )

    finding = tools.probe_git(runner)

    assert finding.name == "prereq.git"
    assert finding.status == "ok"
    assert "2.43.0" in finding.detail


def test_probe_git_fails_when_too_old(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A found git below 2.30 fails with install guidance.
    @return     None
    @exception  AssertionError If status is not ``"fail"``.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner({("git", "--version"): ok_result(stdout="git version 1.8.3.1\n")})

    finding = tools.probe_git(runner)

    assert finding.status == "fail"
    assert finding.guidance is not None


def test_probe_git_fails_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A missing git executable fails with install guidance.
    @return     None
    @exception  AssertionError If status is not ``"fail"`` or guidance absent.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner({})

    finding = tools.probe_git(runner)

    assert finding.status == "fail"
    assert finding.guidance is not None


def test_probe_git_warns_on_unparseable_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Unparseable git version output degrades to a warning, not a
                crash.
    @return     None
    @exception  AssertionError If status is not exactly ``"warn"``.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner({("git", "--version"): ok_result(stdout="unexpected output\n")})

    finding = tools.probe_git(runner)

    assert finding.status == "warn"


# --- node probe ----------------------------------------------------------


def test_probe_node_ok_when_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A found, parseable node version reports ``"ok"``.
    @return     None
    @exception  AssertionError If status is not ``"ok"``.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner({("node", "--version"): ok_result(stdout="v22.9.0\n")})

    finding = tools.probe_node(runner)

    assert finding.name == "prereq.node"
    assert finding.status == "ok"
    assert "22.9.0" in finding.detail


def test_probe_node_absence_is_a_warning_not_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A missing node is reported as ``"warn"``, never ``"fail"``
                (warn-not-block, unlike ``prereq.python``/``prereq.git``).
    @return     None
    @exception  AssertionError If the status implies a hard failure.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner({})

    finding = tools.probe_node(runner)

    assert finding.status == "warn"
    assert finding.guidance is not None


def test_probe_node_warns_on_unparseable_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Unparseable node version output degrades to a warning, not a
                crash.
    @return     None
    @exception  AssertionError If status is not exactly ``"warn"``.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner({("node", "--version"): ok_result(stdout="unexpected output\n")})

    finding = tools.probe_node(runner)

    assert finding.status == "warn"


def test_probe_node_warns_below_the_supported_major(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A node older than :data:`tools._MIN_NODE` is reported.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If an old node passes as ``"ok"``.
    @details    The adapters use `node:`-prefixed builtin imports,
                `import.meta.url`, and nullish coalescing. On an interpreter
                too old for those, a guard fails as a syntax error at launch —
                which a host reads as a *non-blocking* hook error, letting the
                tool call through. Naming the floor here turns a silent bypass
                into a setup-time message.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner({("node", "--version"): ok_result(stdout="v14.21.3\n")})

    finding = tools.probe_node(runner)

    assert finding.status == "warn"
    assert "14.21.3" in finding.detail
    assert "18" in finding.detail
    assert finding.guidance is not None


def test_probe_node_accepts_exactly_the_supported_major(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      The floor itself is supported, not one release above it.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If the boundary version is rejected.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    floor = f"v{tools._MIN_NODE[0]}.{tools._MIN_NODE[1]}.0\n"
    runner = FakeCommandRunner({("node", "--version"): ok_result(stdout=floor)})

    assert tools.probe_node(runner).status == "ok"


def test_probe_node_never_fails_whatever_the_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      No ``probe_node`` outcome is ever ``"fail"``.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If any outcome would stop the wizard.
    @details    The engine stops the whole run at the first non-green step and
                offers no override, so a `"fail"` here would make AEGIS
                undeployable for an OpenCode-only project — OpenCode runs the
                guard plugin in its own runtime and needs no system Node. The
                message carries the security consequence instead; the severity
                stays recoverable because installing Node afterwards fixes it
                with no repair or re-run.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    for stdout, found in [("v22.9.0\n", True), ("v14.0.0\n", True), ("garbage\n", True), ("", False)]:
        runner = FakeCommandRunner(
            {("node", "--version"): ok_result(stdout=stdout) if found else not_found_result()}
        )

        assert tools.probe_node(runner).status != "fail"


def test_probe_node_states_the_security_consequence(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A missing node explains that guards run unchecked, not merely
                that hooks are unavailable.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If the consequence is not stated.
    @details    Because the finding never blocks, its text is the only thing
                that makes an operator act. "Hooks will not run" reads like a
                missing convenience; the real outcome is that guarded tool
                calls proceed without being checked at all.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner({("node", "--version"): not_found_result()})

    detail = tools.probe_node(runner).detail

    assert "unchecked" in detail


# --- uv probe ------------------------------------------------------------


def test_probe_uv_ok_when_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A found, parseable uv version reports ``"ok"``.
    @return     None
    @exception  AssertionError If status is not ``"ok"``.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner({("uv", "--version"): ok_result(stdout="uv 0.4.18\n")})

    finding = tools.probe_uv(runner)

    assert finding.name == "prereq.uv"
    assert finding.status == "ok"
    assert "0.4.18" in finding.detail


def test_probe_uv_absence_is_informational_not_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A missing uv is reported as ``"info"``, never as a failing
                status, since uv is optional per the plan.
    @return     None
    @exception  AssertionError If the status implies a failure.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Windows")
    runner = FakeCommandRunner({})

    finding = tools.probe_uv(runner)

    assert finding.status not in {"fail", "warn"}
    assert finding.status == "info"


# --- OS-keyed guidance --------------------------------------------------------


@pytest.mark.parametrize("tool", ["python", "git", "node", "uv"])
def test_install_guidance_differs_between_windows_and_ubuntu(tool: str) -> None:
    """
    @brief      Windows and Ubuntu/Debian guidance differ and each names a
                concrete install command for every tool.
    @return     None
    @exception  AssertionError If the two texts match or lack a command.
    """
    windows_guidance = tools._install_guidance(tool, "Windows")
    linux_guidance = tools._install_guidance(tool, "Linux")

    assert windows_guidance != linux_guidance
    assert "winget" in windows_guidance or "python.org" in windows_guidance or "git-scm" in windows_guidance
    assert "apt-get" in linux_guidance or "curl" in linux_guidance


def test_install_guidance_falls_back_for_unknown_os() -> None:
    """
    @brief      An unrecognized OS gets generic guidance instead of crashing.
    @return     None
    @exception  AssertionError If the call raises or returns empty text.
    """
    guidance = tools._install_guidance("python", "Darwin")
    assert guidance
    assert "python.org" in guidance


# --- ProbeFinding contract ----------------------------------------------------


def test_tool_findings_satisfy_probe_finding_and_round_trip_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Every tool-probe result satisfies ``ProbeFinding`` and
                round-trips through ``environment_report_json``.
    @return     None
    @exception  AssertionError If a finding fails the protocol check or a
                field is dropped by the JSON round trip.
    """
    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    runner = FakeCommandRunner(
        {
            ("py", "-3", "--version"): not_found_result(),
            ("python3", "--version"): ok_result(stdout="Python 3.11.6\n"),
            ("git", "--version"): ok_result(stdout="git version 2.43.0\n"),
            ("node", "--version"): ok_result(stdout="v22.9.0\n"),
            ("uv", "--version"): not_found_result(),
        }
    )

    findings = [
        tools.probe_python(runner),
        tools.probe_git(runner),
        tools.probe_node(runner),
        tools.probe_uv(runner),
    ]
    for finding in findings:
        assert isinstance(finding, ProbeFinding)

    payload = json.loads(environment_report_json(findings))
    assert {entry["name"] for entry in payload["findings"]} == {
        "prereq.python",
        "prereq.git",
        "prereq.node",
        "prereq.uv",
    }


# END OF FILE
