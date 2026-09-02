<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 05 - Implementation phases

The original implementation plan is complete. This document records the
implemented product shape at AEGIS 0.9.1 and the maintenance boundary for
future changes.

## Completed implementation

| Area | Implemented outcome |
|---|---|
| Workflow payload | A managed `.agentic/` payload with the full contract, six ordinary stage files, adoption instructions, and reusable artifact templates. |
| Durable artifacts | TOML requirements, Markdown specs/knowledge/journals, append-only rulings, replaceable handoffs/stage reports, and anchor/evolution JSON evidence. |
| Companion CLI | Offline-first standard-library `aegis.py` with installation, scaffolding, traceability, configured test execution, reporting, and machine-readable output. |
| Validation | A 21-check advisory catalog, optional strict CI enforcement, impacted-test selection, configured command timeouts, anchors, evolution, and delivery reporting. |
| Coordination | One-level child tasks, bounded `brief`/ `summary` views, explicit review policy, and durable handoff state for cross-session/model work. |
| Documentation and delivery | User guides in `06_SoftwareDocu/`, planning record updates, versioned release archives, checksums, and publication records in `07_Delivery/`. |

## Current product boundaries

The runnable implementation remains under:

```text
05_Software/aegis/
  template/.agentic/       installable managed payload
  tests/                   product verification suite
  README.md                package overview

02_Tools/
  build_aegis_release.py   release archive and publication-record builder
```

The root `.agentic/` directory is an installed copy used to govern this
repository. It is not the product source of truth. Update the template first,
then copy the exact managed payload into root or downstream repositories and
run `init`.

## 0.9.1 implementation state

Version 0.9.1 adds the `trace` requirement-register export in Markdown and CSV,
with corrected literal text rendering, omission reporting, and category labels.
The repository's impacted-test command now uses its configured Python runtime.

## 0.9.0 coordination baseline

Version 0.9.0 introduced the coordinated-workflow capabilities:

- deterministic `brief` resume output distinct from `summary`;
- optional explicit review with `enabled` and `max_fix_cycles`;
- independent specification-compliance and implementation-quality verdicts;
- append-only rulings and stage-bound handoffs;
- visible one-level child tasks;
- expanded check coverage for configuration, manual verification, review
  evidence, stage zones, and command execution;
- synchronized Markdown and presentation documentation.

The root repository deliberately enables explicit review with two permitted
fix cycles. That is repository configuration, not a new workflow stage.

## Maintenance rules

1. Treat `template/.agentic/` as the source of managed workflow behavior.
2. Update tests when CLI behavior changes; run focused checks first and the
   product suite before release.
3. Update the relevant user and planning documentation in the same change when
   commands, workflow contracts, artifact formats, or configuration change.
4. Keep the template generic. Do not add this repository's task history,
   release entries, or project-specific facts to the downstream starter files.
5. Treat versioning, archive construction, and publication records as
   repository operations. Do not open a workflow journal for the release
   itself.
6. Build releases only with `02_Tools/build_aegis_release.py --version
   <x.y.z>`. It verifies the 15-file payload, runs the product suite, verifies
   both archive inventories, and writes hashes and metadata under
   `07_Delivery/aegis-<version>/`.

Future work begins from the current implementation and its tests, not from the
obsolete pre-implementation phase estimates that this document replaces.
