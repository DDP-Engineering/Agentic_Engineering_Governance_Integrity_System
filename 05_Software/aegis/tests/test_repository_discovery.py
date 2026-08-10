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
@file    test_repository_discovery.py
@brief   Verify installed-repository discovery and Git boundary handling.
@details Covers the IP-01 repository subset of TA-REPO-001 and TA-REPO-002.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from pathlib import Path

import pytest
from aegis.infrastructure.discovery import (
    RepositoryDiscoveryError,
    discover_repository,
)

# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


def test_discovery_walks_up_to_installed_git_repository(tmp_path: Path) -> None:
    """@brief Verify nested invocation resolves the installed root."""
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / ".agentic").mkdir()
    (root / ".agentic" / "config.toml").write_bytes(b"schema = 1\n")
    nested = root / "src" / "package"
    nested.mkdir(parents=True)

    discovered = discover_repository(nested)

    assert discovered.root == root.resolve()
    assert discovered.config_path == (root / ".agentic" / "config.toml").resolve()


def test_discovery_accepts_worktree_git_file(tmp_path: Path) -> None:
    """@brief Verify linked Git worktrees are valid repository boundaries."""
    root = tmp_path / "worktree"
    (root / ".agentic").mkdir(parents=True)
    (root / ".agentic" / "config.toml").write_bytes(b"schema = 1\n")
    (root / ".git").write_text("gitdir: ../metadata\n", encoding="utf-8")

    assert discover_repository(root).root == root.resolve()


def test_discovery_stops_at_uninstalled_git_boundary(tmp_path: Path) -> None:
    """@brief Verify a child repository cannot inherit a parent's install."""
    parent = tmp_path / "parent"
    (parent / ".git").mkdir(parents=True)
    (parent / ".agentic").mkdir()
    (parent / ".agentic" / "config.toml").write_bytes(b"schema = 1\n")
    child = parent / "child"
    (child / ".git").mkdir(parents=True)
    nested = child / "src"
    nested.mkdir()

    with pytest.raises(RepositoryDiscoveryError) as error:
        discover_repository(nested)

    assert error.value.code == "repository_error"
    assert error.value.path == child.resolve()


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
