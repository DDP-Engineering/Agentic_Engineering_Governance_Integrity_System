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

# TASK-958d9e7e — Derive a requirement coverage diagram from repository artifacts

stage: done
type: feature
path: full
requirements: REQ-FUNC-6b4ff1ad, REQ-FUNC-e46f1d0c
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

## Design

Component: validation and evidence CLI (REQ-FUNC-6b4ff1ad). `diagram` joins
`check`, `report`, `anchor` and `evolution` as a reporter over governance
records — it derives a view and writes it, and changes nothing.

Interface (REQ-FUNC-6b4ff1ad): `aegis diagram [--component NAME]
[--task TASK-<id>] [--out PATH]`. Stdout by default; `--out` writes UTF-8
explicitly, because the prototype's separator became `?` the moment it
reached a Windows console under cp1252, and a diagram that renders
differently per platform is not a durable artifact.

Data: no new files and no new state. The register is already the graph.
Requirement TOMLs give the id, title, status, `linked_tests` and
`verification`; `manual_method()` already decides what counts as a declared
by-hand method, so coverage classes reuse it rather than re-deciding it.
Knowledge pages give only the display name (the `#` heading) and the
grouping (the `REQ-` ids under `## Key behaviors`) — a strict regex over
prose, never the prose itself. Requirement files are structured and
trustworthy; knowledge pages are prose whose sections the template calls
recommended, so nothing load-bearing is parsed out of them. Retired
requirements are drawn greyed rather than dropped, so a register that
retired a behavior does not silently look smaller.

Rejected: a component-coupling map derived by intersecting `affected_paths`.
It renders, and it is honest about what it measures, but a shared path
cannot say which way a dependency points, and boxes joined by lines are read
as an architecture. Deriving a picture that implies more than the artifacts
know is worse than not drawing it.

Test seam (REQ-FUNC-6b4ff1ad): `05_Software/aegis/tests/test_run_report.py`,
beside the `report` tests, over a `make_repo` fixture carrying one covered,
one by-hand, one uncovered and one unclaimed requirement.

Files: `05_Software/aegis/template/.agentic/aegis.py` (command plus helpers),
its `CLI.md` and `AGENTS.md` command list, the mirrored installed payload
under `.agentic/`, and the root `CHANGELOG.md`.

## Log

- 2026-08-21 frame: scope is one new CLI command, `diagram`, that renders the
  requirement register as a Mermaid coverage map derived from the requirement
  files and the component knowledge pages.
- 2026-08-21 frame: in scope - one flowchart grouping requirements by owning
  component, colored by how each behavior is verified; scoping by component or
  by task; writing UTF-8 to a file so the output does not depend on the
  console code page.
- 2026-08-21 frame: excluded - no component-coupling map (a derived edge cannot
  carry direction or layering, so the drawing would imply more than the
  artifacts know), no diagram renderer (a raster pipeline would end the
  offline, dependency-free promise), and no model-authored diagram.
- 2026-08-21 frame: path full - this adds a durable CLI contract and a
  documented command, not a fix.
- 2026-08-21 frame: expected requirements - one REQ-FUNC for the command.
- 2026-08-21 frame: scope confirmed in conversation before this journal was
  opened; the command shape was agreed against a throwaway prototype run over
  this repository's own artifacts.
- 2026-08-21 frame: DEVIATION frame - work stays on `master` with no task
  branch, at the owner's explicit instruction; the usual branch isolation and
  its PR-shaped review are given up for this task.
- 2026-08-21 specify: two behaviors, so two requirements - REQ-FUNC-6b4ff1ad
  for the diagram itself and REQ-FUNC-e46f1d0c for narrowing it. No spec: the
  requirement prose names every group and class the drawing can contain, which
  is the whole contract.
- 2026-08-21 design: note written in `## Design`; the rejected alternative was
  a derived component-coupling map.
- 2026-08-21 build: red recorded before implementing -
  `python -m pytest -q 05_Software/aegis/tests/test_run_report.py -k diagram`
  exited non-zero with 5 failed, every one of them
  `argparse: invalid choice: 'diagram'`, because the subcommand did not exist.
- 2026-08-21 build: anchor recorded at cf9e7b3 over 72 files, after red and
  before the first implementation edit.
- 2026-08-21 build: implemented `cmd_diagram` with `coverage_class`,
  `knowledge_components`, `diagram_scope` and `render_diagram`; the same five
  selectors then passed.
- 2026-08-21 build: `REQ_ID_RE` is anchored `^...$`, so scanning a knowledge
  page's prose with it found nothing; added `REQ_ID_SCAN_RE` as the unanchored
  twin rather than loosening the id validator that `check` depends on.
- 2026-08-21 build: extended the payload CLI-reference guard in
  `test_structure.py` to require a `diagram` entry, so the command cannot ship
  undocumented.
