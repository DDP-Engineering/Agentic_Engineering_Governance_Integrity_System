#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file build_release.py
@brief Build the payload zipapp and self-contained Windows/Linux archives.
@details Uses the standard library for archive orchestration and invokes uv only
         at release-build time for the locked Complete dependency export and
         wheel installation. Embedded CPython inputs are pinned by filename and
         SHA-256 in ``runtime-lock.json``. Each application archive
         contains an internal file manifest; the output directory receives a
         release manifest and ``SHA256SUMS`` for the final artifacts. Linux tar
         modes are normalized explicitly so cross-builds from Windows retain
         executable launchers, interpreters, and shell scripts.
@details **Artifact names carry no version** (0.3.0). A build overwrites the
         previous one in a single output directory rather than accumulating a
         new set per release, and documentation, install scripts, and any
         automation can reference a stable path. Nothing is lost by dropping the
         suffix: each artifact self-reports its version (``waegis.pyz version``
         prints the wizard version, bundled payload version, and payload
         digest), and the tracked ``release-manifest.json`` records the version
         alongside the hashes.
@details Artifacts are build outputs and are never tracked in Git. Committing
         them would grow history permanently and irreversibly for no benefit —
         a fixed filename does *not* reduce history size, because Git stores
         blobs rather than names, and the ``.tar.gz`` in particular cannot be
         delta-compressed at all (stream gzip: one early change shifts every
         following byte). The tracked publication record is
         ``07_Delivery/waegis-<version>/`` with ``RELEASE.md``, ``SHA256SUMS``,
         and ``release-manifest.json``; the binaries are reproducible from a
         source checkout at that version.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 0.8.0
"""

# IMPORTS

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.error
import urllib.request
import zipapp
import zipfile
import zlib
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"
PAYLOAD_ROOT = REPOSITORY_ROOT / "05_Software" / "aegis" / "template"
LOCK_FILE = Path(__file__).with_name("runtime-lock.json")
REPOWISE_RUNTIME_LOCK_FILE = Path(__file__).with_name("repowise-runtime-lock.json")
BASE_URL = "https://github.com/astral-sh/python-build-standalone/releases/download"
GENERATED_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".vitest",
}
GENERATED_SUFFIXES = {".pyc"}
GENERATED_PATTERNS = ("*.egg-info", ".uv-cache*")

# @brief Default build output: the one directory delivery binaries live in.
# @details A single, Git-ignored location (the repository's root `.gitignore`
#          ignores every `dist/`). Builds overwrite it instead of leaving a new
#          versioned set behind, which is what previously accumulated hundreds
#          of megabytes of stale archives across three separate directories.
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "07_Delivery" / "dist"

# @brief Release artifact filenames. Deliberately version-free — see the module
#        docstring for why the version lives in the artifact and the manifest
#        rather than in the filename.
ZIPAPP_NAME = "waegis.pyz"
WINDOWS_ARCHIVE_NAME = "waegis-windows-x64.zip"
LINUX_ARCHIVE_NAME = "waegis-linux-x64.tar.gz"
COMPLETE_WINDOWS_ARCHIVE_NAME = "waegis-complete-windows-x64.zip"
COMPLETE_LINUX_ARCHIVE_NAME = "waegis-complete-linux-x64.tar.gz"
REPOWISE_VERSION = "0.37.0"
REPOWISE_TAG = "v0.37.0"
REPOWISE_SOURCE_ARCHIVE = f"repowise-{REPOWISE_VERSION}-source.zip"


# DATA MODELS / TYPEDEFINITIONS


class PackagingError(Exception):
    """@brief A release input or output failed validation."""


# HELPER FUNCTIONS


def sha256_file(path: Path) -> str:
    """@brief Calculate the SHA-256 digest of one file without loading it wholly."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_tree(source: Path, destination: Path) -> None:
    """
    @brief      Copy a source tree while rejecting links and generated state.
    @param[in]  source Existing source directory.
    @param[in]  destination Destination directory created or extended.
    @return     None.
    @details    Uses the same payload exclusions as the deployment copier and
                additionally rejects the packaging-only ``.mypy_cache``.
    @exception  PackagingError If the source is missing or contains a link or
                unsupported filesystem entry.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    if not source.is_dir():
        raise PackagingError(f"release input directory does not exist: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if (
            any(part in GENERATED_NAMES for part in relative.parts)
            or relative.suffix in GENERATED_SUFFIXES
            or any(
                fnmatchcase(part, pattern)
                for part in relative.parts
                for pattern in GENERATED_PATTERNS
            )
        ):
            continue
        if path.is_symlink():
            raise PackagingError(f"release input contains a symlink: {path}")
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        else:
            raise PackagingError(f"release input is not a regular file: {path}")


def _load_lock(path: Path = LOCK_FILE) -> dict[str, Any]:
    """
    @brief      Read and minimally validate one embedded-runtime lock.
    @param[in]  path Core or RepoWise sidecar runtime lock.
    @return     Parsed runtime-lock document.
    @exception  PackagingError If the lock schema or target table is invalid.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-30
    @version    0.2.0
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("targets"), dict):
        raise PackagingError(f"invalid runtime lock: {path}")
    return data


