<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

Release notes, delivery metadata, packaging notes, prompt references, and
publication records for the standalone AEGIS project belong here.

## Layout

```text
07_Delivery/
  dist/                     build output - fixed names, overwritten, never tracked
    waegis.pyz
    waegis-windows-x64.zip
    waegis-linux-x64.tar.gz
    SHA256SUMS
    release-manifest.json
  waegis-<version>/         publication record - tracked, one per release
    RELEASE.md
    SHA256SUMS
    release-manifest.json
```

Artifact filenames carry **no version**, so documentation, install scripts, and
automation can reference a stable path, and a rebuild overwrites the previous
set instead of leaving another ~94 MB behind. The version is not lost: each
artifact reports it (`python waegis.pyz version`) and every publication record
pins it beside the hashes.

Binaries are never tracked in Git. A fixed filename does not change that
calculation — Git stores blobs rather than names, so committing them would grow
history by the full artifact size on every release, permanently and
irreversibly. `.gitignore` in this directory carries the measurements behind
that decision. What is tracked is the publication record, and the binaries are
reproducible from a source checkout at the recorded version:

```bash
uv run python 05_Software/waegis/packaging/build_release.py
```

## Releases

> **Every release before 0.6.0 ships a payload with no Codex enforcement.**
> Their `.codex/hooks.json` carries annotation keys that Codex's strict parser
> rejects, and a rejected file registers *zero* hooks — the read, write-zone,
> secret, shell-write, delivery, and evidence guards are all silently absent
> under that agent. Verified in the built artifacts for 0.2.0, 0.3.0, 0.4.0,
> and 0.5.0. Other adapters are unaffected. Upgrade any install to 0.6.0 with
> `waegis upgrade --repo <path>`, then re-review the hooks in Codex.

- `waegis-0.6.0/` - WAEGIS 0.6.0 with bundled AEGIS payload 1.4.1 (current).
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

## Current Delivery Model

WAEGIS deploys the template as copied files plus a bundled Python CLI:

- The separate WAEGIS package configures, copies, records, and verifies the
  installable template in a new or existing target project.
- The copied project receives `.agentic/cli/` with the workflow CLI source.
- The copied project receives `.agentic/tools/` with Windows PowerShell and
  Bash wrappers for immediate local execution.
- The copied project can optionally install the CLI into `.agentic/.venv/`.

WAEGIS is the deployment/lifecycle tool and is never copied into the target
AEGIS payload.

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
