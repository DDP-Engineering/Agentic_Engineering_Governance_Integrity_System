<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS 0.3.0 Delivery Package

- **WAEGIS version**: 0.3.0
- **Bundled AEGIS payload**: 1.1.0
- **Compatible AEGIS payload range**: `>=0.4.0,<2.0`
- **Built**: 2026-07-23
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
e8b19865dd7ca83985844bb53be23340115997d25ba4b546ad34d692e9de271b  waegis-0.3.0-linux-x64.tar.gz
f501ab57b6f0d4be61f287d83669b4c558cbbdd40243bd19972afd7cb8a6015f  waegis-0.3.0-windows-x64.zip
2bf496db42459e093f1b6f1b402cd0a8d739eb85d25a1e28d782f228329013bd  waegis-0.3.0.pyz
```

The `.pyz` wrapper hash varies between builds (zipapp embeds timestamps); the
bundled AEGIS payload content digest is stable at
`178a7f1c8b8d0e46af69bb237f414ddb9a4786fd047c45977371e987e266567a`.

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
