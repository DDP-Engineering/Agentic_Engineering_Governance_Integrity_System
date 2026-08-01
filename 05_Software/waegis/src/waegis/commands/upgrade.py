#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file upgrade.py
@brief ``waegis upgrade --repo PATH [--dry-run] [--json] [--payload PATH]``:
       the plan §10.2 three-way, manifest-driven payload upgrade (T6.2).
       Closes milestone M6.
@details **This is the highest data-loss-risk command in WAEGIS** (plan §14).
         Every write path is built so an operator's local edits can never be
         silently destroyed: nothing is auto-resolved, the manifest is rewritten
         only *after* a successful post-apply smoke re-verify, and an aborted
         run is always safely resumable.
@details **Three-way classification.** For every payload-relative ``path`` in
         ``union(manifest.files, new-payload files)`` — with ``manifest.generated``
         paths and the manifest's own path removed from the union entirely — the
         command compares three hashes:

         - ``O`` = the manifest's recorded *original* (as-shipped) hash, or
           ``None`` when the path is not tracked (a new upstream file, or an
           adoption-time ``skipped`` path, which copier records under
           ``skipped`` rather than ``files``);
         - ``L`` = the current on-disk hash at the repo, or ``None`` when the
           file no longer exists;
         - ``N`` = the new payload's hash for that path, or ``None`` when the
           new payload no longer ships it.

         An absent side (``None``) is treated as unequal to every hash and to
         another absent side. The full table (plan §10.2):

         | O | L | N | condition          | action                     |
         |---|---|---|--------------------|----------------------------|
         | . | =O| =O| unchanged          | UNCHANGED (skip)           |
         | . | =O| !=| upstream changed   | AUTO_APPLY_NEW             |
         | . |!=O| =O| local changed only | KEEP_LOCAL                 |
         | . |!=O| !=| L=N                | ALREADY_CONVERGED          |
         | . |!=O| !=| L!=N               | CONFLICT (hook)            |
         | - | - | +| new upstream, L=-  | ADD_NEW                    |
         | - | + | +| new upstream, L=N  | NEW_CONVERGED              |
         | - | + | +| new upstream, L!=N | CONFLICT (hook)            |
         | + | =O| - | removed, unmodified| DELETE_REMOVED             |
         | + |!=O| - | removed, modified  | KEEP_MODIFIED_REMOVED      |
         | + | - | - | removed, gone      | DELETE_REMOVED (no-op)     |

         ``generated`` files (currently ``.agentic/workflow.toml``) are excluded
         from the union up front: they are never classified, never appear in any
         action list, and are never written — doctor (T6.1) validates them
         against the new payload's schema instead. ``skipped`` files are *not*
         exempted: being ``O``-absent, they naturally re-enter the
         new-upstream rows and are re-offered (plan §6).
@details **Apply ordering & the manifest-rewrite-last barrier.** Mirrors T3.2's
         copier no-partial-write discipline, extended with a smoke barrier:
         (1a) classify — read-only, no hook; ``--dry-run`` returns here having
         written nothing and touched no manifest. (1b) decide — the conflict
         hook is called exactly once per true three-way conflict, still
         read-only. (2) apply every file write (auto-apply, add, delete, and
         each resolved conflict outcome). (2.5) **barrier** — run
         ``verify.cli-smoke`` + ``verify.workflow-smoke``; if either fails the
         function STOPS and the manifest is *not* rewritten (the repo's files
         may have changed but the old manifest still truthfully describes the
         old state, so a re-run or manual revert both stay coherent). (3) only
         on a fully successful apply + smoke re-verify is the manifest rewritten
         (new ``payload_version``, new original hashes) — the single
         :func:`write_manifest` call, textually last.
@details **Resume-safety.** Because the manifest is only rewritten in step 3, a
         run aborted after step 2 leaves the OLD manifest plus a partially- or
         fully-updated disk. A second ``waegis upgrade`` recomputes the plan
         from scratch against the unchanged old manifest and the current disk:
         already-applied files have ``L=N`` while ``O`` still holds the old
         original, so they classify ALREADY_CONVERGED / NEW_CONVERGED (no
         re-write); deleted files classify DELETE_REMOVED (no-op). The run
         converges to the correct final state with no double-apply.
