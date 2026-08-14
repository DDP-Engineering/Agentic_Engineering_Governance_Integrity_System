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
@brief Characterization tests for the isolated AEGIS release builder.
@details Redirects generated archives and publication records to pytest-managed
         temporary paths, leaving the repository's tracked delivery records
         untouched while exercising deterministic packaging behavior.
"""

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import pytest


# CONSTANTS

ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = ROOT / "02_Tools" / "build_aegis_release.py"
COUNTER = itertools.count()


# HELPER FUNCTIONS

def load_builder():
    """Load a fresh builder module so each test can redirect its globals."""
    spec = importlib.util.spec_from_file_location(
        f"release_builder_under_test_{next(COUNTER)}", BUILDER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def configure_output(builder, tmp_path: Path) -> None:
    """Redirect generated release outputs away from the checked-out records."""
    (tmp_path / "CHANGELOG.md").write_bytes(
        (builder.REPO_ROOT / "CHANGELOG.md").read_bytes()
    )
    builder.REPO_ROOT = tmp_path
    builder.DELIVERY = tmp_path / "delivery"
    builder.DIST = builder.DELIVERY / "dist"


def digest(path: Path) -> str:
    """Return a SHA-256 digest for deterministic-archive assertions."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# TESTS

def test_build_writes_deterministic_archives_and_publication_records(
        tmp_path, monkeypatch):
    """REQ-REL-59983fe5: isolated output remains reproducible and recorded."""
    builder = load_builder()
    configure_output(builder, tmp_path)
    monkeypatch.setattr(builder, "run_tests", lambda: None)
    version = builder.payload_version()

    assert builder.build(version) == 0
    prefix = f"{builder.NAME}-{version}"
    artifacts = [builder.DIST / f"{prefix}.zip", builder.DIST / f"{prefix}.tar.gz"]
    first_digests = {path.name: digest(path) for path in artifacts}
    record = builder.DELIVERY / prefix
    manifest = json.loads((record / "release-manifest.json").read_text("utf-8"))

    assert manifest["version"] == version
    assert {item["sha256"] for item in manifest["artifacts"].values()} == set(
        first_digests.values()
    )
    assert (record / "SHA256SUMS").is_file()
    assert (record / "RELEASE.md").is_file()
    for path in artifacts:
        assert f"{prefix}/.agentic/aegis.py" in builder.archive_members(path)
        assert f"{prefix}/INSTALL.md" in builder.archive_members(path)

    assert builder.build(version) == 0
    assert {path.name: digest(path) for path in artifacts} == first_digests


def test_build_rejects_a_mismatched_version_before_writing_output(
        tmp_path, monkeypatch):
    """REQ-REL-d875f7a3: mismatched version requests create no delivery output."""
    builder = load_builder()
    configure_output(builder, tmp_path)
    monkeypatch.setattr(builder, "run_tests", lambda: pytest.fail("unexpected run"))

    with pytest.raises(SystemExit, match="does not match payload"):
        builder.build("0.0.0")

    assert not builder.DELIVERY.exists()


def test_build_validates_and_tests_before_staging_release_files(
        tmp_path, monkeypatch):
    """REQ-REL-858e8cac: validation completes before release assembly begins."""
    builder = load_builder()
    configure_output(builder, tmp_path)
    events = []
    original_stage_tree = builder.stage_tree

    monkeypatch.setattr(builder, "verify_payload", lambda: events.append("payload"))
    monkeypatch.setattr(builder, "run_tests", lambda: events.append("tests"))

    def stage_tree(stage, version):
        assert events == ["payload", "tests"]
        return original_stage_tree(stage, version)

    monkeypatch.setattr(builder, "stage_tree", stage_tree)
    assert builder.build(builder.payload_version()) == 0
