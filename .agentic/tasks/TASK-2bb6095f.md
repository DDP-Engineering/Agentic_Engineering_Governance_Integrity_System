<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-2bb6095f - Name the enclosing symbol in CodeGraph reference answers

stage: deliver
type: change
path: full
interaction: autopilot
requirements: REQ-FUNC-c88e2b22, REQ-FUNC-40ac076a, REQ-FUNC-b383069e, REQ-FUNC-ff8000c4
parent:
branch: ddp/codegraph-plugin-plan
base: 1aee86b4d4220e834f19ddedea42fa3f0a36e207
opened: 2026-10-04

## Done checklist (current stage)

- [ ] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: `know_graph_callers`, `know_graph_refs` and `know_graph_symbol`
identify the function that contains each reference only by an ID prefix
(`from=cc6a51a850`). To say which function makes a call - the usual question -
an agent must run `know_graph_symbol` once per ID. (OBSERVED in the 2026-10-04 ADORE trial: AEGIS 0.14.0 and CodeGraph deployed to F:\2026_AgenticDeliveryOrchestratorRuntimeEngine (commit 450798e), two headless Claude Code runs on the same navigation question; transcripts in the session scratchpad, not committed: of the
hinted run's 10 `know_graph` calls, 4 batches were such lookups; one of them,
a shell loop over IDs, was refused by the host's permission check; the run
cost $1.37 against $1.06 for the run without CodeGraph, with the same answer.)
Desired outcome: one `callers` or `refs` answer names the enclosing function or
class of every reference, so a caller question needs no follow-up lookups.
Actors: an AI agent or developer querying through `python .agentic/aegis.py
know_graph_*`; the AEGIS core, which validates each response envelope.
Primary scenario: `know_graph_callers <id of derive_run_id>` -> each line shows
the call site and the name of the function containing it (for example
`Orchestrator._run_id`) as well as its ID -> the agent reports or follows the
chain with `know_graph_callers` on that ID, without `know_graph_symbol`.
Examples: `caller: lexical-binding call derive_run_id |
04_Software/adore/orchestrator.py:2723 | from=cc6a51a850` today; the agent then
needed `know_graph_symbol cc6a51a850` to learn it is `Orchestrator._run_id`.
Counterexamples: a module-level reference has the module as its container,
and a reference with no container keeps `from=-`; JSON consumers that ignore
unknown fields keep working.
In scope: the reference record and compact reference line in
`05_Software/aegis/plugins/codegraph/codegraph/queries.py` and `protocol.py`
(for `callers`, `refs` and `symbol` neighbors); spec
`.agentic/specs/REQ-FUNC-8cb1a3b7.md` (Records, Compact text); the covering
requirement; plugin tests including the golden digest; `.agentic/CLI.md` and
the plugin README where they show answer lines; the dogfood mirror
`.agentic/plugins/codegraph/`; the CodeGraph knowledge page; a several-IDs form of
the ID-taking commands (`symbol`, `callers`, `refs`) in the core dispatch
`cmd_know_graph` and the plugin, with its tests (RULING-002).
Out of scope: accepting names instead of IDs for `callers`/`refs`; index
schema changes (the containing symbol's name is already stored with that
symbol, INFERRED from `queries.py` joins); host permission behavior.
Constraints: protocol version 1 stays (the core checks envelope fields only,
OBSERVED in `codegraph_validate`; the change adds a field); answers stay within
`max_output_bytes` (default 8192), so a longer line means fewer records per
page; long names follow the existing shortening rules (`LONG_TEXT`,
`SHORTENED`); identical results on Windows and Linux (REQ-PLAT-3430c1f3);
Python 3.11-3.14.
Success signals: the trial question's `callers` answers name `Orchestrator._run_id`,
`_pick_ticket` and `_claim_and_conduct` directly (automated on a fixture
repository); the existing plugin suites pass on the platform matrix; a repeat
of the hinted trial needs no `know_graph_symbol` lookups for names (manual).
Evidence: STATED - the request. OBSERVED - `protocol._reference_line` renders
`from=<from_display>`; `queries.reference` builds `from` and `from_display`
only; spec Records list `from` and `from_display`; trial transcript. INFERRED -
the name can be fetched with a join on `r.from_id` without a schema change.
UNKNOWN - the exact name form (qualified name versus the name below the
module, since the path is already on the line), settled in design.
Assumptions: an additive JSON field is compatible within protocol v1.
Unknowns: the name form (design).
Decision-blocking questions: (1) multi-ID lookup - answered: in scope
(RULING-002).
Proposed behaviors: each reference record gains the enclosing symbol's name;
the compact reference line shows that name with its ID prefix; `-` stays for
references with no container.
Path and reason: full - the protocol record and text format change and the
spec must say so.

