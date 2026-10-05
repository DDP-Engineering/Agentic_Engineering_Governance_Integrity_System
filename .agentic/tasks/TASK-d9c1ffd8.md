<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-d9c1ffd8 - Point agents to CodeGraph from the root pointer digest

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-eab16188
parent:
branch: ddp/codegraph-plugin-plan
base: 1aee86b4d4220e834f19ddedea42fa3f0a36e207
opened: 2026-10-04

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: An agent working in a repository with CodeGraph enabled does not know
the `know_graph` commands exist unless it opens `.agentic/AGENTS.md`. The root
pointer digest that hosts load automatically (`AGENTS.md`, `CLAUDE.md`,
`QWEN.md`) never mentions them, and an agent answering a question rather than
starting governed work does not open the full contract. (OBSERVED in the 2026-10-04 ADORE trial: AEGIS 0.14.0 and CodeGraph deployed to F:\2026_AgenticDeliveryOrchestratorRuntimeEngine (commit 450798e), two headless Claude Code runs on the same navigation question; transcripts in the session scratchpad, not committed:
without a hint the agent made 0 `know_graph` calls - 6 Grep, 12 Read; with a
one-line hint naming the "Code navigation" section it made 10.)
Desired outcome: the generated digest tells an agent, in one short line, that
the `know_graph` commands exist when CodeGraph is enabled and where their
contract is, so an agent with CodeGraph available reaches for it unprompted.
Actors: an AI agent whose host loads a root pointer file; a maintainer who
runs `init` to refresh pointer blocks; a local-model user whose context budget
the digest consumes.
Primary scenario: a maintainer enables `[codegraph]` and runs `init` -> the
refreshed pointer blocks carry the CodeGraph line -> an agent asked "who calls
X?" reads it from the auto-loaded `CLAUDE.md` -> runs `know_graph_check` and a
query before falling back to search.
Examples: the ADORE trial question (direct and second-level callers of
`derive_run_id`, raise and catch sites of `LockHeldError`).
Counterexamples: a repository without the plugin or with `enabled = false` -
the line must not lead an agent to run commands that answer `disabled`
repeatedly; the commands remain an aid, never a stage requirement (AGENTS.md
"Code navigation").
In scope: `POINTER_DIGEST` in `05_Software/aegis/template/.agentic/aegis.py`
(mirrored to `.agentic/aegis.py`); this repository's refreshed root pointer
blocks; a test in `05_Software/aegis/tests/test_structure.py`; the requirement
that covers the digest contract; docs that quote the digest; knowledge pages
(Reusable workflow payload owns the navigation instruction; CodeGraph plugin).
Out of scope: making the digest depend on configuration; host integration
packages and skills under `05_Software/aegis/integrations/` (no CodeGraph
mention there, OBSERVED by search); changing the `AGENTS.md` navigation rules.
Constraints: the digest is static text written by `init` (OBSERVED,
`write_pointer`); it is read on every session, including by local models with
a tight context budget, so the addition stays one short sentence (about 40
words); existing digest phrases asserted by
`test_pointer_digest_is_sufficient_for_offline_resume` stay.
Success signals: a fresh `init` writes the line into all three pointer files
(automated); repeating the ADORE organic trial after an upgrade shows the
agent using `know_graph` without a hint (manual, model-dependent).
Evidence: STATED - the request to open tasks for the trial findings. OBSERVED
- `POINTER_DIGEST` (aegis.py, about 400 words, no CodeGraph mention);
`.agentic/AGENTS.md` "Code navigation (optional)"; ADORE `claude.md` digest
without CodeGraph; trial counts above. INFERRED - Claude Code loaded ADORE's
`claude.md` as project instructions (case-insensitive file system); a static,
conditionally worded line costs less than configuration-dependent pointer text.
UNKNOWN - whether one line is enough for other hosts and smaller models.
Assumptions: hosts keep auto-loading the root pointer files.
Unknowns: the effect on non-Claude hosts (not measured).
Decision-blocking questions: none for this task (branch: see the shared
question).
Proposed behaviors: the digest gains one sentence: when `[codegraph] enabled =
true`, the `know_graph` commands answer where Python symbols are defined and
used - run `know_graph_check` first, read "Code navigation" in
`.agentic/AGENTS.md`, and read cited source before relying on an answer.
Path and reason: full - the generated pointer text is externally observable
and the covering requirement (REQ-PLAT-e675406e names the digest survival
contract, not navigation) needs an addition.

| criterion | yes | no | evidence |
|---|---|---|---|
| no new externally observable behavior | | no | generated pointer files change |
| no new interface or data format | yes | | text only |
| no new dependency | yes | | none |
| an existing requirement covers the behavior | | no | no requirement names navigation in the digest |
| no security- or data-handling change | yes | | none |

