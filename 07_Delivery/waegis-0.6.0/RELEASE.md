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

| File | Size | Target | Needs on target |
| --- | --- | --- | --- |
| `waegis-0.6.0.pyz` | ~1.5 MB | Any OS | Python 3.11+ on `PATH` |
| `waegis-0.6.0-windows-x64.zip` | ~24 MB | Windows x64 | Nothing (embedded CPython) |
| `waegis-0.6.0-linux-x64.tar.gz` | ~66 MB | Linux x64 | Nothing (embedded CPython) |

The binaries themselves are not tracked in Git (see `.gitignore`); this record
and the checksums below are. Rebuild them from source with the command in the
`.gitignore`, or copy them from the builder's own `dist/` output.

## Checksums (SHA-256)

```text
91239f29f29bde28e4b81cae6eaec04984469a24457e729f86b20a4a5abbe90c  waegis-0.6.0-linux-x64.tar.gz
ce44c6ef7cc4ad6aadf3e889ba46f6e9a1b04ded100ac80c6077e2b14bc49e93  waegis-0.6.0-windows-x64.zip
8b380283fc861d7f1361f6df655a612fe06bca5cc4ce5b8fd64999444ddee90a  waegis-0.6.0.pyz
```

The `.pyz` wrapper hash varies between builds (zipapp embeds timestamps); the
bundled AEGIS payload content digest is stable at
`52317e5c6979ba44b0ae9eaf0ce1f8089019ce2c1e472fce8fd4840d0f8adc55`.

## Usage

Portable zipapp (Python 3.11+ present):

```bash
python waegis-0.6.0.pyz version
python waegis-0.6.0.pyz new /path/to/NewProject
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
