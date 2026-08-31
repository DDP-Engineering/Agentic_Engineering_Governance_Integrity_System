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

Stage report is one replaceable latest snapshot, not an evidence store.
Use plain one-line fields with no fences or bullets inside that section.
stage is the reported stage; current must match the journal header after any
transition. result is in_progress | completed | paused | blocked | skipped.
Keep all observations and decisions in the append-only Log as well.
Leave unknown fields blank; summary prints not recorded, never an assumed pass.
Refresh after work or decisions even if current has not changed.
-->

# TASK-ffda5ca3 — Add coordinated lightweight workflow enhancements

stage: deliver
type: feature
path: full
requirements: REQ-FUNC-3bc8597c, REQ-FUNC-e55c43d1, REQ-FUNC-9514e017, REQ-FUNC-cbff6478, REQ-FUNC-7ea14fe4, REQ-FUNC-938600f4, REQ-FUNC-1844e18d, REQ-FUNC-d37ad85a, REQ-FUNC-d60b322b, REQ-FUNC-b8f0efc5, REQ-UX-84868466, REQ-UX-94a33d75, REQ-PLAT-e675406e
branch: master
base: 2fae0e9ad6435fa06fc3adb8e5d407286c1c0a28
opened: 2026-08-31

## Done checklist (current stage)

- [ ] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Log

- 2026-08-31 deliver: user requested synchronization of the six affected 06_SoftwareDocu PPTX companions and confirmed LibreOffice is available; candidate changes therefore return the task to validate without expanding Git authority.
- 2026-08-31 frame: scope is the coordinated implementation of optional one-level child tasks, deterministic bounded `brief`, optional independent review verdicts, a bounded fix/re-review loop, and durable rulings and handoffs under one compatible journal contract.
- 2026-08-31 frame: full path chosen because the work adds public CLI behavior, journal formats, configuration, validation rules, and workflow contracts.
- 2026-08-31 frame: the approved coordinated plan is the design contract, and the user explicitly approved proceeding through specify, design, build, and validate without another ordinary frame stop.
- 2026-08-31 frame: expected new requirements independently cover child relationships, bounded briefs, independent verdicts, bounded re-review, and durable rulings/handoffs; affected existing requirements will be updated rather than duplicated.
- 2026-08-31 frame: anticipated changes are limited to the product payload, copied-payload tests, repository requirements/specifications/knowledge, product documentation, and the root Unreleased changelog named by the plan.
- 2026-08-31 frame: exclusions are nested children, automatic dispatch or Git operations, model invocation, network access, services, databases, daemons, hidden runtime state, new stages, status JSON breakage, root payload deployment, versioning, packaging, release, and publication.
- 2026-08-31 frame: Git authority is limited to leaving implementation changes unstaged and uncommitted on the existing `master`; branch, worktree, stage, unstage, commit, push, pull request, merge, rebase, reset, stash, restore, clean, release, package, and deploy actions are prohibited.
- 2026-08-31 frame: protected pre-existing state comprises the three staged deletions under `07_Delivery/aegis-0.7.2/` and both untracked planning documents under `00_Planning/New Features/`; none may be modified by this task.
- 2026-08-31 frame: DEVIATION frame - remain on `master` instead of creating a task branch because the user explicitly authorized implementation there and prohibited branches and worktrees.
- 2026-08-31 frame: the installed root AEGIS 0.8.0 payload governs this task but must not be edited or extended with unsupported fields; new payload behavior will be exercised only through copied payloads and temporary workspaces.
- 2026-08-31 frame: validation will use failing tests first, focused feature suites, the full temporary-workspace matrix, compilation, CLI help, Ruff, the complete product suite, diff review, and the installed task-scoped strict check.
- 2026-08-31 frame: no existing open journal owns this exact five-feature implementation; TASK-783dc269 is a completed paused predecessor for compact stage reporting and TASK-d2351998 is unrelated.
- 2026-08-31 frame: frame checklist completed and the approved full-path task advanced to specify.
- 2026-08-31 specify: generated five functional requirements with CLI-assigned IDs for child tasks, deterministic briefs, independent verdicts, bounded re-review, and durable rulings/handoffs; each has an exact behavior spec and concrete copied-payload verification map.
- 2026-08-31 specify: updated eight affected existing requirements for compatible task scaffolding, extended stage summaries, review-aware delivery reporting, unchanged six-stage governance, richer durable templates, bound review reporting, brief-first resume, and offline payload constraints.
- 2026-08-31 specify: no new behavior is assigned to the installed root payload, and the governing task journal remains on the supported AEGIS 0.8.0 stage-report schema.
- 2026-08-31 specify: task-scoped check exited 0 with no errors after removing two nonexistent generated-config paths; six accepted warnings cover two unrelated held-delivery journals and four protected/out-of-layout planning or delivery paths, with four existing notes.
- 2026-08-31 specify: DEVIATION specify - accept six advisory warnings because the two journals and four planning/delivery paths are unrelated or explicitly protected and must not be reconciled by this implementation.
- 2026-08-31 specify: all specification checklist items completed and the task advanced to design.
- 2026-08-31 test: test --impacted (5 test ref(s)) exit 0 (158.1s)

