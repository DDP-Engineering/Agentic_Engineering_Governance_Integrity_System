#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Build and inspect deterministic AEGIS release archives from local inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tomllib
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

SUPPORTED_PRODUCTS = {"aegis", "waegis"}
SUPPORTED_PLATFORMS = {"windows-x86_64", "ubuntu-22.04-x86_64"}
ZIP_TIME = (2026, 1, 1, 0, 0, 0)


class BuildError(ValueError):
    """Report a refused archive build without leaving a partial archive."""


class InspectionError(ValueError):
    """Report an archive that is unsafe, inconsistent, or non-exact."""


class PayloadError(ValueError):
    """Report an invalid or non-exact canonical payload."""


def _safe_payload_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise PayloadError(f"Unsafe payload path: {value!r}")
    return path.as_posix()


def render_manifest(files: dict[str, bytes], version: str, *, platform: str) -> bytes:
    """Render exact manifest bytes from an assembled payload file mapping."""
    entries = [
        (relative, len(content), hashlib.sha256(content).hexdigest())
        for relative, content in sorted(files.items())
        if relative != "manifest.toml"
    ]
    identity_source = "\n".join(
        f"{relative}\0{size}\0{digest}" for relative, size, digest in entries
    ).encode("utf-8")
    payload_id = hashlib.sha256(identity_source).hexdigest()[:32]
    lines = [
        "schema = 1",
        'artifact_type = "payload_manifest"',
        f'payload_id = "PAYLOAD-{payload_id}"',
        'product = "AEGIS"',
        f'product_version = "{version}"',
        f'platform = "{platform}"',
        'architecture = "x86_64"',
        "",
    ]
    for relative, size, digest in entries:
        lines.extend(
            [
                "[[files]]",
                f'path = "{relative}"',
                f"size = {size}",
                f'sha256 = "{digest}"',
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def generate_manifest(
    payload_root: Path, version: str, *, platform: str = "source"
) -> bytes:
    """Render a sorted complete manifest for every regular payload file."""
    files: dict[str, bytes] = {}
    for path in sorted(payload_root.rglob("*"), key=lambda item: item.as_posix()):
        if (
            not path.is_file()
            or path.name == "manifest.toml"
            or "__pycache__" in path.parts
        ):
            continue
        files[path.relative_to(payload_root).as_posix()] = path.read_bytes()
    return render_manifest(files, version, platform=platform)


def verify_manifest(
    payload_root: Path, *, exact_bytes: bool = True
) -> dict[str, bytes]:
    """Return manifest-owned bytes or reject inventory and optional byte drift."""
    try:
        manifest = (payload_root / "manifest.toml").read_bytes()
        data = tomllib.loads(manifest.decode("utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PayloadError(f"Payload manifest is invalid: {exc}") from exc
    if data.get("schema") != 1 or data.get("artifact_type") != "payload_manifest":
        raise PayloadError("Payload manifest schema is unsupported")
    files: dict[str, bytes] = {"manifest.toml": manifest}
    for entry in data.get("files", []):
        relative = _safe_payload_path(str(entry.get("path", "")))
        if relative in files:
            raise PayloadError(f"Duplicate payload path: {relative}")
        try:
            candidate = (payload_root / Path(relative)).resolve(strict=True)
            candidate.relative_to(payload_root.resolve())
            content = candidate.read_bytes()
        except (OSError, ValueError) as exc:
            raise PayloadError(f"Missing payload file: {relative}") from exc
        differs = len(content) != entry.get("size") or (
            hashlib.sha256(content).hexdigest() != entry.get("sha256")
        )
        if exact_bytes and differs:
            raise PayloadError(f"Payload digest mismatch: {relative}")
        files[relative] = content
    actual = {
        path.relative_to(payload_root).as_posix()
        for path in payload_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if actual != set(files):
        differences = sorted(actual.symmetric_difference(files))
        raise PayloadError(f"Payload inventory mismatch: {differences}")
    return files


def _regular_files(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def _runtime_inputs(lock_path: Path, platform: str) -> dict[str, dict[str, Any]]:
    try:
        data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise BuildError(f"Runtime input lock is invalid: {exc}") from exc
    if data.get("schema") != 1:
        raise BuildError("Runtime input lock schema is unsupported")
    return {
        str(entry["component"]): entry
        for entry in data.get("inputs", [])
        if entry.get("platform") == platform
    }


def _require_runtime_inputs(
    lock_path: Path, platform: str
) -> dict[str, dict[str, Any]]:
    selected = _runtime_inputs(lock_path, platform)
    for component in ("python", "git"):
        entry = selected.get(component)
        if not entry or not entry.get("supplied"):
            raise BuildError(
                f"Locked {component} runtime input is not supplied for {platform}"
            )
        archive = Path(str(entry.get("archive_path", ""))).resolve()
        if not archive.is_file() or not entry.get("version") or not entry.get("sha256"):
            raise BuildError(
                f"Locked {component} runtime input is incomplete for {platform}"
            )
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise BuildError(
                f"Locked {component} runtime digest mismatch for {platform}"
            )
        if component == "python" and not str(entry["version"]).startswith("3.12."):
            raise BuildError(
                "Bundled Python runtime must be an exact Python 3.12 input"
            )
    return selected


def _runtime_files(
    entries: dict[str, dict[str, Any]], platform: str, product: str
) -> dict[str, bytes]:
    """Verify and namespace every member of the exact locked runtime archives."""
    files: dict[str, bytes] = {}
    for component, entry in sorted(entries.items()):
        archive_path = Path(str(entry["archive_path"])).resolve()
        try:
            with zipfile.ZipFile(archive_path) as bundle:
                seen: set[str] = set()
                for info in bundle.infolist():
                    if info.is_dir():
                        continue
                    member = PurePosixPath(info.filename)
                    safe = (
                        bool(info.filename)
                        and not member.is_absolute()
                        and ".." not in member.parts
                        and "\\" not in info.filename
                    )
                    relative = member.as_posix()
                    if not safe or relative in seen:
                        raise BuildError(
                            f"Locked {component} archive has an unsafe path"
                        )
                    seen.add(relative)
                    root = ".agentic/aegis/runtime" if product == "aegis" else "runtime"
                    files[f"{root}/{component}/{relative}"] = bundle.read(info)
        except zipfile.BadZipFile as exc:
            raise BuildError(
                f"Locked {component} runtime input is not a ZIP archive"
            ) from exc
    root = ".agentic/aegis/runtime" if product == "aegis" else "runtime"
    expected = (
        (f"{root}/python/python.exe", f"{root}/git/cmd/git.exe")
        if platform == "windows-x86_64"
        else (f"{root}/python/bin/python3", f"{root}/git/bin/git")
    )
    missing = [path for path in expected if path not in files]
    if missing:
        raise BuildError(
            f"Locked runtime archive lacks required launch path: {missing[0]}"
        )
    return files


def _launcher_files(product: str, platform: str) -> dict[str, bytes]:
    name = product
    python_launcher = f"""#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "lib"))
from {name}.composition import main
raise SystemExit(main(sys.argv[1:]))
    """.encode()
    if platform == "windows-x86_64":
        wrapper = (
            b"@echo off\r\n"
            b"setlocal\r\n"
            b'set "ROOT=%~dp0.."\r\n'
            b'if exist "%ROOT%\\runtime\\git\\cmd\\git.exe" '
            b'set "PATH=%ROOT%\\runtime\\git\\cmd;%PATH%"\r\n'
            b'if exist "%ROOT%\\runtime\\python\\python.exe" '
            b'("%ROOT%\\runtime\\python\\python.exe" "%~dp0launcher.py" %*) '
            b'else (py -3 "%~dp0launcher.py" %*)\r\n'
            b"exit /b %ERRORLEVEL%\r\n"
        )
        return {"bin/launcher.py": python_launcher, f"bin/{name}.cmd": wrapper}
    wrapper = (
        b"#!/bin/sh\n"
        b"set -eu\n"
        b'root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\n'
        b'if [ -x "$root/runtime/git/bin/git" ]; then '
        b'PATH="$root/runtime/git/bin:$PATH"; export PATH; fi\n'
        b'if [ -x "$root/runtime/python/bin/python3" ]; then '
        b'exec "$root/runtime/python/bin/python3" "$root/bin/launcher.py" "$@"; fi\n'
        b'exec python3 "$root/bin/launcher.py" "$@"\n'
    )
    return {"bin/launcher.py": python_launcher, f"bin/{name}": wrapper}


def _product_files(repository: Path, product: str, platform: str) -> dict[str, bytes]:
    template = repository / "05_Software/aegis/template"
    payload = template / ".agentic/aegis"
    try:
        # Git may materialize platform line endings in a clean checkout. The
        # archive receives a new exact-byte manifest below, while this check
        # still rejects missing, added, duplicate, and unsafe payload paths.
        verify_manifest(payload, exact_bytes=False)
    except PayloadError as exc:
        raise BuildError(str(exc)) from exc
    manifest = generate_manifest(
        payload,
        "1.0.0",
        platform="windows" if platform == "windows-x86_64" else "linux",
    )
    if product == "aegis":
        files = _regular_files(template)
        files[".agentic/aegis/manifest.toml"] = manifest
        return files
    source = repository / "05_Software/waegis/src/waegis"
    files = {
        f"lib/waegis/{path}": content
        for path, content in _regular_files(source).items()
    }
    files.update(
        {
            f"lib/waegis/payload/.agentic/aegis/{path}": content
            for path, content in _regular_files(payload).items()
        }
    )
    files["lib/waegis/payload/.agentic/aegis/manifest.toml"] = manifest
    files.update(_launcher_files(product, platform))
    return files


def _write_zip(path: Path, files: dict[str, bytes]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as bundle:
            for name, content in sorted(files.items()):
                info = zipfile.ZipInfo(name, ZIP_TIME)
                info.create_system = 3
                info.external_attr = (
                    0o755 if name.endswith(("/aegis", "/waegis")) else 0o644
                ) << 16
                bundle.writestr(info, content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_archive(
    repository: Path,
    output_directory: Path,
    *,
    product: str,
    platform: str,
    with_dependencies: bool,
    runtime_lock: Path,
) -> Path:
    """Build one exact archive or refuse unavailable dependency inputs."""
    repository = repository.resolve()
    if product not in SUPPORTED_PRODUCTS or platform not in SUPPORTED_PLATFORMS:
        raise BuildError("Unsupported product or platform archive request")
    runtime_entries: dict[str, dict[str, Any]] = {}
    if with_dependencies:
        runtime_entries = _require_runtime_inputs(runtime_lock.resolve(), platform)
    files = _product_files(repository, product, platform)
    if with_dependencies:
        files.update(_runtime_files(runtime_entries, platform, product))
        if product == "aegis":
            prefix = ".agentic/aegis/"
            payload_files = {
                path.removeprefix(prefix): content
                for path, content in files.items()
                if path.startswith(prefix) and path != f"{prefix}manifest.toml"
            }
            files[f"{prefix}manifest.toml"] = render_manifest(
                payload_files,
                "1.0.0",
                platform="windows" if platform == "windows-x86_64" else "linux",
            )
    prerequisites = (
        ["Bundled locked Python 3.12 runtime", "Bundled locked Git runtime"]
        if with_dependencies
        else [
            "Python >=3.11,<4 available to the launcher",
            "Git with porcelain-v2 support available to the launcher",
        ]
    )
    files["PREREQUISITES.md"] = (
        "# Runtime prerequisites\n\n"
        + "\n".join(f"- {item}" for item in prerequisites)
        + "\n"
    ).encode("utf-8")

    def ownership(name: str) -> str:
        if "/runtime/" in name or name.startswith("runtime/"):
            return "private_runtime"
        if name.startswith(".agentic/aegis/") or ("/payload/.agentic/aegis/" in name):
            return "aegis_payload"
        if name.startswith(".agentic/"):
            return "project_starter"
        if name.startswith(("lib/waegis/", "bin/")):
            return "waegis_product"
        return "release_metadata"

    inventory_files = [
        {
            "path": name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
            "ownership": ownership(name),
        }
        for name, content in sorted(files.items())
    ]
    inventory = {
        "schema": "aegis.archive.inventory",
        "schema_version": 1,
        "product": product,
        "product_version": "1.0.0",
        "protocol_version": 1,
        "platform": platform,
        "architecture": "x86_64",
        "with_dependencies": with_dependencies,
        "python_version": (
            runtime_entries["python"]["version"]
            if with_dependencies
            else "external >=3.11,<4"
        ),
        "git_version": (
            runtime_entries["git"]["version"]
            if with_dependencies
            else "external porcelain-v2 compatible"
        ),
        "prerequisites": prerequisites,
        "runtime_inputs": [
            {
                "component": component,
                "version": entry["version"],
                "sha256": entry["sha256"],
            }
            for component, entry in sorted(runtime_entries.items())
        ],
        "files": inventory_files,
    }
    files["ARCHIVE_INVENTORY.json"] = (
        json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    output_directory.mkdir(parents=True, exist_ok=True)
    edition = "with-dependencies" if with_dependencies else "external-runtime"
    output = output_directory / f"{product}-1.0.0-{platform}-{edition}.zip"
    _write_zip(output, files)
    return output


def _safe_archive_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
    )


def inspect_archive(path: Path) -> dict[str, Any]:
    """Verify an archive entirely before any caller extracts it."""
    try:
        with zipfile.ZipFile(path) as bundle:
            names = [entry.filename for entry in bundle.infolist()]
            if len(names) != len(set(names)) or not all(
                _safe_archive_path(name) for name in names
            ):
                raise InspectionError("Archive contains an unsafe or duplicate path")
            if "ARCHIVE_INVENTORY.json" not in names:
                raise InspectionError("Archive inventory is missing")
            try:
                inventory = json.loads(
                    bundle.read("ARCHIVE_INVENTORY.json").decode("utf-8")
                )
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise InspectionError("Archive inventory is invalid") from exc
            declared = {entry["path"]: entry for entry in inventory.get("files", [])}
            actual = set(names) - {"ARCHIVE_INVENTORY.json"}
            if actual != set(declared):
                raise InspectionError(
                    "Archive inventory does not match archive members"
                )
            for name, entry in declared.items():
                content = bundle.read(name)
                digest = hashlib.sha256(content).hexdigest()
                if len(content) != entry.get("size") or digest != entry.get("sha256"):
                    raise InspectionError(f"Archive inventory digest mismatch: {name}")
            lowered = {name.lower() for name in names}
            if any(name.endswith("pyvenv.cfg") for name in lowered):
                raise InspectionError(
                    "Archive contains a persistent virtual-environment marker"
                )
            bundled = bool(inventory.get("with_dependencies"))
            runtime_members = [
                name
                for name in names
                if name.startswith(("runtime/", ".agentic/aegis/runtime/"))
            ]
            if not bundled and runtime_members:
                raise InspectionError(
                    "External-runtime archive unexpectedly contains runtime files"
                )
            if bundled and not inventory.get("runtime_inputs"):
                raise InspectionError("Bundled archive has no locked runtime inputs")
            return {
                "product": inventory.get("product"),
                "platform": inventory.get("platform"),
                "with_dependencies": bundled,
                "file_count": len(declared),
            }
    except zipfile.BadZipFile as exc:
        raise InspectionError("Archive is not a valid ZIP file") from exc


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and inspect deterministic offline AEGIS archives."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build one release archive.")
    build.add_argument("--repository", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--product", choices=sorted(SUPPORTED_PRODUCTS), required=True)
    build.add_argument("--platform", choices=sorted(SUPPORTED_PLATFORMS), required=True)
    build.add_argument("--with-dependencies", action="store_true")
    build.add_argument(
        "--runtime-lock",
        default=str(Path(__file__).with_name("runtime_inputs.toml")),
    )
    inspect = subparsers.add_parser("inspect", help="Inspect one release archive.")
    inspect.add_argument("archive")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one local build or inspection command."""
    args = _argument_parser().parse_args(argv)
    try:
        if args.command == "build":
            archive = build_archive(
                Path(args.repository),
                Path(args.output),
                product=args.product,
                platform=args.platform,
                with_dependencies=args.with_dependencies,
                runtime_lock=Path(args.runtime_lock),
            )
            print(archive)
        else:
            print(json.dumps(inspect_archive(Path(args.archive)), sort_keys=True))
    except BuildError as exc:
        print(f"Build refused: {exc}", file=sys.stderr)
        return 2
    except (InspectionError, OSError) as exc:
        print(f"Inspection failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
