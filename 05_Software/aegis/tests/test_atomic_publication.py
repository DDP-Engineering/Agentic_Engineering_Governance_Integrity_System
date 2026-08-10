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
@file    test_atomic_publication.py
@brief   Verify canonical single-file atomic replacement behavior.
@details Covers the IP-01 source subset of PR-STATE-001 and TA-PUBLISH-001-003.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import subprocess
import sys
from pathlib import Path

import pytest
from aegis.infrastructure.publication import (
    PublicationCheckpoint,
    PublicationError,
    atomic_replace,
)

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

HARD_EXIT_SCRIPT = """
import os
import sys
from pathlib import Path

from aegis.infrastructure.publication import PublicationCheckpoint, atomic_replace

target = Path(sys.argv[1])
stop_at = PublicationCheckpoint(sys.argv[2])

def stop(observed):
    if observed is stop_at:
        os._exit(91)

atomic_replace(target, b"after\\n", checkpoint=stop)
"""

# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


def test_atomic_replace_publishes_exact_complete_bytes(tmp_path: Path) -> None:
    """@brief Verify a successful publication installs the complete new file."""
    target = tmp_path / "state.md"
    target.write_bytes(b"before\n")

    atomic_replace(target, b"after\n")

    assert target.read_bytes() == b"after\n"


def test_parent_preparation_failure_is_translated_without_claiming_target(
    tmp_path: Path,
) -> None:
    """@brief Verify preparation failures preserve the publication contract."""
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"not a directory")
    target = blocker / "state.md"

    with pytest.raises(PublicationError) as raised:
        atomic_replace(target, b"after\n")

    assert not target.exists()
    assert blocker.read_bytes() == b"not a directory"
    assert str(target) in str(raised.value)


@pytest.mark.parametrize(
    "checkpoint,expected",
    [
        (PublicationCheckpoint.TEMPORARY_FLUSHED, b"before\n"),
        (PublicationCheckpoint.TARGET_REPLACED, b"after\n"),
    ],
)
def test_interruption_exposes_only_before_or_after_state(
    tmp_path: Path,
    checkpoint: PublicationCheckpoint,
    expected: bytes,
) -> None:
    """@brief Inject interruption on both sides of the atomic decision point."""
    target = tmp_path / "state.md"
    target.write_bytes(b"before\n")

    def interrupt(observed: PublicationCheckpoint) -> None:
        if observed is checkpoint:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        atomic_replace(target, b"after\n", checkpoint=interrupt)

    assert target.read_bytes() == expected
    assert target.read_bytes() in {b"before\n", b"after\n"}


@pytest.mark.parametrize(
    "checkpoint,expected",
    [
        (PublicationCheckpoint.TEMPORARY_FLUSHED, b"before\n"),
        (PublicationCheckpoint.TARGET_REPLACED, b"after\n"),
    ],
)
def test_hard_process_exit_exposes_only_before_or_after_state(
    tmp_path: Path,
    checkpoint: PublicationCheckpoint,
    expected: bytes,
) -> None:
    """@brief Kill a worker at each publication side without running cleanup."""
    target = tmp_path / "state.md"
    target.write_bytes(b"before\n")

    completed = subprocess.run(
        [sys.executable, "-c", HARD_EXIT_SCRIPT, str(target), checkpoint.value],
        check=False,
    )

    assert completed.returncode == 91
    assert target.read_bytes() == expected
    assert target.read_bytes() in {b"before\n", b"after\n"}


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