def _download_runtime(
    target: str,
    cache: Path,
    *,
    offline: bool,
    lock_file: Path = LOCK_FILE,
) -> Path:
    """
    @brief      Acquire one pinned runtime and verify its SHA-256 before use.
    @param[in]  target Runtime target key.
    @param[in]  cache Local pinned-asset cache.
    @param[in]  offline Refuse cache misses when true.
    @param[in]  lock_file Runtime lock selecting the Python line and assets.
    @return     Verified runtime archive.
    @exception  PackagingError If the target is unpinned, unavailable, or has
                the wrong digest.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-30
    @version    0.2.0
    """
    lock = _load_lock(lock_file)
    try:
        entry = lock["targets"][target]
        asset = str(entry["asset"])
        expected = str(entry["sha256"])
    except (KeyError, TypeError) as exc:
        raise PackagingError(f"runtime target is not pinned: {target}") from exc
    archive = cache / asset
    if archive.is_file() and sha256_file(archive) == expected:
        return archive
    archive.unlink(missing_ok=True)
    if offline:
        raise PackagingError(f"offline runtime cache miss for {asset}")
    cache.mkdir(parents=True, exist_ok=True)
    temporary = archive.with_name(archive.name + ".tmp")
    url = f"{BASE_URL}/{lock['release']}/{asset}"
    try:
        with urllib.request.urlopen(url, timeout=120) as response, open(temporary, "wb") as output:
            shutil.copyfileobj(response, output)
        if sha256_file(temporary) != expected:
            raise PackagingError(f"SHA-256 mismatch for downloaded runtime: {asset}")
        os.replace(temporary, archive)
    except (OSError, urllib.error.URLError) as exc:
        temporary.unlink(missing_ok=True)
        raise PackagingError(f"cannot download pinned runtime {url}: {exc}") from exc
    return archive


def _safe_member_path(root: Path, name: str) -> Path:
    """@brief Convert one tar member name to a confined extraction path."""
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise PackagingError(f"unsafe runtime archive path: {name!r}")
    target = root.joinpath(*relative.parts)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PackagingError(f"runtime archive path escapes staging: {name!r}") from exc
    return target


