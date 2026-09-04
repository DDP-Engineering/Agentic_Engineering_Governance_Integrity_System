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

# TASK-e171dae0 — Promote component knowledge routing contract

stage: done
type: change
path: full
requirements: REQ-FUNC-9db20045, REQ-FUNC-32fe33a0, REQ-FUNC-500cfb8b, REQ-FUNC-b8f0efc5
parent:
branch: ddp/promote-component-knowledge-contract
base: 07453e5d1f9f2e9b489c73d8c2de9f402eb9947b
opened: 2026-09-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Log

- 2026-09-04 frame: Scope is to promote the validated routing-oriented component-page structure into the canonical template and workflow instructions, synchronize user-facing adoption documentation, and apply it to the core CLI lifecycle and agent integrations pages as two additional trials.
- 2026-09-04 frame: Excluded are a central component index, machine-readable metadata, automated freshness enforcement, CLI/runtime behavior changes, release/version work, and bulk conversion of every existing component page.
- 2026-09-04 frame: The full path is required because this changes an agent-facing workflow contract, introduces a focused functional requirement, and needs synchronized tests and documentation.
- 2026-09-04 frame: No child tasks are planned because the template, stage guidance, tests, documentation, and representative page trials form one tightly coupled contract change.
- 2026-09-04 frame: Proposed requirement creation is a functional contract requiring component knowledge pages to route implementation work with concise selection signals, boundaries, invariants, current architecture, owned files, and a conditional change map while preserving source-and-test verification.
- 2026-09-04 frame: Proposed requirement update is REQ-FUNC-32fe33a0 so adoption creates the enriched routing-oriented component page from observed source and test evidence.
- 2026-09-04 frame: REQ-FUNC-500cfb8b remains unchanged and will verify that the richer page contract still requires a current Mermaid architecture diagram.
- 2026-09-04 frame: The first summary attempt rejected `review_round: 0`; the not-yet-applicable field was cleared before retrying.
- 2026-09-04 frame: The user approved the proposed scope, exclusions, full path, and requirement strategy.
- 2026-09-04 specify: Created REQ-FUNC-9db20045 for the single implementation-routing behavior, revised REQ-FUNC-32fe33a0 so adoption produces routing-oriented evidence, and reused REQ-FUNC-500cfb8b and REQ-FUNC-b8f0efc5 unchanged for current architecture and durable template coverage.
- 2026-09-04 specify: No separate specification is needed because the requirement plus a short task design can define the section obligations, optional change-map rule, workflow consumption, and test seams without a file format or protocol.
- 2026-09-04 specify: `python .agentic/aegis.py check` reported zero errors, 22 unrelated pre-existing task-journal warnings, and three manual-verification notes.
- 2026-09-04 design: The decision record fixes the mandatory routing sections, conditional change-map rule, exact-source authority boundary, stage consumption, representative trials, documentation synchronization, and structural test seam.
- 2026-09-04 design: No component architecture diagram is owed because only the knowledge and workflow contract changes, not the internal structure of the components documented by the trial pages.
- 2026-09-04 design: `python .agentic/aegis.py check` again reported zero errors and the same 22 unrelated pre-existing warnings and three notes.
- 2026-09-04 build red: command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py::test_component_knowledge_routes_implementation_work`; exit=1; expected missing behavior=the canonical component template has no `## Routing` section and the workflow stages do not yet consume the routing contract.
- 2026-09-04 build: `python .agentic/aegis.py anchor --task TASK-e171dae0` recorded 180 Git-visible files at base `07453e5` before implementation.
- 2026-09-04 build: The canonical template now defines routing, boundaries, invariants, a conditional change map, current architecture, files, and an explicit exact-source-and-tests authority boundary, while frame, specify, design, validate, and adoption consume the contract.
- 2026-09-04 build: Core CLI routing trials sent summary changes to `parse_stage_report` and `cmd_summary`, initialization changes to `cmd_init`, and trace-export changes away to the Validation and evidence CLI page.
- 2026-09-04 build: Agent integration routing trials sent shared operation changes to `shared/operations.mjs` and `adapter.mjs`, Claude hook changes to `integrations/claude/`, and workflow-step changes away to the Reusable workflow payload.
- 2026-09-04 build: REQ-FUNC-32fe33a0 inspection read canonical `steps/adopt.md` and observed source-and-test evidence gathering, routing-oriented page sections, optional change maps, architecture capture, backlog handling, and outcome-dependent close-out instructions.
- 2026-09-04 build: Presentation finalization attempts exited 1 while correcting reference-font, template-coverage, source-font, and child-runtime policy configuration; no failed candidate replaced the tracked deck.
- 2026-09-04 build: Presentation revision two passed package integrity, layout, font, first-party import, eight-slide template coverage, and visual review with SHA-256 `7A1BF26C72DC22BFADC1B44C9C9D7E994366277CE4222342C3DF86E8A2BC8F78`.
- 2026-09-04 build: The deck validator retained four intentional source-template warnings for decorative circles extending beyond slides 1 and 8; there were zero findings.
- 2026-09-04 build green: command=`python .agentic/aegis.py test --impacted --base HEAD`; exit=0; result=80 passed in the requirement-selected set.
- 2026-09-04 build: After final wording corrections, `python .agentic/aegis.py test --impacted --base HEAD` again exited 0 with 80 passed.
- 2026-09-04 build: Evolution reported the expected 11 modified product files, with no additions or removals; repository-owned `.agentic` requirements, journal, evidence, and two trial pages are deliberately excluded from the Git-visible manifest.
- 2026-09-04 build: `python .agentic/aegis.py check` returned zero errors, 18 unrelated pre-existing task-journal warnings, and three manual-verification notes.
- 2026-09-04 validate: Round-one specification review required one correction because the Agent integrations invariant claimed every operation invokes the CLI although `read`, `candidate`, `diff`, and `job` use bounded file, Git, or cache paths directly.
- 2026-09-04 validate: The overbroad integration invariant was narrowed to the observed delegation and direct-read exceptions, invalidating both round-one verdicts before round-two review.
- 2026-09-04 validate: Round-two specification review approved the corrected candidate, while quality review required a compatibility fallback because existing component pages may predate `## Routing` and cannot be bulk-migrated within this task.
- 2026-09-04 validate: Both round-two verdicts were invalidated before adding a focused legacy-page fallback and re-entering build for the bounded review fix.
- 2026-09-04 build red: command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py::test_component_knowledge_routes_implementation_work`; exit=1; expected missing behavior=frame has no legacy-page fallback and validation does not require incremental migration of a touched legacy page.
- 2026-09-04 build green: command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py::test_component_knowledge_routes_implementation_work`; exit=0; result=1 passed after adding provisional legacy-page orientation and touched-page migration.
- 2026-09-04 build green: command=`python .agentic/aegis.py test --impacted --base HEAD`; exit=0; result=80 passed after the bounded review fix.
- 2026-09-04 build: `python .agentic/aegis.py check` returned zero errors, 19 warnings, and three notes; the one new warning is the intentionally synchronized artifact-format planning document outside configured layout globs.
- 2026-09-04 validate: Final round-three specification review approved the legacy fallback as bounded to touched pages and compliant with the routing, adoption, architecture, and no-bulk-migration contracts.
- 2026-09-04 validate: Final round-three quality review approved the corrected invariants, compatibility fallback, structural test, documentation consistency, and validated presentation candidate.
- 2026-09-04 validate: `python -m py_compile 05_Software/aegis/tests/test_structure.py`, canonical CLI `--help`, and `git diff --check` all passed; the latter emitted only line-ending normalization notices.
- 2026-09-04 validate: Final evolution refreshed to the expected 13 modified product files with no additions or removals in the Git-visible candidate manifest.
- 2026-09-04 validate: `python .agentic/aegis.py check --task TASK-e171dae0 --strict --run` exited 0 with the configured full test and lint commands passing, zero errors, 16 warnings, and three notes.
- 2026-09-04 validate: The one current-task warning was malformed journal verdict detail appended to otherwise approved values; after correcting those journal-only fields, `check --task TASK-e171dae0 --strict` exited 0 with zero errors, 15 warnings, and three notes.
- 2026-09-04 validate: Accepted final findings are the required planning-document synchronization outside configured layout globs, unrelated pre-existing task-journal warnings, and declared manual-verification notes; no candidate failure remains.
- 2026-09-04 deliver: The user approved closing and committing the validated candidate on the current branch, explicitly required no push, and requested that a new AEGIS workflow start afterward.
- 2026-09-04 DEVIATION frame: The first summary command exited non-zero because `review_round: 0` is invalid before review - the journal field was cleared and the summary then succeeded.
- 2026-09-04 DEVIATION build: The focused structural test exited 1 at both intended red checkpoints - each result demonstrated the named missing behavior before its implementation and was followed by passing focused and impacted tests.
- 2026-09-04 DEVIATION build: Presentation finalization attempts exited 1 while policy settings were corrected - failed candidates never replaced the tracked deck, and the final deck passed package, layout, font, import, fidelity, and visual validation with only four intentional decoration warnings.
- 2026-09-04 DEVIATION validate: One CLI help command exited non-zero because it used a path relative to the wrong directory - the canonical payload path was then used and passed.
- 2026-09-04 DEVIATION validate: Final checks retained the required planning-file outside-layout warning, unrelated pre-existing journal warnings, and declared manual-verification notes - the planning location is required by repository rules and the remaining records are outside this task or explicitly manual.
- 2026-09-04 DEVIATION validate: The first strict proof reported malformed current-task review evidence because explanatory text followed the approved verdict values - the journal-only fields were corrected to exact approved values and strict recheck passed.
- 2026-09-04 DEVIATION deliver: An empty patch with a misspelled repository path was rejected - no file changed and the corrected journal-only patch followed.
- 2026-09-04 deliver: Because the approved outcome is the repository-local commit itself with no push or PR, this close-out is carried by that same delivery commit and no post-commit outcome remains to fail.

