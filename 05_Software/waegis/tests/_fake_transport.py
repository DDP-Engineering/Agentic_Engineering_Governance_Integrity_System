#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file _fake_transport.py
@brief Test-only fake ``Transport``/``RegistryReader`` for the network probe
       suite (T2.2).
@details Not collected by pytest (underscore prefix). Maps an exact
         ``(host, port, use_tls)`` key to a canned
         :class:`waegis.probes.network.ConnectResult`; a key not present
         raises :class:`AssertionError` so an unexpected connect attempt
         fails the test loudly instead of silently reporting a plausible
         outcome. ``FakeRegistryReader`` returns a fixed, canned
         :class:`waegis.probes.network.WindowsProxySetting` (or ``None``).
         Every network probe test uses these instead of touching a real
         socket or registry.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from waegis.probes.network import CertificateInfo, ConnectResult, WindowsProxySetting

# PUBLIC API


class FakeTransport:
    """
    @brief Scripted, offline stand-in for :class:`waegis.probes.network.Transport`.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(self, responses: dict[tuple[str, int, bool], ConnectResult]) -> None:
        """
        @brief      Build a fake transport from a fixed
                    ``(host, port, use_tls) -> ConnectResult`` mapping.
        @param[in]  responses Mapping of exact connect keys to the scripted
                    result the fake returns.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        self._responses = dict(responses)
        self.calls: list[tuple[str, int, bool]] = []

    def connect(self, host: str, port: int, *, use_tls: bool, timeout: float = 5.0) -> ConnectResult:
        """
        @brief      Return the scripted result for ``(host, port, use_tls)``,
                    recording the call.
        @param[in]  host Target hostname or address.
        @param[in]  port Target TCP port.
        @param[in]  use_tls Whether TLS was requested.
        @param[in]  timeout Ignored (no real connect happens).
        @return     The scripted :class:`ConnectResult`.
        @exception  AssertionError If ``(host, port, use_tls)`` was not
                    scripted — an unscripted connect attempt is a test bug,
                    not a "not found" outcome.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        key = (host, port, use_tls)
        self.calls.append(key)
        if key not in self._responses:
            raise AssertionError(f"FakeTransport.connect called with unscripted key: {key!r}")
        return self._responses[key]


class FakeRegistryReader:
    """
    @brief Scripted, offline stand-in for
           :class:`waegis.probes.network.RegistryReader`.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(self, setting: WindowsProxySetting | None) -> None:
        """
        @brief      Build a fake registry reader that always returns
                    ``setting``.
        @param[in]  setting The canned :class:`WindowsProxySetting` to
                    return, or ``None``.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        self._setting = setting
        self.calls = 0

    def read_wininet_proxy(self) -> WindowsProxySetting | None:
        """
        @brief      Return the canned setting, recording the call.
        @return     The canned :class:`WindowsProxySetting`, or ``None``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        self.calls += 1
        return self._setting


def connected(issuer: str = "", subject: str = "") -> ConnectResult:
    """
    @brief      Build a ``"connected"`` :class:`ConnectResult`, optionally
                with certificate details.
    @param[in]  issuer Certificate issuer distinguished-name text.
    @param[in]  subject Certificate subject distinguished-name text.
    @return     ``ConnectResult(outcome="connected", certificate=...)`` when
                ``issuer`` or ``subject`` is non-empty, otherwise no
                certificate.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    if issuer or subject:
        return ConnectResult(outcome="connected", certificate=CertificateInfo(issuer=issuer, subject=subject))
    return ConnectResult(outcome="connected")


def timed_out() -> ConnectResult:
    """
    @brief      Build a ``"timed_out"`` :class:`ConnectResult`.
    @return     ``ConnectResult(outcome="timed_out")``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return ConnectResult(outcome="timed_out")


def refused() -> ConnectResult:
    """
    @brief      Build a ``"refused"`` :class:`ConnectResult`.
    @return     ``ConnectResult(outcome="refused")``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return ConnectResult(outcome="refused")


def dns_failure() -> ConnectResult:
    """
    @brief      Build a ``"dns_failure"`` :class:`ConnectResult`.
    @return     ``ConnectResult(outcome="dns_failure")``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return ConnectResult(outcome="dns_failure")


# END OF FILE