## Requirement coverage

Behavior inventory: init (actor) writes or refreshes the AEGIS block in AGENTS.md, CLAUDE.md
and QWEN.md (trigger) -> the block carries one conditional CodeGraph sentence (response);
positive: fresh init and refresh both carry it; boundary: CodeGraph disabled or absent - the
sentence is conditional and asks for no command; existing offline-resume phrases stay;
observable: the three pointer files.

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| agents learn CodeGraph exists from the auto-loaded digest | init writes one conditional know_graph sentence into each pointer block | REQ-UX-eab16188 | fresh init: sentence in all three files | sentence is conditional on `enabled = true`; offline-resume phrases retained | automated init test in test_cli_core.py; test_pointer_digest_is_sufficient_for_offline_resume | no design impact (single constant) |

## Design

Skipped: a single-constant change in `POINTER_DIGEST` (aegis.py, mirrored) with no new interface, data format or dependency (3_design.md Skip when). REQ-UX-eab16188: no design impact.

## Log

- 2026-10-04 frame: full path (generated pointer text changes, no covering requirement); scope awaiting the user.
- 2026-10-04 frame: scope accepted by the user as framed; worked first of the three follow-ups; interaction autopilot up to delivery (RULING-001); full path.
- 2026-10-04 specify: 1 requirement created (REQ-UX-eab16188), 0 revised, 0 reused, 0 retired; no spec needed - the requirement carries the whole contract.
- 2026-10-05 design: skipped - single constant, no interface, format or dependency change (see ## Design).
- 2026-10-05 build red: REQ-UX-eab16188; command=`python -m pytest -q tests/test_cli_core.py::test_init_pointers_name_the_knowledge_graph_commands` (in 05_Software/aegis); exit=1; expected missing behavior=the generated AEGIS block lacks the CodeGraph sentence (first missing phrase `[codegraph] enabled = true` in AGENTS.md).
- 2026-10-05 build green: REQ-UX-eab16188; command=`python .agentic/aegis.py test --impacted --base HEAD --no-fallback` (8 test files: core, structure, check, run report, evolution, dispatch, system programs, plugin cli); exit=0; 475 passed, 5 skipped.
- 2026-10-05 build: refreshing this repository's root pointers with `init` also brought in digest text from earlier releases that had never been refreshed here (Log, autopilot, Stage report and deviation paragraphs) - current shipped text, kept; init's new managed sidecar-ignore block in .gitignore reverted (repository policy, out of scope; this repository tracks its sidecars). evolution: 4 modified files as expected (template aegis.py, AGENTS.md, CLAUDE.md, QWEN.md; the test was edited before the anchor); check --task: errors=0, warnings are pre-existing (other journals, tracked sidecars, untracked 01_Documentation/LocalModelsTests.7z).
- 2026-10-05 validate: knowledge reconciled (reusable-workflow-payload.md Key behaviors gains REQ-UX-eab16188); project and environment context unaffected; explicit review round 1 requested from two independent reviewers (specification compliance, implementation quality); manual no-hint agent trial running against a scratch clone of ADORE.
- 2026-10-05 validate manual observation (frame success signal, not a requirement verification): method=headless Claude Code, same no-hint question as the 2026-10-04 ADORE trial, run in a scratch clone of ADORE (commit 450798e) with this candidate's aegis.py and refreshed pointers, read-only tools, $3 cap; observed=the agent read [codegraph] in aegis.toml, ran know_graph_check first, read Code navigation and CLI.md, then queried find/callers/refs/symbol (14 know_graph invocations; earlier no-hint run: 0); correct answer; 207 s, $1.56. Single model-dependent run. Also observed: a name passed to know_graph_callers was refused and five lookup rounds resolved from= IDs to names - the friction TASK-2bb6095f addresses.
- 2026-10-05 validate: correction to the previous observation - 8 tool calls ran know_graph commands (27 command occurrences including loops); 3 tool calls were refused by the host permission check (shell loops) and 1 failed (a name passed where an ID is required); the "14 invocations" figure was a transcript line count.
- 2026-10-05 validate review round 1: specification compliance - approved with minor findings: (S1) the pointer refresh carries earlier-release digest text - state it as a deviation; (S2) the test lives in test_cli_core.py, not test_structure.py as the Frame's In scope said; (S3) the clause 'answer where Python symbols are defined and used' was neither verified nor tested; (S4) affected_paths listed the mirror and generated pointer files, against the template-only convention; (S5) the evolution report predates the .gitignore revert; (S6) the CodeGraph knowledge page in scope was untouched.
- 2026-10-05 validate review round 1: implementation quality - approved with minor findings: (I1) the CHANGELOG bullet ran to three lines and misstated the condition; (I2) stale evolution report (= S5); (I3) only the fresh-init path was tested, not the refresh path. Mirror byte-identity confirmed with cmp.
- 2026-10-05 validate: round 1 minors fixed (candidate changed, both verdicts cleared): test now asserts the 'defined and used' clause and a new refresh test seeds stale blocks (S3, I3); requirement verification and linked_tests updated, affected_paths trimmed to the template aegis.py (S4); CHANGELOG reduced to two lines (I1); codegraph-plugin.md Key behaviors names REQ-UX-eab16188 (S6); the test's location is test_cli_core.py, where the init tests live - the Frame line naming test_structure.py is superseded by the coverage table (S2); evolution to be refreshed after the last edit (S5, I2).
- 2026-10-05 DEVIATION validate: the root pointer refresh also brings in digest paragraphs shipped in 0.11.0-0.13.0 that were never refreshed in this repository (journal Log, autopilot, Stage report, narrower deviation rule) - accepted as current shipped text; the commit is larger than the feature and changes the instructions agents follow here (S1).
- 2026-10-05 validate review round 2: specification compliance - approved (S1-S6 resolved; three linked tests pass); implementation quality - approved (I1-I3 resolved); one new optional minor accepted unfixed: KNOW_GRAPH_POINTER and pointer_block sit beside their tests instead of the file's CONSTANTS/HELPERS sections - moving them is layout only and would reset both verdicts. Both verdicts apply to the current candidate.
- 2026-10-05 validate final: command=`python .agentic/aegis.py check --task TASK-d9c1ffd8 --strict --run`; exit=0; ran test (`python -m pytest -q 05_Software/aegis/tests`, ok 175.8 s), lint (`python -m ruff check 05_Software/aegis`, ok), codegraph_test (`python -m pytest -q 05_Software/aegis/plugins/codegraph/tests`, ok 161.4 s); errors=0, warnings=17 - all pre-existing and outside this candidate: tracked sidecars (34), deliver/review-state warnings on eight older open journals, and the untracked 01_Documentation/LocalModelsTests.7z (not part of this candidate). Evolution refreshed after the last candidate edit (6 modified files).
- 2026-10-05 deliver: candidate unchanged since the final proof (journal-only edits); the user approved 'Commit only' - one local commit on ddp/codegraph-plugin-plan, no push or PR, close-out carried by the same commit; excluded: TASK-2bb6095f and TASK-8c12ef28 journals (their own deliveries), 01_Documentation/LocalModelsTests.7z.
- 2026-10-05 deliver: the delivery report's '2 recorded' deviations are one deviation counted twice - the Stage report issues field repeated its 'DEVIATION validate' text; that field is reworded. Its 18th warning is this journal's own open close-out item, ticked now; the diff count includes the untracked journals of TASK-2bb6095f and TASK-8c12ef28 and the .7z, none of which is committed.
- 2026-10-05 deliver: close-out - delivered as one local commit on ddp/codegraph-plugin-plan (no push, no PR) carrying this journal, its anchor and evolution records and the delivery report; stage done.

## Rulings

- RULING-001 | date=2026-10-04 | decision=interaction autopilot up to delivery; stop only for delivery approval | reason=user choice when accepting the three CodeGraph follow-up frames | source=user | supersedes=none

## Handoff


current: done
status: ready
next: None - delivered.
must_read: .agentic/tasks/TASK-d9c1ffd8.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: POINTER_DIGEST in template and mirrored aegis.py; root AGENTS.md, CLAUDE.md, QWEN.md; test_cli_core.py (two tests); REQ-UX-eab16188; CHANGELOG; knowledge pages reusable-workflow-payload.md and codegraph-plugin.md
evidence: check --strict --run exit 0 (test ok, lint ok, codegraph_test ok); review round 2 approved/approved; manual no-hint trial used know_graph
issues: one accepted deviation (pointer refresh carries earlier-release digest text, see Log); 17 pre-existing warnings
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 2

## Delivery report (2026-10-05)

- stage: deliver; type: change; path: full; branch: ddp/codegraph-plugin-plan
- requirements:
  - REQ-UX-eab16188 - Name the knowledge-graph commands in the generated pointer digest
- deviations: 2 recorded
  - validate: the root pointer refresh also brings in digest paragraphs shipped in 0.11.0-0.13.0 that were never refreshed in this repository (journal Log, autopilot, Stage report, narrower deviation rule) - accepted as current shipped text; the commit is larger than the feature and changes the instructions agents follow here (S1).
  - validate: pointer refresh carries earlier-release digest text (accepted); 17 pre-existing warnings
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=2
- diff vs task base 1aee86b: 16 file(s) changed, 1973 line(s) added; 1 file(s) not content-scanned
- checks: errors=0 warnings=18 notes=5
- checklist: 5/6 done; open: close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
