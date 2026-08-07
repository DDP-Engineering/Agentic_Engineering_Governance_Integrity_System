<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WP7 adapter and documentation conformance implementation record

- Date: 2026-08-07
- Agent host: Codex
- Exact model: current task model; not exposed in the task record
- Reasoning/effort: current task setting; not exposed in the task record
- Starting commit: `568546c`
- Starting dirty paths: none
- Scope restated: make AEGIS host adapters, copied router/skill guidance,
  public CLI documentation, and deep documentation describe one payload-owned
  workflow contract. No core runtime behavior is changed.

## Red observation

- Inspection command: `rg -n "quick implementation|red-before-green|run
  context|graph.json|journal.jsonl"` across AEGIS adapters, shared skills, and
  public documentation.
- Expected failure: the shared router would still disagree with the existing
  quick-check contract, and host wrappers would contain local lifecycle prose.
- Observed failure: the shared development router treated new quick-run
  red-before-green as not applicable. Host wrappers also repeated local workflow
  setup prose instead of expressing a single bounded route into the payload.

## Changes

- Files: copied host router/skill entries, adapter documentation, payload and
  deep conformance documentation, public package documentation, changelog,
  documentation regressions, and this record.
- Contract decisions: `AGENTS.md` owns the bootstrap, `.agentic/skills/` owns
  procedures, and host adapters own only host invocation and hook translation.
  Every fresh session follows `AGENTS.md`, `run context --json`, only the named
  recovery command and reads, then the current human approval boundary.
- Compatibility behavior: direct CLI, Codex, Claude Code, Pi, OpenCode, and
  Qwen Code use the existing commands unchanged. Recovery documentation remains
  discoverable outside the forward context pack. New quick runs require the
  already-implemented registered-check red/green evidence; no CLI behavior was
  changed.

## Validation

- Focused commands and results: `uv run --group dev python -m pytest -q
  tests/test_documentation_workflow.py tests/test_opencode_adapter.py
  tests/test_pi_adapter.py tests/test_qwen_adapter.py tests/test_quick_runs.py
  tests/test_execution_outcomes.py tests/test_impact_execution.py` -> `102
  passed`.
- Full commands and results: `uv run --group dev python -m pytest -q tests` ->
  `622 passed, 3 skipped`.
- CLI/manual checks: changed-test Ruff passed; `python -B -m py_compile
  tests/test_documentation_workflow.py` passed; `uv run --group dev python -B
  -m aegis --help` passed. `git diff --check` passed, the copied starter
  changelog is empty, no copied-template Python caches were found, and the
  changed path set contains no WAEGIS paths.

## Context effect

- Before bytes/tokens: WP2's bounded context pack remains the baseline.
- After bytes/tokens: adapter entries route to the existing bounded context
  response; no response fields, forms, or context-budget limits change.

## Review

- Reviewer host/model/effort: implementation-session source, diff, scope, and
  genericity audit; an independent review is not available in this worktree.
- Findings: stale shared quick-run prose was corrected; no core mismatch was
  found.
- Resolution: structural tests now reject adapter-local lifecycle procedure,
  host prompt reference injection, and internal graph/journal recovery advice.

## Remaining risk

- Unverified behavior: fresh-session local-model telemetry remains WP8 work.
- Boundary: WAEGIS changes, documentation, tests, validation, and deployment
  behavior are omitted under the user scope override. Any WAEGIS continuity or
  simplification work remains outside WP7.
- Next allowed package: WP8 only after the required acceptance review.

## Correction after parity review

- Finding: the adapter map stated the bounded fresh-session route, while
  `AGENTS.md` and host documentation still required `config validate --json`
  and broad `config show --json` output before every repository action. That
  contradicted the `run context` pack by adding a non-required read and a large
  diagnostic payload.
- Resolution: `run context` is now documented as the configuration-validating
  fresh-session entry point. `config validate` confirms a configuration repair;
  `config show` is explicit diagnosis only. The map and regression suite now
  enumerate and protect the root host notes, every host README, the OpenCode
  primary agent, all adapter wrappers, and the mapped configuration/plugin
  entry files.
- Correction validation: focused documentation, adapter, and context coverage
  passed (`62 passed`); changed-test Ruff, Python compilation, and AEGIS CLI
  help passed. Full AEGIS validation passed (`622 passed, 3 skipped`). Final
  whitespace, genericity, scope, copied-template cache, empty starter
  changelog, and file-size checks passed; no WAEGIS path changed.
