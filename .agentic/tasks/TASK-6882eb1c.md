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

# TASK-6882eb1c — Compare green executions with every red witness

stage: deliver
type: fix
path: quick
requirements: REQ-TEST-c33c5899
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

- 2026-08-13 frame: Fix green test-integrity comparison so it deterministically unions changes against every usable recorded red witness while preserving immutable evidence, advisory findings, provenance, selection, and completion behavior.
- 2026-08-13 frame exclusions: Do not change AEGIS Light implementation or managed payload, planning requirements or reviews, unrelated cumulative work, execution blocking, Stage transitions, witness recording, test repair, or developer judgement, and do not stage, commit, branch, switch, push, publish, or use network Git.
- 2026-08-13 frame path: Quick path is proportionate because PR-INT-002 and PR-INT-004 already require complete fingerprint comparison and immutable red evidence, with no new interface, data format, dependency, security behavior, or data-handling behavior.
- 2026-08-13 frame branch: Remain on master because the developer explicitly required the current branch and prohibited branch creation or switching.
- 2026-08-13 frame requirements: Implement existing PR-INT-002 and PR-INT-004 without editing planning or AEGIS Light requirement artifacts.
- 2026-08-13 frame applicability: The cumulative checkout still selects only the latest red witness in execution_operations.py, so a later Check revisit can hide a test changed since an earlier usable witness.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_comparison_uses_every_recorded_red_witness`; exit=1; expected missing behavior=changed_tests contained only the later throwaway test and omitted the original test changed since the first durable red witness.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_comparison_uses_every_recorded_red_witness`; exit=0; result=1 passed with both original and later changed test paths reported and both Check witnesses unchanged.
- 2026-08-13 build focused: command=`uv run --group dev python -m pytest -q` with the new regression plus six nearby red-witness, fingerprint, and provenance selectors; exit=0; result=7 passed in 51.75 seconds.
- 2026-08-13 build traceability: Reused active REQ-TEST-c33c5899 unchanged because it already covers an immutable prior red witness plus later green execution and the campaign excludes AEGIS Light requirement edits.
- 2026-08-13 build check: command=`python .agentic/aegis.py check --task TASK-6882eb1c`; exit=0; result=WARN with 47 cumulative-checkout warnings from pre-existing unlinked requirements, five earlier Delivery-review journals, planning/review/docs layout, AEGIS Light work, and previously dirty full-AEGIS files outside this bounded task.
- 2026-08-13 build exception: The developer explicitly deferred `test --impacted` and the complete suite until campaign end, so neither command nor any fallback capable of launching them was invoked.
- 2026-08-13 validate review: Reviewed the scoped source/test/docs/manifest hunks against PR-INT-002/004, malformed witness entries, deterministic ordering, Windows/Linux path behavior, advisory findings, immutable evidence, payload compatibility, provenance, selection, completion, and unrequested work; no scope correction was needed.
- 2026-08-13 validate knowledge: Reviewed `.agentic/knowledge/aegis-workflow-application.md`; its purpose, interfaces, immutable red-evidence behavior, and file inventory remain current, so no knowledge edit is warranted.
- 2026-08-13 validate requirements: Re-read active REQ-TEST-c33c5899 and authoritative PR-RED/PR-INT plus AM-STAGE-011 and AM-EVIDENCE-004-008; the existing requirement remains true and planning artifacts remain untouched by this task.
- 2026-08-13 validate static: `py_compile` for both changed Python files, focused Ruff, AEGIS CLI help, and `git diff --check` each exited 0; Ruff reported all checks passed and CLI help exposed 48 operations for AEGIS 1.0.0.
- 2026-08-13 validate payload: Direct source-template `verify_payload()` returned zero findings and the stored manifest exactly matched canonical regeneration with `product_version=1.0.0` and `platform=windows`.
- 2026-08-13 validate strict: command=`python .agentic/aegis.py check --task TASK-6882eb1c --strict` without `--run`; exit=0; result=`strict: ok` with 47 accepted cumulative-checkout warnings and no errors.
- 2026-08-13 validate warnings: The 47 warnings are the same pre-existing categories recorded at Build—three unlinked requirements, five prior Delivery-review journals, and unrelated dirty planning, review, AEGIS Light, documentation, delivery, and earlier full-AEGIS files—so none was corrected or adopted into this task.
- 2026-08-13 validate suite deferral: The complete pytest suite and AEGIS Light impacted-test runner remain intentionally unexecuted per the developer's campaign-level instruction.
