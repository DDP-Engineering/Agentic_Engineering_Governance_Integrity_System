<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Product verification suite

## Purpose

The AEGIS product suite protects the canonical copied payload and its CLI
contracts. It uses temporary repositories, deterministic Git fixtures where
available, configured child commands, and structural source inspections.

The suite verifies the product; it does not govern a live repository or modify
the canonical payload under test.

## Public interface

Run the complete suite with `python -m pytest -q 05_Software/aegis/tests`.
The repository's `.agentic/aegis.toml` exposes the same command as
`python .agentic/aegis.py test`.

The structural suite compares the installed CLI and reference against the
canonical template and derives required reference sections from the parser's
actual commands. Documentation under `06_SoftwareDocu/` remains inspected
directly, without prose or layout assertion tests.

## Key behaviors

- `REQ-TEST-2b78f69d` - Exercise core CLI behavior in isolated payload copies.
- `REQ-TEST-2651b9cf` - Exercise governance and evidence behavior with
  deterministic fixtures.
- `REQ-TEST-e38913a7` - Guard reusable payload structural constraints.

## Architecture

Temporary repositories isolate command behavior and record validation.
Structural checks read the canonical template directly; the installed-copy
guard also reads this repository's `.agentic/aegis.py` and `.agentic/CLI.md`.
The parser supplies the command inventory for the payload-reference check.

## Files

- `05_Software/aegis/tests/test_cli_core.py` - Lifecycle and scaffold tests.
- `05_Software/aegis/tests/test_check.py` - Governance-check catalog tests and
  shared temporary Git fixtures.
- `05_Software/aegis/tests/test_run_report.py` - Command, strict-mode, report,
  JSON, and configuration tests.
- `05_Software/aegis/tests/test_repo_evolution.py` - Anchor and evolution
  record tests.
- `05_Software/aegis/tests/test_structure.py` - Payload invariant tests.
