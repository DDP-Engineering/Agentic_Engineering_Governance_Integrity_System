#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_scope.py
@brief Scope selection, inventory and manifest discovery.
@details Covers REQ-FUNC-baa92928 (selection with the AEGIS layout rules),
         REQ-FUNC-43a76b41 (missing scope), REQ-FUNC-3a18929b (Git or
         filesystem inventory) and REQ-FUNC-c7ece57c (project manifests
         outside the selected sources). The matcher contract table runs
         against both CodeGraph and the AEGIS CLI so the two cannot drift.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

import pytest
from conftest import PLUGIN_ROOT, git

from codegraph import config, scope

# CONSTANTS

AEGIS_PY = PLUGIN_ROOT.parents[1] / "template" / ".agentic" / "aegis.py"

#: (path, pattern, expected) shared by both matchers
MATCH_CASES = [
    ("src/a.py", "src/", True),
    ("src", "src/", True),
    ("srcx/a.py", "src/", False),
    ("src/a.py", "src", True),
    ("src/sub/a.py", "src", True),
    ("srcx/a.py", "src", False),
    ("src/a.py", "src/*.py", True),
    ("src/sub/a.py", "src/*.py", True),
    ("src/a.PY", "src/*.py", False),
    ("Src/a.py", "src/", False),
    ("src/a1.py", "src/a?.py", True),
    ("src/ab.py", "src/a[0-9].py", False),
    ("src/a.py", "src/a.py", True),
    ("src/a.pyc", "src/a.py", False),
]

# HELPER FUNCTIONS


def aegis_module():
    """@brief Import the canonical AEGIS CLI module without running it."""
    spec = importlib.util.spec_from_file_location("aegis_for_matcher", AEGIS_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def settings_for(root: Path, body: str) -> config.Settings:
    """@brief Write aegis.toml under root and load its settings."""
    path = root / ".agentic" / "aegis.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return config.load(root)


def touch(root: Path, *names: str, text: str = "x = 1\n") -> None:
    """@brief Create files with small content."""
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def init_repo(root: Path) -> None:
    """@brief Initialise a Git repository with a deterministic identity."""
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "config", "core.autocrlf", "false")


def selected_paths(settings: config.Settings) -> list[str]:
    """@brief Paths of the files selected for indexing."""
    return [item.path for item in scope.select(settings).files]

# TESTS - selection (REQ-FUNC-baa92928)


@pytest.mark.parametrize("path, pattern, expected", MATCH_CASES)
def test_matcher_agrees_with_the_aegis_cli(path: str, pattern: str, expected: bool):
    """REQ-FUNC-baa92928: identical directory-prefix and glob semantics."""
    assert scope.match_path(path, pattern) is expected
    assert aegis_module().match_path(path, pattern) is expected


def test_selection_applies_layout_include_and_exclusions(tmp_path: Path):
    """REQ-FUNC-baa92928: exclude wins; dependency folders and root .agentic stay out."""
    touch(tmp_path, "src/app.py", "src/gen/auto.py", "tests/test_app.py", "tools/t.py",
          "node_modules/pkg/index.py", "src/__pycache__/x.py", ".agentic/aegis.py",
          "05_Software/aegis/template/.agentic/aegis.py", "docs/readme.py")
    settings = settings_for(tmp_path, (
        '[layout]\nsource = ["src/", "src/", "05_Software/"]\ntests = ["tests/"]\n'
        '[codegraph]\ninclude = ["tools/", "node_modules/"]\nexclude = ["src/gen/", "tools/"]\n'))
    assert selected_paths(settings) == [
        "05_Software/aegis/template/.agentic/aegis.py", "src/app.py", "tests/test_app.py"]


def test_test_files_are_dropped_when_tests_are_not_indexed(tmp_path: Path):
    """REQ-FUNC-baa92928: index_tests = false removes test files from scope."""
    touch(tmp_path, "pkg/core.py", "pkg/tests/test_core.py")
    settings = settings_for(tmp_path, (
        '[layout]\nsource = ["pkg/"]\ntests = ["pkg/tests/"]\n'
        '[codegraph]\nindex_tests = false\n'))
    assert selected_paths(settings) == ["pkg/core.py"]


def test_roles_languages_and_skip_reasons(tmp_path: Path):
    """REQ-FUNC-baa92928: roles, languages and skips are classified separately."""
    touch(tmp_path, "src/a.py", "src/b.pyi", "src/notes.md", "tests/test_a.py")
    (tmp_path / "src" / "big.py").write_text("x = 1\n" * 50, encoding="utf-8")
    (tmp_path / "src" / "blob.py").write_bytes(b"\x00\x01binary")
    settings = settings_for(tmp_path, (
        '[layout]\nsource = ["src/"]\ntests = ["tests/"]\n'
        '[codegraph]\nmax_file_bytes = 100\n'))
    selection = scope.select(settings)
    files = {item.path: (item.role, item.language) for item in selection.files}
    assert files == {"src/a.py": ("source", "python"), "src/b.pyi": ("source", "python"),
                     "tests/test_a.py": ("test", "python")}
    assert selection.skipped == {"src/big.py": "too-large", "src/blob.py": "binary",
                                 "src/notes.md": "unsupported"}

