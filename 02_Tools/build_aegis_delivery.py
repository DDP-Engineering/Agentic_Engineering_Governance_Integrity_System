#!/usr/bin/env python3
"""Build the host and documentation archives and the delivery records of a release."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

import build_aegis_release as core

REPO_ROOT = core.REPO_ROOT
DOCS = REPO_ROOT / "06_SoftwareDocu"
MANUALS = DOCS / "Plugin_Installation"
#: host folder -> (archive name part, display name, installation guide stem)
HOSTS = {
    "opencode": ("OpenCode", "OpenCode", "01_OpenCode_Installation"),
    "codex": ("Codex", "Codex", "02_Codex_Installation"),
    "pi": ("Pi", "Pi", "03_Pi_Installation"),
    "qwen": ("Qwen-Code", "Qwen Code", "04_Qwen_Code_Installation"),
    "claude": ("Claude-Code", "Claude Code", "05_Claude_Code_Installation"),
}
GUIDE = """\
# AEGIS {version} for {name}

Open the [installation guide](docs/Plugin_Installation/{stem}.md) or its \
[PDF](docs/Plugin_Installation/pdf/{stem}.pdf).

Run `Install-AEGIS.cmd` on Windows or `sh install.sh` on Linux. For an existing \
installation, use `node setup.mjs update` with the same profile options. Run \
`node setup.mjs doctor` for runtime and registration checks. Install the core \
separately in each repository.

The package README documents host-specific setup. Repository-wide source, planning \
and build links in the full manuals refer to the AEGIS source checkout. Each user \
supplies their own host account, provider, model, Node.js 22+, Python 3.11+ and Git.
"""
SET_GUIDE = """\
# AEGIS host integrations - {version}

Built on {date} for OpenCode, Codex, Pi, Qwen Code and Claude Code.

Choose your host's Windows ZIP or Linux tar.gz and extract the complete archive.
Open `INSTALLATION_GUIDE.md` for links to the included Markdown and PDF manuals.
Run `Install-AEGIS.cmd` on Windows or `sh install.sh` on Linux. Existing users
run `node setup.mjs update` from the new package with their existing profile
options, then restart the host.

Each user supplies their own host application and account/provider, Node.js 22+,
Python 3.11+ and Git. Install the core separately in every target repository.
Packages contain no runtime, model, credentials or installed user settings.
Run `node setup.mjs doctor` to check runtime and registration metadata.
"""


def members(tree: Path, prefix: str) -> list[tuple[str, bytes, int]]:
    """Every file of a tree as (archive name, bytes, mode); only install.sh runs."""
    found = []
    for path in core.collect(tree):
        data = path.read_bytes()
        text = path.suffix in {".md", ".mjs", ".js", ".json", ".txt", ".sh", ".toml"}
        if text and b"\r\n" in data:
            raise SystemExit(f"CRLF line endings in packaged text file: {path}")
        mode = 0o755 if path.name == "install.sh" else 0o644
        found.append((f"{prefix}/{path.relative_to(tree).as_posix()}", data, mode))
    return found


def write_zip(target: Path, items: list[tuple[str, bytes, int]]) -> None:
    """Write a deterministic ZIP archive that keeps the launcher's mode."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data, mode in items:
            info = zipfile.ZipInfo(name, date_time=core.FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            archive.writestr(info, data)


def write_tar(target: Path, items: list[tuple[str, bytes, int]]) -> None:
    """Write a deterministic gzip-compressed TAR archive."""
    with target.open("wb") as raw, gzip.GzipFile(
            filename="", fileobj=raw, mode="wb", compresslevel=9,
            mtime=core.FIXED_MTIME) as packed, tarfile.open(
            fileobj=packed, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for name, data, mode in items:
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(data), core.FIXED_MTIME, mode
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))


def inventory(items: list[tuple[str, bytes, int]]) -> dict[str, str]:
    """Member name -> SHA-256, for the tracked archive inventory."""
    return {name: hashlib.sha256(data).hexdigest() for name, data, _mode in items}


def git(*args: str) -> str:
    """Read one fact from Git; an unavailable answer stops the build."""
    done = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True, encoding="utf-8", check=False, timeout=120)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout


