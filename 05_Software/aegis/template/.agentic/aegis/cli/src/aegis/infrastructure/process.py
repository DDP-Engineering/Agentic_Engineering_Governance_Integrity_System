#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    process.py
@brief   Execute one configured argument-array command and drain both pipes.
@details Isolates timeout/cancellation process-group cleanup per platform.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from typing import BinaryIO

from aegis.domain.execution import (
    CancellationToken,
    ExecutionRequest,
    ExecutionResult,
)


def _drain(stream: BinaryIO, chunks: list[bytes]) -> None:
    """@brief Drain one child pipe concurrently until EOF."""
    while True:
        chunk = stream.read(65536)
        if not chunk:
            return
        chunks.append(chunk)


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    """@brief Terminate only the configured command's process group."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            shell=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def execute_process(
    request: ExecutionRequest,
    *,
    cancellation: CancellationToken | None = None,
) -> ExecutionResult:
    """@brief Run one command with shell disabled and exact outcome semantics."""
    started = time.monotonic()
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            request.command,
            cwd=request.working_directory,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
    except OSError as error:
        return ExecutionResult(
            "launch_error",
            None,
            b"",
            str(error).encode("utf-8", "replace"),
            time.monotonic() - started,
            "The configured command could not be launched.",
        )
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    stdout_thread = threading.Thread(
        target=_drain, args=(process.stdout, stdout_chunks), daemon=True
    )
    stderr_thread = threading.Thread(
        target=_drain, args=(process.stderr, stderr_chunks), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()
    outcome: str | None = None
    deadline = (
        None if request.timeout_seconds == 0 else started + request.timeout_seconds
    )
    try:
        while process.poll() is None:
            if cancellation is not None and cancellation.cancelled:
                outcome = "cancelled"
                _terminate_group(process)
                break
            if deadline is not None and time.monotonic() >= deadline:
                outcome = "timed_out"
                _terminate_group(process)
                break
            time.sleep(0.02)
    except KeyboardInterrupt:
        outcome = "cancelled"
        _terminate_group(process)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        _terminate_group(process)
        process.wait(timeout=2)
    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)
    if outcome is None:
        outcome = "passed" if process.returncode == 0 else "failed"
    reason = {
        "passed": "The command completed successfully.",
        "failed": "The command completed with a failing exit status.",
        "timed_out": "The configured positive timeout elapsed.",
        "cancelled": "Cancellation was requested and the process group was ended.",
    }[outcome]
    return ExecutionResult(
        outcome,
        process.returncode,
        b"".join(stdout_chunks),
        b"".join(stderr_chunks),
        time.monotonic() - started,
        reason,
    )


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
