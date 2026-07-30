#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_release_packaging_integrity.py
@brief Reproducible release archive and packaging-integrity contract tests.
@details Uses compact local fixtures for epochs, ZIP/tar metadata, strict locks,
         downloads, exact archive verification, link graphs, and publication.
         No test performs a live network request or builds production runtimes.
@author Eng. Dan Dumitru Pasare
@date 2026-07-30
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import stat
import struct
import tarfile
import warnings
import zipfile
from pathlib import Path
from typing import Any

import pytest

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PACKAGE_ROOT / "packaging" / "build_release.py"
TARGETS = ("windows-x64", "linux-x64")


# LOCAL HELPERS


def _builder():  # type: ignore[no-untyped-def]
    """@brief Load an isolated copy of the release builder."""
    spec = importlib.util.spec_from_file_location("waegis_release_integrity", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lock_document(payload: bytes = b"runtime") -> dict[str, Any]:
    """@brief Return one minimal valid strict runtime-lock document."""
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "schema_version": 1,
        "provider": "astral-sh/python-build-standalone",
        "release": "20260510",
        "python_version": "3.13.13",
        "targets": {
            "windows-x64": {"asset": "windows.tar.gz", "sha256": digest},
            "linux-x64": {"asset": "linux.tar.gz", "sha256": "b" * 64},
        },
    }


def _write_lock(path: Path, document: dict[str, Any]) -> None:
    """@brief Write one local runtime lock with canonical JSON."""
    path.write_text(json.dumps(document), encoding="utf-8", newline="")


class _Response(io.BytesIO):
    """@brief Context-managed in-memory urlopen response."""

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _manifest(target: str, files: dict[Any, Any]) -> bytes:
    """@brief Encode one internal archive manifest."""
    return json.dumps(
        {"schema_version": 1, "target": target, "files": files},
        sort_keys=True,
    ).encode("utf-8")


def _write_zip_fixture(
    path: Path,
    *,
    target: str = "windows-x64",
    files: dict[Any, Any] | None = None,
    payload: dict[str, bytes] | None = None,
    manifest_content: bytes | None = None,
    extra_manifests: int = 0,
    duplicate_payload: bool = False,
    special: tuple[str, int] | None = None,
) -> None:
    """@brief Write one compact ZIP verifier fixture."""
    payload = {"app.txt": b"payload"} if payload is None else payload
    if files is None:
        files = {
            name: hashlib.sha256(content).hexdigest()
            for name, content in payload.items()
        }
    content = manifest_content if manifest_content is not None else _manifest(target, files)
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("bundle/archive-manifest.json", content)
        for name, value in payload.items():
            bundle.writestr(f"bundle/{name}", value)
            if duplicate_payload:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    bundle.writestr(f"bundle/{name}", value)
        for index in range(extra_manifests):
            bundle.writestr(f"other{index}/archive-manifest.json", content)
        if special is not None:
            name, mode = special
            info = zipfile.ZipInfo(f"bundle/{name}")
            info.create_system = 3
            info.external_attr = mode << 16
            bundle.writestr(info, b"special")


def _write_tar_fixture(
    path: Path,
    *,
    target: str = "linux-x64",
    files: dict[Any, Any] | None = None,
    payload: dict[str, bytes] | None = None,
    manifest_content: bytes | None = None,
    extra_manifests: int = 0,
    duplicate_payload: bool = False,
    special_type: bytes | None = None,
) -> None:
    """@brief Write one compact tar verifier fixture."""
    payload = {"app.txt": b"payload"} if payload is None else payload
    if files is None:
        files = {
            name: hashlib.sha256(content).hexdigest()
            for name, content in payload.items()
        }
    content = manifest_content if manifest_content is not None else _manifest(target, files)
    with tarfile.open(path, "w:gz") as bundle:
        manifest = tarfile.TarInfo("bundle/archive-manifest.json")
        manifest.size = len(content)
        bundle.addfile(manifest, io.BytesIO(content))
        for name, value in payload.items():
            member = tarfile.TarInfo(f"bundle/{name}")
            member.size = len(value)
            bundle.addfile(member, io.BytesIO(value))
            if duplicate_payload:
                bundle.addfile(member, io.BytesIO(value))
        for index in range(extra_manifests):
            member = tarfile.TarInfo(f"other{index}/archive-manifest.json")
            member.size = len(content)
            bundle.addfile(member, io.BytesIO(content))
        if special_type is not None:
            member = tarfile.TarInfo("bundle/special")
            member.type = special_type
            member.linkname = "app.txt"
            bundle.addfile(member)


