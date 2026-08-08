#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_structure_guards.py
@brief Enforces WAEGIS 3 size, dependency, and architecture boundaries.
@details Parses source ASTs so comments and documentation can discuss removed
         V1 concepts without recreating their imports or symbols.
"""

import ast
import tomllib
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "src" / "waegis"


def _python_files() -> list[Path]:
    return sorted(path for path in SOURCE.rglob("*.py") if "__pycache__" not in path.parts)


def _line_count(paths: list[Path]) -> int:
    return sum(len(path.read_text(encoding="utf-8").splitlines()) for path in paths)


def test_core_and_packaging_line_guards() -> None:
    """@brief D5 prevents architecture regrowth beyond approved budgets."""
    assert _line_count(_python_files()) <= 9_500
    packaging = [
        path
        for path in (PROJECT / "packaging").rglob("*")
        if path.is_file() and path.suffix in {".py", ".cmd", ".sh"}
    ]
    assert _line_count(packaging) <= 1_000


def test_runtime_dependencies_remain_empty() -> None:
    """@brief R7 keeps target execution standard-library only."""
    project = tomllib.loads((PROJECT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == []
    assert project["name"] == "waegis"
    assert project["scripts"] == {"waegis": "waegis.cli:main"}


def test_forbidden_imports_symbols_and_package_names_are_absent() -> None:
    """@brief The anti-regrowth list rejects V1 subsystems as executable code."""
    forbidden_import_roots = {"aegis", "hmac", "requests", "urllib3"}
    forbidden_symbol_fragments = {"transaction", "journal", "stepspec", "repowise"}
    for path in _python_files():
        assert "waegis2" not in path.read_text(encoding="utf-8").casefold()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not ({alias.name.split(".")[0] for alias in node.names} & forbidden_import_roots)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden_import_roots
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                folded = node.name.casefold()
                assert not any(fragment in folded for fragment in forbidden_symbol_fragments)


def test_removed_v1_trees_and_cli_options_are_absent() -> None:
    """@brief V1 engine, probe fleet, RepoWise command, and dirty bypass stay removed."""
    assert not list((SOURCE / "engine").glob("*.py"))
    assert not list((SOURCE / "commands").glob("*.py"))
    assert not list((SOURCE / "probes").glob("*.py"))
    cli = (SOURCE / "cli.py").read_text(encoding="utf-8")
    assert "--allow-dirty" not in cli
    assert 'add_parser("repowise"' not in cli
    assert "git commit" not in cli
    assert "git branch" not in cli


# END OF FILE
