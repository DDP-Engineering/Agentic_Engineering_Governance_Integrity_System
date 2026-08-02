#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_quick_configuration.py
@brief Verify optional proportional quick-run configuration behavior.
@details Covers ship-open defaults, explicit advisory modes, positive
         thresholds, exact types, and closed-schema rejection.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from aegis.config import ConfigurationError, effective_config_dict, load_config

# HELPER FUNCTIONS


def _write(repo_root: Path, text: str) -> Path:
    """@brief Write one workflow configuration test document."""
    path = repo_root / ".agentic" / "workflow.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _error(repo_root: Path, code: str) -> ConfigurationError:
    """@brief Load an invalid document and return its typed error."""
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(repo_root)
    assert exc_info.value.code == code
    return exc_info.value


# TESTS


def test_quick_changed_paths_policy_defaults_when_table_is_absent(
    tmp_path: Path,
    write_unrestricted_workflow_toml: Callable[[Path], Path],
) -> None:
    """
    @brief Resolve the optional quick-run advisory to ship-open defaults.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    write_unrestricted_workflow_toml(tmp_path)

    config = load_config(tmp_path)

    assert config.quick_changed_paths.mode == "disabled"
    assert config.quick_changed_paths.max_paths == 10
    assert effective_config_dict(config)["quick"] == {
        "changed_paths": {
            "mode": "disabled",
            "active_rule_count": 0,
            "max_paths": 10,
        }
    }


@pytest.mark.parametrize(
    ("mode", "max_paths"),
    [("disabled", 7), ("advise", 4)],
)
def test_quick_changed_paths_policy_accepts_explicit_modes(
    tmp_path: Path,
    unrestricted_workflow_toml: str,
    mode: str,
    max_paths: int,
) -> None:
    """
    @brief Parse both explicit proportional-run advisory modes.
    @param[in] tmp_path Temporary repository root.
    @return None.
    """
    _write(
        tmp_path,
        unrestricted_workflow_toml
        + f'\n[quick.changed_paths]\nmode = "{mode}"\nmax_paths = {max_paths}\n',
    )

    config = load_config(tmp_path)

    assert config.quick_changed_paths.mode == mode
    assert config.quick_changed_paths.max_paths == max_paths


@pytest.mark.parametrize(
    ("policy", "code", "key_path"),
    [
        (
            'mode = "enforce"\nmax_paths = 10',
            "CONFIG-MODE-INVALID",
            "quick.changed_paths.mode",
        ),
        (
            'mode = "advise"\nmax_paths = 0',
            "CONFIG-RULE-INVALID",
            "quick.changed_paths.max_paths",
        ),
        (
            'mode = "advise"\nmax_paths = true',
            "CONFIG-TYPE-INVALID",
            "quick.changed_paths.max_paths",
        ),
        (
            'mode = "advise"',
            "CONFIG-KEY-MISSING",
            "quick.changed_paths.max_paths",
        ),
        (
            'mode = "advise"\nmax_paths = 10\nlegacy = true',
            "CONFIG-TYPE-INVALID",
            "quick.changed_paths.legacy",
        ),
    ],
)
def test_quick_changed_paths_policy_rejects_invalid_explicit_values(
    tmp_path: Path,
    unrestricted_workflow_toml: str,
    policy: str,
    code: str,
    key_path: str,
) -> None:
    """
    @brief Keep the optional quick-run policy closed and strictly typed.
    @param[in] tmp_path Temporary repository root.
    @param[in] policy Candidate changed-path policy body.
    @return None.
    """
    _write(
        tmp_path,
        unrestricted_workflow_toml + f"\n[quick.changed_paths]\n{policy}\n",
    )

    error = _error(tmp_path, code)

    assert error.key_path == key_path


# END OF FILE