def _runtime_archive(
    path: Path,
    entries: list[tuple[str, str, bytes | str, int]],
) -> None:
    """@brief Write regular, directory, and link runtime members in given order."""
    with tarfile.open(path, "w:gz") as bundle:
        for kind, name, value, mode in entries:
            member = tarfile.TarInfo(name)
            member.mode = mode
            if kind == "file":
                content = bytes(value)
                member.size = len(content)
                bundle.addfile(member, io.BytesIO(content))
            elif kind == "dir":
                member.type = tarfile.DIRTYPE
                bundle.addfile(member)
            else:
                member.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE
                member.linkname = str(value)
                bundle.addfile(member)


def _snapshot(root: Path) -> dict[str, tuple[bytes, bool]]:
    """@brief Capture portable materialized file bytes and execute metadata."""
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes(),
            bool(path.stat().st_mode & stat.S_IXUSR),
        )
        for path in sorted(
            (candidate for candidate in root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(root).as_posix(),
        )
    }


# TESTS


def test_epoch_selection_clamps_and_rounds_explicit_input(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """@brief SOURCE_DATE_EPOCH is authoritative, ZIP-safe, and two-second exact."""
    builder = _builder()
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1")
    assert builder._canonical_build_epoch() == builder.ZIP_MIN_EPOCH
    monkeypatch.setenv("SOURCE_DATE_EPOCH", str(builder.ZIP_MIN_EPOCH + 3))
    assert builder._canonical_build_epoch() == builder.ZIP_MIN_EPOCH + 2


@pytest.mark.parametrize("value", ["", "-1", "1.5", "not-an-epoch", "4294967295"])
def test_invalid_explicit_epoch_never_falls_back(value: str, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """@brief Malformed, negative, non-integer, and overflowing epochs are typed."""
    builder = _builder()
    monkeypatch.setenv("SOURCE_DATE_EPOCH", value)
    monkeypatch.setattr(builder, "_git_source_epoch", lambda: "315532800")
    with pytest.raises(builder.PackagingError, match="SOURCE_DATE_EPOCH"):
        builder._canonical_build_epoch()


def test_missing_epoch_uses_commit_then_fixed_fallback(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """@brief Missing explicit input selects Git time, then a source-archive fallback."""
    builder = _builder()
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    monkeypatch.setattr(builder, "_git_source_epoch", lambda: "315532803")
    assert builder._canonical_build_epoch() == 315532802
    monkeypatch.setattr(builder, "_git_source_epoch", lambda: None)
    assert builder._canonical_build_epoch() == builder.DETERMINISTIC_FALLBACK_EPOCH


def test_deterministic_zip_ignores_source_mtime_and_enumeration_order(tmp_path: Path) -> None:
    """@brief ZIP bytes and metadata depend on content/name/mode, not filesystem order."""
    builder = _builder()
    root = tmp_path / "source"
    root.mkdir()
    plain = root / "space ü.txt"
    executable = root / "run.sh"
    plain.write_bytes(b"plain")
    executable.write_bytes(b"#!/bin/sh\n")
    entries = [
        ("root/run.sh", executable, True),
        ("root/space ü.txt", plain, False),
    ]
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    epoch = builder.ZIP_MIN_EPOCH + 2
    builder._write_deterministic_zip(first, entries, epoch=epoch)
    os.utime(plain, (2_000_000_000, 2_000_000_000))
    os.utime(executable, (1_000_000_000, 1_000_000_000))
    builder._write_deterministic_zip(second, reversed(entries), epoch=epoch)
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as bundle:
        infos = bundle.infolist()
        assert [item.filename for item in infos] == [
            "root/run.sh",
            "root/space ü.txt",
        ]
        assert all(item.date_time == (1980, 1, 1, 0, 0, 2) for item in infos)
        assert all(item.create_system == 3 for item in infos)
        assert all(item.compress_type == zipfile.ZIP_DEFLATED for item in infos)
        assert [item.external_attr >> 16 for item in infos] == [
            stat.S_IFREG | 0o755,
            stat.S_IFREG | 0o644,
        ]


def test_deterministic_tar_gzip_normalizes_all_metadata(tmp_path: Path) -> None:
    """@brief tar entries and gzip header are byte-stable after source mtime changes."""
    builder = _builder()
    root = tmp_path / "source"
    (root / "nested").mkdir(parents=True)
    (root / "nested" / "space ü.txt").write_bytes(b"plain")
    (root / "run.sh").write_bytes(b"#!/bin/sh\n")
    epoch = builder.ZIP_MIN_EPOCH + 2
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    kwargs = {
        "archive_root": "root",
        "executable_paths": frozenset({"run.sh"}),
        "epoch": epoch,
    }
    builder._write_deterministic_tar_gz(first, root, **kwargs)
    for path in root.rglob("*"):
        os.utime(path, (2_000_000_000, 2_000_000_000))
    builder._write_deterministic_tar_gz(second, root, **kwargs)
    assert first.read_bytes() == second.read_bytes()
    raw = first.read_bytes()
    assert struct.unpack("<I", raw[4:8])[0] == epoch
    assert raw[3] & 0x08 == 0
    with tarfile.open(first, "r:gz") as bundle:
        members = bundle.getmembers()
        assert [member.name for member in members] == sorted(
            member.name for member in members
        )
        assert all(member.mtime == epoch for member in members)
        assert all(
            (member.uid, member.gid, member.uname, member.gname) == (0, 0, "", "")
            for member in members
        )
        modes = {member.name: member.mode for member in members}
        assert modes["root"] == modes["root/nested"] == 0o755
        assert modes["root/run.sh"] == 0o755
        assert modes["root/nested/space ü.txt"] == 0o644


def test_zipapp_and_release_metadata_are_stable_after_source_mtime_change(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """@brief The portable artifact, release manifest, and checksums are stable."""
    builder = _builder()
    source = tmp_path / "src"
    payload = tmp_path / "payload"
    package = source / "waegis"
    package.mkdir(parents=True)
    payload.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    (package / "version.py").write_text(
        'WIZARD_VERSION = "1.1.0"\n',
        encoding="utf-8",
    )
    (payload / "AGENTS.md").write_text("payload\n", encoding="utf-8")
    monkeypatch.setattr(builder, "SOURCE_ROOT", source)
    monkeypatch.setattr(builder, "PAYLOAD_ROOT", payload)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "315532803")
    outputs: list[dict[str, bytes]] = []
    for index in range(2):
        output = tmp_path / f"dist-{index}"
        builder.build_release(
            output,
            runtime_cache=tmp_path / "cache",
            offline=True,
            zipapp_only=True,
        )
        outputs.append(
            {
                name: (output / name).read_bytes()
                for name in ("waegis.pyz", "release-manifest.json", "SHA256SUMS")
            }
        )
        for path in source.rglob("*"):
            os.utime(path, (2_000_000_000, 2_000_000_000))
        for path in payload.rglob("*"):
            os.utime(path, (1_000_000_000, 1_000_000_000))
    assert outputs[0] == outputs[1]


def test_generated_complete_metadata_removes_volatile_identity(tmp_path: Path) -> None:
    """@brief uv command paths, SBOM UUID, and wall time are normalized."""
    builder = _builder()
    requirements = tmp_path / "locked-requirements.txt"
    requirements.write_text(
        "# This file was autogenerated by uv via the following command:\n"
        "#    uv export --output-file C:\\Temp\\random\\requirements.txt\n"
        "package==1.0\n",
        encoding="utf-8",
    )
    builder._normalize_requirements_export(requirements)
    assert requirements.read_text(encoding="utf-8") == (
        "# Locked requirements exported by WAEGIS Complete using uv.\n"
        "package==1.0\n"
    )
    sbom = tmp_path / "sbom.json"
    sbom.write_text(
        json.dumps(
            {
                "serialNumber": "urn:uuid:random",
                "metadata": {"timestamp": "wall-clock"},
            }
        ),
        encoding="utf-8",
    )
    builder._normalize_sbom(sbom, epoch=builder.ZIP_MIN_EPOCH + 2)
    document = json.loads(sbom.read_text(encoding="utf-8"))
    assert "serialNumber" not in document
    assert document["metadata"]["timestamp"] == "1980-01-01T00:00:02Z"


def test_ambiguous_archive_names_are_rejected() -> None:
    """@brief Backslash, traversal, drive, UNC, device, dot, and case collisions fail."""
    builder = _builder()
    for value in (
        r"a\b.txt",
        "../a",
        "/absolute",
        "C:/drive",
        "//server/share",
        "NUL.txt",
        "dir/.",
        "trailing.",
    ):
        with pytest.raises(builder.PackagingError):
            builder._canonical_relative_name(value)
    with pytest.raises(builder.PackagingError, match="case-colliding"):
        builder._reject_name_collisions(("Root/File", "root/file"), context="test")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.update(schema_version=2), "schema_version"),
        (lambda data: data.update(release="../redirect"), "release"),
        (lambda data: data.update(extra=True), "keys"),
        (lambda data: data.pop("provider"), "keys"),
        (lambda data: data.update(targets=[]), "targets"),
        (lambda data: data["targets"].pop("linux-x64"), "targets"),
        (
            lambda data: data["targets"]["windows-x64"].update(asset="../runtime"),
            "basename",
        ),
        (
            lambda data: data["targets"]["windows-x64"].update(sha256="abc"),
            "sha256",
        ),
        (
            lambda data: data["targets"]["windows-x64"].update(size=True),
            "size",
        ),
        (
            lambda data: data["targets"]["linux-x64"].update(asset="windows.tar.gz"),
            "unique",
        ),
        (
            lambda data: data["targets"]["windows-x64"].update(unknown=1),
            "keys",
        ),
    ],
)
def test_runtime_lock_closed_schema_rejects_invalid_values(
    tmp_path: Path,
    mutation,  # type: ignore[no-untyped-def]
    message: str,
) -> None:
    """@brief Every malformed lock class maps to an actionable PackagingError."""
    builder = _builder()
    document = _lock_document()
    mutation(document)
    path = tmp_path / "runtime-lock.json"
    _write_lock(path, document)
    with pytest.raises(builder.PackagingError, match=message):
        builder._load_lock(path)


