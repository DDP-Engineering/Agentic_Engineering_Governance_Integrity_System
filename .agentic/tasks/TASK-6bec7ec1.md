<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  branch        the branch this task is delivered on
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-6bec7ec1 — Keep run listing available when one Run is unreadable

stage: deliver
type: fix
path: quick
requirements: REQ-FUNC-e04edca3, REQ-REL-c5bc94c6, REQ-REL-360930b1
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [ ] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed only after the outcome succeeded

## Log

- 2026-08-13 frame: Scope is a per-Run `run.list` load-error boundary that preserves healthy summaries, emits one truthful unreadable entry, preserves malformed bytes and normal pagination, and keeps healthy Run operations available; exclusions are repair, fabricated Run state, broad loader changes, planning edits, AEGIS Light payload edits, unrelated dirty work, complete-suite or impacted-suite execution, and all Git publication or branch mutation.
- 2026-08-13 frame: The user explicitly selected the quick path for this bounded compatibility fix under existing Run-coexistence, durable-resume, and malformed-byte-preservation requirements and authorized continuation through Validate to the Delivery review checkpoint.
- 2026-08-13 frame: The checkout remains on current branch `master` by explicit instruction, so the workflow's normal task-branch creation step is intentionally not performed.
- 2026-08-13 frame: Current applicability confirmed because `workflow_operations._run_list` still loads each listed Run without a `UseCaseError` or `WorkspaceError` boundary, allowing one malformed `run.md` to abort discovery of every Run.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_run_stage_workflow.py::test_run_list_degrades_over_an_unreadable_run`; exit=1; expected missing behavior=`run-list` returned exit 4 instead of preserving the healthy summary and degrading only the malformed Run.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q tests/test_run_stage_workflow.py::test_run_list_degrades_over_an_unreadable_run`; exit=0; result=1 passed in 1.49s.
- 2026-08-13 build compatibility: exact regression plus normal multiple-Run listing, cursor pagination, and normal/exceptional abandonment selectors passed 4 tests in 5.16s.
- 2026-08-13 build: linked the source and focused regression to REQ-FUNC-e04edca3, REQ-REL-c5bc94c6, and REQ-REL-360930b1, kept each active, and regenerated the payload manifest canonically for AEGIS 1.0.0 on Windows.
- 2026-08-13 validate: semantic review confirmed the boundary catches only `UseCaseError` and `WorkspaceError` per Run, uses exception path metadata or the canonical known `run.md` path, preserves page membership and healthy fields, emits no raw bytes or fabricated Run summary, and performs no mutation.
- 2026-08-13 validate: final focused command for the unreadable regression, normal multiple-Run listing, cursor pagination, and normal/exceptional abandonment exited 0 with 4 passed in 5.27s.
- 2026-08-13 validate: `python -m py_compile` for the changed source and regression exited 0, focused Ruff exited 0, AEGIS CLI help exited 0, and `git diff --check` exited 0.
- 2026-08-13 validate: direct source-template `verify_payload` returned zero findings and the manifest bytes exactly matched canonical generation for product_version 1.0.0 and platform windows.
- 2026-08-13 validate: `python .agentic/aegis.py check --task TASK-6bec7ec1 --strict` exited 0 with strict ok, zero errors, and 47 warnings from cumulative pre-existing work plus expected documentation layout reporting; the task-owned generated manifest is requirement-linked and no longer reported uncovered.
- 2026-08-13 validate: the complete pytest suite, AEGIS Light `test --impacted`, and any fallback capable of launching the suite were explicitly deferred by campaign instruction and were not invoked.
- 2026-08-13 validate: candidate advanced to Delivery review with no staging, commit, branch change, push, publication, network Git, or modification of the malformed fixture after corruption.
- 2026-08-13 delivery review: Parent review removed the optional AEGIS Light knowledge and requirement trace-link edits to respect the stricter user boundary; task-scoped requirement-link warnings are accepted.
- 2026-08-13 delivery review red refinement: command=`uv run --group dev python -m pytest -q tests/test_run_stage_workflow.py::test_run_list_degrades_over_an_unreadable_run`; exit=1; expected missing behavior=the selected Run became unreadable after pointer resolution but its degraded entry reported `selected: false` instead of preserving the existing selection.
- 2026-08-13 delivery review green refinement: the refined unreadable-Run selector plus normal multiple-Run compatibility selector exited 0 with 2 passed in 3.37s after changing the degraded entry to compare its identity with the resolved selection.
- 2026-08-13 delivery review validation: changed Python compiled, scoped `git diff --check` passed, direct payload verification and canonical AEGIS 1.0.0 Windows manifest comparison passed, and the README required no wording change.
- 2026-08-13 delivery review boundary: the four previously restored AEGIS Light knowledge and requirement files remain unmodified; no full suite, staging, commit, push, or publication occurred.
