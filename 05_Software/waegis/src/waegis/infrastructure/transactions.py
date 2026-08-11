#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Publish lifecycle actions atomically with WAEGIS-local recovery state."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from waegis.domain.plans import PlanError, safe_relative


class PublicationInterrupted(PlanError):
    """Represent a fault-injection interruption that remains recoverable."""


class TransactionPublisher:
    """Prepare before/after bytes and roll an authorized plan forward."""

    def __init__(self, target: Path, fault_after: int | None = None) -> None:
        self.target = target
        self.journal = self._repository_path(
            ".agentic/.runtime/waegis/transaction.json"
        )
        self.fault_after = fault_after

    def _repository_path(self, relative: str) -> Path:
        """Reject any existing symlink ancestry that resolves outside target."""
        candidate = self.target / Path(safe_relative(relative))
        probe = candidate
        while not probe.exists() and probe != self.target:
            probe = probe.parent
        try:
            probe.resolve().relative_to(self.target)
        except ValueError as exc:
            raise PlanError(
                f"Repository path resolves outside target: {relative}"
            ) from exc
        return candidate

    def pending_digest(self) -> str | None:
        """Return the authorized plan digest of an interrupted publication."""
        if not self.journal.is_file():
            return None
        return str(self._read_journal().get("plan_digest", "")) or None

    def recover(self, expected_digest: str) -> None:
        """Roll forward only the exact interrupted authorized publication."""
        data = self._read_journal()
        if data.get("plan_digest") != expected_digest:
            raise PlanError(
                "A different interrupted WAEGIS publication requires recovery"
            )
        self._publish(data["actions"], allow_fault=False)
        self._finish()

    def apply(self, actions: list[dict[str, Any]], plan_digest: str) -> None:
        """Prepare durable recovery data, publish, and remove transient state."""
        journal_actions: list[dict[str, Any]] = []
        for action in actions:
            relative = safe_relative(str(action["path"]))
            path = self._repository_path(relative)
            before = path.read_bytes() if path.is_file() else None
            journal_actions.append(
                {
                    "kind": action["kind"],
                    "path": relative,
                    "before": None
                    if before is None
                    else base64.b64encode(before).decode("ascii"),
                    "after": action.get("content_base64"),
                }
            )
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema": 1, "plan_digest": plan_digest, "actions": journal_actions}
        self._atomic_write(
            self.journal, json.dumps(data, sort_keys=True).encode("utf-8")
        )
        self._publish(journal_actions, allow_fault=True)
        self._finish()

    def _read_journal(self) -> dict[str, Any]:
        try:
            return json.loads(self.journal.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("WAEGIS recovery journal is unreadable") from exc

    def _publish(self, actions: list[dict[str, Any]], *, allow_fault: bool) -> None:
        for index, action in enumerate(actions, start=1):
            path = self._repository_path(str(action["path"]))
            if action["kind"] == "delete":
                if path.is_file():
                    path.unlink()
            else:
                encoded = action.get("after")
                if not isinstance(encoded, str):
                    raise PlanError("Prepared write has no content")
                self._atomic_write(path, base64.b64decode(encoded, validate=True))
            if allow_fault and self.fault_after == index:
                raise PublicationInterrupted(
                    "Publication interrupted; exact recovery is available"
                )

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _finish(self) -> None:
        if self.journal.exists():
            self.journal.unlink()
        runtime = self.journal.parent
        while runtime != self.target and runtime.name in {"waegis", ".runtime"}:
            try:
                runtime.rmdir()
            except OSError:
                break
            runtime = runtime.parent
        payload = self.target / ".agentic/aegis"
        if payload.exists():
            for path in sorted(payload.rglob("*"), reverse=True):
                if path.is_dir():
                    try:
                        path.rmdir()
                    except OSError:
                        pass
            try:
                payload.rmdir()
            except OSError:
                pass
