#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_upgrade_classifier.py
@brief Complete pure three-way upgrade classification table.
@details Covers additions, removals, convergence, local edits, upstream edits,
         true conflicts, and non-managed preservation.
"""

import pytest

from waegis.classify import ConflictDecision, UpgradeAction, classify_upgrade, normalize_conflict_decision
from waegis.ownership import Disposition, initial_disposition


@pytest.mark.parametrize(
    ("baseline", "current", "payload", "expected"),
    [
        (None, None, None, UpgradeAction.UNCHANGED),
        (None, None, "new", UpgradeAction.ADD),
        (None, "new", "new", UpgradeAction.CONVERGED),
        (None, "local", "new", UpgradeAction.CONFLICT),
        ("old", "old", "old", UpgradeAction.UNCHANGED),
        ("old", "old", "new", UpgradeAction.REPLACE),
        ("old", "new", "new", UpgradeAction.CONVERGED),
        ("old", "local", "old", UpgradeAction.PRESERVE_LOCAL),
        ("old", "local", "new", UpgradeAction.CONFLICT),
        ("old", "old", None, UpgradeAction.REMOVE),
        ("old", "local", None, UpgradeAction.PRESERVE_LOCAL),
        ("old", None, None, UpgradeAction.CONVERGED),
        ("old", None, "old", UpgradeAction.PRESERVE_LOCAL),
        ("old", None, "new", UpgradeAction.CONFLICT),
    ],
)
def test_three_way_classifier_rows(
    baseline: str | None,
    current: str | None,
    payload: str | None,
    expected: UpgradeAction,
) -> None:
    """@brief Phase 1 ports every classifier decision as a pure contract."""
    assert classify_upgrade(baseline, current, payload) is expected


@pytest.mark.parametrize("disposition", list(Disposition)[1:])
def test_nonmanaged_dispositions_always_preserve(disposition: Disposition) -> None:
    """@brief R4 refuses maintenance authority regardless of hash topology."""
    assert classify_upgrade("old", "old", "new", disposition) is UpgradeAction.PRESERVE_LOCAL


def test_conflict_decisions_use_path_specific_v2_vocabulary() -> None:
    """@brief R1 normalizes only the documented sidecar spelling."""
    assert normalize_conflict_decision("keep-local") is ConflictDecision.KEEP_LOCAL
    assert normalize_conflict_decision("take-payload") is ConflictDecision.TAKE_PAYLOAD
    assert normalize_conflict_decision("write-sidecar") is ConflictDecision.SIDECAR
    with pytest.raises(ValueError):
        normalize_conflict_decision("take-all")


def test_new_project_data_paths_default_to_seeded_not_managed() -> None:
    """@brief R4 new payload files below project-owned trees never gain maintenance authority."""
    assert initial_disposition(".agentic/requirements/REQ-001.md") is Disposition.SEEDED
    assert initial_disposition(".agentic/knowledge/components/payment.md") is Disposition.SEEDED
    assert initial_disposition(".agentic/reports/adoption/result.md") is Disposition.SEEDED
    assert initial_disposition(".agentic/requirements/spec_template.md") is Disposition.MANAGED


# END OF FILE
