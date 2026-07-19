#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_store.py
@brief Workflow support module for test_store.
@details Covers expected workflow behavior through focused pytest checks.
@author Eng. Dan Dumitru Pasare
@date 2026-07-18
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.store import repo_root_from


# TESTS


def test_repo_root_from_rejects_the_agentic_directory_itself(tmp_path: Path) -> None:
    """
    @brief      Resolving the workflow root to `.agentic` itself is refused.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18): before
                this guard, invoking the CLI with the process working
                directory mistakenly set to a project's own `.agentic` folder
                silently created a nested `.agentic/.agentic/...` copy instead
                of failing, because every write path
                (`write_current_run`/`init_graph`) calls
                `mkdir(parents=True, exist_ok=True)` unconditionally.
                Reproduced directly against `aegis.cli.main` before this fix.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    agentic_dir = tmp_path / ".agentic"
    agentic_dir.mkdir()

    with pytest.raises(SystemExit, match=r"Refusing to use.*\.agentic"):
        repo_root_from(agentic_dir)


def test_repo_root_from_rejects_a_path_nested_inside_agentic(tmp_path: Path) -> None:
    """
    @brief      Resolving the workflow root to a path under `.agentic` is refused.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Covers the deeper case observed in practice: a previously
                self-nested `.agentic/.agentic/...` copy, or any other path
                segment named `.agentic`, not just the immediate directory.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    nested = tmp_path / ".agentic" / "cli" / "src"
    nested.mkdir(parents=True)

    with pytest.raises(SystemExit, match=r"Refusing to use.*\.agentic"):
        repo_root_from(nested)


def test_repo_root_from_accepts_a_normal_project_root(tmp_path: Path) -> None:
    """
    @brief      A project root with no `.agentic` path segment resolves normally.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    project_root = tmp_path / "my-project"
    project_root.mkdir()

    assert repo_root_from(project_root) == project_root.resolve()


# END OF FILE
