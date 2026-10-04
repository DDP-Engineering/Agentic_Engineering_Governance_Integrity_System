#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_system_programs.py
@brief The CLI starts Git and taskkill from PATH, never from the repository.
@details Windows searches the working directory before PATH unless
         `NoDefaultCurrentDirectoryInExePath` is set, and some environments
         (this one included) set it - so every test removes the variable,
         works from the repository root, and plants a fake program there.
         The Windows fake is a copy of `hostname.exe`; the POSIX fake is a
         script, reached through a relative PATH entry as POSIX would.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import itertools
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# CONSTANTS

PAYLOAD = Path(__file__).resolve().parents[1] / "template" / ".agentic"
_COUNTER = itertools.count()
SEARCH_GUARD = "NoDefaultCurrentDirectoryInExePath"

# HELPER FUNCTIONS


def load_payload(root: Path):
    """@brief Copy the payload under root and import that copy's aegis.py."""
    shutil.copytree(PAYLOAD, root / ".agentic")
    spec = importlib.util.spec_from_file_location(f"aegis_programs_{next(_COUNTER)}",
                                                  root / ".agentic" / "aegis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plant_fake(folder: Path, name: str) -> Path:
    """@brief A program called name in folder that is plainly not the real one."""
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        target = folder / f"{name}.exe"
        system = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
        shutil.copy2(system / "hostname.exe", target)
    else:
        target = folder / name
        target.write_text("#!/bin/sh\necho FAKE-PROGRAM\n", encoding="utf-8")
        target.chmod(0o755)
    return target


@pytest.fixture()
def exposed(tmp_path: Path, monkeypatch):
    """@brief A repository root as working directory, with the search guard removed."""
    monkeypatch.delenv(SEARCH_GUARD, raising=False)
    monkeypatch.chdir(tmp_path)
    if sys.platform != "win32":
        # POSIX searches only PATH; a relative entry is how a repository copy is reached
        monkeypatch.setenv("PATH", "." + os.pathsep + os.environ.get("PATH", ""))
    return tmp_path

# TESTS (REQ-SEC-283dff37)


def test_git_comes_from_path_not_from_the_repository(exposed: Path):
    """REQ-SEC-283dff37: a git program in the repository root never runs."""
    aegis = load_payload(exposed)
    plant_fake(exposed, "git")
    out = aegis.run_git("--version")
    assert out is not None and out[1].startswith("git version"), out


def test_git_reachable_only_inside_the_repository_is_unavailable(exposed: Path, monkeypatch):
    """REQ-SEC-283dff37: repository, relative and empty PATH entries are skipped."""
    aegis = load_payload(exposed)
    plant_fake(exposed / "tools", "git")
    monkeypatch.setenv("PATH", os.pathsep.join([str(exposed / "tools"), "", "tools"]))
    assert aegis.run_git("--version") is None


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0,
                    reason="POSIX folder permissions, as a non-root user")
def test_a_path_folder_that_cannot_be_read_is_skipped(exposed: Path, monkeypatch,
                                                      tmp_path_factory):
    """REQ-SEC-283dff37: an unreadable PATH folder is passed over, not a crash."""
    aegis = load_payload(exposed)
    locked = tmp_path_factory.mktemp("locked")
    locked.chmod(0)
    monkeypatch.setenv("PATH", str(locked) + os.pathsep + os.environ.get("PATH", ""))
    try:
        out = aegis.run_git("--version")
    finally:
        locked.chmod(0o755)
    assert out is not None and out[1].startswith("git version"), out


def test_a_path_entry_inside_the_repository_is_skipped_even_for_a_link(exposed: Path,
                                                                       monkeypatch):
    """REQ-SEC-283dff37: a repository folder on PATH is never used, whatever its links point to."""
    aegis = load_payload(exposed)
    real = shutil.which("git")
    tools = exposed / "tools"
    tools.mkdir()
    try:
        os.symlink(real, tools / ("git.exe" if sys.platform == "win32" else "git"))
    except (OSError, NotImplementedError):
        pytest.skip("creating links needs a privilege on this machine")
    monkeypatch.setenv("PATH", str(tools))
    assert aegis.system_program("git") is None


@pytest.mark.skipif(sys.platform != "win32", reason="batch files exist on Windows only")
def test_a_batch_file_is_never_taken_for_the_program(exposed: Path, monkeypatch,
                                                     tmp_path_factory):
    """REQ-SEC-283dff37: only `git.exe` qualifies; `cmd.exe` would re-parse a batch file's arguments."""
    aegis = load_payload(exposed)
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    (elsewhere / "git.cmd").write_text("@echo FAKE-PROGRAM\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(elsewhere) + os.pathsep + os.environ.get("PATH", ""))
    program = aegis.system_program("git")
    assert program is not None and program.lower().endswith("git.exe"), program


@pytest.mark.skipif(sys.platform != "win32", reason="taskkill exists on Windows only")
def test_taskkill_comes_from_path_not_from_the_repository(exposed: Path, monkeypatch):
    """REQ-SEC-283dff37: the tree kill runs the system taskkill by its absolute path."""
    aegis = load_payload(exposed)
    plant_fake(exposed, "taskkill")
    launched: list[str] = []
    real_run = subprocess.run

    def recording(command, *args, **kwargs):
        launched.append(command[0])
        return real_run(command, *args, **kwargs)
    monkeypatch.setattr(subprocess, "run", recording)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert aegis.kill_tree(proc) is True
    finally:
        proc.kill()
        proc.wait(10)
    program = Path(launched[0])
    assert program.is_absolute(), launched
    assert not program.resolve().is_relative_to(exposed.resolve()), launched

# END OF FILE