## Design

- Components: change the canonical component template and its frame, specify, design, validate, and adoption consumers; update two repository knowledge pages only as representative trials.
- Interface: REQ-FUNC-9db20045 makes `Routing`, `Purpose and boundaries`, `Public interface`, `Invariants`, `Key behaviors`, `Architecture`, and `Files` the standard agent-facing page contract; `Change map` is included only when multiple independent edit-and-test seams make it useful.
- Authority boundary: REQ-FUNC-9db20045 keeps each page concise and navigational, and requires the agent to inspect the exact source and focused tests before changing behavior.
- Workflow consumption: REQ-FUNC-9db20045 routes frame by request signals and ownership, specify by behaviors and invariants, design by change seams and boundaries, and validate by reconciling every affected section.
- Adoption: REQ-FUNC-32fe33a0 derives the enriched page from observed source and tests one component at a time rather than inventing design intent.
- Architecture: REQ-FUNC-500cfb8b preserves the current-state Mermaid contract; no component implementation shape changes, so no proposed architecture edit is owed.
- Durable template: REQ-FUNC-b8f0efc5 remains satisfied by keeping the richer contract in the canonical component template rather than duplicating it in host adapters.
- Data and storage: no CLI, file-format, runtime state, migration, dependency, security boundary, or network behavior changes.
- Test seams: add one structural test in `05_Software/aegis/tests/test_structure.py` for REQ-FUNC-9db20045; retain the existing architecture tests for REQ-FUNC-500cfb8b and template tests for REQ-FUNC-b8f0efc5; complete REQ-FUNC-32fe33a0 by inspection.
- Documentation: synchronize the package README, artifact-format planning and software documentation, the adoption Markdown/PPTX pair, and `CHANGELOG.md`; route trials update `.agentic/knowledge/core-cli-lifecycle.md` and `.agentic/knowledge/agent_integrations.md`.
- Rejected alternative: a central index, metadata schema, or automated freshness checker is not required by these requirements and would add unvalidated maintenance behavior before the page contract is proven across more components.
- Risk control: concise prompts and an optional change map limit page growth, while two structurally different trials expose routing ambiguity before broader conversion.

