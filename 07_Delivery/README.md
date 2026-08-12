<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

Release notes, delivery metadata, packaging notes, prompt references, and
publication records for the standalone AEGIS project belong here.

## AEGIS version 1 delivery matrix

AEGIS version 1 is delivered as eight platform-specific ZIP archives in
`07_Delivery/dist/`:

| Product | Runtime edition | Windows x86-64 | Ubuntu 22.04 x86-64 |
|---|---|---|---|
| AEGIS | External Python 3.12 and Git | `aegis-1.0.0-windows-x86_64-external-runtime.zip` | `aegis-1.0.0-ubuntu-22.04-x86_64-external-runtime.zip` |
| AEGIS | Private Python 3.12 and Git | `aegis-1.0.0-windows-x86_64-with-dependencies.zip` | `aegis-1.0.0-ubuntu-22.04-x86_64-with-dependencies.zip` |
| WAEGIS containing AEGIS | External Python 3.12 and Git | `waegis-1.0.0-windows-x86_64-external-runtime.zip` | `waegis-1.0.0-ubuntu-22.04-x86_64-external-runtime.zip` |
| WAEGIS containing AEGIS | Private Python 3.12 and Git | `waegis-1.0.0-windows-x86_64-with-dependencies.zip` | `waegis-1.0.0-ubuntu-22.04-x86_64-with-dependencies.zip` |

External-runtime launchers only check and use the existing prerequisites; they
do not install or configure Python or Git. Bundled archives use private runtime
copies below the extracted archive and are built only from locally supplied,
locked inputs. No release build downloads dependencies.

## Layout

```text
07_Delivery/
  dist/                     build output - fixed names, overwritten, never tracked
    waegis.pyz
    waegis-windows-x64.zip
    waegis-linux-x64.tar.gz
    waegis-complete-windows-x64.zip
    waegis-complete-linux-x64.tar.gz
    SHA256SUMS
    release-manifest.json
  waegis-<version>/         publication record - tracked, one per release
    RELEASE.md
    SHA256SUMS
    release-manifest.json

  aegis-light-<version>/    publication record for the AEGIS Light payload
    RELEASE.md
    SHA256SUMS
    release-manifest.json
```

## AEGIS Light

AEGIS Light delivers as two small archives with byte-identical content
(`aegis-light-<version>.zip` and `.tar.gz`) holding the `.agentic/`
payload, `INSTALL.md`, the product `README.md`, `LICENSE.txt` and the
user guides. It embeds no runtime and is not platform-specific: the two
formats are ergonomic, not different builds.

Build with:

```
python 02_Tools/build_aegis_light_release.py --version <version>
```

The builder verifies the payload inventory, runs the product test suite
and refuses to package a red tree, then writes deterministic archives
(normalized member timestamps, so the same sources reproduce the same
checksums) plus `SHA256SUMS` and `release-manifest.json` into `dist/`,
and copies the checksums and manifest into the tracked publication
record. Write `RELEASE.md` there by hand.

Artifact filenames carry **no version**, so documentation, install scripts, and
automation can reference a stable path, and a rebuild overwrites the previous
set instead of leaving another ~94 MB behind. The version is not lost: each
artifact reports it (`python waegis.pyz version`) and every publication record
pins it beside the hashes.

Binaries are never tracked in Git. A fixed filename does not change that
calculation — Git stores blobs rather than names, so committing them would grow
history by the full artifact size on every release, permanently and
irreversibly. `.gitignore` in this directory carries the measurements behind
that decision. What is tracked is the publication record. The binaries and
release metadata are byte-reproducible only with identical source, runtime
locks/assets, target/edition, Complete RepoWise/wheel inputs, canonical epoch,
Python patch version, `uv` version, and zlib/compression implementation.

```bash
SOURCE_DATE_EPOCH=1785425602 \
  uv run python 05_Software/waegis/packaging/build_release.py --offline
```

The canonical epoch is valid `SOURCE_DATE_EPOCH`, otherwise the source commit
timestamp, otherwise the fixed 1980 ZIP epoch for a source export. Explicit
invalid values fail. ZIP/tar/gzip metadata and generated Complete SBOM time use
the normalized two-second epoch. Every archive is written to a unique exclusive
sibling, verified for exact internal membership and digests, then atomically
published. `release-manifest.json` records `build_epoch`; it and
`SHA256SUMS` are deterministic release assets.

Gitea publication timestamps and historical records are outside this contract.
Different Python/uv/zlib implementations are not claimed to hash identically.
See `../06_SoftwareDocu/WAEGIS_RELEASE_REPRODUCIBILITY.md` for supported
cross-host expectations and the two-build mtime/hash smoke procedure.

## Release Hygiene Checklist

Before producing or recording a release:

1. Run the AEGIS structural hygiene tests and both full package suites.
2. Confirm the development AEGIS project, embedded CLI, embedded package, and
   every versioned adapter manifest agree; confirm WAEGIS package metadata,
   canonical `WIZARD_VERSION`, and the current delivery manifest agree.
3. Confirm `template/AGENTS.md` names the current AEGIS line and
   `template/CHANGELOG.md` is byte-empty.
4. Run
   `rg --files -uu 05_Software/aegis/template | rg "__pycache__|\.pyc$|\.pyo$"`
   and require no output.
5. Exercise payload copying and release staging with physically present cache
   fixtures; Git ignore rules alone are insufficient because both builders walk
   the filesystem directly.
6. Build into `dist/`, run internal archive verification, and retain only the
   publication manifest/checksums and reviewed release notes in Git.
