#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file tools.py
@brief Tool probes: python (>=3.11), git (>=2.30), uv (informational) (T2.1).
@details Implements the ``prereq.python`` and ``prereq.git`` probes from plan
         §8.1, plus an optional ``prereq.uv`` probe. Every probe runs commands
         only through the injectable
         :class:`waegis.probes.runner.CommandRunner` (never ``subprocess``
         directly) and returns a
         :class:`waegis.io.reports.ProbeFindingRecord`, so it slots directly
         into :func:`waegis.io.reports.render_environment_report` /
         :func:`waegis.io.reports.environment_report_json`.
@details The python probe tries ``py -3``, ``python3``, ``python`` in that
         order (plan §8.1) and stops at the first candidate whose executable
         is found *and* runs to a zero exit code; a candidate that is not
         found, or is found but exits non-zero (e.g. a ``py`` launcher with no
         Python 3 registered), falls through to the next candidate rather than
         failing the whole probe. Version text is read from both stdout and
         stderr (``CommandResult.combined_output``) since older interpreters
         and some launcher variants report ``--version`` on stderr.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import platform
import re

from waegis.io.reports import ProbeFindingRecord
from waegis.probes.runner import CommandRunner
from waegis.runtime import python_probe_candidates

# CONSTANTS

# @brief Python launcher candidates tried in order (plan §8.1 ``prereq.python``).

# @brief Minimum supported Python / git versions (plan §8.1).
_MIN_PYTHON: tuple[int, int] = (3, 11)
_MIN_GIT: tuple[int, int] = (2, 30)

_PYTHON_VERSION_RE = re.compile(r"Python\s+(\d+)\.(\d+)(?:\.(\d+))?")
_GIT_VERSION_RE = re.compile(r"git version\s+(\d+)\.(\d+)(?:\.(\d+))?")
_UV_VERSION_RE = re.compile(r"uv\s+(\d+)\.(\d+)(?:\.(\d+))?")


# HELPER FUNCTIONS


def _parse_version(text: str, pattern: re.Pattern[str]) -> tuple[int, int, int] | None:
    """
    @brief      Parse a major/minor(/patch) version out of free-form tool
                output.
    @param[in]  text Raw combined stdout/stderr text from a ``--version`` run.
    @param[in]  pattern Compiled regex with three groups: major, minor, and an
                optional patch.
    @return     ``(major, minor, patch)`` (patch defaults to ``0`` when the
                third group is absent), or ``None`` if ``pattern`` does not
                match anywhere in ``text``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    match = pattern.search(text)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def _format_version(version: tuple[int, int, int]) -> str:
    """
    @brief      Render a parsed version tuple as a dotted string.
    @param[in]  version Parsed ``(major, minor, patch)`` tuple.
    @return     Dotted version string, e.g. ``"3.11.9"``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return ".".join(str(part) for part in version)


