#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Generate and verify the exact canonical AEGIS payload manifest."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path, PurePosixPath


class PayloadError(ValueError):
    """Report an invalid or non-exact canonical payload."""


def _safe(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise PayloadError(f"Unsafe payload path: {value!r}")
    return path.as_posix()


def generate_manifest(
    payload_root: Path, version: str, *, platform: str = "source"
) -> bytes:
    """Render a sorted complete manifest for every regular payload file."""
    files: dict[str, bytes] = {}
    for path in sorted(payload_root.rglob("*"), key=lambda item: item.as_posix()):
        if (
            not path.is_file()
            or path.name == "manifest.toml"
            or "__pycache__" in path.parts
        ):
            continue
        relative = path.relative_to(payload_root).as_posix()
        files[relative] = path.read_bytes()
    return render_manifest(files, version, platform=platform)


def render_manifest(files: dict[str, bytes], version: str, *, platform: str) -> bytes:
    """Render exact manifest bytes from an assembled payload file mapping."""
    entries = [
        (relative, len(content), hashlib.sha256(content).hexdigest())
        for relative, content in sorted(files.items())
        if relative != "manifest.toml"
    ]
    identity_source = "\n".join(
        f"{relative}\0{size}\0{digest}" for relative, size, digest in entries
    ).encode("utf-8")
    payload_id = hashlib.sha256(identity_source).hexdigest()[:32]
    lines = [
        "schema = 1",
        'artifact_type = "payload_manifest"',
        f'payload_id = "PAYLOAD-{payload_id}"',
        'product = "AEGIS"',
        f'product_version = "{version}"',
        f'platform = "{platform}"',
        'architecture = "x86_64"',
        "",
    ]
    for relative, size, digest in entries:
        lines.extend(
            [
                "[[files]]",
                f'path = "{relative}"',
                f"size = {size}",
                f'sha256 = "{digest}"',
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def verify_manifest(payload_root: Path) -> dict[str, bytes]:
    """Return all exact manifest-owned bytes or reject inventory drift."""
    try:
        manifest = (payload_root / "manifest.toml").read_bytes()
        data = tomllib.loads(manifest.decode("utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PayloadError(f"Payload manifest is invalid: {exc}") from exc
    if data.get("schema") != 1 or data.get("artifact_type") != "payload_manifest":
        raise PayloadError("Payload manifest schema is unsupported")
    files: dict[str, bytes] = {"manifest.toml": manifest}
    for entry in data.get("files", []):
        relative = _safe(str(entry.get("path", "")))
        if relative in files:
            raise PayloadError(f"Duplicate payload path: {relative}")
        try:
            candidate = (payload_root / Path(relative)).resolve(strict=True)
            candidate.relative_to(payload_root.resolve())
            content = candidate.read_bytes()
        except (OSError, ValueError) as exc:
            raise PayloadError(f"Missing payload file: {relative}") from exc
        if len(content) != entry.get("size") or (
            hashlib.sha256(content).hexdigest() != entry.get("sha256")
        ):
            raise PayloadError(f"Payload digest mismatch: {relative}")
        files[relative] = content
    actual = {
        path.relative_to(payload_root).as_posix()
        for path in payload_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if actual != set(files):
        differences = sorted(actual.symmetric_difference(files))
        raise PayloadError(f"Payload inventory mismatch: {differences}")
    return files