## Rulings

<!-- Append decisions here; never edit history. Supersede with a new ruling.
- RULING-001 | date=YYYY-MM-DD | decision=<decision> | reason=<reason> | source=user | supersedes=none
source: user | repository | requirement | technical
-->

- RULING-001 | date=2026-09-04 | decision=approve the bounded component-knowledge contract promotion frame | reason=the user explicitly answered yes to the presented checkpoint | source=user | supersedes=none
- RULING-002 | date=2026-09-04 | decision=deliver the validated candidate as a repository-local commit without push or PR | reason=the user explicitly requested close, commit, do not push, and then start another AEGIS workflow | source=user | supersedes=none

## Handoff

<!-- Replace these fields with the latest minimal resume snapshot.
status: ready | waiting | blocked
-->

current: done
status: ready
next: create the approved repository-local delivery commit, then start the requested AEGIS workflow for the title-and-path component catalogue command
must_read: .agentic/steps/6_deliver.md; .agentic/tasks/TASK-e171dae0.md
blockers: none

## Stage report

stage: deliver
result: completed
current: done
changed: appended the delivery report and prepared commit-only close-out in the same approved repository-local delivery commit
evidence: validated candidate unchanged; user approved close and commit without push; report recorded 7 deviations, two approved verdicts at review round 3, and checks with zero errors
issues: accepted findings are one required planning file outside layout globs, unrelated pre-existing journal warnings, three declared manual-verification notes, and four intentional presentation decoration warnings with zero presentation findings
next: create the approved commit without pushing, then open the next requested AEGIS task
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-09-04)

