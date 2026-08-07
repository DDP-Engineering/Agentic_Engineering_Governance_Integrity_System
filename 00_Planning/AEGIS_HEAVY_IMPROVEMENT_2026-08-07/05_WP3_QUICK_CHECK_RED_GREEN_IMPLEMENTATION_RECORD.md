<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Quick check red/green implementation record

- Date: 2026-08-07
- Agent host: Codex
- Exact model: current task model; not exposed in the task record
- Reasoning/effort: current task setting; not exposed in the task record
- Starting commit: `f7952842a065bdfcbd80637dd950319f2752245d`
- Starting dirty paths: none
- Scope restated: implement only the quick-run red-before-green contract. No
  nothing-ran, impact execution, WAEGIS, adapter redesign, pilot, or later
  package behavior was changed.

## Red observation

- Test command:
  `uv run --group dev python -m pytest -q tests/test_quick_runs.py -k "new_quick_run_mints or new_quick_implementation_rejects or schema_three_quick_graph_without"`
- Expected failure: the current quick path lacks the `check create` command,
  accepts manual-only evidence, and has no persisted quick red/green policy.
- Observed failure: `3 failed`; argparse rejected `check create`, manual
  evidence advanced implementation, and `Graph` had no `red_green_policy`.

## Changes

- Files: schema-3 graph model/loading, quick-only check registration and
  evidence readiness, check CLI/execution, invariant/report surfaces, focused
  public-path tests, generic payload guidance, package/deep documentation,
  root changelog, and this record.
- Contract decisions: new full and quick graphs persist
  `red_green_policy = "required"`. A policy-less schema-3 quick graph loads as
  `legacy-not-applicable`; a policy-less full graph loads as `required`.
- Compatibility behavior: legacy quick INV-3 remains explicitly
  not-applicable. New quick implementation mints check IDs in strict run-local
  TOML, requires registration before stage apply, retains a red witness through
  green, requires all registered checks to be currently green, and accepts
  only active implementation-stage green `test-run` evidence in the linked
  implementation form.
- Persistence behavior: registration publishes the graph and
  `quick.check.registered` journal event through the existing rollback-capable
  journaled transaction; a failed journal write restores the previous graph.

## Validation

- Focused commands and results:
  - `uv run --group dev python -m pytest -q tests/test_quick_runs.py tests/test_quick_run_reporting_boundaries.py tests/test_check_execution.py tests/test_invariants.py tests/test_documentation_workflow.py tests/test_cli_surface.py` -> `146 passed`.
  - `uv run --group dev ruff check template/.agentic/cli/src/aegis/models.py template/.agentic/cli/src/aegis/check_execution.py template/.agentic/cli/src/aegis/cli.py template/.agentic/cli/src/aegis/invariants.py template/.agentic/cli/src/aegis/report.py template/.agentic/cli/src/aegis/stage_forms.py tests/test_quick_runs.py tests/test_quick_run_reporting_boundaries.py tests/test_documentation_workflow.py` -> passed.
  - `python -B -m py_compile template/.agentic/cli/src/aegis/models.py template/.agentic/cli/src/aegis/check_execution.py template/.agentic/cli/src/aegis/cli.py template/.agentic/cli/src/aegis/invariants.py template/.agentic/cli/src/aegis/report.py template/.agentic/cli/src/aegis/stage_forms.py tests/test_quick_runs.py tests/test_quick_run_reporting_boundaries.py tests/test_documentation_workflow.py` -> passed.
- Full commands and results:
  - AEGIS: `uv run --group dev python -m pytest -q tests` -> `595 passed, 3 skipped`.
  - WAEGIS: `uv run --group dev python -m pytest -q tests` -> `699 passed, 8 skipped`.
- CLI/manual checks:
  - `uv run --group dev python -B -m aegis --help` -> passed.
  - `uv run --group dev python -B -m waegis --help` -> passed.
  - The first AEGIS full run detected only generated payload `__pycache__`
    files from `py_compile`; the six verified generated files were removed and
    the clean full suite passed afterward.

## Context effect

- Before bytes/tokens: no run-local quick check definition or policy is named
  by the bounded bootstrap contract.
- After bytes/tokens: the current implementation form and its run-local check
  definitions remain inside the existing stage directory; no graph/journal
  history is injected into `run context`. Token telemetry remains WP8 work.

## Review

- Reviewer host/model/effort: final source, diff, and focused regression pass
  by the implementing Codex session; an independent other-provider review was
  not available in this delegated worktree.
- Findings: compilation created six interpreter caches under the copied payload.
- Resolution: removed only those verified generated cache files, then reran
  AEGIS release hygiene through the clean full suite.

## Remaining risk

- Unverified behavior: an independent other-provider review remains required
  by the plan's session-isolation policy.
- Next allowed package: WP4 after the required independent package review.
