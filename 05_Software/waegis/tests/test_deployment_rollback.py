#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_deployment_rollback.py
@brief Crash safety for the two deployment commands that write a payload.
@details `new` and `adopt` copy a payload file by file. Without a rollback
         journal an interruption partway through leaves a half-installed
         payload and no manifest, and nothing later restores it — the adoption
         case writes into a repository that already holds the operator's work.
         These tests cover the apply-phase seam in the copier, the transaction
         scope built on it, and an end-to-end failure midway through a real
         adoption copy.
@author Eng. Dan Dumitru Pasare
@date 2026-07-23
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import waegis.payload.copier as copier_module
from waegis.commands.adopt import run_adopt
from waegis.commands.new import run_new
from waegis.payload.copier import ConflictDecision, OverwriteRefusedError, copy_payload
from waegis.payload.manifest import MANIFEST_RELATIVE_PATH, manifest_path
from waegis.transaction import (
    TRANSACTION_DIRECTORY,
    FileTransaction,
    payload_transaction,
    recover_incomplete_transactions,
)

# CONSTANTS

PAYLOAD_FILES = (".agentic/workflow.toml", "AGENTS.md", "src/app.py")


# LOCAL HELPERS


def _make_payload(root: Path) -> Path:
    """
    @brief      Build a small synthetic payload tree.
    @param[in]  root Directory to populate.
    @return     ``root``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    (root / ".agentic").mkdir(parents=True)
    (root / ".agentic" / "workflow.toml").write_bytes(b"[workflow]\nname = 'toy'\n")
    (root / "AGENTS.md").write_bytes(b"# AGENTS\npayload copy\n")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_bytes(b"print('payload')\n")
    return root


class _RecordingScope:
    """
    @brief Apply-phase scope that records the paths it was handed.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-23
    @version 0.1.0
    """

    def __init__(self) -> None:
        """
        @brief      Start with no recorded invocation.
        @return     None
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-23
        @version    0.1.0
        """
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, paths: tuple[str, ...]) -> "_RecordingScope":
        """
        @brief      Record one apply-phase invocation.
        @param[in]  paths Paths the apply phase is about to write.
        @return     Self, used as the context manager.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-23
        @version    0.1.0
        """
        self.calls.append(paths)
        return self

    def __enter__(self) -> "_RecordingScope":
        """@brief Enter the recorded scope."""
        return self

    def __exit__(self, *_exc: object) -> bool:
        """@brief Leave the recorded scope without suppressing anything."""
        return False


def _fail_after_payload_copies(count: int, payload: Path):
    """
    @brief      Build a ``shutil.copy2`` replacement that fails after N payload
                copies.
    @param[in]  count Number of payload copies to allow before raising.
    @param[in]  payload Payload root; only copies sourced from it are counted.
    @return     Callable usable as a ``copy2`` monkeypatch.
    @details    Stands in for the interruption case: the process dies partway
                through the apply phase with some destinations already written.
                Only payload-sourced copies are intercepted, because the
                transaction stages its backups and performs its restores through
                the same ``shutil.copy2``: counting those would spend the budget
                before the first payload byte is written, and the test would
                then pass without ever proving that an overwritten file is
                restored.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    state = {"copies": 0}
    real = copier_module.shutil.copy2

    def flaky(source, destination, *args, **kwargs):  # type: ignore[no-untyped-def]
        """@brief Copy until the payload budget is spent, then raise."""
        if Path(source).is_relative_to(payload):
            if state["copies"] >= count:
                raise OSError("simulated interruption during payload copy")
            state["copies"] += 1
        return real(source, destination, *args, **kwargs)

    return flaky


# TESTS — copier apply-phase seam


def test_apply_scope_receives_exactly_the_paths_that_will_be_written(tmp_path: Path) -> None:
    """
    @brief      Verify the scope is handed the copied files and the manifest.
    @param[in]  tmp_path Temporary root for the payload and target.
    @return     None.
    @details    A journal staged over a superset would back up files the copy
                never touches; a subset would leave writes unprotected.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    scope = _RecordingScope()

    copy_payload(payload, tmp_path / "target", mode="new", on_apply=scope)

    assert len(scope.calls) == 1
    assert scope.calls[0] == tuple(sorted((*PAYLOAD_FILES, MANIFEST_RELATIVE_PATH)))


def test_apply_scope_includes_write_new_sidecars(tmp_path: Path) -> None:
    """
    @brief      Verify a `.new` sidecar destination is inside the scope.
    @param[in]  tmp_path Temporary root for the payload and target.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    (target / "src").mkdir(parents=True)
    (target / "src" / "app.py").write_bytes(b"print('local')\n")
    scope = _RecordingScope()

    copy_payload(
        payload,
        target,
        mode="adopt",
        on_conflict=lambda _conflict: ConflictDecision.WRITE_NEW,
        on_apply=scope,
    )

    assert "src/app.py.new" in scope.calls[0]
    # The conflicting payload path itself is kept local, so it is not written.
    assert "src/app.py" not in scope.calls[0]


