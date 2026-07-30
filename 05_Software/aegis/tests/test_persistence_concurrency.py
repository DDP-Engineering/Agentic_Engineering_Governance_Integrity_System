#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_persistence_concurrency.py
@brief Verify crash-safe AEGIS persistence and cross-process serialization.
@details Exercises real spawned processes on Windows and POSIX without
         timing-dependent sleeps.
@author Eng. Dan Dumitru Pasare
@date 2026-07-30
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

from dataclasses import replace
import json
import multiprocessing
from pathlib import Path
import sys
from typing import Any

import pytest

from aegis import persistence
from aegis.check_execution import run_checks
from aegis.config import load_config
from aegis.models import Check, Graph, Intent, StageRecord
from aegis.persistence import (
    LockTimeoutError,
    atomic_write_json,
    atomic_write_text,
    locked,
    scoped_lock_path,
)
from aegis.repowise import _atomic_json
from aegis.requirement_store import (
    RequirementConflictError,
    find_requirement_record,
    render_requirement_toml,
)
from aegis.requirements import create_requirement, update_requirement
from aegis import requirements as requirements_module
from aegis.store import (
    GraphConflictError,
    append_journal,
    graph_path,
    journal_path,
    load_graph,
    save_graph,
    set_access_mode,
    set_stage,
)

# CONSTANTS

RUN_ID = "feature-2026-07-30T120000Z-a1b2c3d4"

# PROCESS HELPERS


def _graph_update_worker(
    repo_root: str,
    operation: str,
    start: Any,
    messages: Any,
) -> None:
    """
    @brief Apply one graph update after every worker has loaded old state.
    @version 1.0.0
    """
    try:
        root = Path(repo_root)
        graph = load_graph(root, RUN_ID)
        messages.put(("ready", operation))
        if not start.wait(10):
            raise RuntimeError("start signal was not received")
        if operation == "stage":
            set_stage(root, graph, "implementation")
        else:
            set_access_mode(root, graph, "elevated", "concurrency test")
        messages.put(("done", operation))
    except BaseException as exc:
        messages.put(("error", operation, repr(exc)))


def _evidence_worker(
    repo_root: str,
    check_id: str,
    start: Any,
    messages: Any,
) -> None:
    """
    @brief Record one managed check after loading a shared old graph.
    @version 1.0.0
    """
    try:
        root = Path(repo_root)
        graph = load_graph(root, RUN_ID)
        messages.put(("ready", check_id))
        if not start.wait(10):
            raise RuntimeError("start signal was not received")
        evidence = run_checks(root, graph, [check_id])
        messages.put(("done", check_id, evidence[0].id))
    except BaseException as exc:
        messages.put(("error", check_id, repr(exc)))


def _journal_worker(
    repo_root: str,
    worker: str,
    count: int,
    start: Any,
    messages: Any,
) -> None:
    """
    @brief Append a deterministic record set from one spawned process.
    @version 1.0.0
    """
    try:
        messages.put(("ready", worker))
        if not start.wait(10):
            raise RuntimeError("start signal was not received")
        root = Path(repo_root)
        for index in range(count):
            append_journal(
                root,
                RUN_ID,
                "concurrent.record",
                {"worker": worker, "index": index},
            )
        messages.put(("done", worker))
    except BaseException as exc:
        messages.put(("error", worker, repr(exc)))


def _requirement_update_worker(
    repo_root: str,
    requirement_id: str,
    field: str,
    start: Any,
    messages: Any,
) -> None:
    """
    @brief Patch one independent requirement field in a spawned process.
    @version 1.0.0
    """
    try:
        root = Path(repo_root)
        config = load_config(root)
        find_requirement_record(root, requirement_id, config)
        messages.put(("ready", field))
        if not start.wait(10):
            raise RuntimeError("start signal was not received")
        if field == "priority":
            update_requirement(
                root,
                requirement_id,
                priority="Should",
                config=config,
                timestamp="2026-07-30T12:01:00Z",
            )
        else:
            update_requirement(
                root,
                requirement_id,
                rationale="Updated by the second writer.",
                config=config,
                timestamp="2026-07-30T12:02:00Z",
            )
        messages.put(("done", field))
    except BaseException as exc:
        messages.put(("error", field, repr(exc)))


