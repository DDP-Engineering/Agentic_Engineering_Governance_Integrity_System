#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_probes_network.py
@brief Network probe tests: proxy detection, TLS interception, host
       reachability, and blocking-point construction (T2.2).
@details Strictly offline: every case uses :class:`FakeTransport`/
         :class:`FakeRegistryReader` from ``_fake_transport.py``, never a
         real socket or registry handle. Includes a regression guard proving
         no function in ``probes/network.py`` opens a real socket when called
         without an explicit host.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import socket
import threading
import time

import pytest

import waegis.probes.network as network
from waegis.io.reports import ProbeFinding, render_blocking_point_report

from _fake_transport import (
    FakeRegistryReader,
    FakeTransport,
    connected,
    dns_failure,
    refused,
    timed_out,
)

# TESTS

# --- proxy detection ----------------------------------------------------------


def test_probe_proxy_no_env_no_registry_reports_not_configured() -> None:
    """
    @brief      No proxy env vars and no registry reader configured reports
                "no proxy configured".
    @return     None
    @exception  AssertionError If status is not ``"ok"`` or a proxy is
                reported.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    finding = network.probe_proxy_configuration({})

    assert finding.name == "net.proxy"
    assert finding.status == "ok"
    assert "no proxy configured" in finding.detail
    assert finding.guidance is None


def test_probe_proxy_https_proxy_env_var_reported_with_source() -> None:
    """
    @brief      A configured ``HTTPS_PROXY`` env var is reported with its
                source and value.
    @return     None
    @exception  AssertionError If the source or value is missing from detail.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    finding = network.probe_proxy_configuration({"HTTPS_PROXY": "http://proxy.corp:8080"})

    assert finding.status == "info"
    assert "HTTPS_PROXY" in finding.detail
    assert "proxy.corp:8080" in finding.detail


def test_probe_proxy_windows_registry_used_when_no_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A fake Windows registry reporting a system proxy is used when
                no env var is set.
    @return     None
    @exception  AssertionError If the registry source is not surfaced, or the
                registry was not consulted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    registry = FakeRegistryReader(network.WindowsProxySetting(enabled=True, server="proxy.corp:3128"))

    finding = network.probe_proxy_configuration({}, registry=registry)

    assert finding.status == "info"
    assert "registry" in finding.detail
    assert "proxy.corp:3128" in finding.detail
    assert registry.calls == 1


def test_probe_proxy_registry_not_consulted_when_env_var_present() -> None:
    """
    @brief      Env vars take precedence over the registry: the registry is
                never read when an env var already answers the question.
    @return     None
    @exception  AssertionError If the registry was consulted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    registry = FakeRegistryReader(network.WindowsProxySetting(enabled=True, server="ignored:1"))

    finding = network.probe_proxy_configuration({"HTTP_PROXY": "http://proxy.corp:80"}, registry=registry)

    assert "HTTP_PROXY" in finding.detail
    assert registry.calls == 0


def test_probe_proxy_disabled_registry_setting_reports_not_configured() -> None:
    """
    @brief      A registry setting with ``enabled=False`` is treated as "no
                proxy configured", not surfaced as a configured proxy.
    @return     None
    @exception  AssertionError If a disabled setting is reported as
                configured.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    registry = FakeRegistryReader(network.WindowsProxySetting(enabled=False, server="proxy.corp:3128"))

    finding = network.probe_proxy_configuration({}, registry=registry)

    assert finding.status == "ok"
    assert "no proxy configured" in finding.detail


def test_probe_proxy_conflicting_env_var_casings_resolve_deterministically() -> None:
    """
    @brief      Both ``HTTPS_PROXY`` and ``https_proxy`` set to different
                values resolve to a single, deterministic winner
                (uppercase wins per the fixed lookup precedence).
    @return     None
    @exception  AssertionError If the resolved value is not the uppercase
                variant, or the result is nondeterministic across dict
                orderings.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    env_a = {"HTTPS_PROXY": "http://upper.corp:8080", "https_proxy": "http://lower.corp:8080"}
    env_b = {"https_proxy": "http://lower.corp:8080", "HTTPS_PROXY": "http://upper.corp:8080"}

    finding_a = network.probe_proxy_configuration(env_a)
    finding_b = network.probe_proxy_configuration(env_b)

    assert "upper.corp" in finding_a.detail
    assert "upper.corp" in finding_b.detail
    assert "lower.corp" not in finding_a.detail
    assert "lower.corp" not in finding_b.detail


def test_probe_proxy_connectivity_check_direct_succeeds() -> None:
    """
    @brief      When a target and transport are supplied and the direct
                connect succeeds, the proxy is reported configured but not
                required.
    @return     None
    @exception  AssertionError If status is not ``"info"`` or the direct
                success is not mentioned.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("forge.internal", 443, True): connected()})

    finding = network.probe_proxy_configuration(
        {"HTTPS_PROXY": "http://proxy.corp:8080"},
        transport=transport,
        target=("forge.internal", 443),
    )

    assert finding.status == "info"
    assert "direct connect" in finding.detail
    assert "succeeded" in finding.detail
    assert transport.calls == [("forge.internal", 443, True)]


