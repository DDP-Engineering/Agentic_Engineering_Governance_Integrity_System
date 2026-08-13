#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    build_aegis_light_release.py
@brief   Build the AEGIS Light delivery archives, checksums and manifest.
@details AEGIS Light is plain text with no dependencies and no build step, so
         the archives carry no embedded runtime and are not platform-specific:
         the zip and the tar.gz hold byte-identical trees and differ only in
         container format. Archive member timestamps are normalized, so
         rebuilding the same sources reproduces the same checksums.
@details The build refuses to package unverified or unexpected content: the
         payload test suite must pass, and the payload inventory must match
         the expected file list exactly.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Sequence

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT = REPO_ROOT / "05_Software" / "aegis-light"
PAYLOAD = PRODUCT / "template" / ".agentic"
USER_DOCS = REPO_ROOT / "06_SoftwareDocu" / "AEGIS-Light"
DELIVERY = REPO_ROOT / "07_Delivery"
DIST = DELIVERY / "dist"

NAME = "aegis-light"
MANIFEST_SCHEMA = 1

#: fixed member timestamp (1980-01-01), the earliest a zip entry may carry;
#: it makes rebuilds byte-identical instead of embedding the build clock.
FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
FIXED_MTIME = 315532800  # the same instant, for tar

#: the payload is the product; anything unexpected here must fail the build.
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
    "steps/6_deliver.md",
    "steps/adopt.md",
    "templates/component.md",
    "templates/requirement.toml",
    "templates/spec.md",
    "templates/task.md",
}

IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}

INSTALL_MD = """\
<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light {version} - install

Requires Python 3.11 or newer. Git is recommended; without it the
diff-based checks skip themselves and everything else still works.

1. Copy the `.agentic/` folder from this archive into the root of your
   repository.
2. Run the finishing step:

   ```
   python .agentic/aegis.py init
   ```

   (`python3` on Linux distributions without a `python` alias.)

3. Open `.agentic/aegis.toml` and point three keys at your project:
   `[commands] test`, `[layout] source` and `[layout] tests`.

Review the diff, then commit. Nothing else is installed: no hooks, no
services, no state outside your repository.

Then tell your agent:

```
using aegis workflow, implement <what you want>
```

`docs/` holds the guided tour - start with `01_Install_and_Setup.md`,
then `02_Folders_and_Files.md`, then the worked example that matches
your situation. `docs/08_Prompt_Cheatsheet.md` has copy-paste prompts
for every common operation. `.agentic/CLI.md` and
`docs/09_CLI_Reference.md` contain the complete command reference.
"""


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------


def collect(root: Path) -> list[Path]:
    """
    @brief      Every real file under root, cache directories excluded.
    @param[in]  root Directory to walk.
    @return     Sorted list of file paths.
    @exception  None
    """
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts)
    )


def payload_version() -> str:
    """
    @brief      The version the payload itself reports.
    @return     The non-empty `VERSION` string assigned in `aegis.py`.
    @details    The label on the archives is otherwise free text, so a stale
                default silently produces a release whose name disagrees with
                the CLI inside it.
    @exception  SystemExit If the payload is unreadable or has no valid version.
    """
    path = PAYLOAD / "aegis.py"
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise SystemExit(f"cannot read payload version: {exc}") from None

    value = None
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "VERSION"
                        for target in node.targets)):
            value = node.value
        elif (isinstance(node, ast.AnnAssign)
              and isinstance(node.target, ast.Name)
              and node.target.id == "VERSION"):
            value = node.value
    if (isinstance(value, ast.Constant) and isinstance(value.value, str)
            and value.value.strip()):
        return value.value.strip()
    raise SystemExit("payload aegis.py has no non-empty string VERSION assignment")


def verify_payload() -> None:
    """
    @brief      Fail the build when the payload is not exactly as expected.
    @return     None
    @exception  SystemExit If a file is missing or unexpected.
    """
    found = {path.relative_to(PAYLOAD).as_posix() for path in collect(PAYLOAD)}
    missing, extra = EXPECTED_PAYLOAD - found, found - EXPECTED_PAYLOAD
    if missing or extra:
        for name in sorted(missing):
            print(f"  missing from payload: {name}")
        for name in sorted(extra):
            print(f"  unexpected in payload: {name}")
        raise SystemExit("payload inventory does not match the expected set")
    print(f"payload verified: {len(found)} files")


def run_tests() -> None:
    """
    @brief      Run the product test suite; refuse to package a red tree.
    @return     None
    @exception  SystemExit If the suite fails or pytest is unavailable.
    """
    print("running the test suite ...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q"],
            cwd=str(PRODUCT), timeout=1800,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"could not run the test suite: {exc}") from None
    if result.returncode != 0:
        raise SystemExit("test suite failed - refusing to package")