@details **Conflict resolution & the frozen §5 contract.** ``waegis upgrade``
         exposes exactly ``--repo/--dry-run/--json/--payload`` (plan §5, frozen
         per §15 D13) — no ``--answers``/``--non-interactive``. A conflict is
         NEVER resolved without going through the caller-supplied hook (the same
         non-negotiable rule as T3.2's copier). :func:`run_upgrade` therefore
         accepts an ``on_conflict`` hook / ``resolutions`` table / ``asker`` as
         *function* parameters (the test + WADORE seam, mirroring how adopt.py's
         T5.2 hook is driven). The interactive CLI path drives the hook with a
         :class:`waegis.io.prompts.ConsoleAsker`; the ``--json`` (non-interactive)
         CLI path supplies none, so any true conflict makes the command
         stop-and-report — it applies nothing and exits non-zero rather than
         guess.
@details **copier.py reuse.** ``ConflictDecision``, ``SIDECAR_SUFFIX``,
         ``should_exclude``, and the byte-verbatim ``shutil.copy2`` primitive
         are reused verbatim; ``hash_file``/``Manifest``/``FileEntry``/
         ``write_manifest`` come from the manifest module. ``copy_payload`` is
         deliberately *not* called — its conflict model is two-way
         (local-vs-payload), it re-scans the whole tree, and it writes the
         manifest inline via ``build_manifest`` (which re-hashes disk and would
         mis-record the local hash rather than the new original for a
         KEEP_LOCAL file). The three-way orchestration and the
         manifest-rewrite-last barrier are new logic here.
@details **``--json`` seam (frozen, WADORE-relevant per plan §5/§15 D13).** See
         :meth:`UpgradeReport.to_dict` for the full field-name contract;
         changing those names is a wizard MAJOR version bump.
"""

# IMPORTS

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import IO, Any, Callable, Mapping

from ..consent import ConsentDecision, mutation_consent
from ..engine import STATUS_COMPLETED, STATUS_FAILED, Journal, StepResult, StepStatus, waegis_home
from ..io.answers import AnswersFileError, load_answers_file
from ..io.envelope import (
    EXIT_NEEDS_INPUT,
    EXIT_OK as ENVELOPE_EXIT_OK,
    EXIT_OPERATIONAL,
    EXIT_VALIDATION,
    write_envelope,
)
from ..io.prompts import ConsoleAsker, FieldSpec
from ..io.reports import ProbeFindingRecord
from ..lifecycle import find_resume_journal, stable_fingerprint
from ..payload.copier import (
    CopierError,
    ConflictDecision,
    ensure_executable,
    inspect_payload,
    normalize_conflict_decision_value,
)
from ..payload.locate import read_payload_version
from ..payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    MANIFEST_VERSION,
    FileEntry,
    Manifest,
    ManifestLoadResult,
    ManifestState,
    digest_file_entries,
    hash_file,
    load_manifest,
    resolve_managed_path,
    write_manifest,
)
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..repo import gitops
from ..repowise import (
    REPOWISE_ANSWER_KEYS,
    RepoWiseError,
    distribution_edition,
    lifecycle_repowise,
    repowise_status,
)
from ..transaction import FileTransaction
from ..version import WIZARD_VERSION
from ..verification import HASH_TRUSTED_HOOK_CONFIGS, smoke_reverify
from ._shared import (
    CommandOptions,
    PAYLOAD_VALIDATION_ERRORS,
    locate_validated_payload,
    recover_transactions_or_emit,
    sidecar_relative_path,
)

# CONSTANTS

# @brief Fallback payload_version recorded when the new payload ships no
#        readable version declaration (mirrors copier's UNKNOWN_PAYLOAD_VERSION).
UNKNOWN_PAYLOAD_VERSION = "unknown"

# @brief Exit codes (part of the public contract from 0.1.0, plan §5/§15 D13).
EXIT_OK = ENVELOPE_EXIT_OK
EXIT_CONFLICTS = EXIT_NEEDS_INPUT
EXIT_SMOKE_FAILED = EXIT_VALIDATION
EXIT_ERROR = EXIT_OPERATIONAL


# DATA MODELS / TYPEDEFINITIONS


class FileAction(Enum):
    """
    @brief The nine distinct three-way classification outcomes (the plan §10.2
           table's eleven rows collapse onto these — e.g. removed-upstream maps
           to DELETE_REMOVED whether the file is still on disk or already gone).
    @details Every payload-relative path the plan considers is assigned exactly
             one of these. The five non-conflict, non-removal actions plus a
             ``take-payload`` conflict resolution result in the path being
             tracked in the new manifest's ``files`` map; the two removal
             actions drop the path; ``keep-local``/``write-new`` conflict
             resolutions record the path under ``skipped``.
    """

    UNCHANGED = "unchanged"
    AUTO_APPLY_NEW = "auto-apply-new"
    KEEP_LOCAL = "keep-local"
    ALREADY_CONVERGED = "already-converged"
    ADD_NEW = "add-new"
    NEW_CONVERGED = "new-converged"
    CONFLICT = "conflict"
    DELETE_REMOVED = "delete-removed"
    KEEP_MODIFIED_REMOVED = "keep-modified-removed"


# @brief Actions whose path is tracked in the new manifest's ``files`` map with
#        the new original hash (``N``) — no conflict resolution required.
_TRACKED_ACTIONS = frozenset(
    {
        FileAction.UNCHANGED,
        FileAction.AUTO_APPLY_NEW,
        FileAction.KEEP_LOCAL,
        FileAction.ALREADY_CONVERGED,
        FileAction.ADD_NEW,
        FileAction.NEW_CONVERGED,
    }
)


@dataclass(frozen=True)
class UpgradeConflict:
    """
    @brief One true three-way conflict requiring a per-file decision.
    @details Distinct from copier's two-way :class:`PayloadConflict` because it
             also carries the manifest ``original`` (``O``) alongside the
             current ``local`` (``L``) and the ``new`` payload (``N``) entries.
             ``original`` is ``None`` on the new-upstream / no-manifest rows;
             ``local`` is ``None`` when the file was deleted locally but the new
             payload changed it (still a conflict). ``new`` is always present
             (a conflict only arises when the new payload ships the path), and
             ``source_path`` is the new-payload file copied for a
             ``take-payload`` / ``write-new`` decision.
    """

    relative_path: str
    original: FileEntry | None
    local: FileEntry | None
    new: FileEntry
    source_path: Path

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen JSON-safe conflict mapping.
        @return     Mapping keyed ``relative_path, original, local, new`` where
                    each hash side is ``{"sha256", "size"}`` or ``null``.
        @exception  None
        """
        return {
            "relative_path": self.relative_path,
            "original": self.original.to_dict() if self.original is not None else None,
            "local": self.local.to_dict() if self.local is not None else None,
            "new": self.new.to_dict(),
        }


# @brief Caller-supplied per-conflict decision hook: given one three-way
#        conflict, return one :class:`ConflictDecision`. Called exactly once per
#        conflict, in sorted relative-path order, and never for
#        auto-apply/keep-local/unchanged/removal cases. A conflict is NEVER
#        resolved without this hook (the copier's non-negotiable rule, here for
#        the three-way comparison).
UpgradeConflictHook = Callable[[UpgradeConflict], ConflictDecision]


@dataclass(frozen=True)
class PlanItem:
    """
    @brief One classified path: its action and the three hash sides.
    @details ``original``/``local``/``new`` are the ``O``/``L``/``N``
             :class:`FileEntry` values (``None`` where that side is absent).
             ``source_path`` is the new-payload file to copy, or ``None`` when
             the new payload does not ship the path (removal rows).
    """

    path: str
    action: FileAction
    original: FileEntry | None
    local: FileEntry | None
    new: FileEntry | None
    source_path: Path | None

    def as_conflict(self) -> UpgradeConflict:
        """
        @brief      View a CONFLICT item as an :class:`UpgradeConflict`.
        @return     The equivalent :class:`UpgradeConflict`.
        @exception  ValueError If the item is not a CONFLICT (its ``new`` and
                    ``source_path`` would be ``None``).
        """
        if self.action is not FileAction.CONFLICT or self.new is None or self.source_path is None:
            raise ValueError(f"plan item for {self.path!r} is not a resolvable conflict")
        return UpgradeConflict(
            relative_path=self.path,
            original=self.original,
            local=self.local,
            new=self.new,
            source_path=self.source_path,
        )


@dataclass(frozen=True)
class UpgradePlan:
    """
    @brief The full, read-only three-way plan for one repo + new payload.
    @details Pure classification: computing it writes nothing and calls no
             conflict hook (so ``--dry-run`` is exactly "build and render this").
             Carries the context :func:`apply_upgrade` needs to rewrite the
             manifest truthfully: the new payload root and version, the old
             manifest's preserved fields, and the untouched ``generated`` list.
             ``conservative`` is a deprecated compatibility field retained for
             the frozen report/API shape; valid-manifest upgrades always set it
             to ``False`` and no conservative execution mode exists.
    """

    repo: Path
    new_payload_root: Path
    new_payload_version: str
    items: tuple[PlanItem, ...]
    generated: tuple[str, ...]
    conservative: bool
    manifest_state: ManifestState
    product: str
    mode: str
    installed_at: str | None
    payload_digest: str
    configuration: dict[str, Any]

    def by_action(self, action: FileAction) -> tuple[str, ...]:
        """
        @brief      Every path classified with ``action``, sorted.
        @param[in]  action The action to filter by.
        @return     Sorted tuple of repo-relative POSIX paths.
        @exception  None
        """
        return tuple(item.path for item in self.items if item.action is action)

    def conflicts(self) -> tuple[UpgradeConflict, ...]:
        """
        @brief      Every true three-way conflict, in sorted path order.
        @return     Tuple of :class:`UpgradeConflict`.
        @exception  None
        """
        return tuple(item.as_conflict() for item in self.items if item.action is FileAction.CONFLICT)


@dataclass(frozen=True)
class ConflictOutcome:
    """
    @brief One conflict paired with the decision taken and what was written.
    @details ``written_path`` is the repo-relative POSIX path written for the
             decision: the payload path for ``TAKE_PAYLOAD``, the ``<name>.new``
             sidecar for ``WRITE_NEW``, ``None`` for ``KEEP_LOCAL``.
    """

    relative_path: str
    decision: ConflictDecision
    written_path: str | None


@dataclass(frozen=True)
class UpgradeReport:
    """
    @brief Structured outcome of an :func:`apply_upgrade` / :func:`run_upgrade`.
    @details ``smoke_ok`` is ``None`` when the smoke re-verify did not run
             (dry-run, or a stop-and-report before apply). ``manifest_written``
             is ``True`` only after the full apply + successful smoke re-verify
             (the rewrite-last barrier). ``preserved_local_edits`` names files
             upstream removed but the operator had locally modified — kept, not
             deleted (plan §10.2).
    """

    plan: UpgradePlan
    dry_run: bool
    applied: bool
    outcomes: tuple[ConflictOutcome, ...]
    smoke: tuple[ProbeFindingRecord, ...]
    smoke_ok: bool | None
    manifest_written: bool
    manifest: Manifest | None
    exit_code: int
    conflicts_unresolved: bool = False
    rolled_back: bool = False
    error: str | None = None

    def preserved_local_edits(self) -> tuple[str, ...]:
        """
        @brief      Files kept because upstream removed them but they were
                    locally modified (plan §10.2 removed-upstream-modified).
        @return     Sorted tuple of repo-relative POSIX paths.
        @exception  None
        """
        return self.plan.by_action(FileAction.KEEP_MODIFIED_REMOVED)

    def hook_configs_needing_retrust(self) -> tuple[str, ...]:
        """
        @brief      Adapter hook configs this upgrade rewrites whose host keys
                    hook trust to file content, so the upgrade revokes it.
        @details    Only paths the upgrade actually writes count: the two
                    auto-write actions and a conflict resolved ``take-payload``.
                    ``keep-local`` writes nothing and ``write-new`` writes a
                    ``.new`` sidecar, so neither disturbs an existing trust
                    record; ``delete-removed`` leaves no hook file to trust.
                    Reported for a dry run too, where it states what the real
                    run would cost.
        @return     Sorted tuple of repo-relative POSIX paths, empty when this
                    upgrade touches none of them.
        @exception  None
        """
        return _hook_configs_needing_retrust(self.plan, self.outcomes)

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the whole report to the frozen ``--json`` shape.
        @details    Field-name contract (WADORE-relevant, frozen per §15 D13):
                    ``{"repo", "new_payload_version", "manifest_state",
                    "conservative", "dry_run", "applied", "smoke_ok",
                    "manifest_written", "conflicts_unresolved", "exit_code",
                    "actions": {<action-value>: [path, ...], ...},
                    "conflicts": [conflict, ...], "resolutions": [{"path",
                    "decision", "written_path"}, ...], "generated_untouched":
                    [path, ...], "smoke": [{"name","status","detail","guidance"},
                    ...], "hook_configs_needing_retrust": [path, ...]}``.
                    The last key is additive (0.2.0): consumers that predate it
                    keep working, but an integration that reports an upgrade as
                    complete without reading it will call an install healthy
                    while its Codex guards have stopped running.
        @return     The JSON-safe mapping.
        @exception  None
        """
        return {
            "repo": str(self.plan.repo),
            "new_payload_version": self.plan.new_payload_version,
            "manifest_state": self.plan.manifest_state.value,
            "conservative": self.plan.conservative,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "smoke_ok": self.smoke_ok,
            "manifest_written": self.manifest_written,
            "conflicts_unresolved": self.conflicts_unresolved,
            "rolled_back": self.rolled_back,
            "error": self.error,
            "exit_code": self.exit_code,
            "actions": {action.value: list(self.plan.by_action(action)) for action in FileAction},
            "conflicts": [conflict.to_dict() for conflict in self.plan.conflicts()],
            "resolutions": [
                {"path": outcome.relative_path, "decision": outcome.decision.value, "written_path": outcome.written_path}
                for outcome in self.outcomes
            ],
            "generated_untouched": list(self.plan.generated),
            "smoke": [
                {"name": f.name, "status": f.status, "detail": f.detail, "guidance": f.guidance} for f in self.smoke
            ],
            "hook_configs_needing_retrust": list(self.hook_configs_needing_retrust()),
        }


class UpgradeError(Exception):
    """
    @brief Base error for upgrade failures caught before any write.
    """


class ConflictResolutionError(UpgradeError):
    """
    @brief A conflict could not be resolved (no decision available for a path).
    @details Raised by the resolution-table hook when a conflict path is absent
             from the table and no interactive fallback exists. Raised during
             the read-only decide phase, so the target is never touched;
             :func:`run_upgrade` catches it and stops-and-reports.
    """

    def __init__(self, relative_path: str) -> None:
        """
        @brief      Build the error naming the unresolved path.
        @param[in]  relative_path The conflict path with no available decision.
        @return     None
        @exception  None
        """
        self.relative_path = relative_path
        super().__init__(f"no decision available for conflict on {relative_path!r}")


class UpgradeApplyError(UpgradeError):
    """
    @brief One apply-phase failure paired with the transaction's true terminal
           state.
    @details :func:`_apply_upgrade_transactional` raises this instead of
             re-raising the originating exception, because the three post-write
             outcomes are materially different and must never be reported
             alike:

             - ``committed`` — every file write and the manifest rewrite are
               durable on disk and only the post-commit storage cleanup failed;
               nothing was rolled back and recovery retries the cleanup. The
               upgrade SUCCEEDED.
             - ``rolled_back`` — the transaction restored every declared path,
               so the repository is back at its exact pre-upgrade state.
             - neither — rollback itself failed, so the repository may be left
               partially upgraded and the authenticated recovery state was
               retained for a later ``waegis`` run.

             Interrupts (:class:`KeyboardInterrupt` / :class:`SystemExit`) are
             never wrapped: they keep propagating unchanged, carrying any
             rollback failure as a note. ``__cause__`` is always the
             originating exception.
    """

    def __init__(
        self,
        cause: BaseException,
        *,
        committed: bool,
        rolled_back: bool,
        rollback_error: BaseException | None = None,
    ) -> None:
        """
        @brief      Build the typed apply failure.
        @param[in]  cause The exception raised inside the transaction body.
        @param[in]  committed True when the transaction reached ``committed``
                    before the failure (a durable, successful upgrade).
        @param[in]  rolled_back True when rollback completed and restored every
                    declared path.
        @param[in]  rollback_error The rollback failure, when rollback was
                    attempted and did not complete.
        @return     None
        @exception  None
        """
        self.cause = cause
        self.committed = committed
        self.rolled_back = rolled_back
        self.rollback_error = rollback_error
        super().__init__(str(cause) or type(cause).__name__)


# LOCAL HELPERS


def _new_payload_files(payload_root: Path) -> dict[str, FileEntry]:
    """
    @brief      Enumerate and hash every file the new payload would install.
    @details    Applies the same exclusions as the copier
                (:func:`should_exclude`) and defensively skips any
                ``install-manifest.json`` found inside the payload, so ``N`` is
                computed over exactly the set of files a copy would write.
    @param[in]  payload_root New payload (template) root directory.
    @return     Mapping of repo-relative POSIX path to its new hash/size ``N``.
    @exception  PayloadMissingError If ``payload_root`` is not a directory.
    @exception  CopierError If an included payload source is unsafe or not
                a regular file.
    @exception  OSError If the payload tree cannot be walked or a file hashed.
    """
    return dict(inspect_payload(payload_root).entries)


def _classify(original: str | None, local: str | None, new: str | None) -> FileAction:
    """
    @brief      Classify one path from its ``O``/``L``/``N`` hashes (plan §10.2).
    @details    An absent side is passed as ``None`` and treated as unequal to
                every hash and to another absent side, so "operator deleted the
                file" and "upstream dropped the file" cases fall out of the same
                comparisons.
    @param[in]  original ``O`` hash, or ``None`` when untracked.
    @param[in]  local ``L`` hash, or ``None`` when the file is absent on disk.
    @param[in]  new ``N`` hash, or ``None`` when the new payload dropped it.
    @return     The classified :class:`FileAction`.
    @exception  None
    """
    if new is not None:
        if original is None:
            # New upstream file (or an adoption-time skipped path, re-offered).
            if local is None:
                return FileAction.ADD_NEW
            if local == new:
                return FileAction.NEW_CONVERGED
            return FileAction.CONFLICT
        if local == original and new == original:
            return FileAction.UNCHANGED
        if local == original and new != original:
            return FileAction.AUTO_APPLY_NEW
        if local != original and new == original:
            return FileAction.KEEP_LOCAL
        if local == new:  # local != original and new != original
            return FileAction.ALREADY_CONVERGED
        return FileAction.CONFLICT
    # new is None: the new payload no longer ships this path (removed upstream).
    # Only reachable when original is not None (else the path is in neither the
    # manifest nor the new payload and never enters the union).
    if local is None or local == original:
        return FileAction.DELETE_REMOVED
    return FileAction.KEEP_MODIFIED_REMOVED


def _copy_file(source: Path, destination: Path) -> None:
    """
    @brief      Byte-verbatim copy one file, creating parent directories.
    @details    Uses :func:`shutil.copy2` (binary, no newline translation) —
                the same primitive the copier uses, so the copied file's hash
                equals the source hash. Also runs the copy through
                :func:`waegis.payload.copier.ensure_executable` (0.2.0), the
                same POSIX execute-bit backstop ``copy_payload``/``repair``
                apply, so an upgraded ``run.sh`` never regresses to
                non-executable.
    @param[in]  source File to copy from.
    @param[in]  destination File to copy to.
    @return     None
    @exception  OSError If the copy fails.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    ensure_executable(destination)


def _hook_configs_needing_retrust(
    plan: UpgradePlan,
    outcomes: tuple[ConflictOutcome, ...],
) -> tuple[str, ...]:
    """
    @brief      Adapter hook configs this plan rewrites whose host keys hook
                trust to file content, so applying it revokes that trust.
    @details    Single definition of the rule, shared by
                :meth:`UpgradeReport.hook_configs_needing_retrust` and the
                pre-approval/dry-run plan dict — the operator must be able to
                see the cost *before* approving, and a second copy of the rule
                is how the two views drift apart.
                Only paths actually written count: the two auto-write actions
                and a conflict resolved ``take-payload``. ``keep-local`` writes
                nothing and ``write-new`` writes a ``.new`` sidecar, so neither
                disturbs an existing trust record; ``delete-removed`` leaves no
                hook file to trust.
    @param[in]  plan The computed plan.
    @param[in]  outcomes Resolved conflict outcomes (empty before resolution).
    @return     Sorted tuple of repo-relative POSIX paths.
    @exception  None
    """
    written = set(plan.by_action(FileAction.AUTO_APPLY_NEW))
    written |= set(plan.by_action(FileAction.ADD_NEW))
    written |= {
        outcome.relative_path
        for outcome in outcomes
        if outcome.decision is ConflictDecision.TAKE_PAYLOAD
    }
    return tuple(sorted(written.intersection(HASH_TRUSTED_HOOK_CONFIGS)))


def _sidecar_path(repo: Path, relative_path: str) -> Path:
    """
    @brief      Resolve the ``<name>.new`` sidecar path for a write-new decision.
    @param[in]  repo Repository root.
    @param[in]  relative_path Repo-relative POSIX path of the conflicting file.
    @return     Absolute path of the ``.new`` sidecar beside the local file.
    @exception  None
    """
    return resolve_managed_path(repo, sidecar_relative_path(relative_path))


def make_resolution_hook(
    resolutions: Mapping[str, str] | None,
    fallback: UpgradeConflictHook | None,
) -> UpgradeConflictHook:
    """
    @brief      Build a conflict hook driven by a pre-supplied resolution table,
                then an optional interactive fallback (mirrors adopt.py's T5.2).
    @details    A decision for the conflict's path in ``resolutions`` wins;
                otherwise ``fallback`` (typically a console prompt) is used;
                with neither, :class:`ConflictResolutionError` is raised so the
                caller stops-and-reports. Table values are the
                :class:`ConflictDecision` string values
                (``keep-local``/``take-payload``/``write-new``).
    @param[in]  resolutions Optional ``{path: decision}`` table.
    @param[in]  fallback Optional interactive hook for paths absent from the table.
    @return     A :data:`UpgradeConflictHook`.
    @exception  None (the returned hook may raise :class:`ConflictResolutionError`).
    """
    table: Mapping[str, str] = resolutions or {}

    def hook(conflict: UpgradeConflict) -> ConflictDecision:
        """
        @brief      Resolve one conflict via the table or the fallback.
        @param[in]  conflict The conflict to resolve.
        @return     The chosen :class:`ConflictDecision`.
        @exception  ConflictResolutionError If no decision is available.
        @exception  ValueError If a table value is not a valid decision.
        """
        raw = table.get(conflict.relative_path)
        if raw is not None:
            return ConflictDecision(normalize_conflict_decision_value(raw))
        if fallback is not None:
            return fallback(conflict)
        raise ConflictResolutionError(conflict.relative_path)

    return hook


def make_console_hook(asker: ConsoleAsker) -> UpgradeConflictHook:
    """
    @brief      Build an interactive conflict hook driven by a console asker.
    @details    Prompts per conflict with a :class:`FieldSpec` (default
                ``keep-local``, the safest choice), mirroring adopt.py's
                ``_prompt_conflict``. Shows both sides' size + short hash so the
                operator can decide informed.
    @param[in]  asker The console asker prompting the operator.
    @return     A :data:`UpgradeConflictHook`.
    @exception  None
    """

    def hook(conflict: UpgradeConflict) -> ConflictDecision:
        """
        @brief      Interactively resolve one conflict.
        @details    Renders `keep-local`/`take-payload`/`write-new` as a
                    numbered menu via `FieldSpec.choices` (0.1.1) instead of
                    requiring the operator to type the full word.
        @param[in]  conflict The conflict to resolve.
        @return     The chosen :class:`ConflictDecision`.
        @exception  waegis.io.prompts.PromptsError On a missing/invalid answer.
        """
        local_desc = (
            f"local {conflict.local.size} bytes / {conflict.local.sha256[:12]}"
            if conflict.local is not None
            else "local file is absent"
        )
        spec = FieldSpec(
            key=f"conflict:{conflict.relative_path}",
            question=f"{conflict.relative_path} differs three ways ({local_desc}; new payload {conflict.new.size} bytes / {conflict.new.sha256[:12]}) — keep yours, take the new payload, or write it beside yours?",
            description=(
                "Nothing you own is ever silently overwritten: keep-local keeps "
                "yours untouched, take-payload overwrites it with the new "
                "payload, write-new keeps yours and writes the new payload as "
                "a .new file beside it."
            ),
            example="keep-local",
            default="keep-local",
            validator=normalize_conflict_decision_value,
            choices=("keep-local", "take-payload", "write-new"),
        )
        return ConflictDecision(asker.ask_field(spec))

    return hook


def _build_new_manifest(plan: UpgradePlan, outcomes: Mapping[str, ConflictDecision]) -> Manifest:
    """
    @brief      Construct the rewritten manifest from the applied plan.
    @details    ``files`` is built directly from ``N`` (the new payload hashes
                already computed while classifying) for every tracked action and
                every ``take-payload`` conflict — NOT via ``build_manifest``,
                which would re-hash disk and mis-record the *local* hash rather
                than the new original for a KEEP_LOCAL file. ``keep-local`` and
                ``write-new`` conflicts record the payload path under ``skipped``
                (re-offered by a future upgrade); removals drop the path.
                ``product``/``mode``/``installed_at`` are preserved from the old
                manifest; ``installed_by`` is stamped to this wizard build;
                ``generated`` is preserved verbatim.
    @param[in]  plan The computed plan.
    @param[in]  outcomes Resolved conflict decisions keyed by path.
    @return     The new :class:`Manifest` (not yet written).
    @exception  None
    """
    files: dict[str, FileEntry] = {}
    skipped: list[str] = []
    for item in plan.items:
        if item.action in _TRACKED_ACTIONS:
            assert item.new is not None, f"tracked item {item.path!r} lacks a payload entry"
            files[item.path] = item.new
        elif item.action is FileAction.CONFLICT:
            decision = outcomes[item.path]
            if decision is ConflictDecision.TAKE_PAYLOAD:
                assert item.new is not None, f"conflict item {item.path!r} lacks a payload entry"
                files[item.path] = item.new
            else:  # KEEP_LOCAL or WRITE_NEW
                skipped.append(item.path)
        # DELETE_REMOVED / KEEP_MODIFIED_REMOVED: path dropped from the manifest.
    installed_at = plan.installed_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        product=plan.product,
        payload_version=plan.new_payload_version,
        installed_at=installed_at,
        installed_by=f"waegis {WIZARD_VERSION}",
        mode=plan.mode,
        files=files,
        generated=plan.generated,
        skipped=tuple(sorted(skipped)),
        payload_digest=plan.payload_digest,
        configuration=dict(plan.configuration),
    )


