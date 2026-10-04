#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_python_extract.py
@brief Per-file Python extraction, module naming and per-file time limits.
@details Covers REQ-FUNC-aa0a867a (definitions and positions),
         REQ-FUNC-7432a8a2 (how each reference is bound inside its file),
         REQ-FUNC-45ed74a5 (syntax and encoding errors), REQ-FUNC-0c82c3c6
         (import roots and module names), REQ-DATA-9004cf27 (stable symbol
         IDs) and REQ-REL-1162622e (a file that takes too long is failed in
         a worker that is replaced, and the next file still parses).
"""

# IMPORTS

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from codegraph import config, natives, python_extract

# CONSTANTS

SAMPLE = '''\
"""Module docstring with def fake_in_string(): pass"""
import os
from pkg.models import Order as Model
# def fake_in_comment(): pass


def decorate(fn):
    return fn


@decorate
async def fetch(url: str,
                *,
                retries: int = 3) -> bytes:
    data = os.path.join(url)
    return data


class Outer(Base):
    limit: int = 5

    class Inner:
        def method(self, value):
            return self.helper(value)

        def helper(self, value):
            return value

    def käse(self, order: Model):
        local = order
        return save(local)
'''

# HELPER FUNCTIONS


@pytest.fixture(scope="module")
def parser():
    """@brief One vendored parser for in-process extraction tests."""
    return natives.new_parser()


def facts_for(parser, text: str, path: str = "pkg/shop.py", module: str = "pkg.shop"):
    """@brief Extract one in-memory source."""
    return python_extract.extract(path, text.encode("utf-8"), module, parser)


def by_name(facts) -> dict[str, object]:
    """@brief Symbols keyed by qualified name."""
    return {symbol.qualified_name: symbol for symbol in facts.symbols}

# TESTS - definitions (REQ-FUNC-aa0a867a)


def test_definitions_have_kinds_names_signatures_and_positions(parser):
    """REQ-FUNC-aa0a867a: every supported construct with exact positions."""
    facts = facts_for(parser, SAMPLE)
    symbols = by_name(facts)
    assert facts.status == "complete"
    expected = {
        "pkg.shop": ("module", "", (1, 1)),
        "pkg.shop.decorate": ("function", "def decorate(fn)", (7, 1)),
        "pkg.shop.decorate.fn": ("parameter", "", (7, 14)),
        "pkg.shop.fetch": ("function",
                           "async def fetch(url: str, *, retries: int = 3) -> bytes", (11, 1)),
        "pkg.shop.fetch.url": ("parameter", "str", (12, 17)),
        "pkg.shop.fetch.retries": ("parameter", "int", (14, 17)),
        "pkg.shop.fetch.data": ("variable", "", (15, 5)),
        "pkg.shop.Outer": ("class", "class Outer(Base)", (19, 1)),
        "pkg.shop.Outer.limit": ("variable", "int", (20, 5)),
        "pkg.shop.Outer.Inner": ("class", "class Inner", (22, 5)),
        "pkg.shop.Outer.Inner.method": ("method", "def method(self, value)", (23, 9)),
        "pkg.shop.Outer.käse": ("method", "def käse(self, order: Model)", (29, 5)),
        "pkg.shop.Outer.käse.order": ("parameter", "Model", (29, 20)),
        "pkg.shop.Outer.käse.local": ("variable", "", (30, 9)),
    }
    for qualified, (kind, signature, start) in expected.items():
        symbol = symbols[qualified]
        assert (symbol.kind, symbol.signature, (symbol.start_line, symbol.start_column)) == \
            (kind, signature, start), qualified
    assert (symbols["pkg.shop.fetch"].end_line, symbols["pkg.shop.fetch"].end_column) == (16, 15)
    assert symbols["pkg.shop.Outer.Inner.method"].parent_id == symbols["pkg.shop.Outer.Inner"].id


def test_comments_and_strings_define_nothing(parser):
    """REQ-FUNC-aa0a867a: text that only looks like code is not a definition."""
    names = {symbol.name for symbol in facts_for(parser, SAMPLE).symbols}
    assert "fake_in_string" not in names and "fake_in_comment" not in names


def test_crlf_and_lf_sources_give_identical_positions(parser):
    """REQ-FUNC-aa0a867a: line endings never shift a citation."""
    lf = [(s.qualified_name, s.start_line, s.start_column, s.end_line, s.end_column)
          for s in facts_for(parser, SAMPLE).symbols]
    crlf = [(s.qualified_name, s.start_line, s.start_column, s.end_line, s.end_column)
            for s in facts_for(parser, SAMPLE.replace("\n", "\r\n")).symbols]
    assert lf == crlf


def test_columns_count_code_points_not_bytes(parser):
    """REQ-FUNC-aa0a867a: a non-ASCII identifier before a name keeps columns exact."""
    facts = facts_for(parser, "ä = 1; ö = ä\n")
    symbols = by_name(facts)
    assert symbols["pkg.shop.ö"].start_column == 8

# TESTS - in-file bindings (REQ-FUNC-7432a8a2)


def test_references_record_how_each_name_is_bound(parser):
    """REQ-FUNC-7432a8a2: local, import, builtin, self and unbound bindings."""
    facts = facts_for(parser, SAMPLE)
    symbols = by_name(facts)
    refs = {(ref.kind, ref.spelling, ref.line): ref for ref in facts.references}
    assert refs[("import", "os", 2)].binding == "import"
    assert refs[("import", "os", 2)].qualname == "os"
    assert refs[("import", "pkg.models.Order", 3)].qualname == "pkg.models.Order"
    join = refs[("call", "os.path.join", 15)]
    assert (join.binding, join.qualname) == ("import", "os.path.join")
    assert join.from_id == symbols["pkg.shop.fetch"].id
    helper = refs[("call", "self.helper", 24)]
    assert (helper.binding, helper.qualname) == ("self", "pkg.shop.Outer.Inner.helper")
    order_read = refs[("read", "order", 30)]
    assert (order_read.binding, order_read.local_target) == \
        ("local", symbols["pkg.shop.Outer.käse.order"].id)
    assert refs[("call", "save", 31)].binding == "unbound"
    model = refs[("read", "Model", 29)]
    assert (model.binding, model.qualname) == ("import", "pkg.models.Order")
    assert refs[("read", "Base", 19)].binding == "unbound"


def test_parameter_shadows_module_name_and_builtins_are_marked(parser):
    """REQ-FUNC-7432a8a2: the innermost binding wins; builtins are external."""
    facts = facts_for(parser, "def value():\n    return 1\n\n"
                              "def use(value):\n    return len(value)\n")
    symbols = by_name(facts)
    refs = {(ref.kind, ref.spelling): ref for ref in facts.references}
    assert refs[("read", "value")].local_target == symbols["pkg.shop.use.value"].id
    assert refs[("call", "len")].binding == "builtin"


def test_typed_star_parameters_are_parameters(parser):
    """REQ-FUNC-aa0a867a: annotated `*args` and `**kw` bind like plain ones."""
    facts = facts_for(parser, "def f(*args: int, **kw: str):\n    return kw.get(args)\n")
    symbols = by_name(facts)
    assert symbols["pkg.shop.f.args"].signature == "int"
    assert symbols["pkg.shop.f.kw"].signature == "str"
    reads = {ref.spelling: ref.binding for ref in facts.references if ref.kind == "read"}
    assert reads["args"] == "local" and reads["kw"] == "local"


def test_attribute_delete_and_rebinding_targets_are_writes(parser):
    """REQ-FUNC-7432a8a2: later bindings of a name write to its first definition."""
    source = ("x = 1\nclass C:\n    def m(self):\n        self.x = 1\n"
              "del x\nfor x in []:\n    pass\nwith open('f') as x:\n    pass\n"
              "if (x := 2):\n    pass\n")
    facts = facts_for(parser, source)
    writes = sorted((ref.spelling, ref.line) for ref in facts.references if ref.kind == "write")
    assert writes == [("self.x", 4), ("x", 5), ("x", 6), ("x", 8), ("x", 10)]
    target = by_name(facts)["pkg.shop.x"].id
    assert {ref.local_target for ref in facts.references
            if ref.kind == "write" and ref.spelling == "x"} == {target}


def test_nested_class_methods_do_not_see_the_outer_class_body(parser):
    """REQ-FUNC-7432a8a2: class bodies are not part of a method's scope chain."""
    source = ("class Outer:\n    def helper(self):\n        pass\n"
              "    class Inner:\n        def run(self):\n            helper()\n")
    call = next(ref for ref in facts_for(parser, source).references if ref.kind == "call")
    assert (call.spelling, call.binding, call.local_target) == ("helper", "unbound", None)


