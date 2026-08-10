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
@file    discovery.py
@brief   Discover an installed AEGIS repository without home-directory state.
@details Walks upward but stops at the first Git worktree boundary.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

from aegis.ports.repository import InstalledRepository, RepositoryDiscoveryError

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------


def discover_repository(start: str | Path) -> InstalledRepository:
    """
    @brief Walk upward to an installed AEGIS Git repository.
    @param[in] start Explicit path or current working directory.
    @return The installed repository boundary.
    @exception RepositoryDiscoveryError The Git boundary lacks AEGIS config or
    no boundary exists.
    """
    candidate = Path(start).resolve()
    if candidate.is_file():
        candidate = candidate.parent

    while True:
        git_marker = candidate / ".git"
        config_path = candidate / ".agentic" / "config.toml"
        if git_marker.exists():
            if config_path.is_file():
                return InstalledRepository(candidate, config_path.resolve())
            raise RepositoryDiscoveryError(
                "The Git repository does not contain an AEGIS installation.",
                candidate,
            )

        parent = candidate.parent
        if parent == candidate:
            raise RepositoryDiscoveryError(
                "No installed AEGIS Git repository was found.",
                Path(start).resolve(),
            )
        candidate = parent


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
