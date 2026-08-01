#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_verification.py
@brief Shared WAEGIS smoke-verification contract tests.
@details Ensures successful JSON output has the stable AEGIS response envelope.
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest

from waegis.verification import smoke_reverify, wrapper_invocation

from _fake_command_runner import FakeCommandRunner, ok_result

# TESTS


@pytest.mark.parametrize(
    "status_json",
    (
        "[]",
        '{"error": "not a workflow response"}',
        '{"status": "ok"}',
    ),
)
def test_smoke_reverify_rejects_json_without_response_envelope(
    tmp_path: Path,
    status_json: str,
) -> None:
    """
    @brief Reject parseable JSON that is not an AEGIS response envelope.
    @param[in] tmp_path Temporary repository path.
    @param[in] status_json Parseable but structurally invalid status output.
    @return None.
    """
    runner = FakeCommandRunner(
        {
            wrapper_invocation(tmp_path, "--help"): ok_result(),
            wrapper_invocation(
                tmp_path,
                "run",
                "status",
                "--json",
            ): ok_result(stdout=status_json),
        }
    )

    findings, healthy = smoke_reverify(runner, tmp_path)

    assert healthy is False
    assert findings[-1].name == "verify.workflow-smoke"
    assert findings[-1].status == "fail"


def test_smoke_reverify_accepts_stable_response_envelope(tmp_path: Path) -> None:
    """
    @brief Accept a JSON object carrying all stable AEGIS response keys.
    @param[in] tmp_path Temporary repository path.
    @return None.
    """
    runner = FakeCommandRunner(
        {
            wrapper_invocation(tmp_path, "--help"): ok_result(),
            wrapper_invocation(
                tmp_path,
                "run",
                "status",
                "--json",
            ): ok_result(
                stdout=(
                    '{"status":"ok","stage":"intake","artifact":"",'
                    '"next":"aegis stage prepare"}'
                )
            ),
        }
    )

    findings, healthy = smoke_reverify(runner, tmp_path)

    assert healthy is True
    assert findings[-1].name == "verify.workflow-smoke"
    assert findings[-1].status == "ok"


# END OF FILE