def test_lambda_bodies_record_their_references(parser):
    """REQ-FUNC-7432a8a2: a call inside a lambda is a call; its parameters are not reads."""
    source = "def normalize(x):\n    return x\nkey = lambda x, n=normalize: normalize(x)\n"
    facts = facts_for(parser, source)
    target = by_name(facts)["pkg.shop.normalize"].id
    found = [(ref.kind, ref.spelling, ref.local_target) for ref in facts.references
             if ref.line == 3]
    assert ("call", "normalize", target) in found and ("read", "normalize", target) in found
    assert not [ref for ref in found if ref[1] == "x"]


def test_attribute_calls_on_any_receiver_are_calls(parser):
    """REQ-FUNC-7432a8a2: `super().__init__()` and `', '.join()` record their callee."""
    source = "class A:\n    def __init__(self):\n        super().__init__()\n        ', '.join([])\n"
    calls = sorted((ref.spelling, ref.binding) for ref in facts_for(parser, source).references
                   if ref.kind == "call")
    assert calls == [("__init__", "attribute"), ("join", "attribute"), ("super", "builtin")]


def test_global_and_nonlocal_names_bind_to_the_outer_definition(parser):
    """REQ-FUNC-7432a8a2: no local variable is invented for a declared outer name."""
    source = ("counter = 0\ndef bump():\n    global counter\n    counter += 1\n"
              "def outer():\n    total = 0\n    def add():\n        nonlocal total\n"
              "        total += 1\n")
    facts = facts_for(parser, source)
    symbols = by_name(facts)
    assert "pkg.shop.bump.counter" not in symbols and "pkg.shop.outer.add.total" not in symbols
    writes = {ref.spelling: ref.local_target for ref in facts.references if ref.kind == "write"}
    assert writes == {"counter": symbols["pkg.shop.counter"].id,
                      "total": symbols["pkg.shop.outer.total"].id}


