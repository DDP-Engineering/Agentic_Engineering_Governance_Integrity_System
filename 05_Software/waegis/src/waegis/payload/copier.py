#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file copier.py
@brief Manifest-aware, byte-verbatim payload copier with conflict handling.
@details Task T3.2: absorbs the proven safe-copy semantics of
         ``02_Tools/create_project_from_template.py`` (exclusion rules,
         never-overwrite default, force override, dry-run preview) and extends
         them with adoption conflict classification (does-not-exist /
         exists-identical / exists-different), a caller-supplied per-conflict
         decision hook, and install-manifest emission (plan §6, AD-6).
@details **The one rule this module exists to enforce:** an exists-and-different
         conflict is never resolved internally — every resolution flows through
         the caller-supplied :data:`ConflictDecisionHook`. The single explicit
         exception is ``force=True`` (the legacy ``--force`` per-call
         override), which is implemented as an internal constant
         take-payload hook so even that path uses the same resolution code;
         ``force`` combined with a caller hook is rejected as ambiguous.
@details **No-partial-write guarantee:** the copy runs in two phases — a
         read-only scan/classify/decide phase (existence checks, hashing,
         refusals, and every hook call) followed by the apply phase. A
         strict-mode overwrite refusal, an invalid hook return, or an
         exception raised by the hook therefore always leaves the target
         completely untouched.
@details Library only: never prints, imports no network code, and touches
         nothing outside the given payload root (read) and target root
         (write). Hashing is delegated to :func:`waegis.payload.manifest.hash_file`
         and manifest emission to ``build_manifest``/``write_manifest`` — no
         duplicated logic. Files are copied with :func:`shutil.copy2`
         (binary, byte-verbatim, no newline translation) so the copied file's
         hash always equals the source hash.
@details **Execute-bit backstop (added 0.3.0, architecture-review
         follow-up).** :func:`ensure_executable` grants the POSIX execute bit
         on every copied file whose suffix is in :data:`EXECUTABLE_SUFFIXES`
         (currently ``.sh``), called right after every ``shutil.copy2`` in
         :func:`copy_payload`. A no-op on Windows.