# TESTS - missing scope (REQ-FUNC-43a76b41)


def test_empty_layout_reports_scope_missing(tmp_path: Path):
    """REQ-FUNC-43a76b41: no patterns means no scan at all."""
    touch(tmp_path, "src/a.py")
    settings = settings_for(tmp_path, "[codegraph]\nenabled = true\n")
    with pytest.raises(scope.ScopeError) as caught:
        scope.select(settings)
    assert caught.value.reason == "scope_missing"
    assert "[layout]" in str(caught.value)


def test_include_alone_is_a_scope(tmp_path: Path):
    """REQ-FUNC-43a76b41: include by itself is enough to select files."""
    touch(tmp_path, "lib/a.py")
    settings = settings_for(tmp_path, '[codegraph]\ninclude = ["lib/"]\n')
    assert selected_paths(settings) == ["lib/a.py"]

# TESTS - inventory (REQ-FUNC-3a18929b)


def test_git_inventory_lists_tracked_and_untracked_visible_files(tmp_path: Path):
    """REQ-FUNC-3a18929b: ignored and deleted files never appear."""
    init_repo(tmp_path)
    touch(tmp_path, "src/kept.py", "src/gone.py", "src/new.py", "src/ignored.py")
    (tmp_path / ".gitignore").write_text("src/ignored.py\n", encoding="utf-8")
    git(tmp_path, "add", "src/kept.py", "src/gone.py", ".gitignore")
    git(tmp_path, "commit", "-q", "-m", "fixture")
    (tmp_path / "src" / "gone.py").unlink()
    settings = settings_for(tmp_path, '[layout]\nsource = ["src/"]\n')
    assert scope.inventory(settings).mode == "git"
    assert selected_paths(settings) == ["src/kept.py", "src/new.py"]
    settings = settings_for(tmp_path, '[layout]\nsource = ["src/"]\n'
                                      '[codegraph]\ninclude_untracked = false\n')
    assert selected_paths(settings) == ["src/kept.py"]


def test_plain_folder_uses_a_pruned_filesystem_walk(tmp_path: Path):
    """REQ-FUNC-3a18929b: outside Git the scoped folders are walked."""
    touch(tmp_path, "src/a.py", "src/node_modules/x.py", "src/.venv/y.py", "other/z.py")
    settings = settings_for(tmp_path, '[layout]\nsource = ["src/"]\n')
    inventory = scope.inventory(settings)
    assert inventory.mode == "filesystem"
    assert "other/z.py" not in inventory.paths
    assert selected_paths(settings) == ["src/a.py"]


def test_missing_git_falls_back_to_the_filesystem(tmp_path: Path, monkeypatch):
    """REQ-FUNC-3a18929b: no Git executable means a filesystem walk."""
    init_repo(tmp_path)
    touch(tmp_path, "src/a.py")
    monkeypatch.setattr(scope, "GIT", "git-executable-that-does-not-exist")
    settings = settings_for(tmp_path, '[layout]\nsource = ["src/"]\n')
    assert scope.inventory(settings).mode == "filesystem"


def test_failing_git_listing_is_an_error_not_a_wider_scan(tmp_path: Path):
    """REQ-FUNC-3a18929b: a broken repository never widens the scope."""
    init_repo(tmp_path)
    touch(tmp_path, "src/a.py")
    git(tmp_path, "add", "src/a.py")
    git(tmp_path, "commit", "-q", "-m", "fixture")
    (tmp_path / ".git" / "index").write_bytes(b"corrupt index")
    settings = settings_for(tmp_path, '[layout]\nsource = ["src/"]\n')
    with pytest.raises(scope.ScopeError) as caught:
        scope.inventory(settings)
    assert caught.value.reason == "inventory_failed"

# TESTS - manifests (REQ-FUNC-c7ece57c)


def test_manifests_in_ancestor_folders_are_recorded_without_symbols(tmp_path: Path):
    """REQ-FUNC-c7ece57c: root and package manifests count; excluded ones do not."""
    init_repo(tmp_path)
    touch(tmp_path, "pkg/src/shop/orders.py", "pkg/vendored/x.py")
    touch(tmp_path, "pyproject.toml", "pkg/pyproject.toml", "pkg/vendored/pyproject.toml",
          text="[project]\nname = 'x'\n")
    settings = settings_for(tmp_path, (
        '[layout]\nsource = ["pkg/src/", "pkg/vendored/"]\n'
        '[codegraph]\nexclude = ["pkg/vendored/"]\n'))
    selection = scope.select(settings)
    assert [item.path for item in selection.files] == ["pkg/src/shop/orders.py"]
    assert sorted(selection.manifests) == ["pkg/pyproject.toml", "pyproject.toml"]
    digests = scope.manifest_hashes(settings, selection.manifests)
    assert set(digests) == {"pkg/pyproject.toml", "pyproject.toml"}
    assert all(len(value) == 64 for value in digests.values())