def test_runtime_lock_file_and_json_failures_are_typed(tmp_path: Path) -> None:
    """@brief Missing, non-UTF-8, and malformed JSON locks never leak raw errors."""
    builder = _builder()
    for name, content in (
        ("missing.json", None),
        ("binary.json", b"\xff"),
        ("broken.json", b"{"),
    ):
        path = tmp_path / name
        if content is not None:
            path.write_bytes(content)
        with pytest.raises(builder.PackagingError):
            builder._load_lock(path)


def test_offline_cache_hit_and_miss_never_use_network(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """@brief Offline mode returns a verified hit and proves misses have no egress."""
    builder = _builder()
    payload = b"runtime"
    lock = tmp_path / "lock.json"
    _write_lock(lock, _lock_document(payload))
    cache = tmp_path / "cache"
    cache.mkdir()
    cached = cache / "windows.tar.gz"
    cached.write_bytes(payload)
    calls: list[str] = []
    monkeypatch.setattr(
        builder.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: calls.append("network"),
    )
    assert builder._download_runtime(
        "windows-x64",
        cache,
        offline=True,
        lock_file=lock,
    ) == cached
    cached.unlink()
    with pytest.raises(builder.PackagingError, match="offline"):
        builder._download_runtime(
            "windows-x64",
            cache,
            offline=True,
            lock_file=lock,
        )
    assert calls == []


def test_valid_online_cache_is_preserved_without_refresh(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """@brief A valid cache remains authoritative even when transport would fail."""
    builder = _builder()
    payload = b"runtime"
    lock = tmp_path / "lock.json"
    _write_lock(lock, _lock_document(payload))
    cache = tmp_path / "cache"
    cache.mkdir()
    cached = cache / "windows.tar.gz"
    cached.write_bytes(payload)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("valid cache must prevent refresh")

    monkeypatch.setattr(builder.urllib.request, "urlopen", forbidden)
    assert builder._download_runtime(
        "windows-x64",
        cache,
        offline=False,
        lock_file=lock,
    ) == cached
    assert cached.read_bytes() == payload


def test_successful_download_atomically_publishes_verified_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """@brief A matching streamed runtime replaces the cache with no temp residue."""
    builder = _builder()
    payload = b"runtime"
    lock = tmp_path / "lock.json"
    _write_lock(lock, _lock_document(payload))
    cache = tmp_path / "cache"
    monkeypatch.setattr(
        builder.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(payload),
    )
    result = builder._download_runtime(
        "windows-x64",
        cache,
        offline=False,
        lock_file=lock,
    )
    assert result.read_bytes() == payload
    assert list(cache.iterdir()) == [result]


def test_download_digest_mismatch_cleans_unique_temp_and_preserves_cache(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """@brief A mismatched stream never publishes or removes the prior cache object."""
    builder = _builder()
    lock = tmp_path / "lock.json"
    _write_lock(lock, _lock_document(b"expected"))
    cache = tmp_path / "cache"
    cache.mkdir()
    cached = cache / "windows.tar.gz"
    cached.write_bytes(b"prior-invalid-cache")
    protected = tmp_path / "protected.txt"
    protected.write_bytes(b"do-not-touch")
    predictable = cache / "windows.tar.gz.tmp"
    os.link(protected, predictable)
    monkeypatch.setattr(
        builder.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(b"wrong"),
    )
    with pytest.raises(builder.PackagingError, match="SHA-256"):
        builder._download_runtime(
            "windows-x64",
            cache,
            offline=False,
            lock_file=lock,
        )
    assert cached.read_bytes() == b"prior-invalid-cache"
    assert predictable.read_bytes() == b"do-not-touch"
    assert protected.read_bytes() == b"do-not-touch"
    assert sorted(path.name for path in cache.iterdir()) == [
        "windows.tar.gz",
        "windows.tar.gz.tmp",
    ]


@pytest.mark.parametrize(
    "failure",
    [OSError("write failed"), KeyboardInterrupt(), SystemExit(7)],
)
def test_download_interruption_cleans_temp_and_preserves_control_flow(
    tmp_path: Path,
    monkeypatch,
    failure: BaseException,
) -> None:  # type: ignore[no-untyped-def]
    """@brief Write failure and process interruption clean unpublished bytes."""
    builder = _builder()
    lock = tmp_path / "lock.json"
    _write_lock(lock, _lock_document(b"expected"))
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(
        builder.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(b"stream"),
    )

    def fail_copy(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(builder.shutil, "copyfileobj", fail_copy)
    expected_exception = (
        type(failure)
        if isinstance(failure, (KeyboardInterrupt, SystemExit))
        else builder.PackagingError
    )
    with pytest.raises(expected_exception):
        builder._download_runtime(
            "windows-x64",
            cache,
            offline=False,
            lock_file=lock,
        )
    assert list(cache.iterdir()) == []


def test_network_failure_cleans_download_temp(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """@brief Transport failure maps to PackagingError with no unpublished file."""
    builder = _builder()
    lock = tmp_path / "lock.json"
    _write_lock(lock, _lock_document(b"expected"))
    cache = tmp_path / "cache"

    def fail_network(*_args: object, **_kwargs: object) -> None:
        raise builder.urllib.error.URLError("offline fixture")

    monkeypatch.setattr(builder.urllib.request, "urlopen", fail_network)
    with pytest.raises(builder.PackagingError, match="cannot download"):
        builder._download_runtime(
            "windows-x64",
            cache,
            offline=False,
            lock_file=lock,
        )
    assert cache.is_dir() and list(cache.iterdir()) == []


@pytest.mark.parametrize("kind", ["zip", "tar"])
def test_exact_internal_archive_verification_accepts_valid_fixture(
    tmp_path: Path,
    kind: str,
) -> None:
    """@brief Valid ZIP and tar fixtures pass exact membership verification."""
    builder = _builder()
    path = tmp_path / ("valid.zip" if kind == "zip" else "valid.tar.gz")
    if kind == "zip":
        _write_zip_fixture(path)
        builder._verify_internal_zip(path, expected_target="windows-x64")
    else:
        _write_tar_fixture(path)
        builder._verify_internal_tar(path, expected_target="linux-x64")


@pytest.mark.parametrize("kind", ["zip", "tar"])
def test_internal_archive_requires_one_manifest(tmp_path: Path, kind: str) -> None:
    """@brief An otherwise readable archive with no manifest fails typed."""
    builder = _builder()
    path = tmp_path / ("missing.zip" if kind == "zip" else "missing.tar.gz")
    if kind == "zip":
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("bundle/app.txt", b"payload")
        call = lambda: builder._verify_internal_zip(
            path,
            expected_target="windows-x64",
        )
    else:
        with tarfile.open(path, "w:gz") as bundle:
            member = tarfile.TarInfo("bundle/app.txt")
            member.size = 7
            bundle.addfile(member, io.BytesIO(b"payload"))
        call = lambda: builder._verify_internal_tar(
            path,
            expected_target="linux-x64",
        )
    with pytest.raises(builder.PackagingError, match="exactly one"):
        call()


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing", "missing"),
        ("extra", "undeclared"),
        ("digest", "hash mismatch"),
        ("json", "malformed"),
        ("schema", "schema"),
        ("manifest", "exactly one"),
        ("duplicate", "duplicate"),
        ("case", "case-colliding"),
        ("target", "target"),
        ("path", "unsafe"),
        ("types", "digest"),
    ],
)
@pytest.mark.parametrize("kind", ["zip", "tar"])
def test_internal_archive_negative_paths_are_always_typed(
    tmp_path: Path,
    kind: str,
    case: str,
    message: str,
) -> None:
    """@brief Missing, extra, corrupt, ambiguous, and malformed fixtures fail typed."""
    builder = _builder()
    path = tmp_path / (f"{case}.zip" if kind == "zip" else f"{case}.tar.gz")
    kwargs: dict[str, Any] = {}
    if case == "missing":
        kwargs = {"payload": {}, "files": {"app.txt": "a" * 64}}
    elif case == "extra":
        kwargs = {"payload": {"app.txt": b"payload", "extra": b"x"}, "files": {"app.txt": hashlib.sha256(b"payload").hexdigest()}}
    elif case == "digest":
        kwargs = {"files": {"app.txt": "a" * 64}}
    elif case == "json":
        kwargs = {"manifest_content": b"{"}
    elif case == "schema":
        kwargs = {"manifest_content": b'{"schema_version":1,"target":"windows-x64"}' if kind == "zip" else b'{"schema_version":1,"target":"linux-x64"}'}
    elif case == "manifest":
        kwargs = {"extra_manifests": 1}
    elif case == "duplicate":
        kwargs = {"duplicate_payload": True}
    elif case == "case":
        kwargs = {"payload": {"File": b"x", "file": b"y"}}
    elif case == "target":
        kwargs = {"target": "linux-x64" if kind == "zip" else "windows-x64"}
    elif case == "path":
        kwargs = {"files": {"../escape": "a" * 64}}
    elif case == "types":
        kwargs = {"files": {1: 2}}
    if kind == "zip":
        _write_zip_fixture(path, **kwargs)
        verifier = lambda: builder._verify_internal_zip(path, expected_target="windows-x64")
    else:
        _write_tar_fixture(path, **kwargs)
        verifier = lambda: builder._verify_internal_tar(path, expected_target="linux-x64")
    with pytest.raises(builder.PackagingError, match=message):
        verifier()


@pytest.mark.parametrize(
    "member_type",
    [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE],
)
def test_tar_verifier_rejects_every_unsupported_member_type(
    tmp_path: Path,
    member_type: bytes,
) -> None:
    """@brief Symlink, hardlink, device, and FIFO payload entries are unsupported."""
    builder = _builder()
    path = tmp_path / "special.tar.gz"
    _write_tar_fixture(path, special_type=member_type)
    with pytest.raises(builder.PackagingError, match="unsupported"):
        builder._verify_internal_tar(path, expected_target="linux-x64")


def test_zip_verifier_rejects_symlink_and_raw_corruption(tmp_path: Path) -> None:
    """@brief ZIP symlink metadata and malformed container bytes map to PackagingError."""
    builder = _builder()
    link = tmp_path / "link.zip"
    _write_zip_fixture(link, special=("link", stat.S_IFLNK | 0o777))
    with pytest.raises(builder.PackagingError, match="unsupported"):
        builder._verify_internal_zip(link, expected_target="windows-x64")
    corrupt = tmp_path / "corrupt.zip"
    corrupt.write_bytes(b"not a zip")
    with pytest.raises(builder.PackagingError):
        builder._verify_internal_zip(corrupt, expected_target="windows-x64")
    bad_tar = tmp_path / "corrupt.tar.gz"
    bad_tar.write_bytes(b"not a tar")
    with pytest.raises(builder.PackagingError):
        builder._verify_internal_tar(bad_tar, expected_target="linux-x64")


def test_zip_verifier_rejects_encrypted_member_flag(tmp_path: Path) -> None:
    """@brief An encrypted ZIP member is rejected before password handling."""
    builder = _builder()
    path = tmp_path / "encrypted.zip"
    _write_zip_fixture(path)
    raw = bytearray(path.read_bytes())
    raw[6:8] = struct.pack("<H", struct.unpack("<H", raw[6:8])[0] | 1)
    central = raw.find(b"PK\x01\x02")
    assert central >= 0
    raw[central + 8 : central + 10] = struct.pack(
        "<H",
        struct.unpack("<H", raw[central + 8 : central + 10])[0] | 1,
    )
    path.write_bytes(raw)
    with pytest.raises(builder.PackagingError, match="encrypted"):
        builder._verify_internal_zip(path, expected_target="windows-x64")


@pytest.mark.parametrize(
    "unsafe",
    [
        "/absolute",
        "../escape",
        "C:/drive",
        "//server/share",
        r"device\name",
        "NUL.txt",
        "dot/.",
    ],
)
@pytest.mark.parametrize("kind", ["zip", "tar"])
def test_archive_manifest_rejects_platform_unsafe_declared_names(
    tmp_path: Path,
    kind: str,
    unsafe: str,
) -> None:
    """@brief Absolute, traversal, drive, UNC, device, dot, and backslash paths fail."""
    builder = _builder()
    path = tmp_path / ("unsafe.zip" if kind == "zip" else "unsafe.tar.gz")
    kwargs = {"files": {unsafe: "a" * 64}}
    if kind == "zip":
        _write_zip_fixture(path, **kwargs)
        call = lambda: builder._verify_internal_zip(
            path,
            expected_target="windows-x64",
        )
    else:
        _write_tar_fixture(path, **kwargs)
        call = lambda: builder._verify_internal_tar(
            path,
            expected_target="linux-x64",
        )
    with pytest.raises(builder.PackagingError):
        call()


def test_runtime_links_resolve_in_any_order_with_multihop_files(
    tmp_path: Path,
) -> None:
    """@brief Forward/backward and multi-hop file links materialize identically."""
    builder = _builder()
    entries = [
        ("file", "python/bin/python-real", b"runtime", 0o755),
        ("symlink", "python/bin/python-mid", "python-real", 0o777),
        ("symlink", "python/bin/python", "python-mid", 0o777),
    ]
    snapshots = []
    for index, ordered in enumerate((entries, list(reversed(entries)))):
        archive = tmp_path / f"runtime-{index}.tar.gz"
        destination = tmp_path / f"runtime-{index}"
        _runtime_archive(archive, ordered)
        executable = builder._extract_runtime(archive, destination)
        snapshots.append((_snapshot(destination), executable))
    assert snapshots[0] == snapshots[1]
    assert snapshots[0][0]["python/bin/python"][0] == b"runtime"
    assert "python/bin/python" in snapshots[0][1]


def test_runtime_directory_links_support_multihop_graphs(tmp_path: Path) -> None:
    """@brief Chained directory links deliberately copy their complete file trees."""
    builder = _builder()
    archive = tmp_path / "directories.tar.gz"
    _runtime_archive(
        archive,
        [
            ("dir", "python/lib", b"", 0o755),
            ("file", "python/lib/tool", b"tool", 0o755),
            ("symlink", "python/current", "lib", 0o777),
            ("symlink", "python/active", "current", 0o777),
        ],
    )
    destination = tmp_path / "runtime"
    executable = builder._extract_runtime(archive, destination)
    assert (destination / "python/current/tool").read_bytes() == b"tool"
    assert (destination / "python/active/tool").read_bytes() == b"tool"
    assert {"python/current/tool", "python/active/tool"} <= executable


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            [("symlink", "python/link", "missing", 0o777)],
            "unresolved",
        ),
        (
            [
                ("symlink", "python/a", "b", 0o777),
                ("symlink", "python/b", "a", 0o777),
            ],
            "cycle",
        ),
        (
            [("symlink", "python/link", "/absolute", 0o777)],
            "absolute",
        ),
        (
            [("symlink", "python/link", "../../escape", 0o777)],
            "escaping",
        ),
    ],
)
def test_runtime_link_graph_rejects_invalid_targets_before_writing(
    tmp_path: Path,
    entries: list[tuple[str, str, bytes | str, int]],
    message: str,
) -> None:
    """@brief Missing, cyclic, absolute, and escaping graphs leave no partial output."""
    builder = _builder()
    archive = tmp_path / "invalid.tar.gz"
    destination = tmp_path / "runtime"
    _runtime_archive(archive, entries)
    with pytest.raises(builder.PackagingError, match=message):
        builder._extract_runtime(archive, destination)
    assert not destination.exists() or list(destination.rglob("*")) == []


