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
@brief Containment of recorded change-unit paths, at the boundary and after.
@details Recorded paths feed the scope invariant, which every graph-reading
         command evaluates. A path that escapes the repository is refused when
         it is recorded, and a graph that already holds one stays evaluable: the
         scope invariant reports it as a finding rather than raising and taking
         `status`, `invariants`, `report`, and `delivery-preflight` with it.
@author Eng. Dan Dumitru Pasare
@date 2026-07-23
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.config import load_config
from aegis.invariants import evaluate
from aegis.models import ChangeUnit, Graph, Intent
from aegis.paths import contained_relative_path, is_allowed_path
from aegis.store import graph_path, load_graph, resolve_run_id

# CONSTANTS

ENFORCED_SCOPE = (
    '[guardrails.scope]\nmode = "unrestricted"\nallowed_roots = []',
    '[guardrails.scope]\nmode = "enforce"\nallowed_roots = ["src"]',
)


# LOCAL HELPERS


def run_cli(repo_root: Path, *args: str) -> None:
    """
    @brief      Run one CLI command with the process directory at a repository.
    @param[in]  repo_root Repository the command runs against.
    @param[in]  args Command-line arguments.
    @return     None.
    @exception  SystemExit Propagated from the command under test.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    previous = Path.cwd()
    try:
        os.chdir(repo_root)
        main(list(args))
    finally:
        os.chdir(previous)


def start_run(repo_root: Path) -> None:
    """
    @brief      Start one feature run so graph commands have an active target.
    @param[in]  repo_root Repository receiving the run.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    run_cli(repo_root, "start", "--kind", "feature", "--statement", "scope probe")


def active_graph(repo_root: Path) -> Graph:
    """
    @brief      Load the graph selected by the worktree pointer.
    @param[in]  repo_root Repository root.
    @return     The active graph.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    return load_graph(repo_root, resolve_run_id(repo_root))


def graph_with_paths(*touched: str) -> Graph:
    """
    @brief      Build an in-memory graph holding one change unit.
    @param[in]  touched Recorded change-unit paths.
    @return     Graph ready for invariant evaluation.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    return Graph(
        run_id="feature-2026-07-23T101010Z-abcdef12",
        stage="implementation",
        intent=Intent(id="I-0001", kind="feature", statement="scope probe"),
        change_units=[ChangeUnit(id="CU-1", touched_paths=list(touched))],
    )


def scope_result(repo_root: Path, graph: Graph):  # type: ignore[no-untyped-def]
    """
    @brief      Evaluate the invariants and return the scope result.
    @param[in]  repo_root Repository root.
    @param[in]  graph Graph under evaluation.
    @return     The `INV-5` invariant result.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    config = load_config(repo_root)
    return next(item for item in evaluate(repo_root, graph, config) if item.id == "INV-5")


# TESTS — recording boundary


def test_record_change_stores_a_relative_path_unchanged(tmp_path: Path) -> None:
    """
    @brief      Verify an ordinary repository-relative path round-trips.
    @param[in]  tmp_path Repository root.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    start_run(tmp_path)

    run_cli(tmp_path, "record-change", "--id", "CU-1", "--path", "src/app.py")

    assert active_graph(tmp_path).change_units[0].touched_paths == ["src/app.py"]


def test_record_change_normalizes_an_absolute_path_inside_the_repository(tmp_path: Path) -> None:
    """
    @brief      Verify an absolute in-repository path is stored relative.
    @param[in]  tmp_path Repository root.
    @return     None.
    @details    Scope and component checks compare recorded paths against
                repository-relative globs, so one canonical stored form is what
                makes those comparisons meaningful.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    start_run(tmp_path)

    run_cli(tmp_path, "record-change", "--id", "CU-1", "--path", str(tmp_path / "src" / "app.py"))

    assert active_graph(tmp_path).change_units[0].touched_paths == ["src/app.py"]


def test_record_change_deduplicates_paths_that_normalize_together(tmp_path: Path) -> None:
    """
    @brief      Verify two spellings of one path are stored once.
    @param[in]  tmp_path Repository root.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    start_run(tmp_path)

    run_cli(
        tmp_path,
        "record-change",
        "--id",
        "CU-1",
        "--path",
        "src/app.py",
        "--path",
        str(tmp_path / "src" / "app.py"),
    )

    assert active_graph(tmp_path).change_units[0].touched_paths == ["src/app.py"]


