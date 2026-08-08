#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file manifest.py
@brief Closed WAEGIS install-manifest schema and canonical path validation.
@details The manifest is an atomic completion receipt, never a transaction
         journal. Parsing rejects unknown fields and unsafe paths before any
         maintenance authority can be derived from it.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .ownership import Disposition
from .version import MANIFEST_VERSION


# CONSTANTS

MANIFEST_PATH = ".agentic/install-manifest.json"
_TOP_LEVEL_FIELDS = frozenset(
    {
        "manifest_version",
        "product",
        "payload_version",
        "payload_digest",
        "installed_at",
        "installed_by",
        "mode",
        "files",
        "configuration",
    }
)
_FILE_FIELDS = frozenset({"sha256", "size", "disposition"})
_CONFIG_FIELDS = frozenset({"answers", "generator_version", "workflow_sha256"})
_MODES = frozenset({"new", "adopt", "repair", "upgrade"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_RESERVED = frozenset(
    {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
)


# DATA MODELS / TYPEDEFINITIONS


class ManifestError(ValueError):
    """@brief Base failure for invalid or unsafe manifest data."""


class UnsupportedManifestError(ManifestError):
    """@brief Raised when a manifest is recognizable but not schema 2."""


@dataclass(frozen=True, slots=True)
class FileRecord:
    """@brief Observed file receipt and maintenance disposition."""

    sha256: str
    size: int
    disposition: Disposition

    def to_dict(self) -> dict[str, object]:
        """@brief Convert the record to its deterministic JSON mapping."""
        return {
            "sha256": self.sha256,
            "size": self.size,
            "disposition": self.disposition.value,
        }


@dataclass(frozen=True, slots=True)
class InstallManifest:
    """@brief Validated install-manifest schema 2 value."""

    payload_version: str
    payload_digest: str
    installed_at: str
    installed_by: str
    mode: str
    files: Mapping[str, FileRecord]
    configuration: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        """@brief Convert the manifest to a JSON-compatible closed mapping."""
        return {
            "manifest_version": MANIFEST_VERSION,
            "product": "aegis",
            "payload_version": self.payload_version,
            "payload_digest": self.payload_digest,
            "installed_at": self.installed_at,
            "installed_by": self.installed_by,
            "mode": self.mode,
            "files": {path: self.files[path].to_dict() for path in sorted(self.files)},
            "configuration": dict(self.configuration),
        }


# HELPER FUNCTIONS


def _require_fields(value: Mapping[str, Any], expected: frozenset[str], context: str) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ManifestError(f"{context} fields differ; missing={missing}, unknown={unknown}")


def _require_hash(value: object, context: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ManifestError(f"{context} must be a lowercase SHA-256")
    return value


def _validate_json_value(value: object, context: str) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{context}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ManifestError(f"{context} contains a non-string key")
            _validate_json_value(item, f"{context}.{key}")
        return
    raise ManifestError(f"{context} contains a non-JSON value")


def _is_reparse(path: Path) -> bool:
    details = path.lstat()
    attributes = getattr(details, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse)


# EXPORTED FUNCTIONS / PUBLIC API


def canonical_path(value: str) -> str:
    """
    @brief Validate and normalize a repository-relative portable path.
    @param[in] value Candidate path using forward slashes.
    @return The unchanged canonical value.
    @exception ManifestError If the path is ambiguous, platform-specific, or unsafe.
    """
    if not isinstance(value, str) or not value:
        raise ManifestError("path must be a non-empty string")
    if "\x00" in value or "\\" in value or value.startswith("/") or "//" in value:
        raise ManifestError(f"unsafe canonical path: {value!r}")
    if re.match(r"^[A-Za-z]:", value):
        raise ManifestError(f"absolute path is not allowed: {value!r}")
    path = PurePosixPath(value)
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ManifestError(f"path traversal is not allowed: {value!r}")
    for part in parts:
        if part.endswith((" ", ".")) or ":" in part:
            raise ManifestError(f"non-portable path component: {part!r}")
        stem = part.split(".", 1)[0].casefold()
        if stem in _WINDOWS_RESERVED:
            raise ManifestError(f"reserved path component: {part!r}")
    if path.as_posix() != value:
        raise ManifestError(f"path is not canonical: {value!r}")
    return value


def contained_destination(repository: Path, relative: str, *, allow_missing: bool = True) -> Path:
    """
    @brief Resolve a canonical destination while rejecting linked parents.
    @param[in] repository Repository root.
    @param[in] relative Canonical relative path.
    @param[in] allow_missing Permit an absent final path.
    @return Lexically contained destination.
    @exception ManifestError If containment or link checks fail.
    """
    canonical_path(relative)
    root = repository.resolve(strict=True)
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        if current.exists() and _is_reparse(current):
            raise ManifestError(f"destination parent is a link/reparse point: {relative}")
    if candidate.exists():
        if _is_reparse(candidate):
            raise ManifestError(f"destination is a link/reparse point: {relative}")
    elif not allow_missing:
        raise ManifestError(f"destination does not exist: {relative}")
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ManifestError(f"destination escapes repository: {relative}") from exc
    return candidate


def file_record(data: bytes, disposition: Disposition) -> FileRecord:
    """@brief Build one file receipt without a second verification pass."""
    return FileRecord(hashlib.sha256(data).hexdigest(), len(data), disposition)


def parse_manifest(value: Mapping[str, Any]) -> InstallManifest:
    """
    @brief Parse and validate one manifest mapping.
    @param[in] value Decoded JSON mapping.
    @return Closed schema-2 manifest.
    @exception ManifestError If any field or semantic invariant fails.
    @exception UnsupportedManifestError If the schema version is not 2.
    """
    if not isinstance(value, Mapping):
        raise ManifestError("manifest must be a JSON object")
    version = value.get("manifest_version")
    if version != MANIFEST_VERSION:
        raise UnsupportedManifestError(f"unsupported install manifest version: {version!r}")
    _require_fields(value, _TOP_LEVEL_FIELDS, "manifest")
    if value["product"] != "aegis":
        raise ManifestError("manifest product must be 'aegis'")
    for field in ("payload_version", "installed_at", "installed_by"):
        if not isinstance(value[field], str) or not value[field]:
            raise ManifestError(f"manifest {field} must be a non-empty string")
    payload_digest = _require_hash(value["payload_digest"], "manifest payload_digest")
    mode = value["mode"]
    if mode not in _MODES:
        raise ManifestError(f"invalid manifest mode: {mode!r}")
    raw_files = value["files"]
    if not isinstance(raw_files, dict):
        raise ManifestError("manifest files must be an object")
    files: dict[str, FileRecord] = {}
    folded: set[str] = set()
    for raw_path, raw_record in raw_files.items():
        path = canonical_path(raw_path)
        if path == MANIFEST_PATH:
            raise ManifestError("manifest cannot list itself")
        key = path.casefold()
        if key in folded:
            raise ManifestError(f"case-colliding manifest path: {path}")
        folded.add(key)
        if not isinstance(raw_record, dict):
            raise ManifestError(f"file record must be an object: {path}")
        _require_fields(raw_record, _FILE_FIELDS, f"file {path}")
        digest = _require_hash(raw_record["sha256"], f"file {path} sha256")
        size = raw_record["size"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ManifestError(f"file {path} size must be a non-negative integer")
        try:
            disposition = Disposition(raw_record["disposition"])
        except (TypeError, ValueError) as exc:
            raise ManifestError(f"file {path} has invalid disposition") from exc
        files[path] = FileRecord(digest, size, disposition)
    raw_configuration = value["configuration"]
    if not isinstance(raw_configuration, dict):
        raise ManifestError("manifest configuration must be an object")
    unknown_config = set(raw_configuration) - _CONFIG_FIELDS
    if unknown_config:
        raise ManifestError(f"unknown configuration fields: {sorted(unknown_config)}")
    _validate_json_value(raw_configuration, "configuration")
    return InstallManifest(
        payload_version=value["payload_version"],
        payload_digest=payload_digest,
        installed_at=value["installed_at"],
        installed_by=value["installed_by"],
        mode=mode,
        files=files,
        configuration=dict(raw_configuration),
    )


def serialize_manifest(manifest: InstallManifest) -> bytes:
    """@brief Validate and serialize a manifest deterministically."""
    validated = parse_manifest(manifest.to_dict())
    return (json.dumps(validated.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_manifest(path: Path) -> InstallManifest:
    """@brief Load strict UTF-8 JSON and validate manifest schema 2."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read install manifest {path}: {exc}") from exc
    return parse_manifest(raw)


def write_manifest_atomic(path: Path, manifest: InstallManifest) -> None:
    """
    @brief Publish a validated manifest with one same-directory atomic replace.
    @param[in] path Destination manifest path.
    @param[in] manifest Validated completion receipt.
    @return None.
    """
    data = serialize_manifest(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}-{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def detect_manifest_version(path: Path) -> int | None:
    """
    @brief Read only the top-level schema discriminator for migration guidance.
    @param[in] path Candidate V1/V2 manifest.
    @return Integer version, or None when absent/unrecognizable.
    """
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    version = value.get("manifest_version", value.get("schema_version"))
    return version if isinstance(version, int) and not isinstance(version, bool) else None


# END OF FILE