# PUBLIC API


def build_upgrade_plan(
    repo: str | PathLike[str],
    *,
    new_payload_root: str | PathLike[str],
    load_result: ManifestLoadResult,
) -> UpgradePlan:
    """
    @brief      Compute the read-only three-way upgrade plan (plan §10.2).
    @details    Pure and side-effect-free: writes nothing, calls no conflict
                hook. Builds the union of the manifest's ``files`` and the new
                payload's files, removes ``generated`` paths and the manifest's
                own path, and classifies every remaining path from its
                ``O``/``L``/``N`` hashes. A valid current install manifest is
                mandatory; adoption owns repositories without one.
    @param[in]  repo Repository root to upgrade.
    @param[in]  new_payload_root Resolved new payload (template) root.
    @param[in]  load_result Result of :func:`waegis.payload.manifest.load_manifest`.
    @return     The computed :class:`UpgradePlan`.
    @exception  UpgradeError If the current install manifest is absent or invalid.
    @exception  CopierError If the new payload is unreadable or ships an unsafe
                entry (propagated from :func:`_new_payload_files`).
    @exception  OSError If a repo or payload file cannot be hashed.
    """
    repo_path = Path(repo)
    payload_path = Path(new_payload_root)
    new_files = _new_payload_files(payload_path)
    new_version = read_payload_version(payload_path) or UNKNOWN_PAYLOAD_VERSION

    if load_result.state is not ManifestState.VALID or load_result.manifest is None:
        raise UpgradeError("upgrade requires a valid current install manifest")
    manifest = load_result.manifest
    old_files = manifest.files
    generated = manifest.generated
    product, mode, installed_at = manifest.product, manifest.mode, manifest.installed_at
    configuration = dict(manifest.configuration)

    excluded = set(generated)
    excluded.add(MANIFEST_RELATIVE_PATH)
    union = (set(old_files) | set(new_files)) - excluded

    items: list[PlanItem] = []
    for path in sorted(union):
        original = old_files.get(path)
        new_entry = new_files.get(path)
        local_file = resolve_managed_path(repo_path, path)
        local_entry = hash_file(local_file) if local_file.is_file() else None
        action = _classify(
            original.sha256 if original is not None else None,
            local_entry.sha256 if local_entry is not None else None,
            new_entry.sha256 if new_entry is not None else None,
        )
        items.append(
            PlanItem(
                path=path,
                action=action,
                original=original,
                local=local_entry,
                new=new_entry,
                source_path=resolve_managed_path(payload_path, path) if new_entry is not None else None,
            )
        )

    return UpgradePlan(
        repo=repo_path,
        new_payload_root=payload_path,
        new_payload_version=new_version,
        items=tuple(items),
        generated=generated,
        conservative=False,
        manifest_state=load_result.state,
        product=product,
        mode=mode,
        installed_at=installed_at,
        payload_digest=digest_file_entries(new_files),
        configuration=configuration,
    )