def test_probe_proxy_connectivity_check_direct_fails_proxy_reachable() -> None:
    """
    @brief      When the direct connect fails but the configured proxy is
                reachable, the finding stays informational and names the
                working path.
    @return     None
    @exception  AssertionError If status escalates to ``"fail"``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport(
        {
            ("forge.internal", 443, True): timed_out(),
            ("proxy.corp", 8080, False): connected(),
        }
    )

    finding = network.probe_proxy_configuration(
        {"HTTPS_PROXY": "http://proxy.corp:8080"},
        transport=transport,
        target=("forge.internal", 443),
    )

    assert finding.status == "info"
    assert "proxy is reachable" in finding.detail


def test_probe_proxy_connectivity_check_both_paths_fail() -> None:
    """
    @brief      When both the direct and proxied connects fail, the finding
                escalates to ``"fail"`` with an ask-IT guidance text.
    @return     None
    @exception  AssertionError If status is not ``"fail"`` or guidance is
                missing.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport(
        {
            ("forge.internal", 443, True): refused(),
            ("proxy.corp", 8080, False): refused(),
        }
    )

    finding = network.probe_proxy_configuration(
        {"HTTPS_PROXY": "http://proxy.corp:8080"},
        transport=transport,
        target=("forge.internal", 443),
    )

    assert finding.status == "fail"
    assert finding.guidance is not None
    assert "forge.internal:443" in finding.guidance


# --- TLS interception heuristic ------------------------------------------------


def test_probe_tls_interception_ok_for_known_public_ca() -> None:
    """
    @brief      A certificate issuer matching a known public CA marker passes.
    @return     None
    @exception  AssertionError If status is not ``"ok"``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport(
        {("forge.example.com", 443, True): connected(issuer="C=US, O=DigiCert Inc, CN=DigiCert Global Root CA")}
    )

    finding = network.probe_tls_interception(transport, "forge.example.com")

    assert finding.name == "net.tls-interception"
    assert finding.status == "ok"
    assert finding.guidance is None


def test_probe_tls_interception_warns_on_unexpected_issuer() -> None:
    """
    @brief      A certificate issuer that does not match any known public CA
                is reported as a possible interception, naming the issuer.
    @return     None
    @exception  AssertionError If status is not ``"warn"`` or the issuer is
                not named.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport(
        {("forge.example.com", 443, True): connected(issuer="O=Acme Corporate Proxy CA, CN=Acme MITM Root")}
    )

    finding = network.probe_tls_interception(transport, "forge.example.com")

    assert finding.status == "warn"
    assert "possible TLS interception" in finding.detail
    assert "Acme MITM Root" in finding.detail or "Acme Corporate Proxy CA" in finding.detail
    assert finding.guidance is not None
    assert "root CA" in finding.guidance


def test_probe_tls_interception_reports_connect_failure_via_reachability_text() -> None:
    """
    @brief      A failed connect (e.g. timeout) is reported with the same
                failure-kind text as :func:`probe_host_reachability`, not a
                certificate mismatch.
    @return     None
    @exception  AssertionError If status is not ``"fail"`` or the detail does
                not describe a timeout.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("forge.example.com", 443, True): timed_out()})

    finding = network.probe_tls_interception(transport, "forge.example.com")

    assert finding.status == "fail"
    assert "timed out" in finding.detail


# --- generic host reachability --------------------------------------------------


def test_probe_host_reachability_reachable() -> None:
    """
    @brief      A successful connect reports ``"ok"``.
    @return     None
    @exception  AssertionError If status is not ``"ok"``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("mirror.internal", 8443, True): connected()})

    finding = network.probe_host_reachability(transport, "mirror.internal", 8443)

    assert finding.name == "net.reachability"
    assert finding.status == "ok"
    assert "succeeded" in finding.detail


def test_probe_host_reachability_timeout() -> None:
    """
    @brief      A timed-out connect reports ``"fail"`` with timeout-specific
                guidance.
    @return     None
    @exception  AssertionError If the guidance does not mention allowlisting.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("mirror.internal", 8443, True): timed_out()})

    finding = network.probe_host_reachability(transport, "mirror.internal", 8443)

    assert finding.status == "fail"
    assert "timed out" in finding.detail
    assert "allowlist" in finding.guidance


def test_probe_host_reachability_refused() -> None:
    """
    @brief      A refused connect reports ``"fail"`` with refusal-specific
                guidance, distinct from the timeout case.
    @return     None
    @exception  AssertionError If the detail/guidance do not describe a
                refusal.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("mirror.internal", 8443, True): refused()})

    finding = network.probe_host_reachability(transport, "mirror.internal", 8443)

    assert finding.status == "fail"
    assert "refused" in finding.detail
    assert "listening" in finding.guidance or "firewall" in finding.guidance


