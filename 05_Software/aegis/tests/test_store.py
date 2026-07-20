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
@details Updated 0.2.0 for upward root discovery: invoking the CLI from
         `.agentic` (or below it) now heals to the surrounding project root
         instead of exiting, so the former rejection tests assert the healed
         resolution and the `_reject_nested_agentic_root` safety net is
         covered directly. Broader discovery scenarios live in
         `test_root_discovery.py`.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.store import _reject_nested_agentic_root, repo_root_from


# TESTS


def test_repo_root_from_heals_the_agentic_directory_itself(tmp_path: Path) -> None:
    """
    @brief      Resolving from `.agentic` itself heals to the project root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Regression lineage: before the 0.3.0 guard, invoking the CLI
                with the working directory set to a project's own `.agentic`
                folder silently created a nested `.agentic/.agentic/...` copy;
                the guard then made this a hard `SystemExit`. Upward discovery
                improves it once more: the parent that contains `.agentic` is
                resolved as the root and the command simply works.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    agentic_dir = tmp_path / ".agentic"
    agentic_dir.mkdir()

    assert repo_root_from(agentic_dir) == tmp_path.resolve()


def test_repo_root_from_heals_a_path_nested_inside_agentic(tmp_path: Path) -> None:
    """
    @brief      Resolving from a path under `.agentic` heals to the project root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Covers the deeper case observed in practice: any path segment
                below `.agentic`, such as `.agentic/cli/src`, resolves upward
                to the directory that contains `.agentic` instead of exiting.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    nested = tmp_path / ".agentic" / "cli" / "src"
    nested.mkdir(parents=True)

    assert repo_root_from(nested) == tmp_path.resolve()


def test_reject_guard_still_refuses_agentic_roots_directly(tmp_path: Path) -> None:
    """
    @brief      The safety-net guard itself still rejects `.agentic` roots.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Discovery makes the guard unreachable for paths that exist on
                disk (the parent containing `.agentic` always wins first), but
                it remains the last line of defense for nonexistent-path
                fallbacks, so it is covered at unit level here.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    with pytest.raises(SystemExit, match=r"Refusing to use.*\.agentic"):
        _reject_nested_agentic_root(tmp_path / ".agentic")
    with pytest.raises(SystemExit, match=r"Refusing to use.*\.agentic"):
        _reject_nested_agentic_root(tmp_path / ".agentic" / "cli" / "src")


def test_repo_root_from_accepts_a_normal_project_root(tmp_path: Path) -> None:
    """
    @brief      A marked project root resolves to itself.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    The root carries a `.git` marker so the resolution is
                deterministic regardless of any repository markers above the
                pytest temp directory on the host machine.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    project_root = tmp_path / "my-project"
    (project_root / ".git").mkdir(parents=True)

    assert repo_root_from(project_root) == project_root.resolve()


# END OF FILE
