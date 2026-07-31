#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repowise_transaction_recovery.py
@brief RepoWise persistent transaction, crash recovery, and reporting tests.
@details Uses abrupt child-process termination at each write barrier to prove
         that the next authenticated recovery restores the exact prior state,
         while committed cleanup failures preserve applied state.
@author Eng. Dan Dumitru Pasare
@date 2026-07-30
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import waegis.repowise as repowise_module
from waegis.payload.copier import copy_payload
from waegis.payload.locate import locate_payload
from waegis.repowise import RepoWiseError, RepoWiseSettings, configure_repowise
from waegis.transaction import (
    TRANSACTION_DIRECTORY,
    FileTransaction,
    pending_transaction_ids,
    recover_incomplete_transactions,
)


# CONSTANTS

_TRACKED_PATHS = (
    ".agentic/integrations/repowise.toml",
    ".agentic/integrations/repowise-runtime.json",
    ".agentic/install-manifest.json",
)


# LOCAL HELPERS


def _install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """@brief Install a real payload and isolate transaction authentication state."""
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
    repo = tmp_path / "repo"
    copy_payload(locate_payload(), repo, mode="new")
    return repo


def _snapshot(repo: Path) -> dict[str, bytes | None]:
    """@brief Capture exact bytes or absence for the RepoWise operation set."""
    return {
        relative: (repo / relative).read_bytes() if (repo / relative).is_file() else None
        for relative in _TRACKED_PATHS
    }


def _run_crashing_configuration(repo: Path, stage: str) -> subprocess.CompletedProcess[str]:
    """
    @brief Run RepoWise configuration in a child that exits at one barrier.
    @version 0.2.0
    """
    script = r"""
import os
import sys
from pathlib import Path
import waegis.repowise as module
from waegis.repowise import RepoWiseSettings, configure_repowise
from waegis.transaction import FileTransaction

repo = Path(sys.argv[1])
stage = sys.argv[2]

def stop(*args, **kwargs):
    os._exit(91)

if stage == "before-policy":
    module._write_text = stop
elif stage == "after-policy":
    original = module._write_text
    def after_policy(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(91)
    module._write_text = after_policy
elif stage == "after-runtime":
    original = module._write_json
    def after_runtime(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(91)
    module._write_json = after_runtime
elif stage == "before-manifest":
    module.write_manifest = stop
elif stage == "after-manifest":
    original = module.write_manifest
    def after_manifest(*args, **kwargs):
        result = original(*args, **kwargs)
        os._exit(91)
    module.write_manifest = after_manifest
elif stage == "after-commit":
    FileTransaction.cleanup = stop

configure_repowise(repo, RepoWiseSettings())
"""
    # The pytest `pythonpath = ["src"]` wiring is process-local; the child
    # needs an explicit PYTHONPATH to import the uninstalled waegis package.
    env = os.environ.copy()
    package_root = str(Path(repowise_module.__file__).resolve().parents[1])
    env["PYTHONPATH"] = package_root + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        (sys.executable, "-c", script, str(repo), stage),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


# TESTS


@pytest.mark.parametrize(
    "stage",
    (
        "before-policy",
        "after-policy",
        "after-runtime",
        "before-manifest",
        "after-manifest",
    ),
)
def test_abrupt_exit_at_each_repowise_write_barrier_recovers_exact_prior_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """@brief Every uncommitted crash point restores all three files exactly."""
    repo = _install(tmp_path, monkeypatch)
    before = _snapshot(repo)

    crashed = _run_crashing_configuration(repo, stage)

    assert crashed.returncode == 91, crashed.stderr
    assert len(pending_transaction_ids(repo)) == 1
    recovered = recover_incomplete_transactions(repo)
    assert len(recovered) == 1
    assert _snapshot(repo) == before
    assert recover_incomplete_transactions(repo) == ()


