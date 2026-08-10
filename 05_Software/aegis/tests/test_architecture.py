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
@file    test_architecture.py
@brief   Verify source-of-truth, dependency direction, and runtime imports.
@details Covers PR-RUNTIME-001-002, AC-RUNTIME-001, and TA-LAYER-001.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

import ast
import sys
from pathlib import Path

import aegis

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

PACKAGE_ROOT = Path(aegis.__file__).resolve().parent


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------


def imported_roots(path: Path) -> set[str]:
    """@brief Return top-level import names from one Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def imported_modules(path: Path) -> set[str]:
    """@brief Return full absolute import names from one source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


def test_development_imports_the_delivered_source_tree() -> None:
    """@brief Verify repository development executes downstream payload bytes."""
    normalized = PACKAGE_ROOT.as_posix()

    assert normalized.endswith("template/.agentic/aegis/cli/src/aegis")


def test_runtime_uses_only_standard_library_dependencies() -> None:
    """@brief Reject undeclared third-party runtime imports."""
    permitted = set(sys.stdlib_module_names) | {"aegis", "__future__"}

    for source in PACKAGE_ROOT.rglob("*.py"):
        assert imported_roots(source) <= permitted, source


def test_inward_layers_do_not_import_outer_adapters() -> None:
    """@brief Verify domain and application dependencies continue to point inward."""
    forbidden = ("aegis.interface", "aegis.infrastructure", "aegis.composition")

    for layer in ("domain", "application", "ports"):
        for source in (PACKAGE_ROOT / layer).rglob("*.py"):
            assert not any(
                module.startswith(forbidden) for module in imported_modules(source)
            ), source


def test_registry_drives_dispatch_and_cli_inputs_without_operation_branches() -> None:
    """@brief Verify TA-MODULE-003/005 keep one operation declaration."""
    dispatcher = (PACKAGE_ROOT / "application" / "dispatcher.py").read_text(
        encoding="utf-8"
    )
    cli = (PACKAGE_ROOT / "interface" / "cli.py").read_text(encoding="utf-8")

    assert 'entry.operation == "help.show"' not in dispatcher
    assert 'entry.operation == "version.show"' not in dispatcher
    assert "entry.executor(" in dispatcher
    assert "entry.arguments" in cli
    assert "_arguments_for_parser" not in cli


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
