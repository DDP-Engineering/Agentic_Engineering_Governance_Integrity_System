#!/usr/bin/env python3
"""Build deterministic AEGIS delivery archives and publication metadata."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT = REPO_ROOT / "05_Software" / "aegis"
PAYLOAD = PRODUCT / "template" / ".agentic"
USER_DOCS = REPO_ROOT / "06_SoftwareDocu"
DELIVERY = REPO_ROOT / "07_Delivery"
DIST = DELIVERY / "dist"
NAME = "aegis"
SCHEMA = 1
FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
FIXED_MTIME = 315532800
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
EXPECTED_PAYLOAD = {
    "AGENTS.md",
    "CLI.md",
    "LICENSE.txt",
    "aegis.py",
    "steps/1_frame.md",
    "steps/2_specify.md",
    "steps/3_design.md",
    "steps/4_build.md",
    "steps/5_validate.md",
    "steps/adopt.md",
    "steps/diagrams.md",
    "steps/review.md",
    "templates/component.md",
    "templates/environment.md",
    "templates/project.md",
    "templates/requirement.toml",
    "templates/spec.md",
    "templates/task.md",
}

INSTALL_MD = """\
<!--
SPDX-FileCopyrightText: 2026 DDP Engineering
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS {version} - install

Requires Python 3.11 or newer. Git is recommended; without it, Git-based
checks and repository evolution commands report that evidence is unavailable.

1. Copy `.agentic/` from this archive into the repository root.
2. Run `python .agentic/aegis.py init` (`python3` where required). If Git is
   installed but the target has no repository, rerun with `init --git` to
   create one explicitly.
3. Configure `[commands]` and `[layout]` in `.agentic/aegis.toml`.
4. Review the resulting repository diff before committing it.

AEGIS installs no runtime, service, hook, or third-party dependency. Start with
`docs/01_Install_and_Setup.md`; the complete CLI contract is in
`.agentic/CLI.md` and `docs/09_CLI_Reference.md`.
"""


def collect(root: Path) -> list[Path]:
    """Return a deterministic file inventory without generated caches."""
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts)
    )


def payload_version() -> str:
    """Read the literal VERSION assignment from the packaged CLI."""
    path = PAYLOAD / "aegis.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise SystemExit(f"cannot read payload version: {exc}") from None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "VERSION"
                for target in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(
                    node.value.value, str):
                return node.value.value
    raise SystemExit("payload aegis.py has no literal VERSION assignment")


def release_date(version: str) -> str:
    """Read the release date paired with the version in CHANGELOG.md."""
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$",
                      text, re.MULTILINE)
    if not match:
        raise SystemExit(f"CHANGELOG.md has no dated {version} release section")
    return match.group(1)


def verify_payload() -> None:
    """Refuse unexpected or incomplete payload content."""
    found = {path.relative_to(PAYLOAD).as_posix() for path in collect(PAYLOAD)}
    missing, extra = EXPECTED_PAYLOAD - found, found - EXPECTED_PAYLOAD
    if missing or extra:
        for name in sorted(missing):
            print(f"missing from payload: {name}")
        for name in sorted(extra):
            print(f"unexpected in payload: {name}")
        raise SystemExit("payload inventory does not match the expected set")
    print(f"payload verified: {len(found)} files")


def run_tests() -> None:
    """Run the complete AEGIS suite before packaging."""
    print("running the complete product test suite ...", flush=True)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests"],
            cwd=PRODUCT,
            env=environment,
            timeout=1800,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"could not run the product suite: {exc}") from None
    if result.returncode != 0:
        raise SystemExit("product suite failed; refusing to package")


def stage_tree(stage: Path, version: str) -> tuple[int, int]:
    """Assemble the portable release tree."""
    shutil.copytree(PAYLOAD, stage / ".agentic")
    shutil.copy2(PRODUCT / "README.md", stage / "README.md")
    shutil.copy2(REPO_ROOT / "CHANGELOG.md", stage / "CHANGELOG.md")
    shutil.copy2(PAYLOAD / "LICENSE.txt", stage / "LICENSE.txt")
    (stage / "INSTALL.md").write_text(
        INSTALL_MD.format(version=version), encoding="utf-8", newline="\n"
    )
    docs = stage / "docs"
    docs.mkdir()
    guide_files = sorted(USER_DOCS.glob("*.md"))
    for path in guide_files:
        shutil.copy2(path, docs / path.name)
    return len(EXPECTED_PAYLOAD), len(guide_files)


def write_zip(target: Path, stage: Path, prefix: str) -> None:
    """Write a deterministic ZIP archive."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in collect(stage):
            member = f"{prefix}/{path.relative_to(stage).as_posix()}"
            info = zipfile.ZipInfo(member, date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def write_tar(target: Path, stage: Path, prefix: str) -> None:
    """Write a deterministic gzip-compressed TAR archive."""
    with target.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9,
                           mtime=FIXED_MTIME) as compressed:
            with tarfile.open(fileobj=compressed, mode="w",
                              format=tarfile.GNU_FORMAT) as archive:
                for path in collect(stage):
                    data = path.read_bytes()
                    info = tarfile.TarInfo(
                        f"{prefix}/{path.relative_to(stage).as_posix()}"
                    )
                    info.size = len(data)
                    info.mtime = FIXED_MTIME
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    archive.addfile(info, io.BytesIO(data))