def test_abrupt_exit_after_commit_is_cleanup_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A committed transaction is never rolled back when cleanup resumes."""
    repo = _install(tmp_path, monkeypatch)
    before = _snapshot(repo)

    crashed = _run_crashing_configuration(repo, "after-commit")

    assert crashed.returncode == 91, crashed.stderr
    applied = _snapshot(repo)
    assert applied != before
    assert pending_transaction_ids(repo) == ()
    assert recover_incomplete_transactions(repo) == ()
    assert _snapshot(repo) == applied
    root = repo / TRANSACTION_DIRECTORY
    assert not root.exists() or not any(root.iterdir())


def test_cleanup_failure_reports_committed_state_and_recovery_preserves_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Cleanup failure is distinguished from apply failure and retried."""
    repo = _install(tmp_path, monkeypatch)
    original_cleanup = FileTransaction.cleanup

    def fail_cleanup(_transaction: FileTransaction) -> None:
        """@brief Inject one terminal cleanup failure."""
        raise OSError("cleanup unavailable")

    monkeypatch.setattr(FileTransaction, "cleanup", fail_cleanup)
    with pytest.raises(RepoWiseError, match="committed successfully"):
        configure_repowise(repo, RepoWiseSettings())
    applied = _snapshot(repo)
    monkeypatch.setattr(FileTransaction, "cleanup", original_cleanup)

    assert pending_transaction_ids(repo) == ()
    assert recover_incomplete_transactions(repo) == ()
    assert _snapshot(repo) == applied


def test_rollback_failure_is_reported_and_authenticated_state_is_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief No false rollback-success claim is emitted when rollback itself fails."""
    repo = _install(tmp_path, monkeypatch)
    before = _snapshot(repo)
    original_write_json = repowise_module._write_json
    original_rollback = FileTransaction.rollback

    def fail_after_policy(_path: Path, _payload: object) -> None:
        """@brief Fail before runtime persistence."""
        raise OSError("runtime unavailable")

    def fail_rollback(transaction: FileTransaction, **_kwargs: object) -> None:
        """@brief Model a rollback I/O failure that releases the process lock."""
        transaction.abandon()
        raise OSError("restore unavailable")

    monkeypatch.setattr(repowise_module, "_write_json", fail_after_policy)
    monkeypatch.setattr(FileTransaction, "rollback", fail_rollback)
    with pytest.raises(RepoWiseError, match="rollback failed") as caught:
        configure_repowise(repo, RepoWiseSettings())
    assert "runtime unavailable" not in str(caught.value)
    monkeypatch.setattr(repowise_module, "_write_json", original_write_json)
    monkeypatch.setattr(FileTransaction, "rollback", original_rollback)

    assert len(pending_transaction_ids(repo)) == 1
    assert len(recover_incomplete_transactions(repo)) == 1
    assert _snapshot(repo) == before


@pytest.mark.parametrize("process_exception", (KeyboardInterrupt, SystemExit))
def test_process_control_exceptions_are_reraised_after_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process_exception: type[BaseException],
) -> None:
    """@brief Interrupt and exit semantics survive RepoWise rollback handling."""
    repo = _install(tmp_path, monkeypatch)
    before = _snapshot(repo)

    def interrupt_runtime(_path: Path, _payload: object) -> None:
        """@brief Raise one process-control exception after policy persistence."""
        raise process_exception()

    monkeypatch.setattr(repowise_module, "_write_json", interrupt_runtime)
    with pytest.raises(process_exception):
        configure_repowise(repo, RepoWiseSettings())

    assert _snapshot(repo) == before
    assert pending_transaction_ids(repo) == ()


def test_successful_configuration_is_manifest_last_and_second_run_is_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Policy/runtime precede manifest, and identical configuration writes nothing."""
    repo = _install(tmp_path, monkeypatch)
    events: list[str] = []
    original_text = repowise_module._write_text
    original_json = repowise_module._write_json
    original_manifest = repowise_module.write_manifest

    def record_text(path: Path, text: str) -> None:
        """@brief Record and perform the policy write."""
        events.append("policy")
        original_text(path, text)

    def record_json(path: Path, payload: object) -> None:
        """@brief Record and perform the runtime write."""
        events.append("runtime")
        original_json(path, payload)  # type: ignore[arg-type]

    def record_manifest(repo_path: Path, manifest: object) -> Path:
        """@brief Record and perform the manifest write."""
        events.append("manifest")
        return original_manifest(repo_path, manifest)  # type: ignore[arg-type]

    monkeypatch.setattr(repowise_module, "_write_text", record_text)
    monkeypatch.setattr(repowise_module, "_write_json", record_json)
    monkeypatch.setattr(repowise_module, "write_manifest", record_manifest)

    first = configure_repowise(repo, RepoWiseSettings())
    assert first["changed"] is True
    assert events == ["policy", "runtime", "manifest"]
    events.clear()

    second = configure_repowise(repo, RepoWiseSettings())
    assert second["changed"] is False
    assert events == []


# END OF FILE