- stage: deliver; type: change; path: full; branch: ddp/promote-component-knowledge-contract
- requirements:
  - REQ-FUNC-9db20045 - Route implementation work through component knowledge
  - REQ-FUNC-32fe33a0 - Guide component-by-component repository adoption
  - REQ-FUNC-500cfb8b - Keep a current component architecture diagram in its knowledge page
  - REQ-FUNC-b8f0efc5 - Provide durable workflow artifact templates
- deviations: none recorded
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 07453e5: 20 file(s) changed, 1693 line(s) added
- checks: errors=0 warnings=16 notes=3
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it

## Delivery report (2026-09-04)

- stage: deliver; type: change; path: full; branch: ddp/promote-component-knowledge-contract
- requirements:
  - REQ-FUNC-9db20045 - Route implementation work through component knowledge
  - REQ-FUNC-32fe33a0 - Guide component-by-component repository adoption
  - REQ-FUNC-500cfb8b - Keep a current component architecture diagram in its knowledge page
  - REQ-FUNC-b8f0efc5 - Provide durable workflow artifact templates
- deviations: 7 recorded
  - frame: The first summary command exited non-zero because `review_round: 0` is invalid before review - the journal field was cleared and the summary then succeeded.
  - build: The focused structural test exited 1 at both intended red checkpoints - each result demonstrated the named missing behavior before its implementation and was followed by passing focused and impacted tests.
  - build: Presentation finalization attempts exited 1 while policy settings were corrected - failed candidates never replaced the tracked deck, and the final deck passed package, layout, font, import, fidelity, and visual validation with only four intentional decoration warnings.
  - validate: One CLI help command exited non-zero because it used a path relative to the wrong directory - the canonical payload path was then used and passed.
  - validate: Final checks retained the required planning-file outside-layout warning, unrelated pre-existing journal warnings, and declared manual-verification notes - the planning location is required by repository rules and the remaining records are outside this task or explicitly manual.
  - validate: The first strict proof reported malformed current-task review evidence because explanatory text followed the approved verdict values - the journal-only fields were corrected to exact approved values and strict recheck passed.
  - deliver: An empty patch with a misspelled repository path was rejected - no file changed and the corrected journal-only patch followed.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 07453e5: 20 file(s) changed, 1714 line(s) added
- checks: errors=0 warnings=16 notes=3
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
