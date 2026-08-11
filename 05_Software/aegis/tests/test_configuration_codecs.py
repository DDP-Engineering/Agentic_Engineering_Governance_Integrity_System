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
@file    test_configuration_codecs.py
@brief   Verify configuration, encoding, path, and payload codec contracts.
@details Covers PR-CONFIG, PR-ENC, PR-PAYLOAD, AC-CONFIG-001, AC-ENC-001,
         and AC-PAYLOAD-001 for IP-02.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from aegis.domain.values import RepositoryPath, ValueValidationError
from aegis.infrastructure.codecs import (
    ArtifactDecodeError,
    decode_general_text,
    parse_project_config,
    render_project_config,
)
from aegis.infrastructure.payload import load_payload_manifest, verify_payload


def test_repository_path_rejects_absolute_and_escape_values() -> None:
    """@brief Repository-owned paths cannot escape their root."""
    assert str(RepositoryPath("src/orders.py")) == "src/orders.py"
    for unsafe in ("../outside", "/absolute", "C:/absolute", "a/./b", "a//b"):
        with pytest.raises(ValueValidationError):
            RepositoryPath(unsafe)


def test_general_text_decodes_supported_windows_forms_without_byte_guessing() -> None:
    """@brief BOM, CRLF, and permitted Windows-1252 input decode explicitly."""
    assert decode_general_text(b"\xef\xbb\xbfhello\r\n", path="ticket.txt") == "hello\n"
    assert (
        decode_general_text("café\r\n".encode("cp1252"), path="ticket.txt") == "café\n"
    )
    with pytest.raises(ArtifactDecodeError, match="ticket.txt"):
        decode_general_text(b"\x81", path="ticket.txt")


def test_configuration_round_trip_is_canonical_and_supports_multiple_roots() -> None:
    """@brief Canonical rendering preserves command arrays and unlimited timeout."""
    source = {
        "schema": 1,
        "artifact_type": "project_config",
        "paths": {
            "requirements": ".agentic/requirements",
            "components": ".agentic/components",
            "tests": ["tests/unit", "tests/service"],
            "adoptions": ".agentic/adoptions",
            "runs": ".agentic/runs",
        },
        "validation": {
            "tests": {
                "project": {
                    "command": ["python", "-m", "pytest"],
                    "working_directory": ".",
                    "timeout_seconds": 0,
                }
            },
            "lints": {
                "ruff": {
                    "command": ["ruff", "check", "."],
                    "working_directory": ".",
                    "timeout_seconds": 12,
                }
            },
        },
        "policy": {
            "risk_attention_threshold": "medium",
            "protected_scope_patterns": [],
        },
    }
    rendered = render_project_config(parse_project_config(source, path="config.toml"))
    reparsed = parse_project_config(rendered, path="config.toml")

    assert rendered.endswith(b"\n")
    assert b"\r" not in rendered
    assert [str(path) for path in reparsed.test_roots] == [
        "tests/unit",
        "tests/service",
    ]
    assert reparsed.commands["tests.project"].timeout_seconds == 0
    assert reparsed.commands["lints.ruff"].command == ("ruff", "check", ".")


def test_payload_verification_reports_exact_missing_modified_and_unowned_files(
    tmp_path: Path,
) -> None:
    """@brief Manifest ownership is exact and excludes project-owned siblings."""
    payload = tmp_path / ".agentic" / "aegis"
    payload.mkdir(parents=True)
    owned = payload / "cli.txt"
    owned.write_bytes(b"owned\n")
    digest = sha256(owned.read_bytes()).hexdigest()
    manifest = payload / "manifest.toml"
    manifest.write_text(
        "\n".join(
            (
                "schema = 1",
                'artifact_type = "payload_manifest"',
                'payload_id = "PAYLOAD-0123456789abcdef0123456789abcdef"',
                'product = "AEGIS"',
                'product_version = "1.0.0"',
                'platform = "windows"',
                'architecture = "x86_64"',
                "",
                "[[files]]",
                'path = "cli.txt"',
                "size = 6",
                f'sha256 = "{digest}"',
                "",
            )
        ),
        encoding="utf-8",
        newline="\n",
    )
    project_owned = tmp_path / ".agentic" / "rules.md"
    project_owned.write_text("project\n", encoding="utf-8")
    unowned = payload / "extra.txt"

    loaded = load_payload_manifest(manifest)
    assert verify_payload(payload, loaded) == ()
    unowned.write_text("unexpected\n", encoding="utf-8")
    owned.write_bytes(b"changed\n")
    findings = verify_payload(payload, loaded)

    assert [finding.code for finding in findings] == [
        "payload_modified",
        "payload_unowned",
    ]
    assert project_owned.read_text(encoding="utf-8") == "project\n"
