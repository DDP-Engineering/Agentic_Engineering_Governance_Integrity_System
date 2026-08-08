#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_ownership_contract.py
@brief Tests initial ownership and maintenance authority.
@details Protects generated and project-seeded paths from repair/upgrade writes.
"""

import pytest

from waegis.ownership import Disposition, initial_disposition, permits_maintenance


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".agentic/workflow.toml", Disposition.GENERATED),
        ("CHANGELOG.md", Disposition.SEEDED),
        (".agentic/components.toml", Disposition.SEEDED),
        (".agentic/requirements/coverage_waivers.txt", Disposition.SEEDED),
        (".agentic/requirements/security/.gitkeep", Disposition.SEEDED),
        (".agentic/cli/src/aegis/cli.py", Disposition.MANAGED),
    ],
)
def test_initial_dispositions(path: str, expected: Disposition) -> None:
    """@brief R4 assigns explicit authority to representative path families."""
    assert initial_disposition(path) is expected


def test_only_managed_paths_permit_automatic_maintenance() -> None:
    """@brief R4 keeps every project-owned disposition outside repair authority."""
    assert permits_maintenance(Disposition.MANAGED)
    assert all(not permits_maintenance(value) for value in Disposition if value is not Disposition.MANAGED)


# END OF FILE