def _lock_holder(
    lock_path: str,
    acquired: Any,
    release: Any,
) -> None:
    """
    @brief Hold one OS lock until the parent releases it.
    @version 1.0.0
    """
    with locked(Path(lock_path), timeout=5):
        acquired.set()
        if not release.wait(10):
            raise RuntimeError("release signal was not received")


# TEST HELPERS


def _run_workers(
    target: Any,
    arguments: list[tuple[Any, ...]],
) -> list[tuple[Any, ...]]:
    """
    @brief Start synchronized spawned workers and return completion messages.
    @version 1.0.0
    """
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    messages = context.Queue()
    processes = [
        context.Process(
            target=target,
            args=(*values, start, messages),
        )
        for values in arguments
    ]
    for process in processes:
        process.start()
    ready = [messages.get(timeout=15) for _process in processes]
    assert all(message[0] == "ready" for message in ready), ready
    start.set()
    completed = [messages.get(timeout=30) for _process in processes]
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0
    assert all(message[0] == "done" for message in completed), completed
    return completed


def _base_graph() -> Graph:
    """
    @brief Build one persisted graph suitable for concurrency tests.
    @version 1.0.0
    """
    return Graph(
        run_id=RUN_ID,
        stage="check",
        intent=Intent(id="I-concurrency", kind="feature", statement="Persist"),
    )


def _create_requirement(repo_root: Path) -> str:
    """
    @brief Create one UUID-backed requirement for update tests.
    @version 1.0.0
    """
    record = create_requirement(
        repo_root,
        category="functional",
        priority="Must",
        requirement="The persistence result remains complete.",
        rationale="Users require durable state.",
        verification="Inspection: parse the resulting snapshot.",
        config=load_config(repo_root),
        timestamp="2026-07-30T12:00:00Z",
    )
    return record.id


# TESTS


def test_atomic_replacement_preserves_old_content_before_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief A failure before replace leaves the prior complete JSON intact.
    @version 1.0.0
    """
    path = tmp_path / "state" / "graph.json"
    atomic_write_json(path, {"generation": "old"})

    def fail_replace(_source: object, _target: object) -> None:
        """
        @brief Inject interruption at the atomic publication boundary.
        @version 1.0.0
        """
        raise OSError("injected replacement failure")

    monkeypatch.setattr(persistence.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replacement failure"):
        atomic_write_json(path, {"generation": "new", "complete": True})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "generation": "old"
    }
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_atomic_replacement_publishes_complete_content_and_ignores_fixed_temp(
    tmp_path: Path,
) -> None:
    """
    @brief Exclusive unique temps cannot be redirected by a fixed sibling.
    @version 1.0.0
    """
    path = tmp_path / "state" / "graph.json"
    predictable = path.with_name(path.name + ".tmp")
    predictable.parent.mkdir(parents=True)
    predictable.write_text("unrelated sentinel\n", encoding="utf-8")

    atomic_write_json(path, {"generation": "new", "items": [1, 2, 3]})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "generation": "new",
        "items": [1, 2, 3],
    }
    assert predictable.read_text(encoding="utf-8") == "unrelated sentinel\n"


def test_stale_direct_graph_save_is_rejected_without_overwrite(
    tmp_path: Path,
) -> None:
    """
    @brief A stale in-memory graph cannot overwrite an external replacement.
    @version 1.0.0
    """
    graph = _base_graph()
    save_graph(tmp_path, graph)
    stale = load_graph(tmp_path, RUN_ID)
    current = load_graph(tmp_path, RUN_ID)
    current.access_mode = "elevated"
    save_graph(tmp_path, current)
    stale.stage = "implementation"

    with pytest.raises(GraphConflictError):
        save_graph(tmp_path, stale)

    persisted = load_graph(tmp_path, RUN_ID)
    assert persisted.access_mode == "elevated"
    assert persisted.stage == "check"


def test_graph_replace_failure_leaves_old_graph_valid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Interruption before graph replace preserves the old graph document.
    @version 1.0.0
    """
    graph = _base_graph()
    save_graph(tmp_path, graph)
    graph.stage = "implementation"

    def fail_replace(_source: object, _target: object) -> None:
        """
        @brief Inject graph replacement failure.
        @version 1.0.0
        """
        raise OSError("graph replace failed")

    monkeypatch.setattr(persistence.os, "replace", fail_replace)
    with pytest.raises(OSError, match="graph replace failed"):
        save_graph(tmp_path, graph)

    persisted = load_graph(tmp_path, RUN_ID)
    assert persisted.stage == "check"
    assert json.loads(graph_path(tmp_path, RUN_ID).read_text(encoding="utf-8"))
    assert list(
        graph_path(tmp_path, RUN_ID).parent.glob(
            f".{graph_path(tmp_path, RUN_ID).name}.*.tmp"
        )
    ) == []


