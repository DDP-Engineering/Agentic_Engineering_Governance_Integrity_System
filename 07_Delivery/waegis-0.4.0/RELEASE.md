<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS 0.4.0 Delivery Package

- **WAEGIS version**: 0.4.0
- **Bundled AEGIS payload**: 1.3.0
- **Compatible AEGIS payload range**: `>=0.4.0,<2.0`
- **Built**: 2026-07-25
- **Builder**: `05_Software/waegis/packaging/build_release.py` (stdlib-only)
- **Embedded runtime** (self-contained archives): CPython 3.13.13,
  astral-sh/python-build-standalone release 20260510, pinned by SHA-256 in
  `05_Software/waegis/packaging/runtime-lock.json`.

## What is new in this release

- **Shell write guard** (`guard_shell_write.py`): the AEGIS payload now enforces
  the configured write-zone and protected-path policy on file writes performed
  through the shell (`>`/`>>`, `tee`, `cp`/`mv`/`install`, `dd of=`, `sed -i`),
  wired into every adapter's shell matcher. In-repository targets only.
- **`waegis doctor` hook-launcher check** (`runnability.hook-runtime`): warns
  when `node` — the launcher every adapter runs the guards through — is not on
  `PATH`, since its absence silently disables enforcement.
- Additional AEGIS payload hardening (staged-secret scanning, Git rename-parse,
  non-ASCII secret matching, Git Bash runtime-path resolution). See the project
  `CHANGELOG.md` and `05_Software/aegis/template/CHANGELOG.md`.

## Artifacts

| File | Size | Target | Needs on target |
| --- | --- | --- | --- |
| `waegis-0.4.0.pyz` | ~1.5 MB | Any OS | Python 3.11+ on `PATH` |
| `waegis-0.4.0-windows-x64.zip` | ~24 MB | Windows x64 | Nothing (embedded CPython) |
| `waegis-0.4.0-linux-x64.tar.gz` | ~69 MB | Linux x64 | Nothing (embedded CPython) |

The binaries themselves are not tracked in Git (see `.gitignore`); this record
and the checksums below are. Rebuild them from source with the command in the
`.gitignore`, or copy them from the builder's own `dist/` output.

## Checksums (SHA-256)

```text
e19b67263f117d8e6faf4abc1fa4d1d9852b8fc70d940968157616a1fd17ea93  waegis-0.4.0-linux-x64.tar.gz
bfbbbfff68da160a5b58d90f4b59ee7054fd762dce5c05e1265357c2b3712cc8  waegis-0.4.0-windows-x64.zip
3179c0526640e8a11f243dbee5b4564a37e6a593eb36b72a680f13141e453612  waegis-0.4.0.pyz
```

The `.pyz` wrapper hash varies between builds (zipapp embeds timestamps); the
bundled AEGIS payload content digest is stable at
`c5d1d7b497887139bfa6636c6024fae7fe95c0eaff11d71145451c3a1be497dd`.

## Usage

Portable zipapp (Python 3.11+ present):

```bash
python waegis-0.4.0.pyz version
python waegis-0.4.0.pyz new /path/to/NewProject
```

Self-contained Windows archive (no Python required): unzip, then

```powershell
.\waegis-windows-x64\waegis.cmd version
```

Self-contained Linux archive (no Python required): extract, then

```bash
./waegis-linux-x64/waegis version
```

## Verify

```bash
sha256sum -c SHA256SUMS
```

Or with the builder itself:

```bash
uv run python 05_Software/waegis/packaging/build_release.py --output <dir> --verify-only
```