def test_apply_scope_is_not_opened_on_a_dry_run(tmp_path: Path) -> None:
    """
    @brief      Verify a dry run stages no journal because it writes nothing.
    @param[in]  tmp_path Temporary root for the payload and target.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    scope = _RecordingScope()

    copy_payload(payload, tmp_path / "target", mode="new", dry_run=True, on_apply=scope)

    assert scope.calls == []


def test_apply_scope_is_not_opened_when_strict_mode_refuses(tmp_path: Path) -> None:
    """
    @brief      Verify a refusal never stages a journal.
    @param[in]  tmp_path Temporary root for the payload and target.
    @return     None.
    @details    The refusal happens before the apply phase, so there is nothing
                to protect and no transaction directory should appear.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    target.mkdir()
    (target / "AGENTS.md").write_bytes(b"local\n")
    scope = _RecordingScope()

    with pytest.raises(OverwriteRefusedError):
        copy_payload(payload, target, mode="new", on_apply=scope)

    assert scope.calls == []


def test_apply_scope_is_not_opened_when_a_conflict_hook_raises(tmp_path: Path) -> None:
    """
    @brief      Verify a hook that raises leaves the target untouched and
                unjournaled.
    @param[in]  tmp_path Temporary root for the payload and target.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    (target / "src").mkdir(parents=True)
    (target / "src" / "app.py").write_bytes(b"print('local')\n")
    scope = _RecordingScope()

    def exploding_hook(_conflict):  # type: ignore[no-untyped-def]
        """@brief Fail while deciding, before anything is written."""
        raise RuntimeError("operator aborted")

    with pytest.raises(RuntimeError):
        copy_payload(payload, target, mode="adopt", on_conflict=exploding_hook, on_apply=scope)

    assert scope.calls == []
    assert not manifest_path(target).exists()


# TESTS — transaction scope


def test_payload_transaction_commits_and_removes_its_directory(tmp_path: Path) -> None:
    """
    @brief      Verify a clean block commits and leaves no staged state behind.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    with payload_transaction(repo, command="new", paths=("AGENTS.md",)) as transaction:
        (repo / "AGENTS.md").write_text("written\n", encoding="utf-8")
        directory = transaction.directory

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "written\n"
    assert not directory.exists()


