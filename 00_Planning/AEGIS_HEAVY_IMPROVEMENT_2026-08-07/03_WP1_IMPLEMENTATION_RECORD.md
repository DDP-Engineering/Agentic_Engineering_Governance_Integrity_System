<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WP1 implementation record

- Date: 2026-08-07
- Agent host: Codex
- Exact model: current task model; not exposed in the task record
- Reasoning/effort: current task setting; not exposed in the task record
- Starting commit: `56dde67`
- Starting dirty paths: none
- Scope restated: create one declarative completion contract for every standard
  and adoption stage, render it as deterministic TOML comments in primary
  forms, synchronize stage references, and add exact parity coverage. No WP2
  context command or quick-run behaviour was changed.

## Red observation

- Test command: `uv run --group dev python -m pytest -q tests/test_stage_form_lifecycle.py tests/test_documentation_workflow.py`
- Expected failure: the new contract initially omitted the `ALL_STAGES` import,
  so form preparation could not validate the mapping.
- Observed failure: 20 failures, all rooted in `NameError: ALL_STAGES is not
  defined`; the documentation mapping test also assumed a different dictionary
  insertion order from the lifecycle order.
- Resolution: imported `ALL_STAGES` in `stage_schema.py` and tested reference
  coverage as a complete stage set rather than by unrelated insertion order.

## Changes

- Files: `stage_schema.py`, `stage_forms.py`, 15 stage references, focused
  lifecycle and documentation tests, root changelog, and the workflow-record
  explanation.
- Contract decisions: `STAGE_DONE_WHEN` owns the 15 stage checklists. Every
  item is either a machine item with a named command or an explicit human item.
  Reference checkboxes are a tested projection of the text and classification.
- Compatibility behavior: checklists render only as TOML comments. They do not
  become parsed payload fields; collection guidance appears once in `stage.toml`
  and not in individual requirement or check forms. Re-preparation keeps the
  comments deterministic. Stage digests serialize each parsed TOML payload in
  canonical JSON order, so comment-only or formatting-only edits do not alter
  the submitted state identity.

## Validation

- Focused commands and results:
  `uv run --group dev python -m pytest -q tests/test_stage_form_lifecycle.py tests/test_documentation_workflow.py`
  — `55 passed`.
- Full AEGIS command and result:
  `uv run --group dev python -m pytest -q tests` — `577 passed, 3 skipped`.
- Full WAEGIS command and result:
  `uv run --group dev python -m pytest -q tests` — `699 passed, 8 skipped`.
  The first run reached the host's 120-second command limit while pytest was
  flushing output; the rerun with a longer process allowance completed green in
  126.73 seconds.
- CLI/manual checks:
  `python -m py_compile template/.agentic/cli/src/aegis/stage_schema.py template/.agentic/cli/src/aegis/stage_forms.py`,
  `uv run --group dev python -B -m aegis --help`, and
  `uv run --group dev python -B -m waegis --help` all passed. The direct
  `py_compile` generated template bytecode, which was removed before the final
  AEGIS suite; the final suite confirmed the copied template is cache-free.
- Review-correction validation: focused lifecycle/documentation tests passed
  (`56 passed`); the corrected full AEGIS suite passed (`578 passed, 3
  skipped`); the full WAEGIS suite passed (`699 passed, 8 skipped`); and both
  `python -B -m aegis --help` and `python -B -m waegis --help` passed.

## Context effect

- Before bytes/tokens: not measured in this package.
- After bytes/tokens: not measured in this package. WP2 exclusively owns
  context-pack measurement and enforcement.

## Review

- Reviewer host/model/effort: independent review findings supplied by the
  task owner; host/model/effort not exposed in the task record.
- Findings: the independent WP1 review found that raw form-byte hashing made a
  generated completion comment alter `StageRecord.digest`; it also requested
  package README coverage of the canonical checklist projection.
- Resolution: form digests now hash canonical parsed TOML payloads, a regression
  test proves comment-only mutations retain the digest, and the package README
  documents the generated-form/reference relationship.

## Remaining risk

- Unverified behavior: WP2 context budgets and bootstrap behaviour remain
  intentionally unimplemented.
- Next allowed package: WP2 after independent review and approval of this WP1
  boundary.
