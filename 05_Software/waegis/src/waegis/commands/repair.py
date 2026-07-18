#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file repair.py
@brief Transactional repair of missing, modified, and generated managed files.
@details Missing payload files are restorable only when payload bytes match the
         original hash in the install manifest. Modified files require an
         explicit keep/take/sidecar decision. Generated configuration is
         regenerated from stored or supplied answers. Verification precedes
         the manifest-last commit, and every failure rolls back.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import IO, Any, Mapping

from ..io.answers import AnswersFileError, load_answers_file
from ..io.envelope import EXIT_NEEDS_INPUT, EXIT_OK, EXIT_OPERATIONAL, EXIT_VALIDATION, write_envelope
from ..io.prompts import ConsoleAsker, FieldSpec
from ..payload.copier import CopierError, SIDECAR_SUFFIX, ensure_executable, inspect_payload
from ..payload.locate import PayloadLocateError, locate_payload, read_payload_version
from ..payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    ManifestState,
    compute_drift,
    hash_file,
    load_manifest,
    resolve_managed_path,
    write_manifest,
)
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..repo.workflow_toml import generate_workflow_toml
from ..transaction import FileTransaction, recover_incomplete_transactions
from ..verification import smoke_reverify
from ..version import PAYLOAD_COMPAT_SPEC, WIZARD_VERSION, is_payload_compatible
from .configure import _CONFIG_KEYS, _stored_answers
from .new import WORKFLOW_TOML_RELATIVE_PATH

# CONSTANTS

_DECISIONS = frozenset({"keep-local", "take-payload", "write-new"})
_CONTROL_KEYS = frozenset({"repair_conflicts", "run_smoke"})


# HELPER FUNCTIONS


def _emit(
    stream: IO[str],
    *,
    as_json: bool,
    status: str,
    exit_code: int,
    plan: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
    messages: tuple[str, ...] = (),
) -> int:
    """@brief Emit repair output and return the standardized exit code."""
    if as_json:
        return write_envelope(
            stream,
            "repair",
            status=status,
            exit_code=exit_code,
            plan=plan,
            result=result,
            messages=messages,
        )
    for message in messages:
        stream.write(message + "\n")
    if plan is not None:
        stream.write(
            "Repair plan: "
            f"restore {len(plan.get('restore_missing', []))}, "
            f"resolve {len(plan.get('modified', []))}, "
            f"regenerate {len(plan.get('regenerate', []))}.\n"
        )
    if result is not None and result.get("repaired"):
        stream.write("Repair completed and verified.\n")
    return exit_code


def _decision(raw: Any) -> str:
    """@brief Normalize one repair conflict decision."""
    value = str(raw).strip().lower()
    if value not in _DECISIONS:
        raise ValueError("choose one of: keep-local, take-payload, write-new")
    return value


def _sidecar(relative: str) -> str:
    """@brief Return the canonical ``.new`` sidecar relative path."""
    path = PurePosixPath(relative)
    return path.with_name(path.name + SIDECAR_SUFFIX).as_posix()


def _configuration_answers(
    manifest_configuration: Mapping[str, Any], supplied: Mapping[str, Any]
) -> dict[str, Any]:
    """@brief Merge stored and explicitly supplied generator answers."""
    answers = _stored_answers(manifest_configuration)
    answers.update({key: value for key, value in supplied.items() if key in _CONFIG_KEYS})
    return answers


# EXPORTED FUNCTIONS / PUBLIC API