def test_report_counts_selection_and_skips(tmp_path: Path):
    """REQ-FUNC-c7ece57c: the scope report lists manifests with the totals."""
    touch(tmp_path, "src/a.py", "src/b.md", "pyproject.toml")
    settings = settings_for(tmp_path, '[layout]\nsource = ["src/"]\n')
    report = scope.report(settings)
    assert report["inventory"] == "filesystem"
    assert report["totals"]["files"] == 1
    assert report["by_language"] == {"python": 1}
    assert report["by_role"] == {"source": 1}
    assert report["skipped"] == {"unsupported": 1}
    assert report["manifests"] == ["pyproject.toml"]
    assert report["patterns"]["source"] == ["src/"]
    assert os.path.isfile(tmp_path / "src" / "a.py")

# TESTS - Git from PATH only (REQ-SEC-8960c937)


def plant_fake_git(folder: Path) -> None:
    """@brief A program called git in folder that is plainly not Git."""
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        system = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
        shutil.copy2(system / "hostname.exe", folder / "git.exe")
    else:
        fake = folder / "git"
        fake.write_text("#!/bin/sh\necho FAKE-PROGRAM\n", encoding="utf-8")
        fake.chmod(0o755)


@pytest.fixture()
def exposed_repo(tmp_path: Path, monkeypatch) -> Path:
    """@brief A Git work tree as working directory, search guard removed, fake git in its root."""
    from conftest import make_repo
    root = make_repo(tmp_path / "repo", {"src/a.py": "x = 1\n"}, use_git=True)
    plant_fake_git(root)
    monkeypatch.delenv("NoDefaultCurrentDirectoryInExePath", raising=False)
    monkeypatch.chdir(root)
    if sys.platform != "win32":
        monkeypatch.setenv("PATH", "." + os.pathsep + os.environ.get("PATH", ""))
    return root


def test_git_comes_from_path_not_from_the_repository(exposed_repo: Path):
    """REQ-SEC-8960c937: inventory and the Git precondition use the real Git."""
    from codegraph import safety
    settings = config.load(exposed_repo)
    assert scope.inventory(settings).mode == "git"
    assert scope.report(settings)["inventory"] == "git"
    state = safety.destination_state(settings)
    assert state["repository"] is True and state["ignored"] is True


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0,
                    reason="POSIX folder permissions, as a non-root user")
def test_a_path_folder_that_cannot_be_read_is_skipped(exposed_repo: Path, monkeypatch,
                                                      tmp_path_factory):
    """REQ-SEC-8960c937: an unreadable PATH folder is passed over, not a crash."""
    from codegraph import programs
    locked = tmp_path_factory.mktemp("locked")
    locked.chmod(0)
    monkeypatch.setenv("PATH", str(locked) + os.pathsep + os.environ.get("PATH", ""))
    try:
        found = programs.find("git", exposed_repo)
    finally:
        locked.chmod(0o755)
    assert found is not None and not Path(found).is_relative_to(locked)


def test_a_path_entry_inside_the_repository_is_skipped_even_for_a_link(exposed_repo: Path,
                                                                       monkeypatch):
    """REQ-SEC-8960c937: a repository folder on PATH is never used, whatever its links point to."""
    from codegraph import programs
    real = shutil.which("git", path=os.environ.get("PATH", "").replace("." + os.pathsep, "", 1))
    tools = exposed_repo / "linked"
    tools.mkdir()
    try:
        os.symlink(real, tools / ("git.exe" if sys.platform == "win32" else "git"))
    except (OSError, NotImplementedError):
        pytest.skip("creating links needs a privilege on this machine")
    monkeypatch.setenv("PATH", str(tools))
    assert programs.find("git", exposed_repo) is None


def test_git_reachable_only_inside_the_repository_is_not_used(exposed_repo: Path, monkeypatch):
    """REQ-SEC-8960c937: repository, relative and empty PATH entries are skipped."""
    from codegraph import programs
    plant_fake_git(exposed_repo / "tools")
    monkeypatch.setenv("PATH", os.pathsep.join([str(exposed_repo / "tools"), "", "tools"]))
    assert programs.find("git", exposed_repo) is None
    assert scope.inventory(config.load(exposed_repo)).mode == "filesystem"


@pytest.mark.skipif(sys.platform != "win32", reason="batch files exist on Windows only")
def test_a_batch_file_is_never_taken_for_git(exposed_repo: Path, monkeypatch, tmp_path_factory):
    """REQ-SEC-8960c937: only `git.exe` qualifies; `cmd.exe` would re-parse a batch file's arguments."""
    from codegraph import programs
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    (elsewhere / "git.cmd").write_text("@echo FAKE-PROGRAM\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(elsewhere) + os.pathsep + os.environ.get("PATH", ""))
    found = programs.find("git", exposed_repo)
    assert found is not None and found.lower().endswith("git.exe"), found

# END OF FILE