def test_concurrent_graph_updates_preserve_both_mutations(
    tmp_path: Path,
) -> None:
    """
    @brief Two old-state writers reload under lock and preserve both updates.
    @version 1.0.0
    """
    save_graph(tmp_path, _base_graph())

    _run_workers(
        _graph_update_worker,
        [
            (str(tmp_path), "stage"),
            (str(tmp_path), "access"),
        ],
    )

    graph = load_graph(tmp_path, RUN_ID)
    assert graph.stage == "implementation"
    assert graph.access_mode == "elevated"


def test_concurrent_evidence_creation_has_unique_monotonic_identifiers(
    tmp_path: Path,
) -> None:
    """
    @brief Concurrent managed checks retain both records and unique IDs.
    @version 1.0.0
    """
    command = f'"{sys.executable}" -c "raise SystemExit(0)"'
    checks = [
        Check(
            id=f"CHK-00000000-0000-4000-8000-00000000000{number}",
            level="test",
            cites_spec=[],
            cites_requirement=[],
            command=command,
        )
        for number in (1, 2)
    ]
    graph = _base_graph()
    graph.checks = checks
    graph.stage_records["check"] = StageRecord(
        stage="check",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="managed",
    )
    save_graph(tmp_path, graph)

    completed = _run_workers(
        _evidence_worker,
        [
            (str(tmp_path), checks[0].id),
            (str(tmp_path), checks[1].id),
        ],
    )

    persisted = load_graph(tmp_path, RUN_ID)
    assert sorted(item.id for item in persisted.evidence) == [
        "E-0001",
        "E-0002",
    ]
    assert len({item.id for item in persisted.evidence}) == 2
    assert sorted(message[2] for message in completed) == [
        "E-0001",
        "E-0002",
    ]


def test_concurrent_journal_appends_are_complete_parseable_records(
    tmp_path: Path,
) -> None:
    """
    @brief Spawned appenders cannot interleave or truncate JSON lines.
    @version 1.0.0
    """
    count = 12
    _run_workers(
        _journal_worker,
        [
            (str(tmp_path), "alpha", count),
            (str(tmp_path), "beta", count),
        ],
    )

    lines = journal_path(tmp_path, RUN_ID).read_text(
        encoding="utf-8"
    ).splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == count * 2
    assert {
        (record["data"]["worker"], record["data"]["index"])
        for record in records
    } == {
        (worker, index)
        for worker in ("alpha", "beta")
        for index in range(count)
    }