def _copy_materialized_file(source: Path, target: Path) -> str:
    """@brief Copy link-target bytes without relying on platform link support."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(source, "rb") as input_file, open(target, "wb") as output_file:
        shutil.copyfileobj(input_file, output_file)
    target.chmod(source.stat().st_mode & 0o777)
    return str(target)


def _extract_runtime(archive_path: Path, destination: Path) -> frozenset[str]:
    """
    @brief      Safely extract runtime files and materialize confined links.
    @param[in]  archive_path Pinned runtime tar archive.
    @param[in]  destination Runtime staging directory.
    @return     Runtime-relative POSIX paths that require execute permission.
    @exception  PackagingError If an archive entry or link is unsafe or
                unsupported.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    links: list[tarfile.TarInfo] = []
    executable_files: set[str] = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = _safe_member_path(destination, member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if member.issym() or member.islnk():
                links.append(member)
                continue
            if not member.isfile():
                raise PackagingError(f"unsupported runtime archive entry: {member.name!r}")
            source = archive.extractfile(member)
            if source is None:
                raise PackagingError(f"cannot read runtime archive entry: {member.name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, open(target, "wb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(member.mode & 0o777)
            if member.mode & 0o111:
                executable_files.add(PurePosixPath(member.name).as_posix())
    for member in links:
        target = _safe_member_path(destination, member.name)
        link_name = PurePosixPath(member.linkname)
        if link_name.is_absolute():
            raise PackagingError(f"absolute runtime link target: {member.linkname!r}")
        source_base = destination if member.islnk() else target.parent
        source = source_base.joinpath(*link_name.parts).resolve()
        try:
            source.relative_to(destination.resolve())
        except ValueError as exc:
            raise PackagingError(f"runtime link escapes staging: {member.linkname!r}") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, copy_function=_copy_materialized_file)
            source_relative = PurePosixPath(source.relative_to(destination).as_posix())
            target_relative = PurePosixPath(target.relative_to(destination).as_posix())
            for executable in tuple(executable_files):
                try:
                    suffix = PurePosixPath(executable).relative_to(source_relative)
                except ValueError:
                    continue
                executable_files.add((target_relative / suffix).as_posix())
        elif source.is_file():
            _copy_materialized_file(source, target)
            source_relative = source.relative_to(destination).as_posix()
            if source_relative in executable_files or member.mode & 0o111:
                executable_files.add(target.relative_to(destination).as_posix())
        else:
            raise PackagingError(f"unresolved runtime link: {member.name!r} -> {member.linkname!r}")
    return frozenset(executable_files)


def _linux_tar_filter(
    member: tarfile.TarInfo,
    *,
    root_name: str,
    executable_paths: frozenset[str],
) -> tarfile.TarInfo:
    """
    @brief      Normalize Linux archive modes independently of the build host.
    @param[in]  member Tar entry produced from the staged application tree.
    @param[in]  root_name Top-level application directory in the tar archive.
    @param[in]  executable_paths Root-relative files requiring execute bits.
    @return     The same tar entry with a deterministic POSIX mode.
    @exception  None.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    prefix = f"{root_name}/"
    relative = member.name[len(prefix) :] if member.name.startswith(prefix) else ""
    if member.isdir():
        member.mode = 0o755
    elif member.isfile():
        member.mode = 0o755 if relative in executable_paths or relative.endswith(".sh") else 0o644
    return member


def _find_interpreter(runtime_root: Path, target: str) -> Path:
    """@brief Locate the embedded interpreter inside an extracted runtime."""
    names = ("python.exe",) if target == "windows-x64" else ("python3", "python")
    candidates = [path for name in names for path in runtime_root.rglob(name) if path.is_file()]
    if not candidates:
        raise PackagingError(f"embedded interpreter not found for {target}")
    candidates.sort(key=lambda path: ("bin" not in path.parts, len(path.parts), str(path)))
    return candidates[0]


def _run_build_command(
    arguments: list[str],
    *,
    cwd: Path,
    description: str,
    environment: dict[str, str] | None = None,
) -> str:
    """@brief Run one release-build command and surface its complete failure."""
    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PackagingError(f"{description} could not run: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise PackagingError(f"{description} failed: {detail}")
    return completed.stdout.strip()


def _git_repowise(source: Path, *arguments: str) -> str:
    """@brief Run a read-only Git command against the candidate RepoWise source."""
    return _run_build_command(
        [
            "git",
            "-c",
            f"safe.directory={source.as_posix()}",
            "-C",
            str(source),
            *arguments,
        ],
        cwd=source,
        description="RepoWise source validation",
    )


def _validate_repowise_source(source: Path) -> dict[str, Any]:
    """@brief Refuse any source that is not a clean exact RepoWise v0.37.0 tree."""
    source = source.resolve()
    if not source.is_dir():
        raise PackagingError(f"RepoWise source directory does not exist: {source}")
    try:
        with (source / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        raise PackagingError(f"invalid RepoWise pyproject.toml: {exc}") from exc
    if (
        project.get("name") != "repowise"
        or project.get("version") != REPOWISE_VERSION
    ):
        raise PackagingError("RepoWise source must identify as project repowise version 0.37.0")
    status = _git_repowise(source, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        detail = status.replace("\n", "; ")
        raise PackagingError(f"RepoWise source must be clean; Git reports: {detail}")
    tag = _git_repowise(source, "describe", "--tags", "--exact-match")
    if tag not in {REPOWISE_TAG, REPOWISE_VERSION}:
        raise PackagingError(f"RepoWise source must be at tag {REPOWISE_TAG}, found {tag!r}")
    commit = _git_repowise(source, "rev-parse", "HEAD")
    tracked = [
        item
        for item in _git_repowise(source, "ls-files", "-z").split("\0")
        if item
    ]
    if not tracked or "LICENSE" not in tracked or "uv.lock" not in tracked:
        raise PackagingError("RepoWise source lacks its tracked LICENSE or uv.lock")
    return {"root": source, "tag": tag, "commit": commit, "tracked": tracked}


def _write_repowise_source_archive(source_info: Mapping[str, Any], output: Path) -> None:
    """
    @brief      Write byte-identical RepoWise source from the pinned Git commit.
    @details    Reading the worktree would make Windows and Linux source ZIPs
                differ when Git line-ending filters are active. ``git archive``
                reads repository blobs and preserves tracked executable modes.
    @param[in]  source_info Validated source root, tag, commit, and tracked set.
    @param[in]  output Destination source ZIP.
    @return     None.
    @exception  PackagingError If Git cannot archive the validated commit.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-30
    @version    0.2.0
    """
    source = Path(source_info["root"])
    _git_repowise(
        source,
        "archive",
        "--format=zip",
        f"--prefix=repowise-{REPOWISE_VERSION}/",
        f"--output={output}",
        str(source_info["commit"]),
    )
    if not output.is_file() or output.stat().st_size <= 0:
        raise PackagingError("RepoWise source archive was not created")


def _copy_repowise_python(source: Path, site_packages: Path) -> None:
    """@brief Merge the three RepoWise namespace source roots into site-packages."""
    for package in ("core", "cli", "server"):
        root = source / "packages" / package / "src"
        if not root.is_dir():
            raise PackagingError(f"RepoWise package source is missing: {root}")
        _copy_tree(root, site_packages)
    metadata = site_packages / f"repowise-{REPOWISE_VERSION}.dist-info"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.4\n"
        "Name: repowise\n"
        f"Version: {REPOWISE_VERSION}\n"
        "License-Expression: AGPL-3.0-or-later\n",
        encoding="utf-8",
        newline="",
    )
    (metadata / "WHEEL").write_text(
        "Wheel-Version: 1.0\n"
        "Generator: WAEGIS Complete\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n",
        encoding="utf-8",
        newline="",
    )


def _offline_sitecustomize() -> str:
    """@brief Render the managed-runtime non-loopback socket denial guard."""
    return (
        '"""WAEGIS managed RepoWise offline network guard."""\n'
        "import ipaddress\n"
        "import os\n"
        "import socket\n"
        "_original_connect = socket.socket.connect\n"
        "def _offline_connect(instance, address):\n"
        "    if os.environ.get('WAEGIS_REPOWISE_OFFLINE') == '1':\n"
        "        host = address[0] if isinstance(address, tuple) else str(address)\n"
        "        try:\n"
        "            allowed = ipaddress.ip_address(host).is_loopback\n"
        "        except ValueError:\n"
        "            allowed = host == 'localhost'\n"
        "        if not allowed:\n"
        "            raise OSError('WAEGIS RepoWise runtime denied non-loopback network access')\n"
        "    return _original_connect(instance, address)\n"
        "socket.socket.connect = _offline_connect\n"
    )


def _repowise_launcher(target: str, relative_python: str) -> tuple[str, str]:
    """@brief Return the sidecar launcher name and platform-specific text."""
    if target == "windows-x64":
        python = relative_python.replace("/", "\\")
        return (
            "repowise.cmd",
            "@echo off\r\n"
            "setlocal\r\n"
            "set \"WAEGIS_REPOWISE_OFFLINE=1\"\r\n"
            "set \"DO_NOT_TRACK=1\"\r\n"
            "set \"REPOWISE_SKIP_EDITOR_SETUP=1\"\r\n"
            "set \"PYTHONPATH=%~dp0site-packages\"\r\n"
            f"\"%~dp0{python}\" -m waegis_repowise_bootstrap %*\r\n"
            "exit /b %ERRORLEVEL%\r\n",
        )
    return (
        "repowise",
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        'ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        "export WAEGIS_REPOWISE_OFFLINE=1\n"
        "export DO_NOT_TRACK=1\n"
        "export REPOWISE_SKIP_EDITOR_SETUP=1\n"
        'export PYTHONPATH="$ROOT/site-packages"\n'
        f'exec "$ROOT/{relative_python}" -m waegis_repowise_bootstrap "$@"\n',
    )


def _repowise_file_table(root: Path) -> list[dict[str, Any]]:
    """@brief Build the sidecar manifest's sorted file hash table."""
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "repowise-bundle-manifest.json"
    ]


