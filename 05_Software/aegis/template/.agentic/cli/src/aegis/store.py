#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file store.py
@brief Persistence helpers for agentic workflow run state.
@details Mirrors the packaged CLI implementation shipped into generated projects.
@details ``repo_root_from`` (0.3.0, code-review follow-up) now refuses a
         resolved root that is itself named ``.agentic`` or nested inside one:
         previously, invoking the CLI with the process working directory
         mistakenly set to a project's own ``.agentic`` folder (or a
         previously self-nested copy of it) silently created another
         ``.agentic/.agentic/...`` layer instead of failing, since
         ``agentic_root()``/``write_current_run()``/``init_graph()`` all
         ``mkdir(parents=True, exist_ok=True)`` unconditionally.
@details ``repo_root_from`` (0.4.0, analysis-review follow-up) resolves the
         workflow root by upward discovery instead of trusting the working
         directory verbatim: the nearest ancestor containing an ``.agentic``
         directory wins, then the nearest ancestor containing ``.git``, then
         the candidate itself (legacy greenfield behavior). Previously, any
         command run from a repository subdirectory treated that subdirectory
         as the root, so ``status`` reported "No active agentic run" and
         following its advice scaffolded a nested ``src/.agentic/`` silently;
         a working directory inside ``.agentic`` itself now heals to the
         surrounding project root instead of exiting.
@details ``init_graph`` (0.4.0) publishes the active-run selector atomically
         below ignored, worktree-local workspace state only after the initial
         graph has been saved successfully.
@details ``resolve_run_id`` and ``load_graph`` (0.1.0) implement the strict
         explicit-first active-run contract with typed, actionable failures.
@details Graph mutations now reload under a repository/run-scoped OS lock,
         reject stale direct saves, publish through atomic sibling replacement,
         and serialize crash-safe journal replacement.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 0.8.0
"""

# IMPORTS

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from hashlib import sha256
import json
import os  # noqa: F401 - retained for the established fault-injection seam
from pathlib import Path
import re
from typing import Any, Callable, Concatenate, Iterator, ParamSpec, TypeVar
from uuid import uuid4

from .models import ADOPTION_STAGES, AccessMode, Evidence, Graph, Intent, RunKind, Stage, now_iso
from .persistence import (
    PersistenceError,
    atomic_write_bytes,
    atomic_write_text,
    locked,
    scoped_lock_path,
)

# CONSTANTS

AGENTIC_DIR = ".agentic"
RUNS_DIR = "runs"
WORKSPACE_DIR = ".workspace"
WORKSPACE_STATE_DIR = "state"
CURRENT_RUN = "current_run"
GRAPH_FILE = "graph.json"
JOURNAL_FILE = "journal.jsonl"
RUN_ID_PATTERN = re.compile(
    r"^(feature|fix|change|adoption)-"
    r"(?P<timestamp>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z)-"
    r"[0-9a-f]{8}$"
)
_GRAPH_PARAMETERS = ParamSpec("_GRAPH_PARAMETERS")
_GRAPH_RESULT = TypeVar("_GRAPH_RESULT")

# DATA MODELS / TYPEDEFINITIONS


@dataclass
class RunResolutionError(Exception):
    """
    @brief      Describe one stable active-run resolution failure.
    @param[in]  code Stable machine-readable error code.
    @param[in]  pointer_path Repository-relative pointer path, when applicable.
    @param[in]  run_id Valid-shaped candidate run ID, when available.
    @param[in]  message Human-readable failure description.
    @param[in]  remediation Concrete corrective action for an agent.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """

    code: str
    pointer_path: str | None
    run_id: str | None
    message: str
    remediation: str

    def __str__(self) -> str:
        """
        @brief      Render the stable text error contract.
        @return     Error code, message, and remediation.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-22
        @version    0.1.0
        """
        return f"{self.code}: {self.message}\n{self.remediation}"

    def to_dict(self) -> dict[str, str | None]:
        """
        @brief      Serialize the stable run-resolution fields.
        @return     JSON-compatible error mapping.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-22
        @version    0.1.0
        """
        return {
            "code": self.code,
            "pointer_path": self.pointer_path,
            "run_id": self.run_id,
            "message": self.message,
            "remediation": self.remediation,
        }


class GraphConflictError(PersistenceError):
    """
    @brief Reject a stale in-memory graph before it can overwrite newer state.
    @version 1.0.0
    """

    code = "GRAPH-STALE-UPDATE"

    def __init__(self, run_id: str) -> None:
        """
        @brief Initialize an actionable stale-graph conflict.
        @param[in] run_id Conflicting run identity.
        @version 1.0.0
        """
        self.run_id = run_id
        super().__init__(
            f"{self.code}: graph {run_id} changed after it was loaded. "
            "Reload the run and retry the operation."
        )

# PUBLIC API


def repo_root_from(path: Path | None = None) -> Path:
    """
    @brief      Resolve the workflow root by upward marker discovery.
    @param[in]  path Optional starting directory; defaults to the process
                working directory.
    @return     Resolved workflow root.
    @details    Discovery order: the nearest ancestor (starting with the
                candidate itself) that contains an ``.agentic`` directory,
                else the nearest ancestor that contains ``.git``, else the
                candidate itself. This makes every CLI command safe to run
                from any repository subdirectory — including from inside
                ``.agentic`` itself, which previously exited — and prevents
                ``start`` from scaffolding a second ``.agentic/`` below an
                existing install.
    @exception  SystemExit Raised by the safety-net guard when the resolved
                root is itself named ``.agentic`` or nested inside one (only
                reachable for paths that do not exist on disk).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.3.0
    """
    candidate = (path or Path.cwd()).resolve()
    root = _discover_root(candidate)
    _reject_nested_agentic_root(root)
    return root


def _discover_root(candidate: Path) -> Path:
    """
    @brief      Walk upward from a candidate directory to the workflow root.
    @param[in]  candidate Resolved starting directory.
    @return     The discovered workflow root, or the candidate itself.
    @details    Two full passes, not one nearest-marker pass: ``.agentic`` is
                the authoritative AEGIS marker and must win even when a
                vendored checkout puts a ``.git`` closer to the candidate —
                a nearest-marker rule would resolve into the vendored
                repository and reintroduce the nested-scaffold defect there.
                ``.git`` is checked with ``exists()`` rather than ``is_dir()``
                because linked worktrees mark their root with a ``.git``
                file. With no marker anywhere upward the candidate itself is
                returned, preserving the greenfield ``start`` behavior.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    directories = (candidate, *candidate.parents)
    for directory in directories:
        if (directory / AGENTIC_DIR).is_dir():
            return directory
    for directory in directories:
        if (directory / ".git").exists():
            return directory
    return candidate


