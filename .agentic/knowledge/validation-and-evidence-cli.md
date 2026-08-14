<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Validation and evidence CLI

## Purpose

The canonical CLI evaluates repository governance records, runs
repository-configured validation commands, and writes reproducible task
evidence. It is advisory by default and does not enforce a workflow stage,
commit, publish, or access the network.

## Public interface

`check` reports governance findings and optionally runs configured commands.
`test` executes a named configured command, optionally recording task evidence.
`report` appends a delivery snapshot. `anchor` fingerprints repository state
for an active task, while `evolution` classifies later changes against it.

## Key behaviors

- `REQ-FUNC-871f7c12` - Evaluate governance records and diff findings.
- `REQ-FUNC-c2a3f774` - Run configured validation commands with explicit
  results.
- `REQ-FUNC-d37ad85a` - Append delivery reporting based on recorded task
  state.
- `REQ-DATA-4304dec0` - Record task-scoped repository evidence anchors.
- `REQ-DATA-7faf94ff` - Compare repository changes with an evidence anchor.

## Files

- `05_Software/aegis/template/.agentic/aegis.py` - Canonical check, command,
  report, anchor, and evolution implementation.
- `05_Software/aegis/tests/test_check.py` - Governance-check catalog tests.
- `05_Software/aegis/tests/test_run_report.py` - Strict-mode, configured-run,
  test, and reporting tests.
- `05_Software/aegis/tests/test_repo_evolution.py` - Anchor and evolution
  evidence tests.
