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
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-e93d3d72 — Surface recorded judgement and trace a path back to its requirements

stage: done
type: feature
path: full
requirements: REQ-UX-48bb759b, REQ-FUNC-0f4eb4c5
branch: master
base: cf9e7b34985291e786944b4729a8f5992e5fea09
opened: 2026-08-21

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Log

- 2026-08-21 frame: scope is the two retrieval gaps named in conversation -
  the delivery report leads with the deviations the task recorded, and a new
  `explain` command reports what governs one repository path.
- 2026-08-21 frame: excluded on the owner's explicit instruction - no
  cross-task index of rejected alternatives, and no extraction of the design
  note's rejected alternative into the report either. The report change is
  deviations only; the design-note line remains a later addition if wanted.
- 2026-08-21 frame: excluded by judgement - no `--json` on `explain`. Every
  flag owes documentation and a test, and the stated value here was minimum
  implementation; the human-readable form is what the gap actually asked for.
- 2026-08-21 frame: path full. DEVIATION frame - `design` was folded into
  frame and specify rather than written as its own note. The shape was agreed
  in conversation over two prior messages, so a separate note would have
  restated it; the cost is that the reasoning lives in this log, not under a
  `## Design` heading where a later reader looks first.
- 2026-08-21 frame: DEVIATION frame - stays on `master`, uncommitted, carrying
  forward the owner's standing instruction.
- 2026-08-21 specify: two requirements - REQ-UX-48bb759b for what the report
  leads with (it is a comprehension behavior, so UX), REQ-FUNC-0f4eb4c5 for
  the new command.
- 2026-08-21 build: red recorded before implementing -
  `python -m pytest -q 05_Software/aegis/tests/test_run_report.py -k "explain or deviation"`
  exited non-zero with 5 failed: two asserting a `- deviations:` line the
  report did not write, three failing on `invalid choice: 'explain'`.
- 2026-08-21 build: anchor recorded after red and before implementation.
- 2026-08-21 build: added `recorded_deviations`, `repo_path_arg` and
  `cmd_explain`, and inserted the deviations block above the diff and check
  totals in `cmd_report`.
- 2026-08-21 build: DEVIATION build - fixed `parse_journal` to rejoin wrapped
  log lines, which nobody asked for. It was needed for deviations to survive
  the margin, and it also repairs `status`, which was printing half-sentences
  for every wrapped entry; the cost is one behavior change outside the two
  requirements, covered by the deviation tests and the full suite.
- 2026-08-21 build: `explain` normalizes backslashes on every platform, not
  only Windows, so a path copied from one machine means the same thing in a
  Linux CI job.
- 2026-08-21 validate: dogfooded immediately, and `explain` found real drift
  of my own making - REQ-FUNC-500cfb8b was claimed by no knowledge page.
  Claimed it on `reusable-workflow-payload`, and this task's two on
  `validation-and-evidence-cli`.
- 2026-08-21 validate: `explain` truncates with ASCII `...` rather than an
  ellipsis: its output only ever reaches a console, and a console under a
  legacy code page mangles anything else - the same finding that put `--out`
  on `diagram`.
- 2026-08-21 validate: architecture diagram on `validation-and-evidence-cli`
  revised for the new shape, per the contract added by TASK-547a7abd. Recorded
  at validate rather than design because this task had no separate design
  stage; the diagram describes what was built, so it carries no intended-shape
  label.
- 2026-08-21 validate: DEVIATION validate - `check --run` went red on lint
  after the docs pass: ruff RUF010 on an explicit `str()` inside an f-string in
  `cmd_explain`. Fixed with the conversion flag rather than suppressed; the
  cost was one extra full validation cycle.
- 2026-08-21 validate: user documentation updated - the CLI reference gained
  the `explain` section, summary row and exit row, the FAQ gained "I'm reading
  a file I didn't write", and the feature walkthrough shows the command in use.
- 2026-08-21 validate: final `check --strict --run` after all edits - errors=0
  warnings=10 notes=3, `strict: ok`; suite 214 passed 2 skipped, lint clean.
  Every warning is `outside-layout` on repository documentation, or
  `unticked-deliver` on the three uncommitted journals.

## Delivery report (2026-08-21)

- stage: deliver; type: feature; path: full; branch: master
- requirements:
  - REQ-UX-48bb759b - Lead the delivery report with the deviations recorded during the task
  - REQ-FUNC-0f4eb4c5 - Trace a repository path back to the requirements and tasks that govern it
- deviations: 4 recorded
  - frame - `design` was folded into frame and specify rather than written as its own note. The shape was agreed in conversation over two prior messages, so a separate note would have restated it; the cost is that the reasoning lives in this log, not under a `## Design` heading where a later reader looks first.
  - frame - stays on `master`, uncommitted, carrying forward the owner's standing instruction.
  - build - fixed `parse_journal` to rejoin wrapped log lines, which nobody asked for. It was needed for deviations to survive the margin, and it also repairs `status`, which was printing half-sentences for every wrapped entry; the cost is one behavior change outside the two requirements, covered by the deviation tests and the full suite.
  - validate - `check --run` went red on lint after the docs pass: ruff RUF010 on an explicit `str()` inside an f-string in `cmd_explain`. Fixed with the conversion flag rather than suppressed; the cost was one extra full validation cycle.
- diff vs task base cf9e7b3: 41 file(s) changed, 3861 line(s) added
- checks: errors=0 warnings=17 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the
