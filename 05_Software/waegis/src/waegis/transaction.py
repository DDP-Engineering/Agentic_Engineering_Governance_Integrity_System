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
@brief Persistent file-transaction staging, rollback, and crash recovery.
@details A transaction records its state before mutation and backs up every
         destination. A later lifecycle invocation rolls back any transaction
         left in a non-terminal phase by process termination. All target paths
         pass the managed-path confinement validator.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .payload.manifest import normalize_managed_path, resolve_managed_path

# CONSTANTS

TRANSACTION_DIRECTORY = ".agentic/.waegis-transactions"
_TERMINAL_PHASES = frozenset({"committed", "rolled-back"})


# EXPORTED FUNCTIONS / PUBLIC API


class FileTransaction:
    """
    @brief One persistent repository-local file transaction.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-16
    @version 0.1.0
    """

    def __init__(self, repo: Path, directory: Path, state: dict[str, Any]) -> None:
        """
        @brief      Construct from a repository, storage directory, and state.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        self.repo = repo.resolve()
        self.directory = directory
        self.state = state

    @classmethod
    def begin(cls, repo: Path, *, command: str, paths: Iterable[str]) -> "FileTransaction":
        """
        @brief      Stage backups and persist a new transaction before writes.
        @return     Ready transaction in ``staged`` phase.
        @exception  OSError If staging fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        repo = repo.resolve()
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        root = resolve_managed_path(repo, TRANSACTION_DIRECTORY)
        directory = root / transaction_id
        backups = directory / "backups"
        backups.mkdir(parents=True, exist_ok=False)
        entries: list[dict[str, Any]] = []
        for index, raw in enumerate(paths):
            relative = normalize_managed_path(raw)
            target = resolve_managed_path(repo, relative)
            existed = target.is_file()
            backup_name = f"{index:06d}.bak"
            if existed:
                shutil.copy2(target, backups / backup_name)
            entries.append({"path": relative, "existed": existed, "backup": backup_name if existed else None})
        state = {
            "transaction_version": 1,
            "id": transaction_id,
            "command": command,
            "phase": "staged",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "entries": entries,
        }
        transaction = cls(repo, directory, state)
        transaction._flush()
        return transaction

    @classmethod
    def load(cls, repo: Path, directory: Path) -> "FileTransaction":
        """
        @brief      Load a transaction state document.
        @return     Loaded transaction.
        @exception  OSError If unreadable.
        @exception  ValueError If malformed.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        if state.get("transaction_version") != 1 or not isinstance(state.get("entries"), list):
            raise ValueError(f"invalid WAEGIS transaction state: {directory}")
        return cls(repo.resolve(), directory, state)

    def mark(self, phase: str) -> None:
        """
        @brief      Persist a transaction phase transition.
        @return     None
        @exception  ValueError On an unknown phase.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        if phase not in {"staged", "applying", "verified", "committed", "rolled-back"}:
            raise ValueError(f"invalid transaction phase: {phase!r}")
        self.state["phase"] = phase
        self._flush()

    def rollback(self) -> None:
        """
        @brief      Restore every staged destination to its pre-run state.
        @return     None
        @exception  OSError If restoration fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        for entry in reversed(self.state["entries"]):
            target = resolve_managed_path(self.repo, entry["path"])
            if entry["existed"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.directory / "backups" / entry["backup"], target)
            elif target.exists():
                if not target.is_file():
                    raise OSError(f"transaction target became non-file: {target}")
                target.unlink()
        self.mark("rolled-back")
        self.cleanup()

    def commit(self) -> None:
        """
        @brief      Mark committed and remove staged backup storage.
        @return     None
        @exception  OSError If state or cleanup fails.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        self.mark("committed")
        self.cleanup()

    def cleanup(self) -> None:
        """
        @brief      Remove this known transaction directory.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        root = resolve_managed_path(self.repo, TRANSACTION_DIRECTORY).resolve()
        directory = self.directory.resolve()
        directory.relative_to(root)
        shutil.rmtree(directory)

    def _flush(self) -> None:
        """
        @brief      Atomically persist state JSON.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-16
        @version    0.1.0
        """
        path = self.directory / "state.json"
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(self.state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temporary, path)


def recover_incomplete_transactions(repo: Path) -> tuple[str, ...]:
    """
    @brief      Roll back every non-terminal transaction left by interruption.
    @return     Recovered transaction ids.
    @exception  OSError If recovery cannot restore state safely.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    root = resolve_managed_path(repo.resolve(), TRANSACTION_DIRECTORY)
    if not root.is_dir():
        return ()
    recovered: list[str] = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        transaction = FileTransaction.load(repo, directory)
        if transaction.state.get("phase") not in _TERMINAL_PHASES:
            transaction.rollback()
            recovered.append(str(transaction.state.get("id", directory.name)))
        elif directory.exists():
            transaction.cleanup()
    return tuple(recovered)


# END OF FILE
