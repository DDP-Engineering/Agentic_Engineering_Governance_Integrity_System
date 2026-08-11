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
@file    payload.py
@brief   Load and verify the exact manifest-owned AEGIS payload files.
@details Treats project-owned siblings outside .agentic/aegis as out of scope.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from aegis.domain.values import RepositoryPath, ValueValidationError
from aegis.infrastructure.codecs import ArtifactDecodeError


@dataclass(frozen=True, slots=True)
class PayloadFile:
    """@brief Describe one exact manifest-owned payload file."""

    path: RepositoryPath
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class PayloadManifest:
    """@brief Hold payload identity and its exact owned file inventory."""

    payload_id: str
    product_version: str
    platform: str
    architecture: str
    files: tuple[PayloadFile, ...]


@dataclass(frozen=True, slots=True)
class PayloadFinding:
    """@brief Describe one manifest verification discrepancy."""

    code: str
    path: str
    summary: str


def load_payload_manifest(path: Path) -> PayloadManifest:
    """@brief Load a version 1 payload manifest without rewriting it."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("schema") != 1 or data.get("artifact_type") != "payload_manifest":
            raise ArtifactDecodeError(
                "unsupported payload_manifest schema", path=str(path)
            )
        entries = tuple(
            PayloadFile(
                path=RepositoryPath(item["path"]),
                size=item["size"],
                sha256=item["sha256"],
            )
            for item in data.get("files", [])
        )
        if len({str(entry.path) for entry in entries}) != len(entries):
            raise ArtifactDecodeError("duplicate payload path", path=str(path))
        return PayloadManifest(
            payload_id=data["payload_id"],
            product_version=data["product_version"],
            platform=data["platform"],
            architecture=data["architecture"],
            files=entries,
        )
    except ArtifactDecodeError:
        raise
    except (
        OSError,
        UnicodeError,
        tomllib.TOMLDecodeError,
        KeyError,
        TypeError,
        ValueValidationError,
    ) as error:
        raise ArtifactDecodeError(
            "malformed payload manifest", path=str(path)
        ) from error


def verify_payload(root: Path, manifest: PayloadManifest) -> tuple[PayloadFinding, ...]:
    """@brief Compare exact owned bytes with the manifest without changing them."""
    findings: list[PayloadFinding] = []
    resolved_root = root.resolve()
    for entry in manifest.files:
        target = root.joinpath(*str(entry.path).split("/"))
        try:
            resolved = target.resolve(strict=True)
            resolved.relative_to(resolved_root)
        except (OSError, ValueError):
            findings.append(
                PayloadFinding(
                    "payload_missing",
                    str(entry.path),
                    "Owned payload file is missing or unsafe.",
                )
            )
            continue
        if not resolved.is_file():
            findings.append(
                PayloadFinding(
                    "payload_missing",
                    str(entry.path),
                    "Owned payload file is not a regular file.",
                )
            )
            continue
        content = resolved.read_bytes()
        if len(content) != entry.size or sha256(content).hexdigest() != entry.sha256:
            findings.append(
                PayloadFinding(
                    "payload_modified",
                    str(entry.path),
                    "Owned payload bytes differ from the manifest.",
                )
            )
    owned = {str(entry.path) for entry in manifest.files} | {"manifest.toml"}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in owned:
            findings.append(
                PayloadFinding(
                    "payload_unowned",
                    relative,
                    "Payload directory contains a file outside the manifest.",
                )
            )
    return tuple(findings)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
