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
@author Eng. Dan Dumitru Pasare
@date 2026-07-30
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest

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
    @version 0.1.0
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


# END OF FILE