def resolve_upgrade_decisions(
    plan: UpgradePlan,
    hook: UpgradeConflictHook | None,
) -> tuple[dict[str, ConflictDecision], tuple[ConflictOutcome, ...]]:
    """
    @brief      Collect and validate every conflict decision without writing.
    @param[in]  plan The computed plan.
    @param[in]  hook Per-conflict decision hook; required when ``plan`` has
                conflicts.
    @return     Decision mapping and ordered outcomes.
    @exception  UpgradeError If ``hook`` is ``None`` while conflicts exist, or
                the hook returns a non-:class:`ConflictDecision`.
    @exception  ConflictResolutionError If ``hook`` cannot resolve a conflict
                (a :class:`UpgradeError` subclass, raised by hooks built with
                :func:`make_resolution_hook`).
    @exception  OSError If an existing ``write-new`` sidecar cannot be hashed
                to check for a collision.
    """
    conflicts = plan.conflicts()
    if conflicts and hook is None:
        raise UpgradeError("the plan has conflicts but no decision hook was supplied")
    decisions: dict[str, ConflictDecision] = {}
    outcomes: list[ConflictOutcome] = []
    for conflict in conflicts:
        assert hook is not None, "conflicts without a hook are rejected above"
        decision = hook(conflict)
        if not isinstance(decision, ConflictDecision):
            raise UpgradeError(
                f"conflict hook returned {decision!r} for {conflict.relative_path!r}; expected a ConflictDecision"
            )
        written_path: str | None
        if decision is ConflictDecision.TAKE_PAYLOAD:
            written_path = conflict.relative_path
        elif decision is ConflictDecision.KEEP_LOCAL:
            written_path = None
        else:
            sidecar = _sidecar_path(plan.repo, conflict.relative_path)
            if sidecar.exists() and (not sidecar.is_file() or hash_file(sidecar).sha256 != conflict.new.sha256):
                raise UpgradeError(f"refusing to overwrite existing sidecar file: {sidecar}")
            written_path = sidecar.relative_to(plan.repo).as_posix()
        decisions[conflict.relative_path] = decision
        outcomes.append(
            ConflictOutcome(
                relative_path=conflict.relative_path,
                decision=decision,
                written_path=written_path,
            )
        )
    return decisions, tuple(outcomes)


def apply_upgrade(
    plan: UpgradePlan,
    *,
    hook: UpgradeConflictHook | None = None,
    runner: CommandRunner | None = None,
    decisions: Mapping[str, ConflictDecision] | None = None,
    resolved_outcomes: tuple[ConflictOutcome, ...] | None = None,
) -> UpgradeReport:
    """
    @brief      Resolve conflicts, apply every write, smoke re-verify, then (only
                on success) rewrite the manifest — the plan §10.2 apply ordering.
    @details    Ordering, with the manifest-rewrite-last barrier:
                (1b) decide — call ``hook`` once per conflict, in sorted order;
                every decision and any ``write-new`` sidecar collision is
                resolved here, before any write, so a refusal or a
                :class:`ConflictResolutionError` leaves the target untouched.
                (2) apply — delete removed-unmodified files, copy
                auto-apply/add/take-payload files byte-verbatim, write
                ``write-new`` sidecars. (2.5) smoke re-verify via
                :func:`waegis.verification.smoke_reverify`; on failure roll
                back and return with ``manifest_written=False``. (3) rewrite
                the manifest — the single
                :func:`write_manifest`, textually last.
    @param[in]  plan The computed plan.
    @param[in]  hook Per-conflict decision hook; required when the plan has
                conflicts and ``decisions`` is not supplied (a conflict is
                never resolved without one or the other).
    @param[in]  runner Injectable command runner for the smoke re-verify;
                defaults to the real subprocess runner.
    @param[in]  decisions Pre-resolved conflict decisions keyed by path,
                bypassing ``hook`` entirely; when given, the set of keys must
                exactly match the plan's conflict paths.
    @param[in]  resolved_outcomes Pre-built outcomes paired with ``decisions``
                (e.g. from a prior :func:`resolve_upgrade_decisions` call);
                when omitted alongside ``decisions``, outcomes are rebuilt
                with ``written_path=None``.
    @return     The :class:`UpgradeReport`.
    @exception  ConflictResolutionError If a conflict has no available decision
                (raised in the decide phase, before any write).
    @exception  UpgradeError If ``hook`` is missing while conflicts exist, the
                hook returns a non-:class:`ConflictDecision`, a ``write-new``
                sidecar already exists with different content, or
                ``decisions`` does not exactly match the plan's conflicts.
    @exception  OSError If a file copy/delete or the manifest write fails
                before the transaction is opened.
    @exception  UpgradeApplyError Any error raised inside the transaction body
                (e.g. a transaction or manifest failure) is wrapped, after the
                automatic rollback attempt, in a typed failure carrying whether
                the transaction committed, rolled back, or failed to roll back
                — see :class:`UpgradeApplyError`. The originating exception is
                the wrapper's ``__cause__``.
    @exception  BaseException :class:`KeyboardInterrupt` and
                :class:`SystemExit` are never wrapped; they propagate unchanged
                after the same rollback attempt.
    """
    return _apply_upgrade_transactional(
        plan,
        hook=hook,
        runner=runner,
        decisions=decisions,
        resolved_outcomes=resolved_outcomes,
    )


