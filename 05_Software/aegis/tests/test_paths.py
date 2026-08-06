#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_paths.py
@brief Workflow support module for test_paths.
@details Covers expected workflow behavior through focused pytest checks.
@details OS-aware case sensitivity of `matches_pattern` covered as of 0.2.0
         (architecture-review follow-up).
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest

from aegis import paths as paths_module
from aegis.paths import (
    RepositoryPathError,
    matches_pattern,
    normalize_repository_path,
    relative_to_root,
    validate_glob,
)


def test_relative_path_inside_root(tmp_path: Path) -> None:
    """
    @brief      Handle test relative path inside root workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    assert relative_to_root("src/app.py", tmp_path) == "src/app.py"


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    """
    @brief      Handle test path escape is rejected workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    with pytest.raises(ValueError):
        relative_to_root(tmp_path.parent / "outside.txt", tmp_path)


def test_glob_write_zone_match(tmp_path: Path) -> None:
    """
    @brief      Handle test glob write zone match workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    rel = relative_to_root("tests/test_app.py", tmp_path)
    assert matches_pattern(rel, "tests/**")
    assert not matches_pattern(rel, "src/**")


def test_windows_style_pattern_normalization(tmp_path: Path) -> None:
    """
    @brief      Handle test windows style pattern normalization workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    assert matches_pattern(relative_to_root("src/app.py", tmp_path), "src\\**")


def test_matching_is_case_insensitive_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      On Windows, pattern matching is case-insensitive, matching
                that OS's own case-insensitive filesystem.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    monkeypatch.setattr(paths_module.os, "name", "nt")
    assert matches_pattern("Src/App.py", "src/**")
    assert matches_pattern("src/app.py", "SRC/**")


def test_matching_is_case_sensitive_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      On a non-Windows host (architecture-review follow-up,
                0.2.0), pattern matching is case-sensitive, matching the real,
                case-sensitive filesystem on Ubuntu/Linux.
    @param[in]  monkeypatch Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    monkeypatch.setattr(paths_module.os, "name", "posix")
    assert not matches_pattern("Src/App.py", "src/**")
    assert not matches_pattern("src/app.py", "SRC/**")
    assert matches_pattern("src/app.py", "src/**")


def test_normalize_repository_path_accepts_a_relative_path() -> None:
    """@brief Accept a repository-relative path and normalize its separators."""
    assert normalize_repository_path("src\\app.py") == "src/app.py"


def test_normalize_repository_path_rejects_root_escape() -> None:
    """@brief Reject a path that escapes the repository root via `..`."""
    with pytest.raises(RepositoryPathError) as excinfo:
        normalize_repository_path("../outside.txt")
    assert excinfo.value.reason == "escapes-root"


def test_normalize_repository_path_drops_interior_dot_segments() -> None:
    """
    @brief      Collapse `a/./b` to `a/b` and reduce a bare `.` to a rejection.
    @return     None.
    @details    Regression test (B6, 2026-08-04): the normalizer stripped only a
                *leading* `./` and collapsed repeated slashes, so
                `tests/./unit/test_auth.py` validated and persisted unchanged.
                Every later comparison against a Git-reported or
                `rglob`-derived path then failed to match, and the requirement
                linking to it was reported as having no covering test although
                the link existed - a wrong traceability result with no error
                anywhere. `_normalize_set` could not see the two spellings as
                the same selector either, so both could coexist in one record.
    @exception  None
    """
    assert (
        normalize_repository_path("tests/./unit/test_auth.py")
        == "tests/unit/test_auth.py"
    )
    for value in (".", "./", "././"):
        with pytest.raises(RepositoryPathError) as excinfo:
            normalize_repository_path(value)
        assert excinfo.value.reason == "escapes-root"


def test_normalize_repository_path_rejects_globs_unless_allowed() -> None:
    """@brief Reject glob metacharacters unless allow_glob=True is set."""
    with pytest.raises(RepositoryPathError) as excinfo:
        normalize_repository_path("src/*.py")
    assert excinfo.value.reason == "has-globs"
    assert normalize_repository_path("src/*.py", allow_glob=True) == "src/*.py"


def test_validate_glob_rejects_unbalanced_brackets() -> None:
    """@brief Reject a glob bracket expression that is unbalanced or nested."""
    with pytest.raises(RepositoryPathError) as excinfo:
        validate_glob("src/[abc.py")
    assert excinfo.value.reason == "unbalanced-glob"
    validate_glob("src/[abc]*.py")


# END OF FILE
