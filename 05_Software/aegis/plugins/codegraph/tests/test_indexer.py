#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_indexer.py
@brief Index publication, incremental updates and cross-file resolution labels.
@details Covers REQ-FUNC-7e74dacf (incremental updates), REQ-REL-1eeb1914
         (atomic generations with fresh snapshot IDs), the cross-file part of
         REQ-FUNC-7432a8a2 (labels from binding evidence) and the replacement
         part of REQ-FUNC-45ed74a5 (earlier facts of a broken file disappear).
"""

# IMPORTS

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from conftest import make_repo, run_entry, run_json

from codegraph import config, indexer, store

# CONSTANTS

MODULE_A = '''\
def save(order):
    return order


def helper():
    return 1


class Repo:
    def store(self, item):
        return item

    def keep(self, item):
        return self.store(item)
'''

MODULE_B = '''\
import os
import pkg.a
from pkg.a import save
from pkg.util import *


def run(order):
    save(order)
    pkg.a.helper()
    os.path.join("x")
    helper()
    return order
'''

# HELPER FUNCTIONS


def index(root: Path, **kwargs) -> dict:
    """@brief Run indexing in-process for a repository."""
    return indexer.run_index(config.load(root), **kwargs)


def rows(root: Path, sql: str, *params) -> list:
    """@brief Query the database read-only."""
    conn, state = store.open_reader(config.load(root).database)
    assert state == "ready", state
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def symbol_id(root: Path, qualified: str) -> str:
    """@brief ID of one symbol by qualified name."""
    return rows(root, "SELECT id FROM symbols WHERE qualified_name = ?", qualified)[0][0]


def labels(root: Path, path: str) -> dict:
    """@brief (kind, spelling, line) -> (label, target) for one file."""
    found = rows(root, "SELECT r.kind, r.spelling, r.line, r.label, r.target_id FROM refs r "
                       "JOIN files f ON f.id = r.file_id WHERE f.path = ?", path)
    return {(kind, spelling, line): (label, target) for kind, spelling, line, label, target in found}

# TESTS - publication (REQ-REL-1eeb1914)


def test_first_index_creates_an_owned_database_with_one_generation(tmp_path: Path):
    """REQ-REL-1eeb1914: a complete first generation with a 32-hex snapshot."""
    root = make_repo(tmp_path / "repo", {"src/pkg/a.py": MODULE_A})
    result = index(root)
    assert result["files"]["indexed"] == 1
    database = config.load(root).database
    assert store.header_kind(database) == "codegraph"
    conn, state = store.open_reader(database)
    meta = store.read_meta(conn)
    conn.close()
    assert state == "ready" and meta["generation"] == 1 and len(meta["snapshot"]) == 32


def test_every_run_and_rebuild_gets_a_new_snapshot(tmp_path: Path):
    """REQ-REL-1eeb1914: snapshot IDs are never reused."""
    root = make_repo(tmp_path / "repo", {"src/pkg/a.py": MODULE_A})
    first = index(root)["meta"]["snapshot"]
    second = index(root)["meta"]["snapshot"]
    config.load(root).database.unlink()
    third = index(root)["meta"]["snapshot"]
    fourth = index(root, rebuild=True)["meta"]["snapshot"]
    assert len({first, second, third, fourth}) == 4


def test_killed_run_leaves_the_previous_generation(tmp_path: Path):
    """REQ-REL-1eeb1914: an interrupted run publishes nothing."""
    root = make_repo(tmp_path / "repo", {"src/pkg/a.py": MODULE_A})
    _code, first = run_json(["index", "--root", str(root)])
    (root / "src" / "pkg" / "a.py").write_text(MODULE_A + "\n\ndef added():\n    pass\n",
                                               encoding="utf-8")
    for point in ("before_publish", "after_insert"):
        done = run_entry(["index", "--root", str(root), "--json"],
                         env={"CODEGRAPH_TEST_KILL_AT": point})
        assert done.returncode != 0, point
        database = config.load(root).database
        recovered = sqlite3.connect(database)
        snapshot = recovered.execute("SELECT value FROM meta WHERE key='snapshot'").fetchone()[0]
        assert recovered.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        names = {name for (name,) in recovered.execute("SELECT name FROM symbols")}
        recovered.close()
        assert snapshot == first["snapshot"], point
        assert "added" not in names, point

# TESTS - incremental updates (REQ-FUNC-7e74dacf)


def test_incremental_update_reuses_unchanged_files_and_applies_every_change(tmp_path: Path):
    """REQ-FUNC-7e74dacf: add, equal-size edit, delete, rename, exclude, manifest."""
    root = make_repo(tmp_path / "repo", {
        "src/pkg/a.py": "def alpha():\n    pass\n", "src/pkg/b.py": "def bravo():\n    pass\n",
        "src/pkg/c.py": "def charl():\n    pass\n", "src/pkg/d.py": "def delta():\n    pass\n",
        "src/pkg/e.py": "def echo1():\n    pass\n", "src/pkg/f.py": "def fox():\n    pass\n",
        "pyproject.toml": "[project]\nname = 'x'\n"})
    assert index(root)["files"]["indexed"] == 6
    (root / "src/pkg/b.py").write_text("def bravX():\n    pass\n", encoding="utf-8")
    (root / "src/pkg/c.py").unlink()
    (root / "src/pkg/d.py").rename(root / "src/pkg/d2.py")
    (root / "src/pkg/g.py").write_text("def golf():\n    pass\n", encoding="utf-8")
    cfg = root / ".agentic" / "aegis.toml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + 'exclude = ["src/pkg/e.py"]\n',
                   encoding="utf-8")
    before = rows(root, "SELECT sha256 FROM manifests WHERE path = 'pyproject.toml'")
    (root / "pyproject.toml").write_text("[project]\nname = 'y'\n", encoding="utf-8")
    result = index(root)
    names = {name for (name,) in rows(root, "SELECT name FROM symbols WHERE kind = 'function'")}
    assert names == {"alpha", "bravX", "delta", "fox", "golf"}
    assert result["files"]["reused"] == 2
    assert result["files"]["indexed"] == 3
    paths = {path for (path,) in rows(root, "SELECT path FROM files")}
    assert paths == {"src/pkg/a.py", "src/pkg/b.py", "src/pkg/d2.py", "src/pkg/f.py",
                     "src/pkg/g.py"}
    dangling = rows(root, "SELECT count(*) FROM symbols s LEFT JOIN files f ON f.id = s.file_id "
                          "WHERE f.id IS NULL")[0][0]
    assert dangling == 0
    after = rows(root, "SELECT sha256 FROM manifests WHERE path = 'pyproject.toml'")
    assert before and after and before != after

def test_reused_files_take_the_new_role(tmp_path: Path):
    """REQ-FUNC-7e74dacf: a layout change updates roles without re-extracting."""
    files = {"src/a.py": "def a():\n    pass\n", "tests/test_a.py": "def test_a():\n    pass\n"}
    root = make_repo(tmp_path / "repo", files, source=("src/", "tests/"))
    run_json(["index", "--root", str(root)])
    config_path = root / ".agentic" / "aegis.toml"
    config_path.write_text(config_path.read_text(encoding="utf-8").replace(
        "tests = []", 'tests = ["tests/"]'), encoding="utf-8")
    _code, env = run_json(["index", "--root", str(root)])
    assert env["details"]["files"]["reused"] == 2
    _code, env = run_json(["file", "--root", str(root), "--", "tests/test_a.py"])
    assert env["details"]["role"] == "test"
    _code, env = run_json(["check", "--root", str(root)])
    assert env["freshness"] == "current"


def test_failed_files_are_extracted_again(tmp_path: Path):
    """REQ-FUNC-7e74dacf: a file that failed is retried even when it has not changed."""
    root = make_repo(tmp_path / "repo", {"src/slow.py": "def slow():\n    pass\n"},
                     extra="parse_timeout_seconds = 1")
    done = run_entry(["index", "--root", str(root), "--json"],
                     env={"CODEGRAPH_TEST_SLOW_FILE": "src/slow.py"})
    assert json.loads(done.stdout)["details"]["files"]["failed"] == 1
    _code, env = run_json(["index", "--root", str(root)])
    assert (env["details"]["files"]["indexed"], env["details"]["files"]["failed"]) == (1, 0)

# TESTS - cross-file labels (REQ-FUNC-7432a8a2)


def test_cross_file_labels_follow_binding_evidence(tmp_path: Path):
    """REQ-FUNC-7432a8a2: confirmed links only with syntax or lexical evidence."""
    root = make_repo(tmp_path / "repo", {"src/pkg/__init__.py": "", "src/pkg/a.py": MODULE_A,
                                         "src/pkg/b.py": MODULE_B,
                                         "src/other/c.py": "def helper():\n    pass\n"},
                     extra='python_import_roots = ["src/"]')
    index(root)
    found = labels(root, "src/pkg/b.py")
    assert found[("import", "pkg.a", 2)] == ("direct-syntax", symbol_id(root, "pkg.a"))
    assert found[("import", "pkg.a.save", 3)] == ("direct-syntax", symbol_id(root, "pkg.a.save"))
    assert found[("import", "os", 1)] == ("external", None)
    assert found[("import", "pkg.util.*", 4)] == ("unresolved", None)
    assert found[("call", "save", 8)] == ("lexical-binding", symbol_id(root, "pkg.a.save"))
    assert found[("call", "pkg.a.helper", 9)] == ("lexical-binding", symbol_id(root, "pkg.a.helper"))
    assert found[("call", "os.path.join", 10)] == ("external", None)
    assert found[("call", "helper", 11)] == ("candidate", None)
    a_labels = labels(root, "src/pkg/a.py")
    assert a_labels[("call", "self.store", 14)] == ("candidate", None)
    candidates = rows(root, "SELECT c.symbol_id, c.rank FROM candidates c JOIN refs r "
                            "ON r.rowid = c.ref_rowid WHERE r.spelling = 'self.store' "
                            "ORDER BY c.rank")
    assert candidates[0][0] == symbol_id(root, "pkg.a.Repo.store")
    helper_candidates = rows(root, "SELECT c.symbol_id FROM candidates c JOIN refs r "
                                   "ON r.rowid = c.ref_rowid WHERE r.spelling = 'helper' "
                                   "ORDER BY c.rank")
    assert [sid for (sid,) in helper_candidates][:2] == [symbol_id(root, "pkg.a.helper"),
                                                         symbol_id(root, "other.c.helper")]
    assert rows(root, "SELECT count(*) FROM refs WHERE label = 'candidate' "
                      "AND target_id IS NOT NULL")[0][0] == 0


def test_single_name_match_elsewhere_stays_a_candidate(tmp_path: Path):
    """REQ-FUNC-7432a8a2: one match by name is still not a confirmed link."""
    root = make_repo(tmp_path / "repo", {"src/x.py": "def unique_name():\n    pass\n",
                                         "src/y.py": "unique_name()\n"})
    index(root)
    assert labels(root, "src/y.py")[("call", "unique_name", 1)] == ("candidate", None)

# TESTS - syntax errors replace earlier facts (REQ-FUNC-45ed74a5)


def test_broken_file_no_longer_returns_its_earlier_facts(tmp_path: Path):
    """REQ-FUNC-45ed74a5: old facts never masquerade as current."""
    root = make_repo(tmp_path / "repo", {"src/m.py": "def good():\n    pass\n\ndef gone():\n    pass\n"})
    index(root)
    (root / "src/m.py").write_text("def good():\n    pass\n\ndef gone(:\n    pass\n",
                                   encoding="utf-8")
    result = index(root)
    assert result["files"]["partial"] == 1
    names = {name for (name,) in rows(root, "SELECT name FROM symbols WHERE kind='function'")}
    assert names == {"good"}
    assert rows(root, "SELECT status, reason FROM files") == [("partial", "syntax")]

# END OF FILE
