#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_packaging.py
@brief Zipapp, native-wrapper topology, integrity, and runtime-pointer tests.
@details Uses the real payload for zipapp execution and tiny locked-runtime
         shapes for archive-safety/native topology unit coverage.
"""

import io
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest


PROJECT = Path(__file__).parents[1]
PACKAGING = PROJECT / "packaging"
sys.path.insert(0, str(PACKAGING))

from runtime_bundle import (  # noqa: E402
    BundleError,
    RuntimeSource,
    build_linux_bundle,
    build_windows_bundle,
    load_runtime_lock,
)


def _run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(("git", "-C", str(repo), *args), check=True, capture_output=True)


def _runtime_archive(path: Path, executable: str, *, link: str | None = None) -> None:
    with tarfile.open(path, "w:gz") as archive:
        data = b"runtime\n"
        info = tarfile.TarInfo(f"python/{executable}")
        info.size = len(data)
        info.mode = 0o755
        archive.addfile(info, io.BytesIO(data))
        library = tarfile.TarInfo("python/lib/library.txt")
        library.size = len(data)
        library.mode = 0o644
        archive.addfile(library, io.BytesIO(data))
        if link:
            linked = tarfile.TarInfo("python/bin/python3")
            linked.type = tarfile.SYMTYPE
            linked.linkname = link
            archive.addfile(linked)


def _add_file(archive: tarfile.TarFile, name: str, data: bytes = b"data\n") -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(data))


def test_zipapp_runs_offline_and_registers_runtime_only_for_mutation(tmp_path: Path) -> None:
    """@brief D3 zipapp resolves one embedded payload and supports install/check/configure."""
    output = tmp_path / "dist"
    built = _run(sys.executable, str(PACKAGING / "build.py"), "--zipapp-only", "--output", str(output), cwd=PROJECT)
    assert built.returncode == 0, built.stderr
    pyz = output / "waegis.pyz"
    home = tmp_path / "home"
    environment = os.environ.copy()
    environment.update(
        {
            "WAEGIS_HOME": str(home),
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "*",
        }
    )
    version = _run(sys.executable, str(pyz), "version", "--json", cwd=tmp_path, env=environment)
    assert version.returncode == 0, version.stderr
    assert json.loads(version.stdout)["result"]["packaging_type"] == "zipapp"
    pointer = home / "runtime-python"
    assert not pointer.exists()
    target = tmp_path / "project"
    answers = tmp_path / "answers.json"
    answers.write_text(
        json.dumps(
            {
                "answers_version": 2,
                "answers": {"language": "python", "source_roots": ["src"], "test_roots": ["tests"]},
            }
        ),
        encoding="utf-8",
    )
    dry = _run(
        sys.executable,
        str(pyz),
        "new",
        str(target),
        "--answers",
        str(answers),
        "--non-interactive",
        "--dry-run",
        "--json",
        cwd=tmp_path,
        env=environment,
    )
    assert dry.returncode == 0, dry.stderr
    assert not pointer.exists()
    installed = _run(
        sys.executable,
        str(pyz),
        "new",
        str(target),
        "--answers",
        str(answers),
        "--non-interactive",
        "--yes",
        "--json",
        cwd=tmp_path,
        env=environment,
    )
    assert installed.returncode == 0, installed.stderr
    assert Path(pointer.read_text(encoding="utf-8").strip()).resolve() == Path(sys.executable).resolve()
    (target / "src").mkdir()
    (target / "tests").mkdir()
    _git(target, "config", "user.email", "tests@example.invalid")
    _git(target, "config", "user.name", "WAEGIS Tests")
    _git(target, "add", ".")
    _git(target, "commit", "-m", "installed")
    checked = _run(sys.executable, str(pyz), "check", "--repo", str(target), "--json", cwd=tmp_path, env=environment)
    assert checked.returncode == 0, checked.stdout
    pointer.write_text(str(tmp_path / "missing-python") + "\n", encoding="utf-8")
    diagnosed = _run(sys.executable, str(pyz), "check", "--repo", str(target), "--json", cwd=tmp_path, env=environment)
    assert diagnosed.returncode == 1
    findings = json.loads(diagnosed.stdout)["result"]["findings"]
    assert any(item["code"] == "RUNTIME-POINTER-INVALID" for item in findings)
    configure = tmp_path / "configure.json"
    configure.write_text(
        json.dumps({"answers_version": 2, "answers": {"source_roots": ["src", "lib"]}}),
        encoding="utf-8",
    )
    repaired = _run(
        sys.executable,
        str(pyz),
        "configure",
        "--repo",
        str(target),
        "--answers",
        str(configure),
        "--non-interactive",
        "--yes",
        "--json",
        cwd=tmp_path,
        env=environment,
    )
    assert repaired.returncode == 0, repaired.stdout
    assert Path(pointer.read_text(encoding="utf-8").strip()).resolve() == Path(sys.executable).resolve()


def test_release_verifier_detects_changed_artifact_byte(tmp_path: Path) -> None:
    """@brief D3 published SHA-256 metadata detects artifact corruption."""
    output = tmp_path / "dist"
    built = _run(sys.executable, str(PACKAGING / "build.py"), "--zipapp-only", "--output", str(output), cwd=PROJECT)
    assert built.returncode == 0, built.stderr
    with (output / "waegis.pyz").open("ab") as handle:
        handle.write(b"changed")
    verified = _run(sys.executable, str(PACKAGING / "build.py"), "--verify", "--output", str(output), cwd=PROJECT)
    assert verified.returncode != 0
    assert "digest mismatch" in verified.stderr


def test_release_verifier_rejects_undeclared_output_member(tmp_path: Path) -> None:
    """@brief D3 release verification treats output membership as closed."""
    output = tmp_path / "dist"
    built = _run(sys.executable, str(PACKAGING / "build.py"), "--zipapp-only", "--output", str(output), cwd=PROJECT)
    assert built.returncode == 0, built.stderr
    (output / "undeclared.bin").write_bytes(b"unexpected")
    verified = _run(sys.executable, str(PACKAGING / "build.py"), "--verify", "--output", str(output), cwd=PROJECT)
    assert verified.returncode != 0
    assert "output membership differs" in verified.stderr


def test_native_bundles_wrap_exact_zipapp_without_second_payload_tree(tmp_path: Path) -> None:
    """@brief D3 native forms contain one exact pyz and thin launchers."""
    pyz = tmp_path / "waegis.pyz"
    pyz.write_bytes(b"exact-zipapp")
    windows_runtime = tmp_path / "windows.tar.gz"
    linux_runtime = tmp_path / "linux.tar.gz"
    _runtime_archive(windows_runtime, "python.exe")
    _runtime_archive(linux_runtime, "bin/python3.13")
    windows_source = RuntimeSource("windows-x64", "windows.tar.gz", "https://example.invalid", 1, "0" * 64, "python.exe")
    linux_source = RuntimeSource("linux-x64", "linux.tar.gz", "https://example.invalid", 1, "0" * 64, "bin/python3.13")
    windows = tmp_path / "windows.zip"
    linux = tmp_path / "linux-bundle.tar.gz"
    build_windows_bundle(windows_runtime, windows_source, pyz, windows)
    build_linux_bundle(linux_runtime, linux_source, pyz, linux)
    with zipfile.ZipFile(windows) as archive:
        assert archive.read("waegis.pyz") == pyz.read_bytes()
        assert "waegis.cmd" in archive.namelist()
        assert not any(name.startswith("payload/") for name in archive.namelist())
    with tarfile.open(linux, "r:gz") as archive:
        names = archive.getnames()
        extracted = archive.extractfile("waegis.pyz")
        assert extracted is not None and extracted.read() == pyz.read_bytes()
        assert "waegis" in names
        assert not any(name.startswith("payload/") for name in names)


def test_runtime_lock_is_closed_and_internal_links_become_regular_files(tmp_path: Path) -> None:
    """@brief D3 locked internal links are validated and materialized without links."""
    version, sources = load_runtime_lock(PACKAGING / "runtime-lock.json")
    assert version == "3.13.13"
    assert set(sources) == {"windows-x64", "linux-x64"}
    linked = tmp_path / "linked.tar.gz"
    _runtime_archive(linked, "bin/python3.13", link="python3.13")
    pyz = tmp_path / "waegis.pyz"
    pyz.write_bytes(b"zipapp")
    output = tmp_path / "out.tar.gz"
    build_linux_bundle(linked, sources["linux-x64"], pyz, output)
    with tarfile.open(output, "r:gz") as archive:
        materialized = archive.getmember("runtime/bin/python3")
        extracted = archive.extractfile(materialized)
        assert materialized.isfile()
        assert extracted is not None and extracted.read() == b"runtime\n"


@pytest.mark.parametrize("target", ("../../../outside", "missing"))
def test_runtime_external_and_broken_links_are_rejected(tmp_path: Path, target: str) -> None:
    """@brief D3 runtime links cannot escape the root or refer to absent members."""
    _, sources = load_runtime_lock(PACKAGING / "runtime-lock.json")
    linked = tmp_path / "linked.tar.gz"
    _runtime_archive(linked, "bin/python3.13", link=target)
    with pytest.raises(BundleError, match="escapes|broken"):
        build_linux_bundle(linked, sources["linux-x64"], tmp_path / "missing.pyz", tmp_path / "out.tar.gz")


def test_unused_terminfo_aliases_are_excluded_from_linux_runtime(tmp_path: Path) -> None:
    """@brief D3 Linux runtime drops unused case-colliding terminfo aliases."""
    _, sources = load_runtime_lock(PACKAGING / "runtime-lock.json")
    runtime = tmp_path / "runtime.tar.gz"
    with tarfile.open(runtime, "w:gz") as archive:
        _add_file(archive, "python/bin/python3.13")
        _add_file(archive, "python/share/terminfo/2/2621A")
        _add_file(archive, "python/share/terminfo/2/2621a")
    pyz = tmp_path / "waegis.pyz"
    pyz.write_bytes(b"zipapp")
    output = tmp_path / "out.tar.gz"
    build_linux_bundle(runtime, sources["linux-x64"], pyz, output)
    with tarfile.open(output, "r:gz") as archive:
        assert not any(name.startswith("runtime/share/terminfo/") for name in archive.getnames())


# END OF FILE