def _install_guidance(tool: str, system: str) -> str:
    """
    @brief      OS-keyed install guidance with a concrete, copyable command.
    @param[in]  tool One of ``"python"``, ``"git"``, ``"uv"``.
    @param[in]  system A ``platform.system()`` value (``"Windows"``,
                ``"Linux"``, or anything else, e.g. ``"Darwin"``); an unknown
                value falls back to generic guidance rather than raising.
    @return     One or two sentences: what to run, and why it is safe to run.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    table: dict[str, dict[str, str]] = {
        "python": {
            "Windows": "Install Python 3.11 or newer: winget install --id Python.Python.3.11 -e "
            "(or download from python.org and check \"Add python.exe to PATH\").",
            "Linux": "Install Python 3.11 or newer: sudo apt-get update && "
            "sudo apt-get install -y python3.11 python3.11-venv",
            "_default": "Install Python 3.11 or newer from https://www.python.org/downloads/ "
            "and make sure it is on your PATH.",
        },
        "git": {
            "Windows": "Install Git: winget install --id Git.Git -e",
            "Linux": "Install Git: sudo apt-get update && sudo apt-get install -y git",
            "_default": "Install Git 2.30 or newer from https://git-scm.com/downloads.",
        },
        "uv": {
            "Windows": "Optional: winget install --id astral-sh.uv -e "
            "(uv speeds up dependency installs; WAEGIS works without it).",
            "Linux": "Optional: curl -LsSf https://astral.sh/uv/install.sh | sh "
            "(uv speeds up dependency installs; WAEGIS works without it).",
            "_default": "uv is optional; see https://docs.astral.sh/uv/getting-started/installation/ "
            "if you want it.",
        },
    }
    tool_table = table[tool]
    return tool_table.get(system, tool_table["_default"])


# PUBLIC API


def probe_python(runner: CommandRunner) -> ProbeFindingRecord:
    """
    @brief      Detect a usable Python 3.11+ interpreter, trying ``py -3``,
                ``python3``, ``python`` in that order (plan §8.1
                ``prereq.python``).
    @param[in]  runner Injectable :class:`CommandRunner` used for every
                invocation; no probe calls ``subprocess`` directly.
    @return     A ``prereq.python`` :class:`ProbeFindingRecord`: ``"ok"`` when
                a candidate reports >= 3.11, ``"fail"`` when the best
                candidate found is older or no candidate is found at all, or
                ``"warn"`` when a candidate runs but its version text cannot
                be parsed (degrades gracefully rather than crashing).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    system = platform.system()
    candidates = python_probe_candidates()
    for candidate in candidates:
        result = runner.run((*candidate, "--version"))
        if not result.ok():
            continue
        label = " ".join(candidate)
        output = result.combined_output().strip()
        version = _parse_version(output, _PYTHON_VERSION_RE)
        if version is None:
            return ProbeFindingRecord(
                name="prereq.python",
                status="warn",
                detail=f"'{label} --version' produced unparseable output: {output!r}",
                guidance=_install_guidance("python", system),
            )
        detail = f"{label} -> Python {_format_version(version)}"
        if version >= (*_MIN_PYTHON, 0):
            return ProbeFindingRecord(name="prereq.python", status="ok", detail=detail, guidance=None)
        return ProbeFindingRecord(
            name="prereq.python",
            status="fail",
            detail=f"{detail} (>= {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]} required)",
            guidance=_install_guidance("python", system),
        )
    return ProbeFindingRecord(
        name="prereq.python",
        status="fail",
        detail="no usable Python launcher found (tried: "
        + ", ".join(" ".join(candidate) for candidate in candidates)
        + ")",
        guidance=_install_guidance("python", system),
    )


def probe_git(runner: CommandRunner) -> ProbeFindingRecord:
    """
    @brief      Detect ``git`` and verify its version (plan §8.1
                ``prereq.git``: >= 2.30).
    @param[in]  runner Injectable :class:`CommandRunner`.
    @return     A ``prereq.git`` :class:`ProbeFindingRecord`: ``"ok"`` when
                found and >= 2.30, ``"fail"`` when too old or not found, or
                ``"warn"`` when found but the version text is unparseable.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    system = platform.system()
    result = runner.run(("git", "--version"))
    if not result.ok():
        return ProbeFindingRecord(
            name="prereq.git",
            status="fail",
            detail="git was not found",
            guidance=_install_guidance("git", system),
        )
    output = result.combined_output().strip()
    version = _parse_version(output, _GIT_VERSION_RE)
    if version is None:
        return ProbeFindingRecord(
            name="prereq.git",
            status="warn",
            detail=f"'git --version' produced unparseable output: {output!r}",
            guidance=_install_guidance("git", system),
        )
    detail = f"git {_format_version(version)}"
    if version >= (*_MIN_GIT, 0):
        return ProbeFindingRecord(name="prereq.git", status="ok", detail=detail, guidance=None)
    return ProbeFindingRecord(
        name="prereq.git",
        status="fail",
        detail=f"{detail} (>= {_MIN_GIT[0]}.{_MIN_GIT[1]} required)",
        guidance=_install_guidance("git", system),
    )


def probe_uv(runner: CommandRunner) -> ProbeFindingRecord:
    """
    @brief      Detect the optional ``uv`` tool (plan §8.1: informational,
                never blocking — uv is optional).
    @param[in]  runner Injectable :class:`CommandRunner`.
    @return     A ``prereq.uv`` :class:`ProbeFindingRecord`: ``"ok"`` when
                found with a parseable version, ``"info"`` when not found (not
                a failure), or ``"warn"`` when found but unparseable.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    system = platform.system()
    result = runner.run(("uv", "--version"))
    if not result.ok():
        return ProbeFindingRecord(
            name="prereq.uv",
            status="info",
            detail="uv was not found (optional)",
            guidance=_install_guidance("uv", system),
        )
    output = result.combined_output().strip()
    version = _parse_version(output, _UV_VERSION_RE)
    if version is None:
        return ProbeFindingRecord(
            name="prereq.uv",
            status="warn",
            detail=f"'uv --version' produced unparseable output: {output!r}",
            guidance=_install_guidance("uv", system),
        )
    return ProbeFindingRecord(
        name="prereq.uv", status="ok", detail=f"uv {_format_version(version)}", guidance=None
    )


# END OF FILE
