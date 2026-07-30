#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file build_release.py
@brief Build the payload zipapp and self-contained Windows/Linux archives.
@details Uses the standard library for archive orchestration and invokes uv only
         at release-build time for the locked Complete dependency export and
         wheel installation. Embedded CPython inputs are selected through
         closed-schema filename/digest locks. Every final ZIP, zipapp, tar
         member, and gzip header uses one normalized build epoch; portable
         names, entry order, types, creator system, modes, ownership, and
         compression settings are explicit. Each application archive contains
         an exact internal file manifest; undeclared files and unsupported
         member types are rejected before atomic publication.
@details **Artifact names carry no version** (0.3.0). A build overwrites the
         previous one in a single output directory rather than accumulating a
         new set per release, and documentation, install scripts, and any
         automation can reference a stable path. Nothing is lost by dropping the
         suffix: each artifact self-reports its version (``waegis.pyz version``
         prints the wizard version, bundled payload version, and payload
         digest), and the tracked ``release-manifest.json`` records the version
         alongside the hashes.
@details Artifacts are build outputs and are never tracked in Git. Committing
         them would grow history permanently and irreversibly for no benefit —
         a fixed filename does *not* reduce history size, because Git stores
         blobs rather than names, and the ``.tar.gz`` in particular cannot be
         delta-compressed at all (stream gzip: one early change shifts every
         following byte). The tracked publication record is
         ``07_Delivery/waegis-<version>/`` with ``RELEASE.md``, ``SHA256SUMS``,
         and ``release-manifest.json``. Byte reproduction requires identical
         source/lock/runtime/wheel inputs, build epoch, Python/uv versions, and
         compression implementation; it is not promised across different
         Python or zlib implementations.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 0.9.1
"""

# IMPORTS

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.error
import urllib.request
import zipfile
import zlib
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Iterable, Mapping

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"
PAYLOAD_ROOT = REPOSITORY_ROOT / "05_Software" / "aegis" / "template"
LOCK_FILE = Path(__file__).with_name("runtime-lock.json")
REPOWISE_RUNTIME_LOCK_FILE = Path(__file__).with_name("repowise-runtime-lock.json")
BASE_URL = "https://github.com/astral-sh/python-build-standalone/releases/download"
GENERATED_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tox",
    ".nox",
    "htmlcov",
    "node_modules",
    ".vitest",
}
GENERATED_SUFFIXES = {".pyc", ".pyo"}
GENERATED_PATTERNS = (
    "*.egg-info",
    ".uv-cache*",
    ".uv_cache*",
    ".coverage*",
    "coverage.xml",
)

# @brief Default build output: the one directory delivery binaries live in.
# @details A single, Git-ignored location (the repository's root `.gitignore`
#          ignores every `dist/`). Builds overwrite it instead of leaving a new
#          versioned set behind, which is what previously accumulated hundreds
#          of megabytes of stale archives across three separate directories.
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "07_Delivery" / "dist"

# @brief Release artifact filenames. Deliberately version-free — see the module
#        docstring for why the version lives in the artifact and the manifest
#        rather than in the filename.
ZIPAPP_NAME = "waegis.pyz"
WINDOWS_ARCHIVE_NAME = "waegis-windows-x64.zip"
LINUX_ARCHIVE_NAME = "waegis-linux-x64.tar.gz"
COMPLETE_WINDOWS_ARCHIVE_NAME = "waegis-complete-windows-x64.zip"
COMPLETE_LINUX_ARCHIVE_NAME = "waegis-complete-linux-x64.tar.gz"
REPOWISE_VERSION = "0.37.0"
REPOWISE_TAG = "v0.37.0"
REPOWISE_SOURCE_ARCHIVE = f"repowise-{REPOWISE_VERSION}-source.zip"
SUPPORTED_RUNTIME_TARGETS = frozenset({"windows-x64", "linux-x64"})
RUNTIME_LOCK_KEYS = frozenset(
    {"schema_version", "provider", "release", "python_version", "targets", "reason"}
)
RUNTIME_LOCK_REQUIRED_KEYS = RUNTIME_LOCK_KEYS - {"reason"}
RUNTIME_TARGET_KEYS = frozenset({"asset", "sha256", "size"})
RUNTIME_TARGET_REQUIRED_KEYS = RUNTIME_TARGET_KEYS - {"size"}
RUNTIME_PROVIDER = "astral-sh/python-build-standalone"
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}")
SAFE_ASSET_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,254}")
SAFE_RELEASE_PATTERN = re.compile(r"[0-9]{8}")
SAFE_VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
WINDOWS_DRIVE_PATTERN = re.compile(r"[A-Za-z]:")
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)
ZIP_MIN_EPOCH = 315532800
MAX_BUILD_EPOCH = 4294967294
DETERMINISTIC_FALLBACK_EPOCH = ZIP_MIN_EPOCH
ZIP_COMPRESSION = zipfile.ZIP_DEFLATED
ZIP_COMPRESSION_LEVEL = 9
GZIP_COMPRESSION_LEVEL = 9
ARCHIVE_MANIFEST_NAME = "archive-manifest.json"
MAX_ARCHIVE_MEMBERS = 200_000
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
RUNTIME_EXCLUDED_PREFIXES = ("python/share/terminfo/",)


# DATA MODELS / TYPEDEFINITIONS


class PackagingError(Exception):
    """@brief A release input or output failed validation."""


class RuntimeTarget:
    """@brief One strictly validated embedded-runtime asset."""

    __slots__ = ("asset", "sha256", "size")

    def __init__(self, *, asset: str, sha256: str, size: int | None = None) -> None:
        self.asset = asset
        self.sha256 = sha256
        self.size = size


class RuntimeLock:
    """@brief Closed-schema runtime release and target selection."""

    __slots__ = ("release", "python_version", "targets", "reason")

    def __init__(
        self,
        *,
        release: str,
        python_version: str,
        targets: Mapping[str, RuntimeTarget],
        reason: str | None = None,
    ) -> None:
        self.release = release
        self.python_version = python_version
        self.targets = targets
        self.reason = reason


# HELPER FUNCTIONS


def sha256_file(path: Path) -> str:
    """@brief Calculate the SHA-256 digest of one file without loading it wholly."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_json_loads(content: str | bytes, *, context: str) -> Any:
    """@brief Decode JSON while rejecting duplicate object keys."""

    def object_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        """@brief Construct one JSON object without last-key-wins ambiguity."""
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise PackagingError(f"{context} contains duplicate key {key!r}")
            result[key] = value
        return result

    return json.loads(content, object_pairs_hook=object_hook)


def _canonical_relative_name(value: str) -> str:
    """
    @brief      Validate one portable, extraction-safe relative POSIX path.
    @param[in]  value Candidate archive-relative path.
    @return     The unchanged canonical POSIX path.
    @exception  PackagingError If the path is ambiguous or unsafe on Windows
                or POSIX.
    @version    0.1.0
    """
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise PackagingError(f"unsafe archive path: {value!r}")
    if (
        value.startswith(("/", "\\"))
        or "\\" in value
        or "\0" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or WINDOWS_DRIVE_PATTERN.match(value)
    ):
        raise PackagingError(f"unsafe archive path: {value!r}")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise PackagingError(f"unsafe archive path: {value!r}")
    for part in relative.parts:
        stem = part.split(".", 1)[0].upper()
        if (
            ":" in part
            or part.endswith((" ", "."))
            or stem in WINDOWS_RESERVED_NAMES
        ):
            raise PackagingError(f"unsafe archive path: {value!r}")
    canonical = relative.as_posix()
    if canonical != value:
        raise PackagingError(f"non-canonical archive path: {value!r}")
    return canonical


def _reject_name_collisions(names: Iterable[str], *, context: str) -> tuple[str, ...]:
    """@brief Reject duplicate and Windows-case-colliding portable names."""
    ordered = tuple(names)
    if len(ordered) > MAX_ARCHIVE_MEMBERS:
        raise PackagingError(f"{context} has too many members")
    exact: set[str] = set()
    folded: dict[str, str] = {}
    for name in ordered:
        canonical = _canonical_relative_name(name.rstrip("/"))
        normalized = canonical
        if normalized in exact:
            raise PackagingError(f"duplicate {context} member: {name!r}")
        collision = folded.get(normalized.casefold())
        if collision is not None and collision != normalized:
            raise PackagingError(
                f"case-colliding {context} members: {collision!r} and {normalized!r}"
            )
        exact.add(normalized)
        folded[normalized.casefold()] = normalized
    return ordered


