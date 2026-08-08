#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_evidence_forms.py
@brief Manual-evidence form contract tests.
@details Covers stage preparation preconditions before evidence mutation.
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest

from aegis._form_io import load_evidence_form
from aegis.evidence_forms import apply_evidence_form
from aegis.models import Graph, Intent
from aegis.stage_forms import StageOperationError
from aegis.store import save_graph

# TESTS


def test_apply_evidence_requires_prepared_current_stage(tmp_path: Path) -> None:
    """
    @brief Reject manual evidence before the current stage is prepared.
    @param[in] tmp_path Configured temporary repository.
    @return None.
    """
    graph = Graph(
        run_id="fix-20260730T120000Z-1234abcd",
        stage="implementation",
        intent=Intent(id="I-1", kind="fix", statement="Repair evidence guard"),
    )
    save_graph(tmp_path, graph)

    with pytest.raises(
        StageOperationError,
        match="prepare the current stage before applying manual evidence",
    ):
        apply_evidence_form(tmp_path, graph)

    assert graph.evidence == []


def test_apply_evidence_rejects_completed_run(tmp_path: Path) -> None:
    """@brief Manual evidence cannot mutate a terminal run graph."""
    graph = Graph(
        run_id="fix-20260730T120000Z-1234abcd",
        stage="delivery",
        intent=Intent(id="I-1", kind="fix", statement="Closed run"),
        complete=True,
    )
    save_graph(tmp_path, graph)

    with pytest.raises(StageOperationError, match="manual evidence cannot be applied"):
        apply_evidence_form(tmp_path, graph)


def test_invalid_utf8_evidence_form_is_typed(tmp_path: Path) -> None:
    """@brief Editor encoding mistakes become normal stage-operation errors."""
    path = tmp_path / "evidence.toml"
    path.write_bytes(b'summary = "\x81"\n')

    with pytest.raises(StageOperationError, match="cannot load evidence form"):
        load_evidence_form(path)


# END OF FILE