def test_probe_host_reachability_dns_failure() -> None:
    """
    @brief      A DNS failure reports ``"fail"`` with DNS-specific guidance,
                distinct from timeout/refused.
    @return     None
    @exception  AssertionError If the detail/guidance do not describe a DNS
                failure.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("mirror.internal", 8443, True): dns_failure()})

    finding = network.probe_host_reachability(transport, "mirror.internal", 8443)

    assert finding.status == "fail"
    assert "DNS resolution" in finding.detail
    assert "DNS" in finding.guidance


def test_reachability_findings_are_distinct_per_failure_kind() -> None:
    """
    @brief      The three failure kinds produce three distinct
                ``ProbeFindingRecord``s (different detail/guidance text), not
                a single generic "unreachable" message.
    @return     None
    @exception  AssertionError If any two failure-kind findings share detail
                text.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport(
        {
            ("h", 1, True): timed_out(),
            ("h", 2, True): refused(),
            ("h", 3, True): dns_failure(),
        }
    )

    details = {
        network.probe_host_reachability(transport, "h", 1).detail,
        network.probe_host_reachability(transport, "h", 2).detail,
        network.probe_host_reachability(transport, "h", 3).detail,
    }
    assert len(details) == 3


# --- blocking-point construction -------------------------------------------------


def test_failed_reachability_finding_maps_to_blocking_point_report() -> None:
    """
    @brief      A failed reachability finding maps onto a fully populated
                :class:`BlockingPointReport` and renders through
                ``io/reports.py`` unmodified.
    @return     None
    @exception  AssertionError If a field is missing or the render call
                raises.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("forge.internal", 443, True): refused()})
    finding = network.probe_host_reachability(transport, "forge.internal", 443)

    report = network.to_blocking_point_report(
        finding,
        step_id="net.proxy",
        title="Reach the configured forge host",
        attempted="TLS connect to forge.internal:443",
        why="WAEGIS needs to reach the forge to clone the template repository.",
    )

    assert report.step_id == "net.proxy"
    assert report.title == "Reach the configured forge host"
    assert report.attempted == "TLS connect to forge.internal:443"
    assert report.what_happened == finding.detail
    assert report.why
    assert report.it_request == finding.guidance
    assert len(report.alternatives) > 0

    import io

    buffer = io.StringIO()
    render_blocking_point_report(report, buffer)
    rendered = buffer.getvalue()
    assert "BLOCKED" in rendered
    assert finding.guidance in rendered


def test_blocking_point_report_accepts_custom_alternatives() -> None:
    """
    @brief      Caller-supplied alternatives override the default set.
    @return     None
    @exception  AssertionError If the custom alternatives are not used
                verbatim.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({("h", 1, True): dns_failure()})
    finding = network.probe_host_reachability(transport, "h", 1)

    report = network.to_blocking_point_report(
        finding,
        step_id="x",
        title="t",
        attempted="a",
        why="w",
        alternatives=["Use the internal DNS server instead."],
    )

    assert report.alternatives == ("Use the internal DNS server instead.",)


# --- offline-first regression guard --------------------------------------------


def test_network_findings_satisfy_probe_finding_protocol() -> None:
    """
    @brief      Every network-probe result satisfies the ``ProbeFinding``
                protocol so it slots into the existing environment report
                without adaptation.
    @return     None
    @exception  AssertionError If a finding fails the protocol check.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport(
        {
            ("h", 1, True): connected(issuer="O=DigiCert Inc"),
            ("h", 2, True): timed_out(),
        }
    )
    findings = [
        network.probe_proxy_configuration({}),
        network.probe_tls_interception(transport, "h", 1),
        network.probe_host_reachability(transport, "h", 2),
    ]
    for finding in findings:
        assert isinstance(finding, ProbeFinding)


def test_no_host_argument_never_touches_a_real_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Calling the proxy probe without a target never invokes
                ``Transport.connect``, even when a transport instance is
                supplied — guards the offline-first invariant against
                regression.
    @return     None
    @exception  AssertionError If ``connect`` was called.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    transport = FakeTransport({})  # any call raises AssertionError

    finding = network.probe_proxy_configuration(
        {"HTTPS_PROXY": "http://proxy.corp:8080"}, transport=transport, target=None
    )

    assert finding.status == "info"
    assert transport.calls == []


def test_no_host_argument_never_opens_a_real_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      Calling the proxy probe without a target never opens a real
                socket, even when a real :class:`SocketTransport` is
                constructed and available to the caller.
    @return     None
    @exception  AssertionError If ``socket.create_connection`` was called.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """

    def _fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("real socket.create_connection was called with no explicit host")

    monkeypatch.setattr(socket, "create_connection", _fail_if_called)
    real_transport = network.SocketTransport()

    finding = network.probe_proxy_configuration(
        {"HTTPS_PROXY": "http://proxy.corp:8080"}, transport=real_transport, target=None
    )

    assert finding.status == "info"