def build(requested: str) -> int:
    """Archive the five host packages and the guides; write the delivery records."""
    version = core.payload_version()
    if requested != version:
        raise SystemExit(f"requested version {requested!r} does not match payload {version!r}")
    date = core.release_date(version)
    dist, record = core.DIST, core.DELIVERY / f"{core.NAME}-{version}"
    core_names = [f"{core.NAME}-{version}-windows.zip", f"{core.NAME}-{version}-linux.tar.gz"]
    for name in core_names:
        if not (dist / name).is_file():
            raise SystemExit(f"build the core archives first: {name} is missing")
    host_dir = dist / f"agent-plugins-{version}"
    if host_dir.exists():
        shutil.rmtree(host_dir)
    host_dir.mkdir(parents=True)
    inventories: dict[str, dict[str, str]] = {}

    with tempfile.TemporaryDirectory(prefix=".delivery-", dir=dist) as temporary:
        staging = Path(temporary) / "hosts"
        done = subprocess.run(
            ["node", str(REPO_ROOT / "02_Tools" / "build_agent_plugins.mjs"),
             "--output", str(staging)], cwd=REPO_ROOT, check=False, timeout=600)
        if done.returncode != 0:
            raise SystemExit("host package assembly failed")
        for host, (label, name, stem) in HOSTS.items():
            tree = staging / f"aegis-{host}"
            docs = tree / "docs"
            shutil.copytree(MANUALS, docs / "Plugin_Installation")
            for guide in ("Agent_Plugins.md", "Project_Context.md"):
                shutil.copy2(DOCS / guide, docs / guide)
            (tree / "INSTALLATION_GUIDE.md").write_text(
                GUIDE.format(version=version, name=name, stem=stem),
                encoding="utf-8", newline="\n")
            items = members(tree, f"aegis-{host}")
            for suffix, writer in (("windows.zip", write_zip), ("linux.tar.gz", write_tar)):
                target = host_dir / f"AEGIS-{label}-{version}-{suffix}"
                writer(target, items)
                inventories[f"{host_dir.name}/{target.name}"] = inventory(items)

        guides = Path(temporary) / "guides"
        shutil.copytree(DOCS, guides)
        shutil.copy2(REPO_ROOT / "LICENSE.txt", guides / "LICENSE.txt")
        items = members(guides, f"aegis-documentation-{version}")
        documentation = dist / f"AEGIS-Documentation-{version}.zip"
        write_zip(documentation, items)
        inventories[documentation.name] = inventory(items)

    (host_dir / "INSTALL.md").write_text(
        SET_GUIDE.format(version=version, date=dt.date.today().isoformat()),
        encoding="utf-8", newline="\n")
    for name in core_names:
        path = dist / name
        if name.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                inventories[name] = {item.filename: hashlib.sha256(
                    archive.read(item)).hexdigest() for item in archive.infolist()}
        else:
            with tarfile.open(path, "r:gz") as archive:
                inventories[name] = {
                    item.name: hashlib.sha256(archive.extractfile(item).read()).hexdigest()
                    for item in archive.getmembers() if item.isfile()}

    artifacts = {name: {"sha256": core.sha256_of(dist / name),
                        "size": (dist / name).stat().st_size}
                 for name in sorted(inventories)}
    sums = "".join(f"{item['sha256']}  {name}\n" for name, item in artifacts.items())
    patch = git("diff", "HEAD")
    record.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": core.SCHEMA, "product": core.NAME, "version": version,
        "release_date": date, "build_date": dt.date.today().isoformat(),
        "build_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_branch": git("branch", "--show-current").strip(),
        "source_head": git("rev-parse", "HEAD").strip(),
        "source_changes": sorted(filter(None, git("diff", "HEAD", "--name-only").split("\n"))),
        "source_patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
        "artifacts": artifacts,
    }
    outputs = {
        dist / "SHA256SUMS": sums,
        record / "DELIVERY_SHA256SUMS": sums,
        record / "archive-inventories.json": json.dumps(
            inventories, indent=2, sort_keys=True) + "\n",
        record / "delivery-manifest.json": json.dumps(
            manifest, indent=2, sort_keys=True) + "\n",
        record / "source-preparation.diff": patch,
    }
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"built the AEGIS {version} delivery: {len(artifacts)} archives")
    for name, item in artifacts.items():
        print(f"  {name} ({item['size']:,} bytes, {len(inventories[name])} members)")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="must match the payload VERSION")
    raise SystemExit(build(parser.parse_args().version))
