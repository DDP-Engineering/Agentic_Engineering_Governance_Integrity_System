#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    publication.py
@brief   Publish one complete file through atomic sibling replacement.
@details Flushes prepared bytes before the atomic replacement decision point.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


class PublicationCheckpoint(StrEnum):
    """@brief Name observable fault-injection boundaries around replacement."""

    TEMPORARY_FLUSHED = "temporary_flushed"
    TARGET_REPLACED = "target_replaced"


class PublicationError(Exception):
    """@brief Report a failure to prepare or atomically replace one file."""


# -----------------------------------------------------------------------------
# LOCAL HELPERS
# -----------------------------------------------------------------------------


def _flush_directory(directory: Path) -> None:
    """@brief Request the strongest supported directory flush."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------


def atomic_replace(
    target: str | Path,
    content: bytes,
    *,
    checkpoint: Callable[[PublicationCheckpoint], None] | None = None,
) -> None:
    """
    @brief Atomically create or replace one authoritative file.
    @param[in] target Destination file path.
    @param[in] content Exact complete bytes to publish.
    @param[in] checkpoint Optional fault-injection observer.
    @exception PublicationError Preparation or atomic replacement failed.
    """
    target_path = Path(target)
    parent = target_path.parent
    temporary_path: Path | None = None

    try:
        parent.mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            dir=parent,
        )
        temporary_path = Path(raw_path)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        if checkpoint is not None:
            checkpoint(PublicationCheckpoint.TEMPORARY_FLUSHED)

        os.replace(temporary_path, target_path)
        temporary_path = None

        if checkpoint is not None:
            checkpoint(PublicationCheckpoint.TARGET_REPLACED)
        _flush_directory(parent)
    except (KeyboardInterrupt, SystemExit):
        raise
    except OSError as error:
        raise PublicationError(
            f"Atomic publication failed for {target_path}."
        ) from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
