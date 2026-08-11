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
@file    transactions.py
@brief   Publish cohesive repository mutations with recovery and concurrency.
@details Uses a repository-local lock and commit-decision recovery bundle.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from aegis.domain.values import RepositoryPath
from aegis.infrastructure.publication import atomic_replace


class RevisionConflict(RuntimeError):
    """@brief Report a stale expected revision or active writer."""


class RecoveryError(RuntimeError):
    """@brief Report malformed or unverifiable transaction recovery state."""


class TransactionCheckpoint(StrEnum):
    """@brief Name fault-injection boundaries in cohesive publication."""

    PREPARED = "prepared"
    COMMIT_DECIDED = "commit_decided"
    FIRST_TARGET_APPLIED = "first_target_applied"
    ALL_TARGETS_APPLIED = "all_targets_applied"


@dataclass(frozen=True, slots=True)
class FileMutation:
    """@brief Describe one create, replacement, or deletion."""

    path: RepositoryPath
    content: bytes | None


def revision_of(content: bytes) -> str:
    """@brief Return the exact-byte optimistic concurrency token."""
    return f"sha256:{sha256(content).hexdigest()}"


class WorkspaceLock:
    """@brief Serialize recovery and publication in one working copy."""

    def __init__(self, path: Path, *, timeout_seconds: float = 0.25) -> None:
        self._path = path
        self._timeout_seconds = timeout_seconds
        self._stream: object | None = None

    def __enter__(self) -> WorkspaceLock:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        stream = self._path.open("a+b")
        if self._path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + self._timeout_seconds
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if time.monotonic() >= deadline:
                    stream.close()
                    raise RevisionConflict("The AEGIS workspace is busy.") from error
                time.sleep(0.01)
        self._stream = stream
        return self

    def __exit__(self, *_: object) -> None:
        stream = self._stream
        if stream is None:
            return
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()
            self._stream = None


class TransactionStore:
    """@brief Own repository-local preparation, commit, and recovery."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.runtime = self._target(".agentic/.runtime")
        self.transactions = self.runtime / "transactions"
        self.lock_path = self.runtime / "write.lock"

    def _target(self, path: str) -> Path:
        canonical = RepositoryPath(path)
        target = self.root.joinpath(*str(canonical).split("/"))
        existing = target if target.exists() else target.parent
        try:
            existing.resolve().relative_to(self.root)
        except ValueError as error:
            raise RecoveryError(f"Unsafe repository path: {path}") from error
        return target

    def _current_revision(self, path: str) -> str | None:
        target = self._target(path)
        if not target.exists():
            return None
        if not target.is_file():
            raise RecoveryError(f"Authoritative target is not a regular file: {path}")
        return revision_of(target.read_bytes())

    @contextmanager
    def locked(self) -> Iterator[None]:
        """@brief Acquire the bounded repository-local publication lock."""
        with WorkspaceLock(self.lock_path):
            yield

    def recover(self) -> None:
        """@brief Recover every prepared transaction before authoritative reads."""
        with self.locked():
            self._recover_locked()

    def _recover_locked(self) -> None:
        if not self.transactions.exists():
            return
        for transaction in sorted(self.transactions.iterdir()):
            if not transaction.is_dir() or not transaction.name.startswith("TXN-"):
                raise RecoveryError(f"Unexpected recovery entry: {transaction}")
            plan_path = transaction / "plan.json"
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                entries = plan["entries"]
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
                KeyError,
                TypeError,
            ) as error:
                raise RecoveryError(f"Malformed recovery plan: {plan_path}") from error
            committed = (
                (transaction / "decision").read_bytes() == b"commit\n"
                if (transaction / "decision").exists()
                else False
            )
            for entry in entries:
                target = self._target(entry["path"])
                selected = "after" if committed else "before"
                exists = entry[f"{selected}_exists"]
                copy_path = transaction / selected / entry["copy"]
                if exists:
                    content = copy_path.read_bytes()
                    if revision_of(content) != entry[f"{selected}_revision"]:
                        raise RecoveryError(
                            f"Recovery bytes failed digest verification: {copy_path}"
                        )
                    atomic_replace(target, content)
                elif target.exists():
                    target.unlink()
            self._verify(transaction, entries, after=committed)
            shutil.rmtree(transaction)

    def _verify(
        self, transaction: Path, entries: list[dict[str, object]], *, after: bool
    ) -> None:
        side = "after" if after else "before"
        for entry in entries:
            actual = self._current_revision(str(entry["path"]))
            expected = entry[f"{side}_revision"] if entry[f"{side}_exists"] else None
            if actual != expected:
                raise RecoveryError(f"Transaction final digest mismatch: {transaction}")

    def publish(
        self,
        mutations: tuple[FileMutation, ...],
        *,
        expected_revisions: dict[str, str | None] | None = None,
        checkpoint: Callable[[TransactionCheckpoint], None] | None = None,
    ) -> dict[str, str | None]:
        """@brief Publish one complete mutation set or leave recoverable state."""
        if not mutations:
            return {}
        expected_revisions = expected_revisions or {}
        paths = [str(mutation.path) for mutation in mutations]
        if len(paths) != len(set(paths)):
            raise RecoveryError("A transaction cannot target the same path twice.")
        with self.locked():
            self._recover_locked()
            for path, expected in expected_revisions.items():
                actual = self._current_revision(path)
                if actual != expected:
                    raise RevisionConflict(
                        f"Stale revision for {path}: expected {expected}, "
                        f"found {actual}."
                    )
            transaction = self.transactions / f"TXN-{uuid4().hex}"
            before_dir = transaction / "before"
            after_dir = transaction / "after"
            before_dir.mkdir(parents=True)
            after_dir.mkdir(parents=True)
            entries: list[dict[str, object]] = []
            for index, mutation in enumerate(mutations):
                path = str(mutation.path)
                target = self._target(path)
                copy_name = f"{index:04d}.bin"
                before = target.read_bytes() if target.exists() else None
                if before is not None:
                    atomic_replace(before_dir / copy_name, before)
                if mutation.content is not None:
                    atomic_replace(after_dir / copy_name, mutation.content)
                entries.append(
                    {
                        "path": path,
                        "copy": copy_name,
                        "before_exists": before is not None,
                        "before_revision": None
                        if before is None
                        else revision_of(before),
                        "after_exists": mutation.content is not None,
                        "after_revision": None
                        if mutation.content is None
                        else revision_of(mutation.content),
                    }
                )
            plan = (
                json.dumps(
                    {"schema": 1, "entries": entries},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n"
            )
            atomic_replace(transaction / "plan.json", plan)
            if checkpoint is not None:
                checkpoint(TransactionCheckpoint.PREPARED)
            atomic_replace(transaction / "decision", b"commit\n")
            if checkpoint is not None:
                checkpoint(TransactionCheckpoint.COMMIT_DECIDED)
            for index, mutation in enumerate(mutations):
                target = self._target(str(mutation.path))
                if mutation.content is None:
                    if target.exists():
                        target.unlink()
                else:
                    atomic_replace(target, mutation.content)
                if index == 0 and checkpoint is not None:
                    checkpoint(TransactionCheckpoint.FIRST_TARGET_APPLIED)
            if checkpoint is not None:
                checkpoint(TransactionCheckpoint.ALL_TARGETS_APPLIED)
            self._verify(transaction, entries, after=True)
            result = {
                str(entry["path"]): (
                    str(entry["after_revision"]) if entry["after_exists"] else None
                )
                for entry in entries
            }
            shutil.rmtree(transaction)
            return result


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
