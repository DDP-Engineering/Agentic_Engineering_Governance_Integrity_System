#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_payload_locate.py
@brief Payload resolution tests (T3.2): --payload override validation, the
       bundled-install stub, the repo-checkout fallback, the
       nothing-resolves error, and payload version reading.
@details Strictly offline. Uses synthetic ``tmp_path`` payload trees plus the
         real ``05_Software/aegis/template/`` (read-only) for the
         checkout-fallback and version-reading cases.
"""

# IMPORTS

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from waegis.payload import locate
from waegis.payload.locate import (
    PAYLOAD_MARKER,
    PAYLOAD_VERSION_FILE,
    InvalidPayloadError,
    PayloadNotFoundError,
    bundled_payload_root,
    is_payload_root,
    locate_payload,
    read_payload_version,
    repo_checkout_payload_root,
)

# CONSTANTS

# @brief The real repo-checkout template payload (read-only in these tests).
REAL_TEMPLATE = Path(__file__).resolve().parents[2] / "aegis" / "template"

# LOCAL HELPERS


def _make_payload_root(root: Path) -> Path:
    """
    @brief      Create a minimal directory that passes the payload-root check.
    @param[in]  root Directory to turn into a payload root.
    @return     ``root``.
    @exception  None
    """
    marker = root / PAYLOAD_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("[workflow]\n", encoding="utf-8", newline="\n")
    return root


# TESTS


def test_explicit_payload_override_used_when_valid(tmp_path: Path) -> None:
    """
    @brief      A valid explicit --payload path wins and is returned resolved,
                without consulting any fallback.
    @return     None
    @exception  AssertionError If the override is not honored.
    """
    payload = _make_payload_root(tmp_path / "payload")
    assert locate_payload(payload) == payload.resolve()


def test_explicit_payload_override_rejected_without_marker(tmp_path: Path) -> None:
    """
    @brief      An explicit --payload path without the payload marker is
                rejected with InvalidPayloadError, never silently replaced by
                a fallback.
    @return     None
    @exception  AssertionError If a non-payload directory is accepted.
    """
    not_a_payload = tmp_path / "just-a-dir"
    not_a_payload.mkdir()
    with pytest.raises(InvalidPayloadError, match="does not look like a payload root"):
        locate_payload(not_a_payload)


def test_explicit_payload_override_rejected_when_missing(tmp_path: Path) -> None:
    """
    @brief      An explicit --payload path that does not exist at all is also
                an InvalidPayloadError.
    @return     None
    @exception  AssertionError If a missing path is accepted.
    """
    with pytest.raises(InvalidPayloadError):
        locate_payload(tmp_path / "no-such-dir")


def test_bundled_payload_root_is_stubbed_until_packaging() -> None:
    """
    @brief      The bundled-install candidate is a stub returning None until
                T7.x introduces packaging.
    @return     None
    @exception  AssertionError If the stub reports a bundled payload.
    """
    assert bundled_payload_root() is None


def test_repo_checkout_fallback_resolves_real_template() -> None:
    """
    @brief      Running from this repo checkout, the fallback resolves to the
                real 05_Software/aegis/template/ payload.
    @return     None
    @exception  AssertionError If the checkout fallback misses the template.
    """
    assert is_payload_root(REAL_TEMPLATE)
    assert repo_checkout_payload_root() == REAL_TEMPLATE
    assert locate_payload() == REAL_TEMPLATE.resolve()


def test_error_when_no_candidate_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      With no override, no bundled payload, and no repo checkout,
                locate_payload raises the distinct not-found error.
    @return     None
    @exception  AssertionError If the failure is not reported clearly.
    """
    monkeypatch.setattr(locate, "bundled_payload_root", lambda: None)
    monkeypatch.setattr(locate, "repo_checkout_payload_root", lambda: None)
    with pytest.raises(PayloadNotFoundError, match="no AEGIS payload found"):
        locate_payload()


def test_read_payload_version_from_real_template() -> None:
    """
    @brief      The real template's version is read from
                .agentic/cli/pyproject.toml [project].version and matches an
                independent tomllib parse of that file.
    @return     None
    @exception  AssertionError If the version differs from the declaration.
    """
    with open(REAL_TEMPLATE / PAYLOAD_VERSION_FILE, "rb") as handle:
        expected = tomllib.load(handle)["project"]["version"]
    version = read_payload_version(REAL_TEMPLATE)
    assert version == expected
    assert version is not None


def test_read_payload_version_degrades_to_none(tmp_path: Path) -> None:
    """
    @brief      A payload without a version declaration, with unparseable
                TOML, or with a missing/non-string version field yields None
                rather than raising.
    @return     None
    @exception  AssertionError If any degraded case raises or returns a value.
    """
    payload = _make_payload_root(tmp_path / "payload")
    assert read_payload_version(payload) is None

    version_file = payload / PAYLOAD_VERSION_FILE
    version_file.parent.mkdir(parents=True, exist_ok=True)

    version_file.write_text("not [valid toml", encoding="utf-8", newline="\n")
    assert read_payload_version(payload) is None

    version_file.write_text('[project]\nname = "aegis"\n', encoding="utf-8", newline="\n")
    assert read_payload_version(payload) is None

    version_file.write_text("[project]\nversion = 4\n", encoding="utf-8", newline="\n")
    assert read_payload_version(payload) is None

    version_file.write_text('[project]\nversion = "0.4.0"\n', encoding="utf-8", newline="\n")
    assert read_payload_version(payload) == "0.4.0"


# END OF FILE
