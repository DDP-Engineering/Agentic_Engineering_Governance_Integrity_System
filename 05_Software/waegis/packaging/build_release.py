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
@details Uses only the standard library. Embedded CPython inputs are pinned by
         filename and SHA-256 in ``runtime-lock.json``. Each application archive
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
@version 0.3.0
"""

# IMPORTS

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipapp
import zipfile
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"
PAYLOAD_ROOT = REPOSITORY_ROOT / "05_Software" / "aegis" / "template"
LOCK_FILE = Path(__file__).with_name("runtime-lock.json")
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


def _load_lock() -> dict[str, Any]:
    """@brief Read and minimally validate the embedded-runtime lock."""
    data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("targets"), dict):
        raise PackagingError(f"invalid runtime lock: {LOCK_FILE}")
    return data


def _download_runtime(target: str, cache: Path, *, offline: bool) -> Path:
    """@brief Acquire one pinned runtime and verify its SHA-256 before use."""
    lock = _load_lock()
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
    @version    0.1.0
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
        manifest_name = next((name for name in bundle.namelist() if name.endswith("/archive-manifest.json")), None)
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
            (member for member in bundle.getmembers() if member.name.endswith("/archive-manifest.json")),
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


def _windows_launcher(relative_python: str) -> str:
    """@brief Render the Windows application-archive launcher."""
    python = relative_python.replace("/", "\\")
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"WAEGIS_PACKAGING_TYPE=windows-x64-application-archive\"\r\n"
        f"set \"WAEGIS_PACKAGED_RUNTIME=%~dp0{python}\"\r\n"
        f"\"%~dp0{python}\" \"%~dp0waegis.pyz\" %*\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )


def _linux_launcher(relative_python: str) -> str:
    """@brief Render the Linux application-archive launcher."""
    return (
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "ROOT=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
        "export WAEGIS_PACKAGING_TYPE=linux-x64-application-archive\n"
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
        if target == "windows-x64":
            (staging / "waegis.cmd").write_text(
                _windows_launcher(relative_python),
                encoding="utf-8",
                newline="",
            )
        else:
            launcher = staging / "waegis"
            launcher.write_text(
                _linux_launcher(relative_python),
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


def build_release(output: Path, *, runtime_cache: Path, offline: bool, zipapp_only: bool) -> list[Path]:
    """@brief Build requested release files and their external hash manifests."""
    sys.path.insert(0, str(SOURCE_ROOT))
    from waegis.version import WIZARD_VERSION

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
    hashes = {path.name: sha256_file(path) for path in artifacts}
    release_manifest = output / "release-manifest.json"
    # newline="" suppresses the platform translation `\n` -> `\r\n`. These two
    # files are shipped as release assets and consumed by POSIX tooling: a
    # CRLF `SHA256SUMS` makes `sha256sum -c` look for a filename with a
    # trailing carriage return and fail every entry, which reads as a corrupt
    # download rather than as a packaging bug. Building on Windows must not
    # produce different bytes here than building on Linux.
    release_manifest.write_text(
        json.dumps(
            {"schema_version": 1, "waegis_version": WIZARD_VERSION, "artifacts": hashes},
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
    """@brief Verify external release hashes and each application archive manifest."""
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
        elif str(name).endswith("-linux-x64.tar.gz"):
            _verify_internal_tar(path)
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
            )
            verify_release(args.output.resolve())
    except PackagingError as exc:
        parser.exit(3, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
