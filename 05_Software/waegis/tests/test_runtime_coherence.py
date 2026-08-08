#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_runtime_coherence.py
@brief Tests that mutation validation uses the registered AEGIS interpreter.
@details Covers both new-install and existing-repository publication boundaries
         with an interpreter path distinct from the WAEGIS process runtime.
"""

# IMPORTS

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

import pytest

import waegis.install as install
import waegis.publication as publication
from waegis.gitsafety import build_recovery_plan
from waegis.install import InstallPlan
from waegis.manifest import MANIFEST_PATH, InstallManifest
from waegis.publication import PublicationPlan
from waegis.runner import CommandResult, CommandRunner


# DATA MODELS / TYPEDEFINITIONS


class ValidationRunner:
    """@brief Delegate Git commands and emulate successful AEGIS wrappers."""

    def __init__(self) -> None:
        self._commands = CommandRunner()
        self.validation_environments: list[Mapping[str, str] | None] = []

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        """@brief Run Git for real and capture each emulated wrapper environment."""
        if args[0] == "git":
            return self._commands.run(args, cwd=cwd, timeout=timeout, env=env)
        command = tuple(str(item) for item in args)
        self.validation_environments.append(env)
        stdout = ""
        if "--json" in args:
            stdout = '{"status":"ok","stage":null,"artifact":null,"next":null}'
        return CommandResult(command, 0, stdout, "")


# HELPER FUNCTIONS


def _manifest(mode: str) -> InstallManifest:
    return InstallManifest(
        payload_version="3.0.0",
        payload_digest="0" * 64,
        installed_at="2026-08-08T00:00:00Z",
        installed_by="waegis 3.0.0",
        mode=mode,
        files={},
        configuration={},
    )


def _git(repository: Path, *args: str) -> None:
    subprocess.run(("git", "-C", str(repository), *args), check=True, capture_output=True, text=True)


def _assert_registered_runtime_used(runner: ValidationRunner, selected: Path) -> None:
    assert runner.validation_environments == [{"AEGIS_PYTHON": str(selected)}] * 3


# EXPORTED FUNCTIONS / PUBLIC API


def test_install_validation_uses_registered_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """@brief D7 validate a new install with the exact registered interpreter."""
    target = tmp_path / "new-repository"
    selected = tmp_path / "registered-python"
    selected.touch()
    runner = ValidationRunner()
    plan = InstallPlan("new", target, "3.0.0", "0" * 64, {}, {}, (), None, False)
    monkeypatch.setattr(install, "register_runtime", lambda _runner: selected)

    install.apply_install(plan, runner, io.StringIO(), as_json=False)

    _assert_registered_runtime_used(runner, selected)


def test_existing_publication_validation_uses_registered_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief D7 validate an existing repository with its registered interpreter."""
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "init")
    _git(repository, "config", "user.email", "tests@example.invalid")
    _git(repository, "config", "user.name", "WAEGIS Tests")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    runner = ValidationRunner()
    recovery = build_recovery_plan(runner, repository, (MANIFEST_PATH,))
    plan = PublicationPlan("repair", repository, {}, (), recovery, _manifest("repair"))
    selected = tmp_path / "registered-python"
    selected.touch()
    monkeypatch.setattr(publication, "register_runtime", lambda _runner: selected)

    publication.apply_publication(plan, runner, io.StringIO(), as_json=False)

    _assert_registered_runtime_used(runner, selected)


# END OF FILE
