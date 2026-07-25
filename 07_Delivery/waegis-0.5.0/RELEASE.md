<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS 0.5.0 Delivery Package

- **WAEGIS version**: 0.5.0
- **Bundled AEGIS payload**: 1.4.0
- **Compatible AEGIS payload range**: `>=0.4.0,<2.0`
- **Built**: 2026-07-25
- **Builder**: `05_Software/waegis/packaging/build_release.py` (stdlib-only)
- **Embedded runtime** (self-contained archives): CPython 3.13.13,
  astral-sh/python-build-standalone release 20260510, pinned by SHA-256 in
  `05_Software/waegis/packaging/runtime-lock.json`.

## What is new in this release

- **Requirement companion specs (`spec_ref`)**: requirement snapshots carry an
  optional `spec_ref` naming a companion spec file (data structures, interface
  and message formats, exact dialog and copy text, example payloads, worked
  acceptance examples) so an implementation cannot drift from what was analysed,
  while the `requirement` sentence stays a single testable behavior.
  `requirement create/update` gained `--spec-ref`/`--clear-spec-ref`; a
  non-empty reference must resolve to an existing file, and a later-deleted
  target is reported as `REQ-SPEC-MISSING`. Ships `spec_template.md`.
- **`resume` command**: a read-only bootstrap brief (current and next stage,
  intent, alignment, spec items, checks, recent evidence, and the run's cited
  requirements with their `spec_ref`) so a fresh agent session continues an
  existing run without prior chat context.
- **Per-stage skill modules**: the `agentic-development` and `agentic-adoption`
  skills are now thin routers that dispatch to per-stage modules under
  `reference/`, so a session loads only the current stage's guidance.

See `05_Software/aegis/template/CHANGELOG.md` (`[1.4.0]`) for the full list.

## Artifacts

| File | Size | Target | Needs on target |
| --- | --- | --- | --- |
| `waegis-0.5.0.pyz` | ~1.5 MB | Any OS | Python 3.11+ on `PATH` |
| `waegis-0.5.0-windows-x64.zip` | ~24 MB | Windows x64 | Nothing (embedded CPython) |
| `waegis-0.5.0-linux-x64.tar.gz` | ~66 MB | Linux x64 | Nothing (embedded CPython) |

The binaries themselves are not tracked in Git (see `.gitignore`); this record
and the checksums below are. Rebuild them from source with the command in the
`.gitignore`, or copy them from the builder's own `dist/` output.

## Checksums (SHA-256)

```text
9cdf7de0db4e9e048a3624d4a90491194f4415b4369db029300b99c80f9d3083  waegis-0.5.0-linux-x64.tar.gz
4caa835d1b7b1de0e9b7a6c7b53a4d3ade7888b6ed584300bbd67bd88dba2d08  waegis-0.5.0-windows-x64.zip
486633b34d2eb3a8501e165c7e697a06a8fa2dbe91fd445a5d43ebf2f09752af  waegis-0.5.0.pyz
```

The `.pyz` wrapper hash varies between builds (zipapp embeds timestamps); the
bundled AEGIS payload content digest is stable at
`21c94e401f179c1a77178594f49ffddd396299c286ba99e1862675f301182670`.

## Usage

Portable zipapp (Python 3.11+ present):

```bash
python waegis-0.5.0.pyz version
python waegis-0.5.0.pyz new /path/to/NewProject
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
