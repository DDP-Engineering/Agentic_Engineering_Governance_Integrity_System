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
@file test_structure.py
@brief P5 structural guards: the philosophy is enforced, size is not.
@details Anti-regrowth tests. Deliberately no size policing - there is
         no line-count test, by product decision. Guarded invariants:
         no hook/waiver/transaction machinery ever grows back into the
         payload, the CLI stays standard-library-only, `check` stays
         advisory without --strict, and every payload file carries the
         license header. The guard predicates are plain functions over
         source text, self-tested here against deliberately bad input -
         the "verify by mutation" of the P5 acceptance, without touching
         the real file.
"""

# IMPORTS

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from test_check import make_repo, write

# CONSTANTS

TREE = Path(__file__).resolve().parents[1]
PAYLOAD = TREE / "template" / ".agentic"
AEGIS_PY = PAYLOAD / "aegis.py"

#: identifiers of the heavy-AEGIS machinery that must never grow back.
FORBIDDEN_IDENTIFIERS = (
    "hook",
    "waiver",
    "evidence_form",
    "transaction",
    "journal_store",
    "permissionDecision",
)

#: file names that would mean adapter/hook wiring returned to the payload.
FORBIDDEN_FILE_NAMES = (
    "hooks.json",
    "settings.json",
    "run_hook.mjs",
    "workflow.toml",
    "components.toml",
)

#: every text file the payload ships must carry the license marker.
LICENSE_MARK = "PolyForm Noncommercial License 1.0.0"

#: the complete expected payload inventory (relative to .agentic/).
EXPECTED_FILES = (
    "AGENTS.md",
    "LICENSE.txt",
    "aegis.py",
    "steps/1_frame.md",
    "steps/2_specify.md",
    "steps/3_design.md",
    "steps/4_build.md",
    "steps/5_deliver.md",
    "steps/adopt.md",
    "templates/component.md",
    "templates/requirement.toml",
    "templates/spec.md",
    "templates/task.md",
)

IGNORED_DIR_PARTS = {"__pycache__", ".pytest_cache"}


# GUARD PREDICATES (plain functions so they can be self-tested on bad input)


def forbidden_identifier_hits(source: str) -> list[str]:
    """@brief The forbidden identifiers present in `source`, case-insensitive."""
    return [word for word in FORBIDDEN_IDENTIFIERS
            if re.search(word, source, re.IGNORECASE)]


def non_stdlib_imports(source: str) -> list[str]:
    """@brief Top-level module names imported by `source` outside the stdlib."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    return sorted(modules - set(sys.stdlib_module_names))


def payload_files() -> list[Path]:
    """@brief Every real payload file, ignoring caches."""
    return [
        path for path in sorted(PAYLOAD.rglob("*"))
        if path.is_file() and not (IGNORED_DIR_PARTS & set(path.parts))
    ]


# TESTS - the machinery must not grow back


def test_aegis_py_contains_no_forbidden_identifier():
    assert forbidden_identifier_hits(AEGIS_PY.read_text(encoding="utf-8")) == []


def test_the_forbidden_identifier_guard_actually_fires():
    bad = "def install_hook():\n    return Transaction()\n"
    assert forbidden_identifier_hits(bad) == ["hook", "transaction"]


def test_payload_ships_no_adapter_or_policy_files():
    names = {path.name for path in payload_files()}
    assert not names.intersection(FORBIDDEN_FILE_NAMES)
    assert not [p for p in payload_files() if p.suffix in (".mjs", ".json")]


def test_payload_inventory_is_exactly_the_documented_set():
    found = {path.relative_to(PAYLOAD).as_posix() for path in payload_files()}
    assert found == set(EXPECTED_FILES)


# TESTS - the payload is self-contained prose


def test_payload_never_references_external_documents():
    """The payload must stand alone: no plan docs, no sibling products."""
    banned = re.compile(r"plan doc|doc[ -]0\d|00_Planning|AEGIS_LIGHT_PLAN"
                        r"|WAEGIS|AEGIS 2\.", re.IGNORECASE)
    for path in payload_files():
        if path.suffix in (".md", ".py", ".toml"):
            hit = banned.search(path.read_text(encoding="utf-8"))
            assert hit is None, f"{path.name} references '{hit.group(0)}'"


# TESTS - Python 3.11 compatibility


#: an f-string whose braces contain a double-quoted string needs the
#: flexible f-string grammar of Python 3.12 (PEP 701) - the promise is 3.11.
NESTED_FSTRING_RE = re.compile(r'f"[^"\n]*\{[^{}\n]*"')


def test_no_nested_quote_fstrings_python_311_promise():
    hits = [line for line in AEGIS_PY.read_text(encoding="utf-8").splitlines()
            if NESTED_FSTRING_RE.search(line)]
    assert hits == [], f"3.12-only f-string syntax: {hits[0]}"


def test_the_nested_fstring_guard_actually_fires():
    assert NESTED_FSTRING_RE.search('x = f"TASK-{new_id(taken("a", "b"))}"')


# TESTS - the CLI stays standard-library-only


def test_aegis_py_imports_only_the_standard_library():
    assert non_stdlib_imports(AEGIS_PY.read_text(encoding="utf-8")) == []


def test_the_stdlib_import_guard_actually_fires():
    bad = "import requests\nfrom yaml import safe_load\nimport os\n"
    assert non_stdlib_imports(bad) == ["requests", "yaml"]


# TESTS - check stays advisory without --strict


def test_check_exits_zero_without_strict_even_on_errors(tmp_path, monkeypatch,
                                                        capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write(agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml",
          "not [ toml\n")
    capsys.readouterr()
    assert aegis.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "result: ERROR" in out  # the failure is visible, never blocking


def test_json_stdout_stays_one_parseable_document(tmp_path, monkeypatch,
                                                  capsys):
    """Every --json invocation must print exactly one JSON document."""
    import json as _json

    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write(agentic / "requirements" / "functional" / "REQ-FUNC-11111111.toml",
          "not [ toml\n")
    write(agentic / "tasks" / "TASK-aaaa.md",
          "# TASK-aaaa — t\n\nstage: build\ntype: fix\npath: quick\n"
          "requirements:\nbranch: b\nopened: 2026-08-02\n\n## Log\n\n- x\n")

    for argv in (["check", "--json"],
                 ["check", "--json", "--run"],
                 ["check", "--json", "--strict"],
                 ["check", "--json", "--full", "--task", "TASK-aaaa"],
                 ["status", "--json"],
                 ["status", "--json", "--all"],
                 ["status", "TASK-aaaa", "--json"]):
        capsys.readouterr()
        aegis.main(argv)
        document = _json.loads(capsys.readouterr().out)  # raises if impure
        assert document["schema"] == aegis.JSON_SCHEMA


def test_strict_is_an_explicit_opt_in_flag_not_a_default():
    source = AEGIS_PY.read_text(encoding="utf-8")
    match = re.search(r'add_argument\("--strict",\s*action="store_true"', source)
    assert match, "--strict must be a store_true opt-in flag"


# TESTS - license headers everywhere


def test_every_payload_file_carries_the_license_header():
    for path in payload_files():
        head = path.read_text(encoding="utf-8")[:600]
        assert LICENSE_MARK in head, f"missing license header: {path.name}"


def test_every_test_file_carries_the_license_header():
    for path in sorted(TREE.glob("tests/test_*.py")):
        head = path.read_text(encoding="utf-8")[:600]
        assert LICENSE_MARK in head, f"missing license header: {path.name}"
