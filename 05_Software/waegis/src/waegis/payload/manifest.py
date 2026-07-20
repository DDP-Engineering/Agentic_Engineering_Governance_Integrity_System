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
@brief Current install-manifest schema: safe read/write, validation, and drift.
@details Reads and writes one unreleased schema for
         ``.agentic/install-manifest.json``. The schema retains the original
         byte-exact file inventory and adds a deterministic payload digest plus
         non-secret generated-configuration metadata. Managed paths are
         canonical, portable, repo-relative paths; traversal, absolute paths,
         normalization/case collisions, and symlink escapes are rejected before
         callers may read or mutate a managed file.
@details The module provides byte-exact sha256 hashing
         (files are read in binary mode with no newline translation, so a copy
         made with e.g. ``shutil.copy2`` reproduces the same hash regardless of
         host OS line-ending handling, while a file whose bytes were actually
         changed — for example a CRLF rewrite of an LF original — hashes
         differently), POSIX-normalized path keys (portable across Windows and
         POSIX checkouts), and local-vs-manifest drift computation (modified +
         missing only — comparing against a *new* payload's file list to find
         "extra" files is T3.2/T6.2's job, not this module's).
@details **JSON shape.** The current schema uses ``manifest_version, product,
         payload_version, installed_at, installed_by, mode, files, generated,
         skipped, payload_digest, configuration``.
         Each
         ``files`` entry is ``{"sha256": str, "size": int}`` keyed by a
         repo-relative POSIX path. This module renders keys in sorted order
         for determinism; it does not decide which files belong in the
         manifest — callers (T3.2's copier) supply the file list.
@details This module is pure data (read/write/validate/compute) per the io/
         module convention (T1.3): it never prints; callers render.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from os import PathLike
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from ..version import WIZARD_VERSION

# CONSTANTS

# @brief Single current schema. WAEGIS is unreleased; no legacy schema is read.
MANIFEST_VERSION = 1

# @brief Repo-relative path the manifest is written to and read from.
MANIFEST_RELATIVE_PATH = ".agentic/install-manifest.json"

# @brief Top-level keys a v1 manifest document must contain (§6); any missing
#        key is a validation failure, not a default.
_REQUIRED_KEYS = frozenset(
    {
        "manifest_version",
        "product",
        "payload_version",
        "installed_at",
        "installed_by",
        "mode",
        "files",
        "generated",
        "skipped",
        "payload_digest",
        "configuration",
    }
)

# @brief Windows drive-qualified paths must be rejected even on POSIX hosts.
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:")

# @brief Chunk size for streaming file hashing.
_HASH_CHUNK_SIZE = 1 << 16

# DATA MODELS / TYPEDEFINITIONS


class ManifestError(ValueError):
    """
    @brief Raised when a manifest document is malformed or invalid.
    @details Never raised for a merely absent manifest; use :func:`load_manifest`
             to distinguish absent/invalid/valid.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class ManifestState(Enum):
    """
    @brief The three distinguishable outcomes of loading a manifest.
    @details Lets callers (``analyze``, ``doctor``, ``upgrade``) branch on
             exactly "no manifest yet" vs. "manifest present but broken" vs.
             "manifest present and valid" (plan §6 no-manifest legacy case).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    ABSENT = "absent"
    INVALID = "invalid"
    VALID = "valid"


@dataclass(frozen=True)
class FileEntry:
    """
    @brief One ``files`` map entry: the as-shipped sha256 and byte size.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    sha256: str
    size: int

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen ``{"sha256", "size"}`` mapping.
        @return     Mapping with keys ``sha256, size``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return {"sha256": self.sha256, "size": self.size}


@dataclass(frozen=True)
class Manifest:
    """
    @brief Schema-v1/v2 install manifest (plan §6 plus lifecycle hardening).
    @details ``files`` is every payload file copied verbatim, keyed by
             repo-relative POSIX path, with its original as-shipped hash.
             ``generated`` lists files the wizard created/rewrote from answers
             (upgrade never overwrites these). ``skipped`` lists payload files
             the operator chose to keep local during an adoption conflict.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    manifest_version: int
    product: str
    payload_version: str
    installed_at: str
    installed_by: str
    mode: str
    files: dict[str, FileEntry] = field(default_factory=dict)
    generated: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    payload_digest: str = ""
    configuration: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen JSON-safe mapping, in field order.
        @details    ``files`` keys are emitted in sorted order so the
                    serialized document is deterministic regardless of the
                    order the caller built the mapping in.
        @return     Mapping keyed ``manifest_version, product, payload_version,
                    installed_at, installed_by, mode, files, generated,
                    skipped``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        data: dict[str, Any] = {
            "manifest_version": self.manifest_version,
            "product": self.product,
            "payload_version": self.payload_version,
            "installed_at": self.installed_at,
            "installed_by": self.installed_by,
            "mode": self.mode,
            "files": {key: self.files[key].to_dict() for key in sorted(self.files)},
            "generated": list(self.generated),
            "skipped": list(self.skipped),
        }
        data["payload_digest"] = self.payload_digest or digest_file_entries(self.files)
        data["configuration"] = dict(self.configuration)
        return data


@dataclass(frozen=True)
class DriftResult:
    """
    @brief Local-vs-manifest-original drift (plan §6/§10.1), sorted for
           determinism.
    @details ``modified`` — recorded files whose current on-disk hash differs
             from the manifest's original hash. ``missing`` — recorded files no
             longer present on disk. A file present on disk but absent from the
             manifest is neither: computing "extra" requires a *new* payload's
             file list and belongs to T3.2/T6.2, not this function.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    modified: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManifestLoadResult:
    """
    @brief Outcome of :func:`load_manifest`: exactly one of absent / invalid /
           valid.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    state: ManifestState
    manifest: Manifest | None = None
    error: str | None = None


# HELPER FUNCTIONS


def normalize_managed_path(path: str | PathLike[str]) -> str:
    """
    @brief      Validate and normalize one portable managed repo-relative path.
    @details    Replaces backslashes before validation. Rejects empty,
                absolute, UNC, drive-qualified, dot/dot-dot, repeated-separator,
                NUL-containing, and colon-containing paths. The strict
                canonical form prevents two textual keys from resolving to the
                same target and remains portable across Windows/POSIX.
    @param[in]  path Candidate key: repo-relative path, string, or ``PathLike``.
    @return     Canonical forward-slash POSIX path string.
    @exception  ManifestError If the candidate is unsafe or non-canonical.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.2.0
    """
    text = str(path).replace("\\", "/")
    if not text or "\x00" in text:
        raise ManifestError(f"unsafe managed path: {str(path)!r}")
    if text.startswith("/") or text.startswith("//") or _DRIVE_PATH_RE.match(text):
        raise ManifestError(f"managed path must be repo-relative: {str(path)!r}")
    if ":" in text:
        raise ManifestError(f"managed path is not portable across supported platforms: {str(path)!r}")
    raw_parts = text.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ManifestError(f"managed path must be canonical and may not traverse: {str(path)!r}")
    normalized = PurePosixPath(text).as_posix()
    if normalized != text:
        raise ManifestError(f"managed path must be canonical: {str(path)!r}")
    return normalized


def resolve_managed_path(root: str | PathLike[str], path: str | PathLike[str]) -> Path:
    """
    @brief      Resolve a validated managed path and prove it stays under root.
    @details    Rejects an existing symlink/junction component and verifies the
                fully resolved candidate is contained by the resolved root.
                Callers must use this helper before hashing, replacing, or
                deleting manifest-controlled files.
    @param[in]  root Repository or payload root.
    @param[in]  path Candidate managed path.
    @return     Safe absolute candidate path.
    @exception  ManifestError If validation, containment, or symlink checks fail.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    key = normalize_managed_path(path)
    root_path = Path(root).resolve()
    cursor = root_path
    for part in PurePosixPath(key).parts:
        cursor = cursor / part
        if cursor.exists() and _is_link_like(cursor):
            raise ManifestError(f"managed path crosses a symlink: {key!r}")
    candidate = root_path.joinpath(*PurePosixPath(key).parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise ManifestError(f"managed path escapes root: {key!r}") from exc
    return candidate


def _is_link_like(path: Path) -> bool:
    """
    @brief      Detect symbolic links and Windows reparse-point junctions.
    @param[in]  path Existing filesystem path.
    @return     True for a symlink, junction, or other reparse point.
    @exception  OSError If metadata cannot be read.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    if path.is_symlink():
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _normalize_path_collection(values: Iterable[str | PathLike[str]], *, label: str) -> tuple[str, ...]:
    """
    @brief      Normalize a path collection and reject duplicates/case collisions.
    @param[in]  values Candidate paths.
    @param[in]  label Field name used in diagnostics.
    @return     Sorted canonical paths.
    @exception  ManifestError On duplicate or case-colliding keys.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    normalized: list[str] = []
    folded: dict[str, str] = {}
    for raw in values:
        key = normalize_managed_path(raw)
        prior = folded.get(key.casefold())
        if prior is not None:
            raise ManifestError(f"{label} contains duplicate/case-colliding paths: {prior!r}, {key!r}")
        folded[key.casefold()] = key
        normalized.append(key)
    return tuple(sorted(normalized))


def digest_file_entries(entries: Mapping[str, FileEntry]) -> str:
    """
    @brief      Compute a deterministic digest over canonical file entries.
    @param[in]  entries Managed path to byte hash/size mapping.
    @return     Lowercase sha256 digest for the entire payload inventory.
    @exception  ManifestError If an entry path is unsafe or collides by case.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    keys = _normalize_path_collection(entries.keys(), label="payload files")
    hasher = hashlib.sha256()
    for key in keys:
        entry = entries[key]
        hasher.update(key.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(entry.sha256.encode("ascii"))
        hasher.update(b"\0")
        hasher.update(str(entry.size).encode("ascii"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def _require_mapping(entry: Any, key: str) -> Mapping[str, Any]:
    """
    @brief      Validate that one ``files`` entry is a mapping before reading
                its fields.
    @param[in]  entry Candidate per-file entry from the parsed JSON document.
    @param[in]  key The offending manifest key, for the error message.
    @return     ``entry``, narrowed to ``Mapping[str, Any]``.
    @exception  ManifestError If ``entry`` is not a mapping.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    if not isinstance(entry, Mapping):
        raise ManifestError(f"install manifest file entry for {key!r} must be an object with sha256/size")
    return entry


def _file_entry_from_dict(entry: Mapping[str, Any], key: str) -> FileEntry:
    """
    @brief      Parse and validate one ``files`` entry.
    @param[in]  entry The raw ``{"sha256": ..., "size": ...}`` mapping.
    @param[in]  key The offending manifest key, for the error message.
    @return     The parsed :class:`FileEntry`.
    @exception  ManifestError If ``sha256`` is not a non-empty string or
                ``size`` is not an integer.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    sha256 = entry.get("sha256")
    size = entry.get("size")
    if not isinstance(sha256, str) or not sha256:
        raise ManifestError(f"install manifest file entry for {key!r} has a missing/invalid 'sha256'")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ManifestError(f"install manifest file entry for {key!r} has a missing/invalid 'size'")
    return FileEntry(sha256=sha256, size=size)


# PUBLIC API


def hash_file(path: str | PathLike[str]) -> FileEntry:
    """
    @brief      Compute the byte-exact sha256 and size of a file on disk.
    @details    Reads in binary mode with no newline translation and no text
                decoding, so the hash reflects the literal bytes on disk: two
                byte-identical copies hash identically no matter which copy
                mechanism produced them or which OS made the copy, while bytes
                that actually differ (e.g. a CRLF rewrite of an LF file) hash
                differently.
    @param[in]  path Path of the file to hash.
    @return     A :class:`FileEntry` with the file's sha256 hex digest and size.
    @exception  OSError If the file cannot be opened/read.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    hasher = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            size += len(chunk)
    return FileEntry(sha256=hasher.hexdigest(), size=size)


def manifest_path(root: str | PathLike[str]) -> Path:
    """
    @brief      Resolve the manifest file path under a repo root.
    @param[in]  root Repository root directory.
    @return     ``root / ".agentic/install-manifest.json"``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return Path(root) / MANIFEST_RELATIVE_PATH


def build_manifest(
    root: str | PathLike[str],
    *,
    product: str,
    payload_version: str,
    mode: str,
    file_paths: Iterable[str | PathLike[str]],
    generated: Iterable[str | PathLike[str]] = (),
    skipped: Iterable[str | PathLike[str]] = (),
    payload_digest: str | None = None,
    configuration: Mapping[str, Any] | None = None,
    installed_at: str | None = None,
    installed_by: str | None = None,
) -> Manifest:
    """
    @brief      Build the current manifest by hashing safe files under a root.
    @details    ``installed_by`` defaults to ``"waegis {WIZARD_VERSION}"`` read
                from :mod:`waegis.version` at call time (not a hardcoded
                string), so it always reflects the running wizard build.
                ``installed_at`` defaults to the current UTC time in
                ISO-8601 ``Z`` form. The manifest's own path is always excluded
                from ``files``, even if a caller's ``file_paths`` includes it,
                so the manifest never lists itself.
    @param[in]  root Repository root directory the paths are resolved under.
    @param[in]  product Payload product name, e.g. ``"aegis"``.
    @param[in]  payload_version Payload version string being installed.
    @param[in]  mode ``"new"`` or ``"adopt"``.
    @param[in]  file_paths Repo-relative paths (POSIX or Windows-style) of every
                payload file to hash and record under ``files``.
    @param[in]  generated Repo-relative paths of files the wizard generated
                from answers rather than copying verbatim.
    @param[in]  skipped Repo-relative paths of payload files the operator chose
                to keep local during an adoption conflict.
    @param[in]  installed_at Override for the installed-at timestamp (tests).
    @param[in]  installed_by Override for the installed-by string (tests).
    @return     The built :class:`Manifest`.
    @exception  OSError If a listed file cannot be hashed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    root = Path(root).resolve()
    manifest_key = normalize_managed_path(MANIFEST_RELATIVE_PATH)
    files: dict[str, FileEntry] = {}
    normalized_files = _normalize_path_collection(file_paths, label="files")
    for key in normalized_files:
        if key == manifest_key:
            continue
        files[key] = hash_file(resolve_managed_path(root, key))
    generated_paths = tuple(path for path in _normalize_path_collection(generated, label="generated") if path != manifest_key)
    skipped_paths = tuple(path for path in _normalize_path_collection(skipped, label="skipped") if path != manifest_key)
    overlap = set(files) & (set(generated_paths) | set(skipped_paths))
    if overlap:
        raise ManifestError(f"manifest path appears in multiple ownership groups: {sorted(overlap)!r}")
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        product=product,
        payload_version=payload_version,
        installed_at=installed_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        installed_by=installed_by or f"waegis {WIZARD_VERSION}",
        mode=mode,
        files=files,
        generated=generated_paths,
        skipped=skipped_paths,
        payload_digest=payload_digest or digest_file_entries(files),
        configuration=dict(configuration or {}),
    )


def manifest_from_dict(data: Mapping[str, Any]) -> Manifest:
    """
    @brief      Parse and validate a manifest document already loaded from JSON.
    @param[in]  data Parsed JSON object.
    @return     The validated :class:`Manifest`.
    @exception  ManifestError If a required top-level key is missing, the
                ``manifest_version`` is unknown, or a ``files`` entry is
                malformed. The message names the offending key.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    manifest_version = data.get("manifest_version")
    if manifest_version != MANIFEST_VERSION:
        raise ManifestError(f"unsupported install manifest_version: {manifest_version!r}")
    missing_keys = _REQUIRED_KEYS - set(data)
    if missing_keys:
        raise ManifestError(f"install manifest missing required key(s): {sorted(missing_keys)}")

    files_raw = data["files"]
    if not isinstance(files_raw, Mapping):
        raise ManifestError("install manifest 'files' must be an object")
    files: dict[str, FileEntry] = {}
    folded: dict[str, str] = {}
    for raw_key, raw_entry in files_raw.items():
        key = normalize_managed_path(raw_key)
        prior = folded.get(key.casefold())
        if prior is not None:
            raise ManifestError(f"files contains duplicate/case-colliding paths: {prior!r}, {key!r}")
        folded[key.casefold()] = key
        files[key] = _file_entry_from_dict(_require_mapping(raw_entry, raw_key), raw_key)

    generated = _normalize_path_collection(data["generated"], label="generated")
    skipped = _normalize_path_collection(data["skipped"], label="skipped")
    overlap = set(files) & (set(generated) | set(skipped))
    if overlap:
        raise ManifestError(f"manifest path appears in multiple ownership groups: {sorted(overlap)!r}")
    configuration = data["configuration"]
    if not isinstance(configuration, Mapping):
        raise ManifestError("install manifest 'configuration' must be an object")
    payload_digest = data["payload_digest"]
    if not isinstance(payload_digest, str) or len(payload_digest) != 64:
        raise ManifestError("install manifest 'payload_digest' must be a sha256 string")

    return Manifest(
        manifest_version=manifest_version,
        product=data["product"],
        payload_version=data["payload_version"],
        installed_at=data["installed_at"],
        installed_by=data["installed_by"],
        mode=data["mode"],
        files=files,
        generated=generated,
        skipped=skipped,
        payload_digest=payload_digest,
        configuration=dict(configuration),
    )


def write_manifest(root: str | PathLike[str], manifest: Manifest) -> Path:
    """
    @brief      Serialize a manifest as pretty-printed, stable-order JSON and
                write it under a repo root.
    @details    2-space indent, ``\\n`` line endings regardless of host OS.
                Creates the parent ``.agentic/`` directory if needed.
    @param[in]  root Repository root directory.
    @param[in]  manifest The :class:`Manifest` to write.
    @return     The path the manifest was written to.
    @exception  OSError If the file cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return path


def read_manifest(root: str | PathLike[str]) -> Manifest:
    """
    @brief      Read and validate the manifest under a repo root.
    @param[in]  root Repository root directory.
    @return     The validated :class:`Manifest`.
    @exception  FileNotFoundError If no manifest exists under ``root``.
    @exception  ManifestError If the file is not valid JSON or fails schema
                validation.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    path = manifest_path(root)
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"install manifest at {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise ManifestError(f"install manifest at {path} must be a JSON object")
    return manifest_from_dict(data)


def load_manifest(root: str | PathLike[str]) -> ManifestLoadResult:
    """
    @brief      Load the manifest under a repo root, distinguishing absent from
                invalid from valid (plan §6 no-manifest legacy case).
    @param[in]  root Repository root directory.
    @return     A :class:`ManifestLoadResult` in exactly one of the three states.
    @exception  None — every failure is captured in the returned result.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    if not manifest_path(root).is_file():
        return ManifestLoadResult(state=ManifestState.ABSENT)
    try:
        manifest = read_manifest(root)
    except (ManifestError, OSError) as exc:
        return ManifestLoadResult(state=ManifestState.INVALID, error=str(exc))
    return ManifestLoadResult(state=ManifestState.VALID, manifest=manifest)


def compute_drift(root: str | PathLike[str], manifest: Manifest) -> DriftResult:
    """
    @brief      Compute local-vs-manifest-original drift (plan §6/§10.1).
    @details    Only ``modified`` (hash differs from the recorded original) and
                ``missing`` (recorded file no longer exists) are in scope; a
                file on disk that the manifest never recorded is ignored by
                design — detecting that kind of "extra" file requires comparing
                against a *new* payload's file list, which is T3.2/T6.2's job.
    @param[in]  root Repository root directory.
    @param[in]  manifest The manifest to compare current files against.
    @return     A :class:`DriftResult` with sorted ``modified``/``missing`` lists.
    @exception  OSError If a present file cannot be hashed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    root = Path(root).resolve()
    modified: list[str] = []
    missing: list[str] = []
    for key, original in manifest.files.items():
        path = resolve_managed_path(root, key)
        if not path.is_file():
            missing.append(key)
            continue
        if hash_file(path).sha256 != original.sha256:
            modified.append(key)
    return DriftResult(modified=tuple(sorted(modified)), missing=tuple(sorted(missing)))


# END OF FILE
