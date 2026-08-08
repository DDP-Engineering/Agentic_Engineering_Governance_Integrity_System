#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Build/verify the payload-bearing zipapp and two locked native bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Mapping

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from waegis.copier import PayloadInventory, enumerate_payload, serialize_inventory  # noqa: E402
from waegis.locate import read_payload_version  # noqa: E402
from waegis.version import PAYLOAD_COMPAT_SPEC, WIZARD_VERSION  # noqa: E402

from runtime_bundle import (  # noqa: E402
    TARGETS,
    acquire_runtime,
    build_linux_bundle,
    build_windows_bundle,
    load_runtime_lock,
)

KNOWN_ARTIFACTS = frozenset({"waegis.pyz", "waegis-windows-x64.zip", "waegis-linux-x64.tar.gz"})


class BuildError(ValueError):
    """Raised when artifact construction or verification fails."""


def _digest(path: Path) -> tuple[int, str]:
    value = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            value.update(block)
            size += len(block)
    return size, value.hexdigest()


def _zip_info(name: str, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _payload_bytes(payload: Path, inventory: PayloadInventory) -> Mapping[str, bytes]:
    result: dict[str, bytes] = {}
    for record in inventory.records:
        data = payload.joinpath(*record.path.split("/")).read_bytes()
        if len(data) != record.size or hashlib.sha256(data).hexdigest() != record.sha256:
            raise BuildError(f"payload changed after inventory: {record.path}")
        result[f"payload/{record.path}"] = data
    return result


def _entries(payload: Path, inventory: PayloadInventory, payload_version: str) -> Mapping[str, bytes]:
    entries: dict[str, bytes] = {
        "__main__.py": (
            "import os\n"
            'os.environ.setdefault("WAEGIS_PACKAGING_TYPE", "zipapp")\n'
            "from waegis.cli import main\n"
            "raise SystemExit(main())\n"
        ).encode("utf-8"),
        "payload-inventory.json": serialize_inventory(inventory),
        "build-info.json": (
            json.dumps(
                {
                    "schema_version": 1,
                    "waegis_version": WIZARD_VERSION,
                    "payload_version": payload_version,
                    "payload_compatibility": PAYLOAD_COMPAT_SPEC,
                    "payload_digest": inventory.digest,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
    }
    for source in sorted((SOURCE_ROOT / "waegis").glob("*.py")):
        entries[f"waegis/{source.name}"] = source.read_bytes()
    entries.update(_payload_bytes(payload, inventory))
    folded: set[str] = set()
    for name in entries:
        if name.casefold() in folded:
            raise BuildError(f"case-colliding zipapp entry: {name}")
        folded.add(name.casefold())
    return entries


def build_zipapp(payload: Path, output: Path) -> tuple[str, PayloadInventory, str]:
    """Build one deterministic application archive with one payload copy."""
    payload_version = read_payload_version(payload)
    inventory = enumerate_payload(payload)
    entries = _entries(payload, inventory, payload_version)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compresslevel=9) as archive:
            for name in sorted(entries, key=lambda item: item.encode("utf-8")):
                mode = 0o755 if name.endswith((".sh", ".py")) else 0o644
                archive.writestr(_zip_info(name, mode), entries[name])
        verify_zipapp(temporary, inventory)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return payload_version, inventory, _digest(output)[1]


def verify_zipapp(path: Path, inventory: PayloadInventory | None = None) -> dict[str, object]:
    """Verify safe unique membership and the closed embedded payload inventory."""
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BuildError(f"cannot open zipapp: {exc}") from exc
    with archive:
        names: set[str] = set()
        folded: set[str] = set()
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if not name or name.startswith("/") or ".." in Path(name).parts:
                raise BuildError(f"unsafe zipapp entry: {info.filename}")
            if name in names or name.casefold() in folded or info.is_dir() or info.flag_bits & 0x1:
                raise BuildError(f"duplicate, directory, or encrypted zipapp entry: {name}")
            names.add(name)
            folded.add(name.casefold())
        try:
            embedded = json.loads(archive.read("payload-inventory.json"))
        except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
            raise BuildError(f"embedded inventory is invalid: {exc}") from exc
        expected = inventory.to_dict() if inventory else embedded
        if embedded != expected:
            raise BuildError("embedded inventory differs from expected inventory")
        declared = {f"payload/{item['path']}" for item in embedded["files"]}
        actual = {name for name in names if name.startswith("payload/")}
        if actual != declared:
            raise BuildError(f"zipapp payload membership differs; missing={sorted(declared-actual)}, extra={sorted(actual-declared)}")
        for item in embedded["files"]:
            data = archive.read(f"payload/{item['path']}")
            if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise BuildError(f"zipapp payload digest mismatch: {item['path']}")
    return embedded


def _atomic_bundle(builder, runtime: Path, source, zipapp: Path, output: Path) -> None:  # type: ignore[no-untyped-def]
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        builder(runtime, source, zipapp, temporary)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def write_release(output: Path, payload_version: str, inventory: PayloadInventory, artifacts: Mapping[str, Path]) -> None:
    """Publish the common artifact identity manifest and corruption checksums."""
    records = {
        name: {"size": _digest(path)[0], "sha256": _digest(path)[1]}
        for name, path in sorted(artifacts.items())
    }
    zipapp_digest = records["waegis.pyz"]["sha256"]
    manifest = {
        "schema_version": 1,
        "waegis_version": WIZARD_VERSION,
        "payload_version": payload_version,
        "payload_compatibility": PAYLOAD_COMPAT_SPEC,
        "payload_digest": inventory.digest,
        "zipapp_sha256": zipapp_digest,
        "artifacts": records,
    }
    manifest_path = output / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summed = {**artifacts, "release-manifest.json": manifest_path}
    checksums = "".join(f"{_digest(path)[1]}  {name}\n" for name, path in sorted(summed.items()))
    (output / "SHA256SUMS").write_text(checksums, encoding="utf-8")


def verify_release(output: Path) -> None:
    """Verify every published artifact against both manifest and SHA256SUMS."""
    try:
        manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
        sums = (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read release metadata: {exc}") from exc
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "waegis_version",
        "payload_version",
        "payload_compatibility",
        "payload_digest",
        "zipapp_sha256",
        "artifacts",
    }:
        raise BuildError("release manifest schema is invalid")
    records = manifest["artifacts"]
    if not isinstance(records, dict) or "waegis.pyz" not in records or not set(records) <= KNOWN_ARTIFACTS:
        raise BuildError("release artifact names are invalid")
    expected_files = set(records) | {"release-manifest.json", "SHA256SUMS"}
    try:
        actual_files = {path.name for path in output.iterdir()}
    except OSError as exc:
        raise BuildError(f"cannot enumerate release output: {exc}") from exc
    if actual_files != expected_files or any(not (output / name).is_file() for name in actual_files):
        raise BuildError(
            f"release output membership differs; missing={sorted(expected_files-actual_files)}, "
            f"unexpected={sorted(actual_files-expected_files)}"
        )
    for name, record in records.items():
        if (
            not isinstance(record, dict)
            or set(record) != {"size", "sha256"}
            or not isinstance(record["size"], int)
            or isinstance(record["size"], bool)
            or record["size"] < 0
            or not isinstance(record["sha256"], str)
            or len(record["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in record["sha256"])
        ):
            raise BuildError(f"release artifact record is invalid: {name}")
        path = output / name
        if _digest(path) != (record["size"], record["sha256"]):
            raise BuildError(f"artifact digest mismatch: {name}")
    expected_sums: dict[str, str] = {}
    for line in sums:
        digest, separator, name = line.partition("  ")
        if (
            separator != "  "
            or name not in expected_files - {"SHA256SUMS"}
            or name in expected_sums
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise BuildError("SHA256SUMS schema or membership is invalid")
        expected_sums[name] = digest
    if set(expected_sums) != expected_files - {"SHA256SUMS"}:
        raise BuildError("SHA256SUMS membership is incomplete")
    for name in (*records, "release-manifest.json"):
        if expected_sums.get(name) != _digest(output / name)[1]:
            raise BuildError(f"SHA256SUMS mismatch: {name}")
    if manifest["zipapp_sha256"] != records["waegis.pyz"]["sha256"]:
        raise BuildError("release zipapp identity is inconsistent")
    verify_zipapp(output / "waegis.pyz")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PACKAGE_ROOT / "dist")
    parser.add_argument("--payload", type=Path, default=PACKAGE_ROOT.parent / "aegis" / "template")
    parser.add_argument("--cache", type=Path, default=PACKAGE_ROOT / "packaging" / "cache")
    parser.add_argument("--fetch", action="store_true", help="fetch only exact locked runtime cache misses")
    parser.add_argument("--zipapp-only", action="store_true")
    parser.add_argument("--verify", action="store_true", help="verify an existing output directory")
    args = parser.parse_args(argv)
    if args.verify:
        verify_release(args.output)
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    selected = {"waegis.pyz"} if args.zipapp_only else set(KNOWN_ARTIFACTS)
    for name in KNOWN_ARTIFACTS - selected:
        (args.output / name).unlink(missing_ok=True)
    zipapp = args.output / "waegis.pyz"
    payload_version, inventory, _ = build_zipapp(args.payload.resolve(), zipapp)
    artifacts: dict[str, Path] = {"waegis.pyz": zipapp}
    if not args.zipapp_only:
        _, sources = load_runtime_lock(PACKAGE_ROOT / "packaging" / "runtime-lock.json")
        for target in TARGETS:
            runtime = acquire_runtime(sources[target], args.cache, fetch=args.fetch)
            if target == "windows-x64":
                name, builder = "waegis-windows-x64.zip", build_windows_bundle
            else:
                name, builder = "waegis-linux-x64.tar.gz", build_linux_bundle
            artifacts[name] = args.output / name
            _atomic_bundle(builder, runtime, sources[target], zipapp, artifacts[name])
    write_release(args.output, payload_version, inventory, artifacts)
    verify_release(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# END OF FILE
