#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file network.py
@brief Network/corporate probes: proxy detection, TLS-interception heuristic,
       and generic host reachability, behind an injectable transport (T2.2).
@details Implements the network subset of the plan §4 ``net.proxy`` row and
         the analysis doc's corporate-restriction probe matrix (proxy, TLS
         interception, generic host reachability). Package-manager/WSL/admin
         probes are out of scope here.

         **Offline-first is structural, not just tested**: no function in
         this module opens a socket or reads the registry unless the caller
         passes an explicit :class:`Transport`/:class:`RegistryReader` *and*
         (for connectivity checks) an explicit host/port. There is no default
         transport and no hardcoded external host anywhere in this module.
@details Every probe returns a :class:`waegis.io.reports.ProbeFindingRecord`
         and never prints (matches ``machine.py``/``tools.py``). A failed
         finding's ``detail``/``guidance`` map directly onto
         :class:`waegis.io.reports.BlockingPointReport` via
         :func:`to_blocking_point_report`, so a blocked network probe is
         immediately IT-forwardable.
"""

# IMPORTS

from __future__ import annotations

import errno
import socket
import ssl
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable
from urllib.parse import urlsplit

from waegis.io.reports import BlockingPointReport, ProbeFindingRecord

# CONSTANTS

# @brief Shared default for every probe's subprocess/socket timeout.
DEFAULT_PROBE_TIMEOUT = 5.0

# @brief Env vars checked for a configured proxy, in lookup precedence order
#        (plan T2.2: HTTP_PROXY/HTTPS_PROXY and lowercase variants). HTTPS
#        takes precedence over HTTP since every corporate egress check in
#        this module is TLS by default; a fixed order makes conflicting
#        casings (e.g. both HTTPS_PROXY and https_proxy set) resolve
#        deterministically instead of depending on mapping iteration order.
_PROXY_ENV_PRECEDENCE: tuple[str, ...] = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")

# @brief Organization/CA name fragments that identify a widely trusted public
#        CA. Substring, case-insensitive match against the presented
#        certificate's issuer string; a caller may override this list (e.g.
#        with an approved internal CA name) via ``expected_issuer_markers``.
_DEFAULT_PUBLIC_CA_ISSUER_MARKERS: tuple[str, ...] = (
    "DigiCert",
    "Let's Encrypt",
    "ISRG Root",
    "GlobalSign",
    "Sectigo",
    "Amazon",
    "Google Trust Services",
    "Microsoft Corporation",
    "Entrust",
    "GoDaddy",
    "COMODO",
    "USERTrust",
)

# @brief Default alternative paths offered on a network blocking point
#        (analysis doc corporate-restriction matrix): this module implements
#        none of these itself, they are surfaced as text only.
_DEFAULT_ALTERNATIVES: tuple[str, ...] = (
    "Use an offline installation bundle instead of a live network fetch.",
    "Point WAEGIS at an internal mirror or artifact registry.",
    "Ask IT to allowlist the host/port through the corporate proxy.",
    "Use a pre-provisioned image or workstation that already has this dependency.",
    "Choose a different, already-reachable host if an equivalent endpoint exists.",
)

# DATA MODELS / TYPEDEFINITIONS

# @brief Outcome of one :class:`Transport` connect attempt.
# @details ``cert_untrusted`` means the TCP connect succeeded but the TLS
#          certificate chain failed local verification — the primary symptom
#          of corporate TLS interception with an untrusted root.
#          ``tls_failure`` covers any other TLS handshake failure.
ConnectOutcome = Literal[
    "connected",
    "timed_out",
    "refused",
    "dns_failure",
    "cert_untrusted",
    "tls_failure",
]


@dataclass(frozen=True)
class CertificateInfo:
    """
    @brief Issuer/subject of a peer TLS certificate, as plain distinguished
           names.
    """

    issuer: str
    subject: str


@dataclass(frozen=True)
class ConnectResult:
    """
    @brief Outcome of one :class:`Transport` connect attempt.
    @details ``certificate`` is populated only when the attempt used TLS and
             succeeded; it is ``None`` for a plain TCP connect or any
             non-``"connected"`` outcome.
    """

    outcome: ConnectOutcome
    certificate: CertificateInfo | None = None


@runtime_checkable
class Transport(Protocol):
    """
    @brief Injectable seam for network access (mirrors ``probes/runner.py``'s
           ``CommandRunner`` seam for subprocess access).
    @details No probe function in this module calls ``socket``/``ssl``
             directly; every one accepts a :class:`Transport` so tests
             substitute a fake and never touch a real socket.
    """

    def connect(
        self,
        host: str,
        port: int,
        *,
        use_tls: bool,
        timeout: float = DEFAULT_PROBE_TIMEOUT,
    ) -> ConnectResult:
        """
        @brief      Attempt a TCP (optionally TLS) connect to ``host:port``.
        @param[in]  host Target hostname or address.
        @param[in]  port Target TCP port.
        @param[in]  use_tls When ``True``, perform a TLS handshake after the
                    TCP connect and report the peer certificate's
                    issuer/subject on success.
        @param[in]  timeout Seconds to allow the attempt before it is
                    reported as ``"timed_out"``.
        @return     A :class:`ConnectResult` describing what happened.
        """
        ...


@dataclass(frozen=True)
class WindowsProxySetting:
    """
    @brief Best-effort read of the WinINet system proxy setting.
    """

    enabled: bool
    server: str | None


@runtime_checkable
class RegistryReader(Protocol):
    """
    @brief Injectable seam for the Windows system-proxy registry read.
    @details Kept separate from :class:`Transport` since it is a local,
             synchronous read rather than network I/O, but it is subject to
             the same offline-testing discipline: no probe calls ``winreg``
             directly.
    """

    def read_wininet_proxy(self) -> WindowsProxySetting | None:
        """
        @brief      Best-effort read of the current user's WinINet proxy
                    setting.
        @return     A :class:`WindowsProxySetting`, or ``None`` when the
                    setting could not be read (not Windows, key absent,
                    permission denied, etc.) — never raises.
        """
        ...


# HELPER FUNCTIONS


def _env_proxy_lookup(env: Mapping[str, str]) -> tuple[str, str] | None:
    """
    @brief      Find the first configured proxy env var in fixed precedence
                order.
    @param[in]  env Environment mapping to inspect (caller supplies
                ``os.environ`` or a fake mapping; this function never reads
                the real environment itself).
    @return     ``(var_name, value)`` for the first non-empty match in
                :data:`_PROXY_ENV_PRECEDENCE`, or ``None`` if none are set.
    @exception  None
    """
    for key in _PROXY_ENV_PRECEDENCE:
        value = env.get(key)
        if value:
            return key, value
    return None


def _parse_proxy_authority(proxy_url: str) -> tuple[str, int] | None:
    """
    @brief      Extract a ``(host, port)`` pair from a proxy URL or bare
                ``host:port`` string.
    @param[in]  proxy_url Proxy value as found in an env var or the registry
                (e.g. ``"http://proxy.corp:8080"`` or ``"proxy.corp:8080"``).
    @return     ``(host, port)``, defaulting the port to 443 for an
                ``https://`` scheme and 80 otherwise; ``None`` if no hostname
                could be parsed.
    @exception  None
    """
    candidate = proxy_url if "://" in proxy_url else f"//{proxy_url}"
    parsed = urlsplit(candidate)
    if not parsed.hostname:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.hostname, port


def _outcome_text(host: str, port: int, outcome: ConnectOutcome, *, use_tls: bool) -> tuple[str, str]:
    """
    @brief      Novice-readable detail/guidance text for a failed connect
                outcome, keyed by failure kind (not by OS — these are network
                conditions, not install steps).
    @param[in]  host Target hostname or address that was attempted.
    @param[in]  port Target TCP port that was attempted.
    @param[in]  outcome A non-``"connected"`` :data:`ConnectOutcome`.
    @param[in]  use_tls Whether the attempt used TLS (affects the protocol
                label in the text).
    @return     ``(detail, guidance)`` describing what happened and a
                copyable IT request.
    @exception  ValueError If ``outcome`` is ``"connected"`` (not a failure
                kind this helper handles).
    """
    protocol = "TLS" if use_tls else "TCP"
    endpoint = f"{host}:{port}"
    if outcome == "timed_out":
        return (
            f"{protocol} connect to {endpoint} timed out",
            f"please allowlist {endpoint} for this workstation ({protocol} outbound) — a timeout "
            "usually means a firewall or proxy is silently dropping the traffic rather than "
            "rejecting it outright",
        )
    if outcome == "refused":
        return (
            f"{protocol} connect to {endpoint} was refused",
            f"please confirm {endpoint} is the correct endpoint and the service is listening, or "
            "allowlist this workstation if a firewall is actively rejecting the connection",
        )
    if outcome == "dns_failure":
        return (
            f"DNS resolution for {host} failed",
            f"please confirm '{host}' resolves via corporate DNS from this workstation, or provide "
            "the correct internal hostname or IP address",
        )
    if outcome == "cert_untrusted":
        return (
            f"TLS certificate presented by {endpoint} is not trusted by this workstation",
            f"this usually indicates TLS interception — please provide the corporate root CA "
            f"certificate so it can be trusted, or confirm {endpoint} presents a valid chain",
        )
    if outcome == "tls_failure":
        return (
            f"TLS handshake with {endpoint} failed",
            f"please confirm {endpoint} speaks TLS on this port and that no proxy is "
            "terminating the connection mid-handshake",
        )
    raise ValueError(f"_outcome_text does not handle a 'connected' outcome: {outcome!r}")


def _reachability_finding(
    *, name: str, host: str, port: int, outcome: ConnectOutcome, use_tls: bool
) -> ProbeFindingRecord:
    """
    @brief      Build a ``"fail"`` finding for a non-``"connected"`` connect
                outcome, shared by :func:`probe_host_reachability` and
                :func:`probe_tls_interception` so both report the same
                failure-kind text.
    @param[in]  name Probe finding name to use (``"net.reachability"`` or
                ``"net.tls-interception"``).
    @param[in]  host Target hostname or address that was attempted.
    @param[in]  port Target TCP port that was attempted.
    @param[in]  outcome A non-``"connected"`` :data:`ConnectOutcome`.
    @param[in]  use_tls Whether the attempt used TLS.
    @return     A ``"fail"`` :class:`ProbeFindingRecord` with failure-kind
                detail and guidance.
    @exception  None
    """
    detail, guidance = _outcome_text(host, port, outcome, use_tls=use_tls)
    return ProbeFindingRecord(name=name, status="fail", detail=detail, guidance=guidance)


def _format_rdn_sequence(rdn_sequence: Sequence[Sequence[tuple[str, str]]]) -> str:
    """
    @brief      Flatten the RDN-sequence shape returned by
                ``ssl.SSLSocket.getpeercert()`` into a single readable string.
    @param[in]  rdn_sequence The ``"issuer"`` or ``"subject"`` value from
                ``getpeercert()``: a tuple of tuples of ``(key, value)`` pairs.
    @return     Comma-joined ``key=value`` pairs, e.g. ``"O=DigiCert Inc,
                CN=DigiCert Global Root CA"``; empty string for an empty
                sequence.
    @exception  None
    """
    parts: list[str] = []
    for rdn in rdn_sequence:
        for key, value in rdn:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def _certificate_info(peer_cert: Mapping[str, Any] | None) -> CertificateInfo | None:
    """
    @brief      Extract issuer/subject text from ``getpeercert()`` output.
    @param[in]  peer_cert Mapping returned by ``ssl.SSLSocket.getpeercert()``,
                or ``None``.
    @return     A :class:`CertificateInfo`, or ``None`` when no certificate
                data was available.
    @exception  None
    """
    if not peer_cert:
        return None
    issuer = _format_rdn_sequence(peer_cert.get("issuer", ()))
    subject = _format_rdn_sequence(peer_cert.get("subject", ()))
    return CertificateInfo(issuer=issuer, subject=subject)


# PUBLIC API


class SocketTransport:
    """
    @brief Real, ``socket``/``ssl``-backed :class:`Transport` implementation.
    @details The only place in this module allowed to import/use ``socket``
             or ``ssl`` (mirrors ``probes/runner.py``'s
             ``SubprocessCommandRunner``). Never instantiated by any probe
             function in this module — callers must construct and pass it
             explicitly, which is what keeps the module offline by default.
    """

    def connect(
        self,
        host: str,
        port: int,
        *,
        use_tls: bool,
        timeout: float = DEFAULT_PROBE_TIMEOUT,
    ) -> ConnectResult:
        """
        @brief      Attempt a real TCP (optionally TLS) connect to
                    ``host:port``.
        @param[in]  host Target hostname or address.
        @param[in]  port Target TCP port.
        @param[in]  use_tls When ``True``, perform a TLS handshake and report
                    the peer certificate's issuer/subject on success.
        @param[in]  timeout Seconds to allow the attempt before it is
                    reported as ``"timed_out"``.
        @return     A :class:`ConnectResult` capturing the real outcome.
        @exception  OSError Propagated for connection failures other than the
                    ones this method maps to a :data:`ConnectOutcome`
                    (timeout, DNS failure, connection refused).
        """
        try:
            raw_socket = socket.create_connection((host, port), timeout=timeout)
        except socket.timeout:
            return ConnectResult(outcome="timed_out")
        except socket.gaierror:
            return ConnectResult(outcome="dns_failure")
        except ConnectionRefusedError:
            return ConnectResult(outcome="refused")
        except OSError as exc:
            if getattr(exc, "errno", None) == errno.ECONNREFUSED:
                return ConnectResult(outcome="refused")
            raise
        try:
            if not use_tls:
                return ConnectResult(outcome="connected")
            context = ssl.create_default_context()
            try:
                with context.wrap_socket(raw_socket, server_hostname=host) as tls_socket:
                    peer_cert = tls_socket.getpeercert()
            except ssl.SSLCertVerificationError:
                return ConnectResult(outcome="cert_untrusted")
            except socket.timeout:
                return ConnectResult(outcome="timed_out")
            except (ssl.SSLError, OSError):
                return ConnectResult(outcome="tls_failure")
            return ConnectResult(outcome="connected", certificate=_certificate_info(peer_cert))
        finally:
            raw_socket.close()


class WinInetRegistryReader:
    """
    @brief Real, ``winreg``-backed :class:`RegistryReader` implementation.
    @details The only place in this module allowed to import ``winreg``.
             Best-effort by construction: any failure (module unavailable on
             non-Windows, key/value absent, permission denied) is caught and
             reported as ``None`` rather than raised, per the plan's "optional
             / best-effort" constraint.
    """

    def read_wininet_proxy(self) -> WindowsProxySetting | None:
        """
        @brief      Best-effort read of
                    ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings``.
        @return     A :class:`WindowsProxySetting`, or ``None`` if ``winreg``
                    is unavailable or the read fails for any reason.
        @exception  None All failure modes are swallowed and reported as
                    ``None``.
        """
        try:
            import winreg
        except ImportError:
            return None
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            ) as key:
                enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
                server: str | None
                try:
                    server, _ = winreg.QueryValueEx(key, "ProxyServer")
                except OSError:
                    server = None
                return WindowsProxySetting(enabled=bool(enabled), server=server or None)
        except OSError:
            return None


def probe_proxy_configuration(
    env: Mapping[str, str],
    *,
    registry: RegistryReader | None = None,
    transport: Transport | None = None,
    target: tuple[str, int] | None = None,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
) -> ProbeFindingRecord:
    """
    @brief      Detect a configured proxy from env vars, falling back to the
                Windows system proxy, and optionally verify direct-vs-proxied
                reachability to a caller-supplied target (plan §8.1
                ``net.proxy``).
    @details    Env vars (:data:`_PROXY_ENV_PRECEDENCE`) take precedence over
                the registry. ``registry`` is consulted only when supplied
                (real code passes :class:`WinInetRegistryReader`; on
                non-Windows it returns ``None`` on its own, so this function
                needs no OS check). A connectivity check (direct connect,
                then proxied connect if direct fails) runs **only** when both
                ``target`` and ``transport`` are supplied — offline-first
                default (plan T2.2, AD-3).
    @param[in]  env Environment mapping to inspect (caller supplies
                ``os.environ`` or a fake).
    @param[in]  registry Injectable Windows-proxy registry reader; omit on
                non-Windows or when a registry check is not wanted.
    @param[in]  transport Injectable :class:`Transport`; only used when
                ``target`` is also supplied.
    @param[in]  target ``(host, port)`` to test reachability against, only
                when a real check is requested by the caller.
    @param[in]  timeout Seconds per connect attempt.
    @return     A ``net.proxy`` :class:`ProbeFindingRecord`: ``"ok"`` when no
                proxy is configured, ``"info"`` when a proxy is configured
                and either no connectivity check was requested or the check
                found a working path, ``"fail"`` when a connectivity check
                was requested and both the direct and proxied paths failed.
    @exception  OSError Propagated from the injected ``transport`` if its
                ``connect`` implementation raises for a failure kind it does
                not map to a :data:`ConnectOutcome` (see
                :meth:`SocketTransport.connect`); this function itself never
                raises.
    """
    proxy_url: str | None = None
    source: str | None = None

    env_match = _env_proxy_lookup(env)
    if env_match is not None:
        source_name, value = env_match
        proxy_url = value
        source = f"environment variable {source_name}"
    elif registry is not None:
        setting = registry.read_wininet_proxy()
        if setting is not None and setting.enabled and setting.server:
            proxy_url = setting.server
            source = "Windows system proxy (registry)"

    if proxy_url is None:
        checked = "HTTP_PROXY/HTTPS_PROXY env vars" + (" and the Windows system proxy" if registry is not None else "")
        return ProbeFindingRecord(name="net.proxy", status="ok", detail=f"no proxy configured (checked {checked})", guidance=None)

    detail = f"proxy configured via {source}: {proxy_url}"
    status = "info"
    guidance: str | None = None

    if target is not None and transport is not None:
        host, port = target
        direct = transport.connect(host, port, use_tls=True, timeout=timeout)
        if direct.outcome == "connected":
            detail += f"; direct connect to {host}:{port} succeeded (proxy not required for this host)"
        else:
            proxy_authority = _parse_proxy_authority(proxy_url)
            proxied_ok = False
            if proxy_authority is not None:
                proxy_host, proxy_port = proxy_authority
                proxied = transport.connect(proxy_host, proxy_port, use_tls=False, timeout=timeout)
                proxied_ok = proxied.outcome == "connected"
            if proxied_ok:
                detail += f"; direct connect to {host}:{port} failed but the configured proxy is reachable"
            else:
                status = "fail"
                detail += f"; direct connect to {host}:{port} failed and the configured proxy is unreachable too"
                guidance = (
                    f"please allowlist {host}:{port} for this workstation, or confirm the proxy "
                    f"'{proxy_url}' is reachable and correctly configured"
                )

    return ProbeFindingRecord(name="net.proxy", status=status, detail=detail, guidance=guidance)


def probe_tls_interception(
    transport: Transport,
    host: str,
    port: int = 443,
    *,
    expected_issuer_markers: Sequence[str] = _DEFAULT_PUBLIC_CA_ISSUER_MARKERS,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
) -> ProbeFindingRecord:
    """
    @brief      TLS-interception heuristic: connect to an operator-supplied
                host and compare the presented certificate's issuer against a
                list of known public CA name fragments (plan T2.2).
    @details    Performs no network I/O unless called with an explicit
                ``host`` by the caller — this probe never runs against a
                hardcoded external host by default; the wizard invokes it
                only when it has an actual target (e.g. the chosen forge
                host).
    @param[in]  transport Injectable :class:`Transport`.
    @param[in]  host Operator-supplied target host; required, no default.
    @param[in]  port Target TCP port (default 443).
    @param[in]  expected_issuer_markers Case-insensitive substrings that
                identify a trusted public (or approved internal) CA;
                overridable by the caller.
    @param[in]  timeout Seconds to allow the connect attempt.
    @return     A ``net.tls-interception`` :class:`ProbeFindingRecord`:
                ``"ok"`` when the certificate connects and the issuer matches
                a known marker; ``"warn"`` when the certificate is untrusted
                (possible TLS interception), when the connect succeeds but no
                peer certificate details are available, or when the issuer
                does not match a known marker; ``"fail"`` for any other
                non-``"connected"`` outcome (delegates to the same
                failure-kind text as :func:`probe_host_reachability`).
    @exception  OSError Propagated from the injected ``transport`` if its
                ``connect`` implementation raises for a failure kind it does
                not map to a :data:`ConnectOutcome` (see
                :meth:`SocketTransport.connect`); this function itself never
                raises.
    """
    result = transport.connect(host, port, use_tls=True, timeout=timeout)
    if result.outcome == "cert_untrusted":
        return ProbeFindingRecord(
            name="net.tls-interception",
            status="warn",
            detail=f"possible TLS interception: certificate presented by {host}:{port} "
            "is not trusted by this workstation",
            guidance="please provide the corporate TLS interception root CA certificate so "
            "WAEGIS can trust it, or confirm the endpoint presents a valid public chain",
        )
    if result.outcome != "connected":
        return _reachability_finding(name="net.tls-interception", host=host, port=port, outcome=result.outcome, use_tls=True)

    if result.certificate is None:
        return ProbeFindingRecord(
            name="net.tls-interception",
            status="warn",
            detail=f"TLS connect to {host}:{port} succeeded but no peer certificate details were returned",
            guidance="re-run with a transport that reports peer certificate issuer/subject details",
        )

    issuer = result.certificate.issuer
    if any(marker.lower() in issuer.lower() for marker in expected_issuer_markers):
        return ProbeFindingRecord(
            name="net.tls-interception",
            status="ok",
            detail=f"TLS certificate for {host}:{port} issued by '{issuer}' (recognized CA)",
            guidance=None,
        )
    return ProbeFindingRecord(
        name="net.tls-interception",
        status="warn",
        detail=f"possible TLS interception: certificate for {host}:{port} issued by '{issuer}', "
        "which does not match a known public CA",
        guidance=f"please provide the corporate TLS interception root CA certificate so WAEGIS can "
        f"trust it, or confirm '{issuer}' is an approved internal CA",
    )


def probe_host_reachability(
    transport: Transport,
    host: str,
    port: int,
    *,
    use_tls: bool = True,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
) -> ProbeFindingRecord:
    """
    @brief      Generic reachability probe for an operator-supplied
                host/port (plan T2.2): reachable / timed out / connection
                refused / DNS failure, with failure-kind (not per-OS)
                guidance.
    @param[in]  transport Injectable :class:`Transport`.
    @param[in]  host Operator-supplied target host; required, no default.
    @param[in]  port Operator-supplied target port; required, no default.
    @param[in]  use_tls Whether to attempt a TLS handshake after the TCP
                connect.
    @param[in]  timeout Seconds to allow the connect attempt.
    @return     A ``net.reachability`` :class:`ProbeFindingRecord`: ``"ok"``
                when connected, ``"fail"`` for each distinct failure kind
                (timeout, refused, DNS failure, and, when ``use_tls`` is
                ``True``, an untrusted certificate or other TLS handshake
                failure), with matching guidance text.
    @exception  OSError Propagated from the injected ``transport`` if its
                ``connect`` implementation raises for a failure kind it does
                not map to a :data:`ConnectOutcome` (see
                :meth:`SocketTransport.connect`); this function itself never
                raises.
    """
    result = transport.connect(host, port, use_tls=use_tls, timeout=timeout)
    if result.outcome == "connected":
        protocol = "TLS" if use_tls else "TCP"
        return ProbeFindingRecord(
            name="net.reachability", status="ok", detail=f"{protocol} connect to {host}:{port} succeeded", guidance=None
        )
    return _reachability_finding(name="net.reachability", host=host, port=port, outcome=result.outcome, use_tls=use_tls)


def to_blocking_point_report(
    finding: ProbeFindingRecord,
    *,
    step_id: str,
    title: str,
    attempted: str,
    why: str,
    alternatives: Sequence[str] = _DEFAULT_ALTERNATIVES,
) -> BlockingPointReport:
    """
    @brief      Map a failed network :class:`ProbeFindingRecord` directly
                onto a :class:`waegis.io.reports.BlockingPointReport` (plan
                §4/§12, R7), with no changes needed to ``io/reports.py``.
    @param[in]  finding A ``"fail"``-status finding from one of this module's
                probes (``what_happened``/``it_request`` are taken from
                ``finding.detail``/``finding.guidance``).
    @param[in]  step_id The engine step id this blocking point belongs to.
    @param[in]  title Novice-readable title for the report.
    @param[in]  attempted What was attempted (e.g. ``"TLS connect to
                forge.corp:443"``); step-specific, not derivable from the
                finding alone.
    @param[in]  why Why the wizard needs this (step-specific context).
    @param[in]  alternatives Alternative paths to offer; defaults to the
                analysis doc's standard set (offline bundle, internal mirror,
                allowlist-proxy, pre-provisioned image, different host).
    @return     A fully populated :class:`BlockingPointReport`.
    @exception  None
    """
    return BlockingPointReport(
        step_id=step_id,
        title=title,
        attempted=attempted,
        what_happened=finding.detail,
        why=why,
        it_request=finding.guidance or f"please investigate: {finding.detail}",
        alternatives=tuple(alternatives),
    )


# END OF FILE
