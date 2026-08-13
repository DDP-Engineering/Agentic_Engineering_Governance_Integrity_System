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

# TASK-01ecf3b2 — Ignore generated files in Check zone snapshots

stage: deliver
type: fix
path: full
requirements: REQ-PLAT-97b168cf, REQ-PLAT-4253ae41
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

- 2026-08-13 frame: scope is only independently confirmed G-04, replacing the Check snapshot's whole-repository file walk with the existing tracked-plus-unignored Git-visible path set while preserving exact-byte hashing, Git-state classifications, fallback behavior, read-only observation, and advisory findings.
- 2026-08-13 frame: exclusions are every other review finding, all review directories, pre-existing dirty planning and cumulative G-01/G-02/G-03 candidate work, AEGIS Light implementation/payload/plans/managed files and requirements, global `list_files` behavior, denial/configuration/size/environment changes, broad snapshot or attribution refactors, Git staging/branching/commit/push, and full-suite execution.
- 2026-08-13 frame: full path chosen because the durable Check snapshot and its externally visible findings change; explicit user instruction keeps the checkout on master instead of creating a task branch, and autopilot continues through build and validate to Delivery review.
- 2026-08-13 frame: existing REQ-PLAT-97b168cf and REQ-PLAT-4253ae41 plus authoritative PR-ZONE-001-007, PR-INT-003, FS-INTEGRITY-007, and IP-11 cover the behavior; no new requirement is proposed.
- 2026-08-13 specify: reused both active platform requirements unchanged because the full-AEGIS planning contract already defines read-only machine-stable Git observation, and the user's scope excludes AEGIS Light requirement edits made only for traceability.
- 2026-08-13 specify: no separate specification is needed because G-04 and DESIGN_FINGERPRINT_SCOPE.md define the path-set, exact-byte hashing, fallback, and non-blocking constraints directly.

## Design

