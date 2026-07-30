#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_transaction_integrity.py
@brief Authenticated transaction-state validation and rollback safety tests.
@details Exercises forged state, storage redirection, destination substitution,
         content binding, retained rollback evidence, and idempotent recovery
         with real filesystem objects.
@author Eng. Dan Dumitru Pasare
@date 2026-07-30
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from waegis.transaction import (
    MAX_TRANSACTION_ENTRIES,
    FileTransaction,
    TransactionCleanupError,
    TransactionRollbackError,
    TransactionStateError,
    pending_transaction_ids,
    recover_incomplete_transactions,
)


# LOCAL HELPERS


def _stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    paths: tuple[str, ...] = ("managed.txt",),
) -> tuple[Path, FileTransaction, Path]:
    """@brief Stage one applying transaction and return its repository and sentinel."""
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    sentinel = tmp_path / "external-sentinel.txt"
    sentinel.write_bytes(b"external-original")
    for relative in paths:
        target = repo / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"original:{relative}".encode("utf-8"))
    transaction = FileTransaction.begin(repo, command="test", paths=paths)
    transaction.mark("applying")
    for relative in paths:
        (repo / Path(relative)).write_bytes(f"applied:{relative}".encode("utf-8"))
    transaction.abandon()
    return repo, transaction, sentinel


def _state_path(transaction: FileTransaction) -> Path:
    """@brief Return the transaction state path."""
    return transaction.directory / "state.json"


def _read_state(transaction: FileTransaction) -> dict[str, Any]:
    """@brief Read a staged state mapping."""
    return json.loads(_state_path(transaction).read_text(encoding="utf-8"))


def _write_state(transaction: FileTransaction, state: dict[str, Any]) -> None:
    """@brief Replace staged state with a deliberately forged test mapping."""
    _state_path(transaction).write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )


def _assert_rejected_without_external_mutation(
    repo: Path,
    sentinel: Path,
    expected: str | None = None,
) -> None:
    """@brief Prove recovery rejects state and leaves an external sentinel unchanged."""
    before = sentinel.read_bytes()
    with pytest.raises((TransactionStateError, TransactionRollbackError), match=expected):
        recover_incomplete_transactions(repo)
    assert sentinel.read_bytes() == before


def _replace_with_symlink(path: Path, target: Path, *, directory: bool = False) -> None:
    """@brief Replace a path with a symlink or skip when host policy forbids it."""
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    try:
        path.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")


def _replace_with_junction(path: Path, target: Path) -> None:
    """@brief Replace a Windows directory with a junction or skip if unsupported."""
    if os.name != "nt":
        pytest.skip("Windows junctions apply only on Windows")
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()
    result = subprocess.run(
        ("cmd", "/c", "mklink", "/J", str(path), str(target)),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"junction creation is unavailable: {result.stderr or result.stdout}")


# TESTS - CLOSED SCHEMA AND AUTHENTICATED OWNERSHIP


@pytest.mark.parametrize(
    "forged_path",
    (
        "/absolute/target",
        "../traversal",
        "C:/drive-qualified",
        r"\\server\share\file",
        r"\\?\C:\device\file",
        "",
        ".",
    ),
)
def test_forged_destination_forms_are_rejected_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forged_path: str,
) -> None:
    """@brief Absolute, device, traversal, empty, and dot destinations fail closed."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    state = _read_state(transaction)
    state["entries"][0]["path"] = forged_path
    _write_state(transaction, state)

    _assert_rejected_without_external_mutation(repo, sentinel)
    assert (repo / "managed.txt").read_bytes() == b"applied:managed.txt"


def test_forged_sensitive_repository_destination_is_not_trusted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A valid-looking protected path cannot be substituted into signed state."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    protected = repo / ".agentic" / "hooks" / "pre_tool_use.py"
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b"protected")
    state = _read_state(transaction)
    state["entries"][0]["path"] = ".agentic/hooks/pre_tool_use.py"
    _write_state(transaction, state)

    _assert_rejected_without_external_mutation(repo, sentinel, "authentication")
    assert protected.read_bytes() == b"protected"


@pytest.mark.parametrize("backup", ("/tmp/source", "../source", "C:/source", r"\\server\share\x"))
def test_arbitrary_backup_references_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backup: str,
) -> None:
    """@brief Backup references accept only generated basenames."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    state = _read_state(transaction)
    state["entries"][0]["backup"] = backup
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "backup")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("transaction_version", 99, "version"),
        ("phase", "finished", "phase"),
        ("command", "../repair", "command"),
        ("created_at", "yesterday", "created_at"),
    ),
)
def test_invalid_top_level_values_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
    message: str,
) -> None:
    """@brief Version, phase, command, and timestamp contracts are strict."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    state = _read_state(transaction)
    state[field] = value
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, message)


@pytest.mark.parametrize("value", ("true", 1, 0, None, []))
def test_existed_requires_an_exact_json_boolean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: Any,
) -> None:
    """@brief Boolean-looking strings and integers are not coerced."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    state = _read_state(transaction)
    state["entries"][0]["existed"] = value
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "boolean")


