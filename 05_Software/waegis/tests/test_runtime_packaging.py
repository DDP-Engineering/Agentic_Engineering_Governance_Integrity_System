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
@details Covers runtime discovery, reproducible source filtering, pinned
         runtime metadata, zipapp execution, and archive extraction safety.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.3.0
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
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
    assert re.fullmatch(r"\d+\.\d+\.\d+", document["result"]["bundled_payload_version"])
    assert len(document["result"]["bundled_payload_digest"]) == 64

    artifacts[0].write_bytes(artifacts[0].read_bytes() + b"corrupt")
    try:
        builder.verify_release(output)
    except builder.PackagingError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("release verification must reject a modified artifact")


def test_release_artifact_names_carry_no_version(tmp_path: Path) -> None:
    """
    @brief      Release artifacts use stable, version-free filenames.
    @details    Documentation, install scripts, and automation reference these
                paths directly, so a version creeping back into a filename
                breaks them silently at the next release. The version is not
                lost: it is recorded in ``release-manifest.json`` and reported
                by the artifact itself.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.0
    """
    builder = _builder()
    sys.path.insert(0, str(PACKAGE_ROOT / "src"))
    from waegis.version import WIZARD_VERSION

    output = tmp_path / "dist"
    artifacts = builder.build_release(
        output,
        runtime_cache=tmp_path / "runtime-cache",
        offline=True,
        zipapp_only=True,
    )

    assert artifacts[0].name == builder.ZIPAPP_NAME == "waegis.pyz"
    assert builder.WINDOWS_ARCHIVE_NAME == "waegis-windows-x64.zip"
    assert builder.LINUX_ARCHIVE_NAME == "waegis-linux-x64.tar.gz"
    for name in (builder.ZIPAPP_NAME, builder.WINDOWS_ARCHIVE_NAME, builder.LINUX_ARCHIVE_NAME):
        assert WIZARD_VERSION not in name, f"artifact name {name!r} carries the version"

    manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["waegis_version"] == WIZARD_VERSION
    assert set(manifest["artifacts"]) == {builder.ZIPAPP_NAME}


def test_default_build_output_is_the_single_delivery_dist(tmp_path: Path) -> None:
    """
    @brief      The default output is one Git-ignored delivery directory.
    @details    Builds overwrite that directory instead of leaving a versioned
                set behind; the previous default scattered outputs across three
                locations that nothing ever cleaned up.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.0
    """
    builder = _builder()

    assert builder.DEFAULT_OUTPUT_DIR.name == "dist"
    assert builder.DEFAULT_OUTPUT_DIR.parent.name == "07_Delivery"


def test_runtime_lock_pins_both_release_assets() -> None:
    """@brief The release builder has exact assets and hashes for both targets."""
    lock = json.loads((PACKAGE_ROOT / "packaging/runtime-lock.json").read_text(encoding="utf-8"))
    assert lock["release"] == "20260510"
    assert set(lock["targets"]) == {"windows-x64", "linux-x64"}
    assert all(len(entry["sha256"]) == 64 for entry in lock["targets"].values())


def test_release_copy_excludes_generated_payload_state(tmp_path: Path) -> None:
    """
    @brief      Keep release staging aligned with deployment-copy exclusions.
    @param[in]  tmp_path Temporary source and destination roots.
    @return     None.
    @exception  AssertionError If generated dependency, cache, metadata, or
                bytecode state reaches the staged release tree.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.0
    """
    builder = _builder()
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    included = source / "src" / "app.py"
    included.parent.mkdir(parents=True)
    included.write_text("print('release')\n", encoding="utf-8")
    excluded_files = (
        source / "src" / "__pycache__" / "app.pyc",
        source / ".pytest_cache" / "README.md",
        source / ".mypy_cache" / "state.json",
        source / ".ruff_cache" / "state",
        source / ".pi" / "node_modules" / "package" / "index.js",
        source / ".pi" / ".vitest" / "results.json",
        source / ".uv-cache-build" / "archive.bin",
        source / "package.egg-info" / "PKG-INFO",
        source / "standalone.pyc",
    )
    for path in excluded_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"generated")

    builder._copy_tree(source, destination)

    assert (destination / "src" / "app.py").read_text(encoding="utf-8") == "print('release')\n"
    for path in excluded_files:
        assert not (destination / path.relative_to(source)).exists()


def test_runtime_extraction_materializes_relative_symlinks(tmp_path: Path) -> None:
    """
    @brief      Materialize runtime links and retain executable-mode metadata.
    @param[in]  tmp_path Temporary runtime archive and extraction root.
    @return     None.
    @exception  AssertionError If link bytes or executable metadata are lost.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
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
        link.mode = 0o777
        archive.addfile(link)

    destination = tmp_path / "runtime"
    executable_files = builder._extract_runtime(archive_path, destination)

    materialized = destination / "python/bin/python3"
    assert materialized.is_file()
    assert not materialized.is_symlink()
    assert materialized.read_bytes() == content
    assert executable_files == frozenset({"python/bin/python3", "python/bin/python3.13"})


def test_linux_tar_filter_normalizes_cross_build_modes() -> None:
    """
    @brief      Preserve required Linux executables in Windows-hosted builds.
    @return     None.
    @exception  AssertionError If directory, data, script, launcher, or runtime
                modes are not deterministic and executable where required.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    builder = _builder()
    executable_paths = frozenset({"waegis", "runtime/python/bin/python3"})

    directory = tarfile.TarInfo("waegis-linux-x64/runtime")
    directory.type = tarfile.DIRTYPE
    launcher = tarfile.TarInfo("waegis-linux-x64/waegis")
    interpreter = tarfile.TarInfo("waegis-linux-x64/runtime/python/bin/python3")
    shell_script = tarfile.TarInfo("waegis-linux-x64/payload/.agentic/tools/run.sh")
    data = tarfile.TarInfo("waegis-linux-x64/payload/AGENTS.md")

    for member in (directory, launcher, interpreter, shell_script, data):
        builder._linux_tar_filter(
            member,
            root_name="waegis-linux-x64",
            executable_paths=executable_paths,
        )

    assert directory.mode == 0o755
    assert launcher.mode == 0o755
    assert interpreter.mode == 0o755
    assert shell_script.mode == 0o755
    assert data.mode == 0o644
    launcher_text = builder._linux_launcher("runtime/python/bin/python3")
    assert launcher_text.startswith("#!/usr/bin/env sh\n")
    assert "\r\n" not in launcher_text


# END OF FILE
