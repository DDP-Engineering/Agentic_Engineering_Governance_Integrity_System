<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Project profile

## Purpose and users

AEGIS supplies an offline-first advisory software-development workflow for
human developers and coding agents working in Git repositories.

## Product responsibilities

The core provides workflow instructions, portable artifact templates, and a
Python companion CLI for scaffolding, orientation, traceability and verification
reporting. Host integrations connect OpenCode, Codex, Pi, Qwen Code and Claude
Code to the installed repository workflow.

## Supported operation

The Python core targets Python 3.11 or later on Windows and Linux. The host
bridge uses Node.js 22 or later. Core workflow artifacts are ordinary Markdown,
TOML and JSON files carried on project branches.

## Established constraints

Repository ownership, folder boundaries, licensing, validation and versioning
are defined in `AGENTS.md` and `LICENSE.txt`. Implementation style is defined in
`01_Documentation/Code_Style.md`. The canonical reusable payload lives under
`05_Software/aegis/template/.agentic/`; project-owned context and records live
in the root `.agentic/`. Authorization for external actions remains with users.

## Implementation orientation

- `.agentic/knowledge/reusable-workflow-payload.md` routes workflow, stage and
  template work to canonical source and tests.
- `05_Software/aegis/template/.agentic/aegis.py` implements the companion CLI.
- `05_Software/aegis/integrations/` contains host adapters and shared runtime.
- `05_Software/aegis/tests/` contains the Python product suite, including
  integration wrappers; `05_Software/aegis/integrations/tests/` contains host
  and bridge behavior tests.
- `02_Tools/` owns repository setup and delivery-package tooling.

## Authoritative references

- `README.md` — repository scope and folder ownership.
- `05_Software/aegis/README.md` — product setup and behavior.
- `06_SoftwareDocu/00_Index.md` — user and implementation guides.
- `.agentic/requirements/` — behavior contracts selected by affected paths.
