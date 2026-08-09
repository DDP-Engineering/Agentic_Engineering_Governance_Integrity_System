#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_release_builder.py
@brief Regression tests for AEGIS Light release-version selection.
@details The builder must derive a non-empty version from the payload and
         refuse an explicit archive label that disagrees with it.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# CONSTANTS

BUILDER_PATH = (Path(__file__).resolve().parents[3]
                / "02_Tools" / "build_aegis_light_release.py")

# HELPERS


@pytest.fixture
def builder():
    """@brief Load a fresh release-builder module for each test."""
    spec = importlib.util.spec_from_file_location("aegis_light_release_builder",
                                                  BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def set_payload_source(builder, monkeypatch, tmp_path: Path, source: str) -> None:
    """@brief Point the builder at a temporary payload containing `source`."""
    payload = tmp_path / ".agentic"
    payload.mkdir()
    (payload / "aegis.py").write_text(source, encoding="utf-8", newline="\n")
    monkeypatch.setattr(builder, "PAYLOAD", payload)


class VerificationReached(Exception):
    """@brief Sentinel proving version validation reached payload verification."""


# TESTS


@pytest.mark.parametrize("source", [
    'VERSION = "0.2.0"\n',
    "VERSION = '0.2.0'\n",
    "VERSION: str = '0.2.0'\n",
])
def test_payload_version_reads_python_string_assignments(builder, monkeypatch,
                                                          tmp_path, source):
    set_payload_source(builder, monkeypatch, tmp_path, source)
    assert builder.payload_version() == "0.2.0"


@pytest.mark.parametrize("source", [
    "NAME = 'aegis-light'\n",
    "VERSION = ''\n",
    "VERSION = 200\n",
])
def test_payload_version_rejects_missing_empty_or_non_string_values(
        builder, monkeypatch, tmp_path, source):
    set_payload_source(builder, monkeypatch, tmp_path, source)
    with pytest.raises(SystemExit, match="non-empty string VERSION"):
        builder.payload_version()


def test_payload_version_rejects_an_unreadable_payload(builder, monkeypatch,
                                                        tmp_path):
    monkeypatch.setattr(builder, "PAYLOAD", tmp_path / "missing")
    with pytest.raises(SystemExit, match="cannot read payload version"):
        builder.payload_version()


def test_parser_defers_the_default_until_the_build_runs(builder):
    assert builder._build_arg_parser().parse_args([]).version is None


@pytest.mark.parametrize("requested", [None, "0.2.0"])
def test_build_resolves_default_and_matching_versions_before_verification(
        builder, monkeypatch, requested):
    calls = []

    def version():
        calls.append("version")
        return "0.2.0"

    def verification():
        calls.append("verification")
        raise VerificationReached

    monkeypatch.setattr(builder, "payload_version", version)
    monkeypatch.setattr(builder, "verify_payload", verification)
    with pytest.raises(VerificationReached):
        builder.build(requested, False)
    assert calls == ["version", "verification"]


def test_build_rejects_a_label_that_disagrees_with_the_payload(
        builder, monkeypatch):
    monkeypatch.setattr(builder, "payload_version", lambda: "0.2.0")
    monkeypatch.setattr(
        builder, "verify_payload",
        lambda: pytest.fail("payload verification ran after a version mismatch"),
    )
    with pytest.raises(SystemExit, match="does not match payload VERSION"):
        builder.build("0.1.0", False)


# END OF FILE