| criterion | yes | no | evidence |
|---|---|---|---|
| no new externally observable behavior | | no | answer lines change |
| no new interface or data format | | no | new record field |
| no new dependency | yes | | none |
| an existing requirement covers the behavior | | no | REQ-FUNC-8cb1a3b7 fixes `from=<prefix>` |
| no security- or data-handling change | yes | | read-only queries |

## Requirement coverage

Behavior inventory: (1) a reference in a `symbol`, `callers` or `refs` answer -> carries its
container's qualified name (JSON `from_name`) and the text line shows `from=<name> id=<prefix>`;
boundary: no container -> null and `from=-`; long names shortened like other names, IDs never.
(2) one to 20 IDs for `symbol`/`callers`/`refs` -> one answer in request order, each record's
`subject` names its target, text adds `for=<prefix>` with several targets; boundaries: duplicate
IDs answered once, more than 20 -> `invalid_request`, first malformed/unknown/ambiguous target
answers for the whole request naming it; paging across targets binds them in order. (3) the core
accepts several IDs for those three commands and passes them after `--` in order; `find` and
`file` keep one target.

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| a caller question needs no name lookups | each reported reference names its enclosing symbol | REQ-FUNC-c88e2b22 (new) | method, function and module containers named in JSON and text | no container -> null / `from=-`; shortening | plugin test_queries / test_protocol | see Design |
| several IDs in one call (RULING-002) | symbol/callers/refs answer up to 20 targets in one response | REQ-FUNC-40ac076a (new) | two targets in order with `subject` and `for=` | duplicates, 21 IDs, unknown or ambiguous target, paging across targets | plugin test_queries / test_cli | see Design |
| several IDs in one call (RULING-002) | the core passes several IDs after `--` in order | REQ-FUNC-b383069e (revised) | three IDs reach the stub in order | missing target exits 2; find/file keep one target | test_codegraph_dispatch, plugin test_cli | see Design |
| several IDs in one call (RULING-002) | page tokens bind every target in order | REQ-FUNC-ff8000c4 (revised) | paging across two targets returns each record once | targets reordered -> `page_token_mismatch` | plugin test_queries | see Design |

## Design

Requirements coverage: REQ-FUNC-c88e2b22 -> container names in queries.py and protocol.py;
REQ-FUNC-40ac076a -> target list in cli.py, resolution and union queries in queries.py, text in
protocol.py; REQ-FUNC-b383069e -> core argparse and argv in aegis.py; REQ-FUNC-ff8000c4 ->
request digest over the resolved target IDs. The wire contract lives in
.agentic/specs/REQ-FUNC-8cb1a3b7.md ("Several targets", Records, Compact text).

Components: the core only accepts several IDs for `know_graph_symbol`, `_callers`, `_refs`
(`nargs="+"`) and passes them after `--` in order; it still validates only the envelope
(REQ-FUNC-b383069e). The plugin owns the cap, resolution, records and text.

Interfaces: plugin `parse_arguments` sets `args.targets` (list) from the positional values or
from everything after `--`; `find`/`file` keep exactly one target (usage error otherwise, as
today); `args.target` stays the first for the single-target operations. JSON records gain
`from_name` and `subject`; `details.targets` (int) on symbol/callers/refs; `symbol` keeps
`details.symbol` for one target and uses `details.symbols` for several. Protocol stays 1:
fields are additive and the core ignores record fields (OBSERVED `codegraph_validate`).

Data and state: no schema or extractor change - `from_name` is a LEFT JOIN of `symbols` on
`refs.from_id`; the golden fact digest is unaffected. REF_COLUMNS gains the joined name, so
the positional ORDER BY in `callers` moves; queries switch to named sort keys.

Execution: resolve every target first (hex check, prefix lookup, ambiguity) in request order,
dedupe by resolved ID, then one UNION ALL query per action carrying a target ordinal, ordered
by ordinal, then the action's own order, with LIMIT/OFFSET over the whole sequence (callers:
ordinal, linked-before-candidate, path, line, column, rowid).

Failure: first bad target answers for the whole request (error/not_found/ambiguous) and its
message names the target; 21+ targets -> invalid_request before any lookup.