def test_module_range_ends_at_the_last_character(parser):
    """REQ-FUNC-aa0a867a: a trailing newline is not part of the module's range."""
    for text in ("x = 1\n", "x = 1", "x = 1\r\n\r\n"):
        module = by_name(facts_for(parser, text))["pkg.shop"]
        assert (module.end_line, module.end_column) == (1, 5), repr(text)


def test_star_imports_and_dynamic_access_stay_unresolved(parser):
    """REQ-FUNC-7432a8a2: nothing is guessed for star imports; getattr is a built-in call."""
    facts = facts_for(parser, "from pkg.util import *\n\nhandler = getattr(obj, 'x')\n")
    refs = {(ref.kind, ref.spelling): ref for ref in facts.references}
    assert refs[("import", "pkg.util.*")].binding == "star"
    assert refs[("call", "getattr")].binding == "builtin"


def test_relative_imports_resolve_against_the_package(parser):
    """REQ-FUNC-7432a8a2: `from . import x` and `from ..m import y` are qualified."""
    facts = facts_for(parser, "from . import sibling\nfrom ..core import base\n",
                      path="pkg/sub/mod.py", module="pkg.sub.mod")
    qualnames = {ref.spelling: ref.qualname for ref in facts.references if ref.kind == "import"}
    assert qualnames == {"pkg.sub.sibling": "pkg.sub.sibling", "pkg.core.base": "pkg.core.base"}

# TESTS - syntax and encoding errors (REQ-FUNC-45ed74a5)


def test_syntax_error_keeps_unaffected_top_level_statements(parser):
    """REQ-FUNC-45ed74a5: partial files keep safe facts."""
    facts = facts_for(parser, "def good():\n    return 1\n\ndef broken(:\n    pass\n")
    assert facts.status == "partial" and facts.reason == "syntax"
    names = {symbol.name for symbol in facts.symbols}
    assert "good" in names and "broken" not in names


def test_undecodable_file_is_failed(parser):
    """REQ-FUNC-45ed74a5: bytes that are not UTF-8 produce no facts."""
    facts = python_extract.extract("pkg/bad.py", b"x = '\xff\xfe'\n", "pkg.bad", parser)
    assert (facts.status, facts.reason, facts.symbols) == ("failed", "encoding", [])

# TESTS - import roots (REQ-FUNC-0c82c3c6)


def make_settings(root: Path, body: str = "") -> config.Settings:
    """@brief Settings for a temporary repository."""
    (root / ".agentic").mkdir(parents=True, exist_ok=True)
    (root / ".agentic" / "aegis.toml").write_text(body, encoding="utf-8")
    return config.load(root)


def test_module_names_follow_the_deepest_import_root():
    """REQ-FUNC-0c82c3c6: names are relative to the deepest containing root."""
    roots = ["", "pkg", "pkg/src"]
    assert python_extract.module_name("pkg/src/shop/orders.py", roots) == "shop.orders"
    assert python_extract.module_name("pkg/src/shop/__init__.py", roots) == "shop"
    assert python_extract.module_name("pkg/tools/run.py", roots) == "tools.run"
    assert python_extract.module_name("other/x.pyi", ["pkg"]) == "other.x"


def test_import_roots_come_from_setting_then_manifests_then_root(tmp_path: Path):
    """REQ-FUNC-0c82c3c6: explicit roots win; manifests and src layouts follow."""
    (tmp_path / "pkg" / "src").mkdir(parents=True)
    settings = make_settings(tmp_path)
    assert python_extract.import_roots(settings, ["pkg/pyproject.toml"]) == ["pkg", "pkg/src"]
    assert python_extract.import_roots(settings, []) == [""]
    settings = make_settings(tmp_path, '[codegraph]\npython_import_roots = ["lib/"]\n')
    assert python_extract.import_roots(settings, ["pkg/pyproject.toml"]) == ["lib"]


