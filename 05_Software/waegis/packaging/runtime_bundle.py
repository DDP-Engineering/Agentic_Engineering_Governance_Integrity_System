#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Build locked Windows/Linux native bundles around one exact WAEGIS zipapp."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Mapping


WINDOWS_LAUNCHER = b"""@echo off\r
setlocal\r
set "WAEGIS_PACKAGING_TYPE=windows-x64"\r
set "WAEGIS_PACKAGED_RUNTIME=%~dp0runtime\\python.exe"\r
"%WAEGIS_PACKAGED_RUNTIME%" "%~dp0waegis.pyz" %*\r
"""
LINUX_LAUNCHER = b"""#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export WAEGIS_PACKAGING_TYPE=linux-x64
export WAEGIS_PACKAGED_RUNTIME="$root/runtime/bin/python3.13"
exec "$WAEGIS_PACKAGED_RUNTIME" "$root/waegis.pyz" "$@"
"""
README = b"Unpack to a stable location, then run waegis.cmd (Windows) or ./waegis (Linux).\n"
TARGETS = ("windows-x64", "linux-x64")
EXCLUDED_RUNTIME_PREFIXES = ("share/terminfo/",)


class BundleError(ValueError):
    """Raised for unsafe, unlocked, or inconsistent runtime inputs."""


@dataclass(frozen=True, slots=True)
class RuntimeSource:
    """One closed locked upstream runtime input."""

    target: str
    asset: str
    url: str
    size: int
    sha256: str
    executable: str


@dataclass(frozen=True, slots=True)
class RuntimeMember:
    """One regular output member, possibly backed by a validated link target."""

    name: str
    source: tarfile.TarInfo
    mode: int


def _digest(path: Path) -> tuple[int, str]:
    value = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            value.update(block)
            size += len(block)
    return size, value.hexdigest()


