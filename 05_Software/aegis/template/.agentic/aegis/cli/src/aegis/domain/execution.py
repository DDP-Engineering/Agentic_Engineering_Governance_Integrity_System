#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file execution.py @brief Define platform-neutral configured process values."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event


class CancellationToken:
    """@brief Provide a thread-safe operator cancellation seam."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        """@brief Request cancellation of the associated process group."""
        self._event.set()

    @property
    def cancelled(self) -> bool:
        """@return Whether cancellation has been requested."""
        return self._event.is_set()


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """@brief Describe one shell-free configured process invocation."""

    command: tuple[str, ...]
    working_directory: Path
    timeout_seconds: int


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """@brief Return one of the five exact operational outcomes."""

    outcome: str
    exit_status: int | None
    stdout: bytes
    stderr: bytes
    duration_seconds: float
    reason: str

    @property
    def engineering_conclusion(self) -> str:
        """@return Passed/failed only when a command completed."""
        return self.outcome if self.outcome in {"passed", "failed"} else "unknown"


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
