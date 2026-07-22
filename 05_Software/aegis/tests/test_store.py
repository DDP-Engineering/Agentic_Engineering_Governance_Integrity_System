#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_store.py
@brief Workflow support module for test_store.
@details Covers expected workflow behavior through focused pytest checks.
@details Updated 0.2.0 for upward root discovery: invoking the CLI from
         `.agentic` (or below it) now heals to the surrounding project root
         instead of exiting, so the former rejection tests assert the healed
         resolution and the `_reject_nested_agentic_root` safety net is
         covered directly. Broader discovery scenarios live in
         `test_root_discovery.py`.
@details Updated 0.3.0 for WP2 workspace-local state, strict explicit-first
         resolution, typed errors, atomic publication, and Git-ignore behavior.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 0.3.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import aegis.store as store
from aegis.store import (
    RunResolutionError,
    _reject_nested_agentic_root,
    current_run_path,
    init_graph,
    load_graph,
    repo_root_from,
    resolve_run_id,
    workspace_root,
)


# TESTS


def test_repo_root_from_heals_the_agentic_directory_itself(tmp_path: Path) -> None:
    """
    @brief      Resolving from `.agentic` itself heals to the project root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Regression lineage: before the 0.3.0 guard, invoking the CLI
                with the working directory set to a project's own `.agentic`
                folder silently created a nested `.agentic/.agentic/...` copy;
                the guard then made this a hard `SystemExit`. Upward discovery
                improves it once more: the parent that contains `.agentic` is
                resolved as the root and the command simply works.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    agentic_dir = tmp_path / ".agentic"
    agentic_dir.mkdir()

    assert repo_root_from(agentic_dir) == tmp_path.resolve()


def test_repo_root_from_heals_a_path_nested_inside_agentic(tmp_path: Path) -> None:
    """
    @brief      Resolving from a path under `.agentic` heals to the project root.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Covers the deeper case observed in practice: any path segment
                below `.agentic`, such as `.agentic/cli/src`, resolves upward
                to the directory that contains `.agentic` instead of exiting.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    nested = tmp_path / ".agentic" / "cli" / "src"
    nested.mkdir(parents=True)

    assert repo_root_from(nested) == tmp_path.resolve()


def test_reject_guard_still_refuses_agentic_roots_directly(tmp_path: Path) -> None:
    """
    @brief      The safety-net guard itself still rejects `.agentic` roots.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    Discovery makes the guard unreachable for paths that exist on
                disk (the parent containing `.agentic` always wins first), but
                it remains the last line of defense for nonexistent-path
                fallbacks, so it is covered at unit level here.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    with pytest.raises(SystemExit, match=r"Refusing to use.*\.agentic"):
        _reject_nested_agentic_root(tmp_path / ".agentic")
    with pytest.raises(SystemExit, match=r"Refusing to use.*\.agentic"):
        _reject_nested_agentic_root(tmp_path / ".agentic" / "cli" / "src")


def test_repo_root_from_accepts_a_normal_project_root(tmp_path: Path) -> None:
    """
    @brief      A marked project root resolves to itself.
    @param[in]  tmp_path Pytest-provided temporary directory.
    @return     None.
    @details    The root carries a `.git` marker so the resolution is
                deterministic regardless of any repository markers above the
                pytest temp directory on the host machine.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    project_root = tmp_path / "my-project"
    (project_root / ".git").mkdir(parents=True)

    assert repo_root_from(project_root) == project_root.resolve()


