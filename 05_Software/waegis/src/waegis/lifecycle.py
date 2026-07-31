#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file lifecycle.py
@brief Shared lifecycle fingerprints, journal lookup, and answer replay.
@details Keeps command modules from importing private helpers from
         ``commands.new``. Resume is intentionally conservative: only an
         incomplete journal whose command, catalog, target, initial-answer,
         and payload fingerprints all match is eligible. A completed run is
         never a resume candidate; callers perform a fresh detection pass.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .engine import (
    STATUS_DECLINED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_STOPPED,
    Catalog,
    Journal,
)

# CONSTANTS

# @brief States representing an interrupted or incomplete operation.
INCOMPLETE_JOURNAL_STATUSES = frozenset(
    {STATUS_IN_PROGRESS, STATUS_FAILED, STATUS_DECLINED, STATUS_STOPPED}
)

# @brief Required fingerprint dimensions for safe journal replay.
FINGERPRINT_KEYS = frozenset({"command", "catalog", "target", "answers", "payload"})


# EXPORTED FUNCTIONS / PUBLIC API


def stable_fingerprint(value: Any) -> str:
    """
    @brief      Hash one JSON-compatible value deterministically.
    @param[in]  value Value to canonicalize and hash.
    @return     Lowercase sha256 digest.
    @exception  TypeError If ``value`` is not JSON serializable.
    """
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_journal_fingerprints(
    *,
    command: str,
    catalog: Catalog,
    target: Path,
    answers: Mapping[str, Any],
    payload_digest: str,
) -> dict[str, str]:
    """
    @brief      Build all fingerprints required for a replay-safe journal.
    @param[in]  command Lifecycle command name.
    @param[in]  catalog Ordered step catalog.
    @param[in]  target Resolved repository root.
    @param[in]  answers Initial non-secret answers mapping.
    @param[in]  payload_digest Validated payload inventory digest.
    @return     Five-key fingerprint mapping.
    @exception  TypeError If answers are not JSON serializable.
    """
    return {
        "command": stable_fingerprint(command),
        "catalog": stable_fingerprint([step.id for step in catalog.ordered()]),
        "target": stable_fingerprint(str(target.resolve()).casefold()),
        "answers": stable_fingerprint(dict(answers)),
        "payload": stable_fingerprint(payload_digest),
    }


def find_resume_journal(
    home: Path,
    *,
    expected_fingerprints: Mapping[str, str],
) -> Journal | None:
    """
    @brief      Find the newest incomplete journal matching every fingerprint.
    @param[in]  home WAEGIS state root.
    @param[in]  expected_fingerprints Current operation fingerprints.
    @return     Matching journal or ``None``.
    @exception  None Corrupt/unreadable journals are ignored.
    """
    if set(expected_fingerprints) != FINGERPRINT_KEYS:
        return None
    directory = home / "journals"
    if not directory.is_dir():
        return None
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            journal = Journal.load(path)
        except Exception:  # noqa: BLE001 - a corrupt checkpoint must not block a run
            continue
        if journal.status not in INCOMPLETE_JOURNAL_STATUSES:
            continue
        if journal.fingerprints == dict(expected_fingerprints):
            return journal
    return None


def replay_answers(journal: Journal, *, allowed_keys: Iterable[str]) -> dict[str, Any]:
    """
    @brief      Collect non-secret recorded answers from a compatible journal.
    @param[in]  journal Journal already accepted by :func:`find_resume_journal`.
    @param[in]  allowed_keys Explicit field allowlist.
    @return     Last recorded value for each allowed key.
    @exception  None
    """
    allowed = set(allowed_keys)
    replayed: dict[str, Any] = {}
    for result in journal.results():
        for key, value in result.answers.items():
            if key in allowed:
                replayed[key] = value
    return replayed


# END OF FILE