## Design

- Keep the single standard-library CLI and plain Markdown/TOML state; add focused parsers and projections rather than another runtime component (REQ-FUNC-e55c43d1, REQ-PLAT-e675406e).
- Extend new journal scaffolds compatibly with blank `parent`, ordered Rulings, replaceable Handoff, and three review fields while accepting legacy journals that omit them (REQ-FUNC-3bc8597c, REQ-FUNC-7ea14fe4, REQ-FUNC-9514e017, REQ-FUNC-b8f0efc5).
- Parse live sections only, bound diagnostics, bind stage report and handoff to the header stage, and never derive approval from missing or stale data (REQ-FUNC-1844e18d, REQ-FUNC-7ea14fe4, REQ-FUNC-9514e017).
- Add `task --parent` as a child-side-only link and compute sorted visible children by scanning the current checkout; parent validation integrates visible completed work (REQ-FUNC-3bc8597c, REQ-FUNC-938600f4).
- Add `brief` as a pure fixed-order renderer with 240-character scalars, eight active rulings, twenty sorted children, and explicit omission markers (REQ-FUNC-e55c43d1, REQ-UX-94a33d75).
- Add default-off `[review]` settings through generated config text, strict Boolean/integer parsing, and bound review projections in summary, brief, report, and advisory checks (REQ-FUNC-9514e017, REQ-FUNC-d37ad85a, REQ-UX-84868466).
- Keep the fix loop in agent guidance; checks validate durable round/verdict consistency but the CLI never invokes a reviewer or changes a candidate (REQ-FUNC-cbff6478, REQ-FUNC-d60b322b).
- Any candidate change clears both verdicts; enabled delivery requires two current approvals, while disabled review preserves all existing validation and checkpoint rules (REQ-FUNC-9514e017, REQ-FUNC-cbff6478).
- Rulings are append-only and supersedable; handoff is replaceable and refreshed at transitions, pauses, blockers, and session end, with neither able to expand authority (REQ-FUNC-7ea14fe4).
- Test seams are copied-payload CLI creation/parsing, exact-output brief/report, advisory checks, and structural guidance tests for each new requirement.
- Documentation seams are payload AGENTS/CLI/stages, package README, three knowledge pages, seven human guides, and two concise Unreleased bullets.
- Rejected a database, service, orchestration framework, hidden state, model call, or automatic Git workflow because durable files plus deterministic readers satisfy the contracts offline.
- The installed root AEGIS remains untouched; temporary copied payloads are the dogfood boundary until a separately authorized versioned deployment.
- 2026-08-31 design: the approved plan and five requirement specs define one decision-free implementation path with copied-payload parser, CLI, report, check, and structural test seams.
- 2026-08-31 design: intended architecture diagrams were updated for core CLI lifecycle, reusable workflow payload, and validation/report projection, each marked as intended until validation.
- 2026-08-31 design: task-scoped check exited 0 with no errors and the unchanged six accepted warnings plus four existing notes.
- 2026-08-31 design: DEVIATION design - accept the unchanged two held-delivery and four protected/out-of-layout warnings without modifying their unrelated files.
- 2026-08-31 design: all design checklist items completed and the task advanced to build.
- 2026-08-31 build: DEVIATION build - planned `uv run --group dev python -m pytest ...` exited 1 before collection because this folder has no uv project and uv selected Python 3.13 without pytest; use the working repository Python 3.12 runtime and preserve the failed command as evidence.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_cli_core.py tests\test_run_report.py -k "journal or ruling or handoff or summary or stage_report" --tb=short`; exit=1; expected missing behavior=26 failures show absent parent/ruling/handoff parsers, absent review fields and stage binding, with 27 passed and 1 skipped.
- 2026-08-31 build: repository anchor recorded after the first expected red at commit 2fae0e9, covering 73 Git-visible files before product implementation.
- 2026-08-31 build: compatible journal parsing, template scaffolds, focused ruling/handoff parsers, and shared stage binding implemented; focused regression exited 0 with 53 passed, 1 skipped, and 117 deselected.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_cli_core.py tests\test_check.py -k "parent or child" --tb=short`; exit=1; expected missing behavior=7 failures show absent `--parent`, visible-child discovery, and relationship findings, with 4 passed and 115 deselected.
- 2026-08-31 build: optional one-level child creation, child-side-only links, sorted visible-child discovery, and relationship checks implemented; focused regression exited 0 with 11 passed and 115 deselected.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_structure.py tests\test_check.py -k "ruling or handoff or resume" --tb=short`; exit=1; expected missing behavior=8 failures show absent workflow guidance and advisory validation for rulings/handoffs, with 1 passed and 94 deselected.
- 2026-08-31 build: append-only ruling and replaceable handoff guidance plus malformed, supersession, freshness, and status checks implemented; focused regression exited 0 with 9 passed and 94 deselected.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_run_report.py -k "brief" --tb=short`; exit=1; expected missing behavior=8 failures all show the absent public `brief` command and renderer.
- 2026-08-31 build: deterministic fixed-order `brief` implemented with bounded scalars, rulings, children, legacy/stale markers, and no Git/subprocess calls; focused regression exited 0 with 8 passed and 120 deselected.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_cli_core.py tests\test_check.py tests\test_run_report.py -k "review or verdict or summary or brief or report or config or init" --tb=short`; exit=1; expected missing behavior=17 failures show absent review defaults/settings, summary/report/brief policy projections, and config warnings, with 148 passed, 1 skipped, and 110 deselected.
- 2026-08-31 build: default-off exact review configuration, fail-safe settings, independent summary fields, policy-aware brief and delivery report projections, and invalid-config warnings implemented; focused config/init regression passed 25 cases and focused summary/brief/report regression passed 136 with 1 skipped.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_structure.py tests\test_check.py -k "review or verdict or review_round" --tb=short`; exit=1; expected missing behavior=7 failures show absent bounded-loop guidance and review-state findings, with 5 passed and 107 deselected.
- 2026-08-31 build: finite explicit-review state machine, candidate invalidation, disabled-review boundary, enabled-delivery guard, and review-state checks implemented; focused regression exited 0 with 12 passed and 107 deselected.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_structure.py -k "child or brief or review or ruling or handoff or six_stage" --tb=short`; exit=1; expected missing behavior=3 failures show absent integrated child guidance and explicit unchanged-checkpoint statement, with 10 passed and 31 deselected.
- 2026-08-31 build: DEVIATION build - a read-only inspection command exited 1 because constrained PowerShell rejected `[Math]::Min`; no repository state changed, and compatible `Select-Object` selection replaced it.
- 2026-08-31 build: DEVIATION build - the first integrated-guidance patch was rejected atomically because its context included a malformed legacy arrow glyph; no partial edit occurred, and stable surrounding text was used instead.
- 2026-08-31 build: integrated structural rerun remained red with 1 failure and 12 passes because the opt-in/one-level contract used a hyphenated spelling that the exact contract test did not recognize; wording was normalized without changing behavior.
- 2026-08-31 build: integrated structural slice exited 0 with 13 passed and 31 deselected after parent integration and unchanged-checkpoint guidance was completed.
- 2026-08-31 build: full structural suite remained red with 1 failure and 43 passes because the survival digest capitalized an exact lowercase contract phrase; wording was normalized without changing behavior.
- 2026-08-31 build: structural rerun remained red with 1 failure and 43 passes because Markdown wrapping split the exact `bounded fix` survival phrase across lines; the phrase was kept intact without changing behavior.
- 2026-08-31 build: structural rerun remained red with 1 failure and 43 passes because equivalent authority wording omitted the exact `cannot grant authority` survival phrase; the compact digest was made literal.
- 2026-08-31 build: full structural suite exited 0 with 44 passed after the survival digest was made exact and compact.
- 2026-08-31 build: DEVIATION build - an initial traceability read used `.md` rather than the repository's `.toml` requirement extension and exited non-zero; generated paths were resolved before edits.
- 2026-08-31 build: DEVIATION build - one read-only requirement audit exited on PowerShell regex quoting and was rerun with literal quoting; no files changed from the failed command.
- 2026-08-31 build: DEVIATION build - a Windows-incompatible wildcard made one read-only guidance audit return an operand error; the directory audit was rerun with a Markdown glob.
- 2026-08-31 build: DEVIATION build - one README patch and one combined documentation patch were rejected atomically on byte-level context mismatches; neither partially applied, and both were split at stable headings.
- 2026-08-31 build: DEVIATION build - the required host-adapter audit returned `rg` exit 1 because no `.codex`, `.claude`, `.pi`, or `.opencode` payload adapters exist; none were invented.
- 2026-08-31 build: DEVIATION build - the package has no `pyproject.toml` or `uv.lock`, so `uv --group dev` reports that the group has no effect; required uv commands were run with the working Python 3.12 interpreter explicitly selected.
- 2026-08-31 build: traceability completed for five active new requirements and eight affected active requirements, with exact copied-payload tests and final affected paths linked.
- 2026-08-31 build: requirements, three knowledge components, payload/package CLI documentation, seven human guides, and two concise Unreleased additions now describe one compatible contract; repository review dogfooding was intentionally not enabled because the installed root payload cannot support the new fields and deployment is excluded.
- 2026-08-31 build: focused uv feature suites exited 0 with 24 passed/38 deselected, 136 passed/1 skipped, 15 passed/66 deselected, and 13 passed/31 deselected; Ruff exited 0 with all checks passed.
- 2026-08-31 build: configured impacted selection reduced 127 selectors to five affected test files and exited 0 with 332 passed and 2 skipped in 157.07 seconds.
- 2026-08-31 build: inspection verification confirmed the unchanged six-stage order and two checkpoints, one-level child integration, brief-first resume, durable Rulings/Handoff, and bounded explicit-review guidance across AGENTS and all seven step files.
- 2026-08-31 build: evolution matched the designed product candidate exactly at 24 modified non-agentic files, with no added or removed product paths; agentic requirements/specs/task evidence are intentionally excluded by the anchor format.
- 2026-08-31 build: task check exited 0 with no errors, six unchanged accepted warnings for two held-delivery journals and four protected/out-of-layout paths, and three unrelated manual-verification notes.
- 2026-08-31 build: DEVIATION build - accept those six advisory warnings because the two journals and four planning/delivery paths are unrelated or explicitly protected and must remain untouched.
- 2026-08-31 build: all build checklist items completed and the task advanced to validate.
- 2026-08-31 validate: DEVIATION validate - a read-only cross-file contract audit used a Windows-incompatible wildcard and exited 1 after reading direct files; the audit was rerun with a directory Markdown glob and changed no state.
- 2026-08-31 validate: semantic documentation review found and corrected invalid example ruling sources, an invalid `paused` handoff status, missing `brief` exit/help references, and a task template that referred to but did not show its exact ruling/status formats.
- 2026-08-31 validate: semantic implementation review found three task-owned issues: forward/unknown supersession could hide a later valid ruling, ruling parser diagnostics were not explicitly bounded, and enabled review produced premature findings before validate or against legacy done journals; returned to build for focused test-first fixes.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_cli_core.py tests\test_check.py -k "forward_supersession or bounds_malformed_record_diagnostics or outside_validation" --tb=short`; exit=1; expected missing behavior=5 failures prove forward supersession hid a later record, no diagnostic bound existed, and frame/build/done journals received premature review warnings.
- 2026-08-31 build: first fix rerun had 4 passes and 1 test-layout failure because an existing single-error bound assertion was accidentally placed in the new multi-error test; the assertion was restored to its original case before evaluating the implementation.
- 2026-08-31 build: focused validation-review fixes exited 0 with 5 passed and 143 deselected after ordered supersession, a 20-line diagnostic cap, and validate/deliver-only review-state checks were implemented.
- 2026-08-31 build red: command=`python -m pytest -q tests\test_check.py -k "enabled_review_uses_disabled" --tb=short`; exit=1; expected missing behavior=enabled review accepted disabled verdict markers as complete validation evidence.
- 2026-08-31 build: enabled-review disabled-marker regression exited 0 with 1 passed and 84 deselected after validation-state verdict checks were tightened.
- 2026-08-31 build: focused post-review uv suites exited 0 with 24 passed/40 deselected, 136 passed/1 skipped, 19 passed/66 deselected, and 13 passed/31 deselected.
- 2026-08-31 validate: static proof exited 0 for py_compile, CLI help, and Ruff; help exposes `brief`, and Ruff reported all checks passed.
- 2026-08-31 validate: complete product suite exited 0 with 342 passed and 2 skipped in 142.78 seconds; the skips are existing platform-conditional tests, not failures.
- 2026-08-31 validate: the 14-scenario temporary-workspace matrix is covered by copied-payload CLI, brief/report, check, and structure tests for legacy state, ordinary and child tasks, child bounds/errors, deterministic output, ruling bounds/chains, malformed/stale records, disabled/approved/independent-failure review, bounded re-review/exhaustion, invalid config types, and integrated parent validation.
- 2026-08-31 validate: built code matches the intended diagrams for core lifecycle, reusable payload, and validation/report projections, so all three temporary intended-architecture markers were removed.
- 2026-08-31 build: validation-return fixes and their linked tests are green; the task advanced back to validate for final candidate proof.
- 2026-08-31 validate: final evolution refreshed to the expected 24 modified product/document files with no product additions or removals, and `git diff --check` exited 0.
- 2026-08-31 validate: installed task-scoped `check --strict --run` exited 0; configured test completed successfully in 144.2 seconds, configured lint completed successfully, errors=0, warnings=6, notes=3, and strict result=ok.
- 2026-08-31 validate: DEVIATION validate - two existing symlink tests were platform-skipped on Windows because POSIX semantics or symlink creation are unavailable; all 342 runnable tests passed and no task-owned check was skipped.
- 2026-08-31 validate: DEVIATION validate - accept the six unchanged strict warnings because two held-delivery journals are unrelated and four planning/delivery paths are explicitly protected; none may be reconciled in this task.
- 2026-08-31 validate review round 2: spec_compliance=approved after confirming all five new and eight affected requirements, approved exclusions, compatibility, docs, scenario matrix, and unchanged six-stage/checkpoint contract.
- 2026-08-31 validate review round 2: implementation_quality=approved after fixing the four review findings, rerunning focused/static/full proof, reviewing error and stale-state paths, and confirming no unsupported root payload or Git operation occurred.
- 2026-08-31 validate: root installed `.agentic/aegis.py` has no diff; no active Ruling or Handoff was added because the installed 0.8.0 task schema does not support the new product records, and the final presentation will state that limitation rather than dogfood unsupported fields.
- 2026-08-31 validate: all validate checklist items completed and the task advanced to deliver for the mandatory no-commit checkpoint.
- 2026-08-31 validate: synchronized the six affected 06_SoftwareDocu PPTX companions by preserving every source slide and appending one template-frame addendum that summarizes each corresponding Markdown enhancement; original theme parts matched byte-for-byte after export.
- 2026-08-31 validate: rendered and visually reviewed every slide through six final contact sheets, inspected all six addendum slides individually, and verified the final deck text through artifact-tool inspection.
- 2026-08-31 validate: DEVIATION validate - `slides_test.py` reports the established off-canvas decorative circles on title/outro slides; the same slides fail in all six source decks before editing, and the duplicated addenda preserve rather than alter that template geometry.
- 2026-08-31 validate: final evolution recorded 30 modified candidate files, including the six Markdown/PPTX guide pairs; final strict check exited 0 with configured test 107.6s, lint 0.2s, errors=0, warnings=6, notes=3, strict=ok.
- 2026-08-31 validate: six accepted strict warnings remain two unrelated held-delivery journals and four explicitly protected planning/delivery paths; all current warnings are outside this task's permitted scope.
- 2026-08-31 validate: all validate checklist items completed after the requested presentation synchronization and the task advanced to deliver for the mandatory no-commit checkpoint.

## Stage report

stage: validate
result: completed
current: deliver
changed: final compatible product candidate, traceability, knowledge, Markdown guides, and six matching PPTX companions reviewed with all review-return findings resolved
evidence: six PPTX addenda visually rendered and theme-preserved; 30-file evolution; strict check exit 0 with test 107.6s, lint 0.2s, errors=0
issues: six accepted unrelated or protected warnings; root payload cannot dogfood unsupported fields before deployment
next: present the exact delivery checkpoint and wait; do not stage, commit, publish, package, release, or deploy
needs_user: yes; delivery requires the existing human checkpoint
