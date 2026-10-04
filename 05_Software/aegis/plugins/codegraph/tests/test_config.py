#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_config.py
@brief CodeGraph settings and database-path confinement (REQ-SEC-68f1bb5d).
@details Settings come from the same `.agentic/aegis.toml` AEGIS reads. The
         database may only be a `NAME.sqlite` file directly inside the
         repository's `.agentic/knowledge/codegraph/` folder, checked after
         following links, because that folder is the one Git ignores and the
         writer lock protects.
"""

# IMPORTS

from __future__ import annotations

import os
from pathlib import Path

import pytest

from codegraph import config

# HELPER FUNCTIONS


def write_config(root: Path, body: str) -> Path:
    """@brief Write `.agentic/aegis.toml` under root and return its path."""
    path = root / ".agentic" / "aegis.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path

# TESTS


def test_default_and_alternative_database_names_are_accepted(tmp_path: Path):
    """REQ-SEC-68f1bb5d: NAME.sqlite directly inside the storage folder."""
    storage = tmp_path.resolve() / ".agentic" / "knowledge" / "codegraph"
    assert config.resolve_database(tmp_path, config.DEFAULT_DATABASE) == \
        storage / "codegraph.sqlite"
    assert config.resolve_database(
        tmp_path, ".agentic/knowledge/codegraph/alt-1.sqlite") == storage / "alt-1.sqlite"
    assert config.resolve_database(tmp_path, str(storage / "abs_ok.sqlite")) == \
        storage / "abs_ok.sqlite"


@pytest.mark.parametrize("value", [
    "src/index.sqlite",
    "../outside.sqlite",
    ".agentic/knowledge/codegraph/codegraph.sqlite-journal",
    ".agentic/knowledge/codegraph/codegraph.lock",
    ".agentic/knowledge/codegraph/sub/x.sqlite",
    ".agentic/knowledge/codegraph/bad name.sqlite",
    ".agentic/knowledge/codegraph/.hidden.sqlite",
    ".agentic/knowledge/codegraph/../codegraph.sqlite",
])
def test_database_outside_the_storage_rule_is_rejected(tmp_path: Path, value: str):
    """REQ-SEC-68f1bb5d: every other location or name is a one-line error."""
    with pytest.raises(config.ConfigError, match=r"\[codegraph\] database"):
        config.resolve_database(tmp_path, value)


def test_database_reached_through_a_linked_folder_is_rejected(tmp_path: Path):
    """REQ-SEC-68f1bb5d: a link may not move the storage folder elsewhere."""
    outside = tmp_path / "outside"
    outside.mkdir()
    knowledge = tmp_path / "repo" / ".agentic" / "knowledge"
    knowledge.mkdir(parents=True)
    try:
        os.symlink(outside, knowledge / "codegraph", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available on this machine")
    with pytest.raises(config.ConfigError, match=r"\[codegraph\] database"):
        config.resolve_database(tmp_path / "repo", config.DEFAULT_DATABASE)


def test_settings_read_layout_and_apply_defaults(tmp_path: Path):
    """REQ-SEC-68f1bb5d: settings come from aegis.toml with documented defaults."""
    write_config(tmp_path, '[layout]\nsource = ["src/"]\ntests = "tests/"\n'
                           '[codegraph]\nenabled = true\ninclude = ["tools/"]\n')
    settings = config.load(tmp_path)
    assert settings.source == ["src/"]
    assert settings.tests == ["tests/"]
    assert settings.include == ["tools/"]
    assert settings.exclude == []
    assert settings.include_untracked is True
    assert settings.index_tests is True
    assert settings.max_file_bytes == 1048576
    assert settings.parse_timeout_seconds == 10
    assert settings.max_results == 20
    assert settings.max_output_bytes == 8192
    assert settings.database == (tmp_path.resolve() / ".agentic" / "knowledge"
                                 / "codegraph" / "codegraph.sqlite")


@pytest.mark.parametrize("body, key", [
    ('include = "src/"', "include"),
    ("index_tests = 1", "index_tests"),
    ("max_file_bytes = 0", "max_file_bytes"),
    ("parse_timeout_seconds = -1", "parse_timeout_seconds"),
    ("max_results = 500", "max_results"),
    ("max_output_bytes = 100", "max_output_bytes"),
    ('database = "src/x.sqlite"', "database"),
])
def test_invalid_settings_are_one_line_errors(tmp_path: Path, body: str, key: str):
    """REQ-SEC-68f1bb5d: a wrong type or range names the setting."""
    write_config(tmp_path, f"[codegraph]\n{body}\n")
    with pytest.raises(config.ConfigError, match=rf"\[codegraph\] {key}"):
        config.load(tmp_path)


def test_unparseable_configuration_is_a_config_error(tmp_path: Path):
    """REQ-SEC-68f1bb5d: invalid TOML fails before any database access."""
    write_config(tmp_path, "[codegraph\n")
    with pytest.raises(config.ConfigError, match="aegis.toml"):
        config.load(tmp_path)


def test_ingestion_digest_ignores_result_limits(tmp_path: Path):
    """REQ-SEC-68f1bb5d: only ingestion settings change the digest."""
    write_config(tmp_path, '[layout]\nsource = ["src/"]\n[codegraph]\nmax_results = 20\n')
    first = config.ingestion_digest(config.load(tmp_path))
    write_config(tmp_path, '[layout]\nsource = ["src/"]\n[codegraph]\nmax_results = 50\n')
    assert config.ingestion_digest(config.load(tmp_path)) == first
    write_config(tmp_path, '[layout]\nsource = ["src/"]\n[codegraph]\nexclude = ["src/gen/"]\n')
    assert config.ingestion_digest(config.load(tmp_path)) != first

# END OF FILE