def _reject_nested_agentic_root(root: Path) -> None:
    """
    @brief      Refuse a workflow root that is itself named ``.agentic`` or
                nested inside one.
    @param[in]  root Resolved candidate workflow root.
    @return     None
    @details    Safety net behind :func:`_discover_root`. For any path that
                exists on disk discovery heals this case first (the parent
                containing ``.agentic`` always wins), so the guard only fires
                for nonexistent-path fallbacks — where the unchecked
                ``mkdir(parents=True, exist_ok=True)`` write paths
                (``write_current_run``, ``init_graph``) could still grow an
                ``.agentic/.agentic/...`` layer.
    @exception  SystemExit Raised when ``root`` matches or contains an
                ``.agentic`` path segment.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    if root.name == AGENTIC_DIR or AGENTIC_DIR in root.parts:
        raise SystemExit(
            f"Refusing to use '{root}' as the workflow root: it is the "
            f"'{AGENTIC_DIR}' directory itself or nested inside one. Run this "
            "command from the project root, not from inside '.agentic'."
        )


def agentic_root(repo_root: Path) -> Path:
    """
    @brief      Resolve agentic root workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return repo_root / AGENTIC_DIR


def runs_root(repo_root: Path) -> Path:
    """
    @brief      Handle runs root workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return agentic_root(repo_root) / RUNS_DIR


def workspace_root(repo_root: Path) -> Path:
    """
    @brief      Return the ignored, worktree-local AEGIS workspace root.
    @param[in]  repo_root Repository root.
    @return     `.agentic/.workspace` path without creating it.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    return agentic_root(repo_root) / WORKSPACE_DIR


def workspace_state_root(repo_root: Path) -> Path:
    """
    @brief      Return the worktree-local state directory.
    @param[in]  repo_root Repository root.
    @return     `.agentic/.workspace/state` path without creating it.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    return workspace_root(repo_root) / WORKSPACE_STATE_DIR


def current_run_path(repo_root: Path) -> Path:
    """
    @brief      Return the worktree-local active-run pointer path.
    @param[in]  repo_root Repository root.
    @return     `.agentic/.workspace/state/current_run` path.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    return workspace_state_root(repo_root) / CURRENT_RUN


