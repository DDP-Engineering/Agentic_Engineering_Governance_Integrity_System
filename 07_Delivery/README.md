<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

Release notes, delivery metadata, packaging notes, prompt references, and
publication records for the standalone AEGIS project belong here.

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