def _repowise_tree_digest(files: list[dict[str, Any]]) -> tuple[str, int]:
    """@brief Compute the digest algorithm consumed by WAEGIS installation."""
    digest = hashlib.sha256()
    total = 0
    for item in files:
        total += int(item["size"])
        digest.update(str(item["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(item["size"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(item["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), total


def _repowise_packaged_size(root: Path, files: list[dict[str, Any]]) -> int:
    """@brief Estimate compressed sidecar bytes without archive-header overhead.
    @version 1.0.0
    """
    compressed = sum(
        len(zlib.compress((root / str(item["path"])).read_bytes(), level=9))
        for item in files
    )
    unpacked = sum(int(item["size"]) for item in files)
    return max(1, min(compressed, unpacked))


def _third_party_notices(site_packages: Path) -> str:
    """@brief Derive a compact installed-distribution license notice."""
    records = []
    for metadata in sorted(site_packages.glob("*.dist-info/METADATA")):
        name = ""
        version = ""
        license_value = "not declared"
        for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Name: "):
                name = line[6:]
            elif line.startswith("Version: "):
                version = line[9:]
            elif (
                line.startswith(("License-Expression: ", "License: "))
                and license_value == "not declared"
            ):
                license_value = line.split(":", 1)[1].strip() or license_value
        if name:
            records.append(f"{name} {version}: {license_value}")
    return (
        "Third-party distributions included in the RepoWise runtime\n"
        "Generated from installed package metadata; consult the corresponding "
        "source archive and package licenses.\n\n"
        + "\n".join(records)
        + "\n"
    )


def _build_repowise_bundle(
    target: str,
    *,
    source_info: Mapping[str, Any],
    destination: Path,
    runtime_cache: Path,
    offline: bool,
) -> frozenset[str]:
    """@brief Assemble one locked, native-wheel-only RepoWise Complete sidecar."""
    current = (
        "windows-x64"
        if os.name == "nt"
        else "linux-x64"
        if sys.platform.startswith("linux")
        else ""
    )
    if target != current:
        raise PackagingError(
            "RepoWise Complete must be built natively; "
            f"host is {current or sys.platform}, target is {target}"
        )
    source = Path(source_info["root"])
    runtime_lock = _load_lock(REPOWISE_RUNTIME_LOCK_FILE)
    runtime_archive = _download_runtime(
        target,
        runtime_cache,
        offline=offline,
        lock_file=REPOWISE_RUNTIME_LOCK_FILE,
    )
    runtime = destination / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    executable_runtime = _extract_runtime(runtime_archive, runtime)
    interpreter = _find_interpreter(runtime, target)
    relative_python = interpreter.relative_to(destination).as_posix()
    site_packages = destination / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    requirements = destination / "locked-requirements.txt"
    sbom = destination / "sbom.cdx.json"
    environment = dict(os.environ)
    environment["UV_NO_PROGRESS"] = "1"
    export_base = ["uv", "export", "--locked", "--no-dev", "--project", str(source)]
    if offline:
        export_base.append("--offline")
    _run_build_command(
        [
            *export_base,
            "--no-emit-workspace",
            "--format",
            "requirements.txt",
            "--output-file",
            str(requirements),
        ],
        cwd=source,
        description="RepoWise locked dependency export",
        environment=environment,
    )
    _run_build_command(
        [*export_base, "--format", "cyclonedx1.5", "--output-file", str(sbom)],
        cwd=source,
        description="RepoWise SBOM export",
        environment=environment,
    )
    platform_name = (
        "x86_64-pc-windows-msvc"
        if target == "windows-x64"
        else "x86_64-unknown-linux-gnu"
    )
    python_version = ".".join(str(runtime_lock["python_version"]).split(".")[:2])
    install = [
        "uv",
        "pip",
        "install",
        "--target",
        str(site_packages),
        "--python-version",
        python_version,
        "--python-platform",
        platform_name,
        "--only-binary",
        ":all:",
        "--require-hashes",
        "--requirements",
        str(requirements),
        "--link-mode",
        "copy",
    ]
    if offline:
        install.append("--offline")
    _run_build_command(
        install,
        cwd=source,
        description=f"RepoWise {target} locked wheel installation",
        environment=environment,
    )
    _copy_repowise_python(source, site_packages)
    (site_packages / "waegis_repowise_bootstrap.py").write_text(
        '"""Isolated WAEGIS entry point for the bundled RepoWise CLI."""\n'
        "from repowise.cli.editor_integrations import claude_config\n"
        "claude_config.migrate_claude_code_hooks = lambda: False\n"
        "from repowise.cli.main import cli\n"
        "cli()\n",
        encoding="utf-8",
        newline="",
    )
    (site_packages / "sitecustomize.py").write_text(
        _offline_sitecustomize(),
        encoding="utf-8",
        newline="",
    )
    source_archive = destination / REPOWISE_SOURCE_ARCHIVE
    _write_repowise_source_archive(source_info, source_archive)
    licenses = destination / "licenses"
    licenses.mkdir()
    shutil.copy2(source / "LICENSE", licenses / "REPOWISE-AGPL-3.0.txt")
    (licenses / "THIRD-PARTY-NOTICES.txt").write_text(
        _third_party_notices(site_packages),
        encoding="utf-8",
        newline="",
    )
    launcher_name, launcher_text = _repowise_launcher(target, relative_python)
    launcher = destination / launcher_name
    launcher.write_text(launcher_text, encoding="utf-8", newline="")
    if target == "linux-x64":
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    files = _repowise_file_table(destination)
    tree_digest, unpacked_size = _repowise_tree_digest(files)
    packaged_size = _repowise_packaged_size(destination, files)
    manifest = {
        "schema_version": 1,
        "edition": "complete",
        "repowise_version": REPOWISE_VERSION,
        "platform": target,
        "launcher": launcher_name,
        "source": {
            "tag": source_info["tag"],
            "commit": source_info["commit"],
            "archive": REPOWISE_SOURCE_ARCHIVE,
        },
        "source_sha256": sha256_file(source_archive),
        "tree_sha256": tree_digest,
        "packaged_size": packaged_size,
        "unpacked_size": unpacked_size,
        "files": files,
    }
    (destination / "repowise-bundle-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    probe = [str(launcher), "--version"]
    if target == "windows-x64":
        probe = ["cmd.exe", "/d", "/c", str(launcher), "--version"]
    output = _run_build_command(
        probe,
        cwd=destination,
        description="RepoWise bundled native import/version smoke",
        environment={**os.environ, "WAEGIS_REPOWISE_OFFLINE": "1"},
    )
    if REPOWISE_VERSION not in output:
        raise PackagingError(f"RepoWise bundled smoke reported an unexpected version: {output!r}")
    return frozenset(
        {launcher_name, relative_python}
        | {f"runtime/{path}" for path in executable_runtime}
    )


def _tree_manifest(root: Path) -> dict[str, str]:
    """@brief Hash every regular staged file using portable relative names."""
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_archive_manifest(root: Path, *, target: str) -> None:
    """@brief Write the internal application-archive file manifest."""
    payload = {"schema_version": 1, "target": target, "files": _tree_manifest(root)}
    (root / "archive-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _verify_internal_zip(path: Path) -> None:
    """@brief Verify every file declared by a Windows archive manifest."""
    with zipfile.ZipFile(path) as bundle:
        manifest_name = next(
            (
                name
                for name in bundle.namelist()
                if name.endswith("/archive-manifest.json")
            ),
            None,
        )
        if manifest_name is None:
            raise PackagingError(f"application archive has no internal manifest: {path.name}")
        document = json.loads(bundle.read(manifest_name))
        prefix = manifest_name[: -len("archive-manifest.json")]
        for relative, expected in document.get("files", {}).items():
            actual = hashlib.sha256(bundle.read(prefix + relative)).hexdigest()
            if actual != expected:
                raise PackagingError(f"archive member hash mismatch: {path.name}:{relative}")


def _verify_internal_tar(path: Path) -> None:
    """@brief Verify every file declared by a Linux archive manifest."""
    with tarfile.open(path, "r:gz") as bundle:
        manifest = next(
            (
                member
                for member in bundle.getmembers()
                if member.name.endswith("/archive-manifest.json")
            ),
            None,
        )
        if manifest is None:
            raise PackagingError(f"application archive has no internal manifest: {path.name}")
        source = bundle.extractfile(manifest)
        if source is None:
            raise PackagingError(f"cannot read internal archive manifest: {path.name}")
        document = json.loads(source.read())
        prefix = manifest.name[: -len("archive-manifest.json")]
        members = {member.name: member for member in bundle.getmembers()}
        for relative, expected in document.get("files", {}).items():
            member = members.get(prefix + relative)
            source = bundle.extractfile(member) if member is not None else None
            if source is None or hashlib.sha256(source.read()).hexdigest() != expected:
                raise PackagingError(f"archive member hash mismatch: {path.name}:{relative}")


def _read_complete_bundle_manifest(path: Path) -> dict[str, Any]:
    """
    @brief      Read the RepoWise sidecar manifest from a Complete archive.
    @param[in]  path Complete Windows ZIP or Linux tar.gz archive.
    @return     Parsed RepoWise bundle manifest.
    @exception  PackagingError If the archive or sidecar manifest is missing
                or malformed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.0
    """
    suffix = path.name
    try:
        if suffix.endswith("-windows-x64.zip"):
            with zipfile.ZipFile(path) as bundle:
                member = next(
                    (
                        name
                        for name in bundle.namelist()
                        if name.endswith("/repowise/repowise-bundle-manifest.json")
                    ),
                    None,
                )
                if member is None:
                    raise PackagingError(
                        f"Complete archive has no RepoWise bundle manifest: {path.name}"
                    )
                document = json.loads(bundle.read(member))
        elif suffix.endswith("-linux-x64.tar.gz"):
            with tarfile.open(path, "r:gz") as bundle:
                member = next(
                    (
                        item
                        for item in bundle.getmembers()
                        if item.name.endswith("/repowise/repowise-bundle-manifest.json")
                    ),
                    None,
                )
                source = bundle.extractfile(member) if member is not None else None
                if source is None:
                    raise PackagingError(
                        f"Complete archive has no RepoWise bundle manifest: {path.name}"
                    )
                document = json.loads(source.read())
        else:
            raise PackagingError(f"unsupported Complete archive: {path.name}")
    except (OSError, tarfile.TarError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise PackagingError(f"invalid Complete archive: {path.name}") from exc
    if not isinstance(document, dict):
        raise PackagingError(f"invalid RepoWise bundle manifest: {path.name}")
    return document


def _validate_complete_companion(
    path: Path,
    *,
    expected_platform: str,
    source_info: Mapping[str, Any] | None = None,
) -> None:
    """
    @brief      Reject stale or mismatched cross-platform Complete companions.
    @param[in]  path Complete archive to validate.
    @param[in]  expected_platform Platform encoded by the artifact name.
    @param[in]  source_info Optional current RepoWise source identity.
    @return     None.
    @exception  PackagingError If edition, version, platform, tag, or commit
                differs from the current native build.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.0
    """
    document = _read_complete_bundle_manifest(path)
    if (
        document.get("schema_version") != 1
        or document.get("edition") != "complete"
        or document.get("repowise_version") != REPOWISE_VERSION
        or document.get("platform") != expected_platform
    ):
        raise PackagingError(f"mismatched Complete archive metadata: {path.name}")
    source = document.get("source")
    if not isinstance(source, dict):
        raise PackagingError(f"invalid Complete archive source metadata: {path.name}")
    tag = source.get("tag")
    commit = source.get("commit")
    if (
        tag not in {REPOWISE_VERSION, f"v{REPOWISE_VERSION}"}
        or not isinstance(commit, str)
        or len(commit) != 40
        or any(character not in "0123456789abcdef" for character in commit.lower())
        or source.get("archive") != REPOWISE_SOURCE_ARCHIVE
    ):
        raise PackagingError(f"invalid Complete archive source identity: {path.name}")
    if source_info is not None and (
        tag != source_info["tag"]
        or commit != source_info["commit"]
    ):
        raise PackagingError(
            f"stale Complete companion; rebuild {path.name} from the same RepoWise source"
        )


def _build_zipapp(output: Path) -> Path:
    """@brief Build the standalone payload-bundled WAEGIS zipapp."""
    with tempfile.TemporaryDirectory(prefix="waegis-pyz-") as temporary_text:
        staging = Path(temporary_text)
        _copy_tree(SOURCE_ROOT / "waegis", staging / "waegis")
        _copy_tree(PAYLOAD_ROOT, staging / "waegis" / "_bundled_payload")
        temporary = output.with_name(output.name + ".tmp")
        zipapp.create_archive(staging, target=temporary, main="waegis.cli:main")
        os.replace(temporary, output)
    return output


def _windows_launcher(relative_python: str, *, complete: bool = False) -> str:
    """@brief Render the Windows application-archive launcher."""
    python = relative_python.replace("/", "\\")
    edition = "complete" if complete else "core"
    repowise = 'set "WAEGIS_REPOWISE_BUNDLE=%~dp0repowise"\r\n' if complete else ""
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"WAEGIS_PACKAGING_TYPE=windows-x64-application-archive\"\r\n"
        f"set \"WAEGIS_EDITION={edition}\"\r\n"
        f"{repowise}"
        f"set \"WAEGIS_PACKAGED_RUNTIME=%~dp0{python}\"\r\n"
        f"\"%~dp0{python}\" \"%~dp0waegis.pyz\" %*\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )


def _linux_launcher(relative_python: str, *, complete: bool = False) -> str:
    """@brief Render the Linux application-archive launcher."""
    edition = "complete" if complete else "core"
    repowise = 'export WAEGIS_REPOWISE_BUNDLE="$ROOT/repowise"\n' if complete else ""
    return (
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "ROOT=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
        "export WAEGIS_PACKAGING_TYPE=linux-x64-application-archive\n"
        f"export WAEGIS_EDITION={edition}\n"
        f"{repowise}"
        f"export WAEGIS_PACKAGED_RUNTIME=\"$ROOT/{relative_python}\"\n"
        f"exec \"$ROOT/{relative_python}\" \"$ROOT/waegis.pyz\" \"$@\"\n"
    )


def _build_application_archive(
    target: str,
    *,
    zipapp_path: Path,
    output: Path,
    runtime_cache: Path,
    offline: bool,
    repowise_source: Mapping[str, Any] | None = None,
) -> Path:
    """
    @brief      Build one self-contained OS application archive.
    @param[in]  target Runtime target key from ``runtime-lock.json``.
    @param[in]  zipapp_path Previously built payload-bundled zipapp.
    @param[in]  output Final application archive path.
    @param[in]  runtime_cache Cache containing or receiving pinned runtimes.
    @param[in]  offline Refuse network access when true.
    @return     Final archive path.
    @details    Launcher text preserves its declared newline convention on
                every host; Linux tar modes are normalized independently of
                Windows filesystem semantics.
    @exception  PackagingError If runtime acquisition, staging, or archive
                validation inputs fail.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    runtime_archive = _download_runtime(target, runtime_cache, offline=offline)
    with tempfile.TemporaryDirectory(prefix=f"waegis-{target}-") as temporary_text:
        staging = Path(temporary_text) / f"waegis-{target}"
        runtime = staging / "runtime"
        runtime.mkdir(parents=True)
        runtime_executables = _extract_runtime(runtime_archive, runtime)
        interpreter = _find_interpreter(runtime, target)
        relative_python = interpreter.relative_to(staging).as_posix()
        shutil.copy2(zipapp_path, staging / "waegis.pyz")
        _copy_tree(PAYLOAD_ROOT, staging / "payload")
        repowise_executables: frozenset[str] = frozenset()
        if repowise_source is not None:
            repowise_executables = _build_repowise_bundle(
                target,
                source_info=repowise_source,
                destination=staging / "repowise",
                runtime_cache=runtime_cache,
                offline=offline,
            )
        if target == "windows-x64":
            (staging / "waegis.cmd").write_text(
                _windows_launcher(relative_python, complete=repowise_source is not None),
                encoding="utf-8",
                newline="",
            )
        else:
            launcher = staging / "waegis"
            launcher.write_text(
                _linux_launcher(relative_python, complete=repowise_source is not None),
                encoding="utf-8",
                newline="",
            )
            launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        _write_archive_manifest(staging, target=target)
        temporary = output.with_name(output.name + ".tmp")
        if target == "windows-x64":
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(staging.rglob("*")):
                    if path.is_file():
                        bundle.write(path, path.relative_to(staging.parent).as_posix())
        else:
            executable_paths = frozenset(
                {"waegis", relative_python}
                | {f"runtime/{path}" for path in runtime_executables}
                | {f"repowise/{path}" for path in repowise_executables}
            )
            with tarfile.open(temporary, "w:gz") as bundle:
                bundle.add(
                    staging,
                    arcname=staging.name,
                    filter=lambda member: _linux_tar_filter(
                        member,
                        root_name=staging.name,
                        executable_paths=executable_paths,
                    ),
                )
        os.replace(temporary, output)
    return output


# EXPORTED FUNCTIONS / PUBLIC API


def build_release(
    output: Path,
    *,
    runtime_cache: Path,
    offline: bool,
    zipapp_only: bool,
    repowise_source: Path | None = None,
    complete_target: str | None = None,
) -> list[Path]:
    """
    @brief      Build Core artifacts and an optional native Complete artifact.
    @param[in]  output Release output directory.
    @param[in]  runtime_cache Pinned embedded-runtime and wheel cache.
    @param[in]  offline Refuse build-time downloads when true.
    @param[in]  zipapp_only Build only the portable Core zipapp when true.
    @param[in]  repowise_source Optional clean RepoWise source checkout.
    @param[in]  complete_target Optional native Complete platform.
    @return     Paths to the release artifacts represented by the manifest.
    @details    A previously built opposite-platform Complete companion is
                included only when its RepoWise tag and commit match the
                source used for the current native build.
    @exception  PackagingError If source, native runtime, archive, or companion
                validation fails.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.6.0
    """
    sys.path.insert(0, str(SOURCE_ROOT))
    from waegis.version import WIZARD_VERSION

    source_info = (
        _validate_repowise_source(repowise_source)
        if repowise_source is not None
        else None
    )
    if source_info is not None and zipapp_only:
        raise PackagingError("RepoWise Complete cannot be produced with --zipapp-only")
    if complete_target is not None and source_info is None:
        raise PackagingError("--complete-target requires --repowise-source")
    output.mkdir(parents=True, exist_ok=True)
    pyz = _build_zipapp(output / ZIPAPP_NAME)
    artifacts = [pyz]
    if not zipapp_only:
        artifacts.append(
            _build_application_archive(
                "windows-x64",
                zipapp_path=pyz,
                output=output / WINDOWS_ARCHIVE_NAME,
                runtime_cache=runtime_cache,
                offline=offline,
            )
        )
        artifacts.append(
            _build_application_archive(
                "linux-x64",
                zipapp_path=pyz,
                output=output / LINUX_ARCHIVE_NAME,
                runtime_cache=runtime_cache,
                offline=offline,
            )
        )
        if source_info is not None:
            native_target = complete_target or (
                "windows-x64"
                if os.name == "nt"
                else "linux-x64"
                if sys.platform.startswith("linux")
                else ""
            )
            if native_target not in {"windows-x64", "linux-x64"}:
                raise PackagingError(f"unsupported Complete build host: {sys.platform}")
            complete_name = (
                COMPLETE_WINDOWS_ARCHIVE_NAME
                if native_target == "windows-x64"
                else COMPLETE_LINUX_ARCHIVE_NAME
            )
            artifacts.append(
                _build_application_archive(
                    native_target,
                    zipapp_path=pyz,
                    output=output / complete_name,
                    runtime_cache=runtime_cache,
                    offline=offline,
                    repowise_source=source_info,
                )
            )
            other_complete = (
                output / COMPLETE_LINUX_ARCHIVE_NAME
                if native_target == "windows-x64"
                else output / COMPLETE_WINDOWS_ARCHIVE_NAME
            )
            if other_complete.is_file():
                other_platform = (
                    "linux-x64" if native_target == "windows-x64" else "windows-x64"
                )
                _validate_complete_companion(
                    other_complete,
                    expected_platform=other_platform,
                    source_info=source_info,
                )
                artifacts.append(other_complete)
    hashes = {path.name: sha256_file(path) for path in artifacts}
    metadata = {
        path.name: {
            "sha256": hashes[path.name],
            "size": path.stat().st_size,
            "edition": "complete" if path.name.startswith("waegis-complete-") else "core",
        }
        for path in artifacts
    }
    release_manifest = output / "release-manifest.json"
    # newline="" suppresses the platform translation `\n` -> `\r\n`. These two
    # files are shipped as release assets and consumed by POSIX tooling: a
    # CRLF `SHA256SUMS` makes `sha256sum -c` look for a filename with a
    # trailing carriage return and fail every entry, which reads as a corrupt
    # download rather than as a packaging bug. Building on Windows must not
    # produce different bytes here than building on Linux.
    release_manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "waegis_version": WIZARD_VERSION,
                "repowise_version": REPOWISE_VERSION if source_info is not None else None,
                "artifacts": hashes,
                "artifact_metadata": metadata,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="",
    )
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items())),
        encoding="utf-8",
        newline="",
    )
    return artifacts


def verify_release(output: Path) -> None:
    """
    @brief      Verify release hashes, archive manifests, and Complete identity.
    @param[in]  output Release output directory.
    @return     None.
    @exception  PackagingError If metadata, hashes, archive contents, or
                Complete bundle identity validation fails.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.6.0
    """
    manifest_path = output / "release-manifest.json"
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifacts = document["artifacts"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PackagingError(f"invalid release manifest: {manifest_path}") from exc
    if not isinstance(artifacts, dict):
        raise PackagingError(f"invalid artifact table: {manifest_path}")
    expected_sum_lines: list[str] = []
    for name, expected in sorted(artifacts.items()):
        path = output / str(name)
        if not path.is_file() or sha256_file(path) != expected:
            raise PackagingError(f"release artifact hash mismatch: {name}")
        expected_sum_lines.append(f"{expected}  {name}\n")
        if str(name).endswith("-windows-x64.zip"):
            _verify_internal_zip(path)
            if str(name).startswith("waegis-complete-"):
                _validate_complete_companion(path, expected_platform="windows-x64")
        elif str(name).endswith("-linux-x64.tar.gz"):
            _verify_internal_tar(path)
            if str(name).startswith("waegis-complete-"):
                _validate_complete_companion(path, expected_platform="linux-x64")
    sums = output / "SHA256SUMS"
    try:
        actual_sums = sums.read_text(encoding="utf-8")
    except OSError as exc:
        raise PackagingError(f"missing release checksum file: {sums}") from exc
    if actual_sums != "".join(expected_sum_lines):
        raise PackagingError(f"release checksum file does not match manifest: {sums}")


def main(argv: list[str] | None = None) -> int:
    """@brief Parse release-builder arguments and produce the requested artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--runtime-cache", type=Path, default=PACKAGE_ROOT / ".runtime-cache")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--zipapp-only", action="store_true")
    parser.add_argument(
        "--repowise-source",
        type=Path,
        help="Clean RepoWise v0.37.0 source checkout used to build the native Complete edition",
    )
    parser.add_argument(
        "--complete-target",
        choices=("windows-x64", "linux-x64"),
        help="Complete target; must match the native build host",
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            verify_release(args.output.resolve())
        else:
            build_release(
                args.output.resolve(),
                runtime_cache=args.runtime_cache.resolve(),
                offline=args.offline,
                zipapp_only=args.zipapp_only,
                repowise_source=args.repowise_source.resolve() if args.repowise_source else None,
                complete_target=args.complete_target,
            )
            verify_release(args.output.resolve())
    except PackagingError as exc:
        parser.exit(3, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