def new_run_id(kind: str) -> str:
    """
    @brief      Create new run id workflow behavior.
    @param[in]  kind Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return f"{kind}-{now_iso().replace(':', '').replace('+0000', 'Z')}-{uuid4().hex[:8]}"


def run_dir(repo_root: Path, run_id: str) -> Path:
    """
    @brief      Run dir workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  run_id Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return runs_root(repo_root) / run_id


def graph_path(repo_root: Path, run_id: str) -> Path:
    """
    @brief      Resolve graph path workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  run_id Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return run_dir(repo_root, run_id) / GRAPH_FILE


def journal_path(repo_root: Path, run_id: str) -> Path:
    """
    @brief      Resolve journal path workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  run_id Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return run_dir(repo_root, run_id) / JOURNAL_FILE


def write_current_run(repo_root: Path, run_id: str) -> None:
    """
    @brief      Atomically publish the worktree-local active-run pointer.
    @param[in]  repo_root Repository root.
    @param[in]  run_id Valid run ID to publish.
    @return     None.
    @exception  RunResolutionError If `run_id` is malformed.
    @exception  OSError If the state directory or pointer cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.3.0
    """
    if not _is_valid_run_id(run_id):
        raise _explicit_run_error(None, received=run_id)
    atomic_write_text(current_run_path(repo_root), f"{run_id}\n")


def resolve_run_id(repo_root: Path, explicit_run_id: str | None = None) -> str:
    """
    @brief      Resolve and validate an explicit or worktree-selected run ID.
    @param[in]  repo_root Repository root.
    @param[in]  explicit_run_id Optional run ID that takes precedence over the
                workspace pointer.
    @return     Validated run ID whose graph is readable and internally
                consistent.
    @exception  RunResolutionError If the selection or graph is invalid.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    if explicit_run_id is not None:
        if not _is_valid_run_id(explicit_run_id):
            raise _explicit_run_error(None, received=explicit_run_id)
        _load_selected_graph(repo_root, explicit_run_id, explicit=True)
        return explicit_run_id

    pointer = current_run_path(repo_root)
    pointer_relative = _pointer_relative_path()
    if not pointer.exists():
        raise RunResolutionError(
            code="RUN-POINTER-MISSING",
            pointer_path=pointer_relative,
            run_id=None,
            message="No active AEGIS run is selected for this worktree.",
            remediation=(
                "Start one with `aegis run start <kind>` or rerun this command "
                "with `--run <existing-run-id>`.\n"
                f"Expected pointer: {pointer_relative}"
            ),
        )
    try:
        raw = pointer.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError):
        raise _invalid_pointer_error() from None
    if not text.endswith("\n") or text.count("\n") != 1:
        raise _invalid_pointer_error()
    run_id = text[:-1]
    if not _is_valid_run_id(run_id):
        raise _invalid_pointer_error()
    _load_selected_graph(repo_root, run_id, explicit=False)
    return run_id


# LOCAL HELPERS


def _pointer_relative_path() -> str:
    """
    @brief      Return the stable repository-relative pointer path.
    @return     POSIX-form pointer path used in errors and JSON.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    return f"{AGENTIC_DIR}/{WORKSPACE_DIR}/{WORKSPACE_STATE_DIR}/{CURRENT_RUN}"


def _is_valid_run_id(run_id: str) -> bool:
    """
    @brief      Validate the lexical and real-UTC run-ID contract.
    @param[in]  run_id Candidate run ID.
    @return     `True` only for a canonical supported run ID.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    match = RUN_ID_PATTERN.fullmatch(run_id)
    if match is None:
        return False
    try:
        datetime.strptime(match.group("timestamp"), "%Y-%m-%dT%H%M%SZ")
    except ValueError:
        return False
    return True


def _invalid_pointer_error() -> RunResolutionError:
    """
    @brief      Build the stable malformed-pointer error.
    @return     `RUN-POINTER-INVALID` error.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    pointer_relative = _pointer_relative_path()
    return RunResolutionError(
        code="RUN-POINTER-INVALID",
        pointer_path=pointer_relative,
        run_id=None,
        message=f"{pointer_relative} does not contain a valid run ID.",
        remediation=(
            "Start a new run or replace the pointer by starting/selecting a valid run; "
            "do not edit run graphs by guessing an ID."
        ),
    )