def _git_source_epoch(repository: Path = REPOSITORY_ROOT) -> str | None:
    """@brief Read the source commit timestamp without consulting wall-clock time."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "log", "-1", "--format=%ct", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def _normalize_build_epoch(raw: str, *, source: str) -> int:
    """
    @brief      Validate, clamp, and ZIP-precision-normalize a build epoch.
    @param[in]  raw Integer epoch text.
    @param[in]  source Diagnostic name for the epoch source.
    @return     An even epoch within ZIP and gzip representable bounds.
    @exception  PackagingError If the value is malformed, negative, or too
                large for all reproducible archive formats.
    @version    0.1.0
    """
    if not isinstance(raw, str) or not re.fullmatch(r"[0-9]+", raw):
        raise PackagingError(f"{source} must be a non-negative integer")
    try:
        epoch = int(raw, 10)
    except ValueError as exc:
        raise PackagingError(f"{source} must be a non-negative integer") from exc
    if epoch > MAX_BUILD_EPOCH:
        raise PackagingError(
            f"{source} exceeds the supported gzip timestamp range ({MAX_BUILD_EPOCH})"
        )
    return max(epoch, ZIP_MIN_EPOCH) // 2 * 2


def _canonical_build_epoch() -> int:
    """
    @brief      Select one deterministic epoch for every generated artifact.
    @return     Normalized SOURCE_DATE_EPOCH, Git commit time, or fixed fallback.
    @exception  PackagingError If explicit SOURCE_DATE_EPOCH is malformed.
    @version    0.1.0
    """
    explicit = os.environ.get("SOURCE_DATE_EPOCH")
    if explicit is not None:
        return _normalize_build_epoch(explicit, source="SOURCE_DATE_EPOCH")
    committed = _git_source_epoch()
    if committed is not None:
        try:
            return _normalize_build_epoch(committed, source="Git commit timestamp")
        except PackagingError:
            pass
    return DETERMINISTIC_FALLBACK_EPOCH


def _wizard_version() -> str:
    """@brief Read the canonical WAEGIS version without mutating import state."""
    path = SOURCE_ROOT / "waegis" / "version.py"
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PackagingError(f"cannot read WAEGIS version declaration: {path}") from exc
    match = re.search(
        r'^WIZARD_VERSION\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"\s*$',
        content,
        flags=re.MULTILINE,
    )
    if match is None:
        raise PackagingError(f"invalid WAEGIS version declaration: {path}")
    return match.group(1)


def _zip_datetime(epoch: int) -> tuple[int, int, int, int, int, int]:
    """@brief Convert a normalized epoch to the ZIP UTC date tuple."""
    value = dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)
    return (value.year, value.month, value.day, value.hour, value.minute, value.second)


def _unique_temporary_path(destination: Path) -> tuple[int, Path]:
    """@brief Exclusively create a unique sibling temporary publication path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
    except OSError as exc:
        raise PackagingError(f"cannot create temporary output for {destination.name}: {exc}") from exc
    return descriptor, Path(name)


def _flush_file(handle: BinaryIO) -> None:
    """@brief Flush file content through the operating-system durability boundary."""
    handle.flush()
    os.fsync(handle.fileno())


def _atomic_write_bytes(destination: Path, content: bytes) -> None:
    """@brief Atomically publish deterministic generated metadata bytes."""
    descriptor, temporary = _unique_temporary_path(destination)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            _flush_file(handle)
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _tree_entries(
    root: Path,
    *,
    archive_root: str,
    executable_paths: frozenset[str],
) -> list[tuple[str, Path, bool]]:
    """@brief Return regular files sorted by their canonical POSIX archive name."""
    archive_root = _canonical_relative_name(archive_root)
    entries: list[tuple[str, Path, bool]] = []
    source_names: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        canonical = _canonical_relative_name(relative)
        source_names.append(canonical)
        if path.is_symlink():
            raise PackagingError(f"release staging contains a symlink: {relative!r}")
        if path.is_file():
            entries.append(
                (
                    f"{archive_root}/{canonical}",
                    path,
                    canonical in executable_paths or canonical.endswith(".sh"),
                )
            )
        elif not path.is_dir():
            raise PackagingError(f"release staging has unsupported entry: {relative!r}")
    _reject_name_collisions(source_names, context="staging")
    entries.sort(key=lambda entry: entry[0])
    return entries


def _write_deterministic_zip(
    destination: Path,
    entries: Iterable[tuple[str, Path | bytes, bool]],
    *,
    epoch: int,
    verify: Callable[[Path], None] | None = None,
) -> None:
    """
    @brief      Write one metadata-normalized deterministic ZIP.
    @details    ZIP directory entries are deliberately omitted. Every member is
                an explicit regular file with fixed UTC timestamp, POSIX mode,
                creator system, compression method, and compression level.
    @version    0.1.0
    """
    ordered = sorted(entries, key=lambda entry: entry[0])
    _reject_name_collisions((entry[0] for entry in ordered), context="ZIP")
    descriptor, temporary = _unique_temporary_path(destination)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=ZIP_COMPRESSION,
            compresslevel=ZIP_COMPRESSION_LEVEL,
            strict_timestamps=True,
        ) as bundle:
            for name, source, executable in ordered:
                info = zipfile.ZipInfo(name, date_time=_zip_datetime(epoch))
                info.create_system = 3
                info.compress_type = ZIP_COMPRESSION
                info.external_attr = (
                    stat.S_IFREG | (0o755 if executable else 0o644)
                ) << 16
                info.internal_attr = 0
                content = source if isinstance(source, bytes) else source.read_bytes()
                bundle.writestr(
                    info,
                    content,
                    compress_type=ZIP_COMPRESSION,
                    compresslevel=ZIP_COMPRESSION_LEVEL,
                )
        with open(temporary, "r+b") as handle:
            os.fsync(handle.fileno())
        if verify is not None:
            verify(temporary)
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _write_deterministic_tar_gz(
    destination: Path,
    root: Path,
    *,
    archive_root: str,
    executable_paths: frozenset[str],
    epoch: int,
    verify: Callable[[Path], None] | None = None,
) -> None:
    """
    @brief      Write a GNU tar stream and gzip wrapper with normalized metadata.
    @details    Root and source directories are explicit sorted entries; files
                are regular entries. Links and special filesystem objects are
                rejected before publication.
    @version    0.1.0
    """
    archive_root = _canonical_relative_name(archive_root)
    paths: list[tuple[str, Path | None]] = [(archive_root, None)]
    source_names: list[str] = []
    for path in root.rglob("*"):
        relative = _canonical_relative_name(path.relative_to(root).as_posix())
        source_names.append(relative)
        if path.is_symlink():
            raise PackagingError(f"release staging contains a symlink: {relative!r}")
        if not path.is_file() and not path.is_dir():
            raise PackagingError(f"release staging has unsupported entry: {relative!r}")
        paths.append((f"{archive_root}/{relative}", path))
    _reject_name_collisions(source_names, context="staging")
    paths.sort(key=lambda item: item[0])
    descriptor, temporary = _unique_temporary_path(destination)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=GZIP_COMPRESSION_LEVEL,
                fileobj=raw,
                mtime=epoch,
            ) as compressed:
                with tarfile.open(
                    mode="w",
                    fileobj=compressed,
                    format=tarfile.GNU_FORMAT,
                ) as bundle:
                    for name, path in paths:
                        info = tarfile.TarInfo(name)
                        info.mtime = epoch
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        if path is None or path.is_dir():
                            info.type = tarfile.DIRTYPE
                            info.mode = 0o755
                            bundle.addfile(info)
                            continue
                        relative = path.relative_to(root).as_posix()
                        info.type = tarfile.REGTYPE
                        info.mode = (
                            0o755
                            if relative in executable_paths or relative.endswith(".sh")
                            else 0o644
                        )
                        info.size = path.stat().st_size
                        with open(path, "rb") as source:
                            bundle.addfile(info, source)
            _flush_file(raw)
        if verify is not None:
            verify(temporary)
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _copy_tree(source: Path, destination: Path) -> None:
    """
    @brief      Copy a source tree while rejecting links and generated state.
    @param[in]  source Existing source directory.
    @param[in]  destination Destination directory created or extended.
    @return     None.
    @details    Uses the same interpreter, test, dependency, and coverage-state
                exclusions as the deployment copier.
    @exception  PackagingError If the source is missing or contains a link or
                unsupported filesystem entry.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.4.0
    """
    if not source.is_dir():
        raise PackagingError(f"release input directory does not exist: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(
        source.rglob("*"),
        key=lambda item: item.relative_to(source).as_posix(),
    ):
        relative = path.relative_to(source)
        if (
            any(part in GENERATED_NAMES for part in relative.parts)
            or relative.suffix in GENERATED_SUFFIXES
            or any(
                fnmatchcase(part, pattern)
                for part in relative.parts
                for pattern in GENERATED_PATTERNS
            )
        ):
            continue
        if path.is_symlink():
            raise PackagingError(f"release input contains a symlink: {path}")
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        else:
            raise PackagingError(f"release input is not a regular file: {path}")