def _apply_upgrade_transactional(
    plan: UpgradePlan,
    *,
    hook: UpgradeConflictHook | None,
    runner: CommandRunner | None,
    decisions: Mapping[str, ConflictDecision] | None,
    resolved_outcomes: tuple[ConflictOutcome, ...] | None,
) -> UpgradeReport:
    """
    @brief      Apply a fully resolved plan through a persistent transaction.
    @return     Upgrade report, including rollback state on smoke failure.
    @exception  UpgradeApplyError Raised, after the automatic rollback attempt,
                for every non-interrupt failure inside the transaction body,
                carrying the transaction's true terminal state so callers never
                have to inspect message text to tell a committed-but-
                cleanup-failed upgrade from a rolled-back one.
    @exception  BaseException :class:`KeyboardInterrupt` / :class:`SystemExit`
                propagate unchanged after the same rollback attempt.
    """
    active_runner = runner or SubprocessCommandRunner()
    if decisions is None:
        resolved, outcomes = resolve_upgrade_decisions(plan, hook)
    else:
        resolved = dict(decisions)
        conflict_paths = {conflict.relative_path for conflict in plan.conflicts()}
        if set(resolved) != conflict_paths:
            raise UpgradeError("pre-resolved decisions do not exactly match the plan conflicts")
        outcomes = resolved_outcomes or tuple(
            ConflictOutcome(path, resolved[path], None) for path in sorted(resolved)
        )
    affected: set[str] = {MANIFEST_RELATIVE_PATH}
    for item in plan.items:
        if item.action in (FileAction.AUTO_APPLY_NEW, FileAction.ADD_NEW, FileAction.DELETE_REMOVED):
            affected.add(item.path)
        elif item.action is FileAction.CONFLICT:
            decision = resolved[item.path]
            if decision is ConflictDecision.TAKE_PAYLOAD:
                affected.add(item.path)
            elif decision is ConflictDecision.WRITE_NEW:
                affected.add(_sidecar_path(plan.repo, item.path).relative_to(plan.repo).as_posix())
    transaction = FileTransaction.begin(plan.repo, command="upgrade", paths=sorted(affected))
    smoke: tuple[ProbeFindingRecord, ...] = ()
    try:
        transaction.mark("applying")
        for item in plan.items:
            destination = resolve_managed_path(plan.repo, item.path)
            if item.action in (FileAction.AUTO_APPLY_NEW, FileAction.ADD_NEW):
                assert item.source_path is not None, f"apply item {item.path!r} lacks a source path"
                _copy_file(item.source_path, destination)
            elif item.action is FileAction.DELETE_REMOVED:
                if destination.is_file():
                    destination.unlink()
            elif item.action is FileAction.CONFLICT:
                decision = resolved[item.path]
                assert item.source_path is not None, f"conflict item {item.path!r} lacks a source path"
                if decision is ConflictDecision.TAKE_PAYLOAD:
                    _copy_file(item.source_path, destination)
                elif decision is ConflictDecision.WRITE_NEW:
                    _copy_file(item.source_path, _sidecar_path(plan.repo, item.path))
        smoke, smoke_ok = smoke_reverify(active_runner, plan.repo)
        if not smoke_ok:
            transaction.rollback()
            return UpgradeReport(
                plan=plan,
                dry_run=False,
                applied=False,
                outcomes=outcomes,
                smoke=smoke,
                smoke_ok=False,
                manifest_written=False,
                manifest=None,
                exit_code=EXIT_SMOKE_FAILED,
                rolled_back=True,
                error="post-apply smoke verification failed",
            )
        transaction.mark("verified")
        manifest = _build_new_manifest(plan, resolved)
        write_manifest(plan.repo, manifest)
        transaction.commit()
    except BaseException as exc:
        committed = transaction.phase == "committed"
        rolled_back = False
        rollback_error: BaseException | None = None
        if transaction.directory.exists() and not committed:
            try:
                transaction.rollback()
                rolled_back = True
            except Exception as exc_rollback:
                rollback_error = exc_rollback
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            if rollback_error is not None:
                exc.add_note(
                    "upgrade rollback failed; authenticated recovery state "
                    f"was retained: {rollback_error}"
                )
            raise
        raise UpgradeApplyError(
            exc,
            committed=committed,
            rolled_back=rolled_back,
            rollback_error=rollback_error,
        ) from exc
    return UpgradeReport(
        plan=plan,
        dry_run=False,
        applied=True,
        outcomes=outcomes,
        smoke=smoke,
        smoke_ok=True,
        manifest_written=True,
        manifest=manifest,
        exit_code=EXIT_OK,
    )


def render_upgrade_report(report: UpgradeReport, stream: IO[str]) -> None:
    """
    @brief      Render an :class:`UpgradeReport` as a plain-ASCII-safe human
                report (mirrors doctor/analyze's style: no glyphs, no ANSI).
    @details    Shows the plan (counts per action, and the full conflict /
                removed-modified lists which are the operator-actionable ones),
                the smoke re-verify verdict, and whether the manifest was
                rewritten. For a stop-and-report run it lists the conflicts that
                need decisions.
    @details    A successful upgrade that rewrote a hash-trusted hook config
                (0.2.0) ends with an action-required block. This is the one
                place the operator can learn that a *successful* upgrade turned
                their guards off: the host revokes hook trust on any content
                change, and reports it only inside a settings panel. Every other
                signal — exit code, smoke verdict, manifest — says the install
                is healthy, and it is; it is simply not enforcing.
    @param[in]  report The report to render.
    @param[in]  stream Output stream (real console or injected buffer for tests).
    @return     None
    @exception  None
    """
    plan = report.plan
    stream.write(f"WAEGIS upgrade - {plan.repo}\n")
    stream.write(f"  new payload version: {plan.new_payload_version}\n")
    stream.write("\n")

    stream.write("Plan:\n")
    for action in FileAction:
        paths = plan.by_action(action)
        if paths:
            stream.write(f"  {action.value}: {len(paths)} file(s)\n")
    if not plan.items:
        stream.write("  (nothing to do - repo already matches the new payload)\n")
    stream.write("\n")

    conflicts = plan.conflicts()
    if conflicts:
        stream.write("Conflicts (need a per-file decision):\n")
        for conflict in conflicts:
            stream.write(f"  {conflict.relative_path}\n")
        stream.write("\n")

    preserved = report.preserved_local_edits()
    if preserved:
        stream.write("Preserved local edits (upstream removed these, but you had modified them - kept):\n")
        for path in preserved:
            stream.write(f"  {path}\n")
        stream.write("\n")

    retrust = report.hook_configs_needing_retrust()

    if report.dry_run:
        stream.write("Dry run: nothing was written; the install manifest is unchanged.\n")
        if retrust:
            stream.write(
                f"\nNote: a real run would rewrite {', '.join(retrust)}. The host binds hook "
                "trust to file content, so that rewrite would stop those guards running until "
                "they are re-reviewed.\n"
            )
        return

    if report.conflicts_unresolved:
        stream.write(
            "Stopped: conflicts require decisions and none were supplied. Nothing was written; "
            "re-run interactively (without --json) to resolve them.\n"
        )
        return

    stream.write("Smoke re-verify:\n")
    for finding in report.smoke:
        stream.write(f"  [{finding.status}] {finding.name}: {finding.detail}\n")
        if finding.guidance:
            stream.write(f"      guidance: {finding.guidance}\n")
    stream.write("\n")

    if report.manifest_written:
        stream.write("Upgrade complete: files applied, smoke re-verify passed, install manifest rewritten.\n")
        if retrust:
            stream.write(
                "\nACTION REQUIRED - guards are not enforcing until you re-review them:\n"
                f"  This upgrade rewrote {', '.join(retrust)}. The host binds hook trust to the\n"
                "  file's content, so every hook in it is now back to 'review required' and is\n"
                "  NOT running. Nothing else reports this: the upgrade succeeded, the files are\n"
                "  correct, and the session will look healthy while tool calls go uninspected.\n"
                "  Open the agent's /hooks panel, trust the AEGIS hooks, then confirm by asking\n"
                "  it to read a path your enforced protected-path read policy covers.\n"
            )
    else:
        stream.write(
            "Upgrade failed verification and was rolled back; the install manifest and managed "
            "files remain at their pre-upgrade state.\n"
        )


