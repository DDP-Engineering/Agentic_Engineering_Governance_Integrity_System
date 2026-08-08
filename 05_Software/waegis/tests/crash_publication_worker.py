#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file crash_publication_worker.py
@brief Pause a real WAEGIS process at one deterministic publication boundary.
@details Builds a minimal existing-repository install plan so the acceptance
         matrix isolates publication and recovery mechanics. Real-payload
         validation is covered independently by install and upgrade tests.
"""

# IMPORTS

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


# CONSTANTS

PACKAGE_ROOT = Path(__file__).parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"


# HELPER FUNCTIONS


def _pause(signal: Path) -> None:
    signal.write_text("ready\n", encoding="utf-8")
    time.sleep(120)


def _suffix(path: object) -> str:
    return Path(path).resolve().as_posix()


# EXPORTED FUNCTIONS / PUBLIC API


def main(arguments: list[str]) -> int:
    """@brief Patch one boundary, then apply the same real install publication code."""
    if len(arguments) not in {3, 4}:
        raise SystemExit("usage: crash_publication_worker.py POINT SIGNAL REPO [--break-lock]")
    point = arguments[0]
    signal = Path(arguments[1])
    repository = Path(arguments[2]).resolve()
    break_lock = arguments[3:] == ["--break-lock"]
    sys.path.insert(0, str(SOURCE_ROOT))

    import waegis.install as install  # noqa: PLC0415
    from waegis.gitsafety import build_recovery_plan  # noqa: PLC0415
    from waegis.ownership import Disposition  # noqa: PLC0415
    from waegis.runner import CommandRunner  # noqa: PLC0415

    runner = CommandRunner()
    operations = (
        install.FileOperation("tracked.txt", "write", Disposition.MANAGED, b"updated\n"),
        install.FileOperation("new.txt", "write", Disposition.MANAGED, b"new\n"),
        install.FileOperation(
            ".agentic/workflow.toml",
            "write",
            Disposition.GENERATED,
            b"schema_version = 3\n",
        ),
    )
    recovery = build_recovery_plan(
        runner,
        repository,
        ("tracked.txt", "new.txt", ".agentic/workflow.toml", ".agentic/install-manifest.json"),
    )
    plan = install.InstallPlan(
        "adopt",
        repository,
        "3.0.0",
        "0" * 64,
        {},
        {},
        operations,
        recovery,
        False,
    )
    install.register_runtime = lambda _runner: None
    install.validate_aegis = lambda _target, _runner, _runtime_python=None: None

    if point == "after-recovery-before-write":
        original_emit = install._emit_recovery

        def emit_then_pause(*args, **kwargs):  # type: ignore[no-untyped-def]
            original_emit(*args, **kwargs)
            _pause(signal)

        install._emit_recovery = emit_then_pause
    elif point == "after-validation-before-manifest":
        install.validate_aegis = lambda _target, _runner, _runtime_python=None: _pause(signal)
    elif point != "complete":
        original_replace = os.replace

        def replace_at_boundary(source, destination):  # type: ignore[no-untyped-def]
            destination_text = _suffix(destination)
            if point == "during-manifest-replace" and destination_text.endswith(
                "/.agentic/install-manifest.json"
            ):
                _pause(signal)
            original_replace(source, destination)
            if point == "mid-copy-overwrite-and-add" and destination_text.endswith("/new.txt"):
                _pause(signal)
            if point == "after-workflow-before-validation" and destination_text.endswith(
                "/.agentic/workflow.toml"
            ):
                _pause(signal)
            if point == "after-manifest-before-lock-cleanup" and destination_text.endswith(
                "/.agentic/install-manifest.json"
            ):
                _pause(signal)

        os.replace = replace_at_boundary
    install.apply_install(plan, runner, sys.stderr, as_json=True, break_lock=break_lock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


# END OF FILE
