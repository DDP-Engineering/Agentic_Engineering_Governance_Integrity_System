#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file transaction.py
@brief Authenticated file-transaction staging, rollback, and crash recovery.
@details Version-2 transaction state is parsed into closed-schema typed models,
         authenticated with a WAEGIS-home key, and matched to a separately
         protected ownership record before any repository destination changes.
         Backups are content-bound to their destinations and every transaction
         storage object is checked without following links or reparse points.
@details Repository-scoped advisory locking serializes WAEGIS transaction
         application and recovery. Cleanup removes only individually validated
         transaction files and directories; it never recursively deletes a
         state-provided path.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Iterator, Mapping

from .engine.journal import waegis_home
from .payload.manifest import ManifestError, normalize_managed_path, resolve_managed_path

# CONSTANTS

TRANSACTION_DIRECTORY = ".agentic/.waegis-transactions"
TRANSACTION_VERSION = 2
OWNERSHIP_VERSION = 1
MAX_TRANSACTION_ENTRIES = 10_000
MAX_STATE_BYTES = 8 * 1024 * 1024

_AUTH_KEY_NAME = "transaction-auth.key"
_OWNERSHIP_DIRECTORY = "transaction-ownership"
_LOCK_DIRECTORY = "transaction-locks"
_STATE_NAME = "state.json"
_BACKUP_DIRECTORY = "backups"
_PHASES = frozenset({"staged", "applying", "verified", "committed", "rolled-back"})
_TERMINAL_PHASES = frozenset({"committed", "rolled-back"})
_TRANSITIONS = {
    "staged": frozenset({"applying", "rolled-back"}),
    "applying": frozenset({"verified", "rolled-back"}),
    "verified": frozenset({"committed", "rolled-back"}),
    "committed": frozenset(),
    "rolled-back": frozenset(),
}
_STATE_KEYS = frozenset(
    {
        "transaction_version",
        "id",
        "command",
        "phase",
        "created_at",
        "entries",
        "key_id",
        "mac",
    }
)
_ENTRY_KEYS = frozenset(
    {
        "path",
        "existed",
        "backup",
        "backup_size",
        "backup_sha256",
    }
)
_OWNERSHIP_KEYS = frozenset(
    {
        "ownership_version",
        "transaction_id",
        "repository_id",
        "operation_digest",
        "terminal_phase",
        "key_id",
        "mac",
    }
)
_TRANSACTION_ID_RE = re.compile(r"\A\d{8}T\d{6}Z-[0-9a-f]{8}\Z")
_COMMAND_RE = re.compile(r"\A[a-z][a-z0-9-]{0,63}\Z")
_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_KEY_ID_RE = re.compile(r"\A[0-9a-f]{16}\Z")


# DATA MODELS / TYPEDEFINITIONS


class TransactionError(RuntimeError):
    """
    @brief Base class for transaction integrity and lifecycle failures.
    """


class TransactionStateError(TransactionError, ValueError):
    """
    @brief Persisted transaction state cannot be safely trusted.
    """


class TransactionRollbackError(TransactionError):
    """
    @brief Rollback did not completely restore the declared operation set.
    """


class TransactionCleanupError(TransactionError):
    """
    @brief Terminal state is durable but transaction storage cleanup failed.
    """


@dataclass(frozen=True)
class TransactionEntry:
    """
    @brief One authenticated destination and its original-content backup.
    """

    path: str
    existed: bool
    backup: str | None
    backup_size: int | None
    backup_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        """@brief Return the closed-schema JSON representation."""
        return {
            "path": self.path,
            "existed": self.existed,
            "backup": self.backup,
            "backup_size": self.backup_size,
            "backup_sha256": self.backup_sha256,
        }


@dataclass(frozen=True)
class TransactionState:
    """
    @brief Fully validated and authenticated transaction state.
    """

    transaction_version: int
    transaction_id: str
    command: str
    phase: str
    created_at: str
    entries: tuple[TransactionEntry, ...]
    key_id: str
    mac: str

    def unsigned_dict(self) -> dict[str, Any]:
        """@brief Return every authenticated state field except the MAC."""
        return {
            "transaction_version": self.transaction_version,
            "id": self.transaction_id,
            "command": self.command,
            "phase": self.phase,
            "created_at": self.created_at,
            "entries": [entry.to_dict() for entry in self.entries],
            "key_id": self.key_id,
        }

    def to_dict(self) -> dict[str, Any]:
        """@brief Return the complete closed-schema state document."""
        return {**self.unsigned_dict(), "mac": self.mac}

    def operation_dict(self) -> dict[str, Any]:
        """@brief Return the immutable operation set bound by ownership state."""
        return {
            "transaction_version": self.transaction_version,
            "id": self.transaction_id,
            "command": self.command,
            "created_at": self.created_at,
            "entries": [entry.to_dict() for entry in self.entries],
            "key_id": self.key_id,
        }


@dataclass(frozen=True)
class OwnershipRecord:
    """
    @brief Separately protected binding between a repository and operation set.
    """

    ownership_version: int
    transaction_id: str
    repository_id: str
    operation_digest: str
    terminal_phase: str | None
    key_id: str
    mac: str

    def unsigned_dict(self) -> dict[str, Any]:
        """@brief Return every authenticated ownership field except the MAC."""
        return {
            "ownership_version": self.ownership_version,
            "transaction_id": self.transaction_id,
            "repository_id": self.repository_id,
            "operation_digest": self.operation_digest,
            "terminal_phase": self.terminal_phase,
            "key_id": self.key_id,
        }

    def to_dict(self) -> dict[str, Any]:
        """@brief Return the complete ownership document."""
        return {**self.unsigned_dict(), "mac": self.mac}