def upgrade_report_json(report: UpgradeReport) -> str:
    """
    @brief      Serialize an :class:`UpgradeReport` to the frozen ``--json``
                shape (see :meth:`UpgradeReport.to_dict` for the field contract).
    @param[in]  report The report to serialize.
    @return     JSON text, 2-space indent.
    @exception  None
    """
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)



# HARDENED COMMAND ORCHESTRATION


def _upgrade_plan_dict(
    plan: UpgradePlan,
    outcomes: tuple[ConflictOutcome, ...],
    *,
    git_mode: str,
    git_branch: str | None,
) -> dict[str, Any]:
    """@brief Serialize the fully resolved plan shown before approval."""
    return {
        "repo": str(plan.repo),
        "new_payload_version": plan.new_payload_version,
        "payload_digest": plan.payload_digest,
        "git_mode": git_mode,
        "git_branch": git_branch,
        "actions": {action.value: list(plan.by_action(action)) for action in FileAction},
        "resolutions": [
            {
                "path": outcome.relative_path,
                "decision": outcome.decision.value,
                "written_path": outcome.written_path,
            }
            for outcome in outcomes
        ],
        "generated_untouched": list(plan.generated),
        "hook_configs_needing_retrust": list(_hook_configs_needing_retrust(plan, outcomes)),
    }


def _emit_upgrade_envelope_or_report(
    stream: IO[str],
    *,
    as_json: bool,
    status: str,
    exit_code: int,
    plan_data: Mapping[str, Any] | None = None,
    report: UpgradeReport | None = None,
    result_extra: Mapping[str, Any] | None = None,
    messages: tuple[str, ...] = (),
) -> int:
    """@brief Emit one hardened upgrade result."""
    if as_json:
        result = report.to_dict() if report is not None else {}
        if result_extra is not None:
            result.update(result_extra)
        return write_envelope(
            stream,
            "upgrade",
            status=status,
            exit_code=exit_code,
            plan=plan_data,
            result=result,
            messages=messages,
        )
    for message in messages:
        stream.write("waegis upgrade: " + message + "\n")
    if plan_data is not None and "repo" not in plan_data:
        # Recovery-only plan: the transaction-recovery consent was declined
        # before any upgrade plan existed, so only the pending transaction
        # ids are known (the _shared.recover_transactions_or_emit shape).
        for transaction_id in plan_data.get("recovery", []):
            stream.write(f"  pending transaction: {transaction_id}\n")
    elif plan_data is not None:
        stream.write(f"Resolved upgrade plan for {plan_data['repo']}\n")
        stream.write(f"  payload: {plan_data['new_payload_version']} ({plan_data['payload_digest'][:12]})\n")
        stream.write(f"  git mode: {plan_data['git_mode']}\n")
        for action, paths in plan_data["actions"].items():
            if paths:
                stream.write(f"  {action}: {len(paths)} file(s)\n")
        for resolution in plan_data["resolutions"]:
            stream.write(f"  resolve {resolution['path']}: {resolution['decision']}\n")
        retrust = plan_data.get("hook_configs_needing_retrust") or []
        if retrust:
            stream.write(
                f"  NOTE: applying this rewrites {', '.join(retrust)}, which revokes the host's\n"
                "        hook trust - those guards stop running until re-reviewed in /hooks.\n"
            )
    if report is not None:
        render_upgrade_report(report, stream)
    return exit_code


@dataclass(frozen=True)
class UpgradeContext:
    """@brief Resolved public boundary for upgrade command phases."""
    repo_path: Path
    options: CommandOptions
    on_conflict: UpgradeConflictHook | None
    resolutions: Mapping[str, str] | None
    asker: ConsoleAsker | None


@dataclass(frozen=True)
class UpgradeValidated:
    """@brief Validated upgrade inputs before decision planning."""
    context: UpgradeContext
    pending: tuple[str, ...]
    supplied: dict[str, Any]
    payload_root: Path
    inventory: Any
    plan: UpgradePlan
    runner: CommandRunner


@dataclass(frozen=True)
class UpgradePlanState:
    """@brief Fully resolved upgrade plan awaiting operator consent."""
    validated: UpgradeValidated
    git_mode: str
    git_branch: str | None
    fingerprints: dict[str, str]
    decisions: Mapping[str, ConflictDecision]
    outcomes: tuple[ConflictOutcome, ...]
    plan_data: dict[str, Any]


@dataclass(frozen=True)
class UpgradeOutcome:
    """@brief Applied upgrade awaiting RepoWise and final rendering."""
    plan: UpgradePlanState
    report: UpgradeReport


def _upgrade_emit(context: UpgradeContext, **kwargs: Any) -> int:
    """@brief Bind upgrade output options for phase-local early returns."""
    return _emit_upgrade_envelope_or_report(
        context.options.stream, as_json=context.options.as_json, **kwargs
    )


def _load_upgrade_answers(context: UpgradeContext) -> int | dict[str, Any]:
    """@brief Load and closed-schema validate upgrade answers."""
    supplied: dict[str, Any] = {}
    if context.options.answers_path is not None:
        try:
            supplied = load_answers_file(context.options.answers_path)
        except AnswersFileError as exc:
            return _upgrade_emit(
                context, status="failed", exit_code=EXIT_VALIDATION,
                messages=(str(exc),),
            )
    allowed = {"upgrade_conflicts", "git_mode", "git_branch"} | REPOWISE_ANSWER_KEYS
    unknown = sorted(set(supplied) - allowed)
    if unknown:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("unrecognized answer key(s): " + ", ".join(unknown),),
        )
    return supplied


def _validate_upgrade_install(
    context: UpgradeContext, payload_root: Path, payload_version: str,
    load: ManifestLoadResult,
) -> int | UpgradePlan:
    """@brief Validate installed integration/version and build read-only plan."""
    if load.state is not ManifestState.VALID or load.manifest is None:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("upgrade requires a valid current install manifest",),
        )
    try:
        installed_repowise = repowise_status(context.repo_path)
        if installed_repowise.get("source") == "bundled" and distribution_edition() == "core":
            return _upgrade_emit(
                context, status="failed", exit_code=EXIT_VALIDATION,
                messages=(
                    "Complete to Core is refused while RepoWise uses the bundled runtime; "
                    "run waegis configure to select external or disabled first",
                ),
            )
    except RepoWiseError as exc:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=(f"cannot validate installed RepoWise integration: {exc}",),
        )
    if load.manifest.payload_version.split(".", 1)[0] != payload_version.split(".", 1)[0]:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("cross-major AEGIS upgrades are unsupported; deploy AEGIS 2.x "
                      "as a fresh installation with schema 3",),
        )
    try:
        return build_upgrade_plan(
            context.repo_path, new_payload_root=payload_root, load_result=load
        )
    except (OSError, ValueError, CopierError) as exc:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )


def _validate_upgrade(context: UpgradeContext) -> int | UpgradeValidated:
    """@brief Validate recovery, inputs, payload, installation, and Git state."""
    options = context.options
    if not context.repo_path.is_dir():
        return _upgrade_emit(
            context, status="error", exit_code=EXIT_OPERATIONAL,
            messages=(f"--repo path does not exist or is not a directory: {context.repo_path}",),
        )
    recovery = recover_transactions_or_emit(
        context.repo_path, dry_run=options.dry_run, yes=options.yes,
        recovery_asker=context.asker,
        emit=lambda *, status, exit_code, plan=None, messages=(): _upgrade_emit(
            context, status=status, exit_code=exit_code,
            plan_data=plan, messages=messages,
        ),
    )
    if isinstance(recovery, int):
        return recovery
    pending, _recovered = recovery
    supplied = _load_upgrade_answers(context)
    if isinstance(supplied, int):
        return supplied
    try:
        payload_root, inventory, payload_version = locate_validated_payload(
            options.payload
        )
    except PAYLOAD_VALIDATION_ERRORS as exc:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )
    load = load_manifest(context.repo_path)
    plan = _validate_upgrade_install(
        context, payload_root, payload_version, load
    )
    if isinstance(plan, int):
        return plan
    runner = options.runner or SubprocessCommandRunner()
    if not gitops.is_work_tree(runner, context.repo_path):
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("upgrade requires a Git worktree",),
        )
    if gitops.status_porcelain(runner, context.repo_path):
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("upgrade requires a clean Git worktree; commit or stash current changes first",),
        )
    return UpgradeValidated(
        context, tuple(pending), supplied, payload_root, inventory, plan, runner
    )


def _resolve_upgrade_git(
    validated: UpgradeValidated,
) -> int | tuple[str, str | None]:
    """@brief Resolve and validate the upgrade Git mode and branch."""
    context = validated.context
    raw = validated.supplied.get("git_mode")
    if context.options.non_interactive and raw is None:
        return _upgrade_emit(
            context, status="needs-input", exit_code=EXIT_NEEDS_INPUT,
            messages=("non-interactive upgrade requires git_mode in --answers",),
        )
    if raw is None and context.asker is not None:
        raw = context.asker.ask_field(FieldSpec(
            key="git_mode",
            question="Commit the upgrade on the current branch, or on a dedicated branch?",
            description=(
                "Either way the worktree must already be clean before the "
                "upgrade starts. require-clean commits directly on your "
                "current branch; branch-commit creates a dedicated branch "
                "first, so the upgrade's commit lands there instead."
            ),
            example="require-clean", default="require-clean",
            validator=lambda value: str(value).strip().lower(),
        ))
    git_mode = str(raw or "require-clean").strip().lower()
    if git_mode not in {"require-clean", "branch-commit"}:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("git_mode must be require-clean or branch-commit",),
        )
    git_branch = None
    if git_mode == "branch-commit":
        git_branch = str(
            validated.supplied.get("git_branch")
            or f"waegis/upgrade-{validated.plan.new_payload_version}"
        ).strip()
        try:
            git_branch = gitops.validate_branch_name(git_branch)
        except ValueError as exc:
            return _upgrade_emit(
                context, status="failed", exit_code=EXIT_VALIDATION,
                messages=(f"invalid git_branch: {exc}",),
            )
    return git_mode, git_branch