- Components: the full-AEGIS filesystem/Git workspace adapter and its existing Check workflow consumer only (REQ-PLAT-97b168cf; REQ-PLAT-4253ae41).
- Interface: `git_snapshot()` retains its current keys and classifications; only `working_files` membership changes from every filesystem file to `git_visible_files(".")` (REQ-PLAT-97b168cf).
- Data: hash exact bytes for each safe existing tracked or unignored untracked path returned by the helper, preserving tracked files that later match ignore rules and the helper's filesystem fallback if Git listing fails (REQ-PLAT-97b168cf).
- Compatibility: staged, unstaged, untracked, deleted, renamed, branch, HEAD, index, and advisory Check findings remain unchanged, and observation remains read-only (REQ-PLAT-4253ae41).
- Rejected alternative: a cache denylist, new setting, size cap, child environment change, global `list_files` change, or broader attribution refactor would exceed the contract and duplicate repository ignore policy.
- Test seam: a synthetic installed Git repository enters Check, an AEGIS-launched deterministic test creates an ignored `.pytest_cache` artifact, a real source file changes, and completion must omit the ignored path while still reporting the source.
- Expected candidate files: `infrastructure/workspace.py`, `tests/test_execution_integrity.py`, payload `manifest.toml`, and this journal; README/changelog only if direct review shows public documentation needs correction.
- 2026-08-13 design: the note above supplies a single decision-free implementation path; no separate AEGIS Light requirement/specification edit is warranted.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_zone_comparison_ignores_gitignored_paths`; exit=1; expected missing behavior=Check reports ignored AEGIS-launched `.pytest_cache/v/cache/nodeids` alongside the genuine tracked `src/app.py` change instead of limiting out-of-zone findings to Git-visible files.
- 2026-08-13 build refinement red: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_git_visible_files_fall_back_when_git_is_unavailable`; exit=1; expected missing behavior=repository-root Git listing failure falls through to `list_files(".")`, which rejects the root instead of returning safe files with snapshot exclusions.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_fingerprints_exclude_ignored_cache_files tests/test_execution_integrity.py::test_tracked_test_stays_fingerprinted_when_gitignored tests/test_execution_integrity.py::test_git_visible_files_fall_back_when_git_is_unavailable tests/test_execution_integrity.py::test_git_visible_files_skip_tracked_deleted_paths tests/test_execution_integrity.py::test_zone_comparison_ignores_gitignored_paths tests/test_execution_integrity.py::test_check_git_comparison_reports_implementation_change_without_mutation tests/test_execution_integrity.py::test_git_snapshot_classifies_staged_unstaged_untracked_rename_and_delete`; exit=0; result=7 passed in 26.32s on final test/source bytes.
- 2026-08-13 build impacted: not run because the explicit user instruction forbids the AEGIS Light test fallback and defers the full suite to campaign end; the exact scoped full-AEGIS selectors above replace it without a green full-suite claim.
- 2026-08-13 build scope exception: both existing platform requirements remain active and unchanged by explicit user scope, so their affected paths and linked tests were not edited merely for AEGIS Light traceability.
- 2026-08-13 build check: command=`python .agentic/aegis.py check`; exit=0 with 60 advisory warnings from pre-existing/excluded/concurrent journals, AEGIS Light work, planning/review paths, known unlinked requirements, and outside-layout/stage-zone notices; no unrelated file was changed for those warnings.
- 2026-08-13 build: payload manifest regenerated from final cumulative payload bytes with product_version=1.0.0 and platform=windows.
- 2026-08-13 validate review: the scoped diff matches G-04, keeps all Git-state classifications and advisory findings, limits normal snapshots to tracked plus unignored files, provides a root-only safe fallback with the prior `.git/` and runtime exclusions, and adds no denylist, configuration, environment change, global listing change, or attribution refactor.
- 2026-08-13 validate knowledge: the persistence/runtime-adapter and workflow-application knowledge pages were re-read and remain true without edits; the full-AEGIS README and root changelog document the corrected snapshot boundary.
- 2026-08-13 validate requirements: REQ-PLAT-97b168cf and REQ-PLAT-4253ae41 remain active and accurate, and authoritative PR-ZONE-001-007, PR-INT-003, FS-INTEGRITY-007, and IP-11 were re-read without traceability-only AEGIS Light edits.
- 2026-08-13 validate focused: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_fingerprints_exclude_ignored_cache_files tests/test_execution_integrity.py::test_tracked_test_stays_fingerprinted_when_gitignored tests/test_execution_integrity.py::test_git_visible_files_fall_back_when_git_is_unavailable tests/test_execution_integrity.py::test_git_visible_files_skip_tracked_deleted_paths tests/test_execution_integrity.py::test_zone_comparison_ignores_gitignored_paths tests/test_execution_integrity.py::test_check_git_comparison_reports_implementation_change_without_mutation tests/test_execution_integrity.py::test_git_snapshot_classifies_staged_unstaged_untracked_rename_and_delete`; exit=0; result=7 passed in 26.32s on final cumulative source, test, and manifest bytes.
- 2026-08-13 validate static: `python -m py_compile` for the changed workspace module and test, project `ruff check .`, `python -B -m aegis --help`, direct payload verification with product_version=1.0.0/platform=windows, and scoped `git diff --check` all exited 0.
- 2026-08-13 validate strict: command=`python .agentic/aegis.py check --task TASK-01ecf3b2 --strict`; exit=0; result=strict ok with 46 advisory warnings from pre-existing/excluded/concurrent files, known unlinked requirements, and expected outside-layout or uncovered-source notices.
- 2026-08-13 validate deferral: `check --strict --run`, the full AEGIS suite, and the AEGIS Light test fallback were not run by explicit campaign instruction, so no full-suite green result is claimed and campaign-end validation remains required.
- 2026-08-13 validate preservation: G-04 owns only the workspace adapter, ignored-cache/root-fallback test hunks, README/changelog lines, cumulative manifest refresh, and this journal; cumulative G-01/G-02/G-03, AEGIS Light, planning/review, and concurrent dirty files were not edited for this task.