class _RepositoryLock:
    """
    @brief Cross-platform advisory lock held for one repository transaction.
    """

    def __init__(self, repo: Path, auth_home: Path | None = None) -> None:
        """@brief Construct an unacquired repository lock."""
        self.repo = repo.resolve()
        self.path = (
            _auth_home(auth_home)
            / _LOCK_DIRECTORY
            / f"{_repository_id(self.repo)}.lock"
        )
        self.handle: BinaryIO | None = None

    def acquire(self) -> "_RepositoryLock":
        """
        @brief Acquire the repository lock, blocking competing WAEGIS writers.
        @return This acquired lock.
        @exception OSError If the lock cannot be created or acquired.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.path, flags, 0o600)
        handle = os.fdopen(descriptor, "r+b", buffering=0)
        try:
            if self.path.is_symlink() or _is_link_like(self.path):
                raise OSError(f"transaction lock is link-like: {self.path}")
            if os.name == "nt":
                import msvcrt

                if self.path.stat().st_size == 0:
                    handle.write(b"\0")
                    handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except BaseException:
            handle.close()
            raise
        self.handle = handle
        return self

    def release(self) -> None:
        """
        @brief Release the repository lock if held.
        @return None.
        """
        handle = self.handle
        if handle is None:
            return
        self.handle = None
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __enter__(self) -> "_RepositoryLock":
        """@brief Acquire and return this lock."""
        return self.acquire()

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        """@brief Release this lock."""
        self.release()


# LOCAL HELPERS


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """@brief Serialize an authenticated mapping deterministically."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mac(key: bytes, payload: Mapping[str, Any]) -> str:
    """@brief Return the HMAC-SHA-256 of a canonical mapping."""
    return hmac.new(key, _canonical_bytes(payload), hashlib.sha256).hexdigest()