@author Eng. Dan Dumitru Pasare
@date 2026-07-18
@version 0.3.0
"""

# IMPORTS

from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from fnmatch import fnmatchcase
from enum import Enum
from os import PathLike
from pathlib import Path, PurePath
from typing import Any, Callable, Iterable, Mapping

from .locate import read_payload_version
from .manifest import (
    MANIFEST_RELATIVE_PATH,
    FileEntry,
    Manifest,
    build_manifest,
    digest_file_entries,
    hash_file,
    resolve_managed_path,
    write_manifest,
)

# CONSTANTS

# @brief Directory-name parts never copied into a target (generated or
#        dependency state; `node_modules`/`.vitest` belong to the `.pi/`
#        adapter's isolated vitest setup). Ported verbatim from
#        02_Tools/create_project_from_template.py.
EXCLUDED_PARTS = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".vitest"})

# @brief File suffixes never copied into a target.
EXCLUDED_SUFFIXES = frozenset({".pyc"})

# @brief Glob patterns (matched against the payload-relative path) never
#        copied into a target.
EXCLUDED_PATTERNS = ("*.egg-info", ".uv-cache*")

# @brief Fallback recorded as the manifest payload_version when the payload
#        ships no readable version declaration.
UNKNOWN_PAYLOAD_VERSION = "unknown"

# @brief Suffix appended to a conflicting payload file's name for the
#        write-payload-beside-it decision.
SIDECAR_SUFFIX = ".new"

# @brief File suffixes granted the POSIX execute bit after copying (added
#        0.3.0, architecture-review follow-up): shell scripts meant to be run
#        directly (``./run.sh``), not only via ``bash run.sh``. No-op on
#        Windows. See :func:`ensure_executable`.
EXECUTABLE_SUFFIXES = frozenset({".sh"})

# DATA MODELS / TYPEDEFINITIONS


class ConflictDecision(Enum):
    """
    @brief The three legal answers to an exists-and-different conflict.
    @details ``KEEP_LOCAL`` — the local file is kept and the payload file is
             not written (recorded under the manifest's ``skipped``).
             ``TAKE_PAYLOAD`` — the payload file overwrites the local one.
             ``WRITE_NEW`` — the local file is kept and the payload content is
             written byte-verbatim as ``<name>.new`` beside it (the payload
             path itself is still recorded under ``skipped`` so ``upgrade``
             re-offers it).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    KEEP_LOCAL = "keep-local"
    TAKE_PAYLOAD = "take-payload"
    WRITE_NEW = "write-new"


@dataclass(frozen=True)
class PayloadConflict:
    """
    @brief One exists-and-different conflict: a payload file whose target path
           already holds different bytes.
    @details Carries both sides' path, size, and sha256 (via the manifest
             module's :class:`FileEntry`) so an interactive wizard or a
             non-interactive ``--json`` caller can render/report the conflict
             fully before deciding.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    relative_path: str
    source_path: Path
    target_path: Path
    source_entry: FileEntry
    target_entry: FileEntry


# @brief Caller-supplied per-conflict decision hook: given one conflict,
#        return one ConflictDecision. Called exactly once per
#        exists-and-different file, in sorted relative-path order, and never
#        for missing or byte-identical files. Conflicts are NEVER resolved
#        without this hook (force=True is an internal constant take-payload
#        hook, the one documented exception).
ConflictDecisionHook = Callable[[PayloadConflict], ConflictDecision]


@dataclass(frozen=True)
class ConflictResolution:
    """
    @brief One conflict together with the decision taken for it.
    @details ``written_path`` is the repo-relative POSIX path actually written
             for the decision: the payload path for ``TAKE_PAYLOAD``, the
             ``<name>.new`` sidecar for ``WRITE_NEW``, ``None`` for
             ``KEEP_LOCAL``.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    conflict: PayloadConflict
    decision: ConflictDecision
    written_path: str | None


@dataclass(frozen=True)
class CopyResult:
    """
    @brief Structured outcome of one :func:`copy_payload` run.
    @details ``copied`` — repo-relative POSIX paths written verbatim (or that
             would be written, on dry-run); sidecar ``.new`` files are not
             listed here, only in their resolution's ``written_path``.
             ``identical`` — pre-existing byte-identical files that were left
             in place (adoption mode) yet recorded in the manifest ``files``
             as if freshly copied, since the content matches the payload.
             ``conflicts`` — every exists-and-different file found.
             ``resolutions`` — one entry per conflict on a real run; empty on
             dry-run (the hook is not called on dry-run).
             ``skipped`` — payload paths kept local (``KEEP_LOCAL`` and
             ``WRITE_NEW`` decisions), i.e. the manifest's ``skipped``.
             ``manifest``/``manifest_file`` — the emitted manifest and its
             path; both ``None`` on dry-run, which writes nothing at all.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    target: Path
    copied: tuple[str, ...]
    identical: tuple[str, ...]
    conflicts: tuple[PayloadConflict, ...]
    resolutions: tuple[ConflictResolution, ...]
    skipped: tuple[str, ...]
    manifest: Manifest | None
    manifest_file: Path | None
    dry_run: bool


@dataclass(frozen=True)
class PayloadInventory:
    """
    @brief Validated, byte-hashed inventory of one payload tree.
    @details Included paths have passed exclusion, canonical-path, regular-file,
             and source symlink/junction checks. ``digest`` is stable across
             machines and is suitable for manifests and journal fingerprints.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-16
    @version 0.1.0
    """

    root: Path
    directories: tuple[PurePath, ...]
    files: tuple[PurePath, ...]
    entries: dict[str, FileEntry]
    digest: str


class CopierError(Exception):
    """
    @brief Base error for payload copy failures.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class PayloadMissingError(CopierError):
    """
    @brief The payload (template) root directory does not exist.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class TargetDirectoryMissingError(CopierError):
    """
    @brief ``require_existing_target`` was set but the target directory does
           not exist (guards against typo paths in existing-repo adoption).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class OverwriteRefusedError(CopierError):
    """
    @brief Strict new-project mode found pre-existing destination files.
    @details Raised before anything is written; ``conflicting_paths`` carries
             every pre-existing destination (sorted), while the message names
             the first one in the legacy
             ``"Refusing to overwrite existing file: ..."`` format.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(self, conflicting_paths: tuple[Path, ...]) -> None:
        """
        @brief      Build the refusal error from the sorted conflict paths.
        @param[in]  conflicting_paths Every pre-existing destination file.
        @return     None
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        self.conflicting_paths = conflicting_paths
        super().__init__(f"Refusing to overwrite existing file: {conflicting_paths[0]}")


# LOCAL HELPERS


def _force_take_payload(conflict: PayloadConflict) -> ConflictDecision:
    """
    @brief      The internal constant hook implementing the legacy ``force``
                override: every conflict resolves to take-payload.
    @param[in]  conflict The conflict being resolved (unused).
    @return     ``ConflictDecision.TAKE_PAYLOAD``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return ConflictDecision.TAKE_PAYLOAD


# EXPORTED FUNCTIONS / PUBLIC API


def ensure_executable(destination: Path) -> None:
    """
    @brief      Grant the POSIX owner/group/other execute bits on a just-copied
                file whose suffix is in :data:`EXECUTABLE_SUFFIXES`.
    @details    ``shutil.copy2`` already preserves the source file's own mode,
                which is normally sufficient once the payload's own git mode
                is correct. This is a defensive backstop for a payload that
                arrives with the bit already lost in transit (e.g. a payload
                cache populated from a checkout with ``core.filemode``
                disabled, or a zip/tarball extraction that dropped it) — a
                target on Ubuntu should never end up with a non-executable
                ``run.sh`` regardless of how the payload got there. A no-op
                on Windows (``os.name == "nt"``): there is no POSIX execute
                bit to set, and ``Path.chmod`` there only toggles the
                read-only attribute, which is not what this is for. Public
                (not copier-internal) since :mod:`waegis.commands.repair` and
                :mod:`waegis.commands.upgrade` copy payload files through
                their own code paths and need the same backstop.
    @param[in]  destination The just-written file path.
    @return     None
    @exception  OSError If ``stat``/``chmod`` fails for a reason other than
                the file not existing (propagated, not swallowed, since a
                silent failure here would ship a non-executable script with
                no signal).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    if os.name == "nt" or destination.suffix not in EXECUTABLE_SUFFIXES:
        return
    mode = destination.stat().st_mode
    destination.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def should_exclude(path: PurePath) -> bool:
    """
    @brief      Return whether a payload-relative path is generated or
                dependency state that must never be copied into a target.
    @details    Ported from ``create_project_from_template.py`` (excluded
                directory parts, excluded suffixes, excluded glob patterns)
                with one deliberate fix: the glob patterns are matched against
                *every* path component, not only the final one. The legacy
                ``path.match(pattern)`` variant excluded a ``pkg.egg-info``
                directory itself but still copied the files inside it
                (recreating the directory via ``mkdir(parents=True)``);
                pattern-named cache/metadata trees are now excluded whole.
    @param[in]  path Path relative to the payload root.
    @return     True when the path must not be copied.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.2.0
    """
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    return any(fnmatchcase(part, pattern) for part in path.parts for pattern in EXCLUDED_PATTERNS)


def inspect_payload(payload_root: str | PathLike[str]) -> PayloadInventory:
    """
    @brief      Validate and hash the complete copyable payload inventory.
    @param[in]  payload_root Payload root directory.
    @return     Deterministic :class:`PayloadInventory`.
    @exception  PayloadMissingError If the root is not a directory.
    @exception  CopierError If an included source is unsafe or not regular.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    root = Path(payload_root).resolve()
    if not root.is_dir():
        raise PayloadMissingError(f"Template directory not found: {root}")
    dirs: list[PurePath] = []
    files: list[PurePath] = []
    entries: dict[str, FileEntry] = {}
    for source in sorted(root.rglob("*")):
        relative = source.relative_to(root)
        if should_exclude(relative):
            continue
        key = relative.as_posix()
        try:
            safe_source = resolve_managed_path(root, key)
        except ValueError as exc:
            raise CopierError(f"unsafe payload source path {key!r}: {exc}") from exc
        if source.is_dir():
            dirs.append(relative)
            continue
        if key == MANIFEST_RELATIVE_PATH:
            continue
        if not safe_source.is_file():
            raise CopierError(f"payload source is not a regular file: {safe_source}")
        files.append(relative)
        entries[key] = hash_file(safe_source)
    return PayloadInventory(
        root=root,
        directories=tuple(dirs),
        files=tuple(files),
        entries=entries,
        digest=digest_file_entries(entries),
    )


def copy_payload(
    payload_root: str | PathLike[str],
    target: str | PathLike[str],
    *,
    mode: str,
    force: bool = False,
    dry_run: bool = False,
    require_existing_target: bool = False,
    on_conflict: ConflictDecisionHook | None = None,
    payload_version: str | None = None,
    product: str = "aegis",
    generated: Iterable[str] = (),
    configuration: Mapping[str, Any] | None = None,
    installed_at: str | None = None,
    installed_by: str | None = None,
) -> CopyResult:
    """
    @brief      Copy a payload tree into a target root byte-verbatim, resolve
                conflicts through the caller's hook, and emit the install
                manifest.
    @details    Mode selection is by argument: with neither ``force`` nor
                ``on_conflict`` the copy is strict new-project mode and *any*
                pre-existing destination file (identical or different — exact
                legacy-script parity) raises :class:`OverwriteRefusedError`
                before anything is written. With ``on_conflict`` (adoption
                mode) each payload file is classified does-not-exist (copied),
                exists-identical (left in place, still recorded in the
                manifest ``files`` since content matches), or
                exists-different (a conflict — the hook is called exactly once
                per such file, in sorted order). With ``force=True`` every
                conflict resolves internally to take-payload (legacy
                ``--force``) and pre-existing identical files are rewritten,
                preserving the legacy copied-count.
    @details    Two-phase execution: scan/classify/decide first (read-only —
                includes every hook call), apply second; refusals and hook
                errors therefore leave the target untouched. Dry-run returns
                after classification: ``copied`` holds the would-be
                destinations, ``conflicts`` is populated, the hook is not
                called, and nothing (including the manifest) is written.
    @details    The manifest (plan §6) is written to
                ``<target>/.agentic/install-manifest.json`` with ``files`` =
                every payload-sourced file present at the target (copied +
                identical), hashed at the *target* via ``build_manifest`` (the
                hashes equal the source hashes because the copy is
                byte-verbatim), ``generated`` passed through from the caller
                (T4.1 extends it later), and ``skipped`` = the keep-local and
                write-new payload paths. Sidecar ``.new`` files are not
                manifest entries. A ``.agentic/install-manifest.json`` found
                inside the payload source is defensively never copied.
    @param[in]  payload_root Payload (template) root directory to copy from.
    @param[in]  target Target project root to copy into (created if needed).
    @param[in]  mode Manifest ``mode`` value: ``"new"`` or ``"adopt"`` —
                decided by the caller, not this function.
    @param[in]  force Legacy overwrite override; mutually exclusive with
                ``on_conflict``.
    @param[in]  dry_run Classify and report without writing anything.
    @param[in]  require_existing_target Fail if the target directory does not
                already exist (existing-repo adoption guard).
    @param[in]  on_conflict Per-conflict decision hook; required for any
                conflict to be resolved (never decided internally).
    @param[in]  payload_version Manifest payload version; defaults to the
                version read from the payload's own declaration, falling back
                to ``"unknown"``.
    @param[in]  product Manifest product name.
    @param[in]  generated Repo-relative paths recorded as wizard-generated.
    @param[in]  installed_at Manifest timestamp override (tests).
    @param[in]  installed_by Manifest installer-string override (tests).
    @return     A :class:`CopyResult`; all path collections are sorted
                repo-relative POSIX strings.
    @exception  ValueError If ``force`` and ``on_conflict`` are both given.
    @exception  PayloadMissingError If ``payload_root`` is not a directory.
    @exception  TargetDirectoryMissingError If ``require_existing_target`` is
                set and ``target`` is not a directory.
    @exception  OverwriteRefusedError In strict mode when any destination file
                pre-exists.
    @exception  CopierError If a destination exists but is not a regular file,
                the hook returns a non-``ConflictDecision``, or a ``WRITE_NEW``
                sidecar path already exists with different content.
    @exception  OSError If reading or writing a file fails mid-apply (files
                already applied remain — disk-level failures are outside the
                no-partial-write guarantee, which covers refusals and hook
                errors).
    @details    Every write (``copied`` and sidecar) now also runs through
                :func:`ensure_executable` (0.3.0), so a shell script payload
                file always lands executable on a POSIX target regardless of
                the source's own mode.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.2.0
    """
    if force and on_conflict is not None:
        raise ValueError("force=True and on_conflict are mutually exclusive: force is the constant take-payload hook")

    inventory = inspect_payload(payload_root)
    payload_root = inventory.root

    target = Path(target).resolve()
    if require_existing_target and not target.is_dir():
        raise TargetDirectoryMissingError(f"Existing repository directory not found: {target}")

    # Phase 1 — scan (read-only): payload-relative dirs and files, exclusions
    # applied, a payload-shipped manifest defensively skipped.
    dirs = list(inventory.directories)
    files = list(inventory.files)
    source_entries = inventory.entries

    # Phase 1 — classify. Strict mode refuses on bare existence (legacy
    # parity, no hashing needed); adoption/force mode hashes both sides.
    strict = on_conflict is None and not force
    if strict:
        destinations = tuple(resolve_managed_path(target, rel.as_posix()) for rel in files)
        existing = tuple(sorted(path for path in destinations if path.exists()))
        if existing:
            raise OverwriteRefusedError(existing)

    missing: list[PurePath] = []
    identical: list[PurePath] = []
    rewritten: list[PurePath] = []  # force mode: pre-existing identical files rewritten (legacy count parity)
    conflicts: list[PayloadConflict] = []
    for relative in files:
        destination = resolve_managed_path(target, relative.as_posix())
        if not destination.exists():
            missing.append(relative)
            continue
        if not destination.is_file():
            raise CopierError(f"destination exists and is not a regular file: {destination}")
        source_entry = source_entries[relative.as_posix()]
        target_entry = hash_file(destination)
        if source_entry.sha256 == target_entry.sha256:
            (rewritten if force else identical).append(relative)
        else:
            conflicts.append(
                PayloadConflict(
                    relative_path=relative.as_posix(),
                    source_path=payload_root / relative,
                    target_path=destination,
                    source_entry=source_entry,
                    target_entry=target_entry,
                )
            )
    conflicts.sort(key=lambda conflict: conflict.relative_path)

    if dry_run:
        would_copy = missing + rewritten + ([PurePath(c.relative_path) for c in conflicts] if force else [])
        return CopyResult(
            target=target,
            copied=tuple(sorted(rel.as_posix() for rel in would_copy)),
            identical=tuple(sorted(rel.as_posix() for rel in identical)),
            conflicts=tuple(conflicts),
            resolutions=(),
            skipped=(),
            manifest=None,
            manifest_file=None,
            dry_run=True,
        )

    # Phase 1 — decide: every conflict goes through the hook (force is the
    # internal constant take-payload hook). Still read-only.
    hook: ConflictDecisionHook | None = _force_take_payload if force else on_conflict
    resolutions: list[ConflictResolution] = []
    take_payload: list[PurePath] = []
    skipped: list[str] = []
    sidecar_writes: list[tuple[PurePath, PurePath]] = []  # (payload-relative source, sidecar-relative destination)
    for conflict in conflicts:
        assert hook is not None  # strict mode raised above when conflicts could exist
        decision = hook(conflict)
        if not isinstance(decision, ConflictDecision):
            raise CopierError(
                f"conflict decision hook returned {decision!r} for {conflict.relative_path!r}; expected a ConflictDecision"
            )
        relative = PurePath(conflict.relative_path)
        written_path: str | None
        if decision is ConflictDecision.TAKE_PAYLOAD:
            take_payload.append(relative)
            written_path = conflict.relative_path
        elif decision is ConflictDecision.KEEP_LOCAL:
            skipped.append(conflict.relative_path)
            written_path = None
        else:  # ConflictDecision.WRITE_NEW
            sidecar = relative.with_name(relative.name + SIDECAR_SUFFIX)
            sidecar_destination = resolve_managed_path(target, sidecar.as_posix())
            if sidecar_destination.exists() and (
                not sidecar_destination.is_file()
                or hash_file(sidecar_destination).sha256 != conflict.source_entry.sha256
            ):
                raise CopierError(f"refusing to overwrite existing sidecar file: {sidecar_destination}")
            sidecar_writes.append((relative, sidecar))
            skipped.append(conflict.relative_path)
            written_path = sidecar.as_posix()
        resolutions.append(ConflictResolution(conflict=conflict, decision=decision, written_path=written_path))

    # Phase 2 — apply. Everything below writes; all refusals happened above.
    target.mkdir(parents=True, exist_ok=True)
    for relative in dirs:
        resolve_managed_path(target, relative.as_posix()).mkdir(parents=True, exist_ok=True)
    copied = missing + rewritten + take_payload
    for relative in copied:
        destination = resolve_managed_path(target, relative.as_posix())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolve_managed_path(payload_root, relative.as_posix()), destination)
        ensure_executable(destination)
    for relative, sidecar in sidecar_writes:
        sidecar_destination = resolve_managed_path(target, sidecar.as_posix())
        sidecar_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolve_managed_path(payload_root, relative.as_posix()), sidecar_destination)
        ensure_executable(sidecar_destination)

    if payload_version is None:
        payload_version = read_payload_version(payload_root) or UNKNOWN_PAYLOAD_VERSION
    manifest = build_manifest(
        target,
        product=product,
        payload_version=payload_version,
        mode=mode,
        file_paths=[rel.as_posix() for rel in copied + identical],
        generated=generated,
        skipped=skipped,
        payload_digest=inventory.digest,
        configuration=configuration,
        installed_at=installed_at,
        installed_by=installed_by,
    )
    manifest_file = write_manifest(target, manifest)

    return CopyResult(
        target=target,
        copied=tuple(sorted(rel.as_posix() for rel in copied)),
        identical=tuple(sorted(rel.as_posix() for rel in identical)),
        conflicts=tuple(conflicts),
        resolutions=tuple(resolutions),
        skipped=tuple(sorted(skipped)),
        manifest=manifest,
        manifest_file=manifest_file,
        dry_run=False,
    )


# END OF FILE