def test_setup_scripts_are_never_executed(tmp_path: Path, parser):
    """REQ-FUNC-0c82c3c6: discovering roots runs no repository code."""
    marker = tmp_path / "executed.txt"
    (tmp_path / "setup.py").write_text(
        f"open({str(marker)!r}, 'w').write('ran')\n", encoding="utf-8")
    settings = make_settings(tmp_path)
    python_extract.import_roots(settings, ["setup.cfg"])
    python_extract.extract("setup.py", (tmp_path / "setup.py").read_bytes(), "setup", parser)
    assert not marker.exists()

# TESTS - symbol identity (REQ-DATA-9004cf27)


def test_ids_survive_line_shifts_and_change_on_rename(parser):
    """REQ-DATA-9004cf27: identity ignores position but follows the name."""
    first = by_name(facts_for(parser, SAMPLE))
    shifted = by_name(facts_for(parser, "\n\n\n" + SAMPLE))
    renamed = by_name(facts_for(parser, SAMPLE.replace("def helper", "def assist")))
    assert first["pkg.shop.fetch"].id == shifted["pkg.shop.fetch"].id
    assert "pkg.shop.Outer.Inner.assist" in renamed
    assert first["pkg.shop.Outer.Inner.helper"].id not in {s.id for s in renamed.values()}
    assert all(len(s.id) == 32 and int(s.id, 16) >= 0 for s in first.values())


def test_symbol_id_matches_the_documented_formula():
    """REQ-DATA-9004cf27: the ID is the first 32 hex digits of SHA-256 over the key."""
    assert python_extract.symbol_id("pkg/shop.py", "pkg.shop", "module", "pkg.shop", "",
                                    0) == "4c2566078ef03535de8fca9598d7dc82"


def test_normalized_facts_match_the_golden_digest(parser):
    """REQ-PLAT-3430c1f3: every platform and Python extracts the same facts."""
    facts = facts_for(parser, SAMPLE)
    rows = sorted([["symbol", *dataclasses.astuple(s)] for s in facts.symbols]
                  + [["ref", *dataclasses.astuple(r)] for r in facts.references], key=json.dumps)
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=True).encode("ascii")).hexdigest()
    assert (len(facts.symbols), len(facts.references), facts.status) == (20, 19, "complete")
    assert digest == "2bc100f8922a4b3355ad2a7734c308bceed08a29229fbe059391e529d777c500"


def test_identical_definitions_get_distinct_ids(parser):
    """REQ-DATA-9004cf27: duplicates are told apart by their order."""
    facts = facts_for(parser, "def twice():\n    pass\n\ndef twice():\n    pass\n")
    ids = [s.id for s in facts.symbols if s.name == "twice"]
    assert len(ids) == 2 and len(set(ids)) == 2

# TESTS - per-file time limit (REQ-REL-1162622e)


def test_slow_file_fails_with_parse_timeout_and_the_next_file_parses(tmp_path: Path,
                                                                     monkeypatch):
    """REQ-REL-1162622e: the worker is replaced and indexing continues."""
    monkeypatch.setenv(python_extract.SLOW_FILE_HOOK, "pkg/slow.py")
    jobs = [("pkg/a.py", b"def a():\n    pass\n", "pkg.a"),
            ("pkg/slow.py", b"def slow():\n    pass\n", "pkg.slow"),
            ("pkg/b.py", b"def b():\n    pass\n", "pkg.b")]
    with python_extract.ExtractorPool(workers=1, timeout=1) as pool:
        results = {facts.path: facts for facts in pool.extract_all(jobs)}
    assert (results["pkg/slow.py"].status, results["pkg/slow.py"].reason) == \
        ("failed", "parse-timeout")
    assert results["pkg/slow.py"].symbols == []
    assert {s.name for s in results["pkg/b.py"].symbols} == {"b"}
    assert {s.name for s in results["pkg/a.py"].symbols} == {"a"}


def test_pool_stops_when_asked(monkeypatch):
    """REQ-REL-1162622e: a cancellation request ends extraction promptly."""
    monkeypatch.setenv(python_extract.SLOW_FILE_HOOK, "pkg/slow.py")
    jobs = [("pkg/slow.py", b"x = 1\n", "pkg.slow")]
    started: list = []

    def stop() -> bool:   # only once a worker is busy with the slow file
        if pool.workers:
            started.append(pool.workers[0][0])
            return True
        return False
    with (python_extract.ExtractorPool(workers=1, timeout=60) as pool,
          pytest.raises(python_extract.Cancelled)):
        list(pool.extract_all(jobs, should_stop=stop))
    assert started and not started[0].is_alive() and pool.workers == []

# END OF FILE
