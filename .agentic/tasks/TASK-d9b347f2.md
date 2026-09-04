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
  parent        optional top-level TASK-id; blank for an ordinary task
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.

Stage report is one replaceable latest snapshot, not an evidence store.
Use plain one-line fields with no fences or bullets inside that section.
stage is the reported stage; current must match the journal header after any
transition. result is in_progress | completed | paused | blocked | skipped.
Keep all observations and decisions in the append-only Log as well.
Leave unknown fields blank; summary prints not recorded, never an assumed pass.
Refresh after work or decisions even if current has not changed.
-->

# TASK-d9b347f2 — Improve component knowledge routing

stage: done
type: change
path: quick
requirements: REQ-FUNC-b8f0efc5, REQ-FUNC-500cfb8b
parent:
branch: ddp/improve-component-knowledge-page
base: 6f821f7f8eff846eefca75ddd6bec5ce31cdd7b1
opened: 2026-09-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: A component page can compress repository context only after an agent
recognizes that the requested feature belongs to that component; the current
validation CLI page describes the implementation but does not explicitly route
feature language to starting files, invariants, and verification seams.

Desired outcome: Produce one compact, fact-checked component-page prototype
that helps an implementation agent select the component, its starting code,
and relevant tests from a realistic feature prompt.

Actors: The implementation agent consuming the page and the maintainer keeping
the component record current.

Primary scenario: A feature or fix prompt names validation behavior -> the
agent reads the component page -> routing hints identify this component -> the
change map and invariants focus inspection on the relevant source and tests ->
the agent continues with targeted repository evidence.

Examples: Add a trace export format; change coverage classification; change
anchor or evolution evidence behavior.

Counterexamples: Changing the reusable component template, adding a generated
knowledge index, altering the CLI, or treating the page as a substitute for
reading the exact source and tests.

In scope: Edit only
`.agentic/knowledge/validation-and-evidence-cli.md`; add routing, invariants,
related-boundary guidance, and a change map; evaluate the resulting page
against three representative prompts and record the observations here.

Out of scope: Product code, tests, requirements, reusable payload templates,
other component pages, automated freshness checks, generated indexes, commits,
and publication.

Constraints: Preserve current implementation facts and requirement links; keep
the page compact enough to save context; use code-searchable names; make no Git
commit as instructed by the user.

Success signals: Each trial identifies the correct component, starting source
seam, focused tests, relevant invariant, and neighboring boundary without a
repository-wide source read; the final page remains a current-state map rather
than task history.

Evidence: STATED - the user wants component pages to familiarize an agent and
reduce context, approved this pilot, and prohibited commits. OBSERVED - the
current page has Purpose, Public interface, Key behaviors, Architecture, and
Files, while the stage instructions load component knowledge before targeted
source and tests. OBSERVED - the current page has no explicit routing,
invariants, related-components, or change-map section. INFERRED - those sections
should reduce discovery work for feature-oriented prompts. UNKNOWN - whether a
future structured index or automated path ownership check is worth its cost.

Assumptions: This documentation-only prototype does not change software
behavior; its evaluation belongs in the task journal rather than a new durable
product artifact.

Unknowns: The best final metadata syntax and system-wide indexing mechanism are
deferred until the page structure has been evaluated.

Decision-blocking questions: Scope acceptance at the normal frame checkpoint.

Proposed behaviors: No software behavior changes. The page should route an
agent from feature language to current component evidence while preserving the
existing architecture and requirement record.

Path and reason: Quick path. The change is documentation-only, introduces no
interface, format, dependency, security, data-handling, or externally observable
behavior, and stays within the existing durable component-knowledge and current
architecture requirements.

Quick-path criteria:

| Criterion | Result | Evidence |
|---|---|---|
| No new externally observable behavior | yes | Repository knowledge prose only |
| No new interface or data format | yes | No product or template edit in scope |
| No new dependency | yes | Markdown-only change |
| Existing requirement covers the behavior | yes | `REQ-FUNC-b8f0efc5`; `REQ-FUNC-500cfb8b` preserves the existing diagram contract |
| No security or data-handling change | yes | No runtime behavior changes |

## Log