def _upgrade_fingerprints(validated: UpgradeValidated) -> dict[str, str]:
    """@brief Build the stable upgrade journal fingerprints."""
    return {
        "command": stable_fingerprint("upgrade"),
        "catalog": stable_fingerprint("upgrade-transaction-v1"),
        "target": stable_fingerprint(str(validated.context.repo_path).casefold()),
        "answers": stable_fingerprint(validated.supplied),
        "payload": stable_fingerprint(validated.inventory.digest),
    }


def _upgrade_decision_table(
    validated: UpgradeValidated, fingerprints: Mapping[str, str],
) -> int | dict[str, str]:
    """@brief Merge resume, answers-file, and explicit decision seams."""
    context = validated.context
    table: dict[str, str] = {}
    prior = find_resume_journal(
        context.options.home or waegis_home(),
        expected_fingerprints=fingerprints,
    )
    if prior is not None:
        for result in prior.results():
            recorded = result.answers.get("resolutions")
            if isinstance(recorded, Mapping):
                table.update({str(key): str(value) for key, value in recorded.items()})
    supplied_table = validated.supplied.get("upgrade_conflicts", {})
    if not isinstance(supplied_table, Mapping):
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("upgrade_conflicts must be a path-to-decision mapping",),
        )
    table.update({str(key): str(value) for key, value in supplied_table.items()})
    if context.resolutions is not None:
        table.update({str(key): str(value) for key, value in context.resolutions.items()})
    return table


def _upgrade_dry_run(
    validated: UpgradeValidated, git_mode: str, git_branch: str | None,
) -> int:
    """@brief Emit the byte-compatible read-only upgrade preview."""
    preview = _upgrade_plan_dict(
        validated.plan, (), git_mode=git_mode, git_branch=git_branch
    )
    preview["pending_recovery"] = list(validated.pending)
    preview["repowise"] = {
        key: validated.supplied[key]
        for key in sorted(REPOWISE_ANSWER_KEYS.intersection(validated.supplied))
    }
    messages = [
        f"pending transaction recovery not applied in dry-run: {item}"
        for item in validated.pending
    ]
    messages.append("Dry run: no changes were made.")
    return _upgrade_emit(
        validated.context, status="ok", exit_code=EXIT_OK,
        plan_data=preview, messages=tuple(messages),
    )


def _plan_upgrade(validated: UpgradeValidated) -> int | UpgradePlanState:
    """@brief Resolve Git and file decisions into an approval-ready plan."""
    git_result = _resolve_upgrade_git(validated)
    if isinstance(git_result, int):
        return git_result
    git_mode, git_branch = git_result
    fingerprints = _upgrade_fingerprints(validated)
    table = _upgrade_decision_table(validated, fingerprints)
    if isinstance(table, int):
        return table
    if validated.context.options.dry_run:
        return _upgrade_dry_run(validated, git_mode, git_branch)
    fallback = validated.context.on_conflict
    if fallback is None and validated.context.asker is not None:
        fallback = make_console_hook(validated.context.asker)
    hook = make_resolution_hook(table, fallback) if validated.plan.conflicts() else None
    try:
        decisions, outcomes = resolve_upgrade_decisions(validated.plan, hook)
    except (ConflictResolutionError, UpgradeError, ValueError) as exc:
        unresolved = _upgrade_plan_dict(
            validated.plan, (), git_mode=git_mode, git_branch=git_branch
        )
        return _upgrade_emit(
            validated.context, status="needs-input", exit_code=EXIT_NEEDS_INPUT,
            plan_data=unresolved, messages=(str(exc),),
        )
    plan_data = _upgrade_plan_dict(
        validated.plan, outcomes, git_mode=git_mode, git_branch=git_branch
    )
    plan_data["repowise"] = {
        key: validated.supplied[key]
        for key in sorted(REPOWISE_ANSWER_KEYS.intersection(validated.supplied))
    }
    return UpgradePlanState(
        validated, git_mode, git_branch, fingerprints,
        decisions, outcomes, plan_data,
    )


def _consent_upgrade(plan: UpgradePlanState) -> int | UpgradePlanState:
    """@brief Render and obtain explicit consent for the resolved upgrade."""
    context = plan.validated.context
    options = context.options
    if not options.as_json:
        _upgrade_emit(
            context, status="ok", exit_code=EXIT_OK, plan_data=plan.plan_data
        )
    consent = mutation_consent(
        mutation_planned=True, yes=options.yes, asker=context.asker,
        prompt="Apply this fully resolved upgrade plan?",
    )
    if consent is ConsentDecision.APPROVED:
        return plan
    return _upgrade_emit(
        context, status="needs-input", exit_code=EXIT_NEEDS_INPUT,
        plan_data=plan.plan_data if options.as_json else None,
        messages=(
            "upgrade plan was not approved" if consent is ConsentDecision.DECLINED
            else "upgrade mutation requires explicit --yes or an interactive approval",
        ),
    )


def _prepare_upgrade_branch(plan: UpgradePlanState) -> int | None:
    """@brief Create the approved dedicated branch before journaling."""
    if plan.git_mode != "branch-commit":
        return None
    context = plan.validated.context
    if plan.git_branch is None:
        return _upgrade_emit(
            context, status="failed", exit_code=EXIT_VALIDATION,
            messages=("git mode 'branch-commit' requires a branch name",),
        )
    result = gitops.create_branch(
        plan.validated.runner, context.repo_path, plan.git_branch
    )
    if result.ok:
        return None
    return _upgrade_emit(
        context, status="error", exit_code=EXIT_OPERATIONAL,
        plan_data=plan.plan_data if context.options.as_json else None,
        messages=(f"could not create upgrade branch {plan.git_branch!r}: {result.detail}",),
    )


def _begin_upgrade_journal(plan: UpgradePlanState) -> Journal:
    """@brief Begin the upgrade journal and record resolved decisions."""
    context = plan.validated.context
    journal = Journal.begin(
        mode="upgrade", wizard_version=WIZARD_VERSION,
        target=str(context.repo_path), home=context.options.home,
        fingerprints=plan.fingerprints,
    )
    result = StepResult(step_id="upgrade.decisions", status=StepStatus.DONE)
    result.answers = {
        "resolutions": {
            path: decision.value for path, decision in plan.decisions.items()
        },
        "git_mode": plan.git_mode,
    }
    journal.record(result)
    return journal


def _upgrade_apply_failure(
    plan: UpgradePlanState, journal: Journal, failure: UpgradeApplyError,
) -> int:
    """
    @brief      Journal and report one apply failure by the transaction's true
                terminal state.
    @details    Mirrors ``configure``'s ``_configure_apply_failure`` and
                ``repair``'s ``_repair_apply_failure``: a transaction that
                reached ``committed`` before its storage cleanup failed is a
                SUCCESSFUL upgrade and is never reported as failed-and-rolled-
                back, and a rollback that did not complete is never reported as
                if it had. The exit code stays :data:`EXIT_ERROR`
                (``EXIT_OPERATIONAL``) in every branch — the frozen upgrade
                exit-code contract — so the machine-readable distinction lives
                in the ``result`` mapping (``applied`` / ``rolled_back`` /
                ``cleanup_pending``) and in the message.
    @details    Whenever files are left on disk, a ``branch-commit`` run also
                says the changes are uncommitted: the Git commit step only runs
                for a clean apply, so an operator whose upgrade committed on
                disk would otherwise find the new payload in their working tree
                on a dedicated branch with nothing recorded in Git.
    @param[in]  plan The resolved plan being applied.
    @param[in]  journal The open upgrade journal.
    @param[in]  failure The typed apply failure raised by :func:`apply_upgrade`.
    @return     The command exit code.
    @exception  None
    """
    context = plan.validated.context
    cause = failure.cause
    detail = f"{type(cause).__name__}: {cause}"
    plan_data = plan.plan_data if context.options.as_json else None
    if plan.git_mode == "branch-commit" and plan.git_branch is not None:
        uncommitted = (
            "the files left on disk are NOT committed; they are in the working "
            f"tree on branch {plan.git_branch!r}",
        )
    else:
        uncommitted = ()
    if failure.committed:
        # The manifest and every file write are durable; only the transaction's
        # own storage cleanup failed. Journaling this as a failed run would be
        # the same false report the message used to make.
        journal.record(StepResult(
            step_id="upgrade.apply", status=StepStatus.DONE, error=detail,
        ))
        journal.finalize(status=STATUS_COMPLETED)
        return _upgrade_emit(
            context, status="error", exit_code=EXIT_ERROR, plan_data=plan_data,
            result_extra={"applied": True, "rolled_back": False, "cleanup_pending": True},
            messages=("upgrade committed, but transaction cleanup failed; "
                      f"recovery will retry cleanup: {cause}",) + uncommitted,
        )
    journal.record(StepResult(
        step_id="upgrade.apply", status=StepStatus.FAILED, error=detail,
    ))
    journal.finalize(status=STATUS_FAILED, stopped_at_step="upgrade.apply")
    if failure.rollback_error is not None:
        return _upgrade_emit(
            context, status="error", exit_code=EXIT_ERROR, plan_data=plan_data,
            result_extra={"applied": False, "rolled_back": False, "cleanup_pending": True},
            messages=("upgrade failed and rollback did not complete; the repository may "
                      "be partially upgraded and authenticated recovery state was "
                      f"retained: {failure.rollback_error} (original failure: {cause})",)
                     + uncommitted,
        )
    return _upgrade_emit(
        context, status="error", exit_code=EXIT_ERROR, plan_data=plan_data,
        result_extra={"applied": False, "rolled_back": True, "cleanup_pending": False},
        messages=(f"upgrade failed and was rolled back: {cause}",),
    )