def _digest(payload: Mapping[str, Any]) -> str:
    """@brief Return the SHA-256 digest of a canonical mapping."""
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _repository_id(repo: Path) -> str:
    """@brief Return a stable local identity for one resolved repository path."""
    normalized = os.path.normcase(str(repo.resolve()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _auth_home(home: Path | None) -> Path:
    """@brief Resolve the protected local transaction-authentication home."""
    return (home if home is not None else waegis_home()).resolve()


def _auth_key(home: Path | None, *, create: bool) -> bytes:
    """
    @brief Load or exclusively create the WAEGIS transaction HMAC key.
    @return Exactly 32 random bytes.
    @exception TransactionStateError If the key is absent or unsafe.
    """
    base = _auth_home(home)
    path = base / _AUTH_KEY_NAME
    if create:
        base.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(base, 0o700)
        except OSError:
            if os.name != "nt":
                raise
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(secrets.token_bytes(32))
                handle.flush()
                os.fsync(handle.fileno())
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise TransactionStateError(
            "transaction authentication key is unavailable; automatic recovery is refused"
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or _is_link_like(path):
        raise TransactionStateError("transaction authentication key is not a regular file")
    if os.name != "nt" and metadata.st_mode & 0o077:
        raise TransactionStateError("transaction authentication key permissions are too broad")
    data = path.read_bytes()
    if len(data) != 32:
        raise TransactionStateError("transaction authentication key has an invalid length")
    return data


def _key_id(key: bytes) -> str:
    """@brief Return the non-secret identifier of one authentication key."""
    return hashlib.sha256(key).hexdigest()[:16]


def _ownership_path(
    repo: Path,
    transaction_id: str,
    home: Path | None,
) -> Path:
    """@brief Return the protected ownership-record path for a transaction."""
    return (
        _auth_home(home)
        / _OWNERSHIP_DIRECTORY
        / _repository_id(repo)
        / f"{transaction_id}.json"
    )


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    """
    @brief Exclusively create and atomically replace one JSON document.
    @return None.
    @exception OSError If persistence fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(raw_temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _fsync_directory(directory: Path) -> None:
    """@brief Best-effort flush of directory metadata on POSIX."""
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _is_link_like(path: Path) -> bool:
    """
    @brief Detect a symbolic link, junction, or other Windows reparse point.
    @return True when the object must not be followed.
    @exception OSError If metadata cannot be read.
    """
    if path.is_symlink():
        return True
    metadata = path.lstat()
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _regular_metadata(path: Path, *, label: str) -> os.stat_result:
    """@brief Return non-following metadata for a required regular file."""
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise TransactionStateError(f"{label} is missing") from exc
    if _is_link_like(path) or not stat.S_ISREG(metadata.st_mode):
        raise TransactionStateError(f"{label} is not a regular file")
    return metadata


def _directory_metadata(path: Path, *, label: str) -> os.stat_result:
    """@brief Return non-following metadata for a required real directory."""
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise TransactionStateError(f"{label} is missing") from exc
    if _is_link_like(path) or not stat.S_ISDIR(metadata.st_mode):
        raise TransactionStateError(f"{label} is not a real directory")
    return metadata


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    """@brief Read one resource-bounded JSON object from a regular file."""
    metadata = _regular_metadata(path, label=label)
    if metadata.st_size > MAX_STATE_BYTES:
        raise TransactionStateError(f"{label} exceeds the supported size limit")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise TransactionStateError(f"{label} is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise TransactionStateError(f"{label} must contain a JSON object")
    return raw


def _strict_int(value: Any, *, label: str, minimum: int = 0) -> int:
    """@brief Validate an exact JSON integer, excluding booleans."""
    if type(value) is not int or value < minimum:
        raise TransactionStateError(f"{label} must be an integer >= {minimum}")
    return value


def _strict_string(value: Any, *, label: str, pattern: re.Pattern[str] | None = None) -> str:
    """@brief Validate an exact string and optional full-match contract."""
    if type(value) is not str or (pattern is not None and pattern.fullmatch(value) is None):
        raise TransactionStateError(f"{label} has an invalid string value")
    return value


def _parse_created_at(value: Any) -> str:
    """@brief Validate the canonical second-precision UTC timestamp."""
    text = _strict_string(value, label="created_at")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TransactionStateError("created_at has an invalid timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise TransactionStateError("created_at is not canonical")
    return text


def _parse_entry(raw: Any, *, index: int) -> TransactionEntry:
    """
    @brief Parse one exact transaction-entry mapping.
    """
    if type(raw) is not dict or set(raw) != _ENTRY_KEYS:
        raise TransactionStateError(f"entry {index} does not use the exact supported keys")
    path_value = raw["path"]
    if type(path_value) is not str:
        raise TransactionStateError(f"entry {index} path must be a string")
    try:
        path = normalize_managed_path(path_value)
    except ManifestError as exc:
        raise TransactionStateError(f"entry {index} has an unsafe destination path") from exc
    if path != path_value:
        raise TransactionStateError(f"entry {index} destination path is not canonical")
    if type(raw["existed"]) is not bool:
        raise TransactionStateError(f"entry {index} existed must be a boolean")
    existed = raw["existed"]
    if existed:
        # The exact-equality check below subsumes any pattern match.
        backup = _strict_string(raw["backup"], label=f"entry {index} backup")
        if backup != f"{index:06d}.bak":
            raise TransactionStateError(f"entry {index} backup is not the generated reference")
        backup_size = _strict_int(raw["backup_size"], label=f"entry {index} backup_size")
        backup_sha256 = _strict_string(
            raw["backup_sha256"],
            label=f"entry {index} backup_sha256",
            pattern=_SHA256_RE,
        )
    else:
        if any(raw[key] is not None for key in ("backup", "backup_size", "backup_sha256")):
            raise TransactionStateError(f"entry {index} has backup metadata for a new file")
        backup = None
        backup_size = None
        backup_sha256 = None
    return TransactionEntry(path, existed, backup, backup_size, backup_sha256)


def _parse_state(raw: Mapping[str, Any], *, directory_name: str, key: bytes) -> TransactionState:
    """@brief Parse and authenticate a complete version-2 state document."""
    if set(raw) != _STATE_KEYS:
        raise TransactionStateError("transaction state does not use the exact supported keys")
    version = _strict_int(raw["transaction_version"], label="transaction_version")
    if version != TRANSACTION_VERSION:
        if version == 1:
            raise TransactionStateError(
                "legacy transaction version 1 lacks authenticated ownership metadata; "
                "automatic recovery is refused and the transaction directory must be reviewed manually"
            )
        raise TransactionStateError(f"unsupported transaction version: {version}")
    transaction_id = _strict_string(raw["id"], label="id", pattern=_TRANSACTION_ID_RE)
    if transaction_id != directory_name:
        raise TransactionStateError("transaction id does not match its containing directory")
    command = _strict_string(raw["command"], label="command", pattern=_COMMAND_RE)
    phase = _strict_string(raw["phase"], label="phase")
    if phase not in _PHASES:
        raise TransactionStateError("transaction phase is unsupported")
    created_at = _parse_created_at(raw["created_at"])
    entries_raw = raw["entries"]
    if type(entries_raw) is not list:
        raise TransactionStateError("entries must be a list")
    if not entries_raw or len(entries_raw) > MAX_TRANSACTION_ENTRIES:
        raise TransactionStateError(
            f"entries must contain between 1 and {MAX_TRANSACTION_ENTRIES} items"
        )
    entries = tuple(_parse_entry(item, index=index) for index, item in enumerate(entries_raw))
    folded: dict[str, str] = {}
    backups: set[str] = set()
    for entry in entries:
        prior = folded.get(entry.path.casefold())
        if prior is not None:
            raise TransactionStateError(
                f"duplicate or case-colliding destinations: {prior!r} and {entry.path!r}"
            )
        folded[entry.path.casefold()] = entry.path
        if entry.backup is not None and entry.backup in backups:
            raise TransactionStateError("duplicate backup reference")
        if entry.backup is not None:
            backups.add(entry.backup)
    key_id = _strict_string(raw["key_id"], label="key_id", pattern=_KEY_ID_RE)
    if key_id != _key_id(key):
        raise TransactionStateError("transaction authentication key does not match")
    supplied_mac = _strict_string(raw["mac"], label="mac", pattern=_SHA256_RE)
    unsigned = {name: raw[name] for name in _STATE_KEYS if name != "mac"}
    if not hmac.compare_digest(supplied_mac, _mac(key, unsigned)):
        raise TransactionStateError("transaction state authentication failed")
    return TransactionState(
        transaction_version=version,
        transaction_id=transaction_id,
        command=command,
        phase=phase,
        created_at=created_at,
        entries=entries,
        key_id=key_id,
        mac=supplied_mac,
    )


def _sign_state(state: TransactionState, key: bytes) -> TransactionState:
    """@brief Return state with an HMAC matching its current fields."""
    return replace(state, mac=_mac(key, state.unsigned_dict()))


def _parse_ownership(
    raw: Mapping[str, Any],
    *,
    state: TransactionState,
    repo: Path,
    key: bytes,
) -> OwnershipRecord:
    """@brief Parse and authenticate a separately protected ownership record."""
    if set(raw) != _OWNERSHIP_KEYS:
        raise TransactionStateError("transaction ownership record has unsupported keys")
    version = _strict_int(raw["ownership_version"], label="ownership_version")
    if version != OWNERSHIP_VERSION:
        raise TransactionStateError("transaction ownership version is unsupported")
    transaction_id = _strict_string(
        raw["transaction_id"],
        label="ownership transaction_id",
        pattern=_TRANSACTION_ID_RE,
    )
    repository_id = _strict_string(
        raw["repository_id"],
        label="ownership repository_id",
        pattern=_SHA256_RE,
    )
    operation_digest = _strict_string(
        raw["operation_digest"],
        label="ownership operation_digest",
        pattern=_SHA256_RE,
    )
    terminal_value = raw["terminal_phase"]
    if terminal_value is not None and terminal_value not in _TERMINAL_PHASES:
        raise TransactionStateError("ownership terminal_phase is invalid")
    terminal_phase = terminal_value
    key_id = _strict_string(raw["key_id"], label="ownership key_id", pattern=_KEY_ID_RE)
    supplied_mac = _strict_string(raw["mac"], label="ownership mac", pattern=_SHA256_RE)
    unsigned = {name: raw[name] for name in _OWNERSHIP_KEYS if name != "mac"}
    if not hmac.compare_digest(supplied_mac, _mac(key, unsigned)):
        raise TransactionStateError("transaction ownership authentication failed")
    if transaction_id != state.transaction_id:
        raise TransactionStateError("transaction ownership id does not match state")
    if repository_id != _repository_id(repo):
        raise TransactionStateError("transaction ownership belongs to another repository")
    if operation_digest != _digest(state.operation_dict()):
        raise TransactionStateError("transaction operation set does not match ownership")
    if key_id != state.key_id or key_id != _key_id(key):
        raise TransactionStateError("transaction ownership key does not match state")
    return OwnershipRecord(
        version,
        transaction_id,
        repository_id,
        operation_digest,
        terminal_phase,
        key_id,
        supplied_mac,
    )


def _validate_location(repo: Path, directory: Path) -> tuple[Path, Path, Path]:
    """@brief Prove a transaction and its storage directories are local and real."""
    root = resolve_managed_path(repo, TRANSACTION_DIRECTORY)
    _directory_metadata(root, label="transaction root")
    candidate = Path(directory)
    if not candidate.is_absolute():
        candidate = repo / candidate
    try:
        if candidate.parent.resolve(strict=True) != root.resolve(strict=True):
            raise TransactionStateError("transaction directory is not directly beneath the transaction root")
    except (FileNotFoundError, OSError) as exc:
        raise TransactionStateError("transaction directory containment cannot be established") from exc
    _directory_metadata(candidate, label="transaction directory")
    if candidate.resolve(strict=True).parent != root.resolve(strict=True):
        raise TransactionStateError("transaction directory escapes the transaction root")
    state_path = candidate / _STATE_NAME
    backups_path = candidate / _BACKUP_DIRECTORY
    _regular_metadata(state_path, label="transaction state file")
    return candidate, state_path, backups_path


def _hash_regular_file(path: Path, *, label: str) -> tuple[int, str]:
    """@brief Hash a stable regular file without following a link-like object."""
    before = _regular_metadata(path, label=label)
    digest = hashlib.sha256()
    size = 0
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            raise TransactionStateError(f"{label} changed while it was opened")
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            size += len(block)
            digest.update(block)
    finally:
        os.close(descriptor)
    after = _regular_metadata(path, label=label)
    if (after.st_dev, after.st_ino, after.st_size) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
    ):
        raise TransactionStateError(f"{label} changed while it was hashed")
    return size, digest.hexdigest()


def _validate_storage(
    directory: Path,
    state: TransactionState,
) -> None:
    """@brief Validate every owned storage object and backup before recovery."""
    allowed_children = {_STATE_NAME, _BACKUP_DIRECTORY}
    children = {item.name: item for item in directory.iterdir()}
    unknown = set(children) - allowed_children
    if unknown:
        raise TransactionStateError(
            "transaction directory contains unexpected objects: " + ", ".join(sorted(unknown))
        )
    expected = {entry.backup for entry in state.entries if entry.backup is not None}
    backups_path = directory / _BACKUP_DIRECTORY
    if backups_path.exists() or backups_path.is_symlink():
        _directory_metadata(backups_path, label="transaction backup directory")
        actual_items = {item.name: item for item in backups_path.iterdir()}
    elif state.phase in _TERMINAL_PHASES:
        actual_items = {}
    else:
        raise TransactionStateError("transaction backup directory is missing")
    unexpected = set(actual_items) - expected
    if unexpected:
        raise TransactionStateError(
            "transaction contains unowned backup files: " + ", ".join(sorted(unexpected))
        )
    missing = expected - set(actual_items)
    if missing and state.phase not in _TERMINAL_PHASES:
        raise TransactionStateError(
            "transaction is missing required backup files: " + ", ".join(sorted(missing))
        )
    for entry in state.entries:
        if entry.backup is None or entry.backup not in actual_items:
            continue
        backup = actual_items[entry.backup]
        size, digest = _hash_regular_file(backup, label=f"backup {entry.backup}")
        if size != entry.backup_size or digest != entry.backup_sha256:
            raise TransactionStateError(
                f"backup {entry.backup} does not match its authenticated content metadata"
            )


def _validate_destinations(repo: Path, state: TransactionState) -> dict[str, Path]:
    """@brief Validate every rollback target type before any target is mutated."""
    targets: dict[str, Path] = {}
    for entry in state.entries:
        try:
            target = resolve_managed_path(repo, entry.path)
        except ManifestError as exc:
            raise TransactionRollbackError(
                f"transaction destination is no longer safely contained: {entry.path!r}"
            ) from exc
        parent = target.parent
        try:
            parent_metadata = parent.lstat()
        except FileNotFoundError:
            if entry.existed:
                raise TransactionRollbackError(
                    f"parent directory disappeared for original file: {entry.path!r}"
                )
            targets[entry.path] = target
            continue
        if _is_link_like(parent) or not stat.S_ISDIR(parent_metadata.st_mode):
            raise TransactionRollbackError(
                f"transaction destination parent is not a real directory: {entry.path!r}"
            )
        try:
            metadata = target.lstat()
        except FileNotFoundError:
            targets[entry.path] = target
            continue
        if _is_link_like(target) or not stat.S_ISREG(metadata.st_mode):
            raise TransactionRollbackError(
                f"transaction destination became a non-regular object: {entry.path!r}"
            )
        targets[entry.path] = target
    return targets


def _copy_backup_exact(backup: Path, target: Path, entry: TransactionEntry) -> None:
    """@brief Atomically restore one backup to the exact intended pathname."""
    target.parent.mkdir(parents=False, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{target.name}.waegis-restore.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(raw_temporary)
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        source_descriptor = os.open(backup, flags)
        digest = hashlib.sha256()
        size = 0
        try:
            with os.fdopen(descriptor, "wb") as output:
                while True:
                    block = os.read(source_descriptor, 1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    size += len(block)
                    digest.update(block)
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.close(source_descriptor)
        if size != entry.backup_size or digest.hexdigest() != entry.backup_sha256:
            raise TransactionRollbackError(
                f"backup changed during restore for {entry.path!r}"
            )
        try:
            metadata = target.lstat()
        except FileNotFoundError:
            pass
        else:
            if _is_link_like(target) or not stat.S_ISREG(metadata.st_mode):
                raise TransactionRollbackError(
                    f"transaction destination changed type during restore: {entry.path!r}"
                )
        os.replace(temporary, target)
        _fsync_directory(target.parent)
        restored_size, restored_digest = _hash_regular_file(
            target,
            label=f"restored destination {entry.path}",
        )
        if restored_size != entry.backup_size or restored_digest != entry.backup_sha256:
            raise TransactionRollbackError(
                f"restored destination verification failed: {entry.path!r}"
            )
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _stage_backup(target: Path, backup: Path) -> tuple[int, str]:
    """@brief Exclusively copy and content-verify one original regular file."""
    before = _regular_metadata(target, label=f"transaction destination {target}")
    source_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        source_flags |= os.O_NOFOLLOW
    source_descriptor = os.open(target, source_flags)
    destination_descriptor = os.open(
        backup,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    digest = hashlib.sha256()
    size = 0
    try:
        opened = os.fstat(source_descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            raise TransactionStateError("transaction destination changed while staging")
        with os.fdopen(destination_descriptor, "wb") as output:
            while True:
                block = os.read(source_descriptor, 1024 * 1024)
                if not block:
                    break
                output.write(block)
                size += len(block)
                digest.update(block)
            output.flush()
            os.fsync(output.fileno())
    finally:
        os.close(source_descriptor)
    after = _regular_metadata(target, label=f"transaction destination {target}")
    if (after.st_dev, after.st_ino, after.st_size) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
    ):
        raise TransactionStateError("transaction destination changed while staging")
    backup_size, backup_digest = _hash_regular_file(backup, label=f"staged backup {backup.name}")
    if backup_size != size or backup_digest != digest.hexdigest():
        raise TransactionStateError("staged backup verification failed")
    return size, digest.hexdigest()


def _scan_transaction_directories(repo: Path) -> tuple[Path, ...]:
    """@brief Enumerate real direct-child transaction directories safely."""
    root = resolve_managed_path(repo, TRANSACTION_DIRECTORY)
    try:
        metadata = root.lstat()
    except FileNotFoundError:
        return ()
    if _is_link_like(root) or not stat.S_ISDIR(metadata.st_mode):
        raise TransactionStateError("repository transaction root is not a real directory")
    directories: list[Path] = []
    for candidate in sorted(root.iterdir(), key=lambda item: item.name):
        if _is_link_like(candidate):
            raise TransactionStateError(
                f"link-like object found beneath transaction root: {candidate.name!r}"
            )
        metadata = candidate.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            raise TransactionStateError(
                f"unexpected non-directory beneath transaction root: {candidate.name!r}"
            )
        state_path = candidate / _STATE_NAME
        if state_path.is_symlink():
            raise TransactionStateError(
                f"transaction state file is link-like: {candidate.name!r}"
            )
        if not state_path.exists():
            continue
        directories.append(candidate)
    return tuple(directories)


# EXPORTED FUNCTIONS / PUBLIC API


class FileTransaction:
    """
    @brief One persistent authenticated repository-local file transaction.
    """

    def __init__(
        self,
        repo: Path,
        directory: Path,
        state: TransactionState,
        *,
        key: bytes,
        auth_home: Path | None,
        lock: _RepositoryLock | None,
    ) -> None:
        """
        @brief Construct from already validated transaction components.
        @return None.
        """
        self.repo = repo.resolve()
        self.directory = directory
        self._model = state
        self._key = key
        self._auth_home = auth_home
        self._lock = lock

    @property
    def state(self) -> dict[str, Any]:
        """@brief Return a compatibility copy of the authenticated state."""
        return self._model.to_dict()

    @property
    def phase(self) -> str:
        """@brief Return the durable transaction phase."""
        return self._model.phase

    @classmethod
    def begin(
        cls,
        repo: Path,
        *,
        command: str,
        paths: Iterable[str],
        auth_home: Path | None = None,
    ) -> "FileTransaction":
        """
        @brief Stage authenticated backups and persist ownership before writes.
        @return Ready transaction in ``staged`` phase holding the repository lock.
        @exception TransactionError If staging or authentication fails.
        @exception OSError If persistence fails.
        @exception ManifestError If a destination path escapes or crosses a
                   symlink into the repository root while resolving entries.
        """
        repo = repo.resolve()
        if _COMMAND_RE.fullmatch(command) is None:
            raise TransactionStateError(
                "transaction command must match [a-z][a-z0-9-]{0,63}"
            )
        normalized: list[str] = []
        folded: dict[str, str] = {}
        for raw in paths:
            try:
                relative = normalize_managed_path(raw)
            except ManifestError as exc:
                raise TransactionStateError("transaction contains an unsafe destination path") from exc
            prior = folded.get(relative.casefold())
            if prior is not None:
                raise TransactionStateError(
                    f"duplicate or case-colliding destinations: {prior!r} and {relative!r}"
                )
            folded[relative.casefold()] = relative
            normalized.append(relative)
        normalized.sort()
        if not normalized or len(normalized) > MAX_TRANSACTION_ENTRIES:
            raise TransactionStateError(
                f"transactions require between 1 and {MAX_TRANSACTION_ENTRIES} destinations"
            )
        lock = _RepositoryLock(repo, auth_home).acquire()
        directory: Path | None = None
        ownership_path: Path | None = None
        staged_backups: list[Path] = []
        try:
            if _scan_transaction_directories(repo):
                raise TransactionStateError(
                    "existing transaction state must be recovered before a new transaction begins"
                )
            key = _auth_key(auth_home, create=True)
            transaction_id = (
                datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                + "-"
                + secrets.token_hex(4)
            )
            root = resolve_managed_path(repo, TRANSACTION_DIRECTORY)
            root.mkdir(parents=True, exist_ok=True)
            directory = root / transaction_id
            directory.mkdir(mode=0o700, exist_ok=False)
            backups = directory / _BACKUP_DIRECTORY
            backups.mkdir(mode=0o700, exist_ok=False)
            entries: list[TransactionEntry] = []
            for index, relative in enumerate(normalized):
                target = resolve_managed_path(repo, relative)
                try:
                    metadata = target.lstat()
                except FileNotFoundError:
                    entries.append(TransactionEntry(relative, False, None, None, None))
                    continue
                if _is_link_like(target) or not stat.S_ISREG(metadata.st_mode):
                    raise TransactionStateError(
                        f"transaction destination is not a regular file: {relative!r}"
                    )
                backup_name = f"{index:06d}.bak"
                backup_path = backups / backup_name
                size, digest = _stage_backup(target, backup_path)
                staged_backups.append(backup_path)
                entries.append(
                    TransactionEntry(relative, True, backup_name, size, digest)
                )
            created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            state = TransactionState(
                TRANSACTION_VERSION,
                transaction_id,
                command,
                "staged",
                created_at,
                tuple(entries),
                _key_id(key),
                "",
            )
            state = _sign_state(state, key)
            ownership_unsigned = {
                "ownership_version": OWNERSHIP_VERSION,
                "transaction_id": transaction_id,
                "repository_id": _repository_id(repo),
                "operation_digest": _digest(state.operation_dict()),
                "terminal_phase": None,
                "key_id": state.key_id,
            }
            ownership = OwnershipRecord(
                OWNERSHIP_VERSION,
                transaction_id,
                ownership_unsigned["repository_id"],
                ownership_unsigned["operation_digest"],
                None,
                state.key_id,
                _mac(key, ownership_unsigned),
            )
            ownership_path = _ownership_path(repo, transaction_id, auth_home)
            _write_json_atomic(ownership_path, ownership.to_dict())
            _write_json_atomic(directory / _STATE_NAME, state.to_dict())
            return cls(
                repo,
                directory,
                state,
                key=key,
                auth_home=auth_home,
                lock=lock,
            )
        except BaseException as begin_error:
            if directory is not None and directory.exists():
                try:
                    for backup in reversed(staged_backups):
                        if backup.exists() and stat.S_ISREG(backup.lstat().st_mode):
                            backup.unlink()
                    state_path = directory / _STATE_NAME
                    if state_path.exists() and stat.S_ISREG(state_path.lstat().st_mode):
                        state_path.unlink()
                    backups_path = directory / _BACKUP_DIRECTORY
                    if backups_path.exists():
                        backups_path.rmdir()
                    directory.rmdir()
                except OSError as cleanup_error:
                    begin_error.add_note(
                        "transaction begin cleanup left residue under "
                        f"{directory}: {cleanup_error}"
                    )
            if ownership_path is not None:
                try:
                    ownership_path.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    begin_error.add_note(
                        "transaction begin cleanup could not remove ownership "
                        f"record {ownership_path}: {cleanup_error}"
                    )
            lock.release()
            raise

    @classmethod
    def load(
        cls,
        repo: Path,
        directory: Path,
        *,
        auth_home: Path | None = None,
    ) -> "FileTransaction":
        """
        @brief Load, strictly validate, authenticate, and ownership-bind state.
        @return Loaded transaction without acquiring a mutation lock.
        @exception TransactionStateError If any trust check fails.
        @exception OSError If trusted local state cannot be read.
        """
        repo = repo.resolve()
        safe_directory, state_path, _backups = _validate_location(repo, directory)
        raw = _read_json_object(state_path, label="transaction state")
        if raw.get("transaction_version") == 1:
            raise TransactionStateError(
                "legacy transaction version 1 lacks authenticated ownership metadata; "
                "automatic recovery is refused and the transaction directory must be reviewed manually"
            )
        key = _auth_key(auth_home, create=False)
        state = _parse_state(raw, directory_name=safe_directory.name, key=key)
        ownership_path = _ownership_path(repo, state.transaction_id, auth_home)
        ownership_raw = _read_json_object(
            ownership_path,
            label="transaction ownership record",
        )
        ownership = _parse_ownership(
            ownership_raw,
            state=state,
            repo=repo,
            key=key,
        )
        if ownership.terminal_phase is None and state.phase in _TERMINAL_PHASES:
            raise TransactionStateError(
                "terminal transaction state is not bound by its ownership record"
            )
        if ownership.terminal_phase is not None:
            if state.phase in _TERMINAL_PHASES and state.phase != ownership.terminal_phase:
                raise TransactionStateError(
                    "transaction terminal phase conflicts with its ownership record"
                )
            if state.phase not in _TERMINAL_PHASES:
                state = _sign_state(
                    replace(
                        state,
                        phase=ownership.terminal_phase,
                        mac="",
                    ),
                    key,
                )
        _validate_storage(safe_directory, state)
        return cls(
            repo,
            safe_directory,
            state,
            key=key,
            auth_home=auth_home,
            lock=None,
        )

    def mark(self, phase: str) -> None:
        """
        @brief Persist an authenticated legal transaction phase transition.
        @return None.
        @exception TransactionStateError On an unknown or illegal transition.
        @exception OSError If persisting the new phase fails.
        """
        if phase not in _PHASES:
            raise TransactionStateError(f"invalid transaction phase: {phase!r}")
        if phase == self._model.phase:
            return
        if phase not in _TRANSITIONS[self._model.phase]:
            raise TransactionStateError(
                f"invalid transaction phase transition: {self._model.phase!r} -> {phase!r}"
            )
        if phase in _TERMINAL_PHASES:
            self._bind_terminal_ownership(phase)
        self._model = _sign_state(replace(self._model, phase=phase, mac=""), self._key)
        _write_json_atomic(self.directory / _STATE_NAME, self._model.to_dict())

    def _bind_terminal_ownership(self, phase: str) -> None:
        """
        @brief Persist the authoritative terminal outcome outside the repository.
        @param[in] phase Either ``committed`` or ``rolled-back``.
        @return None.
        @exception TransactionStateError If ownership is invalid or conflicting.
        """
        ownership_path = _ownership_path(
            self.repo,
            self._model.transaction_id,
            self._auth_home,
        )
        ownership_raw = _read_json_object(
            ownership_path,
            label="transaction ownership record",
        )
        ownership = _parse_ownership(
            ownership_raw,
            state=self._model,
            repo=self.repo,
            key=self._key,
        )
        if ownership.terminal_phase is not None:
            if ownership.terminal_phase != phase:
                raise TransactionStateError(
                    "transaction ownership already records a conflicting terminal phase"
                )
            return
        updated = replace(ownership, terminal_phase=phase, mac="")
        updated = replace(updated, mac=_mac(self._key, updated.unsigned_dict()))
        _write_json_atomic(ownership_path, updated.to_dict())

    def rollback(self, *, _release_lock: bool = True) -> None:
        """
        @brief Revalidate all state and destinations, then restore exact paths.
        @return None after complete restoration and cleanup.
        @exception TransactionRollbackError If restoration is unsafe or incomplete.
        @exception TransactionCleanupError If rollback is durable but cleanup fails.
        @exception TransactionStateError If reloading state fails authentication or
                   binding before restoration is attempted.
        @param[in] _release_lock Internal recovery coordination flag.
        """
        acquired_here = False
        if self._lock is None:
            self._lock = _RepositoryLock(self.repo, self._auth_home).acquire()
            acquired_here = True
        try:
            validated = FileTransaction.load(
                self.repo,
                self.directory,
                auth_home=self._auth_home,
            )
            self._model = validated._model
            if self.phase == "committed":
                raise TransactionRollbackError("a committed transaction cannot be rolled back")
            if self.phase == "rolled-back":
                self.cleanup()
                return
            targets = _validate_destinations(self.repo, self._model)
            backups = self.directory / _BACKUP_DIRECTORY
            for entry in reversed(self._model.entries):
                target = targets[entry.path]
                if entry.existed:
                    if entry.backup is None:
                        raise TransactionRollbackError(
                            f"authenticated backup reference is missing for {entry.path!r}"
                        )
                    _copy_backup_exact(backups / entry.backup, target, entry)
                else:
                    try:
                        metadata = target.lstat()
                    except FileNotFoundError:
                        continue
                    if _is_link_like(target) or not stat.S_ISREG(metadata.st_mode):
                        raise TransactionRollbackError(
                            f"new-file destination became non-regular: {entry.path!r}"
                        )
                    target.unlink()
                    _fsync_directory(target.parent)
            self.mark("rolled-back")
            try:
                self.cleanup()
            except Exception as exc:
                raise TransactionCleanupError(
                    f"transaction {self._model.transaction_id} rolled back but cleanup failed"
                ) from exc
        except TransactionError:
            raise
        except OSError as exc:
            raise TransactionRollbackError(
                f"transaction {self._model.transaction_id} rollback failed; state was retained"
            ) from exc
        finally:
            if _release_lock and (acquired_here or self.phase in _TERMINAL_PHASES):
                self._release_lock()

    def commit(self) -> None:
        """
        @brief Mark committed, then remove only validated transaction storage.
        @return None.
        @exception TransactionCleanupError If commit is durable but cleanup fails.
        @exception TransactionStateError If marking the state committed fails.
        """
        try:
            self.mark("committed")
            try:
                self.cleanup()
            except Exception as exc:
                raise TransactionCleanupError(
                    f"transaction {self._model.transaction_id} committed but cleanup failed"
                ) from exc
        finally:
            self._release_lock()

    def cleanup(self) -> None:
        """
        @brief Remove only authenticated, individually revalidated storage objects.
        @return None.
        @exception TransactionStateError If storage identity changed.
        @exception OSError If exact non-recursive cleanup fails.
        """
        validated = FileTransaction.load(
            self.repo,
            self.directory,
            auth_home=self._auth_home,
        )
        if validated.phase not in _TERMINAL_PHASES:
            raise TransactionStateError("non-terminal transaction storage must be retained")
        backups = self.directory / _BACKUP_DIRECTORY
        if backups.exists():
            for entry in validated._model.entries:
                if entry.backup is None:
                    continue
                backup = backups / entry.backup
                try:
                    _regular_metadata(backup, label=f"backup {entry.backup}")
                except TransactionStateError:
                    if backup.exists() or backup.is_symlink():
                        raise
                    continue
                backup.unlink()
            backups.rmdir()
        state_path = self.directory / _STATE_NAME
        _regular_metadata(state_path, label="transaction state file")
        state_path.unlink()
        self.directory.rmdir()
        ownership = _ownership_path(
            self.repo,
            validated._model.transaction_id,
            self._auth_home,
        )
        _regular_metadata(ownership, label="transaction ownership record")
        ownership.unlink()

    def abandon(self) -> None:
        """
        @brief Release the process lock while retaining non-terminal crash state.
        @details Embedders and deterministic crash tests may use this immediately
                 before terminating or handing recovery to another process.
        @return None.
        @exception OSError If releasing the underlying lock fails.
        """
        self._release_lock()

    def _release_lock(self) -> None:
        """@brief Release this transaction's repository lock if held."""
        lock = self._lock
        self._lock = None
        if lock is not None:
            lock.release()

    def __del__(self) -> None:
        """@brief Best-effort release of the advisory process lock."""
        try:
            self._release_lock()
        except Exception:
            pass


@contextmanager
def payload_transaction(
    repo: Path,
    *,
    command: str,
    paths: Iterable[str],
    auth_home: Path | None = None,
) -> Iterator[FileTransaction]:
    """
    @brief Wrap repository writes in one authenticated rollback journal.
    @param[in] repo Repository root receiving the writes.
    @param[in] command Safe command label matching ``[a-z][a-z0-9-]{0,63}``.
    @param[in] paths Every repository-relative path the block may write.
    @param[in] auth_home Optional protected WAEGIS-home override.
    @return Context manager yielding the staged transaction.
    @exception TransactionError If beginning, marking, or committing fails.
    @exception OSError If persisting transaction state fails.
    @exception ManifestError If a managed destination path is unsafe.
    @exception BaseException Whatever the wrapped block raises, re-raised
               after rollback (wrapped as :class:`TransactionRollbackError`
               if rollback itself fails, except for a
               :class:`KeyboardInterrupt`/:class:`SystemExit`).
    """
    transaction = FileTransaction.begin(
        repo,
        command=command,
        paths=paths,
        auth_home=auth_home,
    )
    transaction.mark("applying")
    try:
        yield transaction
    except BaseException as exc:
        try:
            transaction.rollback()
        except Exception as rollback_exc:
            note = (
                f"transaction rollback failed and authenticated state was retained: "
                f"{rollback_exc}"
            )
            if hasattr(exc, "add_note"):
                exc.add_note(note)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise TransactionRollbackError(note) from exc
        raise
    transaction.mark("verified")
    transaction.commit()


def recover_incomplete_transactions(
    repo: Path,
    *,
    auth_home: Path | None = None,
) -> tuple[str, ...]:
    """
    @brief Validate all discovered state, then recover every non-terminal item.
    @return Recovered transaction ids.
    @details All repository transaction state is validated before the first
             destination mutation. Terminal state is cleanup-only, so a second
             recovery never repeats rollback.
    @exception TransactionStateError If ownership, integrity, schema, or
               containment cannot be established.
    @exception TransactionRollbackError If a destination cannot be restored.
    @exception TransactionCleanupError If a recovered transaction's terminal
               state is durable but cleanup of its storage fails.
    @exception OSError If removing validated terminal transaction storage fails.
    """
    repo = repo.resolve()
    directories = _scan_transaction_directories(repo)
    if not directories:
        return ()
    with _RepositoryLock(repo, auth_home) as recovery_lock:
        directories = _scan_transaction_directories(repo)
        transactions = tuple(
            FileTransaction.load(repo, directory, auth_home=auth_home)
            for directory in directories
        )
        recovered: list[str] = []
        for transaction in transactions:
            if transaction.phase not in _TERMINAL_PHASES:
                transaction._lock = recovery_lock
                transaction.rollback(_release_lock=False)
                transaction._lock = None
                recovered.append(transaction._model.transaction_id)
            else:
                transaction.cleanup()
        return tuple(recovered)


def pending_transaction_ids(
    repo: Path,
    *,
    auth_home: Path | None = None,
) -> tuple[str, ...]:
    """
    @brief Validate and list pending transactions without writing any state.
    @param[in] repo Repository root to inspect.
    @param[in] auth_home Optional protected WAEGIS-home override.
    @return Stable non-terminal transaction identifiers in directory order.
    @exception TransactionStateError If any discovered state is untrusted.
    """
    repo = repo.resolve()
    transactions = tuple(
        FileTransaction.load(repo, directory, auth_home=auth_home)
        for directory in _scan_transaction_directories(repo)
    )
    return tuple(
        transaction._model.transaction_id
        for transaction in transactions
        if transaction.phase not in _TERMINAL_PHASES
    )


# END OF FILE
