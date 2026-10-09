#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_cli.py
@brief The plugin command line: scope preview, protocol versions, views, paths.
@details Covers REQ-FUNC-29d6c038 (scope preview writes nothing),
         REQ-FUNC-569a1a97 (protocol version), the command-line part of
         REQ-UX-461978be (one JSON document, quiet standard error) and the
         command-line part of REQ-SEC-68f1bb5d (invalid database paths).
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import copy_plugin, make_repo, run_entry, run_json, tree_state

from codegraph import cli

# CONSTANTS

FILES = {"src/a.py": "def alpha():\n    return 1\n", "src/notes.md": "# notes\n",
         "src/big.py": "x = 1\n" * 40, "tests/test_a.py": "def test_alpha():\n    pass\n"}

# TESTS - scope preview (REQ-FUNC-29d6c038)


def test_scope_preview_reports_selection_and_writes_nothing(tmp_path: Path):
    """REQ-FUNC-29d6c038: totals, counts, skips and inventory; no file written."""
    root = make_repo(tmp_path / "repo", FILES, tests=("tests/",), source=("src/", "tests/"),
                     extra="max_file_bytes = 100", use_git=True)
    entry = copy_plugin(root / ".agentic" / "plugins" / "codegraph")
    before = tree_state(root)
    code, env = run_json(["scope", "--root", str(root)], entry=entry)
    assert (code, env["status"]) == (0, "ok")
    details = env["details"]
    assert details["inventory"] == "git"
    assert details["totals"]["files"] == 2
    assert details["by_role"] == {"source": 1, "test": 1}
    assert details["skipped"] == {"too-large": 1, "unsupported": 1}
    text = run_entry(["scope", "--root", str(root)], entry=entry).stdout
    assert "totals: bytes=" in text
    assert tree_state(root) == before
    assert not list(root.rglob("__pycache__"))


def test_scope_without_layout_is_unavailable(tmp_path: Path):
    """REQ-FUNC-29d6c038: a missing scope is reported, not scanned."""
    root = make_repo(tmp_path / "repo", FILES, source=())
    code, env = run_json(["scope", "--root", str(root)])
    assert (code, env["status"], env["reason"]) == (0, "unavailable", "scope_missing")


def test_index_without_layout_writes_nothing(tmp_path: Path):
    """REQ-FUNC-43a76b41: indexing a missing scope fails with the advice and no file."""
    root = make_repo(tmp_path / "repo", FILES, source=())
    before = tree_state(root)
    code, env = run_json(["index", "--root", str(root)])
    assert (code, env["status"], env["reason"]) == (1, "error", "scope_missing")
    assert "[layout]" in env["message"]
    assert tree_state(root) == before

# TESTS - command line (REQ-FUNC-b383069e)


@pytest.mark.parametrize("argv, target", [
    (["find", "--root", "r", "--json", "--", "-weird"], "-weird"),
    (["find", "--root", "r", "--text-envelope", "--limit", "5", "--", "Order"], "Order"),
    (["find", "Order", "--root", "r"], "Order"),
    (["status", "--root", "r", "--json"], None)])
def test_target_parses_the_same_on_every_python(argv: list[str], target):
    """REQ-FUNC-b383069e: a target after `--` is data on Python 3.11 through 3.14."""
    assert cli.parse_arguments(argv).target == target


@pytest.mark.parametrize("argv", [["find", "--root", "r", "--", "a", "b"],
                                  ["find", "a", "--root", "r", "--", "b"],
                                  ["file", "--root", "r", "--", "a.py", "b.py"],
                                  ["callers", "a1", "--root", "r", "--", "b2"]])
def test_more_than_one_target_is_a_usage_error(argv: list[str]):
    """REQ-FUNC-b383069e: one name or path, given once; IDs only after `--`."""
    with pytest.raises(SystemExit) as caught:
        cli.parse_arguments(argv)
    assert caught.value.code == 2


@pytest.mark.parametrize("operation", ["symbol", "callers", "refs"])
def test_id_operations_take_several_targets_after_the_marker(operation: str):
    """REQ-FUNC-40ac076a: every ID after `--` is kept, in order."""
    args = cli.parse_arguments([operation, "--root", "r", "--", "a1", "b2", "c3"])
    assert args.targets == ["a1", "b2", "c3"] and args.target == "a1"
    assert cli.parse_arguments([operation, "a1", "--root", "r"]).targets == ["a1"]
    assert cli.parse_arguments(["find", "--root", "r", "--", "x"]).targets == ["x"]

# TESTS - protocol version (REQ-FUNC-569a1a97)


@pytest.mark.parametrize("version, status", [("1", "ok"), ("0", "error"), ("2", "error")])
def test_requested_protocol_version_is_answered_or_refused(tmp_path: Path, version: str,
                                                           status: str):
    """REQ-FUNC-569a1a97: unsupported versions list the supported ones."""
    root = make_repo(tmp_path / "repo", FILES)
    run_json(["index", "--root", str(root)])
    code, env = run_json(["status", "--root", str(root), "--protocol", version])
    assert env["status"] == status and env["protocol"] == 1
    if status == "error":
        assert (code, env["reason"], env["details"]["supported"]) == (1, "protocol", [1])

# TESTS - views and quiet standard error (REQ-UX-461978be)


def test_queries_print_one_document_and_nothing_on_stderr(tmp_path: Path):
    """REQ-UX-461978be: progress belongs to indexing and standard error only."""
    root = make_repo(tmp_path / "repo", FILES)
    index = run_entry(["index", "--root", str(root), "--json"])
    assert index.returncode == 0 and "codegraph: extract" in index.stderr
    json.loads(index.stdout)
    for operation in (["status"], ["find", "--", "alpha"], ["check"]):
        done = run_entry([operation[0], "--root", str(root), "--json", *operation[1:]])
        assert done.stderr == "", operation
        json.loads(done.stdout)
        envelope = run_entry([operation[0], "--root", str(root), "--text-envelope",
                              *operation[1:]])
        view = json.loads(envelope.stdout)
        assert "text" in view and "results" not in view

# TESTS - database path (REQ-SEC-68f1bb5d)


@pytest.mark.parametrize("value", ["src/index.sqlite",
                                   ".agentic/knowledge/codegraph/codegraph.lock",
                                   ".agentic/knowledge/codegraph/sub/x.sqlite"])
def test_invalid_database_paths_are_refused_before_any_file(tmp_path: Path, value: str):
    """REQ-SEC-68f1bb5d: index and queries refuse; nothing is created."""
    root = make_repo(tmp_path / "repo", FILES)
    before = tree_state(root)
    for operation in (["index"], ["find", "--", "alpha"]):
        done = run_entry([operation[0], "--root", str(root), "--database", value,
                          *operation[1:]])
        assert done.returncode == 1
        assert done.stderr.startswith("error: [codegraph] database")
        assert done.stdout == ""
    assert tree_state(root) == before

# END OF FILE
