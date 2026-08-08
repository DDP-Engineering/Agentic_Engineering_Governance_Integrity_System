#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file runtime.py
@brief Select and atomically register the interpreter used by deployed AEGIS.
@details Mutating commands call registration only after repository/consent/lock
         preconditions. Read-only, dry-run, and refused operations never write
         the per-user pointer.
"""

# IMPORTS

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .copier import write_bytes_atomic
from .runner import Runner


# DATA MODELS / TYPEDEFINITIONS


class RuntimeSelectionError(ValueError):
    """@brief Raised when no exact compatible AEGIS interpreter is available."""


# EXPORTED FUNCTIONS / PUBLIC API


def waegis_home() -> Path:
    """@brief Resolve the explicit or platform-standard per-user WAEGIS home."""
    explicit = os.environ.get("WAEGIS_HOME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return (base / "waegis").resolve()


def runtime_pointer() -> Path:
    """@brief Return the established interpreter pointer location."""
    return waegis_home() / "runtime-python"


def select_runtime(runner: Runner) -> Path:
    """@brief Select explicit, packaged, then executing compatible Python."""
    candidates = [os.environ.get("AEGIS_PYTHON"), os.environ.get("WAEGIS_PACKAGED_RUNTIME"), sys.executable]
    failures: list[str] = []
    for raw in candidates:
        if not raw:
            continue
        located = shutil.which(raw) if not Path(raw).is_absolute() else raw
        if not located:
            failures.append(f"not found: {raw}")
            continue
        path = Path(located).resolve()
        if not path.is_file():
            failures.append(f"not a file: {path}")
            continue
        try:
            result = runner.run(
                (str(path), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"),
                timeout=15,
            )
        except OSError as exc:
            failures.append(f"cannot execute {path}: {exc}")
            continue
        if result.returncode == 0:
            try:
                major, minor = (int(part) for part in result.stdout.strip().split(".", 1))
            except ValueError:
                major, minor = 0, 0
            if (major, minor) >= (3, 11):
                return path
        failures.append(f"incompatible interpreter: {path}")
    raise RuntimeSelectionError("no Python 3.11+ runtime is available for deployed AEGIS; " + "; ".join(failures))


def register_runtime(runner: Runner) -> Path:
    """@brief Atomically persist and activate the exact selected interpreter."""
    selected = select_runtime(runner)
    pointer = runtime_pointer()
    write_bytes_atomic(pointer, (str(selected) + "\n").encode("utf-8"))
    os.environ["AEGIS_PYTHON"] = str(selected)
    return selected


def pointer_health() -> tuple[str, str | None]:
    """@brief Inspect an existing runtime pointer without creating or changing it."""
    pointer = runtime_pointer()
    if not pointer.exists():
        return "absent", None
    try:
        value = pointer.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        return "invalid", str(exc)
    if not value:
        return "invalid", "pointer is empty"
    target = Path(value)
    if not target.is_absolute() or not target.is_file():
        return "invalid", value
    return "valid", str(target)


# END OF FILE