def sha256_of(path: Path) -> str:
    """Stream one file through SHA-256."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_members(path: Path) -> set[str]:
    """Read the regular-file member names from either archive format."""
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return {item.filename for item in archive.infolist() if not item.is_dir()}
    with tarfile.open(path, "r:gz") as archive:
        return {item.name for item in archive.getmembers() if item.isfile()}


def release_text(version: str, date: str, metadata: dict[str, dict]) -> str:
    """Create the tracked human-readable publication record."""
    rows = "\n".join(
        f"| {item['platform'].title()} | `{name}` | {item['size']:,} | "
        f"`{item['sha256']}` |"
        for name, item in sorted(metadata.items())
    )
    return f"""\
# AEGIS {version} delivery package

- Released: {date}
- Runtime: Python 3.11 or newer; none embedded
- Dependencies: Python standard library only
- Platforms: Windows ZIP and Linux tar.gz payloads

The `{version}` section of `CHANGELOG.md` records what this release changed.

| Platform | Artifact | Bytes | SHA-256 |
|---|---|---:|---|
{rows}

The archives under `../dist/` are ignored build outputs. This folder is the
tracked publication record used to verify those local artifacts.
"""


def build(requested: str | None) -> int:
    """Build archives plus deterministic checksum and publication records."""
    version = payload_version()
    if requested is not None and requested != version:
        raise SystemExit(
            f"requested version {requested!r} does not match payload {version!r}"
        )
    date = release_date(version)
    verify_payload()
    run_tests()
    prefix = f"{NAME}-{version}"
    DIST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{prefix}-", dir=DIST) as temporary:
        stage = Path(temporary)
        payload_count, docs_count = stage_tree(stage, version)
        artifacts = {
            "windows": DIST / f"{prefix}-windows.zip",
            "linux": DIST / f"{prefix}-linux.tar.gz",
        }
        write_zip(artifacts["windows"], stage, prefix)
        write_tar(artifacts["linux"], stage, prefix)
        expected = {
            f"{prefix}/{path.relative_to(stage).as_posix()}" for path in collect(stage)
        }
    for artifact in artifacts.values():
        if archive_members(artifact) != expected:
            raise SystemExit(f"archive inventory verification failed: {artifact.name}")
    metadata = {
        path.name: {
            "platform": platform,
            "sha256": sha256_of(path),
            "size": path.stat().st_size,
        }
        for platform, path in artifacts.items()
    }
    for obsolete in (DIST / f"{prefix}.zip", DIST / f"{prefix}.tar.gz"):
        obsolete.unlink(missing_ok=True)
    manifest = {
        "schema": SCHEMA,
        "product": NAME,
        "version": version,
        "release_date": date,
        "python": ">=3.11",
        "dependencies": "standard-library-only",
        "payload_file_count": payload_count,
        "documentation_file_count": docs_count,
        "artifacts": metadata,
    }
    record = DELIVERY / prefix
    record.mkdir(parents=True, exist_ok=True)
    sums = "".join(
        f"{item['sha256']}  {name}\n" for name, item in sorted(metadata.items())
    )
    (record / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    (record / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (record / "RELEASE.md").write_text(
        release_text(version, date, metadata), encoding="utf-8", newline="\n"
    )
    print(f"built AEGIS {version}:")
    for path in artifacts.values():
        print(f"  {path.relative_to(REPO_ROOT)} ({path.stat().st_size:,} bytes)")
    print(f"  publication record: {record.relative_to(REPO_ROOT)}")
    return 0


def main(arguments: Sequence[str] | None = None) -> int:
    """Parse command-line arguments and build the release."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="must match the payload VERSION")
    args = parser.parse_args(arguments)
    return build(args.version)


if __name__ == "__main__":
    raise SystemExit(main())