Compatibility: single-target answers keep their records and order; their text lines change
only in the `from=` part (names added). Old page tokens stay valid for one target because the
digest over one ID is unchanged.

Test seams: plugin tests/test_queries.py (names, several targets, dedupe, cap, failures,
paging), tests/test_protocol.py (line formats, `for=`, shortening of from_name, golden text),
tests/test_cli.py (target parsing; revise test_more_than_one_target_is_a_usage_error to
find/file); core tests/test_codegraph_dispatch.py (three IDs in order; find with two -> exit 2).

Alternatives: module-relative names (shorter, but need the path to be unambiguous); partial
answers with per-target statuses (richer, but a new envelope shape); a `details.subjects` ID
list instead of a count (can exceed the 512-byte minimum budget with 20 targets).

Expected files: aegis.py (template + mirror), plugin cli.py, queries.py, protocol.py, plugin
tests, test_codegraph_dispatch.py, CLI.md, 06_SoftwareDocu/09_CLI_Reference.md, plugin
README, CHANGELOG, codegraph knowledge page; dogfood mirror .agentic/plugins/codegraph/.
Risks: longer text lines fit fewer records per byte budget; the union query with 20 targets
is larger SQL but bounded. Open decisions: none. No architecture drawing owed (behavior only).

## Log

