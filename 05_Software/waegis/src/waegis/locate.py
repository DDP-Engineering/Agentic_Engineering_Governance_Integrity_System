#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file locate.py
@brief Resolve explicit and source-checkout AEGIS payloads.
@details Phase-one resolution validates payload identity without importing the
         payload package. Zipapp extraction is added by the packaging phase.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import tomllib
import zipfile
import sys
from pathlib import Path

from .copier import InventoryError, PayloadInventory, enumerate_payload, parse_inventory, verify_inventory
from .manifest import canonical_path
from .runtime import waegis_home
from .version import is_payload_compatible


# CONSTANTS

PAYLOAD_VERSION_FILE = ".agentic/cli/pyproject.toml"


# DATA MODELS / TYPEDEFINITIONS


class PayloadError(ValueError):
    """@brief Raised when a payload cannot be resolved or is incompatible."""


# EXPORTED FUNCTIONS / PUBLIC API


def source_checkout_payload() -> Path | None:
    """@brief Return the repository-adjacent AEGIS template when present."""
    software_root = Path(__file__).resolve().parents[3]
    candidate = software_root / "aegis" / "template"
    return candidate.resolve() if candidate.is_dir() else None


def packaged_zipapp() -> Path | None:
    """@brief Return the executing payload-bearing zipapp when applicable."""
    candidate = Path(sys.argv[0]).resolve()
    return candidate if candidate.is_file() and zipfile.is_zipfile(candidate) else None


def _packaged_payload() -> tuple[Path, PayloadInventory] | None:
    archive = packaged_zipapp()
    if archive is None:
        return None
    try:
        with zipfile.ZipFile(archive) as bundle:
            inventory = parse_inventory(json.loads(bundle.read("payload-inventory.json")))
    except (OSError, KeyError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, InventoryError) as exc:
        raise PayloadError(f"cannot read embedded payload inventory: {exc}") from exc
    return extract_zipapp_payload(archive, inventory, waegis_home() / "payload-cache"), inventory


def read_payload_version(root: Path) -> str:
    """
    @brief Read the payload version from its embedded Python project metadata.
    @param[in] root Payload root.
    @return Version text.
    @exception PayloadError If metadata is absent or malformed.
    """
    path = root.joinpath(*PAYLOAD_VERSION_FILE.split("/"))
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        version = data["project"]["version"]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise PayloadError(f"cannot read payload version from {path}: {exc}") from exc
    if not isinstance(version, str) or not version:
        raise PayloadError(f"payload version is invalid in {path}")
    return version


def resolve_payload(explicit: Path | None = None) -> tuple[Path, str, PayloadInventory]:
    """
    @brief Resolve and verify a directory payload for planning.
    @param[in] explicit Optional operator-supplied payload root.
    @return Resolved root, compatible version, and closed inventory.
    @exception PayloadError If no compatible payload is available.
    """
    packaged = None if explicit is not None else _packaged_payload()
    root = explicit.resolve() if explicit is not None else packaged[0] if packaged else source_checkout_payload()
    if root is None or not root.is_dir():
        raise PayloadError("no AEGIS payload is available; pass --payload PATH")
    version = read_payload_version(root)
    try:
        compatible = is_payload_compatible(version)
    except ValueError as exc:
        raise PayloadError(f"payload version is invalid: {version!r}") from exc
    if not compatible:
        raise PayloadError(f"payload version {version!r} is outside >=3.0.0,<4.0.0")
    inventory = packaged[1] if packaged else enumerate_payload(root)
    return root, version, inventory


def extract_zipapp_payload(
    archive: Path,
    inventory: PayloadInventory,
    cache_root: Path,
) -> Path:
    """
    @brief Safely extract an inventoried ``payload/`` tree from a zipapp.
    @param[in] archive Payload-bearing zipapp/ZIP path.
    @param[in] inventory Closed expected payload inventory.
    @param[in] cache_root Per-user content cache root.
    @return Verified content-addressed payload directory.
    @exception PayloadError If archive membership, type, or bytes differ.
    """
    destination = cache_root / inventory.digest / "payload"
    if destination.is_dir():
        try:
            verify_inventory(destination, inventory)
        except InventoryError as exc:
            raise PayloadError(f"cached payload is invalid: {exc}") from exc
        return destination
    cache_root.mkdir(parents=True, exist_ok=True)
    temporary_parent = Path(tempfile.mkdtemp(prefix="waegis-payload-", dir=cache_root))
    temporary_payload = temporary_parent / "payload"
    temporary_payload.mkdir()
    expected = inventory.by_path
    seen: set[str] = set()
    folded: set[str] = set()
    try:
        try:
            bundle = zipfile.ZipFile(archive)
        except (OSError, zipfile.BadZipFile) as exc:
            raise PayloadError(f"cannot open payload archive {archive}: {exc}") from exc
        with bundle:
            for info in bundle.infolist():
                name = info.filename.replace("\\", "/")
                if not name.startswith("payload/") or name == "payload/":
                    continue
                relative = name[len("payload/") :].rstrip("/")
                try:
                    path = canonical_path(relative)
                except ValueError as exc:
                    raise PayloadError(f"unsafe payload archive member: {name!r}") from exc
                key = path.casefold()
                if key in folded:
                    raise PayloadError(f"duplicate or case-colliding archive member: {name!r}")
                mode = info.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                if info.is_dir():
                    continue
                seen.add(path)
                folded.add(key)
                if info.flag_bits & 0x1 or file_type not in {0, stat.S_IFREG}:
                    raise PayloadError(f"unsupported payload archive member type: {name!r}")
                record = expected.get(path)
                if record is None:
                    raise PayloadError(f"undeclared payload archive member: {path}")
                data = bundle.read(info)
                digest = hashlib.sha256(data).hexdigest()
                if len(data) != record.size or digest != record.sha256:
                    raise PayloadError(f"payload archive member digest mismatch: {path}")
                output = temporary_payload.joinpath(*path.split("/"))
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
        missing = sorted(set(expected) - seen)
        if missing:
            raise PayloadError(f"payload archive is missing members: {missing}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(temporary_payload, destination)
        except OSError:
            if not destination.is_dir():
                raise
            verify_inventory(destination, inventory)
        return destination
    except (OSError, zipfile.BadZipFile, InventoryError) as exc:
        raise PayloadError(f"cannot extract payload archive {archive}: {exc}") from exc
    finally:
        shutil.rmtree(temporary_parent, ignore_errors=True)


# END OF FILE