def test_runtime_rejects_members_written_through_link_parents(tmp_path: Path) -> None:
    """@brief Archive paths may not traverse a link-valued parent component."""
    builder = _builder()
    archive = tmp_path / "link-parent.tar.gz"
    destination = tmp_path / "runtime"
    _runtime_archive(
        archive,
        [
            ("dir", "python/real", b"", 0o755),
            ("symlink", "python/alias", "real", 0o777),
            ("file", "python/alias/injected", b"unsafe", 0o644),
        ],
    )
    with pytest.raises(builder.PackagingError, match="link parent"):
        builder._extract_runtime(archive, destination)
    assert not destination.exists() or list(destination.rglob("*")) == []


def test_verified_publication_preserves_prior_file_and_cleans_temp(
    tmp_path: Path,
) -> None:
    """@brief Verification failure preserves prior bytes; success replaces atomically."""
    builder = _builder()
    output = tmp_path / "artifact.zip"
    output.write_bytes(b"prior")

    def reject(_path: Path) -> None:
        raise builder.PackagingError("verification failed")

    with pytest.raises(builder.PackagingError, match="verification failed"):
        builder._write_deterministic_zip(
            output,
            [("root/file", b"new", False)],
            epoch=builder.ZIP_MIN_EPOCH,
            verify=reject,
        )
    assert output.read_bytes() == b"prior"
    assert list(tmp_path.iterdir()) == [output]
    builder._write_deterministic_zip(
        output,
        [("root/file", b"new", False)],
        epoch=builder.ZIP_MIN_EPOCH,
        verify=lambda path: zipfile.ZipFile(path).close(),
    )
    assert output.read_bytes() != b"prior"
    assert list(tmp_path.iterdir()) == [output]


def test_public_build_and_verify_helpers_map_unexpected_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """@brief Ordinary incidental exceptions do not escape public packaging APIs."""
    builder = _builder()

    def fail_build(*_args: object, **_kwargs: object) -> None:
        raise ValueError("incidental")

    monkeypatch.setattr(builder, "_build_release_impl", fail_build)
    with pytest.raises(builder.PackagingError, match="release build failed"):
        builder.build_release(
            tmp_path,
            runtime_cache=tmp_path / "cache",
            offline=True,
            zipapp_only=True,
        )
    monkeypatch.setattr(builder, "_verify_release_impl", fail_build)
    with pytest.raises(builder.PackagingError, match="release verification failed"):
        builder.verify_release(tmp_path)


# END OF FILE