def test_start_publishes_exact_workspace_pointer_without_cache(tmp_path: Path) -> None:
    """
    @brief      Starting a run creates only state and an LF pointer.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    graph = init_graph(tmp_path, "feature", "Workspace-local state")

    pointer = current_run_path(tmp_path)
    assert pointer == tmp_path / ".agentic" / ".workspace" / "state" / "current_run"
    assert pointer.read_bytes() == f"{graph.run_id}\n".encode("utf-8")
    assert not (workspace_root(tmp_path) / "cache").exists()
    assert resolve_run_id(tmp_path) == graph.run_id


def test_old_pointer_is_ignored_even_when_it_names_a_valid_run(tmp_path: Path) -> None:
    """
    @brief      The retired `.agentic/current_run` path is never a fallback.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    graph = init_graph(tmp_path, "feature", "Ignore old pointer")
    current_run_path(tmp_path).unlink()
    old_pointer = tmp_path / ".agentic" / "current_run"
    old_pointer.write_text(f"{graph.run_id}\n", encoding="utf-8", newline="\n")

    with pytest.raises(RunResolutionError) as raised:
        resolve_run_id(tmp_path)

    assert raised.value.code == "RUN-POINTER-MISSING"
    assert raised.value.pointer_path == ".agentic/.workspace/state/current_run"


@pytest.mark.parametrize("content", [b"", b" \n", b"feature-invalid\n", b"feature-2026-02-30T120000Z-12345678\n", b"feature-2026-07-22T120000Z-12345678\r\n"])
def test_invalid_pointer_content_has_stable_error(tmp_path: Path, content: bytes) -> None:
    """
    @brief      Empty, malformed, impossible-date, and non-LF pointers fail.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  content Exact pointer bytes under test.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    pointer = current_run_path(tmp_path)
    pointer.parent.mkdir(parents=True)
    pointer.write_bytes(content)

    with pytest.raises(RunResolutionError) as raised:
        resolve_run_id(tmp_path)

    assert raised.value.code == "RUN-POINTER-INVALID"
    assert raised.value.run_id is None
    assert str(raised.value).startswith("RUN-POINTER-INVALID:")


def test_stale_and_mismatched_pointer_graphs_are_actionable(tmp_path: Path) -> None:
    """
    @brief      Missing and identity-mismatched graphs are stale selections.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    run_id = "feature-2026-07-22T120000Z-12345678"
    pointer = current_run_path(tmp_path)
    pointer.parent.mkdir(parents=True)
    pointer.write_text(f"{run_id}\n", encoding="utf-8", newline="\n")

    with pytest.raises(RunResolutionError) as missing:
        resolve_run_id(tmp_path)
    assert missing.value.code == "RUN-POINTER-STALE"
    assert missing.value.run_id == run_id

    graph = init_graph(tmp_path, "fix", "Different run")
    target = tmp_path / ".agentic" / "runs" / run_id / "graph.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(graph.to_dict(), sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    pointer.write_text(f"{run_id}\n", encoding="utf-8", newline="\n")
    with pytest.raises(RunResolutionError) as mismatch:
        resolve_run_id(tmp_path)
    assert mismatch.value.code == "RUN-POINTER-STALE"


def test_explicit_run_precedes_pointer_without_mutating_it(tmp_path: Path) -> None:
    """
    @brief      Explicit selection wins and leaves worktree state unchanged.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    pointer_graph = init_graph(tmp_path, "feature", "Pointer run")
    explicit_graph = init_graph(tmp_path, "fix", "Explicit run")
    store.write_current_run(tmp_path, pointer_graph.run_id)
    before = current_run_path(tmp_path).read_bytes()

    selected = resolve_run_id(tmp_path, explicit_graph.run_id)

    assert selected == explicit_graph.run_id
    assert load_graph(tmp_path, selected).intent.statement == "Explicit run"
    assert current_run_path(tmp_path).read_bytes() == before


def test_invalid_explicit_run_never_falls_back_to_pointer(tmp_path: Path) -> None:
    """
    @brief      A malformed explicit ID does not use a valid local pointer.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    init_graph(tmp_path, "feature", "Pointer run")

    with pytest.raises(RunResolutionError) as raised:
        resolve_run_id(tmp_path, "../escape")

    assert raised.value.code == "RUN-ID-NOT-FOUND"
    assert raised.value.pointer_path is None
    assert raised.value.run_id is None


