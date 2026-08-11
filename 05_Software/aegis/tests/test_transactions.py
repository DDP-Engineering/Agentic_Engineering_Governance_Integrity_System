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
@file    test_transactions.py
@brief   Verify cohesive publication, stale-write rejection, and recovery.
@details Covers PR-STATE, PR-COLLAB-008/011, AC-PROTO-005, and AC-STATE-001
         for IP-03.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from aegis.domain.values import RepositoryPath
from aegis.infrastructure.transactions import (
    FileMutation,
    RevisionConflict,
    TransactionCheckpoint,
    TransactionStore,
    revision_of,
)


def test_stale_revision_rejects_the_complete_mutation(tmp_path: Path) -> None:
    """@brief A stale caller cannot overwrite a newer authoritative value."""
    target = tmp_path / "state.md"
    target.write_bytes(b"current\n")
    store = TransactionStore(tmp_path)

    with pytest.raises(RevisionConflict):
        store.publish(
            (FileMutation(RepositoryPath("state.md"), b"caller\n"),),
            expected_revisions={"state.md": "sha256:" + "0" * 64},
        )

    assert target.read_bytes() == b"current\n"
    assert not (tmp_path / ".agentic" / ".runtime" / "transactions").exists()


@pytest.mark.parametrize(
    "checkpoint,expected",
    [
        (TransactionCheckpoint.PREPARED, (b"before-a\n", b"before-b\n")),
        (TransactionCheckpoint.COMMIT_DECIDED, (b"after-a\n", b"after-b\n")),
        (TransactionCheckpoint.FIRST_TARGET_APPLIED, (b"after-a\n", b"after-b\n")),
    ],
)
def test_recovery_exposes_a_complete_before_or_after_state(
    tmp_path: Path,
    checkpoint: TransactionCheckpoint,
    expected: tuple[bytes, bytes],
) -> None:
    """@brief Recovery rolls back before decision and rolls forward after it."""
    first = tmp_path / "a.md"
    second = tmp_path / "b.md"
    first.write_bytes(b"before-a\n")
    second.write_bytes(b"before-b\n")
    store = TransactionStore(tmp_path)

    def interrupt(observed: TransactionCheckpoint) -> None:
        if observed is checkpoint:
            raise SystemExit(91)

    with pytest.raises(SystemExit):
        store.publish(
            (
                FileMutation(RepositoryPath("a.md"), b"after-a\n"),
                FileMutation(RepositoryPath("b.md"), b"after-b\n"),
            ),
            expected_revisions={
                "a.md": revision_of(first.read_bytes()),
                "b.md": revision_of(second.read_bytes()),
            },
            checkpoint=interrupt,
        )

    TransactionStore(tmp_path).recover()

    assert (first.read_bytes(), second.read_bytes()) == expected
    transactions = tmp_path / ".agentic" / ".runtime" / "transactions"
    assert not transactions.exists() or list(transactions.iterdir()) == []


def test_create_replace_and_delete_publish_as_one_decided_state(tmp_path: Path) -> None:
    """@brief One transaction can cohesively create, replace, and delete files."""
    replace = tmp_path / "replace.md"
    delete = tmp_path / "delete.md"
    replace.write_bytes(b"before\n")
    delete.write_bytes(b"remove\n")
    result = TransactionStore(tmp_path).publish(
        (
            FileMutation(RepositoryPath("create.md"), b"created\n"),
            FileMutation(RepositoryPath("replace.md"), b"after\n"),
            FileMutation(RepositoryPath("delete.md"), None),
        ),
        expected_revisions={
            "create.md": None,
            "replace.md": revision_of(b"before\n"),
            "delete.md": revision_of(b"remove\n"),
        },
    )

    assert (tmp_path / "create.md").read_bytes() == b"created\n"
    assert replace.read_bytes() == b"after\n"
    assert not delete.exists()
    assert result["delete.md"] is None
