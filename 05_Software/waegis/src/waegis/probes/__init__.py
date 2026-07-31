#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file __init__.py
@brief Package marker for the WAEGIS probe layer.
@details Holds machine, tool, and network probes behind injectable runners so
         tests stay offline (plan §M2, AD-3).

         - ``runner.py`` (T2.1): the shared ``CommandRunner`` protocol and its
           real ``SubprocessCommandRunner`` implementation. It lives in its own
           module rather than here so this file stays a plain package marker;
           import it directly (``from waegis.probes.runner import
           CommandRunner``).
         - ``machine.py`` (T2.1): OS/version support-matrix, architecture, and
           free-disk probes.
         - ``tools.py`` (T2.1): python/git/uv probes over ``CommandRunner``.
         - ``network.py`` (T2.2): proxy detection, TLS-interception
           heuristic, and generic host reachability behind an injectable
           ``Transport``/``RegistryReader``.

         Every probe returns a :class:`waegis.io.reports.ProbeFindingRecord`
         and never prints; rendering is the ``io/`` layer's job.
"""

# END OF FILE
