#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file repowise.py
@brief Public WAEGIS RepoWise status and synchronization command handlers.
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path
from typing import IO

from ..consent import ConfirmationAsker, ConsentDecision, mutation_consent
from ..io.envelope import EXIT_NEEDS_INPUT, EXIT_OK, EXIT_OPERATIONAL, EXIT_VALIDATION, write_envelope
from ..repowise import RepoWiseError, repowise_status, sync_repowise


# EXPORTED FUNCTIONS / PUBLIC API


def run_repowise_status(repo: Path, *, as_json: bool, stream: IO[str]) -> int:
    """
    @brief Run the read-only RepoWise status command.
    @param[in] repo Target repository.
    @param[in] as_json Emit one stable JSON envelope when true.
    @param[in] stream Output stream.
    @return Standard WAEGIS exit code.
    @exception None
    """
    try:
        result = repowise_status(repo)
    except RepoWiseError as exc:
        if as_json:
            return write_envelope(
                stream,
                "repowise status",
                status="failed",
                exit_code=EXIT_VALIDATION,
                messages=(str(exc),),
            )
        stream.write(f"error: {exc}\n")
        return EXIT_VALIDATION
    if as_json:
        return write_envelope(
            stream,
            "repowise status",
            status="ok",
            exit_code=EXIT_OK,
            result=result,
        )
    for key in (
        "configured",
        "source",
        "mode",
        "profile",
        "installed",
        "index",
        "artifact",
        "receipt",
        "next",
    ):
        if key in result:
            stream.write(f"{key}: {result[key] if result[key] is not None else 'none'}\n")
    return EXIT_OK


def run_repowise_sync(
    repo: Path,
    *,
    as_json: bool,
    stream: IO[str],
    yes: bool = False,
    asker: ConfirmationAsker | None = None,
) -> int:
    """
    @brief Run managed RepoWise synchronization and artifact validation.
    @param[in] repo Target repository.
    @param[in] as_json Emit one stable JSON envelope when true.
    @param[in] stream Output stream.
    @param[in] yes Explicit approval to skip interactive confirmation.
    @param[in] asker Interactive confirmation seam used when ``yes`` is false and
               ``as_json`` is false.
    @return Zero on success, one when consent is declined or requires interactive
            input, two on a RepoWise config/status error, or three on operational
            failure.
    @exception None
    """
    try:
        status_report = repowise_status(repo)
    except RepoWiseError as exc:
        if as_json:
            return write_envelope(
                stream, "repowise sync", status="failed", exit_code=EXIT_VALIDATION, messages=(str(exc),)
            )
        stream.write(f"error: {exc}\n")
        return EXIT_VALIDATION
    if status_report.get("current") is True:
        plan = {"repo": str(repo.resolve()), "action": "no-op"}
    else:
        plan = {"repo": str(repo.resolve()), "action": "synchronize-index"}
    consent = mutation_consent(
        mutation_planned=plan["action"] != "no-op",
        yes=yes,
        asker=None if as_json else asker,
        prompt="Synchronize the RepoWise index?",
    )
    if consent is not ConsentDecision.APPROVED:
        message = (
            "RepoWise synchronization was not approved"
            if consent is ConsentDecision.DECLINED
            else "RepoWise synchronization requires explicit --yes or an interactive approval"
        )
        if as_json:
            return write_envelope(
                stream,
                "repowise sync",
                status="needs-input",
                exit_code=EXIT_NEEDS_INPUT,
                plan=plan,
                messages=(message,),
            )
        stream.write(message + "\n")
        return EXIT_NEEDS_INPUT
    try:
        result = sync_repowise(repo, stream=None if as_json else stream)
    except RepoWiseError as exc:
        if as_json:
            return write_envelope(
                stream,
                "repowise sync",
                status="failed",
                exit_code=EXIT_VALIDATION,
                messages=(str(exc),),
            )
        stream.write(f"error: {exc}\n")
        return EXIT_VALIDATION
    exit_code = EXIT_OK if result.ok else EXIT_OPERATIONAL
    status = "ok" if result.ok else "error"
    if as_json:
        return write_envelope(
            stream,
            "repowise sync",
            status=status,
            exit_code=exit_code,
            result=result.to_dict(),
        )
    stream.write(f"status: {'ok' if result.ok else 'failed'}\n")
    stream.write(f"action: {result.action}\n")
    stream.write(f"profile: {result.profile}\n")
    stream.write(f"message: {result.message}\n")
    stream.write(f"log: {result.log or 'none'}\n")
    stream.write(f"resume: {result.resume_command or 'none'}\n")
    return exit_code


# END OF FILE