@pytest.mark.parametrize("mutation", ("missing-top", "unknown-top", "missing-entry", "unknown-entry"))
def test_missing_and_unknown_keys_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """@brief State and entry mappings use exact closed schemas."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    state = _read_state(transaction)
    if mutation == "missing-top":
        state.pop("command")
    elif mutation == "unknown-top":
        state["extra"] = True
    elif mutation == "missing-entry":
        state["entries"][0].pop("backup_size")
    else:
        state["entries"][0]["source"] = str(sentinel)
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "keys")


def test_mismatched_transaction_id_and_directory_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief The authenticated id must equal the containing directory name."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    state = _read_state(transaction)
    state["id"] = "20260730T120000Z-deadbeef"
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "directory")


def test_duplicate_and_case_colliding_destinations_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Portable case-fold collisions cannot select one target twice."""
    repo, transaction, sentinel = _stage(
        tmp_path,
        monkeypatch,
        paths=("first.txt", "second.txt"),
    )
    state = _read_state(transaction)
    state["entries"][1]["path"] = "FIRST.TXT"
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "case-colliding")


def test_duplicate_backup_references_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Two destinations cannot claim the same authenticated backup."""
    repo, transaction, sentinel = _stage(
        tmp_path,
        monkeypatch,
        paths=("first.txt", "second.txt"),
    )
    state = _read_state(transaction)
    state["entries"][1]["backup"] = state["entries"][0]["backup"]
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "generated reference")


def test_missing_and_extra_backups_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Recovery requires every owned backup and rejects unowned extras."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    backup = transaction.directory / "backups" / "000000.bak"
    backup.unlink()
    _assert_rejected_without_external_mutation(repo, sentinel, "missing")

    backup.write_bytes(b"original:managed.txt")
    (backup.parent / "999999.bak").write_bytes(b"extra")
    _assert_rejected_without_external_mutation(repo, sentinel, "unowned")


def test_altered_backup_content_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A substituted backup fails its authenticated size/digest binding."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    (transaction.directory / "backups" / "000000.bak").write_bytes(b"attacker")
    _assert_rejected_without_external_mutation(repo, sentinel, "content metadata")


def test_altered_ownership_record_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief The external operation binding cannot be edited without its key."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    home = Path(os.environ["WAEGIS_HOME"])
    ownership = next((home / "transaction-ownership").rglob("*.json"))
    document = json.loads(ownership.read_text(encoding="utf-8"))
    document["operation_digest"] = "0" * 64
    ownership.write_text(json.dumps(document), encoding="utf-8")
    _assert_rejected_without_external_mutation(repo, sentinel, "ownership authentication")


def test_corrupt_and_resource_hostile_state_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Malformed JSON and excessive entry collections fail without recovery."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    _state_path(transaction).write_text("{", encoding="utf-8")
    _assert_rejected_without_external_mutation(repo, sentinel, "valid JSON")

    _write_state(transaction, transaction.state)
    state = _read_state(transaction)
    state["entries"] = [state["entries"][0]] * (MAX_TRANSACTION_ENTRIES + 1)
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "between")


def test_legacy_state_is_refused_with_manual_remediation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Unauthenticated version-1 state is never silently migrated."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    state = _read_state(transaction)
    state["transaction_version"] = 1
    _write_state(transaction, state)
    _assert_rejected_without_external_mutation(repo, sentinel, "reviewed manually")


# TESTS - STORAGE CONTAINMENT


def test_backup_symlink_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Recovery never follows a link substituted for an owned backup."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    backup = transaction.directory / "backups" / "000000.bak"
    _replace_with_symlink(backup, sentinel)
    _assert_rejected_without_external_mutation(repo, sentinel, "regular")


def test_symlinked_transaction_directory_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A transaction-root child symlink is rejected before state use."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    relocated = tmp_path / "relocated-transaction"
    transaction.directory.rename(relocated)
    try:
        transaction.directory.symlink_to(relocated, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    _assert_rejected_without_external_mutation(repo, sentinel, "link-like")


def test_junctioned_transaction_directory_is_rejected_when_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A Windows transaction-root child reparse point is refused."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    relocated = tmp_path / "junctioned-transaction"
    transaction.directory.rename(relocated)
    _replace_with_junction(transaction.directory, relocated)
    _assert_rejected_without_external_mutation(repo, sentinel, "link-like")


def test_symlinked_backup_directory_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A backup-directory redirection is rejected."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    backups = transaction.directory / "backups"
    relocated = tmp_path / "relocated-backups"
    backups.rename(relocated)
    try:
        backups.symlink_to(relocated, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    _assert_rejected_without_external_mutation(repo, sentinel, "backup directory")


def test_junctioned_backup_directory_is_rejected_when_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A Windows reparse-point backup redirection fails closed."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    backups = transaction.directory / "backups"
    relocated = tmp_path / "junction-target"
    shutil.copytree(backups, relocated)
    _replace_with_junction(backups, relocated)
    _assert_rejected_without_external_mutation(repo, sentinel, "backup directory")


# TESTS - ROLLBACK DESTINATION SAFETY AND IDEMPOTENCE


@pytest.mark.parametrize("new_file", (False, True))
def test_directory_substitution_retains_recovery_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    new_file: bool,
) -> None:
    """@brief Existing and new-file destinations replaced by directories are refused."""
    paths = ("managed.txt", "new.txt") if new_file else ("managed.txt",)
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch, paths=paths)
    target = repo / ("new.txt" if new_file else "managed.txt")
    if new_file:
        state = _read_state(transaction)
        entry = state["entries"][1]
        entry.update(
            {
                "existed": False,
                "backup": None,
                "backup_size": None,
                "backup_sha256": None,
            }
        )
        _write_state(transaction, state)
        # The state edit is intentionally unauthenticated, so stage a genuine
        # new-file transaction instead.
        shutil.rmtree(repo)
        repo.mkdir()
        (repo / "managed.txt").write_bytes(b"original")
        transaction = FileTransaction.begin(repo, command="test", paths=("new.txt",))
        transaction.mark("applying")
        (repo / "new.txt").write_bytes(b"created")
        transaction.abandon()
        target = repo / "new.txt"
    target.unlink()
    target.mkdir()

    _assert_rejected_without_external_mutation(repo, sentinel, "non-regular")
    assert transaction.directory.exists()


@pytest.mark.parametrize("new_file", (False, True))
def test_symlink_substitution_retains_recovery_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    new_file: bool,
) -> None:
    """@brief Existing and new-file destinations replaced by symlinks are refused."""
    if new_file:
        monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
        repo = tmp_path / "repo"
        repo.mkdir()
        sentinel = tmp_path / "external-sentinel.txt"
        sentinel.write_bytes(b"external-original")
        transaction = FileTransaction.begin(repo, command="test", paths=("new.txt",))
        transaction.mark("applying")
        (repo / "new.txt").write_bytes(b"created")
        transaction.abandon()
        target = repo / "new.txt"
    else:
        repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
        target = repo / "managed.txt"
    _replace_with_symlink(target, sentinel)

    _assert_rejected_without_external_mutation(repo, sentinel)
    assert sentinel.read_bytes() == b"external-original"
    assert transaction.directory.exists()


def test_junction_destination_substitution_is_rejected_when_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A Windows destination junction is never treated as a restore pathname."""
    repo, transaction, sentinel = _stage(tmp_path, monkeypatch)
    junction_target = tmp_path / "junction-destination"
    junction_target.mkdir()
    (junction_target / "sentinel.txt").write_bytes(b"junction-original")
    _replace_with_junction(repo / "managed.txt", junction_target)

    _assert_rejected_without_external_mutation(repo, sentinel)
    assert (junction_target / "sentinel.txt").read_bytes() == b"junction-original"
    assert transaction.directory.exists()