- 2026-10-04 frame: full path (protocol record and compact line change); multi-ID lookup and scope awaiting the user.
- 2026-10-04 frame: scope accepted by the user with multi-ID lookup added (RULING-002); queued second; interaction autopilot up to delivery (RULING-001); full path.
- 2026-10-05 specify: 2 requirements created (REQ-FUNC-c88e2b22 names, REQ-FUNC-40ac076a several targets), 2 revised (REQ-FUNC-b383069e - several IDs pass through after `--`, find/file keep one; REQ-FUNC-ff8000c4 - tokens bind every target in order), 0 retired; protocol spec REQ-FUNC-8cb1a3b7.md (records `from_name` and `subject`, Several targets, budgets, paging, compact text, example) and dispatch spec REQ-FUNC-b383069e.md updated. Decisions taken under autopilot and recorded in the spec: qualified names, cap of 20 targets, all-or-first-failure resolution, duplicates answered once.
- 2026-10-05 design: note written (## Design) - additive protocol-1 fields, union queries with a target ordinal, all-or-first-failure resolution, `details.targets` count for the text view (spec updated); no schema or extractor change.
- 2026-10-05 build red: REQ-FUNC-c88e2b22; command=`python -m pytest -q -p no:cacheprovider tests/test_queries.py::test_references_name_their_containing_symbol tests/test_protocol.py::test_reference_lines_name_their_container tests/test_protocol.py::test_an_oversized_container_name_is_shortened_like_other_names` (in 05_Software/aegis/plugins/codegraph); exit=1; expected missing behavior=reference records have no from_name (KeyError), the compact line shows only from=<prefix>, and from_name is not among the shortened fields.
- 2026-10-05 build green: REQ-FUNC-c88e2b22; command=`python -m pytest -q -p no:cacheprovider tests/test_queries.py tests/test_protocol.py tests/test_cli.py` (in 05_Software/aegis/plugins/codegraph); exit=0; 116 passed, 1 skipped.
- 2026-10-05 build red: REQ-FUNC-40ac076a, REQ-FUNC-b383069e, REQ-FUNC-ff8000c4 (shared several-targets seam); commands=`python -m pytest -q -p no:cacheprovider tests/test_queries.py::test_several_targets_answer_in_request_order tests/test_queries.py::test_duplicate_targets_are_answered_once tests/test_queries.py::test_target_failures_answer_for_the_whole_request tests/test_queries.py::test_paging_runs_across_targets_and_binds_their_order tests/test_cli.py::test_id_operations_take_several_targets_after_the_marker tests/test_protocol.py::test_several_targets_render_their_subjects` (plugin) and `python -m pytest -q tests/test_codegraph_dispatch.py::test_id_commands_pass_every_id_in_order` (05_Software/aegis); exit=1 each; expected missing behavior=the plugin rejects a second target (give exactly one target, after --), the core rejects extra IDs (unrecognized arguments), and the text view has no for= suffix or per-target symbol lines.
- 2026-10-05 build green: REQ-FUNC-40ac076a, REQ-FUNC-b383069e, REQ-FUNC-ff8000c4, REQ-FUNC-c88e2b22; commands=`python -m pytest -q -p no:cacheprovider tests` in 05_Software/aegis/plugins/codegraph on Windows Python 3.12 (238 passed, 4 skipped), 3.11 and 3.14 with the borrowed pytest packages (238 passed, 4 skipped each) and WSL Ubuntu Python 3.12 (241 passed, 1 skipped), all exit 0; `python -m pytest -q tests/test_codegraph_dispatch.py` in 05_Software/aegis (44 passed, 1 skipped); `python -m ruff check 05_Software/aegis` clean after parenthesizing three implicit concatenations.
- 2026-10-05 build: evolution 12 modified files, all in scope (plugin cli/queries/protocol/README, plugin tests, core aegis.py and dispatch test, CLI.md and 09_CLI_Reference.md, CHANGELOG); plugin README added to the affected_paths of REQ-FUNC-c88e2b22 and REQ-FUNC-40ac076a, CLI.md to REQ-FUNC-40ac076a; remaining check warnings: uncovered-source on the plugin's test files (the [layout] source glob 05_Software/aegis/plugins/ also holds its tests - known overlap, accepted in TASK-82033852) and pre-existing ones (other journals, tracked sidecars, the untracked .7z).
- 2026-10-05 validate: diff reviewed hunk by hunk; one change made - the `symbol` neighborhood is now read lazily and stops at limit+1 records (itertools.islice), so up to 20 targets no longer read and hash every neighbor's file before windowing (same window and has_more; REQ-NFR-17c50caa); knowledge reconciled (codegraph-plugin.md interface, invariants, key behaviors); project and environment context unaffected (they describe the commands generally); explicit review round 1 requested from two independent reviewers; manual no-hint agent trial running against the scratch ADORE clone with this plugin.
- 2026-10-05 validate manual observation (frame success signal, not a requirement verification): method=headless Claude Code, the same no-hint question, scratch clone of ADORE with the TASK-d9c1ffd8 digest and this candidate's plugin, read-only tools, $3 cap; observed=the agent ran know_graph_check, find, callers and refs, then one `know_graph_callers` call with three IDs for the second hop; one know_graph_symbol call (for detail, not for a name); no shell loops; all 15 ground-truth sites in the answer; 15 tool calls, 120 s, $0.85 - against 28 calls, 207 s, $1.56 with the digest alone and 19 calls, 105 s, $1.06 with plain search. One refusal: a PowerShell command joined with ';' (host parser). Single model-dependent run.
- 2026-10-05 validate review round 1: implementation quality - changes_required: (I1, blocking) with several `symbol` targets and a tight byte budget, `fit` trims `details.symbols` while a kept neighbor's target is among the dropped ones, and the text view then drops that neighbor (footer shown=1 with no reference line) or prints it under the wrong symbol when one symbol remains; (I2) the refs request-order and callers per-target-order assertions cannot fail (request order equals path order; the paging case has no candidates); (I3) Design says named sort keys, code keeps positional ORDER BY; (I4) docs say each line ends for=, but only reference lines carry it and the stale marker follows; (I5) the core rejects options placed between IDs - document that IDs go together.
- 2026-10-05 validate review round 1: specification compliance - approved with minor findings: (S1) the cross-target paging test is not linked to REQ-FUNC-40ac076a; (S2) REQ-FUNC-ff8000c4 verification lacks the reordered-targets case; (S3) the spec example shows freshness=current for callers, which answers not_fully_checked; (S4) = I4, plus CLI.md says each symbol gets its own neighborhood while one window is shared; (S5) = I3, and the design's one-UNION-per-action does not describe `symbol`; (S6) the islice change is in scope but the spec Budgets bullet does not mention `symbol` reading limit+1; (S7) the per-action protocol fixtures lack the new record fields and a several-target fixture.
- 2026-10-05 validate -> build: fix cycle 1 of 4 for the recorded round-1 findings only (I1-I5, S1-S7); review_round becomes 2 on return.
- 2026-10-05 build red (fix cycle 1, I1): REQ-FUNC-40ac076a; command=`python -m pytest -q -p no:cacheprovider tests/test_protocol.py::test_a_kept_neighbor_survives_when_its_target_is_trimmed` (plugin); exit=1; expected missing behavior=at a 512-byte text budget the kept neighbor of the 16th of 20 targets is not printed (0 caller lines).
- 2026-10-05 build green (fix cycle 1, I1): fit keeps a target in details.symbols while a kept neighbor answers for it, and the several-target text prints any neighbor without a shown target after the groups; `python -m pytest -q -p no:cacheprovider tests/test_protocol.py` exit=0, 73 passed.
- 2026-10-05 build (fix cycle 1): I2 - the refs order assertion now requests targets in the reverse of path order, and the cross-target paging case adds candidates and checks that the first page of seven holds only the first target's six linked calls and its candidate; mutation check on scratch copies: reordering the refs sort to path-first and the callers sort to linked-first each fail one of these tests. I3/S5 - positional ORDER BY kept and commented in queries.py; the Design note's 'named sort keys' and 'one UNION ALL per action' are superseded: callers and refs use one UNION ALL each with positional sorts, symbol reads per target through a bounded generator. I4/S4/I5 - CLI.md, 09_CLI_Reference.md and the plugin README say each reference line carries for= with several distinct targets, IDs are listed together after any options, and several symbols share one neighborhood limit. S1 - three tests linked to REQ-FUNC-40ac076a; S2 - REQ-FUNC-ff8000c4 verification names reordered targets and per-target order; S3 - spec example freshness corrected; S6 - spec Budgets names the symbol read cap and the kept-target rule, Compact text the for= placement and the after-groups fallback; S7 - protocol fixtures carry from_name, subject, subject_display and details.targets, and a several-target fixture test checks every record line; cli.py docstring shows [-- target...].
- 2026-10-05 build green (fix cycle 1): plugin suite `python -m pytest -q -p no:cacheprovider tests` exit 0 on Windows 3.11, 3.12 and 3.14 (242 passed, 4 skipped each) and WSL Ubuntu 3.12 (245 passed, 1 skipped); ruff clean; dogfood plugin resynced; evolution refreshed (12 modified files).
- 2026-10-05 build -> validate: review round 2 requested from both reviewers.
- 2026-10-05 validate review round 2: implementation quality - approved (I1-I5 resolved; the kept-neighbor test fails against the old trimming; both order mutations fail a test; minor notes: the after-groups text fallback is unreachable while fit keeps answered targets - kept as a guard; the JSON view at the 512-byte minimum grows to about 1 KB with a protected target, as the single-target case already does). Specification compliance - approved (S1-S7 resolved); one new minor accepted unfixed: REQ-FUNC-40ac076a's verification text does not mention the budget case its linked kept-neighbor test also checks - the spec's Budgets rule states it, and editing the requirement now would reset both verdicts; note: several symbol targets with no kept neighbors may all be trimmed at the minimum budget, which the spec allows. Both verdicts apply to the current candidate.
- 2026-10-05 validate final: command=`python .agentic/aegis.py check --task TASK-2bb6095f --strict --run`; exit=0; test (`python -m pytest -q 05_Software/aegis/tests`) ok 197.6 s, lint (`python -m ruff check 05_Software/aegis`) ok, codegraph_test (`python -m pytest -q 05_Software/aegis/plugins/codegraph/tests`) ok 177.7 s; errors=0, warnings=20: uncovered-source on the plugin's three changed test files (the [layout] source glob 05_Software/aegis/plugins/ also holds its tests - accepted, see build), and pre-existing ones outside this candidate (36 tracked sidecars, older open journals, the untracked .7z). Evolution refreshed after the last candidate edit (12 modified files).

## Rulings

- RULING-001 | date=2026-10-04 | decision=interaction autopilot up to delivery; stop only for delivery approval | reason=user choice when accepting the three CodeGraph follow-up frames | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=multi-ID lookup is in scope: the ID-taking know_graph commands accept several symbol IDs in one call | reason=user answer to frame question 1 | source=user | supersedes=none

## Handoff


current: deliver
status: waiting
next: Present the validated candidate and wait for the delivery choice.
must_read: .agentic/tasks/TASK-2bb6095f.md
blockers: none

## Stage report


stage: validate
result: completed
current: deliver
changed: plugin cli.py, queries.py, protocol.py, README; core aegis.py (+mirror); CLI.md (+mirror, 09_CLI_Reference.md); tests; 4 requirements; 2 specs; CHANGELOG; codegraph-plugin.md; dogfood plugin copy
evidence: check --strict --run exit 0 (test ok, lint ok, codegraph_test ok); plugin suite green on Windows 3.11/3.12/3.14 and WSL 3.12; review round 2 approved/approved; manual trial 15 tool calls, $0.85
issues: accepted: REQ-FUNC-40ac076a verification text omits the budget case; uncovered-source on plugin tests (layout overlap); pre-existing warnings
next: deliver - awaiting the delivery choice
needs_user: yes
spec_compliance: approved
implementation_quality: approved
review_round: 2