def load_runtime_lock(path: Path) -> tuple[str, Mapping[str, RuntimeSource]]:
    """Parse the closed exact-source runtime lock."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BundleError(f"cannot read runtime lock: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "provider",
        "release",
        "python_version",
        "targets",
    }:
        raise BundleError("runtime lock has unknown or missing top-level fields")
    if value["schema_version"] != 2 or value["provider"] != "astral-sh/python-build-standalone":
        raise BundleError("unsupported runtime lock schema/provider")
    if not isinstance(value["python_version"], str) or not isinstance(value["release"], str):
        raise BundleError("runtime lock release/version must be strings")
    targets = value["targets"]
    if not isinstance(targets, dict) or set(targets) != set(TARGETS):
        raise BundleError("runtime lock must contain exactly Windows and Linux x64")
    result: dict[str, RuntimeSource] = {}
    for target in TARGETS:
        item = targets[target]
        if not isinstance(item, dict) or set(item) != {"asset", "url", "size", "sha256", "executable"}:
            raise BundleError(f"runtime lock target schema is invalid: {target}")
        if not all(isinstance(item[key], str) and item[key] for key in ("asset", "url", "sha256", "executable")):
            raise BundleError(f"runtime lock target strings are invalid: {target}")
        if not isinstance(item["size"], int) or isinstance(item["size"], bool) or item["size"] <= 0:
            raise BundleError(f"runtime lock target size is invalid: {target}")
        digest = item["sha256"]
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise BundleError(f"runtime lock target hash is invalid: {target}")
        result[target] = RuntimeSource(target=target, **item)
    return value["python_version"], result


def acquire_runtime(source: RuntimeSource, cache: Path, *, fetch: bool) -> Path:
    """Use only a verified cache object, optionally fetching its exact URL."""
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / source.asset
    if destination.is_file() and _digest(destination) == (source.size, source.sha256):
        return destination
    if not fetch:
        raise BundleError(f"verified runtime cache miss: {destination}; rerun with --fetch on an approved online builder")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{source.asset}.", suffix=".tmp", dir=cache)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with urllib.request.urlopen(source.url, timeout=120) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        if _digest(temporary) != (source.size, source.sha256):
            raise BundleError(f"downloaded runtime does not match lock: {source.asset}")
        os.replace(temporary, destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def _member_name(member: tarfile.TarInfo) -> str:
    """Return a validated archive-rooted POSIX member name."""
    if "\\" in member.name:
        raise BundleError(f"unsafe runtime member: {member.name}")
    name = member.name.rstrip("/")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise BundleError(f"unsafe runtime member: {member.name}")
    if path.parts[0] != "python":
        raise BundleError(f"unsafe runtime member: {member.name}")
    return path.as_posix()


def _link_target(member_name: str, link_name: str) -> str:
    """Resolve an internal relative link without allowing archive-root escape."""
    if not link_name or "\\" in link_name:
        raise BundleError(f"unsafe runtime link target: {link_name}")
    link = PurePosixPath(link_name)
    if link.is_absolute():
        raise BundleError(f"unsafe runtime link target: {link_name}")
    parts: list[str] = list(PurePosixPath(member_name).parent.parts)
    for part in link.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if len(parts) <= 1:
                raise BundleError(f"runtime link escapes archive root: {link_name}")
            parts.pop()
        else:
            parts.append(part)
    if not parts or parts[0] != "python":
        raise BundleError(f"runtime link escapes archive root: {link_name}")
    return PurePosixPath(*parts).as_posix()


def _runtime_members(archive: Path) -> tuple[RuntimeMember, ...]:
    """Validate runtime input and materialize safe internal links as files."""
    seen: set[str] = set()
    folded: set[str] = set()
    records: dict[str, tarfile.TarInfo] = {}
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            name = _member_name(member)
            if name == "python":
                continue
            relative = PurePosixPath(*PurePosixPath(name).parts[1:]).as_posix()
            if relative.startswith(EXCLUDED_RUNTIME_PREFIXES):
                continue
            key = relative.casefold()
            if relative in seen or key in folded:
                raise BundleError(f"duplicate/case-colliding runtime member: {relative}")
            seen.add(relative)
            folded.add(key)
            records[name] = member

    def resolve(member: tarfile.TarInfo, trail: frozenset[str]) -> tarfile.TarInfo:
        name = _member_name(member)
        if name in trail:
            raise BundleError(f"cyclic runtime link: {name}")
        if member.isfile():
            return member
        if member.issym():
            target_name = _link_target(name, member.linkname)
            target = records.get(target_name)
            if target is None:
                raise BundleError(f"broken runtime link: {name} -> {member.linkname}")
            return resolve(target, trail | {name})
        if member.isdir():
            raise BundleError(f"runtime link targets a directory: {name}")
        raise BundleError(f"special runtime member is forbidden: {name}")

    files: list[RuntimeMember] = []
    for name, member in records.items():
        if member.isdir():
            continue
        source = resolve(member, frozenset())
        relative = PurePosixPath(*PurePosixPath(name).parts[1:]).as_posix()
        files.append(RuntimeMember(relative, source, source.mode))
    return tuple(files)


def _extract(bundle: tarfile.TarFile, member: tarfile.TarInfo) -> BinaryIO:
    source = bundle.extractfile(member)
    if source is None:
        raise BundleError(f"cannot read runtime member: {member.name}")
    return source


def _zip_info(name: str, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def build_windows_bundle(runtime: Path, source: RuntimeSource, zipapp: Path, output: Path) -> None:
    """Build the Windows x64 ZIP with one exact zipapp payload."""
    members = _runtime_members(runtime)
    names = {member.name for member in members}
    if source.executable not in names:
        raise BundleError(f"locked runtime executable is absent: {source.executable}")
    with zipfile.ZipFile(output, "w", compresslevel=9) as result, tarfile.open(runtime, "r:gz") as bundle:
        result.writestr(_zip_info("waegis.pyz"), zipapp.read_bytes())
        result.writestr(_zip_info("waegis.cmd", 0o755), WINDOWS_LAUNCHER)
        result.writestr(_zip_info("README.txt"), README)
        for member in sorted(members, key=lambda item: item.name.encode("utf-8")):
            with _extract(bundle, member.source) as data:
                result.writestr(_zip_info(f"runtime/{member.name}", member.mode), data.read())


def _tar_bytes(result: tarfile.TarFile, name: str, data: bytes, mode: int) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    result.addfile(info, io.BytesIO(data))


def build_linux_bundle(runtime: Path, source: RuntimeSource, zipapp: Path, output: Path) -> None:
    """Build the Linux x64 tar.gz with one exact zipapp payload."""
    members = _runtime_members(runtime)
    names = {member.name for member in members}
    if source.executable not in names:
        raise BundleError(f"locked runtime executable is absent: {source.executable}")
    with output.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as result, tarfile.open(runtime, "r:gz") as bundle:
            _tar_bytes(result, "waegis.pyz", zipapp.read_bytes(), 0o644)
            _tar_bytes(result, "waegis", LINUX_LAUNCHER, 0o755)
            _tar_bytes(result, "README.txt", README, 0o644)
            for member in sorted(members, key=lambda item: item.name.encode("utf-8")):
                with _extract(bundle, member.source) as data:
                    _tar_bytes(result, f"runtime/{member.name}", data.read(), member.mode)


# END OF FILE