def test_record_change_refuses_a_path_outside_the_repository(tmp_path: Path) -> None:
    """
    @brief      Verify an escaping path is refused with actionable guidance.
    @param[in]  tmp_path Repository root.
    @return     None.
    @details    Persisting one would leave every later policy evaluation
                reasoning about a path it can never resolve.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    start_run(tmp_path)
    outside = tmp_path.parent / "outside.py"

    with pytest.raises(SystemExit) as raised:
        run_cli(tmp_path, "record-change", "--id", "CU-1", "--path", str(outside))

    assert "outside the repository" in str(raised.value)
    assert active_graph(tmp_path).change_units == []


# TESTS — evaluation stays possible for a graph that already holds one


def test_scope_invariant_reports_an_escaping_path_instead_of_raising(
    tmp_path: Path, replace_workflow_toml: Callable[[str, str], Path]
) -> None:
    """
    @brief      Verify an escaping recorded path becomes a finding, not a crash.
    @param[in]  tmp_path Repository root.
    @param[in]  replace_workflow_toml Fixture enabling scope enforcement.
    @return     None.
    @details    Graphs written before the recording boundary existed — or edited
                by hand — still have to be evaluable.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    replace_workflow_toml(*ENFORCED_SCOPE)
    escaping = str(tmp_path.parent / "outside.py")

    result = scope_result(tmp_path, graph_with_paths(escaping))

    assert result.holds is False
    assert "outside the repository" in result.message
    assert escaping in result.message


def test_scope_invariant_separates_escaping_paths_from_out_of_scope_paths(
    tmp_path: Path, replace_workflow_toml: Callable[[str, str], Path]
) -> None:
    """
    @brief      Verify the two failure kinds are reported distinctly.
    @param[in]  tmp_path Repository root.
    @param[in]  replace_workflow_toml Fixture enabling scope enforcement.
    @return     None.
    @details    "Not under an allowed root" and "not in this repository at all"
                need different operator responses.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    replace_workflow_toml(*ENFORCED_SCOPE)

    result = scope_result(
        tmp_path,
        graph_with_paths("src/app.py", "docs/readme.md", str(tmp_path.parent / "outside.py")),
    )

    assert result.holds is False
    assert "Out-of-scope paths: docs/readme.md" in result.message
    assert "outside the repository" in result.message
    # The in-scope path is not reported as a problem.
    assert "src/app.py" not in result.message


def test_status_still_runs_when_a_stored_graph_holds_an_escaping_path(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify a graph holding an escaping path no longer bricks the run.
    @param[in]  tmp_path Repository root.
    @param[in]  replace_workflow_toml Fixture enabling scope enforcement.
    @param[in]  capsys Output capture fixture.
    @return     None.
    @details    This is the user-visible failure: `status`, `invariants`,
                `report`, and `delivery-preflight` all evaluate invariants, so
                one bad recorded path used to abort each of them with a
                traceback until the graph was repaired by hand.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    start_run(tmp_path)
    replace_workflow_toml(*ENFORCED_SCOPE)
    run_id = resolve_run_id(tmp_path)
    path = graph_path(tmp_path, run_id)
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["change_units"] = [
        {"id": "CU-1", "touched_paths": [str(tmp_path.parent / "outside.py")]}
    ]
    path.write_text(json.dumps(stored, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    capsys.readouterr()  # drop the `start` output so only `status` is parsed

    run_cli(tmp_path, "status")

    report = json.loads(capsys.readouterr().out)
    assert report["run_id"] == run_id
    failures = [item for item in report["blocking_failures"] if item["id"] == "INV-5"]
    assert failures and "outside the repository" in failures[0]["message"]


# TESTS — shared containment helper


def test_contained_relative_path_accepts_paths_inside_the_root(tmp_path: Path) -> None:
    """
    @brief      Verify the lenient helper normalizes contained paths.
    @param[in]  tmp_path Root directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    assert contained_relative_path("src/app.py", tmp_path) == "src/app.py"
    assert contained_relative_path(tmp_path / "src" / "app.py", tmp_path) == "src/app.py"


def test_contained_relative_path_returns_none_for_an_escape(tmp_path: Path) -> None:
    """
    @brief      Verify the lenient helper reports an escape without raising.
    @param[in]  tmp_path Root directory.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    assert contained_relative_path(tmp_path.parent / "outside.py", tmp_path) is None
    assert contained_relative_path("../outside.py", tmp_path) is None


def test_the_strict_helper_still_raises_so_boundaries_can_refuse(tmp_path: Path) -> None:
    """
    @brief      Verify the strict containment helper keeps raising.
    @param[in]  tmp_path Root directory.
    @return     None.
    @details    The pair is deliberate: input boundaries want the exception so
                they can refuse loudly, evaluators want the `None`. This is also
                the behavior that made the scope invariant abort before it
                classified escapes itself.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    with pytest.raises(ValueError, match="escapes workspace root"):
        is_allowed_path(tmp_path.parent / "outside.py", tmp_path, ["src/**"])


# END OF FILE
