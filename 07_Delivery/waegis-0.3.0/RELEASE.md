<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS 0.3.0 Delivery Package

- **WAEGIS version**: 0.3.0
- **Bundled AEGIS payload**: 1.2.0
- **Compatible AEGIS payload range**: `>=0.4.0,<2.0`
- **Built**: 2026-07-24
- **Builder**: `05_Software/waegis/packaging/build_release.py` (stdlib-only)
- **Embedded runtime** (self-contained archives): CPython 3.13.13,
  astral-sh/python-build-standalone release 20260510, pinned by SHA-256 in
  `05_Software/waegis/packaging/runtime-lock.json`.

## Artifacts

| File | Size | Target | Needs on target |
| --- | --- | --- | --- |
| `waegis-0.3.0.pyz` | ~1.5 MB | Any OS | Python 3.11+ on `PATH` |
| `waegis-0.3.0-windows-x64.zip` | ~24 MB | Windows x64 | Nothing (embedded CPython) |
| `waegis-0.3.0-linux-x64.tar.gz` | ~69 MB | Linux x64 | Nothing (embedded CPython) |

The binaries themselves are not tracked in Git (see `.gitignore`); this record
and the checksums below are. Rebuild them from source with the command in the
`.gitignore`, or copy them from the builder's own `packaging/dist/` output.

## Checksums (SHA-256)

```text
813e2400a0155e3b0bc5ffc205750b7bce0fb6a82b57d8174f0df89270bbc49e  waegis-0.3.0-linux-x64.tar.gz
c2a441f3b34dbe84e04acf5b08eb55fe4df3519ea21c96cf57c1bb9ec3c2f954  waegis-0.3.0-windows-x64.zip
c070a532545bd12c393a80d06ed941ad65bf7832e4141849ddc98e2b9d9ff0d6  waegis-0.3.0.pyz
```

The `.pyz` wrapper hash varies between builds (zipapp embeds timestamps); the
bundled AEGIS payload content digest is stable at
`be60e07e771a2dc77acc3579abbb26b29926c5c2ca32e422e88915e3e4f19838`.

## Usage

Portable zipapp (Python 3.11+ present):

```bash
python waegis-0.3.0.pyz version
python waegis-0.3.0.pyz new /path/to/NewProject
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
