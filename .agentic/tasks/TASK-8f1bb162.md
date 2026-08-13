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

# TASK-8f1bb162 — Clarify global grammar and retain error selection context

stage: deliver
type: fix
path: quick
requirements: REQ-FUNC-a6f115bd, REQ-REL-7093e21e, REQ-PLAT-7cd54b8e, REQ-PLAT-f183e3cc
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged except for journal-only delivery records
- [x] validation evidence, diff, exclusions, and outcome prepared for presentation
- [x] delivery is limited to the requested unstaged and uncommitted handoff
- [x] journal is included in the unstaged candidate; no report or delivery commit is authorized
- [x] no commit, PR, push, fetch, publish, branch, or worktree action performed
- [x] close-out publication is excluded by the delegated instruction

## Log

- 2026-08-13 frame: scope is the compatible G-27 global-option placement diagnostic, G-28 truthful post-resolution error context, and G-29 canonical next-action input vocabulary with focused tests, help or full-AEGIS documentation, and Unreleased changelog coverage.
- 2026-08-13 frame: exclusions are grammar aliases or broadening, protocol redesign, shell command strings, AEGIS Light or managed-payload changes, planning/requirements/knowledge/spec edits, broad suites, review directories, unrelated shared-tree work, Git publication, and F:/2026_VoiceWeaver.
- 2026-08-13 frame: quick path is required by the delegated task because this is a small backward-compatible correction to existing PR-PROTO and PR-HOST behavior with no new dependency or data-handling boundary.
- 2026-08-13 frame: branch remains master under the explicit instruction not to create or switch branches; scope and existing requirements REQ-FUNC-a6f115bd, REQ-REL-7093e21e, REQ-PLAT-7cd54b8e, and REQ-PLAT-f183e3cc are confirmed by the detailed delegation.
- 2026-08-13 frame: the delegated validation contract overrides AEGIS Light build defaults by forbidding requirement edits, `test --impacted`, and all full or unfiltered suites.
- 2026-08-13 build red G-27: command=`uv run --group dev python -m pytest -q tests/test_cli_protocol.py::test_global_option_after_command_explains_canonical_placement`; exit=1; expected missing behavior=known misplaced root option lacks the canonical global-options-precede-command explanation.
- 2026-08-13 build red G-28: command=`uv run --group dev python -m pytest -q tests/test_cli_protocol.py::test_post_resolution_errors_retain_truthful_selection_context`; exit=1; expected missing behavior=post-resolution missing-revision error returns null Run, Stage, and revision context.
- 2026-08-13 build red G-29: command=`uv run --group dev python -m pytest -q tests/test_cli_protocol.py::test_next_action_arguments_use_operation_input_vocabulary`; exit=1; expected missing behavior=revision read action emits conflicting stage rather than canonical stage_name input vocabulary.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q` with nine exact G-27/G-28/G-29 and adjacent F-08/F-11 selectors; exit=0; result=9 passed in 5.04s.
- 2026-08-13 build: AEGIS Light requirement, knowledge, and impacted-test updates remain intentionally excluded by the delegated scope, and the journal advanced to validate after the three independent regressions and adjacent focused set passed.
- 2026-08-13 validate self-review: the bounded diff preserves canonical grammar and F-11 examples, enriches only post-resolution error results through guarded read-only loads, prefers durable explicit targets with selected-context fallback, retains original errors when context is unreadable, and adds no aliases, shell strings, protocol redesign, network behavior, or unrelated edits.
- 2026-08-13 validate trace review: the four linked existing requirements and both affected component knowledge pages were re-read and remain true; all requirement and knowledge files were preserved under the explicit delegated exclusion.
- 2026-08-13 validate proof: exact nine-selector pytest command exit=0 with 9 passed in 5.15s; py_compile of six changed Python files exit=0; focused Ruff exit=0; root and exact stage.show CLI help exit=0; direct source payload verification returned no findings; exact manifest verification covered 58 files; and `git diff --check` exit=0.
- 2026-08-13 validate advisory: command=`python .agentic/aegis.py check`; exit=0; result=WARN with errors=0 warnings=95 notes=0, all from cumulative shared-tree missing-link, open-delivery-journal, scope-drift, or outside-layout state and none introduced as a blocking task error.
- 2026-08-13 validate exclusions: no full suite, 02_Tools full suite, impacted test runner, broad pytest, strict full-run check, review-directory edit, AEGIS Light payload edit, planning/requirements/knowledge/spec edit, VoiceWeaver access, staging, commit, branch, worktree, fetch, push, publish, or network Git action was performed.
- 2026-08-13 deliver: candidate remains unstaged, uncommitted, and unpushed as explicitly required; delivery is this evidence-backed local handoff only.
