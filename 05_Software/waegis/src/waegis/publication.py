#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file publication.py
@brief Shared existing-repository publication, validation, and exact rollback.
@details Configure, repair, and upgrade precompute immutable bytes and an exact
         Git recovery set, then use this manifest-last publication boundary.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, TextIO

from .gitsafety import RecoveryPlan, acquire_lock, execute_recovery, require_clean, require_planned_head
from .manifest import MANIFEST_PATH, InstallManifest, contained_destination, serialize_manifest
from .runner import Runner
from .runtime import register_runtime


# CONSTANTS

NO_ACTIVE_RUN_MARKER = "RUN-POINTER-MISSING"
STATUS_KEYS = frozenset({"status", "stage", "artifact", "next"})
SMOKE_TIMEOUT = 120.0


# DATA MODELS / TYPEDEFINITIONS


class PublicationError(RuntimeError):
    """@brief Raised when publication, validation, or rollback fails."""


@dataclass(frozen=True, slots=True)
class PublicationPlan:
    """@brief Complete consent-ready update for one existing repository."""

    command: str
    target: Path
    writes: Mapping[str, bytes]
    removals: tuple[str, ...]
    recovery: RecoveryPlan
    manifest: InstallManifest

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "target": str(self.target),
            "writes": sorted(self.writes),
            "removals": list(self.removals),
            "recovery": self.recovery.to_dict(),
            "manifest": {
                "payload_version": self.manifest.payload_version,
                "payload_digest": self.manifest.payload_digest,
                "mode": self.manifest.mode,
            },
        }


# HELPER FUNCTIONS


def wrapper_invocation(target: Path, *args: str) -> tuple[str, ...]:
    if os.name == "nt":
        return (
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(target / ".agentic" / "tools" / "run.ps1"),
            *args,
        )
    return ("bash", str(target / ".agentic" / "tools" / "run.sh"), *args)


def _json_envelope(result: object, context: str) -> None:
    try:
        value = json.loads(str(result))
    except json.JSONDecodeError as exc:
        raise PublicationError(f"{context} returned invalid JSON") from exc
    if not isinstance(value, dict) or not STATUS_KEYS.issubset(value):
        raise PublicationError(f"{context} returned an unexpected envelope")


def _emit_recovery(plan: PublicationPlan, stream: TextIO, *, as_json: bool) -> None:
    record = plan.recovery.to_dict()
    if as_json:
        stream.write(json.dumps({"waegis_recovery": record}, sort_keys=True) + "\n")
    else:
        stream.write("Recovery plan (emitted before mutation):\n")
        for command in plan.recovery.rendered():
            stream.write(f"  {command}\n")
    stream.flush()


# EXPORTED FUNCTIONS / PUBLIC API


def validate_aegis(target: Path, runner: Runner, runtime_python: str | Path = sys.executable) -> None:
    """@brief Validate the actual installed wrapper, config, and status contract."""
    environment = {"AEGIS_PYTHON": str(runtime_python)}
    help_result = runner.run(wrapper_invocation(target, "--help"), cwd=target, timeout=SMOKE_TIMEOUT, env=environment)
    if help_result.returncode != 0:
        detail = help_result.stderr.strip() or help_result.stdout.strip()
        raise PublicationError(f"AEGIS wrapper --help failed: {detail}")
    config = runner.run(
        wrapper_invocation(target, "config", "validate", "--json"),
        cwd=target,
        timeout=SMOKE_TIMEOUT,
        env=environment,
    )
    if config.returncode != 0:
        detail = config.stderr.strip() or config.stdout.strip()
        raise PublicationError(f"AEGIS config validate failed: {detail}")
    _json_envelope(config.stdout, "AEGIS config validate")
    status = runner.run(
        wrapper_invocation(target, "run", "status", "--json"),
        cwd=target,
        timeout=SMOKE_TIMEOUT,
        env=environment,
    )
    combined = f"{status.stdout}\n{status.stderr}"
    if status.returncode == 0:
        _json_envelope(status.stdout, "AEGIS run status")
    elif NO_ACTIVE_RUN_MARKER not in combined:
        raise PublicationError(f"AEGIS run status failed incoherently: {combined.strip()}")


def apply_publication(
    plan: PublicationPlan,
    runner: Runner,
    recovery_stream: TextIO,
    *,
    as_json: bool,
    break_lock: bool = False,
) -> None:
    """@brief Apply one consented update and publish its manifest last."""
    lock = None
    stage_root: Path | None = None
    recovery_emitted = False
    try:
        require_clean(runner, plan.target)
        lock = acquire_lock(runner, plan.target, plan.command, break_lock=break_lock)
        require_clean(runner, plan.target)
        require_planned_head(runner, plan.recovery)
        _emit_recovery(plan, recovery_stream, as_json=as_json)
        recovery_emitted = True
        runtime_python = register_runtime(runner)
        stage_root = Path(tempfile.mkdtemp(prefix=".waegis-stage-", dir=plan.target.parent))
        for path, data in plan.writes.items():
            staged = stage_root.joinpath(*path.split("/"))
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(data)
        staged_manifest = stage_root.joinpath(*MANIFEST_PATH.split("/"))
        staged_manifest.parent.mkdir(parents=True, exist_ok=True)
        staged_manifest.write_bytes(serialize_manifest(plan.manifest))
        for path in plan.writes:
            destination = contained_destination(plan.target, path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage_root.joinpath(*path.split("/")), destination)
        for path in plan.removals:
            destination = contained_destination(plan.target, path)
            if destination.exists():
                destination.unlink()
        validate_aegis(plan.target, runner, runtime_python)
        destination = contained_destination(plan.target, MANIFEST_PATH)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_manifest, destination)
    except BaseException as exc:
        rollback_error: Exception | None = None
        if recovery_emitted:
            try:
                execute_recovery(runner, plan.recovery)
            except Exception as rollback_exc:  # pragma: no cover - fault-injected separately
                rollback_error = rollback_exc
        if isinstance(exc, KeyboardInterrupt):
            if rollback_error:
                raise PublicationError(f"interrupted; automatic recovery failed: {rollback_error}") from exc
            raise
        detail = str(exc)
        if rollback_error:
            detail += f"; automatic recovery failed: {rollback_error}"
        raise PublicationError(detail) from exc
    finally:
        if lock is not None:
            lock.release()
        if stage_root is not None:
            shutil.rmtree(stage_root, ignore_errors=True)


# END OF FILE
