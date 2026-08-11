#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Test IP-17 reproducible archives without claiming unavailable runtimes."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

from aegis_release.archives import BuildError, build_archive
from aegis_release.inspection import InspectionError, inspect_archive

REPOSITORY = Path(__file__).parents[3]
RUNTIME_INPUTS = REPOSITORY / "05_Software/release_tools/runtime_inputs.toml"


def test_release_module_exposes_local_tool_help() -> None:
    """IP-17: The package module is an executable local tooling entry point."""
    completed = subprocess.run(
        [sys.executable, "-m", "aegis_release", "--help"],
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0
    assert b"build" in completed.stdout
    assert b"inspect" in completed.stdout


def test_dependency_excluding_archives_are_reproducible_and_exact(
    tmp_path: Path,
) -> None:
    """Build/inspect both products for both declared platform archive shapes."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    for product in ("aegis", "waegis"):
        for platform in ("windows-x86_64", "ubuntu-22.04-x86_64"):
            left = build_archive(
                REPOSITORY,
                first,
                product=product,
                platform=platform,
                with_dependencies=False,
                runtime_lock=RUNTIME_INPUTS,
            )
            right = build_archive(
                REPOSITORY,
                second,
                product=product,
                platform=platform,
                with_dependencies=False,
                runtime_lock=RUNTIME_INPUTS,
            )
            assert (
                hashlib.sha256(left.read_bytes()).digest()
                == hashlib.sha256(right.read_bytes()).digest()
            )
            report = inspect_archive(left)
            assert report["product"] == product
            assert report["platform"] == platform
            assert report["with_dependencies"] is False
            assert report["file_count"] > 5


def test_dependency_including_build_refuses_unsupplied_runtime_inputs(
    tmp_path: Path,
) -> None:
    """Never fabricate private Python/Git inputs or a completed bundled archive."""
    with pytest.raises(BuildError, match="not supplied"):
        build_archive(
            REPOSITORY,
            tmp_path,
            product="waegis",
            platform="windows-x86_64",
            with_dependencies=True,
            runtime_lock=RUNTIME_INPUTS,
        )
    assert not list(tmp_path.glob("*.zip"))


def test_dependency_including_seam_embeds_only_exact_locked_runtime_archives(
    tmp_path: Path,
) -> None:
    """Exercise the build seam with synthetic inputs without claiming runtimes work."""
    python_input = tmp_path / "python.zip"
    git_input = tmp_path / "git.zip"
    with zipfile.ZipFile(python_input, "w") as bundle:
        bundle.writestr("python.exe", b"synthetic locked Python input")
    with zipfile.ZipFile(git_input, "w") as bundle:
        bundle.writestr("cmd/git.exe", b"synthetic locked Git input")
    lock = tmp_path / "runtime-inputs.toml"
    lock.write_text(
        'schema = 1\nstatus = "synthetic_test_inputs"\n\n'
        '[[inputs]]\nplatform = "windows-x86_64"\ncomponent = "python"\n'
        'supplied = true\nversion = "3.12.99-synthetic"\n'
        f'sha256 = "{hashlib.sha256(python_input.read_bytes()).hexdigest()}"\n'
        f'archive_path = "{python_input.as_posix()}"\n\n'
        '[[inputs]]\nplatform = "windows-x86_64"\ncomponent = "git"\n'
        'supplied = true\nversion = "9.9.9-synthetic"\n'
        f'sha256 = "{hashlib.sha256(git_input.read_bytes()).hexdigest()}"\n'
        f'archive_path = "{git_input.as_posix()}"\n',
        encoding="utf-8",
    )
    assert tomllib.loads(lock.read_text())["status"] == "synthetic_test_inputs"

    for product, prefix in (
        ("aegis", ".agentic/aegis/"),
        ("waegis", ""),
    ):
        archive = build_archive(
            REPOSITORY,
            tmp_path / "output",
            product=product,
            platform="windows-x86_64",
            with_dependencies=True,
            runtime_lock=lock,
        )
        report = inspect_archive(archive)
        assert report["with_dependencies"] is True
        with zipfile.ZipFile(archive) as bundle:
            assert f"{prefix}runtime/python/python.exe" in bundle.namelist()
            assert f"{prefix}runtime/git/cmd/git.exe" in bundle.namelist()
            inventory = json.loads(bundle.read("ARCHIVE_INVENTORY.json"))
            assert inventory["protocol_version"] == 1
            assert inventory["python_version"] == "3.12.99-synthetic"
            assert inventory["git_version"] == "9.9.9-synthetic"
            assert all(entry["ownership"] for entry in inventory["files"])


def test_archive_relocates_and_runs_first_operations_with_external_python(
    tmp_path: Path,
) -> None:
    """Exercise current-host extraction without implying Ubuntu host acceptance."""
    for product in ("aegis", "waegis"):
        archive = build_archive(
            REPOSITORY,
            tmp_path / "archives",
            product=product,
            platform="windows-x86_64",
            with_dependencies=False,
            runtime_lock=RUNTIME_INPUTS,
        )
        relocated = tmp_path / f"relocated-{product}"
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(relocated)
        launcher = (
            relocated / ".agentic/aegis/bin/launcher.py"
            if product == "aegis"
            else relocated / "bin/launcher.py"
        )
        completed = subprocess.run(
            [sys.executable, str(launcher), "--format", "json", "version-show"],
            cwd=relocated,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr.decode(errors="replace")
        response = json.loads(completed.stdout.decode("utf-8"))
        assert response["schema"] == "aegis.machine.response"
        assert response["product"].lower() == product


def test_inspector_rejects_traversal_and_uninventoried_content(tmp_path: Path) -> None:
    """Reject unsafe or non-inventory archive content before extraction."""
    hostile = tmp_path / "hostile.zip"
    with zipfile.ZipFile(hostile, "w") as bundle:
        bundle.writestr("../escape.txt", "unsafe")
    with pytest.raises(InspectionError, match="unsafe"):
        inspect_archive(hostile)

    archive = build_archive(
        REPOSITORY,
        tmp_path / "archives",
        product="aegis",
        platform="windows-x86_64",
        with_dependencies=False,
        runtime_lock=RUNTIME_INPUTS,
    )
    changed = tmp_path / "changed.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(changed, "w") as output:
        for info in source.infolist():
            output.writestr(info, source.read(info.filename))
        output.writestr("unlisted.txt", "not inventoried")
    with pytest.raises(InspectionError, match="inventory"):
        inspect_archive(changed)