def test_regular_file_replacement_restores_exact_original_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A regular apply result is atomically replaced by its exact backup."""
    repo, transaction, _sentinel = _stage(tmp_path, monkeypatch)
    (repo / "managed.txt").write_bytes(b"another-regular-file")

    recovered = recover_incomplete_transactions(repo)

    assert recovered == (transaction.state["id"],)
    assert (repo / "managed.txt").read_bytes() == b"original:managed.txt"
    assert not transaction.directory.exists()


def test_recovery_is_idempotent_after_successful_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A second recovery performs no target mutation."""
    repo, transaction, _sentinel = _stage(tmp_path, monkeypatch)
    assert recover_incomplete_transactions(repo) == (transaction.state["id"],)
    restored = (repo / "managed.txt").read_bytes()

    assert recover_incomplete_transactions(repo) == ()
    assert (repo / "managed.txt").read_bytes() == restored


def test_replayed_nonterminal_state_cannot_roll_back_a_committed_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief External terminal ownership makes an older valid state cleanup-only."""
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "managed.txt"
    target.write_bytes(b"original")
    transaction = FileTransaction.begin(repo, command="test", paths=("managed.txt",))
    transaction.mark("applying")
    replay = (transaction.directory / "state.json").read_bytes()
    target.write_bytes(b"committed")
    transaction.mark("verified")
    original_cleanup = FileTransaction.cleanup

    def fail_cleanup(_transaction: FileTransaction) -> None:
        """@brief Retain terminal state after its authoritative commit marker."""
        raise OSError("cleanup unavailable")

    monkeypatch.setattr(FileTransaction, "cleanup", fail_cleanup)
    with pytest.raises(TransactionCleanupError):
        transaction.commit()
    monkeypatch.setattr(FileTransaction, "cleanup", original_cleanup)
    (transaction.directory / "state.json").write_bytes(replay)

    assert pending_transaction_ids(repo) == ()
    assert recover_incomplete_transactions(repo) == ()
    assert target.read_bytes() == b"committed"


def test_pending_discovery_is_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Dry-run discovery validates state without applying rollback."""
    repo, transaction, _sentinel = _stage(tmp_path, monkeypatch)
    state_before = _state_path(transaction).read_bytes()
    target_before = (repo / "managed.txt").read_bytes()

    assert pending_transaction_ids(repo) == (transaction.state["id"],)
    assert _state_path(transaction).read_bytes() == state_before
    assert (repo / "managed.txt").read_bytes() == target_before