def test_journal_replace_failure_preserves_complete_prior_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Journal publication failure leaves the earlier journal parseable.
    @version 1.0.0
    """
    append_journal(tmp_path, RUN_ID, "first", {"value": 1})
    original = journal_path(tmp_path, RUN_ID).read_bytes()

    def fail_replace(_source: object, _target: object) -> None:
        """
        @brief Inject journal replacement failure.
        @version 1.0.0
        """
        raise OSError("journal replace failed")

    monkeypatch.setattr(persistence.os, "replace", fail_replace)
    with pytest.raises(OSError, match="journal replace failed"):
        append_journal(tmp_path, RUN_ID, "second", {"value": 2})

    assert journal_path(tmp_path, RUN_ID).read_bytes() == original
    assert [json.loads(line) for line in original.decode("utf-8").splitlines()]


def test_concurrent_requirement_updates_preserve_independent_fields(
    tmp_path: Path,
) -> None:
    """
    @brief Same-requirement writers serialize complete update transactions.
    @version 1.0.0
    """
    requirement_id = _create_requirement(tmp_path)

    _run_workers(
        _requirement_update_worker,
        [
            (str(tmp_path), requirement_id, "priority"),
            (str(tmp_path), requirement_id, "rationale"),
        ],
    )

    record = find_requirement_record(
        tmp_path,
        requirement_id,
        load_config(tmp_path),
    )
    assert record.priority == "Should"
    assert record.rationale == "Updated by the second writer."


def test_external_requirement_change_before_publish_returns_typed_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Non-cooperative external modification is never overwritten silently.
    @version 1.0.0
    """
    requirement_id = _create_requirement(tmp_path)
    config = load_config(tmp_path)
    current = find_requirement_record(tmp_path, requirement_id, config)
    target = tmp_path / str(current.source_file)
    original_check = requirements_module._require_existing_spec
    changed = False

    def modify_after_load(repo_root: Path, spec_ref: str) -> None:
        """
        @brief Replace the source after update load but before CAS publish.
        @version 1.0.0
        """
        nonlocal changed
        original_check(repo_root, spec_ref)
        if changed:
            return
        changed = True
        external = replace(
            current,
            rationale="External writer won.",
            last_updated="2026-07-30T12:03:00Z",
        )
        atomic_write_text(target, render_requirement_toml(external))

    monkeypatch.setattr(
        requirements_module,
        "_require_existing_spec",
        modify_after_load,
    )
    with pytest.raises(RequirementConflictError) as conflict:
        update_requirement(
            tmp_path,
            requirement_id,
            priority="Could",
            config=config,
            timestamp="2026-07-30T12:04:00Z",
        )

    assert conflict.value.code == "REQUIREMENT-STALE-UPDATE"
    persisted = find_requirement_record(tmp_path, requirement_id, config)
    assert persisted.rationale == "External writer won."
    assert persisted.priority == "Must"


def test_requirement_replace_failure_leaves_valid_old_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Requirement replacement failure never truncates the current TOML.
    @version 1.0.0
    """
    requirement_id = _create_requirement(tmp_path)
    config = load_config(tmp_path)
    before = find_requirement_record(tmp_path, requirement_id, config)

    def fail_replace(_source: object, _target: object) -> None:
        """
        @brief Inject requirement replacement failure.
        @version 1.0.0
        """
        raise OSError("requirement replace failed")

    monkeypatch.setattr(persistence.os, "replace", fail_replace)
    with pytest.raises(OSError, match="requirement replace failed"):
        update_requirement(
            tmp_path,
            requirement_id,
            priority="Could",
            config=config,
            timestamp="2026-07-30T12:05:00Z",
        )

    after = find_requirement_record(tmp_path, requirement_id, config)
    assert after == before


def test_repowise_replace_failure_preserves_valid_old_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief RepoWise snapshot uses the shared crash-safe writer.
    @version 1.0.0
    """
    path = tmp_path / ".agentic" / "runs" / RUN_ID / "repowise.json"
    _atomic_json(path, {"generation": "old"})

    def fail_replace(_source: object, _target: object) -> None:
        """
        @brief Inject RepoWise replacement failure.
        @version 1.0.0
        """
        raise OSError("RepoWise replace failed")

    monkeypatch.setattr(persistence.os, "replace", fail_replace)
    with pytest.raises(OSError, match="RepoWise replace failed"):
        _atomic_json(path, {"generation": "new"})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "generation": "old"
    }


def test_live_lock_times_out_and_unlocked_stale_file_is_reused(
    tmp_path: Path,
) -> None:
    """
    @brief Live locks fail closed; retained stale lock files need no deletion.
    @version 1.0.0
    """
    context = multiprocessing.get_context("spawn")
    acquired = context.Event()
    release = context.Event()
    path = scoped_lock_path(tmp_path, "runs", "path with spaces")
    process = context.Process(
        target=_lock_holder,
        args=(str(path), acquired, release),
    )
    process.start()
    assert acquired.wait(10)
    try:
        with pytest.raises(LockTimeoutError):
            with locked(path, timeout=0.2):
                pass
    finally:
        release.set()
        process.join(timeout=15)
    assert process.exitcode == 0
    assert path.is_file()
    with locked(path, timeout=2):
        assert path.is_file()


# END OF FILE
