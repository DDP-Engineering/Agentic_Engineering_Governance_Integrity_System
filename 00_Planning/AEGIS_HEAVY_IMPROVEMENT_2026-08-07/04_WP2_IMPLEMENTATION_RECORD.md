<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WP2 implementation record

- Date: 2026-08-07
- Agent host: Codex
- Exact model: current task model; not exposed in the task record
- Reasoning/effort: current task setting; not exposed in the task record
- Starting commit: `2fbd2dc5dc93cdf46d2493a6011a41f92f920e84`
- Starting dirty paths: none
- Scope restated: add only the bounded, read-only fresh-session context
  contract and its documentation/tests. No quick-run evidence, nothing-ran,
  impact execution, WAEGIS behavior, or later-package behavior was changed.

## Red observation

- Test command:
  `uv run --group dev python -m pytest -q tests/test_stage_context_budget.py`
- Expected failure: WP2 needs a `run context` command before the budget and
  cross-session assertions can pass.
- Observed failure: `5 failed`; argparse rejected `context` because `aegis run`
  exposed only `start`, `status`, `resume`, `list`, `select`, and `abandon`.

## Changes

- Files: `stage_context.py`, `cli.py`, `stage_schema.py`, focused context and
  documentation tests, copied payload guidance/routers/adapters, package and
  deep documentation, root changelog, and this record.
- Contract decisions: `aegis run context --json` has
  `context_schema_version = 1`; it derives the selected stage's one skill and
  reference from the authoritative lifecycle schema, exposes the current
  primary form and only the immediately preceding retained primary form, and
  reports unavailable predecessor forms with `aegis stage show` recovery.
- Compatibility behavior: `run status` remains the detailed diagnostic output.
  Context reads no graph history beyond the loaded selected graph and performs
  no mutation. It excludes evidence, journal, requirement, report, and full
  configuration content, so new historical evidence cannot grow its response.
- Documentation behavior: AGENTS, shared routers, prompt cheat sheet, CLI
  reference, and Codex/Claude/Pi/OpenCode/Qwen adapters all route fresh
  sessions through the same bounded command and prohibit ordinary graph/journal
  recovery.

## Validation

- Focused commands and results:
  - `uv run --group dev python -m pytest -q tests/test_stage_context_budget.py`
    -> `10 passed`.
  - `uv run --group dev python -m pytest -q tests/test_stage_context_budget.py tests/test_documentation_workflow.py tests/test_cli_surface.py`
    -> `71 passed`.
- Full commands and results:
  - AEGIS: `uv run --group dev python -m pytest -q tests` -> `589 passed, 3 skipped`.
  - WAEGIS: `uv run --group dev python -m pytest -q tests` -> `699 passed, 8 skipped`.
- CLI/manual checks:
  - `python -B -m py_compile template/.agentic/cli/src/aegis/cli.py template/.agentic/cli/src/aegis/stage_schema.py template/.agentic/cli/src/aegis/stage_context.py tests/test_documentation_workflow.py tests/test_stage_context_budget.py` -> passed.
  - `uv run --group dev python -B -m aegis --help` -> passed.
  - `uv run --group dev python -B -m aegis run --help` -> passed and lists `context`.
  - `uv run --group dev python -B -m waegis --help` -> passed.

## Context effect

- Before bytes/tokens: no `run context` surface existed; a deterministic
  bootstrap measurement was therefore unavailable.
- After bytes/tokens: representative full-run JSON is 827 UTF-8 bytes; its
  complete payload bootstrap pack is 23,470 UTF-8 bytes. Automated tests
  enforce the 4 KiB JSON and 30 KiB complete-pack limits for full, quick, and
  adoption starts, include both current and retained predecessor forms, and
  prove identical context output with 1,000 additional evidence rows. Model
  tokenizer measurements remain a WP8 pilot responsibility.

## Review

- Reviewer host/model/effort: final source and diff pass by the implementing
  Codex session; an other-provider independent review was not available in
  this delegated worktree.
- Findings: full AEGIS validation initially found generated interpreter cache
  artifacts under the copied template after local debug and `py_compile`
  execution.
- Resolution: removed only the verified generated
  `template/.agentic/cli/src/aegis/__pycache__` directory and reran the full
  AEGIS suite successfully; the final hygiene test is green.

## Remaining risk

- Unverified behavior: the offline byte gate is complete, but Qwen tokenizer
  telemetry and genuinely fresh-model sessions remain WP8 acceptance work.
- Next allowed package: WP3 after the required independent package review.

## Correction after independent review

- Review findings: adoption-delivery incorrectly selected the standard delivery
  router; discarded applied forms were still named as readable current inputs;
  and the initial byte tests did not cover captured public CLI output after
  realistic lifecycle handoffs.
- Resolution: adoption-delivery now selects the adoption router/reference.
  `run context` returns `artifact = "none"`,
  `unavailable_current_artifact`, and only `aegis stage show` when an applied
  form was discarded, so guidance never tells a fresh session to prepare a
  revision that regresses applied state. The budget suite now drives full,
  quick, and adoption runs through real CLI handoffs (including prepared
  adoption-delivery), adds 1,000 evidence rows, and compares captured indented
  public JSON bytes before and after the history expansion.
- Correction validation:
  - `uv run --group dev python -m pytest -q tests/test_stage_context_budget.py tests/test_documentation_workflow.py tests/test_cli_surface.py`
    -> `70 passed`.
  - AEGIS full suite -> `588 passed, 3 skipped`.
  - WAEGIS full suite -> `699 passed, 8 skipped`.
  - AEGIS/WAEGIS CLI help and Python compilation passed. `py_compile` created
    one verified payload cache directory, which was removed before the final
    AEGIS hygiene run.
