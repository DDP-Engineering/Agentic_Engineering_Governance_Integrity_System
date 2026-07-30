#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_change_unit_paths.py
@brief Containment tests for implementation-stage changed paths.
@details AEGIS 2 records change units only through stage forms. These tests
         cover both that input boundary and defensive invariant evaluation.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 2.0.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from aegis.config import load_config
from aegis.invariants import evaluate
from aegis.models import ChangeUnit, Graph, Intent
from aegis.paths import contained_relative_path, relative_to_root
from aegis.stage_forms import StageOperationError, apply_stage, prepare_stage
from aegis.store import save_graph

# CONSTANTS

ENFORCED_SCOPE = (
    '[guardrails.scope]\nmode = "unrestricted"\nallowed_roots = []',
    '[guardrails.scope]\nmode = "enforce"\nallowed_roots = ["src"]',
)

# TESTS


def test_implementation_form_normalizes_and_deduplicates_changed_paths(
    tmp_path: Path,
) -> None:
    """@brief Import equivalent in-repository paths as one relative path."""
    graph = _implementation_graph()
    save_graph(tmp_path, graph)
    form = prepare_stage(tmp_path, graph, load_config(tmp_path))
    absolute = (tmp_path / "src" / "app.py").as_posix()
    _replace(
        form,
        {
            "changed_paths = []": (
                f'changed_paths = ["src/app.py", "{absolute}"]'
            ),
            'summary = ""': 'summary = "Implementation recorded"',
        },
    )

    apply_stage(tmp_path, graph, load_config(tmp_path))

    assert graph.change_units[0].touched_paths == ["src/app.py"]


def test_implementation_form_rejects_path_outside_repository(
    tmp_path: Path,
) -> None:
    """@brief Refuse a changed path that escapes the repository."""
    graph = _implementation_graph()
    save_graph(tmp_path, graph)
    form = prepare_stage(tmp_path, graph, load_config(tmp_path))
    outside = (tmp_path.parent / "outside.py").as_posix()
    _replace(
        form,
        {
            "changed_paths = []": f'changed_paths = ["{outside}"]',
            'summary = ""': 'summary = "Invalid path"',
        },
    )

    with pytest.raises(StageOperationError, match="outside the repository"):
        apply_stage(tmp_path, graph, load_config(tmp_path))


def test_scope_invariant_classifies_escape_and_out_of_scope_path(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Keep malformed stored paths evaluable as distinct findings."""
    replace_workflow_toml(*ENFORCED_SCOPE)
    graph = _implementation_graph()
    graph.change_units = [
        ChangeUnit(
            id="CU-1",
            touched_paths=[
                "src/app.py",
                "docs/readme.md",
                str(tmp_path.parent / "outside.py"),
            ],
        )
    ]

    result = next(
        item
        for item in evaluate(tmp_path, graph, load_config(tmp_path))
        if item.id == "INV-5"
    )

    assert not result.holds
    assert "Out-of-scope paths: docs/readme.md" in result.message
    assert "outside the repository" in result.message
    assert "src/app.py" not in result.message


def test_containment_helpers_keep_strict_and_lenient_contracts(
    tmp_path: Path,
) -> None:
    """@brief Preserve strict input and lenient evaluation containment APIs."""
    assert contained_relative_path("src/app.py", tmp_path) == "src/app.py"
    assert contained_relative_path(tmp_path.parent / "outside.py", tmp_path) is None
    with pytest.raises(ValueError, match="escapes workspace root"):
        relative_to_root(tmp_path.parent / "outside.py", tmp_path)


def _implementation_graph() -> Graph:
    """@brief Build a schema-3 graph positioned at implementation."""
    return Graph(
        run_id="feature-20260729T120000Z-abcdef12",
        stage="implementation",
        intent=Intent(id="I-0001", kind="feature", statement="Scope probe"),
    )


def _replace(path: Path, replacements: dict[str, str]) -> None:
    """@brief Apply exact substitutions to a generated test form."""
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert text.count(old) == 1
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


# END OF FILE
