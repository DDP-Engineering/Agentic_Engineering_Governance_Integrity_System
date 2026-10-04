#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_queries.py
@brief Read-only CodeGraph queries through the real entry point.
@details Covers REQ-FUNC-af6434a9 (queries never write), REQ-FUNC-a8ece064
         (status), REQ-FUNC-41815b22 (freshness check), REQ-FUNC-ab604fdb
         (find), REQ-FUNC-a603d692 (file outline), REQ-FUNC-d6ef4d32 (symbol
         neighborhood), REQ-FUNC-359c2a92 (callers), REQ-FUNC-81588d5e
         (refs), REQ-FUNC-ff30861f (cited-file checks), REQ-FUNC-e8436251
         (ID prefixes), REQ-FUNC-ff8000c4 (paging) and REQ-NFR-17c50caa
         (budgets on real query output).
"""

# IMPORTS

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import copy_plugin, make_repo, run_entry, run_json, tree_state

from codegraph import config, natives, queries, scope, store

# CONSTANTS

ORDERS = '''\
class OrderRepository:
    def save(self, order):
        return self.write(order)

    def write(self, order):
        return order


def save_order(order):
    repo = OrderRepository()
    return repo.save(order)
'''

SERVICE = '''\
from shop.orders import save_order
import shop.orders


def checkout(order):
    save_order(order)
    shop.orders.save_order(order)
    return order
'''

ELSEWHERE = '''\
def save_order(item):
    return item
'''

CALLER = '''\
def unrelated():
    save_order(1)
'''

COUNTER = '''\
counter = 0
counter = counter + 1
print(counter)


def other():
    counter = 5
    return counter
'''

FILES = {"src/shop/__init__.py": "", "src/shop/orders.py": ORDERS,
         "src/shop/service.py": SERVICE, "src/legacy/elsewhere.py": ELSEWHERE,
         "src/legacy/caller.py": CALLER,
         "src/shop/counter.py": COUNTER, "tests/test_orders.py":
         "from shop.orders import save_order\n\n\ndef test_save():\n    save_order(1)\n"}
EXTRA = 'python_import_roots = ["src/"]'

# HELPER FUNCTIONS


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """@brief An indexed repository shared by the query tests."""
    root = make_repo(tmp_path / "repo", FILES, tests=("tests/",), source=("src/", "tests/"),
                     extra=EXTRA)
    code, env = run_json(["index", "--root", str(root)])
    assert code == 0, env
    return root


def query(root: Path, *args: str) -> dict:
    """@brief Run one query and return its JSON envelope."""
    _code, env = run_json([args[0], "--root", str(root), *args[1:]])
    return env


def find_id(root: Path, qualified: str) -> str:
    """@brief Full ID of one symbol by qualified name."""
    env = query(root, "find", "--limit", "50", "--", qualified)
    matches = [r["id"] for r in env["results"] if r["qualified_name"] == qualified]
    assert matches, (qualified, env)
    return matches[0]

# TESTS - read-only (REQ-FUNC-af6434a9)


def test_queries_change_nothing_in_any_database_state(tmp_path: Path):
    """REQ-FUNC-af6434a9: no file, folder, journal or bytecode is created."""
    root = make_repo(tmp_path / "repo", FILES, extra=EXTRA)
    entry = copy_plugin(root / ".agentic" / "plugins" / "codegraph")
    operations = [["status"], ["check"], ["find", "--", "save"],
                  ["file", "--", "src/shop/orders.py"], ["symbol", "--", "0000000000"],
                  ["callers", "--", "0000000000"], ["refs", "--", "0000000000"]]

    def all_queries(label: str) -> None:
        before = tree_state(root)
        for operation in operations:
            for flags in (("-I", "-B", "-X", "utf8"), ()):
                run_entry([operation[0], "--root", str(root), "--json", *operation[1:]],
                          entry=entry, flags=flags)
        assert tree_state(root) == before, label

    all_queries("missing")
    run_entry(["index", "--root", str(root), "--json"], entry=entry)
    all_queries("ready")
    (root / "src" / "shop" / "orders.py").write_text(ORDERS + "\n# edit\n", encoding="utf-8")
    all_queries("stale")
    database = config.load(root).database
    lock = sqlite3.connect(database, isolation_level=None)
    lock.execute("BEGIN EXCLUSIVE")
    all_queries("busy")
    lock.execute("ROLLBACK")
    lock.close()
    raw = database.read_bytes()
    database.write_bytes(b"not a database at all, but long enough" * 10)
    all_queries("incompatible")
    database.write_bytes(raw)
    assert not list(root.rglob("__pycache__"))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX folder permissions")
def test_queries_work_in_a_read_only_storage_folder(repo: Path):
    """REQ-FUNC-af6434a9: a readable database in a non-writable folder serves reads."""
    storage = config.load(repo).database.parent
    os.chmod(storage, 0o555)
    try:
        env = query(repo, "find", "--", "save_order")
        assert env["status"] == "ok" and env["results"]
    finally:
        os.chmod(storage, 0o755)

# TESTS - status (REQ-FUNC-a8ece064)


def test_status_reports_state_coverage_and_git_diagnostics(tmp_path: Path, monkeypatch):
    """REQ-FUNC-a8ece064: availability, counts, capability, Git view; no source read."""
    missing_root = make_repo(tmp_path / "missing", FILES, extra=EXTRA)
    missing = query(missing_root, "status")
    assert (missing["status"], missing["index"]) == ("unavailable", "missing")
    assert missing["details"]["database_folder"]["ignored"] is None
    root = make_repo(tmp_path / "git", FILES, extra=EXTRA, use_git=True)
    run_json(["index", "--root", str(root)])
    env = query(root, "status")
    assert (env["status"], env["index"], env["freshness"]) == ("ok", "ready", "not_fully_checked")
    details = env["details"]
    assert details["available"] is True
    assert details["scope"]["complete"] == 6 and details["languages"] == ["python"]
    assert details["database_folder"] == {"ignored": True, "tracked": []}
    assert env["indexing_supported"] is True and env["generation"] == 1
    opened: list[str] = []
    real_read = Path.read_bytes
    real_open = Path.open

    def spy_read(path, *args, **kwargs):
        opened.append(str(path))
        return real_read(path, *args, **kwargs)

    def spy_open(path, *args, **kwargs):
        opened.append(str(path))
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_bytes", spy_read)
    monkeypatch.setattr(Path, "open", spy_open)
    args = SimpleNamespace(limit=None, max_bytes=None, page=None, target=None, deadline=None)
    env = queries.answer("status", config.load(root), args, natives.capability(), "json")
    assert env["status"] == "ok"
    assert not [p for p in opened if p.replace("\\", "/").endswith(".py")]


def test_status_sees_storage_git_would_record(tmp_path: Path):
    """REQ-FUNC-a8ece064: not-ignored and tracked storage are visible."""
    root = make_repo(tmp_path / "repo", FILES, extra=EXTRA, use_git=True, ignore_storage=False)
    env = query(root, "status")
    assert env["details"]["database_folder"]["ignored"] is False

# TESTS - check (REQ-FUNC-41815b22)


def test_check_reports_current_then_each_kind_of_staleness(repo: Path):
    """REQ-FUNC-41815b22: equal-size edits, additions, deletions, manifests, config."""
    assert query(repo, "check")["freshness"] == "current"
    cfg = repo / ".agentic" / "aegis.toml"
    original = cfg.read_text(encoding="utf-8")
    cfg.write_text(original + "max_results = 7\n", encoding="utf-8")
    assert query(repo, "check")["freshness"] == "current"
    cfg.write_text(original, encoding="utf-8")
    orders = repo / "src" / "shop" / "orders.py"
    orders.write_text(ORDERS.replace("save", "sav3"), encoding="utf-8")
    env = query(repo, "check")
    assert (env["freshness"], env["details"]["changed"]) == ("stale", ["src/shop/orders.py"])
    orders.write_text(ORDERS, encoding="utf-8")
    (repo / "src" / "shop" / "new.py").write_text("x = 1\n", encoding="utf-8")
    assert query(repo, "check")["details"]["added"] == ["src/shop/new.py"]
    (repo / "src" / "shop" / "new.py").unlink()
    (repo / "src" / "shop" / "counter.py").unlink()
    assert query(repo, "check")["details"]["deleted"] == ["src/shop/counter.py"]
    (repo / "src" / "shop" / "counter.py").write_text(COUNTER, encoding="utf-8")
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    assert query(repo, "check")["details"]["manifests_changed"] == ["pyproject.toml"]
    (repo / "pyproject.toml").unlink()
    cfg.write_text(original + 'exclude = ["src/legacy/"]\n', encoding="utf-8")
    env = query(repo, "check")
    assert env["freshness"] == "stale" and env["details"]["config_changed"] is True


def test_check_during_a_source_edit_is_unknown(repo: Path):
    """REQ-FUNC-41815b22: a source changing mid-check is never reported current."""
    _code, env = run_json(["check", "--root", str(repo)],
                          env={"CODEGRAPH_TEST_EDIT_DURING_CHECK": "src/shop/orders.py"})
    assert env["freshness"] == "unknown"

# TESTS - find (REQ-FUNC-ab604fdb)


def test_find_ranks_exact_then_prefix_then_words_deterministically(repo: Path):
    """REQ-FUNC-ab604fdb: equally ranked duplicates are all returned."""
    env = query(repo, "find", "--", "save_order")
    names = [(r["qualified_name"], r["role"]) for r in env["results"]]
    assert names[:2] == [("legacy.elsewhere.save_order", "source"),
                         ("shop.orders.save_order", "source")]
    assert query(repo, "find", "--", "save_order")["results"] == env["results"]
    exact = query(repo, "find", "--", "shop.orders.OrderRepository.save")
    assert exact["results"][0]["qualified_name"] == "shop.orders.OrderRepository.save"
    words = query(repo, "find", "--", "order repository")
    assert words["results"][0]["qualified_name"] == "shop.orders.OrderRepository"
    assert all(len(r["id"]) == 32 and r["start"]["line"] >= 1 for r in env["results"])


def test_find_without_match_is_ok_and_empty(repo: Path):
    """REQ-FUNC-ab604fdb: no match is a successful empty answer."""
    env = query(repo, "find", "--", "nothing_like_this")
    assert (env["status"], env["results"]) == ("ok", [])

# TESTS - file (REQ-FUNC-a603d692)


def test_file_outline_in_source_order_with_nesting(repo: Path):
    """REQ-FUNC-a603d692: classes, methods and functions with depth."""
    env = query(repo, "file", "--", "src/shop/orders.py")
    outline = [(r["qualified_name"], r["depth"]) for r in env["results"]]
    assert outline == [("shop.orders", 0), ("shop.orders.OrderRepository", 1),
                       ("shop.orders.OrderRepository.save", 2),
                       ("shop.orders.OrderRepository.write", 2),
                       ("shop.orders.save_order", 1)]
    assert env["details"]["extraction"] == "complete"
    assert query(repo, "file", "--", ".\\src\\shop\\orders.py")["results"] == env["results"]
    assert query(repo, "file", "--", "src/shop/missing.py")["status"] == "not_found"

# TESTS - symbol, callers, refs (REQ-FUNC-d6ef4d32, REQ-FUNC-359c2a92, REQ-FUNC-81588d5e)


def test_symbol_shows_its_labelled_neighborhood(repo: Path):
    """REQ-FUNC-d6ef4d32: callers, callees and references once each."""
    env = query(repo, "symbol", "--", find_id(repo, "shop.orders.save_order"))
    assert env["details"]["symbol"]["qualified_name"] == "shop.orders.save_order"
    relations = {(r["relation"], r["spelling"], r["label"]) for r in env["results"]}
    assert ("callee", "OrderRepository", "lexical-binding") in relations
    assert ("callee", "repo.save", "candidate") in relations
    assert ("caller", "save_order", "lexical-binding") in relations
    assert ("caller", "save_order", "candidate") in relations
    small = query(repo, "symbol", "--limit", "1", "--", find_id(repo, "shop.orders.save_order"))
    assert len(small["results"]) == 1 and small["has_more"] is True


def test_callers_lists_linked_and_candidate_callers_separately(repo: Path):
    """REQ-FUNC-359c2a92: same-name calls elsewhere stay candidates."""
    env = query(repo, "callers", "--", find_id(repo, "shop.orders.save_order"))
    linked = sorted((r["path"], r["line"], r["label"]) for r in env["results"])
    assert linked == [("src/shop/service.py", 6, "lexical-binding"),
                      ("src/shop/service.py", 7, "lexical-binding"),
                      ("tests/test_orders.py", 5, "lexical-binding")]
    candidates = [(r["path"], r["line"], r["label"]) for r in env["details"]["candidates"]]
    assert candidates == [("src/legacy/caller.py", 2, "candidate")]


def test_refs_lists_reads_writes_and_arguments_but_not_shadows(repo: Path):
    """REQ-FUNC-81588d5e: a shadowing local of the same name is excluded."""
    env = query(repo, "refs", "--", find_id(repo, "shop.counter.counter"))
    found = sorted((r["kind"], r["line"]) for r in env["results"])
    assert found == [("read", 2), ("read", 3), ("write", 2)]

# TESTS - cited files (REQ-FUNC-ff30861f)


def test_changed_cited_files_are_marked_stale(repo: Path):
    """REQ-FUNC-ff30861f: unchanged citations stay current."""
    (repo / "src" / "legacy" / "elsewhere.py").write_text(ELSEWHERE + "\n# edit\n",
                                                          encoding="utf-8")
    env = query(repo, "find", "--", "save_order")
    citations = {r["path"]: r["citation"] for r in env["results"]}
    assert citations["src/legacy/elsewhere.py"] == "stale"
    assert citations["src/shop/orders.py"] == "current"
    assert env["freshness"] == "not_fully_checked"
    text = run_entry(["find", "--root", str(repo), "--", "save_order"]).stdout
    assert "(changed since indexing)" in text

# TESTS - ID prefixes (REQ-FUNC-e8436251)


def make_twins(repo: Path) -> list[str]:
    """@brief Give two indexed functions IDs that share an 11-character prefix."""
    database = config.load(repo).database
    conn = sqlite3.connect(database)
    ids = [row[0] for row in conn.execute(
        "SELECT id FROM symbols WHERE kind IN ('function','method') ORDER BY id LIMIT 2")]
    twins = ["abcdef01234" + "0" * 21, "abcdef01234" + "f" * 21]
    for old, new in zip(ids, twins):
        conn.execute("UPDATE symbols SET id = ? WHERE id = ?", (new, old))
    conn.commit()
    conn.close()
    return twins


def test_prefixes_resolve_against_the_whole_index(repo: Path):
    """REQ-FUNC-e8436251: ambiguous prefixes list choices; unknown is not_found."""
    twins = make_twins(repo)
    ambiguous = query(repo, "symbol", "--", "abcdef0123")
    assert ambiguous["status"] == "ambiguous"
    assert sorted(r["id"] for r in ambiguous["results"]) == sorted(twins)
    assert query(repo, "symbol", "--", "abcdef012340")["status"] == "ok"
    assert query(repo, "symbol", "--", "0123456789ab")["status"] == "not_found"
    assert query(repo, "callers", "--", "abcdef01234f")["status"] == "ok"
    text = run_entry(["find", "--root", str(repo), "--", "save"]).stdout
    assert all(len(part.split("=", 1)[1]) >= 10 for part in text.split()
               if part.startswith("id="))

# TESTS - paging and budgets (REQ-FUNC-ff8000c4, REQ-NFR-17c50caa)


def fan_out_repo(tmp_path: Path) -> Path:
    """@brief A repository with 60 similarly named handlers."""
    body = "".join(f"def handler_{n:02d}():\n    pass\n\n\n" for n in range(60))
    root = make_repo(tmp_path / "fan", {"src/many.py": body})
    run_json(["index", "--root", str(root)])
    return root


def test_paging_returns_every_record_once_and_binds_the_request(tmp_path: Path):
    """REQ-FUNC-ff8000c4: expired after re-indexing; another request is an error."""
    root = fan_out_repo(tmp_path)
    seen, token = [], None
    while True:
        args = ["find", "--limit", "20", "--", "handler"]
        if token:
            args = ["find", "--limit", "20", "--page", token, "--", "handler"]
        env = query(root, *args)
        seen += [r["name"] for r in env["results"]]
        token = env["next_page"]
        if not env["has_more"]:
            break
    assert sorted(seen) == [f"handler_{n:02d}" for n in range(60)] and len(seen) == 60
    first = query(root, "find", "--limit", "20", "--", "handler")["next_page"]
    other = query(root, "find", "--limit", "20", "--page", first, "--", "handle")
    assert (other["status"], other["reason"]) == ("error", "page_token_mismatch")
    run_json(["index", "--rebuild", "--root", str(root)])
    stale = query(root, "find", "--limit", "20", "--page", first, "--", "handler")
    assert stale["status"] == "expired"


def test_default_and_enlarged_query_budgets(tmp_path: Path):
    """REQ-NFR-17c50caa: 20 records and 8 KiB by default; 32 KiB at most."""
    root = fan_out_repo(tmp_path)
    done = run_entry(["find", "--root", str(root), "--json", "--", "handler"])
    import json
    env = json.loads(done.stdout)
    assert len(env["results"]) <= 20 and len(done.stdout.encode("utf-8")) <= 8192 + 1
    assert env["has_more"] is True
    big = run_entry(["find", "--root", str(root), "--json", "--limit", "200",
                     "--max-bytes", "100000", "--", "handler"])
    assert len(big.stdout.encode("utf-8")) <= 32768 + 1
    text = run_entry(["find", "--root", str(root), "--max-bytes", "1024", "--", "handler"])
    assert len(text.stdout.encode("utf-8")) <= 1024 + 1

# TESTS - review fixes: paging, budgets, rendering, isolation (REQ-FUNC-ff8000c4,
# REQ-NFR-17c50caa, REQ-FUNC-e8436251, REQ-FUNC-41815b22, REQ-FUNC-a8ece064, REQ-FUNC-a603d692)

FAN = "def target():\n    pass\n\n\n" + "".join(
    f"def c{n:02d}():\n    target()\n\n\n" for n in range(12))
OTHER = "def use(obj):\n" + "".join("    obj.target()\n" for _ in range(8))


def page_all(root: Path, *query_args: str, key=None, limit: str = "5") -> list:
    """@brief Follow page tokens to the end; fails if paging does not terminate."""
    seen, token = [], None
    for _ in range(100):
        page = ["--page", token] if token else []
        env = query(root, query_args[0], "--limit", limit, *page, *query_args[1:])
        seen += key(env)
        if not env["has_more"]:
            return seen
        token = env["next_page"]
    pytest.fail("paging did not end")


def test_callers_page_through_linked_callers_then_candidates_once(tmp_path: Path):
    """REQ-FUNC-ff8000c4: every caller and candidate appears once, and paging ends."""
    root = make_repo(tmp_path / "repo", {"src/fan.py": FAN, "src/other.py": OTHER})
    run_json(["index", "--root", str(root)])
    sid = find_id(root, "src.fan.target")

    def records(env: dict) -> list:
        return ([("linked", r["path"], r["line"]) for r in env["results"]]
                + [("candidate", r["path"], r["line"])
                   for r in env["details"].get("candidates", [])])
    seen = page_all(root, "callers", "--", sid, key=records)
    assert len(seen) == len(set(seen)) == 20
    assert sum(1 for kind, *_rest in seen if kind == "candidate") == 8
    refs = page_all(root, "refs", "--", sid,
                    key=lambda env: [(r["path"], r["line"]) for r in env["results"]])
    assert len(refs) == len(set(refs)) == 12


def test_ambiguous_choices_render_as_symbols_within_the_budget(repo: Path):
    """REQ-FUNC-e8436251: text names each choice with its ID; budgets still apply."""
    make_twins(repo)
    text = run_entry(["symbol", "--root", str(repo), "--", "abcdef0123"]).stdout
    assert text.count("id=abcdef01234") == 2 and "from=" not in text
    small = run_entry(["symbol", "--root", str(repo), "--json", "--max-bytes", "512",
                       "--", "abcdef0123"])
    env = json.loads(small.stdout)
    assert len(env["results"]) == 1 and env["has_more"] is True


@pytest.mark.parametrize("option, value", [("--limit", "0"), ("--limit", "201"),
                                           ("--max-bytes", "100")])
def test_out_of_range_budgets_are_invalid_requests(repo: Path, option: str, value: str):
    """REQ-NFR-17c50caa: budgets outside 1-200 records or below 512 bytes are refused."""
    env = query(repo, "find", option, value, "--", "save")
    assert (env["status"], env["reason"], env["index"]) == ("error", "invalid_request", "ready")


def test_a_budget_smaller_than_one_record_still_makes_progress(tmp_path: Path):
    """REQ-NFR-17c50caa: each page carries at least one record, so paging always ends."""
    body = "".join(f"def handler_{n:02d}():\n    pass\n\n\n" for n in range(30))
    root = make_repo(tmp_path / "fan", {"src/many.py": body}, extra="max_output_bytes = 512")
    run_json(["index", "--root", str(root)])
    seen = page_all(root, "find", "--", "handler", limit="20",
                    key=lambda env: [r["name"] for r in env["results"]] or ["<empty page>"])
    assert sorted(seen) == [f"handler_{n:02d}" for n in range(30)]


def test_check_treats_a_vanished_file_as_unknown(repo: Path, monkeypatch):
    """REQ-FUNC-41815b22: a file removed during the check makes freshness unknown."""
    real = scope.select

    def select_then_remove(settings, *args, **kwargs):
        selection = real(settings, *args, **kwargs)
        (repo / "src" / "legacy" / "caller.py").unlink()
        return selection
    monkeypatch.setattr(scope, "select", select_then_remove)
    args = SimpleNamespace(limit=None, max_bytes=None, page=None, target=None, deadline=None)
    env = queries.answer("check", config.load(repo), args, natives.capability(), "json")
    assert (env["status"], env["freshness"]) == ("ok", "unknown")


def test_check_out_of_time_says_so_in_every_view(repo: Path):
    """REQ-FUNC-41815b22: a deadline gives unknown with its own message, shown in text."""
    env = query(repo, "check", "--deadline", "0.000001")
    assert env["freshness"] == "unknown" and "time" in env["message"]
    text = run_entry(["check", "--root", str(repo), "--deadline", "0.000001"]).stdout
    assert env["message"] in text


def test_check_lists_stay_within_the_byte_budget(tmp_path: Path):
    """REQ-NFR-17c50caa: long freshness lists are shortened to the budget."""
    root = make_repo(tmp_path / "repo", {"src/m.py": "x = 1\n"})
    run_json(["index", "--root", str(root)])
    for n in range(60):
        (root / "src" / f"new_module_{n:02d}_with_a_long_descriptive_name.py").write_text(
            "y = 2\n", encoding="utf-8")
    done = run_entry(["check", "--root", str(root), "--json", "--limit", "200",
                      "--max-bytes", "1024"])
    env = json.loads(done.stdout)
    assert len(done.stdout.encode("utf-8")) <= 1024 + 1
    assert env["has_more"] is True and env["freshness"] == "stale"


def test_a_query_reads_one_generation(repo: Path, monkeypatch):
    """REQ-REL-1eeb1914: a publication cannot change the rows a running query reads."""
    database = config.load(repo).database
    real = store.read_meta
    blocked: list[bool] = []

    def read_then_publish(conn):
        meta = real(conn)
        writer = sqlite3.connect(database, timeout=0.1)
        try:
            writer.execute("DELETE FROM symbols WHERE name = 'save_order'")
            writer.commit()
        except sqlite3.OperationalError:
            blocked.append(True)
            writer.rollback()
        finally:
            writer.close()
        return meta
    monkeypatch.setattr(store, "read_meta", read_then_publish)
    args = SimpleNamespace(limit=None, max_bytes=None, page=None, target="save_order",
                           deadline=None)
    env = queries.answer("find", config.load(repo), args, natives.capability(), "json")
    assert blocked and any(r["name"] == "save_order" for r in env["results"])


def test_status_text_shows_whether_this_python_can_index(repo: Path):
    """REQ-FUNC-a8ece064: the default view reports indexing capability."""
    text = run_entry(["status", "--root", str(repo)]).stdout
    assert "indexing: supported (" in text


def test_plugin_envelopes_carry_state_and_capability(repo: Path):
    """REQ-FUNC-8cb1a3b7: plugin answers fill index and capability whenever known."""
    env = query(repo, "scope")
    assert env["index"] == "ready" and env["indexing_supported"] is True
    _code, env = run_json(["status", "--root", str(repo), "--protocol", "2"])
    assert env["indexing_supported"] is not None


def test_file_without_a_path_is_an_invalid_request(repo: Path):
    """REQ-FUNC-a603d692: an empty path is a request error, not a missing file."""
    env = query(repo, "file", "--", "")
    assert (env["status"], env["reason"]) == ("error", "invalid_request")

# END OF FILE
