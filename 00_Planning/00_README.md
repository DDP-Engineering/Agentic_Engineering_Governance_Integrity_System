<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS implementation overview

Status: implemented and released as **AEGIS 0.9.0**. The runnable product is
at `05_Software/aegis/`; the installable payload is
`05_Software/aegis/template/.agentic/`; the current user guides are under
`06_SoftwareDocu/`.

This directory records the implemented design. If it differs from the
installed payload, `.agentic/aegis.py --help`, `.agentic/AGENTS.md`, and
the payload step files are authoritative. Update this record when the
implementation or workflow contract changes.

## What AEGIS is

AEGIS is an offline-first, advisory software-development workflow. A small
standard-library Python CLI scaffolds durable files, runs configured commands,
and reports governance findings. The workflow itself is Markdown that an agent
or developer reads and follows.

It deliberately does not create a hidden run store, a hosted service, hooks,
or a separate permission system. Git and ordinary repository files retain the
history and recovery path.

## Current model

- Six fixed ordinary stages: `frame -> specify -> design -> build -> validate
  -> deliver`.
- A small fix or change may use the recorded quick path:
  `frame -> build -> validate -> deliver`.
- Existing-repository adoption is a separate `survey -> components -> close
  -> done` flow, not a seventh ordinary stage.
- Requirements, specifications, journals, knowledge pages, anchors, and
  evolution reports are plain files below `.agentic/`.
- `check` is advisory by default. `check --strict` is the optional CI
  boundary that fails on errors and configured promoted warnings.
- Explicit review is optional policy, not a stage. When enabled it records
  specification-compliance and implementation-quality verdicts with a bounded
  fix-and-re-review loop; ordinary validation remains required either way.
- `brief` is the bounded resume view; `summary` is the narrower projection
  of the latest recorded stage report.

AEGIS applies to software development. Repository maintenance, versioning,
release construction, package publication, and deployment follow the
repository's own procedures rather than opening an AEGIS journal.

## Planning record

| Document | Current purpose |
|---|---|
| [01_Workflow_And_Stages.md](01_Workflow_And_Stages.md) | Lifecycle, interaction boundaries, review policy, and resume behavior. |
| [02_Artifacts_And_Formats.md](02_Artifacts_And_Formats.md) | Ownership split, directory layout, configuration, and durable formats. |
| [03_Companion_CLI.md](03_Companion_CLI.md) | Implemented CLI commands, read/write boundaries, and check behavior. |
| [04_Collaboration_And_Small_Models.md](04_Collaboration_And_Small_Models.md) | Branch-based collaboration and bounded re-entry for constrained models. |
| [05_Implementation_Phases.md](05_Implementation_Phases.md) | Completed implementation shape and maintenance expectations. |

The user-facing reading order is `06_SoftwareDocu/00_Index.md`.
