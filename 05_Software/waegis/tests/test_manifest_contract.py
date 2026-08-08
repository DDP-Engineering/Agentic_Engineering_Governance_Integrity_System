#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_manifest_contract.py
@brief Adversarial tests for manifest schema 2 and portable paths.
@details Proves deterministic golden serialization and rejects authority-bearing
         ambiguity before maintenance commands can use a manifest.
"""

import json
from pathlib import Path

import pytest

from waegis.manifest import (
    ManifestError,
    UnsupportedManifestError,
    canonical_path,
    detect_manifest_version,
    parse_manifest,
    serialize_manifest,
)


FIXTURE = Path(__file__).parent / "fixtures" / "install-manifest-v2.json"


def _fixture_value() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_golden_manifest_round_trips_byte_identically() -> None:
    """@brief R4 pins the deterministic closed schema-2 receipt."""
    manifest = parse_manifest(_fixture_value())
    assert serialize_manifest(manifest) == FIXTURE.read_bytes()


@pytest.mark.parametrize(
    "path",
    ["", "/root", "C:/root", "a\\b", "a//b", "a/../b", "a/./b", "NUL.txt", "a./b", "a:b"],
)
def test_canonical_paths_reject_unsafe_or_nonportable_values(path: str) -> None:
    """@brief R4 rejects traversal, platform ambiguity, and device names."""
    with pytest.raises(ManifestError):
        canonical_path(path)


def test_manifest_rejects_unknown_top_level_and_file_fields() -> None:
    """@brief Closed schemas cannot silently acquire maintenance authority."""
    value = _fixture_value()
    value["unexpected"] = True
    with pytest.raises(ManifestError, match="unknown"):
        parse_manifest(value)
    value = _fixture_value()
    value["files"][".agentic/cli/a.py"]["extra"] = 1  # type: ignore[index]
    with pytest.raises(ManifestError, match="unknown"):
        parse_manifest(value)


def test_manifest_rejects_case_collision_self_listing_and_bad_disposition() -> None:
    """@brief R4 denies ambiguous paths and invalid ownership vocabulary."""
    value = _fixture_value()
    value["files"][".AGENTIC/CLI/A.py"] = value["files"][".agentic/cli/a.py"]  # type: ignore[index]
    with pytest.raises(ManifestError, match="case-colliding"):
        parse_manifest(value)
    value = _fixture_value()
    value["files"][".agentic/install-manifest.json"] = value["files"][".agentic/cli/a.py"]  # type: ignore[index]
    with pytest.raises(ManifestError, match="list itself"):
        parse_manifest(value)
    value = _fixture_value()
    value["files"][".agentic/cli/a.py"]["disposition"] = "owned"  # type: ignore[index]
    with pytest.raises(ManifestError, match="invalid disposition"):
        parse_manifest(value)


def test_v1_detector_reads_only_a_top_level_discriminator(tmp_path: Path) -> None:
    """@brief R1 recognizes prior state without loading V1 ownership data."""
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version": 1, "files": "untrusted"}', encoding="utf-8")
    assert detect_manifest_version(path) == 1
    path.write_text("not-json", encoding="utf-8")
    assert detect_manifest_version(path) is None


def test_unsupported_manifest_version_has_a_distinct_failure() -> None:
    """@brief Upgrade can route V1 safely without treating it as corrupt V2."""
    value = _fixture_value()
    value["manifest_version"] = 1
    with pytest.raises(UnsupportedManifestError):
        parse_manifest(value)


# END OF FILE
