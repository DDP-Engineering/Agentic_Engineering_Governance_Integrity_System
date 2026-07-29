<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

Release notes, delivery metadata, packaging notes, prompt references, and
publication records for the standalone AEGIS project belong here.

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
  notice. See `waegis-0.6.0/RELEASE.md` for artifacts, checksums, usage, the
  build command, and the required post-upgrade hook review.
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
  for artifacts, checksums, usage, and the build command. The binaries are
  reproducible from source and are not tracked in Git; the release record and
  checksums are.

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
