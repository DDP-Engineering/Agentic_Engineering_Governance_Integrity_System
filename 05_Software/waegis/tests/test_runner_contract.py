#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_runner_contract.py
@brief Tests argument-array-only subprocess execution.
@details Proves literal metacharacters are not interpreted through a shell and
         validates error/timeout boundaries.
"""

import sys

import pytest

from waegis.runner import CommandRunner


def test_runner_passes_literal_arguments_and_captures_streams() -> None:
    """@brief Subprocess arguments never receive shell interpretation."""
    result = CommandRunner().run(
        [sys.executable, "-c", "import sys; print(sys.argv[1]); print('err', file=sys.stderr)", "$(unsafe)"],
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout == "$(unsafe)\n"
    assert result.stderr == "err\n"


@pytest.mark.parametrize("args", [[], [""]])
def test_runner_rejects_missing_executable(args: list[str]) -> None:
    """@brief Invalid command arrays fail before subprocess creation."""
    with pytest.raises(ValueError):
        CommandRunner().run(args)


def test_runner_rejects_nonpositive_timeout() -> None:
    """@brief Every subprocess has a positive explicit timeout."""
    with pytest.raises(ValueError, match="positive"):
        CommandRunner().run([sys.executable, "-V"], timeout=0)


# END OF FILE
