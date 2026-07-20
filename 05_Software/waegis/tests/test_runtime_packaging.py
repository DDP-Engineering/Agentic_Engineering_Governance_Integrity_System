#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_runtime_packaging.py
@brief Embedded-runtime registration and payload-zipapp acceptance tests.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

from waegis.runtime import python_probe_candidates, register_packaged_runtime, runtime_pointer_path

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PACKAGE_ROOT / "packaging" / "build_release.py"


# LOCAL HELPERS


def _builder():  # type: ignore[no-untyped-def]
    """@brief Load the repository-native packaging module."""
    spec = importlib.util.spec_from_file_location("waegis_build_release", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# TESTS


def test_packaged_runtime_registers_atomic_text_pointer(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """@brief A packaged launcher registers its interpreter for shell/Node consumers."""
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("WAEGIS_PACKAGED_RUNTIME", sys.executable)
    registered = register_packaged_runtime()
    assert registered == Path(sys.executable).resolve()
    assert runtime_pointer_path().read_text(encoding="utf-8").strip() == str(registered)


def test_probe_order_prefers_explicit_then_registered(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """@brief Runtime resolution obeys explicit, registered, system order."""
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("WAEGIS_PACKAGED_RUNTIME", sys.executable)
    register_packaged_runtime()
    monkeypatch.setenv("AEGIS_PYTHON", "explicit-python")
    candidates = python_probe_candidates()
    assert candidates[0] == ("explicit-python",)
    assert candidates[1] == (str(Path(sys.executable).resolve()),)
    assert candidates[-3:] == (("py", "-3"), ("python3",), ("python",))


def test_payload_bundled_zipapp_smoke_and_hash_verification(tmp_path: Path) -> None:
    """@brief Build, verify, and execute a zipapp without repository fallback."""
    builder = _builder()
    output = tmp_path / "dist"
    artifacts = builder.build_release(
        output,
        runtime_cache=tmp_path / "runtime-cache",
        offline=True,
        zipapp_only=True,
    )
    builder.verify_release(output)
    assert len(artifacts) == 1
    environment = dict(os.environ)
    environment["WAEGIS_HOME"] = str(tmp_path / "home")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(artifacts[0]), "version", "--json"],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert document["result"]["packaging_type"] == "zipapp"
    assert document["result"]["bundled_payload_version"] == "0.5.0"
    assert len(document["result"]["bundled_payload_digest"]) == 64

    artifacts[0].write_bytes(artifacts[0].read_bytes() + b"corrupt")
    try:
        builder.verify_release(output)
    except builder.PackagingError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("release verification must reject a modified artifact")


def test_runtime_lock_pins_both_release_assets() -> None:
    """@brief The release builder has exact assets and hashes for both targets."""
    lock = json.loads((PACKAGE_ROOT / "packaging/runtime-lock.json").read_text(encoding="utf-8"))
    assert lock["release"] == "20260510"
    assert set(lock["targets"]) == {"windows-x64", "linux-x64"}
    assert all(len(entry["sha256"]) == 64 for entry in lock["targets"].values())


def test_runtime_extraction_materializes_relative_symlinks(tmp_path: Path) -> None:
    """@brief Linux runtime links become ordinary files on a Windows build host."""
    builder = _builder()
    archive_path = tmp_path / "runtime.tar.gz"
    content = b"embedded-python"
    with tarfile.open(archive_path, "w:gz") as archive:
        regular = tarfile.TarInfo("python/bin/python3.13")
        regular.size = len(content)
        regular.mode = 0o755
        archive.addfile(regular, io.BytesIO(content))
        link = tarfile.TarInfo("python/bin/python3")
        link.type = tarfile.SYMTYPE
        link.linkname = "python3.13"
        archive.addfile(link)

    destination = tmp_path / "runtime"
    builder._extract_runtime(archive_path, destination)

    materialized = destination / "python/bin/python3"
    assert materialized.is_file()
    assert not materialized.is_symlink()
    assert materialized.read_bytes() == content


# END OF FILE
