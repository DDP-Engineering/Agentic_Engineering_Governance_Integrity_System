#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file machine.py
@brief Machine probes: OS/version support matrix, architecture, free disk (T2.1).
@details Implements the ``machine.os`` and ``machine.disk`` probes from plan
         §8.1, plus an architecture probe used to enrich the environment
         report. Every probe returns a
         :class:`waegis.io.reports.ProbeFindingRecord` so it slots directly
         into :func:`waegis.io.reports.render_environment_report` /
         :func:`waegis.io.reports.environment_report_json` with no adapter.
@details Reads real machine state only through ``platform.system()``,
         ``platform.release()``, ``platform.machine()``, and
         ``shutil.disk_usage()`` — never through a probe-specific abstraction —
         so tests can monkeypatch the ``platform``/``shutil`` module functions
         directly and pass identically on Windows and Linux CI.
@details The support matrix (plan §8.1: Windows 11, Ubuntu 22+) is
         **warn-not-block** per plan §8.1/§10.1: an OS outside the matrix never
         raises above ``warn``. Kernel ``platform.release()`` on Linux does not
         carry the distro version (e.g. Ubuntu 22.04), so this probe reports
         what it can verify (the kernel string) and does not claim to confirm
         an Ubuntu major version it cannot see; only a Windows release clearly
         below the supported line is downgraded to ``warn``.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import platform
import shutil
from os import PathLike

from waegis.io.reports import ProbeFindingRecord

# CONSTANTS

# @brief Windows ``platform.release()`` values considered within the support
#        matrix. Python's ``platform.release()`` reports "10" for both
#        Windows 10 and Windows 11 builds on many CPython versions, so "10" is
#        accepted alongside the "11" some builds now report; anything older
#        (e.g. "7", "8", "8.1", "Vista") is outside the matrix.
_SUPPORTED_WINDOWS_RELEASES: frozenset[str] = frozenset({"10", "11"})

# @brief Bytes per gibibyte, used to render human-readable disk sizes.
_GIBIBYTE = 1024**3


# HELPER FUNCTIONS


def _os_guidance(system: str) -> str:
    """
    @brief      Novice-readable guidance for an OS outside the support matrix.
    @param[in]  system Value of ``platform.system()`` (e.g. ``"Windows"``,
                ``"Linux"``, ``"Darwin"``).
    @return     A short explanation of the supported matrix and the risk of
                continuing anyway.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return (
        f"WAEGIS is verified on Windows 11 and Ubuntu 22.04+; {system or 'this operating system'} "
        "is untested. The wizard will continue, but re-run doctor if a later step behaves "
        "unexpectedly."
    )


# PUBLIC API


def probe_os_support() -> ProbeFindingRecord:
    """
    @brief      Report the detected OS/release and whether it is within the
                supported matrix (plan §8.1: Windows 11, Ubuntu 22+).
    @return     A ``machine.os`` :class:`ProbeFindingRecord`: ``"ok"`` inside
                the matrix, ``"warn"`` (never ``"fail"``) outside it, always
                naming the detected system and release in ``detail``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    system = platform.system()
    release = platform.release()
    detail = f"{system} {release}".strip() or "unknown operating system"

    if system == "Windows":
        if release in _SUPPORTED_WINDOWS_RELEASES:
            return ProbeFindingRecord(name="machine.os", status="ok", detail=detail, guidance=None)
        return ProbeFindingRecord(
            name="machine.os", status="warn", detail=detail, guidance=_os_guidance(system)
        )
    if system == "Linux":
        return ProbeFindingRecord(name="machine.os", status="ok", detail=detail, guidance=None)
    return ProbeFindingRecord(name="machine.os", status="warn", detail=detail, guidance=_os_guidance(system))


def probe_architecture() -> ProbeFindingRecord:
    """
    @brief      Report the detected machine architecture.
    @return     A ``machine.arch`` :class:`ProbeFindingRecord`, always
                ``"ok"`` — architecture is informational, not verified against
                a support matrix.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    machine = platform.machine() or "unknown"
    return ProbeFindingRecord(name="machine.arch", status="ok", detail=machine, guidance=None)


def probe_disk_space(path: str | PathLike[str], *, minimum_bytes: int) -> ProbeFindingRecord:
    """
    @brief      Report whether free disk space at ``path`` meets a caller-
                supplied minimum (plan §8.1 ``machine.disk``: >= 1 GB at
                TARGET's drive).
    @param[in]  path Filesystem path whose containing volume is checked (need
                not exist yet on every platform; callers pass the closest
                existing ancestor when TARGET itself is not yet created).
    @param[in]  minimum_bytes Minimum required free bytes; the caller decides
                the threshold (plan default: 1 GiB) so this probe stays
                policy-free.
    @return     A ``machine.disk`` :class:`ProbeFindingRecord`: ``"ok"`` when
                free space meets the minimum, ``"fail"`` otherwise (unlike
                ``machine.os``, insufficient disk genuinely blocks deployment).
    @exception  OSError Propagated from ``shutil.disk_usage`` if ``path`` and
                every ancestor are inaccessible.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    usage = shutil.disk_usage(path)
    free_gib = usage.free / _GIBIBYTE
    minimum_gib = minimum_bytes / _GIBIBYTE
    detail = f"{free_gib:.2f} GiB free at {path} (>= {minimum_gib:.2f} GiB required)"
    if usage.free >= minimum_bytes:
        return ProbeFindingRecord(name="machine.disk", status="ok", detail=detail, guidance=None)
    return ProbeFindingRecord(
        name="machine.disk",
        status="fail",
        detail=detail,
        guidance=f"free at least {minimum_gib:.2f} GiB at {path} before continuing (delete files or choose another drive)",
    )


# END OF FILE