def test_payload_transaction_restores_every_destination_on_failure(tmp_path: Path) -> None:
    """
    @brief      Verify a failed block restores overwritten files and removes new
                ones.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("original\n", encoding="utf-8")

    with pytest.raises(RuntimeError):
        with payload_transaction(repo, command="adopt", paths=("AGENTS.md", "src/app.py")):
            (repo / "AGENTS.md").write_text("payload\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("payload\n", encoding="utf-8")
            raise RuntimeError("interrupted")

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "original\n"
    assert not (repo / "src" / "app.py").exists()


# TESTS — end-to-end deployment crash safety


def test_an_interrupted_adoption_copy_leaves_the_repository_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief      Verify a failure midway through the apply phase restores the
                repository exactly as it was.
    @param[in]  tmp_path Temporary root for the payload and repository.
    @param[in]  monkeypatch Fixture used to fail the copy partway through.
    @return     None.
    @details    This is the case the journal exists for: adoption overwrites
                files the operator already had, so a partial apply must not
                survive. Two conflicts are taken from the payload and the copy
                fails between them, so the run covers both halves of a rollback
                — restoring content that was already overwritten, and removing
                files the copy newly created. Verified against the unjournaled
                path: without the scope, `.agentic/workflow.toml` and the
                overwritten `AGENTS.md` stay on disk with no manifest recording
                either.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "AGENTS.md").write_bytes(b"# AGENTS\nlocal contract\n")
    (repo / "src" / "app.py").write_bytes(b"print('local work')\n")
    # Copy order is missing files first, then take-payload overwrites: the
    # single missing file and AGENTS.md land, then src/app.py raises.
    monkeypatch.setattr(copier_module.shutil, "copy2", _fail_after_payload_copies(2, payload))

    with pytest.raises(OSError):
        copy_payload(
            payload,
            repo,
            mode="adopt",
            on_conflict=lambda _conflict: ConflictDecision.TAKE_PAYLOAD,
            require_existing_target=True,
            on_apply=lambda paths: payload_transaction(repo, command="adopt", paths=paths),
        )

    # Overwritten operator content is restored byte for byte.
    assert (repo / "AGENTS.md").read_bytes() == b"# AGENTS\nlocal contract\n"
    assert (repo / "src" / "app.py").read_bytes() == b"print('local work')\n"
    # Files the interrupted copy created are gone, and no manifest claims them.
    assert not (repo / ".agentic" / "workflow.toml").exists()
    assert not manifest_path(repo).exists()
    # No staged journal is left behind either.
    assert not (repo / TRANSACTION_DIRECTORY).exists() or not any(
        (repo / TRANSACTION_DIRECTORY).iterdir()
    )


def test_a_killed_run_is_rolled_back_by_the_next_command(tmp_path: Path) -> None:
    """
    @brief      Verify a transaction left non-terminal by process death is
                recovered on the next WAEGIS command.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Rollback inside the scope covers exceptions; a killed process
                never reaches it, so the persisted journal must carry the
                recovery.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.2.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("original\n", encoding="utf-8")

    # Simulate the process dying between `applying` and `commit`.
    transaction = FileTransaction.begin(repo, command="adopt", paths=("AGENTS.md", "src/app.py"))
    transaction.mark("applying")
    (repo / "AGENTS.md").write_text("payload\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("payload\n", encoding="utf-8")
    transaction.abandon()

    recovered = recover_incomplete_transactions(repo)

    assert recovered == (transaction.state["id"],)
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "original\n"
    assert not (repo / "src" / "app.py").exists()


# TESTS — recovery scan robustness


def test_recovery_skips_a_directory_that_holds_no_transaction_state(tmp_path: Path) -> None:
    """
    @brief      Verify unrelated litter under the transaction root is ignored.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Every mutating command runs recovery first, so raising on a
                directory that carries no journal at all would make the whole
                tool unusable until it was deleted by hand.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    (repo / TRANSACTION_DIRECTORY / "leftover").mkdir(parents=True)

    assert recover_incomplete_transactions(repo) == ()


def test_recovery_still_raises_for_a_malformed_transaction_state(tmp_path: Path) -> None:
    """
    @brief      Verify a damaged journal is loud rather than silently skipped.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    A present but unreadable journal means a real interrupted run
                whose recovery record was damaged; ignoring it would strand a
                partially applied change.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    directory = repo / TRANSACTION_DIRECTORY / "20260723T101010Z-abcdef12"
    directory.mkdir(parents=True)
    (directory / "state.json").write_text(json.dumps({"transaction_version": 99}), encoding="utf-8")

    with pytest.raises(ValueError):
        recover_incomplete_transactions(repo)


# TESTS — the deployment commands run recovery before touching the target


def _stage_interrupted_transaction(repo: Path) -> FileTransaction:
    """
    @brief      Leave a repository holding one non-terminal transaction.
    @param[in]  repo Repository root to stage against.
    @return     The staged transaction.
    @details    Models a previous run killed between ``applying`` and commit:
                the operator's file is overwritten and the journal still holds
                the original.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.2.0
    """
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "AGENTS.md").write_text("original\n", encoding="utf-8")
    transaction = FileTransaction.begin(repo, command="adopt", paths=("AGENTS.md",))
    transaction.mark("applying")
    (repo / "AGENTS.md").write_text("half-applied\n", encoding="utf-8")
    transaction.abandon()
    return transaction


def test_run_new_recovers_an_interrupted_transaction_before_running(tmp_path: Path) -> None:
    """
    @brief      Verify ``waegis new`` rolls back a prior interrupted run first.
    @param[in]  tmp_path Temporary target root.
    @return     None.
    @details    The run itself is expected to stop early (no answers supplied);
                what matters is that recovery already happened by then, because
                a journal nothing ever reads would leave the fix incomplete.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    target = tmp_path / "project"
    _stage_interrupted_transaction(target)

    run_new(target, stream=io.StringIO(), non_interactive=True, yes=True, home=tmp_path / "home")

    assert (target / "AGENTS.md").read_text(encoding="utf-8") == "original\n"


def test_run_adopt_recovers_an_interrupted_transaction_before_running(tmp_path: Path) -> None:
    """
    @brief      Verify ``waegis adopt`` rolls back a prior interrupted run first.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    _stage_interrupted_transaction(repo)

    run_adopt(repo, stream=io.StringIO(), non_interactive=True, yes=True, home=tmp_path / "home")

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "original\n"


def test_a_dry_run_never_recovers_because_it_must_not_mutate(tmp_path: Path) -> None:
    """
    @brief      Verify ``--dry-run`` leaves a staged transaction alone.
    @param[in]  tmp_path Temporary target root.
    @return     None.
    @details    A dry run promises to change nothing, and rolling a prior run
                back is a change.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    target = tmp_path / "project"
    transaction = _stage_interrupted_transaction(target)

    run_new(
        target,
        stream=io.StringIO(),
        non_interactive=True,
        dry_run=True,
        home=tmp_path / "home",
    )

    assert (target / "AGENTS.md").read_text(encoding="utf-8") == "half-applied\n"
    assert transaction.directory.exists()


# END OF FILE
