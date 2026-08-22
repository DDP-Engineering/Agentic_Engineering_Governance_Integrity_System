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

# TASK-547a7abd — Carry each component's architecture in its knowledge page

stage: done
type: change
path: full
requirements: REQ-FUNC-500cfb8b
branch: master
base: cf9e7b34985291e786944b4729a8f5992e5fea09
opened: 2026-08-21

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Log

- 2026-08-21 frame: scope is the workflow contract for component architecture
  diagrams - the component page template gains an architecture section, adoption
  draws one per component, and design revises it for the component a task
  changes, including the shape it is meant to have afterwards.
- 2026-08-21 frame: excluded - no derived call graph. A prototype over this
  repository's own `aegis.py` read cleanly with stdlib `ast`, but an analyzer
  exists for one language only and derivation can never draw a shape that does
  not exist yet; both defeat the point.
- 2026-08-21 frame: excluded - no `check` rule for diagram drift. `check` does
  not read knowledge page content today, and adding a scan is a larger change
  than the contract this task is agreeing.
- 2026-08-21 frame: path full - this changes the workflow contract two stages
  owe, which is a durable obligation rather than a fix.
- 2026-08-21 frame: source and timing chosen by the owner from three options -
  authored into the knowledge page, drawn at adopt and revised at design.
- 2026-08-21 frame: DEVIATION frame - stays on `master` with no task branch and
  will not be committed, carrying forward the owner's standing instruction from
  the previous task.
- 2026-08-21 specify: one requirement, REQ-FUNC-500cfb8b. Its verification is an
  `Inspection:` method because the behavior is a workflow obligation in prose;
  the two structural tests guard that the prose says what it must, which is a
  different claim from the obligation being followed.
- 2026-08-21 build: red recorded before editing the payload -
  `python -m pytest -q 05_Software/aegis/tests/test_structure.py -k architecture`
  exited non-zero with 2 failed, both `AssertionError: '## Architecture' in ...`,
  because no payload file mentioned the section.
- 2026-08-21 build: anchor recorded at cf9e7b3 over 72 files, after red and
  before the first payload edit.
- 2026-08-21 build: added the `## Architecture` section to the component
  template with the size guidance, the direction rule, and a worked fence;
  adoption gained step 7 and a Done-when item; design gained step 7, an output
  and a Done-when item; validate gained the reconciliation and the instruction
  to drop the intended-shape label.
- 2026-08-21 build: inserting a numbered step renumbered the rest of both step
  files; corrected a duplicate `8.` and the continuation indents that a
  single-to-double digit change breaks.
- 2026-08-21 validate: diff reviewed - 4 payload files, their mirrored copies,
  one knowledge page, the folder guide and the changelog. No code changed, so
  no portability or security surface moved. No unrequested work.
- 2026-08-21 validate: dogfooded on `validation-and-evidence-cli`, the one
  component this session read closely - it now carries a 15-node architecture
  diagram. The other five pages are left without one deliberately: writing
  diagrams for components I have not read would be invention, and the contract
  says adoption draws them with the source open.
- 2026-08-21 validate: DEVIATION validate - REQ-FUNC-500cfb8b first declared an
  `Inspection:` verification while also linking two structural tests. That is
  the manual-label-for-an-automatable-test substitution the workflow warns
  against; rewrote the field as the plain observation the tests make.
- 2026-08-21 validate: evolution refreshed - 4 modified payload files, all
  expected. `check --strict --run` after all edits: errors=0 warnings=4 notes=3,
  `strict: ok`, suite and lint green.
- 2026-08-21 validate: DEVIATION validate - accepted three `outside-layout`
  warnings for `CHANGELOG.md`, `06_SoftwareDocu/02_Folders_and_Files.md` and
  `09_CLI_Reference.md`, and one `unticked-deliver` for the previous task, which
  is uncommitted by instruction. Same standing cost as before: repository
  documentation sits outside the configured globs.
- 2026-08-22 deliver: DEVIATION deliver - reconciled after the fact:
  delivery was carried by release commit 1926871 with these items still
  unticked, so they are ticked retroactively at the owner's instruction.

## Delivery report (2026-08-21)

- stage: deliver; type: change; path: full; branch: master
- requirements:
  - REQ-FUNC-500cfb8b - Carry a component architecture diagram in its knowledge page
- diff vs task base cf9e7b3: 30 file(s) changed, 2410 line(s) added
- checks: errors=0 warnings=9 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the
- 2026-08-21 validate: user documentation updated in the same change, per the
  repository rule. Returned both journals to `stage: validate` first, because
  editing the candidate after reaching `deliver` is a return, not a shortcut.
- 2026-08-21 validate: user documentation updated - `02_Folders_and_Files.md`
  describes the architecture section and why it is authored rather than derived,
  `03_Example_Feature.md` shows design redrawing a component and validate
  dropping the intended-shape mark, `05_Example_Adoption.md` shows the diagram
  being drawn per component, and `07_FAQ.md` answers "Why isn't the architecture
  diagram generated from my code?" with its cost stated.
- 2026-08-21 validate: DEVIATION validate - the `.pptx` decks beside these
  guides still carry the 18 August text and are now behind their Markdown
  siblings. They are built outside this repository's tooling, so this change
  cannot regenerate them; the cost is that a reader opening a deck sees the
  workflow without the architecture step.

## Delivery report (2026-08-21)

- stage: deliver; type: change; path: full; branch: master
- requirements:
  - REQ-FUNC-500cfb8b - Carry a component architecture diagram in its knowledge page
- diff vs task base cf9e7b3: 35 file(s) changed, 2528 line(s) added
- checks: errors=0 warnings=14 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the

## Delivery report (2026-08-21)

- stage: deliver; type: change; path: full; branch: master
- requirements:
  - REQ-FUNC-500cfb8b - Carry a component architecture diagram in its knowledge page
- deviations: 4 recorded
  - frame - stays on `master` with no task branch and will not be committed, carrying forward the owner's standing instruction from the previous task.
  - validate - REQ-FUNC-500cfb8b first declared an `Inspection:` verification while also linking two structural tests. That is the manual-label-for-an-automatable-test substitution the workflow warns against; rewrote the field as the plain observation the tests make.
  - validate - accepted three `outside-layout` warnings for `CHANGELOG.md`, `06_SoftwareDocu/02_Folders_and_Files.md` and `09_CLI_Reference.md`, and one `unticked-deliver` for the previous task, which is uncommitted by instruction. Same standing cost as before: repository documentation sits outside the configured globs.
  - validate - the `.pptx` decks beside these guides still carry the 18 August text and are now behind their Markdown siblings. They are built outside this repository's tooling, so this change cannot regenerate them; the cost is that a reader opening a deck sees the workflow without the architecture step.
- diff vs task base cf9e7b3: 41 file(s) changed, 3889 line(s) added
- checks: errors=0 warnings=15 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the
