<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WP5 impact execution implementation record

- Date: 2026-08-07
- Agent host: Codex
- Exact model: current task model; not exposed in the task record
- Reasoning/effort: current task setting; not exposed in the task record
- Starting commit: `ea93ebc`
- Starting dirty paths: none
- Scope restated: implement only safe `verify impact --run` execution with an
  argv-focused prefix, deterministic selection, fail-safe full test fallback,
  ordinary test-gate evidence, and WP4 `nothing-ran`. No WP6 or later behavior
  was started.

## Red observation

- Test command:
  `uv run --group dev python -m pytest -q tests/test_impact_execution.py`
- Expected failure: schema-3 configuration rejected the new
  `gates.test.impacted_command` key and the existing global `--run` parser
  treated the requested impact execution flag as a missing run ID.
- Observed failure: `10 failed, 1 passed`; every configured-prefix case failed
  configuration validation and every explicit execution case failed argparse.

## Changes

- Files: AEGIS CLI/configuration/gate runner, focused public CLI tests, generic
  payload guidance, package/deep documentation, WAEGIS workflow validation and
  preservation coverage, root changelog, and this record.
- Contract decisions:
  - `[gates.test].impacted_command` is optional argv data. Existing schema-3
    configuration that omits it remains valid; the copied template documents a
    generic example without enabling it.
  - `verify impact [paths-file] --run` preserves reporting-only impact output
    when `--run` is absent. When present, it executes a sorted unique selector
    union through `shell = false`, or records `full-fallback` and runs every
    configured full test command with the exact reason.
  - Uncovered source paths, related requirements with no tests, empty selector
    sets, unsafe selectors, and omitted focused prefixes cannot skip the full
    gate. If neither focused nor fallback execution can launch, the request is
    non-zero `nothing-ran`.
  - Focused/full-fallback output logs, gate evidence, and the
    `impact.execution` journal event publish through one rollback-capable
    transaction. Failed publication removes any newly written output log.
- Compatibility behavior: ordinary `verify impact` is unchanged; ordinary
  full-gate commands retain their existing command execution behavior. WAEGIS
  validates the optional field and preserves it when regenerating a configured
  workflow without making it a newly required non-interactive answer.

## Validation

- Focused commands and results:
  - AEGIS impact/gate/outcome/documentation/CLI coverage: `108 passed`.
  - WAEGIS workflow/configuration compatibility coverage: `44 passed`.
- Full commands and results:
  - AEGIS: `uv run --group dev python -m pytest -q tests` -> `620 passed, 3 skipped`.
  - WAEGIS: `uv run --group dev python -m pytest -q tests` -> `700 passed, 8 skipped`.
- CLI/manual checks:
  - `uv run --group dev python -B -m aegis --help` -> passed.
  - `uv run --group dev python -B -m aegis verify impact --help` -> passed and
    names the action-local `--run` flag.
  - `uv run --group dev python -B -m waegis --help` -> passed.
  - Changed-file Ruff and `python -B -m py_compile` passed for AEGIS and
    WAEGIS Python files and tests.

## Context effect

- Before bytes/tokens: no WP5 context-pack change applies.
- After bytes/tokens: no bootstrap files or `run context` fields changed. WP2's
  byte budget remains unaffected; tokenizer telemetry remains WP8 work.

## Review

- Reviewer host/model/effort: implementation-session strict source, diff,
  whitespace, cache, and generic-template audit; independent other-provider
  review was not available in this delegated worktree.
- Findings: the initial WAEGIS prompt addition made the optional prefix a
  required non-interactive answer, breaking existing answer files.
- Resolution: retain WAEGIS validation and generation preservation while
  leaving the new field optional for existing installer inputs.

## Remaining risk

- Follow-up correction: focused impact selection now checks every matched
  requirement record for linked tests before using the aggregate selector set.
  A public CLI regression covers a mixed linked/testless match and verifies
  full-fallback output, evidence, and journal records with no focused launch.
- Unverified behavior: an independent other-provider review remains pending;
  no external downstream project was executed in this package.
- Next allowed package: WP6 after independent review and approval of this WP5
  boundary.