def test_failed_initial_graph_save_never_selects_the_run(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Pointer publication happens only after graph persistence.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """

    def fail_save(_repo_root: Path, _graph) -> None:  # type: ignore[no-untyped-def]
        """@brief Simulate an initial graph persistence failure."""
        raise OSError("simulated graph failure")

    monkeypatch.setattr(store, "save_graph", fail_save)
    with pytest.raises(OSError, match="simulated graph failure"):
        init_graph(tmp_path, "feature", "Failed start")

    assert not current_run_path(tmp_path).exists()
    assert not workspace_root(tmp_path).exists()


def test_failed_pointer_replacement_preserves_previous_selection(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      Atomic publication keeps the prior pointer on replace failure.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    first = init_graph(tmp_path, "feature", "First selection")

    def fail_replace(_source: Path, _destination: Path) -> None:
        """@brief Simulate an atomic pointer replacement failure."""
        raise OSError("simulated pointer failure")

    monkeypatch.setattr(store.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated pointer failure"):
        init_graph(tmp_path, "fix", "Unpublished selection")

    assert current_run_path(tmp_path).read_bytes() == f"{first.run_id}\n".encode("utf-8")


def test_invalid_json_graph_is_reported_as_stale_pointer(tmp_path: Path) -> None:
    """
    @brief      A selected graph with invalid JSON is stale, never guessed.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    graph = init_graph(tmp_path, "feature", "Invalid JSON")
    path = tmp_path / ".agentic" / "runs" / graph.run_id / "graph.json"
    path.write_text("{invalid\n", encoding="utf-8", newline="\n")

    with pytest.raises(RunResolutionError) as raised:
        resolve_run_id(tmp_path)

    assert raised.value.code == "RUN-POINTER-STALE"
    assert raised.value.run_id == graph.run_id


def test_two_worktrees_keep_independent_active_pointers(tmp_path: Path) -> None:
    """
    @brief      Linked Git worktrees select independent active runs.
    @param[in]  tmp_path Temporary parent directory.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    first_root = tmp_path / "worktree-one"
    second_root = tmp_path / "worktree-two"
    first_root.mkdir()
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=first_root, check=True)
    subprocess.run(["git", "config", "user.name", "AEGIS Test"], cwd=first_root, check=True)
    subprocess.run(["git", "config", "user.email", "aegis@example.invalid"], cwd=first_root, check=True)
    (first_root / ".gitignore").write_text(
        ".agentic/.workspace/\n",
        encoding="utf-8",
        newline="\n",
    )
    (first_root / "README.md").write_text("fixture\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", ".gitignore", "README.md"], cwd=first_root, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "fixture"], cwd=first_root, check=True)
    subprocess.run(
        ["git", "worktree", "add", "--quiet", "-b", "linked", str(second_root)],
        cwd=first_root,
        check=True,
    )
    first = init_graph(first_root, "feature", "First worktree")
    second = init_graph(second_root, "fix", "Second worktree")

    assert resolve_run_id(first_root) == first.run_id
    assert resolve_run_id(second_root) == second.run_id
    assert current_run_path(first_root).read_bytes() != current_run_path(second_root).read_bytes()


def test_started_pointer_is_invisible_to_git_status(tmp_path: Path) -> None:
    """
    @brief      Starting a run does not expose workspace state to Git.
    @param[in]  tmp_path Temporary Git repository root.
    @return     None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    subprocess.run(
        ["git", "init", "--quiet", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    (tmp_path / ".gitignore").write_text(
        ".agentic/.workspace/\n",
        encoding="utf-8",
        newline="\n",
    )

    init_graph(tmp_path, "feature", "Ignored pointer")

    status = subprocess.run(
        ["git", "status", "--porcelain", "--", ".agentic/.workspace"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert status.stdout == ""


# END OF FILE
