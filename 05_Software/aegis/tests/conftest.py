#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file conftest.py
@brief Shared pytest fixtures for the AEGIS package test suite.
@details Provides the complete schema-version-3 unrestricted workflow
         configuration used consistently by configuration consumers.
@author Eng. Dan Dumitru Pasare
@date 2026-07-22
@version 0.4.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

# CONSTANTS

WORKFLOW_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "workflow_unrestricted.toml"

# SHARED FIXTURES


@pytest.fixture(scope="session")
def unrestricted_workflow_toml() -> str:
    """
    @brief      Return the complete unrestricted workflow TOML fixture.
    @return     UTF-8 TOML text conforming to the ratified schema version 3.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    return WORKFLOW_FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture()
def write_unrestricted_workflow_toml(
    unrestricted_workflow_toml: str,
) -> Callable[[Path], Path]:
    """
    @brief      Provide a factory that installs the shared workflow fixture.
    @param[in]  unrestricted_workflow_toml Complete schema-version-3 fixture.
    @return     Factory accepting a repository root and returning the written
                `.agentic/workflow.toml` path.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """

    def _write(repo_root: Path) -> Path:
        """
        @brief      Write the shared fixture below one repository root.
        @param[in]  repo_root Repository root that receives `.agentic`.
        @return     Path of the written workflow configuration.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-22
        @version    0.1.0
        """
        path = repo_root / ".agentic" / "workflow.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(unrestricted_workflow_toml, encoding="utf-8", newline="\n")
        return path

    return _write


@pytest.fixture(autouse=True)
def configured_temporary_repository(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    unrestricted_workflow_toml: str,
) -> None:
    """
    @brief      Give every temporary test repository a complete valid config.
    @param[in]  tmp_path Pytest temporary repository root.
    @param[in]  unrestricted_workflow_toml Shared schema-version-3 fixture.
    @return     None.
    @details    Tests exercising missing/invalid configuration remove or
                replace this file explicitly. This prevents unrelated tests
                from relying on the retired implicit Python configuration.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    if request.node.path.name in {"test_root_discovery.py", "test_store.py"}:
        return
    path = tmp_path / ".agentic" / "workflow.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(unrestricted_workflow_toml, encoding="utf-8", newline="\n")


@pytest.fixture()
def replace_workflow_toml(tmp_path: Path) -> Callable[[str, str], Path]:
    """
    @brief      Provide exact replacement edits over the complete shared config.
    @param[in]  tmp_path Temporary repository root.
    @return     Editor accepting one expected fragment and its replacement.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """

    def _replace(old: str, new: str) -> Path:
        """@brief Replace one unique fragment in the complete workflow TOML."""
        path = tmp_path / ".agentic" / "workflow.toml"
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise AssertionError(f"expected one workflow.toml fragment, found {text.count(old)}: {old!r}")
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
        return path

    return _replace


# END OF FILE
