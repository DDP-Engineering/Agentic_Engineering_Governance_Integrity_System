#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_crash_recovery_matrix.py
@brief Hard-kill acceptance across every install publication boundary.
@details Executes preprinted recovery verbatim, proves exact restoration, and
         proves an immediate lock-breaking rerun succeeds for each boundary.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from waegis.manifest import load_manifest


# CONSTANTS

BOUNDARIES = (
    "after-recovery-before-write",
    "mid-copy-overwrite-and-add",
    "after-workflow-before-validation",
    "after-validation-before-manifest",
    "during-manifest-replace",
    "after-manifest-before-lock-cleanup",
)
PACKAGE_ROOT = Path(__file__).parents[1]
PYTHON = Path(getattr(sys, "_base_executable", sys.executable))
WORKER = Path(__file__).with_name("crash_publication_worker.py")


# HELPER FUNCTIONS


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("git", "-C", str(repo), *args), text=True, capture_output=True, check=True)


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tracked.txt").write_text("original\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "WAEGIS Tests")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _tree(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(item for item in repo.rglob("*") if item.is_file() and ".git" not in item.parts):
        result[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _run_recovery(repo: Path, stderr: str) -> None:
    recovery = json.loads(stderr.splitlines()[0])["waegis_recovery"]
    assert recovery["commands"]
    for command in recovery["commands"]:
        completed = subprocess.run(command, cwd=repo, shell=True, text=True, capture_output=True)
        assert completed.returncode == 0, completed.stderr


def _environment(tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["WAEGIS_HOME"] = str(tmp_path / "waegis-home")
    environment["PYTHONPATH"] = str(PACKAGE_ROOT / "src")
    return environment


# EXPORTED FUNCTIONS / PUBLIC API


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_hard_kill_restores_and_reruns_at_every_install_boundary(tmp_path: Path, boundary: str) -> None:
    """@brief R3 kill, recover, compare, and immediately rerun at one publication boundary."""
    repo = _repository(tmp_path)
    before = _tree(repo)
    signal = tmp_path / "publication-paused"
    environment = _environment(tmp_path)
    process = subprocess.Popen(
        (str(PYTHON), str(WORKER), boundary, str(signal), str(repo)),
        cwd=PACKAGE_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 30
    while not signal.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if not signal.exists():
        process.kill()
        output = process.communicate(timeout=15)
        pytest.fail(f"publication boundary was not reached: {output}")
    process.kill()
    _, stderr = process.communicate(timeout=15)
    _run_recovery(repo, stderr)
    assert _tree(repo) == before
    assert _git(repo, "status", "--porcelain", "--untracked-files=all").stdout == ""

    completed = subprocess.run(
        (str(PYTHON), str(WORKER), "complete", str(signal), str(repo), "--break-lock"),
        cwd=PACKAGE_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert load_manifest(repo / ".agentic" / "install-manifest.json").payload_version == "3.0.0"


# END OF FILE