def run_repair(
    repo: str | os.PathLike[str],
    *,
    stream: IO[str],
    answers_path: str | os.PathLike[str] | None = None,
    dry_run: bool = False,
    non_interactive: bool = False,
    yes: bool = False,
    as_json: bool = False,
    payload: str | os.PathLike[str] | None = None,
    stdin: IO[str] | None = None,
    runner: CommandRunner | None = None,
) -> int:
    """
    @brief      Repair one installed repository with rollback guarantees.
    @details    The interactive conflict-decision prompt (`keep-local`/
                `take-payload`/`write-new`) now renders as a numbered menu via
                `FieldSpec.choices` (0.1.1) instead of requiring the operator
                to type the full word.
    @details    Every restored/rewritten file now also runs through
                `ensure_executable` (0.1.2), the same POSIX execute-bit
                backstop `copy_payload` applies.
    @return     Standardized exit code 0/1/2/3.
    @exception  None All errors are rendered.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.2
    """
    repo_path = Path(repo).resolve()
    if as_json:
        non_interactive = True
    if not repo_path.is_dir():
        return _emit(
            stream,
            as_json=as_json,
            status="error",
            exit_code=EXIT_OPERATIONAL,
            messages=(f"--repo path does not exist or is not a directory: {repo_path}",),
        )
    try:
        recovered = recover_incomplete_transactions(repo_path)
    except (OSError, ValueError) as exc:
        return _emit(
            stream,
            as_json=as_json,
            status="error",
            exit_code=EXIT_OPERATIONAL,
            messages=(f"could not recover an interrupted transaction: {exc}",),
        )
    load = load_manifest(repo_path)
    if load.state is not ManifestState.VALID or load.manifest is None:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            messages=("repair requires a valid current install manifest",),
        )
    manifest = load.manifest
    supplied: dict[str, Any] = {}
    if answers_path is not None:
        try:
            supplied = load_answers_file(answers_path)
        except AnswersFileError as exc:
            return _emit(stream, as_json=as_json, status="failed", exit_code=EXIT_VALIDATION, messages=(str(exc),))
    unknown = sorted(set(supplied) - _CONFIG_KEYS - _CONTROL_KEYS)
    if unknown:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            messages=("unrecognized answer key(s): " + ", ".join(unknown),),
        )
    try:
        payload_root = locate_payload(payload)
        inventory = inspect_payload(payload_root)
        payload_version = read_payload_version(payload_root)
        if payload_version is None or not is_payload_compatible(payload_version):
            raise ValueError(
                f"payload version {payload_version or 'unknown'!r} is incompatible; expected {PAYLOAD_COMPAT_SPEC}"
            )
    except (PayloadLocateError, CopierError, ValueError, OSError) as exc:
        return _emit(stream, as_json=as_json, status="failed", exit_code=EXIT_VALIDATION, messages=(str(exc),))

    drift = compute_drift(repo_path, manifest)
    unavailable: list[str] = []
    for relative in drift.missing:
        source_entry = inventory.entries.get(relative)
        if source_entry is None or source_entry.sha256 != manifest.files[relative].sha256:
            unavailable.append(relative)
    if unavailable:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            result={"unavailable": unavailable},
            messages=("payload bytes do not match recorded originals for: " + ", ".join(unavailable),),
        )

    raw_table = supplied.get("repair_conflicts", {})
    if not isinstance(raw_table, Mapping):
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            messages=("repair_conflicts must be a path-to-decision mapping",),
        )
    decisions: dict[str, str] = {}
    asker = None if non_interactive else ConsoleAsker(stdin=stdin or sys.stdin, stdout=stream)
    try:
        for relative in drift.modified:
            if relative in raw_table:
                decisions[relative] = _decision(raw_table[relative])
            elif asker is not None:
                spec = FieldSpec(
                    key=f"repair:{relative}",
                    description=(
                        f"Managed file {relative} was modified. Choose keep-local, take-payload, or write-new."
                    ),
                    example="keep-local",
                    default="keep-local",
                    validator=_decision,
                    choices=("keep-local", "take-payload", "write-new"),
                )
                decisions[relative] = asker.ask_field(spec)
    except ValueError as exc:
        return _emit(stream, as_json=as_json, status="failed", exit_code=EXIT_VALIDATION, messages=(str(exc),))
    unresolved = [path for path in drift.modified if path not in decisions]
    for relative, decision in decisions.items():
        if decision == "keep-local":
            continue
        source_entry = inventory.entries.get(relative)
        if source_entry is None or source_entry.sha256 != manifest.files[relative].sha256:
            unavailable.append(relative)
    if unavailable:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            result={"unavailable": sorted(set(unavailable))},
            messages=(
                "payload bytes do not match recorded originals for: "
                + ", ".join(sorted(set(unavailable))),
            ),
        )

    configuration_answers = _configuration_answers(manifest.configuration, supplied)
    generated_metadata = manifest.configuration.get("generated_files")
    regenerate: list[str] = []
    for relative in manifest.generated:
        target = resolve_managed_path(repo_path, relative)
        metadata = generated_metadata.get(relative) if isinstance(generated_metadata, Mapping) else None
        expected = metadata.get("sha256") if isinstance(metadata, Mapping) else None
        if not target.is_file() or not isinstance(expected, str) or hash_file(target).sha256 != expected:
            regenerate.append(relative)
    if regenerate and (
        regenerate != [WORKFLOW_TOML_RELATIVE_PATH]
        or not all(key in configuration_answers for key in ("source_roots", "test_roots", "language", "gate_test_cmds", "gate_lint_cmds", "alignment_enabled"))
    ):
        return _emit(
            stream,
            as_json=as_json,
            status="needs-input",
            exit_code=EXIT_NEEDS_INPUT,
            result={"regenerate": regenerate},
            messages=("generated configuration metadata/answers are incomplete; run waegis configure",),
        )
    plan = {
        "repo": str(repo_path),
        "restore_missing": list(drift.missing),
        "modified": [{"path": path, "decision": decisions.get(path)} for path in drift.modified],
        "regenerate": regenerate,
        "recovered_transactions": list(recovered),
    }
    if unresolved:
        return _emit(
            stream,
            as_json=as_json,
            status="needs-input",
            exit_code=EXIT_NEEDS_INPUT,
            plan=plan,
            messages=("modified files require explicit decisions: " + ", ".join(unresolved),),
        )
    mutations = bool(drift.missing or drift.modified or regenerate)
    if dry_run:
        return _emit(stream, as_json=as_json, status="ok", exit_code=EXIT_OK, plan=plan)
    if not mutations:
        return _emit(
            stream,
            as_json=as_json,
            status="ok",
            exit_code=EXIT_OK,
            plan=plan,
            result={"repaired": False, "no_op": True},
        )
    if non_interactive and not yes:
        return _emit(
            stream,
            as_json=as_json,
            status="needs-input",
            exit_code=EXIT_NEEDS_INPUT,
            plan=plan,
            messages=("non-interactive mutation requires --yes",),
        )
    if not yes and asker is not None and not asker.confirm("Apply this repair plan?", default=True):
        return _emit(
            stream,
            as_json=as_json,
            status="needs-input",
            exit_code=EXIT_NEEDS_INPUT,
            plan=plan,
            messages=("repair plan was not approved",),
        )

    affected = set(drift.missing) | set(regenerate) | {MANIFEST_RELATIVE_PATH}
    for path, decision in decisions.items():
        if decision == "take-payload":
            affected.add(path)
        elif decision == "write-new":
            affected.add(_sidecar(path))
    transaction: FileTransaction | None = None
    try:
        transaction = FileTransaction.begin(repo_path, command="repair", paths=sorted(affected))
        transaction.mark("applying")
        for relative in drift.missing:
            destination = resolve_managed_path(repo_path, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resolve_managed_path(payload_root, relative), destination)
            ensure_executable(destination)
        skipped = set(manifest.skipped)
        files = dict(manifest.files)
        for relative, decision in decisions.items():
            if decision == "take-payload":
                take_payload_destination = resolve_managed_path(repo_path, relative)
                shutil.copy2(resolve_managed_path(payload_root, relative), take_payload_destination)
                ensure_executable(take_payload_destination)
                skipped.discard(relative)
            else:
                files.pop(relative, None)
                skipped.add(relative)
                if decision == "write-new":
                    sidecar = resolve_managed_path(repo_path, _sidecar(relative))
                    sidecar.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(resolve_managed_path(payload_root, relative), sidecar)
                    ensure_executable(sidecar)
        configuration = dict(manifest.configuration)
        if regenerate:
            workflow = resolve_managed_path(repo_path, WORKFLOW_TOML_RELATIVE_PATH)
            base = (
                workflow.read_text(encoding="utf-8")
                if workflow.is_file()
                else resolve_managed_path(payload_root, WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
            )
            generated = generate_workflow_toml(base, **configuration_answers)
            temporary = workflow.with_name(workflow.name + ".waegis-tmp")
            temporary.write_text(generated.text, encoding="utf-8", newline="")
            os.replace(temporary, workflow)
            configuration = {
                "answers": {key: configuration_answers[key] for key in sorted(configuration_answers)},
                "generator_version": WIZARD_VERSION,
                "generated_files": {
                    WORKFLOW_TOML_RELATIVE_PATH: {"sha256": hash_file(workflow).sha256}
                },
            }
        expected_manifest = replace(
            manifest,
            files=files,
            skipped=tuple(sorted(skipped)),
            configuration=configuration,
        )
        expected_drift = compute_drift(repo_path, expected_manifest)
        if expected_drift.modified or expected_drift.missing:
            raise RuntimeError(
                f"doctor-style drift verification failed: modified={expected_drift.modified}, missing={expected_drift.missing}"
            )
        if bool(supplied.get("run_smoke", True)):
            smoke, smoke_ok = smoke_reverify(runner or SubprocessCommandRunner(), repo_path)
            if not smoke_ok:
                failures = "; ".join(item.detail for item in smoke if item.status == "fail")
                raise RuntimeError(f"smoke verification failed: {failures}")
        transaction.mark("verified")
        write_manifest(repo_path, expected_manifest)
        transaction.commit()
    except BaseException as exc:
        if transaction is not None and transaction.directory.exists():
            transaction.rollback()
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            plan=plan,
            result={"repaired": False, "rolled_back": True},
            messages=(f"repair failed and was rolled back: {exc}",),
        )
    return _emit(
        stream,
        as_json=as_json,
        status="ok",
        exit_code=EXIT_OK,
        plan=plan,
        result={"repaired": True, "no_op": False, "rolled_back": False},
    )


# END OF FILE
