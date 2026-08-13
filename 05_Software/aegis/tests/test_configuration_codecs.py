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
    _load_toml,
    decode_general_text,
    parse_markdown_document,
    parse_project_config,
    render_markdown_document,
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


def test_configuration_parser_ignores_legacy_timeout() -> None:
    """@brief Legacy timeout input stays readable without entering the model."""
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
                    "timeout_seconds": "ignored legacy value",
                }
            },
        },
        "policy": {
            "risk_attention_threshold": "medium",
            "protected_scope_patterns": [],
        },
    }
    parsed = parse_project_config(source, path="config.toml")

    assert [str(path) for path in parsed.test_roots] == [
        "tests/unit",
        "tests/service",
    ]
    assert parsed.commands["tests.project"].command == ("python", "-m", "pytest")
    assert parsed.commands["lints.ruff"].command == ("ruff", "check", ".")
    assert not hasattr(parsed.commands["tests.project"], "timeout_seconds")


def test_toml_temporal_values_are_normalized_recursively() -> None:
    """@brief Low-level TOML decoding emits protocol-safe temporal strings."""
    parsed = _load_toml(
        b"created = 2026-01-01T00:00:00Z\n"
        b"dates = [2026-01-02, 2026-01-03]\n"
        b"[nested]\nlocal_time = 12:34:56\n",
        path="temporal.toml",
    )

    assert parsed == {
        "created": "2026-01-01T00:00:00+00:00",
        "dates": ["2026-01-02", "2026-01-03"],
        "nested": {"local_time": "12:34:56"},
    }


def test_component_codec_round_trip_preserves_file_digest_baselines() -> None:
    """@brief Component exact-byte baselines survive canonical codec round trips."""
    metadata = {
        "schema": 1,
        "artifact_type": "component",
        "id": "COMP-0123456789abcdef0123456789abcdef",
        "status": "active",
        "name": "Binary member owner",
        "files": ["src/alpha.py", "src/zeta.bin"],
        "requirement_ids": [],
        "reviewed_at": "2026-08-13T00:00:00Z",
    }
    state = {
        "purpose_boundary": "Own two declared members.",
        "interfaces": "None",
        "requirement_links": [],
        "file_roles": [
            {"path": "src/alpha.py", "role": "Text member."},
            {"path": "src/zeta.bin", "role": "Binary member."},
        ],
        "dependencies": [],
        "test_links": [],
        "known_gaps": [],
        "drift_review": {
            "behavior": "yes",
            "interfaces": "yes",
            "dependencies": "yes",
            "files": "yes",
        },
        "file_digests": {
            "src/alpha.py": "a" * 64,
            "src/zeta.bin": "f" * 64,
        },
    }

    rendered = render_markdown_document(metadata, state, kind="component")
    reparsed_metadata, reparsed_state, _ = parse_markdown_document(
        rendered, path=".agentic/components/COMP-example.md"
    )

    assert reparsed_state["file_digests"] == state["file_digests"]
    assert (
        render_markdown_document(reparsed_metadata, reparsed_state, kind="component")
        == rendered
    )


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
