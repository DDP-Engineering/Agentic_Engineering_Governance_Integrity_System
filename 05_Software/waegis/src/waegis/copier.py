#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file copier.py
@brief Closed payload inventory and atomic byte publication helpers.
@details Enumerates one deterministic payload, rejects ambiguous filesystem
         entries, and assigns ownership before any install plan is rendered.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .manifest import ManifestError, canonical_path
from .ownership import Disposition, initial_disposition


# CONSTANTS

_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".hypothesis",
        ".svn",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".uv-cache",
        ".uv_cache",
        "__pycache__",
        "node_modules",
        "htmlcov",
    }
)
_EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})
_EXCLUDED_FILES = frozenset({".coverage", "coverage.xml"})


# DATA MODELS / TYPEDEFINITIONS


class InventoryError(ManifestError):
    """@brief Raised when payload membership or bytes are unsafe or inconsistent."""


@dataclass(frozen=True, slots=True)
class InventoryRecord:
    """@brief One immutable payload entry."""

    path: str
    size: int
    sha256: str
    disposition: Disposition

    def to_dict(self) -> dict[str, object]:
        """@brief Convert the record to a JSON-compatible mapping."""
        return {
            "path": self.path,
            "size": self.size,
            "sha256": self.sha256,
            "disposition": self.disposition.value,
        }


@dataclass(frozen=True, slots=True)
class PayloadInventory:
    """@brief Closed sorted payload inventory and identity digest."""

    records: tuple[InventoryRecord, ...]
    digest: str

    @property
    def by_path(self) -> Mapping[str, InventoryRecord]:
        """@brief Return records keyed by canonical path."""
        return {record.path: record for record in self.records}

    def to_dict(self) -> dict[str, object]:
        """@brief Convert the inventory to a deterministic serializable mapping."""
        return {
            "schema_version": 1,
            "digest": self.digest,
            "files": [record.to_dict() for record in self.records],
        }


# HELPER FUNCTIONS


def _is_reparse(path: Path) -> bool:
    details = path.lstat()
    attributes = getattr(details, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse)


def _hash_file_once(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return size, digest.hexdigest()


def _inventory_digest(records: Iterable[InventoryRecord]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record.size).encode("ascii"))
        digest.update(b"\0")
        digest.update(record.sha256.encode("ascii"))
        digest.update(b"\0")
        digest.update(record.disposition.value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


# EXPORTED FUNCTIONS / PUBLIC API


def enumerate_payload(root: Path) -> PayloadInventory:
    """
    @brief Enumerate, classify, and hash every installable payload file.
    @param[in] root Payload root directory.
    @return Sorted closed inventory.
    @exception InventoryError If a member is unsafe or ambiguous.
    """
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise InventoryError(f"payload root does not exist: {root}") from exc
    if not resolved.is_dir() or _is_reparse(resolved):
        raise InventoryError(f"payload root is not a regular directory: {root}")
    records: list[InventoryRecord] = []
    folded: set[str] = set()
    for directory, names, files in os.walk(resolved, topdown=True, followlinks=False):
        directory_path = Path(directory)
        kept_directories: list[str] = []
        for name in sorted(names):
            child = directory_path / name
            if name in _EXCLUDED_DIRECTORIES or name.endswith(".egg-info"):
                continue
            if _is_reparse(child):
                raise InventoryError(f"payload directory is a link/reparse point: {child}")
            kept_directories.append(name)
        names[:] = kept_directories
        for name in sorted(files):
            if name in _EXCLUDED_FILES or Path(name).suffix in _EXCLUDED_SUFFIXES:
                continue
            source = directory_path / name
            if _is_reparse(source) or not source.is_file():
                raise InventoryError(f"payload member is not a regular file: {source}")
            relative = source.relative_to(resolved).as_posix()
            path = canonical_path(relative)
            key = path.casefold()
            if key in folded:
                raise InventoryError(f"case-colliding payload path: {path}")
            folded.add(key)
            size, digest = _hash_file_once(source)
            records.append(InventoryRecord(path, size, digest, initial_disposition(path)))
    records.sort(key=lambda record: record.path.encode("utf-8"))
    return PayloadInventory(tuple(records), _inventory_digest(records))


def verify_inventory(root: Path, expected: PayloadInventory) -> None:
    """
    @brief Verify exact payload membership and content against an inventory.
    @param[in] root Extracted payload root.
    @param[in] expected Closed expected inventory.
    @exception InventoryError If any membership, metadata, or digest differs.
    """
    actual = enumerate_payload(root)
    if actual != expected:
        expected_paths = set(expected.by_path)
        actual_paths = set(actual.by_path)
        raise InventoryError(
            "payload inventory mismatch; "
            f"missing={sorted(expected_paths - actual_paths)}, "
            f"unexpected={sorted(actual_paths - expected_paths)}, "
            f"expected_digest={expected.digest}, actual_digest={actual.digest}"
        )


def serialize_inventory(inventory: PayloadInventory) -> bytes:
    """@brief Serialize a closed inventory deterministically."""
    return (json.dumps(inventory.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_inventory(value: object) -> PayloadInventory:
    """
    @brief Parse a closed inventory mapping.
    @param[in] value Decoded JSON value.
    @return Validated payload inventory.
    @exception InventoryError If schema or digest validation fails.
    """
    if not isinstance(value, dict) or set(value) != {"schema_version", "digest", "files"}:
        raise InventoryError("inventory must use the closed schema")
    if value["schema_version"] != 1 or not isinstance(value["files"], list):
        raise InventoryError("unsupported inventory schema")
    records: list[InventoryRecord] = []
    folded: set[str] = set()
    for item in value["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256", "disposition"}:
            raise InventoryError("inventory file record must use the closed schema")
        path = canonical_path(item["path"])
        if path.casefold() in folded:
            raise InventoryError(f"case-colliding inventory path: {path}")
        folded.add(path.casefold())
        size = item["size"]
        digest = item["sha256"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise InventoryError(f"invalid inventory size: {path}")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise InventoryError(f"invalid inventory digest: {path}")
        try:
            disposition = Disposition(item["disposition"])
        except (TypeError, ValueError) as exc:
            raise InventoryError(f"invalid inventory disposition: {path}") from exc
        records.append(InventoryRecord(path, size, digest, disposition))
    records.sort(key=lambda record: record.path.encode("utf-8"))
    digest = _inventory_digest(records)
    if value["digest"] != digest:
        raise InventoryError("inventory identity digest does not match its records")
    return PayloadInventory(tuple(records), digest)


def write_bytes_atomic(destination: Path, data: bytes) -> None:
    """@brief Publish bytes with one same-directory atomic replacement."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.{os.getpid()}-{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


# END OF FILE