7. For a self-governed release, retain the complete approved AEGIS run described
   in `../06_SoftwareDocu/SELF_GOVERNED_RELEASE.md`. Structural hygiene tests are
   not a substitute for requirements, design, check, validation, and delivery
   evidence.

## Releases

AEGIS 2.1 / WAEGIS 1.1 defines two editions from one codebase. Core preserves
the three existing artifacts and defaults RepoWise to disabled. Complete adds
native RepoWise 0.37.0 artifacts built separately on Windows x64 and Linux x64.
See `REPOWISE_COMPLETE_DELIVERY.md` for native build, offline, manifest, SBOM,
notice, and AGPL review requirements.

AEGIS 2.1.0 / WAEGIS 1.1.0 is the current release. All three Core and both
Complete artifacts were built in `dist/`; the Complete archives passed native
Windows x64 and Linux x64 builds and full internal-manifest verification.

> **Every release before 0.6.0 ships a payload with no Codex enforcement.**
> Their `.codex/hooks.json` carries annotation keys that Codex's strict parser
> rejects, and a rejected file registers *zero* hooks — the read, write-zone,
> secret, shell-write, delivery, and evidence guards are all silently absent
> under that agent. Verified in the built artifacts for 0.2.0, 0.3.0, 0.4.0,
> and 0.5.0. Other adapters are unaffected. Upgrade any install to 0.6.0 with
> `waegis upgrade --repo <path>`, then re-review the hooks in Codex.

- `aegis-light-0.2.0/` - AEGIS Light 0.2.0, the advisory companion product
  (current). Separate from AEGIS/WAEGIS: no shared artifacts, no embedded
  runtime, standard library only. Completes the heuristic catalog at seventeen
  checks — advisory per-stage write zones (`stage-zone`) and by-hand
  verification (`manual-verification`). First AEGIS Light publication record,
  and the first AEGIS Light archives whose digests reproduce from source. See
  `aegis-light-0.2.0/RELEASE.md`.
- `waegis-1.1.0/` - WAEGIS 1.1.0 with bundled AEGIS payload 2.1.0 and optional
  RepoWise 0.37.0 Complete sidecars (current). Contains the five-artifact
  publication manifest and checksums. See `waegis-1.1.0/RELEASE.md`.
- `waegis-0.6.0/` - WAEGIS 0.6.0 with bundled AEGIS payload 1.4.1
  (latest prior tracked publication record).
  Fixes the rejected Codex hook configuration described above, and adds the
  `waegis doctor` adapter-config check plus the post-upgrade hook re-trust
  notice. **First release with version-free artifact names**; releases up to
  0.5.0 shipped as `waegis-<version>.pyz` and friends. See
  `waegis-0.6.0/RELEASE.md` for artifacts, checksums, usage, the build command,
  and the required post-upgrade hook review.
- `waegis-0.5.0/` - WAEGIS 0.5.0 with bundled AEGIS payload 1.4.0
  (**superseded - no Codex enforcement**). Adds requirement companion specs
  (`spec_ref`), the read-only `resume` bootstrap brief, and per-stage skill
  modules for the development and adoption routers. See
  `waegis-0.5.0/RELEASE.md` for artifacts, checksums, usage, and the build
  command.
- `waegis-0.4.0/` - WAEGIS 0.4.0 with bundled AEGIS payload 1.3.0
  (**superseded - no Codex enforcement**). Adds the shell write guard and the
  `waegis doctor` hook-launcher check. See `waegis-0.4.0/RELEASE.md` for
  artifacts, checksums, usage, and the build command.
- `waegis-0.3.0/` - WAEGIS 0.3.0 with bundled AEGIS payload 1.2.0
  (**superseded - no Codex enforcement**). Portable zipapp plus self-contained
  Windows and Linux archives (embedded CPython). See `waegis-0.3.0/RELEASE.md`
  for artifacts, checksums, usage, and the build command.

## Legacy AEGIS 2.1 / WAEGIS 1.1 delivery model

WAEGIS deploys the template as copied files plus a bundled Python CLI:

- The separate WAEGIS package configures, copies, records, and verifies the
  installable template in a new or existing target project.
- The copied project receives `.agentic/cli/` with the workflow CLI source.
- The copied project receives `.agentic/tools/` with Windows PowerShell and
  Bash wrappers for immediate local execution.
- The copied project can optionally install the CLI into `.agentic/.venv/`.

WAEGIS is the deployment/lifecycle tool and is never copied into the target
AEGIS payload.

Complete carries RepoWise as a separate release sidecar. WAEGIS installs it
only when selected under
`.agentic/tools/repowise/0.37.0/<platform>/`; AEGIS reads only validated
artifacts and receipts. Target installation/indexing never downloads packages.

The current CLI has no third-party runtime dependencies. Python 3.11 or newer
is required. The install scripts prefer `uv` when available and otherwise use
Python's built-in `venv` plus `pip`.

## Delivery References

- The workflow CLI command API reference is maintained as a single canonical
  document at
  `05_Software/aegis/template/.agentic/documents/CLI_API_REFERENCE.md`, which
  is delivered into target repositories. No separate delivery copy is kept here.
- `PROMPT_CHEATSHEET.md` - delivery reference copy of the operator prompts for
  creating a target project, running gates, validating component documentation,
  and preparing delivery. The installable copy is delivered through
  `05_Software/aegis/template/.agentic/documents/PROMPT_CHEATSHEET.md`.
