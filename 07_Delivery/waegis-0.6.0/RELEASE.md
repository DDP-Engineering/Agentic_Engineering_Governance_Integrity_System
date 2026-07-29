<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS 0.6.0 Delivery Package

- **WAEGIS version**: 0.6.0
- **Bundled AEGIS payload**: 1.4.1
- **Compatible AEGIS payload range**: `>=0.4.0,<2.0`
- **Built**: 2026-07-29
- **Builder**: `05_Software/waegis/packaging/build_release.py` (stdlib-only)
- **Embedded runtime** (self-contained archives): CPython 3.13.13,
  astral-sh/python-build-standalone release 20260510, pinned by SHA-256 in
  `05_Software/waegis/packaging/runtime-lock.json`.

## Upgrade urgency

**Every install made from WAEGIS 0.4.0 or 0.5.0 has no Codex enforcement at
all.** Those bundles ship an AEGIS payload whose `.codex/hooks.json` Codex
rejects outright, so it registers zero hooks: the read guard, write-zone guard,
secret scan, shell-write guard, delivery preflight, and evidence recorder are
all silently inactive under that agent. Tool calls are not blocked — they are
never inspected. Other adapters are unaffected.

Upgrade an existing install with `waegis upgrade --repo <path>`, then **re-review
the hooks in Codex** (see "After upgrading" below). Verify with
`waegis doctor --repo <path>`, whose new `runnability.adapter-configs` check
reports a rejected adapter config as a failure.

## What is new in this release

- **Fixed: Codex guards were entirely absent in every installed repository.**
  `.codex/hooks.json` carried the `_legal`/`_comment*` annotation keys used
  across the other adapters' JSON, but Codex parses that file with a strict
  deserializer accepting exactly two top-level keys, `description` and `hooks`.
  An unknown key is not ignored — it rejects the whole file. The hook wiring
  itself was always schema-valid and is unchanged.
- **`waegis doctor` gained `runnability.adapter-configs`**, which parses each
  strictly-deserialized adapter config and verifies its top-level keys against
  the set its host accepts. Severity is `fail`: a config the host discards
  removes enforcement rather than degrading it. The previous adapter check
  confirmed only that the adapter *directory* existed, which reported healthy
  over a repository with no guards.
- **`waegis upgrade` reports hook configs needing re-trust**, in both the plan
  preview and the post-apply report, with an additive
  `hook_configs_needing_retrust` key in `--json`.
- **Payload documentation for the Codex trust gates**: a new `.codex/README.md`,
  a `.agentic/hooks/README.md` section covering project trust and per-hook
  review, and a correction to `.pi/README.md`, which had claimed Codex needs no
  trust step.

See `05_Software/aegis/template/CHANGELOG.md` (`[1.4.1]`) for the full list.

## After upgrading: re-review the Codex hooks

Codex binds per-hook trust to the **content hash** of `.codex/hooks.json`. Any
change to that file — including this upgrade — returns every hook in it to
"review required" and stops it running until re-reviewed. The upgrade succeeds,
the files are correct, and the session looks healthy while tool calls go
uninspected; `waegis upgrade` prints an action-required block naming the file,
and nothing else reports it.

Codex also loads project-local hooks only for a **trusted** project. Both gates
fail open and neither produces an error.

1. Open Codex at the repository root and trust the project if prompted.
2. Open `/hooks` and trust the AEGIS hooks.
3. Confirm enforcement is live: ask the agent to read a path covered by an
   enforced `guardrails.protected_paths` read policy. A correctly loaded
   configuration denies it.

## Artifacts

**This is the first release with version-free artifact names.** Filenames are
now stable across releases so documentation, install scripts, and automation can
reference a fixed path; the version lives in the artifact and in this record
instead. Builds land in `07_Delivery/dist/` and overwrite the previous set.

| File | Size | Target | Needs on target |
| --- | --- | --- | --- |
| `waegis.pyz` | ~1.5 MB | Any OS | Python 3.11+ on `PATH` |
| `waegis-windows-x64.zip` | ~24 MB | Windows x64 | Nothing (embedded CPython) |
| `waegis-linux-x64.tar.gz` | ~66 MB | Linux x64 | Nothing (embedded CPython) |

The binaries are not tracked in Git (see `../.gitignore` for why a fixed name
does not change that); this record and the checksums below are. Rebuild them
from a source checkout at this version:

```bash
uv run python 05_Software/waegis/packaging/build_release.py
```

## Identifying a build

Because the filename no longer carries a version, ask the artifact:

```bash
python waegis.pyz version
```

```text
WAEGIS 0.6.0
Compatible AEGIS payloads: >=0.4.0,<2.0
Bundled payload: 1.4.1
Payload digest: 52317e5c6979ba44b0ae9eaf0ce1f8089019ce2c1e472fce8fd4840d0f8adc55
Packaging: zipapp
```

`release-manifest.json` beside the artifacts records the same version with the
hashes, so a directory of binaries is never ambiguous about what it holds.

## Checksums (SHA-256)

```text
c31f0b4ab2e7648b255cecf2ecfa30d481f052dc17f31bce26ad305843024dc3  waegis-linux-x64.tar.gz
0ccf94ea19acc93ae55de9d4899b97e61f17fc19d1ff90fc168af5438b5209b1  waegis-windows-x64.zip
19686ef8d0d05340a9199b01b545b5e1a64e39a8cc4d8e21730b6c439479b551  waegis.pyz
```

The `.pyz` wrapper hash varies between builds (zipapp embeds timestamps), so a
rebuild will not reproduce these three hashes byte for byte. The bundled AEGIS
payload content digest is the stable identity and is
`52317e5c6979ba44b0ae9eaf0ce1f8089019ce2c1e472fce8fd4840d0f8adc55`.

## Usage

Portable zipapp (Python 3.11+ present):

```bash
python waegis.pyz version
python waegis.pyz new /path/to/NewProject
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

Run from the directory holding the artifacts (`07_Delivery/dist/` for a local
build) — this record directory carries the checksums but not the binaries:

```bash
sha256sum -c SHA256SUMS
```

Or with the builder itself, which also checks each archive's internal manifest:

```bash
uv run python 05_Software/waegis/packaging/build_release.py --verify-only
```