def test_repository_lock_serializes_transactions_across_processes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A second process cannot begin while the first holds its transaction."""
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "first.txt").write_bytes(b"first")
    (repo / "second.txt").write_bytes(b"second")
    first_script = r"""
import sys
from pathlib import Path
from waegis.transaction import FileTransaction
repo = Path(sys.argv[1])
transaction = FileTransaction.begin(repo, command="test", paths=("first.txt",))
transaction.mark("applying")
print("READY", flush=True)
sys.stdin.readline()
transaction.rollback()
"""
    second_script = r"""
import sys
from pathlib import Path
from waegis.transaction import FileTransaction
repo = Path(sys.argv[1])
print("ATTEMPTING", flush=True)
transaction = FileTransaction.begin(repo, command="test", paths=("second.txt",))
print("ACQUIRED", flush=True)
transaction.rollback()
"""
    environment = os.environ.copy()
    first = subprocess.Popen(
        (sys.executable, "-c", first_script, str(repo)),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    assert first.stdout is not None
    assert first.stdout.readline().strip() == "READY"
    second = subprocess.Popen(
        (sys.executable, "-c", second_script, str(repo)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    assert second.stdout is not None
    assert second.stdout.readline().strip() == "ATTEMPTING"
    with pytest.raises(subprocess.TimeoutExpired):
        second.wait(timeout=0.25)
    assert first.stdin is not None
    first.stdin.write("\n")
    first.stdin.flush()
    assert first.wait(timeout=10) == 0, first.stderr.read() if first.stderr else ""
    output, error = second.communicate(timeout=10)
    assert second.returncode == 0, error
    assert output.strip() == "ACQUIRED"


# END OF FILE