def _load_lock(path: Path = LOCK_FILE) -> RuntimeLock:
    """
    @brief      Parse one closed-schema embedded-runtime lock.
    @param[in]  path Core or RepoWise sidecar runtime lock.
    @return     Strictly validated runtime-lock model.
    @exception  PackagingError If the file, JSON, schema, release, targets,
                assets, digests, or optional sizes are invalid.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-30
    @version    0.3.0
    """
    try:
        if not path.is_file() or path.is_symlink():
            raise PackagingError(f"runtime lock is not a regular file: {path}")
        data = _strict_json_loads(
            path.read_text(encoding="utf-8"),
            context=f"runtime lock {path}",
        )
    except PackagingError:
        raise
    except UnicodeDecodeError as exc:
        raise PackagingError(f"runtime lock is not valid UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PackagingError(
            f"runtime lock contains invalid JSON at line {exc.lineno}: {path}"
        ) from exc
    except OSError as exc:
        raise PackagingError(f"cannot read runtime lock {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackagingError(f"runtime lock root must be an object: {path}")
    keys = frozenset(data)
    missing = sorted(RUNTIME_LOCK_REQUIRED_KEYS - keys)
    unknown = sorted(keys - RUNTIME_LOCK_KEYS)
    if missing or unknown:
        raise PackagingError(
            f"runtime lock keys are invalid ({'missing=' + repr(missing) if missing else ''}"
            f"{'; ' if missing and unknown else ''}"
            f"{'unknown=' + repr(unknown) if unknown else ''}): {path}"
        )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise PackagingError(f"runtime lock schema_version must be exactly 1: {path}")
    if data["provider"] != RUNTIME_PROVIDER:
        raise PackagingError(f"runtime lock provider is unsupported: {path}")
    release = data["release"]
    if not isinstance(release, str) or SAFE_RELEASE_PATTERN.fullmatch(release) is None:
        raise PackagingError(f"runtime lock release must be an eight-digit identifier: {path}")
    python_version = data["python_version"]
    if (
        not isinstance(python_version, str)
        or SAFE_VERSION_PATTERN.fullmatch(python_version) is None
    ):
        raise PackagingError(f"runtime lock python_version is invalid: {path}")
    reason = data.get("reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise PackagingError(f"runtime lock reason must be a non-empty string: {path}")
    targets = data["targets"]
    if not isinstance(targets, dict):
        raise PackagingError(f"runtime lock targets must be an object: {path}")
    target_names = frozenset(targets)
    if target_names != SUPPORTED_RUNTIME_TARGETS:
        raise PackagingError(
            "runtime lock targets must be exactly "
            f"{sorted(SUPPORTED_RUNTIME_TARGETS)}, found {sorted(str(item) for item in target_names)}"
        )
    validated: dict[str, RuntimeTarget] = {}
    assets: dict[str, str] = {}
    for target in sorted(SUPPORTED_RUNTIME_TARGETS):
        entry = targets[target]
        if not isinstance(entry, dict):
            raise PackagingError(f"runtime lock target {target!r} must be an object")
        entry_keys = frozenset(entry)
        entry_missing = sorted(RUNTIME_TARGET_REQUIRED_KEYS - entry_keys)
        entry_unknown = sorted(entry_keys - RUNTIME_TARGET_KEYS)
        if entry_missing or entry_unknown:
            raise PackagingError(
                f"runtime lock target {target!r} keys are invalid "
                f"(missing={entry_missing}, unknown={entry_unknown})"
            )
        asset = entry["asset"]
        if (
            not isinstance(asset, str)
            or SAFE_ASSET_PATTERN.fullmatch(asset) is None
            or Path(asset).name != asset
            or PurePosixPath(asset).name != asset
        ):
            raise PackagingError(
                f"runtime lock target {target!r} asset must be a safe basename"
            )
        prior = assets.get(asset.casefold())
        if prior is not None:
            raise PackagingError(
                f"runtime lock assets must be unique: {prior!r} and {asset!r}"
            )
        assets[asset.casefold()] = asset
        digest = entry["sha256"]
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise PackagingError(
                f"runtime lock target {target!r} sha256 must be 64 hexadecimal characters"
            )
        size = entry.get("size")
        if size is not None and (type(size) is not int or size <= 0):
            raise PackagingError(
                f"runtime lock target {target!r} size must be a positive integer"
            )
        validated[target] = RuntimeTarget(asset=asset, sha256=digest.lower(), size=size)
    return RuntimeLock(
        release=release,
        python_version=python_version,
        targets=validated,
        reason=reason,
    )


def _download_runtime(
    target: str,
    cache: Path,
    *,
    offline: bool,
    lock_file: Path = LOCK_FILE,
) -> Path:
    """
    @brief      Acquire one pinned runtime and verify its SHA-256 before use.
    @param[in]  target Runtime target key.
    @param[in]  cache Local pinned-asset cache.
    @param[in]  offline Refuse cache misses when true.
    @param[in]  lock_file Runtime lock selecting the Python line and assets.
    @return     Verified runtime archive.
    @exception  PackagingError If the target is unpinned, unavailable, or has
                the wrong digest.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-30
    @version    0.3.0
    """
    lock = _load_lock(lock_file)
    try:
        entry = lock.targets[target]
    except (KeyError, TypeError) as exc:
        raise PackagingError(f"runtime target is not pinned: {target}") from exc
    asset = entry.asset
    expected = entry.sha256
    archive = cache / asset
    try:
        if archive.is_file() and not archive.is_symlink():
            if (
                (entry.size is None or archive.stat().st_size == entry.size)
                and sha256_file(archive) == expected
            ):
                return archive
    except OSError as exc:
        raise PackagingError(f"cannot validate cached runtime {archive}: {exc}") from exc
    if offline:
        raise PackagingError(f"offline runtime cache miss for {asset}")
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PackagingError(f"cannot create runtime cache {cache}: {exc}") from exc
    descriptor, temporary = _unique_temporary_path(archive)
    url = f"{BASE_URL}/{lock.release}/{asset}"
    try:
        with os.fdopen(descriptor, "wb") as output:
            with urllib.request.urlopen(url, timeout=120) as response:
                shutil.copyfileobj(response, output, length=1024 * 1024)
            _flush_file(output)
        if entry.size is not None and temporary.stat().st_size != entry.size:
            raise PackagingError(f"size mismatch for downloaded runtime: {asset}")
        if sha256_file(temporary) != expected:
            raise PackagingError(f"SHA-256 mismatch for downloaded runtime: {asset}")
        os.replace(temporary, archive)
    except BaseException as exc:
        temporary.unlink(missing_ok=True)
        if isinstance(exc, (KeyboardInterrupt, SystemExit, PackagingError)):
            raise
        raise PackagingError(f"cannot download pinned runtime {url}: {exc}") from exc
    return archive


def _safe_member_path(root: Path, name: str) -> Path:
    """@brief Convert one tar member name to a confined extraction path."""
    relative = PurePosixPath(_canonical_relative_name(name.rstrip("/")))
    target = root.joinpath(*relative.parts)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PackagingError(f"runtime archive path escapes staging: {name!r}") from exc
    return target


def _copy_materialized_file(source: Path, target: Path) -> str:
    """@brief Copy link-target bytes without relying on platform link support."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(source, "rb") as input_file, open(target, "wb") as output_file:
        shutil.copyfileobj(input_file, output_file)
    target.chmod(source.stat().st_mode & 0o777)
    return str(target)


def _extract_runtime(archive_path: Path, destination: Path) -> frozenset[str]:
    """
    @brief      Safely extract runtime files and materialize confined links.
    @param[in]  archive_path Pinned runtime tar archive.
    @param[in]  destination Runtime staging directory.
    @return     Runtime-relative POSIX paths that require execute permission.
    @exception  PackagingError If an archive entry or link is unsafe or
                unsupported.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.3.0
    """
    try:
        if destination.is_symlink() or (
            destination.exists() and not destination.is_dir()
        ):
            raise PackagingError(
                f"runtime destination is not a safe directory: {destination}"
            )
        destination.mkdir(parents=True, exist_ok=True)
    except PackagingError:
        raise
    except OSError as exc:
        raise PackagingError(
            f"cannot create runtime destination {destination}: {exc}"
        ) from exc
    executable_files: set[str] = set()
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            raw_members = [
                member
                for member in archive.getmembers()
                if not any(
                    member.name.rstrip("/").startswith(prefix.rstrip("/"))
                    for prefix in RUNTIME_EXCLUDED_PREFIXES
                )
            ]
            if len(raw_members) > MAX_ARCHIVE_MEMBERS:
                raise PackagingError("runtime archive has too many members")
            names = [member.name.rstrip("/") for member in raw_members]
            _reject_name_collisions(names, context="runtime archive")
            members: dict[str, tarfile.TarInfo] = {}
            link_targets: dict[str, str] = {}
            for member, name in zip(raw_members, names, strict=True):
                _safe_member_path(destination, name)
                if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
                    raise PackagingError(f"unsupported runtime archive entry: {name!r}")
                members[name] = member
            link_names = {
                name for name, member in members.items() if member.issym() or member.islnk()
            }
            for name in members:
                parent = PurePosixPath(name).parent
                while parent != PurePosixPath("."):
                    if parent.as_posix() in link_names:
                        raise PackagingError(
                            f"runtime member traverses link parent: {name!r}"
                        )
                    parent = parent.parent
            for name in sorted(link_names):
                member = members[name]
                raw_target = member.linkname
                if (
                    not isinstance(raw_target, str)
                    or not raw_target
                    or raw_target.startswith(("/", "\\"))
                    or "\\" in raw_target
                    or WINDOWS_DRIVE_PATTERN.match(raw_target)
                ):
                    raise PackagingError(
                        f"absolute or unsafe runtime link target: {raw_target!r}"
                    )
                base_parts = (
                    []
                    if member.islnk()
                    else list(PurePosixPath(name).parent.parts)
                )
                for part in PurePosixPath(raw_target).parts:
                    if part in {"", "."}:
                        continue
                    if part == "..":
                        if not base_parts:
                            raise PackagingError(
                                f"escaping runtime link target: {raw_target!r}"
                            )
                        base_parts.pop()
                    else:
                        base_parts.append(part)
                target_name = _canonical_relative_name(
                    PurePosixPath(*base_parts).as_posix()
                )
                if target_name not in members:
                    raise PackagingError(
                        f"unresolved runtime link: {name!r} -> {raw_target!r}"
                    )
                link_targets[name] = target_name

            resolved: dict[str, str] = {}

            def resolve(name: str, stack: tuple[str, ...] = ()) -> str:
                """@brief Resolve one validated runtime link graph node."""
                if name in resolved:
                    return resolved[name]
                if name in stack:
                    cycle = " -> ".join((*stack, name))
                    raise PackagingError(f"runtime link cycle: {cycle}")
                target_name = link_targets.get(name)
                result = (
                    name
                    if target_name is None
                    else resolve(target_name, (*stack, name))
                )
                resolved[name] = result
                return result

            for name in sorted(link_targets):
                resolve(name)

            for name in sorted(members):
                member = members[name]
                target = _safe_member_path(destination, name)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    source = archive.extractfile(member)
                    if source is None:
                        raise PackagingError(f"cannot read runtime archive entry: {name!r}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source, open(target, "wb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                    target.chmod(member.mode & 0o777)
                    if member.mode & 0o111:
                        executable_files.add(name)

            def materialize(source_name: str, target_name: str) -> None:
                """@brief Materialize one resolved file or directory graph node."""
                ultimate_name = resolve(source_name)
                ultimate = members[ultimate_name]
                target = _safe_member_path(destination, target_name)
                if ultimate.isfile():
                    source = _safe_member_path(destination, ultimate_name)
                    _copy_materialized_file(source, target)
                    if ultimate.mode & 0o111 or members[source_name].mode & 0o111:
                        executable_files.add(target_name)
                    return
                if not ultimate.isdir():
                    raise PackagingError(
                        f"runtime link has unsupported resolved type: {source_name!r}"
                    )
                target.mkdir(parents=True, exist_ok=True)
                prefix = f"{ultimate_name}/"
                for candidate in sorted(members):
                    if not candidate.startswith(prefix):
                        continue
                    relative = PurePosixPath(candidate).relative_to(
                        PurePosixPath(ultimate_name)
                    )
                    ancestors = tuple(relative.parents)
                    if any(
                        (
                            PurePosixPath(ultimate_name) / ancestor
                        ).as_posix() in link_names
                        for ancestor in ancestors
                        if ancestor != PurePosixPath(".")
                    ):
                        continue
                    materialize(
                        candidate,
                        (PurePosixPath(target_name) / relative).as_posix(),
                    )

            for name in sorted(link_targets):
                materialize(name, name)
    except PackagingError:
        raise
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise PackagingError(f"invalid runtime archive {archive_path.name}: {exc}") from exc
    return frozenset(executable_files)


def _linux_tar_filter(
    member: tarfile.TarInfo,
    *,
    root_name: str,
    executable_paths: frozenset[str],
    epoch: int = DETERMINISTIC_FALLBACK_EPOCH,
) -> tarfile.TarInfo:
    """
    @brief      Normalize Linux archive metadata independently of the build host.
    @param[in]  member Tar entry produced from the staged application tree.
    @param[in]  root_name Top-level application directory in the tar archive.
    @param[in]  executable_paths Root-relative files requiring execute bits.
    @return     The same tar entry with a deterministic POSIX mode.
    @exception  None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.3.0
    """
    prefix = f"{root_name}/"
    relative = member.name[len(prefix) :] if member.name.startswith(prefix) else ""
    if member.isdir():
        member.mode = 0o755
    elif member.isfile():
        member.mode = 0o755 if relative in executable_paths or relative.endswith(".sh") else 0o644
    member.mtime = epoch
    member.uid = 0
    member.gid = 0
    member.uname = ""
    member.gname = ""
    member.pax_headers = {}
    return member


def _find_interpreter(runtime_root: Path, target: str) -> Path:
    """@brief Locate the embedded interpreter inside an extracted runtime.
    @version 0.2.0
    """
    names = ("python.exe",) if target == "windows-x64" else ("python3", "python")
    candidates = [path for name in names for path in runtime_root.rglob(name) if path.is_file()]
    if not candidates:
        raise PackagingError(f"embedded interpreter not found for {target}")
    candidates.sort(
        key=lambda path: (
            "bin" not in path.parts,
            len(path.parts),
            path.relative_to(runtime_root).as_posix(),
        )
    )
    return candidates[0]


def _run_build_command(
    arguments: list[str],
    *,
    cwd: Path,
    description: str,
    environment: dict[str, str] | None = None,
) -> str:
    """@brief Run one release-build command and surface its complete failure."""
    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PackagingError(f"{description} could not run: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise PackagingError(f"{description} failed: {detail}")
    return completed.stdout.strip()


def _git_repowise(source: Path, *arguments: str) -> str:
    """@brief Run a read-only Git command against the candidate RepoWise source."""
    return _run_build_command(
        [
            "git",
            "-c",
            f"safe.directory={source.as_posix()}",
            "-C",
            str(source),
            *arguments,
        ],
        cwd=source,
        description="RepoWise source validation",
    )


def _validate_repowise_source(source: Path) -> dict[str, Any]:
    """@brief Refuse any source that is not a clean exact RepoWise v0.37.0 tree."""
    source = source.resolve()
    if not source.is_dir():
        raise PackagingError(f"RepoWise source directory does not exist: {source}")
    try:
        with (source / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        raise PackagingError(f"invalid RepoWise pyproject.toml: {exc}") from exc
    if (
        project.get("name") != "repowise"
        or project.get("version") != REPOWISE_VERSION
    ):
        raise PackagingError("RepoWise source must identify as project repowise version 0.37.0")
    status = _git_repowise(source, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        detail = status.replace("\n", "; ")
        raise PackagingError(f"RepoWise source must be clean; Git reports: {detail}")
    tag = _git_repowise(source, "describe", "--tags", "--exact-match")
    if tag not in {REPOWISE_TAG, REPOWISE_VERSION}:
        raise PackagingError(f"RepoWise source must be at tag {REPOWISE_TAG}, found {tag!r}")
    commit = _git_repowise(source, "rev-parse", "HEAD")
    tracked = [
        item
        for item in _git_repowise(source, "ls-files", "-z").split("\0")
        if item
    ]
    if not tracked or "LICENSE" not in tracked or "uv.lock" not in tracked:
        raise PackagingError("RepoWise source lacks its tracked LICENSE or uv.lock")
    return {"root": source, "tag": tag, "commit": commit, "tracked": tracked}


def _write_repowise_source_archive(
    source_info: Mapping[str, Any],
    output: Path,
    *,
    epoch: int | None = None,
) -> None:
    """
    @brief      Write byte-identical RepoWise source from the pinned Git commit.
    @details    Reading the worktree would make Windows and Linux source ZIPs
                differ when Git line-ending filters are active. ``git archive``
                reads repository blobs and preserves tracked executable modes.
    @param[in]  source_info Validated source root, tag, commit, and tracked set.
    @param[in]  output Destination source ZIP.
    @return     None.
    @exception  PackagingError If Git cannot archive the validated commit.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-30
    @version    0.3.0
    """
    source = Path(source_info["root"])
    descriptor, raw_archive = _unique_temporary_path(output.with_suffix(".tar"))
    os.close(descriptor)
    try:
        _git_repowise(
            source,
            "archive",
            "--format=tar",
            f"--output={raw_archive}",
            str(source_info["commit"]),
        )
        entries: list[tuple[str, bytes, bool]] = []
        try:
            with tarfile.open(raw_archive, "r:") as bundle:
                members = bundle.getmembers()
                _reject_name_collisions(
                    (member.name.rstrip("/") for member in members),
                    context="RepoWise source",
                )
                for member in members:
                    if member.isdir():
                        continue
                    if not member.isfile():
                        raise PackagingError(
                            f"RepoWise source contains unsupported entry: {member.name!r}"
                        )
                    source_file = bundle.extractfile(member)
                    if source_file is None:
                        raise PackagingError(
                            f"cannot read RepoWise source entry: {member.name!r}"
                        )
                    with source_file:
                        content = source_file.read()
                    entries.append(
                        (
                            f"repowise-{REPOWISE_VERSION}/"
                            f"{_canonical_relative_name(member.name)}",
                            content,
                            bool(member.mode & 0o111),
                        )
                    )
        except PackagingError:
            raise
        except (OSError, tarfile.TarError, EOFError) as exc:
            raise PackagingError(f"cannot inspect RepoWise Git archive: {exc}") from exc
        _write_deterministic_zip(
            output,
            entries,
            epoch=_canonical_build_epoch() if epoch is None else epoch,
        )
    finally:
        raw_archive.unlink(missing_ok=True)
    if not output.is_file() or output.stat().st_size <= 0:
        raise PackagingError("RepoWise source archive was not created")


def _copy_repowise_python(source: Path, site_packages: Path) -> None:
    """@brief Merge the three RepoWise namespace source roots into site-packages."""
    for package in ("core", "cli", "server"):
        root = source / "packages" / package / "src"
        if not root.is_dir():
            raise PackagingError(f"RepoWise package source is missing: {root}")
        _copy_tree(root, site_packages)
    metadata = site_packages / f"repowise-{REPOWISE_VERSION}.dist-info"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.4\n"
        "Name: repowise\n"
        f"Version: {REPOWISE_VERSION}\n"
        "License-Expression: AGPL-3.0-or-later\n",
        encoding="utf-8",
        newline="",
    )
    (metadata / "WHEEL").write_text(
        "Wheel-Version: 1.0\n"
        "Generator: WAEGIS Complete\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n",
        encoding="utf-8",
        newline="",
    )


def _offline_sitecustomize() -> str:
    """@brief Render the managed-runtime non-loopback socket denial guard."""
    return (
        '"""WAEGIS managed RepoWise offline network guard."""\n'
        "import ipaddress\n"
        "import os\n"
        "import socket\n"
        "_original_connect = socket.socket.connect\n"
        "def _offline_connect(instance, address):\n"
        "    if os.environ.get('WAEGIS_REPOWISE_OFFLINE') == '1':\n"
        "        host = address[0] if isinstance(address, tuple) else str(address)\n"
        "        try:\n"
        "            allowed = ipaddress.ip_address(host).is_loopback\n"
        "        except ValueError:\n"
        "            allowed = host == 'localhost'\n"
        "        if not allowed:\n"
        "            raise OSError('WAEGIS RepoWise runtime denied non-loopback network access')\n"
        "    return _original_connect(instance, address)\n"
        "socket.socket.connect = _offline_connect\n"
    )


def _repowise_launcher(target: str, relative_python: str) -> tuple[str, str]:
    """@brief Return the sidecar launcher name and platform-specific text."""
    if target == "windows-x64":
        python = relative_python.replace("/", "\\")
        return (
            "repowise.cmd",
            "@echo off\r\n"
            "setlocal\r\n"
            "set \"WAEGIS_REPOWISE_OFFLINE=1\"\r\n"
            "set \"DO_NOT_TRACK=1\"\r\n"
            "set \"REPOWISE_SKIP_EDITOR_SETUP=1\"\r\n"
            "set \"PYTHONPATH=%~dp0site-packages\"\r\n"
            f"\"%~dp0{python}\" -m waegis_repowise_bootstrap %*\r\n"
            "exit /b %ERRORLEVEL%\r\n",
        )
    return (
        "repowise",
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        'ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        "export WAEGIS_REPOWISE_OFFLINE=1\n"
        "export DO_NOT_TRACK=1\n"
        "export REPOWISE_SKIP_EDITOR_SETUP=1\n"
        'export PYTHONPATH="$ROOT/site-packages"\n'
        f'exec "$ROOT/{relative_python}" -m waegis_repowise_bootstrap "$@"\n',
    )


def _repowise_file_table(root: Path) -> list[dict[str, Any]]:
    """@brief Build the sidecar manifest's sorted file hash table.
    @version 0.2.0
    """
    paths = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.name != "repowise-bundle-manifest.json"
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in paths
    ]


def _repowise_tree_digest(files: list[dict[str, Any]]) -> tuple[str, int]:
    """@brief Compute the digest algorithm consumed by WAEGIS installation."""
    digest = hashlib.sha256()
    total = 0
    for item in files:
        total += int(item["size"])
        digest.update(str(item["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(item["size"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(item["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), total


def _repowise_packaged_size(root: Path, files: list[dict[str, Any]]) -> int:
    """@brief Estimate compressed sidecar bytes without archive-header overhead.
    @version 1.0.0
    """
    compressed = sum(
        len(zlib.compress((root / str(item["path"])).read_bytes(), level=9))
        for item in files
    )
    unpacked = sum(int(item["size"]) for item in files)
    return max(1, min(compressed, unpacked))


def _third_party_notices(site_packages: Path) -> str:
    """@brief Derive a compact installed-distribution license notice.
    @version 0.2.0
    """
    records = []
    for metadata in sorted(
        site_packages.glob("*.dist-info/METADATA"),
        key=lambda path: path.relative_to(site_packages).as_posix(),
    ):
        name = ""
        version = ""
        license_value = "not declared"
        for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Name: "):
                name = line[6:]
            elif line.startswith("Version: "):
                version = line[9:]
            elif (
                line.startswith(("License-Expression: ", "License: "))
                and license_value == "not declared"
            ):
                license_value = line.split(":", 1)[1].strip() or license_value
        if name:
            records.append(f"{name} {version}: {license_value}")
    return (
        "Third-party distributions included in the RepoWise runtime\n"
        "Generated from installed package metadata; consult the corresponding "
        "source archive and package licenses.\n\n"
        + "\n".join(records)
        + "\n"
    )


def _normalize_sbom(path: Path, *, epoch: int) -> None:
    """@brief Replace uv's volatile SBOM identity and timestamp deterministically."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackagingError(f"cannot normalize generated SBOM {path}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("metadata"), dict):
        raise PackagingError(f"generated SBOM has an invalid document shape: {path}")
    document.pop("serialNumber", None)
    timestamp = dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)
    document["metadata"]["timestamp"] = timestamp.isoformat().replace("+00:00", "Z")
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )


def _normalize_requirements_export(path: Path) -> None:
    """@brief Remove uv's temporary output path from its generated header."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise PackagingError(f"cannot normalize locked requirements {path}: {exc}") from exc
    if (
        len(lines) < 2
        or lines[0] != "# This file was autogenerated by uv via the following command:"
        or not lines[1].startswith("#    uv export ")
    ):
        raise PackagingError(f"generated locked requirements has an unexpected header: {path}")
    path.write_text(
        "# Locked requirements exported by WAEGIS Complete using uv.\n"
        + "\n".join(lines[2:])
        + "\n",
        encoding="utf-8",
        newline="",
    )


def _build_repowise_bundle(
    target: str,
    *,
    source_info: Mapping[str, Any],
    destination: Path,
    runtime_cache: Path,
    offline: bool,
    epoch: int,
) -> frozenset[str]:
    """@brief Assemble one locked, native-wheel-only RepoWise Complete sidecar.
    @version 0.2.0
    """
    current = (
        "windows-x64"
        if os.name == "nt"
        else "linux-x64"
        if sys.platform.startswith("linux")
        else ""
    )
    if target != current:
        raise PackagingError(
            "RepoWise Complete must be built natively; "
            f"host is {current or sys.platform}, target is {target}"
        )
    source = Path(source_info["root"])
    runtime_lock = _load_lock(REPOWISE_RUNTIME_LOCK_FILE)
    runtime_archive = _download_runtime(
        target,
        runtime_cache,
        offline=offline,
        lock_file=REPOWISE_RUNTIME_LOCK_FILE,
    )
    runtime = destination / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    executable_runtime = _extract_runtime(runtime_archive, runtime)
    interpreter = _find_interpreter(runtime, target)
    relative_python = interpreter.relative_to(destination).as_posix()
    site_packages = destination / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    requirements = destination / "locked-requirements.txt"
    sbom = destination / "sbom.cdx.json"
    environment = dict(os.environ)
    environment["UV_NO_PROGRESS"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["SOURCE_DATE_EPOCH"] = str(epoch)
    export_base = ["uv", "export", "--locked", "--no-dev", "--project", str(source)]
    if offline:
        export_base.append("--offline")
    _run_build_command(
        [
            *export_base,
            "--no-emit-workspace",
            "--format",
            "requirements.txt",
            "--output-file",
            str(requirements),
        ],
        cwd=source,
        description="RepoWise locked dependency export",
        environment=environment,
    )
    _normalize_requirements_export(requirements)
    _run_build_command(
        [*export_base, "--format", "cyclonedx1.5", "--output-file", str(sbom)],
        cwd=source,
        description="RepoWise SBOM export",
        environment=environment,
    )
    _normalize_sbom(sbom, epoch=epoch)
    platform_name = (
        "x86_64-pc-windows-msvc"
        if target == "windows-x64"
        else "x86_64-unknown-linux-gnu"
    )
    python_version = ".".join(runtime_lock.python_version.split(".")[:2])
    install = [
        "uv",
        "pip",
        "install",
        "--target",
        str(site_packages),
        "--python-version",
        python_version,
        "--python-platform",
        platform_name,
        "--only-binary",
        ":all:",
        "--require-hashes",
        "--requirements",
        str(requirements),
        "--link-mode",
        "copy",
    ]
    if offline:
        install.append("--offline")
    _run_build_command(
        install,
        cwd=source,
        description=f"RepoWise {target} locked wheel installation",
        environment=environment,
    )
    _copy_repowise_python(source, site_packages)
    (site_packages / "waegis_repowise_bootstrap.py").write_text(
        '"""Isolated WAEGIS entry point for the bundled RepoWise CLI."""\n'
        "from repowise.cli.editor_integrations import claude_config\n"
        "claude_config.migrate_claude_code_hooks = lambda: False\n"
        "from repowise.cli.main import cli\n"
        "cli()\n",
        encoding="utf-8",
        newline="",
    )
    (site_packages / "sitecustomize.py").write_text(
        _offline_sitecustomize(),
        encoding="utf-8",
        newline="",
    )
    source_archive = destination / REPOWISE_SOURCE_ARCHIVE
    _write_repowise_source_archive(source_info, source_archive, epoch=epoch)
    licenses = destination / "licenses"
    licenses.mkdir()
    shutil.copy2(source / "LICENSE", licenses / "REPOWISE-AGPL-3.0.txt")
    (licenses / "THIRD-PARTY-NOTICES.txt").write_text(
        _third_party_notices(site_packages),
        encoding="utf-8",
        newline="",
    )
    launcher_name, launcher_text = _repowise_launcher(target, relative_python)
    launcher = destination / launcher_name
    launcher.write_text(launcher_text, encoding="utf-8", newline="")
    if target == "linux-x64":
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    files = _repowise_file_table(destination)
    tree_digest, unpacked_size = _repowise_tree_digest(files)
    packaged_size = _repowise_packaged_size(destination, files)
    manifest = {
        "schema_version": 1,
        "build_epoch": epoch,
        "edition": "complete",
        "repowise_version": REPOWISE_VERSION,
        "platform": target,
        "launcher": launcher_name,
        "source": {
            "tag": source_info["tag"],
            "commit": source_info["commit"],
            "archive": REPOWISE_SOURCE_ARCHIVE,
        },
        "source_sha256": sha256_file(source_archive),
        "tree_sha256": tree_digest,
        "packaged_size": packaged_size,
        "unpacked_size": unpacked_size,
        "files": files,
    }
    (destination / "repowise-bundle-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    probe = [str(launcher), "--version"]
    if target == "windows-x64":
        probe = ["cmd.exe", "/d", "/c", str(launcher), "--version"]
    output = _run_build_command(
        probe,
        cwd=destination,
        description="RepoWise bundled native import/version smoke",
        environment={
            **os.environ,
            "WAEGIS_REPOWISE_OFFLINE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    if REPOWISE_VERSION not in output:
        raise PackagingError(f"RepoWise bundled smoke reported an unexpected version: {output!r}")
    return frozenset(
        {launcher_name, relative_python}
        | {f"runtime/{path}" for path in executable_runtime}
    )


def _tree_manifest(root: Path) -> dict[str, str]:
    """@brief Hash every regular staged file using portable relative names.
    @version 0.2.0
    """
    paths = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in paths
    }


def _write_archive_manifest(root: Path, *, target: str) -> None:
    """@brief Write the internal application-archive file manifest.
    @version 0.2.0
    """
    if target not in SUPPORTED_RUNTIME_TARGETS:
        raise PackagingError(f"unsupported internal archive target: {target!r}")
    payload = {"schema_version": 1, "target": target, "files": _tree_manifest(root)}
    (root / "archive-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )


def _manifest_file_table(
    content: bytes,
    *,
    expected_target: str | None,
    archive_name: str,
) -> dict[str, str]:
    """@brief Parse and strictly validate one internal archive manifest."""
    if len(content) > MAX_MANIFEST_BYTES:
        raise PackagingError(f"internal archive manifest is too large: {archive_name}")
    try:
        document = _strict_json_loads(
            content.decode("utf-8"),
            context=f"internal archive manifest {archive_name}",
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackagingError(f"malformed internal archive manifest: {archive_name}") from exc
    if not isinstance(document, dict) or frozenset(document) != {
        "schema_version",
        "target",
        "files",
    }:
        raise PackagingError(f"invalid internal archive manifest schema: {archive_name}")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise PackagingError(f"unsupported internal archive manifest schema: {archive_name}")
    target = document["target"]
    if (
        not isinstance(target, str)
        or target not in SUPPORTED_RUNTIME_TARGETS
        or (expected_target is not None and target != expected_target)
    ):
        raise PackagingError(f"wrong internal archive target: {archive_name}")
    files = document["files"]
    if not isinstance(files, dict) or not files or len(files) > MAX_ARCHIVE_MEMBERS:
        raise PackagingError(f"invalid internal archive file table: {archive_name}")
    normalized: dict[str, str] = {}
    for relative, digest in files.items():
        if not isinstance(relative, str) or relative == ARCHIVE_MANIFEST_NAME:
            raise PackagingError(f"invalid declared archive path: {relative!r}")
        canonical = _canonical_relative_name(relative)
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise PackagingError(f"invalid declared archive digest: {relative!r}")
        normalized[canonical] = digest.lower()
    _reject_name_collisions(normalized, context="manifest")
    return normalized


def _digest_stream(source: BinaryIO) -> str:
    """@brief Hash one bounded archive stream without loading the payload wholly."""
    digest = hashlib.sha256()
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _manifest_prefix(name: str, *, archive_name: str) -> str:
    """@brief Validate the single-root location of an internal manifest."""
    canonical = _canonical_relative_name(name)
    parts = PurePosixPath(canonical).parts
    if len(parts) != 2 or parts[1] != ARCHIVE_MANIFEST_NAME:
        raise PackagingError(
            f"internal archive manifest must be directly below one root: {archive_name}"
        )
    return f"{parts[0]}/"


def _verify_internal_zip(path: Path, *, expected_target: str | None = None) -> None:
    """
    @brief      Verify exact regular-file membership and digests in one ZIP.
    @details    Safe directory entries are allowed and ignored. The manifest is
                the sole regular member omitted from its own ``files`` table.
    @version    0.2.0
    """
    try:
        with zipfile.ZipFile(path) as bundle:
            infos = bundle.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise PackagingError(f"application ZIP has too many members: {path.name}")
            _reject_name_collisions(
                (info.filename for info in infos),
                context="ZIP",
            )
            manifests = [
                info
                for info in infos
                if info.filename.endswith(f"/{ARCHIVE_MANIFEST_NAME}")
            ]
            if len(manifests) != 1:
                raise PackagingError(
                    f"application archive must have exactly one internal manifest: {path.name}"
                )
            manifest = manifests[0]
            prefix = _manifest_prefix(manifest.filename, archive_name=path.name)
            regular: dict[str, zipfile.ZipInfo] = {}
            for info in infos:
                name = info.filename
                canonical = _canonical_relative_name(name.rstrip("/"))
                if not canonical.startswith(prefix.rstrip("/") + "/") and canonical != prefix.rstrip("/"):
                    raise PackagingError(f"ZIP member is outside the archive root: {name!r}")
                if info.flag_bits & 0x1:
                    raise PackagingError(f"encrypted ZIP member is unsupported: {name!r}")
                mode = info.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                is_directory = info.is_dir()
                if is_directory:
                    if file_type not in {0, stat.S_IFDIR}:
                        raise PackagingError(f"unsupported ZIP directory type: {name!r}")
                    continue
                if file_type not in {0, stat.S_IFREG}:
                    raise PackagingError(f"unsupported ZIP member type: {name!r}")
                regular[name] = info
            if manifest.filename not in regular:
                raise PackagingError(f"internal ZIP manifest is not a regular file: {path.name}")
            if manifest.file_size > MAX_MANIFEST_BYTES:
                raise PackagingError(f"internal ZIP manifest is too large: {path.name}")
            with bundle.open(manifest) as source:
                files = _manifest_file_table(
                    source.read(MAX_MANIFEST_BYTES + 1),
                    expected_target=expected_target,
                    archive_name=path.name,
                )
            expected_names = {f"{prefix}{relative}" for relative in files}
            actual_payload = set(regular) - {manifest.filename}
            missing = sorted(expected_names - actual_payload)
            extra = sorted(actual_payload - expected_names)
            if missing:
                raise PackagingError(f"archive member missing: {path.name}:{missing[0]}")
            if extra:
                raise PackagingError(f"undeclared archive member: {path.name}:{extra[0]}")
            for relative, expected in files.items():
                member = regular[f"{prefix}{relative}"]
                with bundle.open(member) as source:
                    actual = _digest_stream(source)
                if actual != expected:
                    raise PackagingError(
                        f"archive member hash mismatch: {path.name}:{relative}"
                    )
    except PackagingError:
        raise
    except (OSError, EOFError, RuntimeError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise PackagingError(f"invalid application ZIP {path.name}: {exc}") from exc


def _verify_internal_tar(path: Path, *, expected_target: str | None = None) -> None:
    """
    @brief      Verify exact regular-file membership and digests in one tar.gz.
    @details    Safe directory entries are allowed and ignored. Links, devices,
                FIFOs, and every other non-regular payload type are rejected.
    @version    0.2.0
    """
    try:
        with tarfile.open(path, "r:gz") as bundle:
            members = bundle.getmembers()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise PackagingError(f"application tar has too many members: {path.name}")
            _reject_name_collisions(
                (member.name.rstrip("/") for member in members),
                context="tar",
            )
            manifests = [
                member
                for member in members
                if member.name.endswith(f"/{ARCHIVE_MANIFEST_NAME}")
            ]
            if len(manifests) != 1:
                raise PackagingError(
                    f"application archive must have exactly one internal manifest: {path.name}"
                )
            manifest = manifests[0]
            prefix = _manifest_prefix(manifest.name, archive_name=path.name)
            regular: dict[str, tarfile.TarInfo] = {}
            for member in members:
                name = member.name.rstrip("/")
                canonical = _canonical_relative_name(name)
                if not canonical.startswith(prefix.rstrip("/") + "/") and canonical != prefix.rstrip("/"):
                    raise PackagingError(f"tar member is outside the archive root: {name!r}")
                if member.isdir():
                    continue
                if not member.isfile():
                    raise PackagingError(f"unsupported tar member type: {name!r}")
                regular[name] = member
            if not manifest.isfile() or manifest.size > MAX_MANIFEST_BYTES:
                raise PackagingError(f"invalid internal tar manifest: {path.name}")
            source = bundle.extractfile(manifest)
            if source is None:
                raise PackagingError(f"cannot read internal archive manifest: {path.name}")
            with source:
                files = _manifest_file_table(
                    source.read(MAX_MANIFEST_BYTES + 1),
                    expected_target=expected_target,
                    archive_name=path.name,
                )
            expected_names = {f"{prefix}{relative}" for relative in files}
            actual_payload = set(regular) - {manifest.name}
            missing = sorted(expected_names - actual_payload)
            extra = sorted(actual_payload - expected_names)
            if missing:
                raise PackagingError(f"archive member missing: {path.name}:{missing[0]}")
            if extra:
                raise PackagingError(f"undeclared archive member: {path.name}:{extra[0]}")
            for relative, expected in files.items():
                source = bundle.extractfile(regular[f"{prefix}{relative}"])
                if source is None:
                    raise PackagingError(f"archive member missing: {path.name}:{relative}")
                with source:
                    actual = _digest_stream(source)
                if actual != expected:
                    raise PackagingError(
                        f"archive member hash mismatch: {path.name}:{relative}"
                    )
    except PackagingError:
        raise
    except (OSError, EOFError, ValueError, KeyError, tarfile.TarError) as exc:
        raise PackagingError(f"invalid application tar {path.name}: {exc}") from exc


def _read_complete_bundle_manifest(path: Path) -> dict[str, Any]:
    """
    @brief      Read the RepoWise sidecar manifest from a Complete archive.
    @param[in]  path Complete Windows ZIP or Linux tar.gz archive.
    @return     Parsed RepoWise bundle manifest.
    @exception  PackagingError If the archive or sidecar manifest is missing
                or malformed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.0
    """
    suffix = path.name
    try:
        if suffix.endswith("-windows-x64.zip"):
            with zipfile.ZipFile(path) as bundle:
                member = next(
                    (
                        name
                        for name in bundle.namelist()
                        if name.endswith("/repowise/repowise-bundle-manifest.json")
                    ),
                    None,
                )
                if member is None:
                    raise PackagingError(
                        f"Complete archive has no RepoWise bundle manifest: {path.name}"
                    )
                document = json.loads(bundle.read(member))
        elif suffix.endswith("-linux-x64.tar.gz"):
            with tarfile.open(path, "r:gz") as bundle:
                member = next(
                    (
                        item
                        for item in bundle.getmembers()
                        if item.name.endswith("/repowise/repowise-bundle-manifest.json")
                    ),
                    None,
                )
                source = bundle.extractfile(member) if member is not None else None
                if source is None:
                    raise PackagingError(
                        f"Complete archive has no RepoWise bundle manifest: {path.name}"
                    )
                document = json.loads(source.read())
        else:
            raise PackagingError(f"unsupported Complete archive: {path.name}")
    except (OSError, tarfile.TarError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise PackagingError(f"invalid Complete archive: {path.name}") from exc
    if not isinstance(document, dict):
        raise PackagingError(f"invalid RepoWise bundle manifest: {path.name}")
    return document


def _validate_complete_companion(
    path: Path,
    *,
    expected_platform: str,
    source_info: Mapping[str, Any] | None = None,
    expected_epoch: int | None = None,
) -> None:
    """
    @brief      Reject stale or mismatched cross-platform Complete companions.
    @param[in]  path Complete archive to validate.
    @param[in]  expected_platform Platform encoded by the artifact name.
    @param[in]  source_info Optional current RepoWise source identity.
    @param[in]  expected_epoch Optional normalized release build epoch.
    @return     None.
    @exception  PackagingError If edition, version, platform, tag, or commit
                differs from the current native build.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.2.0
    """
    document = _read_complete_bundle_manifest(path)
    if (
        document.get("schema_version") != 1
        or document.get("edition") != "complete"
        or document.get("repowise_version") != REPOWISE_VERSION
        or document.get("platform") != expected_platform
        or type(document.get("build_epoch")) is not int
        or document["build_epoch"] < ZIP_MIN_EPOCH
        or document["build_epoch"] > MAX_BUILD_EPOCH
        or document["build_epoch"] % 2
        or (
            expected_epoch is not None
            and document["build_epoch"] != expected_epoch
        )
    ):
        raise PackagingError(f"mismatched Complete archive metadata: {path.name}")
    source = document.get("source")
    if not isinstance(source, dict):
        raise PackagingError(f"invalid Complete archive source metadata: {path.name}")
    tag = source.get("tag")
    commit = source.get("commit")
    if (
        tag not in {REPOWISE_VERSION, f"v{REPOWISE_VERSION}"}
        or not isinstance(commit, str)
        or len(commit) != 40
        or any(character not in "0123456789abcdef" for character in commit.lower())
        or source.get("archive") != REPOWISE_SOURCE_ARCHIVE
    ):
        raise PackagingError(f"invalid Complete archive source identity: {path.name}")
    if source_info is not None and (
        tag != source_info["tag"]
        or commit != source_info["commit"]
    ):
        raise PackagingError(
            f"stale Complete companion; rebuild {path.name} from the same RepoWise source"
        )


def _verify_zipapp(path: Path) -> None:
    """@brief Validate one generated zipapp before atomic publication."""
    try:
        with zipfile.ZipFile(path) as bundle:
            infos = bundle.infolist()
            _reject_name_collisions(
                (info.filename for info in infos),
                context="zipapp",
            )
            if sum(info.filename == "__main__.py" for info in infos) != 1:
                raise PackagingError("zipapp must contain exactly one __main__.py")
            for info in infos:
                if info.is_dir() or info.flag_bits & 0x1:
                    raise PackagingError(
                        f"zipapp contains an unsupported member: {info.filename!r}"
                    )
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                    raise PackagingError(
                        f"zipapp contains an unsupported member type: {info.filename!r}"
                    )
                with bundle.open(info) as source:
                    while source.read(1024 * 1024):
                        pass
    except PackagingError:
        raise
    except (OSError, EOFError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
        raise PackagingError(f"invalid generated zipapp: {exc}") from exc


def _build_zipapp(output: Path, *, epoch: int) -> Path:
    """@brief Build the deterministic standalone payload-bundled WAEGIS zipapp.
    @version 0.2.0
    """
    with tempfile.TemporaryDirectory(prefix="waegis-pyz-") as temporary_text:
        staging = Path(temporary_text)
        _copy_tree(SOURCE_ROOT / "waegis", staging / "waegis")
        _copy_tree(PAYLOAD_ROOT, staging / "waegis" / "_bundled_payload")
        (staging / "__main__.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            "from waegis.cli import main\n"
            "main()\n",
            encoding="utf-8",
            newline="",
        )
        entries = [
            (
                _canonical_relative_name(path.relative_to(staging).as_posix()),
                path,
                False,
            )
            for path in staging.rglob("*")
            if path.is_file()
        ]
        _write_deterministic_zip(
            output,
            entries,
            epoch=epoch,
            verify=_verify_zipapp,
        )
    return output


def _windows_launcher(relative_python: str, *, complete: bool = False) -> str:
    """@brief Render the Windows application-archive launcher."""
    python = relative_python.replace("/", "\\")
    edition = "complete" if complete else "core"
    repowise = 'set "WAEGIS_REPOWISE_BUNDLE=%~dp0repowise"\r\n' if complete else ""
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"WAEGIS_PACKAGING_TYPE=windows-x64-application-archive\"\r\n"
        f"set \"WAEGIS_EDITION={edition}\"\r\n"
        f"{repowise}"
        f"set \"WAEGIS_PACKAGED_RUNTIME=%~dp0{python}\"\r\n"
        f"\"%~dp0{python}\" \"%~dp0waegis.pyz\" %*\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )


def _linux_launcher(relative_python: str, *, complete: bool = False) -> str:
    """@brief Render the Linux application-archive launcher."""
    edition = "complete" if complete else "core"
    repowise = 'export WAEGIS_REPOWISE_BUNDLE="$ROOT/repowise"\n' if complete else ""
    return (
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "ROOT=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
        "export WAEGIS_PACKAGING_TYPE=linux-x64-application-archive\n"
        f"export WAEGIS_EDITION={edition}\n"
        f"{repowise}"
        f"export WAEGIS_PACKAGED_RUNTIME=\"$ROOT/{relative_python}\"\n"
        f"exec \"$ROOT/{relative_python}\" \"$ROOT/waegis.pyz\" \"$@\"\n"
    )


def _build_application_archive(
    target: str,
    *,
    zipapp_path: Path,
    output: Path,
    runtime_cache: Path,
    offline: bool,
    epoch: int,
    repowise_source: Mapping[str, Any] | None = None,
) -> Path:
    """
    @brief      Build one self-contained OS application archive.
    @param[in]  target Runtime target key from ``runtime-lock.json``.
    @param[in]  zipapp_path Previously built payload-bundled zipapp.
    @param[in]  output Final application archive path.
    @param[in]  runtime_cache Cache containing or receiving pinned runtimes.
    @param[in]  offline Refuse network access when true.
    @return     Final archive path.
    @details    Launcher text preserves its declared newline convention on
                every host; Linux tar modes are normalized independently of
                Windows filesystem semantics.
    @exception  PackagingError If runtime acquisition, staging, or archive
                validation inputs fail.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.3.0
    """
    runtime_archive = _download_runtime(target, runtime_cache, offline=offline)
    with tempfile.TemporaryDirectory(prefix=f"waegis-{target}-") as temporary_text:
        staging = Path(temporary_text) / f"waegis-{target}"
        runtime = staging / "runtime"
        runtime.mkdir(parents=True)
        runtime_executables = _extract_runtime(runtime_archive, runtime)
        interpreter = _find_interpreter(runtime, target)
        relative_python = interpreter.relative_to(staging).as_posix()
        shutil.copy2(zipapp_path, staging / "waegis.pyz")
        _copy_tree(PAYLOAD_ROOT, staging / "payload")
        repowise_executables: frozenset[str] = frozenset()
        if repowise_source is not None:
            repowise_executables = _build_repowise_bundle(
                target,
                source_info=repowise_source,
                destination=staging / "repowise",
                runtime_cache=runtime_cache,
                offline=offline,
                epoch=epoch,
            )
        if target == "windows-x64":
            (staging / "waegis.cmd").write_text(
                _windows_launcher(relative_python, complete=repowise_source is not None),
                encoding="utf-8",
                newline="",
            )
        else:
            launcher = staging / "waegis"
            launcher.write_text(
                _linux_launcher(relative_python, complete=repowise_source is not None),
                encoding="utf-8",
                newline="",
            )
            launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        _write_archive_manifest(staging, target=target)
        executable_paths = frozenset(
            (
                {"waegis.cmd" if target == "windows-x64" else "waegis", relative_python}
                | {f"runtime/{path}" for path in runtime_executables}
                | {f"repowise/{path}" for path in repowise_executables}
            )
        )
        if target == "windows-x64":
            _write_deterministic_zip(
                output,
                _tree_entries(
                    staging,
                    archive_root=staging.name,
                    executable_paths=executable_paths,
                ),
                epoch=epoch,
                verify=lambda path: _verify_internal_zip(
                    path,
                    expected_target=target,
                ),
            )
        else:
            _write_deterministic_tar_gz(
                output,
                staging,
                archive_root=staging.name,
                executable_paths=executable_paths,
                epoch=epoch,
                verify=lambda path: _verify_internal_tar(
                    path,
                    expected_target=target,
                ),
            )
    return output


# EXPORTED FUNCTIONS / PUBLIC API


def _build_release_impl(
    output: Path,
    *,
    runtime_cache: Path,
    offline: bool,
    zipapp_only: bool,
    repowise_source: Path | None = None,
    complete_target: str | None = None,
) -> list[Path]:
    """
    @brief      Implement Core and optional native Complete artifact assembly.
    @param[in]  output Release output directory.
    @param[in]  runtime_cache Pinned embedded-runtime and wheel cache.
    @param[in]  offline Refuse build-time downloads when true.
    @param[in]  zipapp_only Build only the portable Core zipapp when true.
    @param[in]  repowise_source Optional clean RepoWise source checkout.
    @param[in]  complete_target Optional native Complete platform.
    @return     Paths to the release artifacts represented by the manifest.
    @details    One normalized SOURCE_DATE_EPOCH, source-commit timestamp, or
                fixed fallback drives every archive entry and gzip header. A
                previously built opposite-platform Complete companion is
                included only when its RepoWise tag and commit match the
                source used for the current native build.
    @exception  PackagingError If source, native runtime, archive, or companion
                validation fails.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.7.0
    """
    wizard_version = _wizard_version()
    source_info = (
        _validate_repowise_source(repowise_source)
        if repowise_source is not None
        else None
    )
    if source_info is not None and zipapp_only:
        raise PackagingError("RepoWise Complete cannot be produced with --zipapp-only")
    if complete_target is not None and source_info is None:
        raise PackagingError("--complete-target requires --repowise-source")
    epoch = _canonical_build_epoch()
    output.mkdir(parents=True, exist_ok=True)
    pyz = _build_zipapp(output / ZIPAPP_NAME, epoch=epoch)
    artifacts = [pyz]
    if not zipapp_only:
        artifacts.append(
            _build_application_archive(
                "windows-x64",
                zipapp_path=pyz,
                output=output / WINDOWS_ARCHIVE_NAME,
                runtime_cache=runtime_cache,
                offline=offline,
                epoch=epoch,
            )
        )
        artifacts.append(
            _build_application_archive(
                "linux-x64",
                zipapp_path=pyz,
                output=output / LINUX_ARCHIVE_NAME,
                runtime_cache=runtime_cache,
                offline=offline,
                epoch=epoch,
            )
        )
        if source_info is not None:
            native_target = complete_target or (
                "windows-x64"
                if os.name == "nt"
                else "linux-x64"
                if sys.platform.startswith("linux")
                else ""
            )
            if native_target not in {"windows-x64", "linux-x64"}:
                raise PackagingError(f"unsupported Complete build host: {sys.platform}")
            complete_name = (
                COMPLETE_WINDOWS_ARCHIVE_NAME
                if native_target == "windows-x64"
                else COMPLETE_LINUX_ARCHIVE_NAME
            )
            artifacts.append(
                _build_application_archive(
                    native_target,
                    zipapp_path=pyz,
                    output=output / complete_name,
                    runtime_cache=runtime_cache,
                    offline=offline,
                    epoch=epoch,
                    repowise_source=source_info,
                )
            )
            other_complete = (
                output / COMPLETE_LINUX_ARCHIVE_NAME
                if native_target == "windows-x64"
                else output / COMPLETE_WINDOWS_ARCHIVE_NAME
            )
            if other_complete.is_file():
                other_platform = (
                    "linux-x64" if native_target == "windows-x64" else "windows-x64"
                )
                _validate_complete_companion(
                    other_complete,
                    expected_platform=other_platform,
                    source_info=source_info,
                    expected_epoch=epoch,
                )
                artifacts.append(other_complete)
    hashes = {path.name: sha256_file(path) for path in artifacts}
    metadata = {
        path.name: {
            "sha256": hashes[path.name],
            "size": path.stat().st_size,
            "edition": "complete" if path.name.startswith("waegis-complete-") else "core",
        }
        for path in artifacts
    }
    release_manifest = output / "release-manifest.json"
    # newline="" suppresses the platform translation `\n` -> `\r\n`. These two
    # files are shipped as release assets and consumed by POSIX tooling: a
    # CRLF `SHA256SUMS` makes `sha256sum -c` look for a filename with a
    # trailing carriage return and fail every entry, which reads as a corrupt
    # download rather than as a packaging bug. Building on Windows must not
    # produce different bytes here than building on Linux.
    manifest_content = (
        json.dumps(
            {
                "schema_version": 1,
                "build_epoch": epoch,
                "waegis_version": wizard_version,
                "repowise_version": REPOWISE_VERSION if source_info is not None else None,
                "artifacts": hashes,
                "artifact_metadata": metadata,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    _atomic_write_bytes(release_manifest, manifest_content.encode("utf-8"))
    _atomic_write_bytes(
        output / "SHA256SUMS",
        "".join(
            f"{digest}  {name}\n"
            for name, digest in sorted(hashes.items(), key=lambda item: item[0])
        ).encode("utf-8"),
    )
    return artifacts


def build_release(
    output: Path,
    *,
    runtime_cache: Path,
    offline: bool,
    zipapp_only: bool,
    repowise_source: Path | None = None,
    complete_target: str | None = None,
) -> list[Path]:
    """
    @brief      Build reproducible WAEGIS release artifacts.
    @return     Paths represented by deterministic release metadata.
    @exception  PackagingError For every ordinary input, filesystem, tool,
                download, staging, archive, or publication failure.
    @version    0.1.0
    """
    try:
        return _build_release_impl(
            output,
            runtime_cache=runtime_cache,
            offline=offline,
            zipapp_only=zipapp_only,
            repowise_source=repowise_source,
            complete_target=complete_target,
        )
    except PackagingError:
        raise
    except Exception as exc:
        raise PackagingError(f"release build failed: {exc}") from exc


def _verify_release_impl(output: Path) -> None:
    """
    @brief      Verify release hashes, archive manifests, and Complete identity.
    @param[in]  output Release output directory.
    @return     None.
    @exception  PackagingError If metadata, hashes, archive contents, or
                Complete bundle identity validation fails.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.7.0
    """
    manifest_path = output / "release-manifest.json"
    try:
        document = _strict_json_loads(
            manifest_path.read_text(encoding="utf-8"),
            context=f"release manifest {manifest_path}",
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackagingError(f"invalid release manifest: {manifest_path}") from exc
    if not isinstance(document, dict) or frozenset(document) != {
        "schema_version",
        "build_epoch",
        "waegis_version",
        "repowise_version",
        "artifacts",
        "artifact_metadata",
    }:
        raise PackagingError(f"invalid release manifest schema: {manifest_path}")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise PackagingError(f"unsupported release manifest schema: {manifest_path}")
    epoch = document["build_epoch"]
    if (
        type(epoch) is not int
        or epoch < ZIP_MIN_EPOCH
        or epoch > MAX_BUILD_EPOCH
        or epoch % 2
    ):
        raise PackagingError(f"invalid release build epoch: {manifest_path}")
    if (
        not isinstance(document["waegis_version"], str)
        or SAFE_VERSION_PATTERN.fullmatch(document["waegis_version"]) is None
        or document["repowise_version"] not in {None, REPOWISE_VERSION}
    ):
        raise PackagingError(f"invalid release version metadata: {manifest_path}")
    artifacts = document["artifacts"]
    artifact_metadata = document["artifact_metadata"]
    if not isinstance(artifacts, dict) or not artifacts:
        raise PackagingError(f"invalid artifact table: {manifest_path}")
    if not isinstance(artifact_metadata, dict) or set(artifact_metadata) != set(artifacts):
        raise PackagingError(f"invalid artifact metadata table: {manifest_path}")
    allowed_names = {
        ZIPAPP_NAME,
        WINDOWS_ARCHIVE_NAME,
        LINUX_ARCHIVE_NAME,
        COMPLETE_WINDOWS_ARCHIVE_NAME,
        COMPLETE_LINUX_ARCHIVE_NAME,
    }
    names: list[str] = []
    for name, expected in artifacts.items():
        if (
            not isinstance(name, str)
            or name not in allowed_names
            or Path(name).name != name
            or not isinstance(expected, str)
            or SHA256_PATTERN.fullmatch(expected) is None
        ):
            raise PackagingError(f"invalid release artifact entry: {name!r}")
        metadata = artifact_metadata[name]
        if (
            not isinstance(metadata, dict)
            or frozenset(metadata) != {"sha256", "size", "edition"}
            or metadata["sha256"] != expected
            or type(metadata["size"]) is not int
            or metadata["size"] <= 0
            or metadata["edition"] not in {"core", "complete"}
            or (
                metadata["edition"] == "complete"
                and not name.startswith("waegis-complete-")
            )
            or (
                metadata["edition"] == "core"
                and name.startswith("waegis-complete-")
            )
        ):
            raise PackagingError(f"invalid release artifact metadata: {name!r}")
        names.append(name)
    _reject_name_collisions(names, context="release")
    expected_sum_lines: list[str] = []
    for name, expected in sorted(artifacts.items(), key=lambda item: str(item[0])):
        path = output / str(name)
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != artifact_metadata[name]["size"]
            or sha256_file(path) != expected.lower()
        ):
            raise PackagingError(f"release artifact hash mismatch: {name}")
        expected_sum_lines.append(f"{expected}  {name}\n")
        if name == ZIPAPP_NAME:
            _verify_zipapp(path)
        elif str(name).endswith("-windows-x64.zip"):
            _verify_internal_zip(path, expected_target="windows-x64")
            if str(name).startswith("waegis-complete-"):
                _validate_complete_companion(
                    path,
                    expected_platform="windows-x64",
                    expected_epoch=epoch,
                )
        elif str(name).endswith("-linux-x64.tar.gz"):
            _verify_internal_tar(path, expected_target="linux-x64")
            if str(name).startswith("waegis-complete-"):
                _validate_complete_companion(
                    path,
                    expected_platform="linux-x64",
                    expected_epoch=epoch,
                )
    sums = output / "SHA256SUMS"
    try:
        actual_sums = sums.read_text(encoding="utf-8")
    except OSError as exc:
        raise PackagingError(f"missing release checksum file: {sums}") from exc
    if actual_sums != "".join(expected_sum_lines):
        raise PackagingError(f"release checksum file does not match manifest: {sums}")


def verify_release(output: Path) -> None:
    """
    @brief      Verify release metadata and every represented artifact.
    @exception  PackagingError For every ordinary metadata, filesystem, or
                archive failure.
    @version    0.1.0
    """
    try:
        _verify_release_impl(output)
    except PackagingError:
        raise
    except Exception as exc:
        raise PackagingError(f"release verification failed: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    """@brief Parse release-builder arguments and produce the requested artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--runtime-cache", type=Path, default=PACKAGE_ROOT / ".runtime-cache")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--zipapp-only", action="store_true")
    parser.add_argument(
        "--repowise-source",
        type=Path,
        help="Clean RepoWise v0.37.0 source checkout used to build the native Complete edition",
    )
    parser.add_argument(
        "--complete-target",
        choices=("windows-x64", "linux-x64"),
        help="Complete target; must match the native build host",
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            verify_release(args.output.resolve())
        else:
            build_release(
                args.output.resolve(),
                runtime_cache=args.runtime_cache.resolve(),
                offline=args.offline,
                zipapp_only=args.zipapp_only,
                repowise_source=args.repowise_source.resolve() if args.repowise_source else None,
                complete_target=args.complete_target,
            )
            verify_release(args.output.resolve())
    except PackagingError as exc:
        parser.exit(3, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