def _explicit_run_error(
    run_id: str | None,
    *,
    received: str | None = None,
) -> RunResolutionError:
    """
    @brief      Build the stable explicit-selection error.
    @param[in]  run_id Valid-shaped candidate, when available.
    @param[in]  received Original malformed value, when no valid candidate is
                available for the serialized `run_id` field.
    @return     `RUN-ID-NOT-FOUND` error.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    display = run_id if run_id is not None else (received or "<invalid-run-id>")
    return RunResolutionError(
        code="RUN-ID-NOT-FOUND",
        pointer_path=None,
        run_id=run_id,
        message=(
            f"Explicit run {display} does not resolve to a valid graph under "
            f"{AGENTIC_DIR}/{RUNS_DIR}/."
        ),
        remediation=(
            "List the available run directories or start a new run, then retry "
            "with the exact ID."
        ),
    )


def _stale_pointer_error(run_id: str) -> RunResolutionError:
    """
    @brief      Build the stable stale-pointer error.
    @param[in]  run_id Valid-shaped workspace selection.
    @return     `RUN-POINTER-STALE` error.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    return RunResolutionError(
        code="RUN-POINTER-STALE",
        pointer_path=_pointer_relative_path(),
        run_id=run_id,
        message=(
            f"This worktree selects {run_id}, but {AGENTIC_DIR}/{RUNS_DIR}/"
            f"{run_id}/{GRAPH_FILE} is missing or invalid."
        ),
        remediation=(
            "Start a new run or pass `--run <existing-run-id>` explicitly."
        ),
    )