- 2026-09-04 frame: scoped one documentation-only component-page prototype and three read-only prompt trials; excluded templates, tooling, other pages, product behavior, commits, and publication.
- 2026-09-04 frame: selected the quick path because the change introduces no externally observable behavior, interface, format, dependency, security, or data-handling effect and remains within existing component-knowledge requirements.
- 2026-09-04 frame: the checkout was clean on master, so work moved to branch `ddp/improve-component-knowledge-page` before the journal was created.
- 2026-09-04 frame: the user accepted the proposed one-page prototype, three prompt trials, explicit exclusions, and no-commit constraint.
- 2026-09-04 build: documentation-only work changes no requirement behavior, so no red test is applicable; re-read `REQ-FUNC-b8f0efc5` and `REQ-FUNC-500cfb8b` to preserve durable component context and the current architecture contract.
- 2026-09-04 build: recorded anchor `5c6936dea89900f3` immediately before editing the component page.
- 2026-09-04 build: improved the page with feature-language routing, explicit ownership boundaries, seven safety invariants, a seven-row change map, a smaller current-state architecture diagram, and searchable implementation/test seams.
- 2026-09-04 build inspection: the 989-word prototype is 178 words larger than the original, every named symbol and exact test selector resolves, and the diagram now carries 16 nodes instead of 24.
- 2026-09-04 build trial trace-format: prompt `Add JSON output to trace` routed to this component, `cmd_trace` plus `trace_rows` and the renderers, the `test_trace_*` group, row-retention and portable-format invariants, `REQ-FUNC-d3905502`, and the Reusable workflow payload boundary for the public CLI contract.
- 2026-09-04 build trial coverage: prompt `Change the coverage precedence used by the diagram` routed to `coverage_class`, diagram symbols, `test_every_coverage_class_matches_what_check_reports`, the shared-verdict invariant, `REQ-FUNC-6b4ff1ad`, and the effect on `check`, `trace`, and `explain`.
- 2026-09-04 build trial evidence: prompt `Include ignored files in anchor and evolution evidence` routed to `repository_manifest`, `cmd_anchor`, `cmd_evolution`, the two named evolution tests, `REQ-DATA-4304dec0` and `REQ-DATA-7faf94ff`, while the Git-visible-state invariant exposed that the request changes the current contract rather than being a local edit.
- 2026-09-04 build manual observation: targeted source and test searches confirmed all three page-only routing results without a repository-wide source read; the page correctly directs the next step to exact implementation evidence rather than replacing it.
- 2026-09-04 build deviation: evolution reported 180 unchanged files and no changes because candidate fingerprints exclude all `.agentic/` state, including component knowledge; the page diff was reviewed directly with Git plus path, symbol, selector, and word-count checks.
- 2026-09-04 build deviation: advisory check returned 15 warnings and 3 notes; the task-local `scope-drift` warning is accepted because adding this repository-specific page to reusable product requirement paths would be false, while the other 14 warnings and 3 manual-verification notes belong to existing repository records.
- 2026-09-04 build: no impacted test was run and no requirement paths, links, status, or prose changed because this prototype changes documentation context only and introduces no product behavior.
- 2026-09-04 validate review round 1: specification compliance and implementation quality both returned `changes_required` against candidate `95ac50ddb93be57e6f11b3601590a1093b1d9ae822297038467e9dc9774d3046` and page hash `7968F6A315D26D8FC9830876CEBDE2E923CAC4E7DBDF0557623EE5277A9D01D1`.
- 2026-09-04 validate review finding: qualify the no-network claim because explicit configured child commands are not sandboxed and retain their own possible network side effects.
- 2026-09-04 validate review finding: correct the architecture prose and edges so shared parsing is not described as a single parse, `cmd_test` does not appear to scan the register or classify coverage, and `collect_diff` is not shown as report-only.
- 2026-09-04 validate review evidence correction: the reviewed diagram declared 14 nodes rather than the recorded 16, and one evolution selector used contextual `::` shorthand rather than a standalone exact selector; both records will be corrected with the page.
- 2026-09-04 build review fix: qualified direct AEGIS network behavior from unsandboxed configured-child side effects, replaced the shorthand evolution selector with its full standalone selector, and removed the single-parse claim.
- 2026-09-04 build review fix: split `cmd_check` from `cmd_test`, made `collect_diff` a shared node reached by checking, impacted-test selection, and reporting, and retained focused edges for register views and evidence.
- 2026-09-04 build evidence correction: the revised page is 1,037 words with 17 Mermaid node declarations, candidate `3a9bcf44500fe968973a1246d0e75add2b682fdb5e93b017582970c2fcebd4c0`, and page hash `9F573E98A7081F0B10D41CCE4B5DA90521A45C1B469B11D0BF2D30FE2A507DE4`.
- 2026-09-04 build: all round-one findings were corrected without changing the accepted scope, three trial routes remain intact, `git diff --check` is clean, and the repeated advisory check retains the same accepted task-local and pre-existing warnings.
- 2026-09-04 validate review round 2: specification compliance approved candidate `3a9bcf44500fe968973a1246d0e75add2b682fdb5e93b017582970c2fcebd4c0` and page hash `9F573E98A7081F0B10D41CCE4B5DA90521A45C1B469B11D0BF2D30FE2A507DE4` with no remaining findings.
- 2026-09-04 validate review round 2: implementation quality independently approved the same candidate and page hash with no remaining correctness, routing, portability, security, Mermaid, maintenance, context-cost, or scope findings.
- 2026-09-04 validate final proof: job `d99029ea-cbf5-4091-9669-2d6328875d3b` ran `check --task TASK-d9b347f2 --strict --run --json`, exit 0, with 390 tests passed, 2 skipped, lint passed, strict passed, and candidate unchanged.
- 2026-09-04 validate deviation: final proof retained 15 advisory warnings and 3 notes; the task-local warning is the accepted knowledge-only traceability limitation, while the remainder belong to pre-existing open tasks and manual-verification records outside scope.
- 2026-09-04 deliver: the user superseded the no-commit limit and approved one local commit on `ddp/improve-component-knowledge-page`; push, PR, and publication remain unauthorized and out of scope.
- 2026-09-04 deliver: candidate `3a9bcf44500fe968973a1246d0e75add2b682fdb5e93b017582970c2fcebd4c0` and page hash `9F573E98A7081F0B10D41CCE4B5DA90521A45C1B469B11D0BF2D30FE2A507DE4` remain unchanged from final proof and approved reviews.
- 2026-09-04 deliver: the first report snapshot said no deviations were recorded because earlier log summaries did not use the exact uppercase marker shape, so the journal-only evidence is corrected below before a fresh report.
- 2026-09-04 DEVIATION build: evolution could not see the component-page edit because AEGIS excludes `.agentic/` state from that evidence, so direct Git diff, hash, symbol, selector, and word-count inspection supplied the missing view.
- 2026-09-04 DEVIATION build: the task-local scope-drift warning is accepted because linking this repository-specific knowledge page as a reusable product requirement path would be false; other advisory findings are pre-existing.
- 2026-09-04 DEVIATION validate: final strict validation passed with accepted advisory warnings and notes from the knowledge-only traceability limitation, pre-existing open tasks, and manual-verification records.
- 2026-09-04 deliver: the refreshed report records all three deviations, approved round-two reviews, 16 report-time advisory warnings, 3 notes, and the four task files in the local delivery scope.
- 2026-09-04 deliver close-out: the authorized local commit is the complete outcome, so `stage: done`, the report, and this close-out are prepared to be carried atomically in that single commit without push or PR.
- 2026-09-04 deliver close-out: the local commit succeeded and this journal-only final-status correction is folded into that same unpushed branch commit; the validated component candidate remains unchanged.