def staged_tree(stage: Path, version: str) -> None:
    """
    @brief      Assemble the archive tree: payload, docs and entry documents.
    @param[in]  stage Empty directory to populate.
    @param[in]  version Release version, written into INSTALL.md.
    @return     None
    @exception  None
    """
    shutil.copytree(PAYLOAD, stage / ".agentic",
                    ignore=shutil.ignore_patterns(*IGNORED_PARTS))
    shutil.copy2(PRODUCT / "README.md", stage / "README.md")
    shutil.copy2(PAYLOAD / "LICENSE.txt", stage / "LICENSE.txt")
    (stage / "INSTALL.md").write_text(INSTALL_MD.format(version=version),
                                      encoding="utf-8", newline="\n")
    docs = stage / "docs"
    docs.mkdir()
    for path in sorted(USER_DOCS.glob("*.md")):
        shutil.copy2(path, docs / path.name)


def write_zip(target: Path, stage: Path, prefix: str) -> None:
    """
    @brief      Write a deterministic zip of the staged tree.
    @param[in]  target Destination archive path.
    @param[in]  stage Staged tree root.
    @param[in]  prefix Top-level directory name inside the archive.
    @return     None
    @exception  None
    """
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in collect(stage):
            member = f"{prefix}/{path.relative_to(stage).as_posix()}"
            info = zipfile.ZipInfo(member, date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def write_tar(target: Path, stage: Path, prefix: str) -> None:
    """
    @brief      Write a deterministic gzip tar of the staged tree.
    @param[in]  target Destination archive path.
    @param[in]  stage Staged tree root.
    @param[in]  prefix Top-level directory name inside the archive.
    @return     None
    @exception  None
    @details    The gzip container is written explicitly rather than through
                `tarfile.open(..., "w:gz")`, which stamps the build clock into
                the gzip header MTIME and the output path into its FNAME
                field. Normalizing the tar members alone left the inner stream
                identical while every rebuild produced a different outer
                checksum - the archive was reproducible in content but not in
                digest, which is the only form of it a release record can cite.
    """
    with open(target, "wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb",
                           compresslevel=9, mtime=FIXED_MTIME) as compressed:
            with tarfile.open(fileobj=compressed, mode="w",
                              format=tarfile.GNU_FORMAT) as archive:
                for path in collect(stage):
                    info = tarfile.TarInfo(
                        f"{prefix}/{path.relative_to(stage).as_posix()}")
                    data = path.read_bytes()
                    info.size = len(data)
                    info.mtime = FIXED_MTIME
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    archive.addfile(info, io.BytesIO(data))


def sha256_of(path: Path) -> str:
    """
    @brief      SHA-256 of a file, streamed.
    @param[in]  path File to digest.
    @return     Lowercase hexadecimal digest.
    @exception  None
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------


def build(version: str | None, record: bool) -> int:
    """
    @brief      Build the archives, checksums, manifest and release record.
    @param[in]  version Requested release version, or None for the payload value.
    @param[in]  record Also write the tracked publication record folder.
    @return     Process exit status.
    @exception  SystemExit On verification failure.
    """
    actual_version = payload_version()
    if version is not None and version != actual_version:
        raise SystemExit(
            f"requested release version {version!r} does not match "
            f"payload VERSION {actual_version!r}"
        )
    version = actual_version
    verify_payload()
    run_tests()

    prefix = f"{NAME}-{version}"
    DIST.mkdir(parents=True, exist_ok=True)
    stage = DIST / f".stage-{prefix}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    staged_tree(stage, version)

    artifacts = [DIST / f"{prefix}.zip", DIST / f"{prefix}.tar.gz"]
    write_zip(artifacts[0], stage, prefix)
    write_tar(artifacts[1], stage, prefix)
    shutil.rmtree(stage)

    digests = {path.name: sha256_of(path) for path in artifacts}
    sums = DIST / "SHA256SUMS"
    sums.write_text(
        "".join(f"{digests[path.name]}  {path.name}\n" for path in artifacts),
        encoding="utf-8", newline="\n",
    )
    manifest = {
        "aegis_light_version": version,
        "artifact_metadata": {
            path.name: {"edition": "payload", "sha256": digests[path.name],
                        "size": path.stat().st_size}
            for path in artifacts
        },
        "artifacts": digests,
        "schema_version": MANIFEST_SCHEMA,
    }
    manifest_path = DIST / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8", newline="\n")

    print(f"\nwrote {DIST}:")
    for path in [*artifacts, sums, manifest_path]:
        print(f"  {path.name:<28} {path.stat().st_size:>9,} bytes")

    if record:
        folder = DELIVERY / prefix
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sums, folder / "SHA256SUMS")
        shutil.copy2(manifest_path, folder / "release-manifest.json")
        print(f"\npublication record: {folder} "
              "(add RELEASE.md, then commit)")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    """
    @brief      Construct the command-line argument parser.
    @return     Configured :class:`argparse.ArgumentParser`.
    @exception  None
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=None,
                        help="release version (default: the payload's VERSION)")
    parser.add_argument("--no-record", action="store_true",
                        help="build dist/ only, skip the publication record")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """
    @brief      Command-line entry point.
    @param[in]  arguments Argument vector, or None to use sys.argv.
    @return     Process exit status.
    @exception  None
    """
    args = _build_arg_parser().parse_args(arguments)
    return build(args.version, not args.no_record)


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