def _apply_upgrade_journaled(
    plan: UpgradePlanState, journal: Journal,
) -> int | UpgradeReport:
    """
    @brief      Apply the upgrade and preserve journal failure semantics.
    @details    A failure raised inside the transaction body arrives as a typed
                :class:`UpgradeApplyError` and is reported by its true terminal
                state (:func:`_upgrade_apply_failure`). Anything else escaping
                :func:`apply_upgrade` was raised before the transaction opened
                — a decision-set mismatch, a sidecar collision, or a failure to
                begin the transaction — so no repository file was touched.
    @param[in]  plan The consented plan.
    @param[in]  journal The open upgrade journal.
    @return     The applied report, or a command exit code on failure.
    @exception  BaseException :class:`KeyboardInterrupt` / :class:`SystemExit`
                are re-raised after the journal is finalized.
    """
    context = plan.validated.context
    try:
        report = apply_upgrade(
            plan.validated.plan, runner=plan.validated.runner,
            decisions=plan.decisions, resolved_outcomes=plan.outcomes,
        )
    except UpgradeApplyError as failure:
        return _upgrade_apply_failure(plan, journal, failure)
    except BaseException as exc:
        journal.record(StepResult(
            step_id="upgrade.apply", status=StepStatus.FAILED,
            error=f"{type(exc).__name__}: {exc}",
        ))
        journal.finalize(status=STATUS_FAILED, stopped_at_step="upgrade.apply")
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return _upgrade_emit(
            context, status="error", exit_code=EXIT_ERROR,
            plan_data=plan.plan_data if context.options.as_json else None,
            result_extra={"applied": False, "rolled_back": False, "cleanup_pending": False},
            messages=(f"upgrade failed before any change was applied: {exc}",),
        )
    journal.record(StepResult(
        step_id="upgrade.apply",
        status=StepStatus.DONE if report.exit_code == EXIT_OK else StepStatus.FAILED,
    ))
    if report.exit_code == EXIT_OK:
        journal.finalize(status=STATUS_COMPLETED)
    else:
        journal.finalize(status=STATUS_FAILED, stopped_at_step="upgrade.apply")
    return report


def _commit_upgrade_git(
    plan: UpgradePlanState, report: UpgradeReport,
) -> int | None:
    """@brief Commit a successful branch-mode upgrade after journaling."""
    if report.exit_code != EXIT_OK or plan.git_mode != "branch-commit":
        return None
    runner = plan.validated.runner
    repo_path = plan.validated.context.repo_path
    add_result = gitops.add_all(runner, repo_path)
    commit_result = gitops.commit(
        runner, repo_path,
        f"Upgrade AEGIS to {plan.validated.plan.new_payload_version}",
    )
    if add_result.ok and commit_result.ok:
        return None
    context = plan.validated.context
    return _upgrade_emit(
        context, status="error", exit_code=EXIT_OPERATIONAL,
        plan_data=plan.plan_data if context.options.as_json else None,
        report=report,
        messages=("upgrade applied but Git commit failed; changes remain on the dedicated branch",),
    )


def _apply_upgrade(plan: UpgradePlanState) -> int | UpgradeOutcome:
    """@brief Apply branch, journal, transaction, and commit in original order."""
    branch_error = _prepare_upgrade_branch(plan)
    if branch_error is not None:
        return branch_error
    journal = _begin_upgrade_journal(plan)
    report = _apply_upgrade_journaled(plan, journal)
    if isinstance(report, int):
        return report
    commit_error = _commit_upgrade_git(plan, report)
    if commit_error is not None:
        return commit_error
    return UpgradeOutcome(plan, report)


def _report_upgrade(outcome: UpgradeOutcome) -> int:
    """@brief Run RepoWise post-processing and emit the upgrade outcome."""
    plan = outcome.plan
    validated = plan.validated
    context = validated.context
    options = context.options
    repowise_result: dict[str, Any] | None = None
    repowise_error: str | None = None
    requested = bool(REPOWISE_ANSWER_KEYS.intersection(validated.supplied)) or (
        context.asker is not None and not options.non_interactive
    )
    if outcome.report.exit_code == EXIT_OK and requested:
        try:
            repowise_result = lifecycle_repowise(
                context.repo_path, validated.supplied, lifecycle="upgrade",
                interactive=not options.non_interactive, asker=context.asker,
                stream=None if options.as_json else options.stream, yes=options.yes,
            )
        except (OSError, RepoWiseError) as exc:
            repowise_error = str(exc)
    if repowise_error or (repowise_result and not repowise_result["sync"]["ok"]):
        return _upgrade_emit(
            context, status="error", exit_code=EXIT_OPERATIONAL,
            plan_data=plan.plan_data if options.as_json else None,
            report=outcome.report,
            result_extra={
                "aegis": {"ok": True},
                "repowise": repowise_result or {
                    "aegis": "ok", "sync": {"ok": False, "error": repowise_error}
                },
            },
            messages=((repowise_error,) if repowise_error else ()),
        )
    return _upgrade_emit(
        context, status="ok" if outcome.report.exit_code == EXIT_OK else "failed",
        exit_code=outcome.report.exit_code,
        plan_data=plan.plan_data if options.as_json else None,
        report=outcome.report,
        result_extra={
            "aegis": {"ok": outcome.report.exit_code == EXIT_OK},
            "repowise": repowise_result,
        },
    )


def _run_upgrade_phases(
    repo: str | PathLike[str],
    *,
    options: CommandOptions,
    on_conflict: UpgradeConflictHook | None = None,
    resolutions: Mapping[str, str] | None = None,
    asker: ConsoleAsker | None = None,
) -> int:
    """@brief Orchestrate validate, plan, consent, apply, and report phases."""
    normalized = replace(
        options, non_interactive=options.non_interactive or options.as_json
    )
    context = UpgradeContext(
        Path(repo).resolve(), normalized, on_conflict, resolutions,
        None if options.as_json else asker,
    )
    validated = _validate_upgrade(context)
    if isinstance(validated, int):
        return validated
    plan = _plan_upgrade(validated)
    if isinstance(plan, int):
        return plan
    approved = _consent_upgrade(plan)
    if isinstance(approved, int):
        return approved
    outcome = _apply_upgrade(approved)
    if isinstance(outcome, int):
        return outcome
    return _report_upgrade(outcome)


def run_upgrade(
    repo: str | PathLike[str],
    *,
    as_json: bool,
    dry_run: bool,
    stream: IO[str],
    payload: str | None = None,
    answers_path: str | PathLike[str] | None = None,
    non_interactive: bool = False,
    yes: bool = False,
    on_conflict: UpgradeConflictHook | None = None,
    resolutions: Mapping[str, str] | None = None,
    asker: ConsoleAsker | None = None,
    runner: CommandRunner | None = None,
    home: Path | None = None,
) -> int:
    """
    @brief      Run the manifest-driven upgrade through its lifecycle phases.
    @details    Preserves the public conflict hook/resolution/asker seams.
                Dry-run remains read-only; unresolved conflicts stop before
                consent; apply remains journaled and transactional; Git commit
                and RepoWise processing retain their established order.
    @param[in]  repo Repository root to upgrade.
    @param[in]  as_json Emit the frozen JSON envelope instead of a human report.
    @param[in]  dry_run Build and render the plan only; write nothing.
    @param[in]  stream Output stream for the human report or JSON envelope.
    @param[in]  payload Optional explicit new payload path/version selector.
    @param[in]  answers_path Optional path to a pre-supplied answers file
                (``git_mode``, ``git_branch``, ``upgrade_conflicts``, and the
                RepoWise answer keys).
    @param[in]  non_interactive Refuse to prompt; missing required answers
                stop the run with ``needs-input``.
    @param[in]  yes Treat mutation consent as pre-approved.
    @param[in]  on_conflict Optional per-conflict decision hook (the
                :data:`UpgradeConflictHook` seam).
    @param[in]  resolutions Optional ``{path: decision}`` table merged ahead of
                ``on_conflict``.
    @param[in]  asker Optional console asker for interactive git-mode and
                conflict prompts; ignored when ``as_json`` is set.
    @param[in]  runner Injectable command runner for Git and smoke operations;
                defaults to the real subprocess runner.
    @param[in]  home Optional override for the WAEGIS home directory used for
                journal resume lookups.
    @return     Standardized command exit code 0/1/2/3.
    @exception  None Operational failures are rendered and mapped to exit codes;
                KeyboardInterrupt and SystemExit are re-raised after journaling.
    """
    return _run_upgrade_phases(
        repo,
        options=CommandOptions(
            stream, None, runner, home, yes, dry_run, non_interactive,
            as_json, answers_path, payload,
        ),
        on_conflict=on_conflict,
        resolutions=resolutions,
        asker=asker,
    )




# END OF FILE