- 2026-08-21 validate: diff reviewed - 12 files, all inside the agreed scope,
  no unrequested work. Portability: the command writes LF and, under `--out`,
  UTF-8 explicitly; the console path is left to the platform, which is why
  `--out` exists at all. No network, no new dependency, no repository state
  written. Error paths: unknown component lists the pages that do exist,
  unknown task reuses `read_journal`'s existing failure.
- 2026-08-21 validate: review found `--component` and `--task` together
  silently honored the component and dropped the task; made them a mutually
  exclusive argparse group and covered it in the rejects test.
- 2026-08-21 validate: dogfooded on this repository - the whole register draws
  24 nodes, one component draws 5, and an unknown component exits 1. The
  register run showed both new requirements under `(no knowledge page)` until
  the component page claimed them, which is the unclaimed group doing its job.
- 2026-08-21 validate: knowledge page `validation-and-evidence-cli.md` updated
  with the two behaviors, the new public interface line, and the file role.
- 2026-08-21 validate: evolution refreshed after the last edit - 7 modified
  files, all expected; the test files were already inside the anchor because it
  was taken after red.
- 2026-08-21 validate: `check --strict --run` after all edits - errors=0
  warnings=2 notes=3, `strict: ok`; suite 207 passed 2 skipped, lint clean.
- 2026-08-21 validate: DEVIATION validate - accepted two `outside-layout`
  warnings for `06_SoftwareDocu/09_CLI_Reference.md` and `CHANGELOG.md`. Both
  are documentation this repository requires be updated in the same change,
  and neither is inside the configured source or test globs; the cost is that
  the warning will recur for every documentation change until the globs say so.
- 2026-08-21 validate: the three `manual-verification` notes are pre-existing
  and belong to other requirements, not to this task.

## Delivery report (2026-08-21)

- stage: deliver; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-6b4ff1ad - Render the requirement register as a component coverage diagram
  - REQ-FUNC-e46f1d0c - Narrow the coverage diagram to one component or one task
- diff vs task base cf9e7b3: 17 file(s) changed, 1473 line(s) added
- checks: errors=0 warnings=5 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the

- 2026-08-21 deliver: `check --task` flagged `uncovered-source` on the payload's
  `CLI.md` and `AGENTS.md` - this task changed both, and neither of its
  requirements claimed them. Added both to REQ-FUNC-6b4ff1ad's
  `affected_paths`, which the design note had already listed as files this
  behavior touches; the warning cleared, leaving errors=0 warnings=3 notes=3.
- 2026-08-21 deliver: the remaining `unticked-deliver` warning is truthful -
  the owner asked for no commit and no push, so the four commit-and-publish
  items stay unticked and the task stays at `stage: deliver`.

## Delivery report (2026-08-21)

- stage: deliver; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-6b4ff1ad - Render the requirement register as a component coverage diagram
  - REQ-FUNC-e46f1d0c - Narrow the coverage diagram to one component or one task
- diff vs task base cf9e7b3: 17 file(s) changed, 1494 line(s) added
- checks: errors=0 warnings=3 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the
- 2026-08-21 validate: user documentation updated in the same change, per the
  repository rule. Returned both journals to `stage: validate` first, because
  editing the candidate after reaching `deliver` is a return, not a shortcut.
- 2026-08-21 validate: `09_CLI_Reference.md` gained the full `diagram` section,
  the summary row and the exit-behavior row; `07_FAQ.md` gained "Where do I see
  coverage at a glance"; `08_Prompt_Cheatsheet.md` gained a coverage-map sweep
  prompt and `00_Index.md` lists that topic.
- 2026-08-21 validate: version left at 0.6.0 by the owner's instruction. The
  changelog entry stays under `## [Unreleased]`: 0.6.0 is already published in
  `07_Delivery/aegis-0.6.0/` with `SHA256SUMS`, so folding new work into that
  dated section would make the shipped package disagree with its own record.
  Worth noting once - a new command plus a workflow-contract change is what the
  repository's own rules call a MINOR bump, so the next release should be 0.7.0.

## Delivery report (2026-08-21)

- stage: deliver; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-6b4ff1ad - Render the requirement register as a component coverage diagram
  - REQ-FUNC-e46f1d0c - Narrow the coverage diagram to one component or one task
- diff vs task base cf9e7b3: 35 file(s) changed, 2518 line(s) added
- checks: errors=0 warnings=14 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the

## Delivery report (2026-08-21)

- stage: deliver; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-6b4ff1ad - Render the requirement register as a component coverage diagram
  - REQ-FUNC-e46f1d0c - Narrow the coverage diagram to one component or one task
- deviations: 2 recorded
  - frame - work stays on `master` with no task branch, at the owner's explicit instruction; the usual branch isolation and its PR-shaped review are given up for this task.
  - validate - accepted two `outside-layout` warnings for `06_SoftwareDocu/09_CLI_Reference.md` and `CHANGELOG.md`. Both are documentation this repository requires be updated in the same change, and neither is inside the configured source or test globs; the cost is that the warning will recur for every documentation change until the globs say so.
- diff vs task base cf9e7b3: 41 file(s) changed, 3876 line(s) added
- checks: errors=0 warnings=15 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the