def _load_selected_graph(repo_root: Path, run_id: str, *, explicit: bool) -> Graph:
    """
    @brief      Validate containment and parse one selected graph.
    @param[in]  repo_root Repository root.
    @param[in]  run_id Canonical run ID.
    @param[in]  explicit Whether failures use the explicit-selection contract.
    @return     Parsed, internally consistent graph.
    @exception  RunResolutionError If containment, I/O, JSON, model parsing,
                or graph identity validation fails.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.3.0
    """
    error = _explicit_run_error(run_id) if explicit else _stale_pointer_error(run_id)
    root = runs_root(repo_root).resolve()
    path = graph_path(repo_root, run_id)
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        raise error from None
    if not resolved.is_file():
        raise error
    try:
        raw = resolved.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("graph JSON must be an object")
        graph = Graph.from_dict(payload)
    except (
        AttributeError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        raise error from None
    if graph.run_id != run_id:
        raise error
    graph._source_digest = sha256(raw).hexdigest()
    graph._source_state_digest = sha256(_serialize_graph(graph)).hexdigest()
    return graph


def init_graph(
    repo_root: Path,
    kind: RunKind,
    statement: str,
    access_mode: AccessMode = "standard",
    scope_hint: list[str] | None = None,
) -> Graph:
    """
    @brief      Handle init graph workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  kind Input value used by the workflow helper.
    @param[in]  statement Input value used by the workflow helper.
    @param[in]  access_mode Input value used by the workflow helper.
    @param[in]  scope_hint Optional extra roots accepted by the scope advisory.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.6.0
    """
    run_id = new_run_id(kind)
    starting_stage: Stage = ADOPTION_STAGES[0] if kind == "adoption" else "intake"
    graph = Graph(
        run_id=run_id,
        stage=starting_stage,
        intent=Intent(
            id=f"I-{uuid4()}",
            kind=kind,
            statement=statement,
            scope_hint=list(scope_hint or []),
        ),
        access_mode=access_mode,
    )
    run_dir(repo_root, run_id).mkdir(parents=True, exist_ok=True)
    save_graph(repo_root, graph)
    write_current_run(repo_root, run_id)
    append_journal(
        repo_root,
        run_id,
        "run.started",
        {
            "kind": kind,
            "statement": statement,
            "access_mode": access_mode,
            "scope_hint": graph.intent.scope_hint,
        },
    )
    return graph


def load_graph(repo_root: Path, run_id: str) -> Graph:
    """
    @brief      Load one already selected run graph without consulting state.
    @param[in]  repo_root Repository root.
    @param[in]  run_id Explicit, previously resolved run ID.
    @return     Parsed graph whose internal run ID matches `run_id`.
    @exception  RunResolutionError If the ID or graph is invalid.
    @note       Call :func:`resolve_run_id` before this function when a command
                may use the workspace pointer.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    if not _is_valid_run_id(run_id):
        raise _explicit_run_error(None, received=run_id)
    return _load_selected_graph(repo_root, run_id, explicit=True)


def save_graph(repo_root: Path, graph: Graph) -> None:
    """
    @brief Atomically publish a graph unless its loaded source is stale.
    @param[in] repo_root Repository root.
    @param[in,out] graph Complete graph carrying its last loaded digest.
    @return None.
    @exception GraphConflictError If a newer graph is already on disk.
    @exception OSError If persistence or replacement fails.
    @version 0.2.0
    """
    path = graph_path(repo_root, graph.run_id)
    content = _serialize_graph(graph)
    with locked(run_lock_path(repo_root, graph.run_id)):
        expected = getattr(graph, "_source_digest", None)
        if path.is_file() and expected is not None:
            current = sha256(path.read_bytes()).hexdigest()
            if current != expected:
                raise GraphConflictError(graph.run_id)
        atomic_write_bytes(path, content)
        graph._source_digest = sha256(content).hexdigest()
        graph._source_state_digest = sha256(content).hexdigest()


def append_journal(
    repo_root: Path,
    run_id: str,
    event: str,
    data: dict[str, Any],
) -> None:
    """
    @brief Serialize one complete UTF-8 JSON line through atomic replacement.
    @param[in] repo_root Repository root.
    @param[in] run_id Run identity selecting the journal.
    @param[in] event Stable event name.
    @param[in] data JSON-compatible event data.
    @return None.
    @exception PersistenceError If the existing journal ends in a partial line.
    @exception OSError If persistence or replacement fails.
    @version 0.2.0
    """
    path = journal_path(repo_root, run_id)
    entry = {"time": now_iso(), "event": event, "data": data}
    line = (json.dumps(entry, sort_keys=True) + "\n").encode("utf-8")
    with locked(journal_lock_path(repo_root, run_id)):
        existing = path.read_bytes() if path.is_file() else b""
        if existing and not existing.endswith(b"\n"):
            raise PersistenceError(
                f"journal {path} ends with an incomplete record; "
                "restore a valid journal before appending"
            )
        atomic_write_bytes(path, existing + line)


def run_lock_path(repo_root: Path, run_id: str) -> Path:
    """
    @brief Return the repository/run-scoped graph mutation lock.
    @param[in] repo_root Repository root.
    @param[in] run_id Run identity.
    @return Worktree-local persistent lock path.
    @version 1.0.0
    """
    return scoped_lock_path(repo_root, "runs", run_id)


def journal_lock_path(repo_root: Path, run_id: str) -> Path:
    """
    @brief Return the repository/run-scoped journal append lock.
    @param[in] repo_root Repository root.
    @param[in] run_id Run identity.
    @return Worktree-local persistent lock path.
    @version 1.0.0
    """
    return scoped_lock_path(repo_root, "journals", run_id)


def next_evidence_id(graph: Graph, offset: int = 0) -> str:
    """
    @brief Allocate the next collision-safe monotonic evidence identifier.
    @param[in] graph Authoritative graph held by the current run transaction.
    @param[in] offset Additional identifier offset for a validated batch.
    @return Existing-compatible `E-NNNN` identifier.
    @version 1.0.0
    """
    numbers = [
        int(item.id[2:])
        for item in graph.evidence
        if re.fullmatch(r"E-[0-9]+", item.id)
    ]
    number = max(numbers, default=0) + offset + 1
    identifiers = {item.id for item in graph.evidence}
    candidate = f"E-{number:04d}"
    while candidate in identifiers:
        number += 1
        candidate = f"E-{number:04d}"
    return candidate


@contextmanager
def graph_transaction(repo_root: Path, graph: Graph) -> Iterator[Graph]:
    """
    @brief Reload and hold the authoritative graph for one complete mutation.
    @param[in] repo_root Repository root.
    @param[in,out] graph Caller graph refreshed in place under the run lock.
    @return Iterator yielding the refreshed graph.
    @exception RunResolutionError If the authoritative graph is invalid.
    @version 1.0.0
    """
    with locked(run_lock_path(repo_root, graph.run_id)) as lock:
        persisted = graph_path(repo_root, graph.run_id)
        if not lock.reentrant and persisted.is_file():
            current_digest = sha256(persisted.read_bytes()).hexdigest()
            expected_digest = getattr(graph, "_source_digest", None)
            if expected_digest != current_digest:
                source_state_digest = getattr(
                    graph,
                    "_source_state_digest",
                    None,
                )
                current_state_digest = sha256(
                    _serialize_graph(graph)
                ).hexdigest()
                if (
                    source_state_digest is not None
                    and current_state_digest != source_state_digest
                ):
                    raise GraphConflictError(graph.run_id)
                _replace_graph_state(
                    graph,
                    _load_selected_graph(
                        repo_root,
                        graph.run_id,
                        explicit=True,
                    ),
                )
        try:
            yield graph
        except BaseException:
            if not lock.reentrant:
                try:
                    _replace_graph_state(
                        graph,
                        _load_selected_graph(
                            repo_root,
                            graph.run_id,
                            explicit=True,
                        ),
                    )
                except (OSError, RunResolutionError, ValueError):
                    pass
            raise


def serialized_graph_mutation(
    function: Callable[
        Concatenate[Path, Graph, _GRAPH_PARAMETERS],
        _GRAPH_RESULT,
    ],
) -> Callable[
    Concatenate[Path, Graph, _GRAPH_PARAMETERS],
    _GRAPH_RESULT,
]:
    """
    @brief Decorate a graph mutator with authoritative reload and run locking.
    @param[in] function Mutator whose first arguments are repository and graph.
    @return Wrapped mutator with the same public signature.
    @version 1.0.0
    """
    @wraps(function)
    def wrapper(
        repo_root: Path,
        graph: Graph,
        *args: _GRAPH_PARAMETERS.args,
        **kwargs: _GRAPH_PARAMETERS.kwargs,
    ) -> _GRAPH_RESULT:
        """
        @brief Run one graph mutation inside its serialized transaction.
        @version 1.0.0
        """
        with graph_transaction(repo_root, graph):
            return function(repo_root, graph, *args, **kwargs)

    return wrapper


@serialized_graph_mutation
def add_evidence(repo_root: Path, graph: Graph, evidence: Evidence) -> Graph:
    """
    @brief      Add evidence workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  graph Input value used by the workflow helper.
    @param[in]  evidence Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.3.0
    """
    if any(item.id == evidence.id for item in graph.evidence):
        raise PersistenceError(
            f"evidence identifier already exists: {evidence.id}"
        )
    graph.evidence.append(evidence)
    save_graph(repo_root, graph)
    append_journal(repo_root, graph.run_id, "evidence.recorded", evidence.__dict__)
    return graph


@serialized_graph_mutation
def set_stage(repo_root: Path, graph: Graph, stage: Stage) -> Graph:
    """
    @brief      Set stage workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  graph Input value used by the workflow helper.
    @param[in]  stage Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    graph.stage = stage
    save_graph(repo_root, graph)
    append_journal(repo_root, graph.run_id, "stage.set", {"stage": stage})
    return graph


@serialized_graph_mutation
def set_access_mode(
    repo_root: Path,
    graph: Graph,
    access_mode: AccessMode,
    reason: str,
) -> Graph:
    """
    @brief      Set access mode workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  graph Input value used by the workflow helper.
    @param[in]  access_mode Input value used by the workflow helper.
    @param[in]  reason Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    graph.access_mode = access_mode
    save_graph(repo_root, graph)
    append_journal(
        repo_root,
        graph.run_id,
        "access_mode.set",
        {"access_mode": access_mode, "reason": reason},
    )
    return graph


def _replace_graph_state(target: Graph, source: Graph) -> None:
    """
    @brief Refresh one caller-held graph object without changing its identity.
    @param[in,out] target Graph instance retained by the caller.
    @param[in] source Newly loaded authoritative graph.
    @return None.
    @version 1.0.0
    """
    target.__dict__.clear()
    target.__dict__.update(source.__dict__)


def _serialize_graph(graph: Graph) -> bytes:
    """
    @brief Serialize one graph using the canonical persisted JSON format.
    @param[in] graph Complete graph state.
    @return UTF-8 bytes ending in one newline.
    @version 1.0.0
    """
    return (
        json.dumps(graph.to_dict(), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


# END OF FILE
