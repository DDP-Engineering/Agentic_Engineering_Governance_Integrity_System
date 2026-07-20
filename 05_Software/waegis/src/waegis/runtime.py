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
@brief Atomic registration and resolution of the WAEGIS-managed Python runtime.
@details Application archives run from a pinned embedded CPython. On first use
         the archive registers that interpreter in the per-user WAEGIS home so
         deployed AEGIS wrappers and hook adapters can run without a system
         Python installation. The pointer is deliberately a one-line text file
         so PowerShell, POSIX shell, and Node adapters can all read it without
         needing Python or an additional JSON parser.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import os
from pathlib import Path

from .engine.journal import waegis_home

# CONSTANTS

RUNTIME_POINTER = "runtime-python"
PACKAGED_RUNTIME_ENV = "WAEGIS_PACKAGED_RUNTIME"


# DATA MODELS / TYPEDEFINITIONS


class RuntimeRegistrationError(Exception):
    """@brief A packaged or registered runtime path is invalid or cannot be persisted."""


# HELPER FUNCTIONS


def _validated_executable(value: str | os.PathLike[str]) -> Path:
    """@brief Resolve and validate a concrete Python executable path."""
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise RuntimeRegistrationError(f"Python runtime executable does not exist: {path}")
    return path


# EXPORTED FUNCTIONS / PUBLIC API


def runtime_pointer_path() -> Path:
    """@brief Return the per-user runtime pointer path without creating it."""
    return waegis_home() / RUNTIME_POINTER


def register_runtime(python_executable: str | os.PathLike[str]) -> Path:
    """
    @brief      Atomically register a WAEGIS-managed Python executable.
    @param[in]  python_executable Existing interpreter executable.
    @return     The resolved executable path written to the pointer.
    @exception  RuntimeRegistrationError If the path is invalid or cannot be written.
    """
    executable = _validated_executable(python_executable)
    pointer = runtime_pointer_path()
    temporary = pointer.with_name(pointer.name + ".tmp")
    try:
        pointer.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(f"{executable}\n", encoding="utf-8")
        os.replace(temporary, pointer)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeRegistrationError(f"cannot register WAEGIS runtime at {pointer}: {exc}") from exc
    return executable


def registered_runtime() -> Path | None:
    """@brief Read and validate the registered interpreter, or return ``None``."""
    pointer = runtime_pointer_path()
    try:
        value = pointer.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not value:
        return None
    try:
        return _validated_executable(value)
    except RuntimeRegistrationError:
        return None


def register_packaged_runtime() -> Path | None:
    """
    @brief Register the interpreter named by ``WAEGIS_PACKAGED_RUNTIME``.
    @return The registered path, or ``None`` for source/zipapp execution.
    @exception RuntimeRegistrationError If a packaged launcher supplied an invalid path.
    """
    value = os.environ.get(PACKAGED_RUNTIME_ENV)
    return register_runtime(value) if value else None


def python_probe_candidates() -> tuple[tuple[str, ...], ...]:
    """
    @brief Build the Python resolution order for WAEGIS prerequisite probes.
    @details Explicit ``AEGIS_PYTHON`` wins, followed by the registered WAEGIS
             runtime and finally supported system launchers. Duplicate concrete
             commands are removed while preserving order.
    """
    candidates: list[tuple[str, ...]] = []
    explicit = os.environ.get("AEGIS_PYTHON")
    if explicit:
        candidates.append((explicit,))
    registered = registered_runtime()
    if registered is not None:
        candidates.append((str(registered),))
    candidates.extend((("py", "-3"), ("python3",), ("python",)))
    unique: list[tuple[str, ...]] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


# END OF FILE