## Rulings

<!-- Append decisions here; never edit history. Supersede with a new ruling.
- RULING-001 | date=YYYY-MM-DD | decision=<decision> | reason=<reason> | source=user | supersedes=none
source: user | repository | requirement | technical
-->

- RULING-001 | date=2026-09-04 | decision=Do not create a commit or publish this task | reason=The user explicitly prohibited commits | source=user | supersedes=none
- RULING-002 | date=2026-09-04 | decision=Create one local commit on `ddp/improve-component-knowledge-page` without push, PR, or publication | reason=The user explicitly authorized a commit on this separate branch | source=user | supersedes=RULING-001

## Handoff

<!-- Replace these fields with the latest minimal resume snapshot.
status: ready | waiting | blocked
-->

current: done
status: ready
next: none - local commit is the complete authorized outcome
must_read: .agentic/tasks/TASK-d9b347f2.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: validated component-page prototype, task evidence, delivery reports, and close-out committed locally on the task branch
evidence: unchanged approved candidate; 390 tests passed with 2 skipped; lint and strict check passed; refreshed report records three deviations; local commit succeeded
issues: 16 report-time advisory warnings and 3 notes remain; Mermaid was structurally inspected but not rendered; no push or PR performed
next: none - the authorized local commit is the complete outcome
needs_user: no - explicit local-commit authority is sufficient and outward publication remains excluded
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-09-04)

- stage: deliver; type: change; path: quick; branch: ddp/improve-component-knowledge-page
- requirements:
  - REQ-FUNC-b8f0efc5 - Provide durable workflow artifact templates
  - REQ-FUNC-500cfb8b - Keep a current component architecture diagram in its knowledge page
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 6f821f7: 4 file(s) changed, 1285 line(s) added
- checks: errors=0 warnings=16 notes=3
- checklist: 3/6 done; open: journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it

## Delivery report (2026-09-04)

- stage: deliver; type: change; path: quick; branch: ddp/improve-component-knowledge-page
- requirements:
  - REQ-FUNC-b8f0efc5 - Provide durable workflow artifact templates
  - REQ-FUNC-500cfb8b - Keep a current component architecture diagram in its knowledge page
- deviations: 3 recorded
  - build: evolution could not see the component-page edit because AEGIS excludes `.agentic/` state from that evidence, so direct Git diff, hash, symbol, selector, and word-count inspection supplied the missing view.
  - build: the task-local scope-drift warning is accepted because linking this repository-specific knowledge page as a reusable product requirement path would be false; other advisory findings are pre-existing.
  - validate: final strict validation passed with accepted advisory warnings and notes from the knowledge-only traceability limitation, pre-existing open tasks, and manual-verification records.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 6f821f7: 4 file(s) changed, 1301 line(s) added
- checks: errors=0 warnings=16 notes=3
- checklist: 3/6 done; open: journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