# --- SocketTransport: every attempt is bounded by the caller's timeout --------


def test_a_stalled_resolver_still_returns_within_the_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief      A DNS server that never answers must not outlast the caller's
                ``timeout``; the attempt is reported as ``timed_out``.
    @details    ``socket.create_connection`` resolves the address before the
                socket carrying ``timeout`` exists, so the timeout argument
                alone does not bound ``getaddrinfo``. This is the corporate
                misconfiguration the network probes exist to diagnose, and the
                one case that used to hang them.
    @param[in]  monkeypatch Used to stall the resolver without any real DNS.
    @return     None
    @exception  AssertionError If the probe blocks past its timeout or reports
                an outcome other than ``timed_out``.
    """
    resolver_released = threading.Event()

    def stalled_getaddrinfo(*_args: object, **_kwargs: object) -> None:
        """@brief Block like a non-responding resolver until the test releases it."""
        resolver_released.wait(30.0)
        raise socket.gaierror("resolver released by the test")

    monkeypatch.setattr(socket, "getaddrinfo", stalled_getaddrinfo)
    started = time.monotonic()
    try:
        result = network.SocketTransport().connect(
            "stalled.invalid", 443, use_tls=True, timeout=0.25
        )
        elapsed = time.monotonic() - started
    finally:
        resolver_released.set()

    assert result.outcome == "timed_out"
    assert elapsed < 5.0, f"probe blocked for {elapsed:.1f}s on a stalled resolver"


def test_an_abandoned_connect_worker_never_delays_interpreter_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief      The worker left behind by a timed-out connect is a daemon, so a
                resolver that never answers cannot move the stall from the probe
                to process exit.
    @details    A pooled worker would reintroduce the hang: ``ThreadPoolExecutor``
                registers an ``atexit`` hook that joins its threads, so the probe
                would return on time and then block the interpreter on the way
                out. Nothing is gained by bounding the probe if exit is not
                bounded too.
    @param[in]  monkeypatch Used to stall the resolver without any real DNS.
    @return     None
    @exception  AssertionError If no worker lingers, or one lingers as a
                non-daemon thread.
    """
    resolver_released = threading.Event()

    def stalled_getaddrinfo(*_args: object, **_kwargs: object) -> None:
        """@brief Block like a non-responding resolver until the test releases it."""
        resolver_released.wait(30.0)
        raise socket.gaierror("resolver released by the test")

    monkeypatch.setattr(socket, "getaddrinfo", stalled_getaddrinfo)
    try:
        result = network.SocketTransport().connect(
            "stalled.invalid", 443, use_tls=False, timeout=0.25
        )
        lingering = [
            thread for thread in threading.enumerate() if thread.name == "waegis-connect"
        ]
        assert result.outcome == "timed_out"
        assert lingering, "expected the abandoned connect worker to still be running"
        assert all(thread.daemon for thread in lingering)
    finally:
        resolver_released.set()


def test_a_failing_resolver_is_still_reported_as_a_dns_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief      Bounding the connect must not change how a resolver that
                answers "no such host" is classified.
    @param[in]  monkeypatch Used to fail resolution without any real DNS.
    @return     None
    @exception  AssertionError If the outcome is not ``dns_failure``.
    """

    def failing_getaddrinfo(*_args: object, **_kwargs: object) -> None:
        """@brief Reject the name the way a working resolver rejects an unknown host."""
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", failing_getaddrinfo)

    result = network.SocketTransport().connect(
        "missing.invalid", 443, use_tls=True, timeout=0.25
    )

    assert result.outcome == "dns_failure"


def test_a_refused_connection_is_still_reported_as_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief      Bounding the connect must not change how an actively refused
                port is classified.
    @param[in]  monkeypatch Used to refuse the connect without any real socket.
    @return     None
    @exception  AssertionError If the outcome is not ``refused``.
    """

    def refusing_create_connection(*_args: object, **_kwargs: object) -> None:
        """@brief Refuse the way a closed port does."""
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(socket, "create_connection", refusing_create_connection)

    result = network.SocketTransport().connect(
        "host.invalid", 443, use_tls=True, timeout=0.25
    )

    assert result.outcome == "refused"


# END OF FILE
