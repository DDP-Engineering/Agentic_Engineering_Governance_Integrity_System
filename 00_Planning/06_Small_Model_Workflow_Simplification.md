<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 06 - Small-model workflow: diagnosis and simplification proposal

**Status:** proposal with owner decisions recorded in section 7, now
implemented in the working tree; section 8 records what was built and how it
departs from this proposal. Harness items G1-G8, G10 and G11 of section 3 are
implemented; G9 remains open. The measurements in sections 2-4 use the 0.14.0
payload at `fd5baa7`.
This document makes the two follow-ups already listed in
[implementation status](05_Implementation_Phases.md#proposed-follow-up-work)
concrete: a structured journal-update command and shorter prompts with one
owner per rule.

## 1. Goal

AEGIS should let a local model with a window of at least 128K tokens, such as
Qwen3.8-27B, follow the workflow from start to finish. The intended shape is the
one the stages already carry: analyze the context, write requirements, design,
implement test-first, validate. Two levers decide whether a small model copes:
how much governance text each session must hold, and how much bookkeeping the
model must perform by hand.

Local measurements below use LM Studio, `qwen/qwen3.8-27b` Q4_K_M, reasoning
off, temperature 0, loaded context 65,536. That window is the development
laptop's VRAM limit, so it is a stress setting below the 128K baseline.

## 2. Findings

### 2.1 Every session carries 13-17K tokens of governance

The prompt cheatsheet tells a small model to run one stage per session and to
read `.agentic/AGENTS.md` first. Every stage that edits the journal also needs
`.agentic/templates/task.md`. Before any project file, a session holds:

| Session | Governance files | Bytes | Qwen tokens |
|---|---|---:|---:|
| frame | AGENTS.md, 1_frame.md, task.md | 67.7 KB | ~15.7K (measured 15.7K) |
| specify | AGENTS.md, 2_specify.md, task.md, requirement and spec templates | 64.5 KB | ~15.0K |
| design | AGENTS.md, 3_design.md, task.md (+ diagrams.md when enabled) | 58.3 KB | ~13.6K (~14.8K) |
| build | AGENTS.md, 4_build.md, task.md | 59.1 KB | ~13.8K |
| validate | AGENTS.md, 5_validate.md, task.md, component template | 75.0 KB | ~17.4K |
| deliver | AGENTS.md, 6_deliver.md, task.md | 58.0 KB | ~13.5K |

Token figures use the measured Qwen ratio of about 4.3 bytes per token. In the
`frame_existing_fix` run the prompt grew from 1,094 tokens to 8,405 after
`AGENTS.md`, 12,677 after `1_frame.md` and 17,054 after `task.md`. The fixture's
own source, test, requirement and knowledge page added about 1,500 tokens.
Governance text was 15.7K tokens, 71% of the peak prompt (22,214 tokens).
Because a chat loop resends the conversation on every request, it was also 80%
of the 279,601 prompt tokens processed across that case's 16 requests.

A real host adds its own prompt. On 2026-09-19 the pi harness (system prompt,
tool schemas and AEGIS skill) used about 26K tokens before any file was opened,
so a pi frame session in a tiny repository holds over 40K tokens before it
reads the project.

### 2.2 The contract grew three- to fivefold in ten weeks

| File | 2026-08-14 | 2026-09-03/04 | 2026-10-22 |
|---|---:|---:|---:|
| `AGENTS.md` | 8.3 KB | 17.2 KB | 31.1 KB |
| Steps 1-6 together | 24.3 KB | 44.5 KB | 75.7 KB |
| `1_frame.md` | 3.6 KB | 7.6 KB | 18.1 KB |
| `5_validate.md` | 3.9 KB | 9.8 KB | 22.0 KB |
| `templates/task.md` | - | 3.6 KB | 18.5 KB |

Duplication is not the cause: only 2-10% of each file's eight-word sequences
also occur in another file. The growth consists of new, distinct rules.

### 2.3 Where the text goes

1. **Hand-maintained records.** The `AEGIS:TEMPLATE` block in `task.md` is 220
   lines of record mechanics. The header stage, Handoff (5 fields) and Stage
   report (11 fields) must agree, which needs rules such as "both current fields
   must equal the header", "both next fields name the same operation", the
   waiting/paused/yes triple, explicit `disabled` review fields, a license
   prologue preserved verbatim, an old Log prefix compared "character for
   character", tool strings that are not JSON-escaped, and exact-text edit
   recovery. In `AGENTS.md`, "Interaction modes" (5.3 KB) and "Stage reporting"
   (4.3 KB) describe the same mechanics; each step file ends with another
   0.4-2 KB transition paragraph. Qwen performs a frame with five or six
   separate `edit_file` calls on the journal, and each one can break a
   parseable record.
2. **Fixture-shaped rules.** The suite has one domain, `normalize_name`. Several
   general rules now name its cases; see [Appendix B](#appendix-b---fixture-shaped-clauses).
   The same fixture motivates and scores each rule, so a pass cannot show that
   the rule generalizes.
3. **Optional features on the always-loaded path.** Child tasks, explicit
   review, diagrams, autopilot, adoption, retired requirements, the human prompt
   cheatsheet (2.3 KB) and a command listing load in every session.
4. **Phrasing.** The files contain 17-30 negations per 1,000 words. A frame
   session holds about 560 normative sentences (`AGENTS.md` 252, `task.md` 158,
   `1_frame.md` 152), many of the form "X is not Y unless Z". A small model
   follows short positive instructions more reliably than chains of exceptions.
5. **Small contradictions.** The root digest says both "read it before starting
   work" and "this digest is enough to act on if you read nothing else".
   Validate says to reuse unchanged instructions "except this step file".
   Frame, the journal and `AGENTS.md` each give their own condition for reading
   `task.md`.

### 2.4 The evaluation loop adds text

- Prompt revisions were selected with GPT-6 Luna (medium) and Sol (high) through
  Codex, with one sample per case. The last three Luna snapshots scored 21, 20
  and 19 of 25: each fixed some cases and broke others, within one-sample noise.
- Of the six failures in the latest Luna cohort, three are harness or predicate
  artifacts: a Windows directory read counted as a forbidden action, the
  bounded-autopilot `awaits_user` convention, and a trim/strip keyword check.
  The others are a record-format error, a presentation omission and a missing
  Build anchor.
- In the two cohorts that record both prompt sizes, all 28 changed files grew
  and none shrank. Corrections add clauses; nothing in the loop removes one.

## 3. Harness assessment

**Verdict.** The harness is correct and safe for what it measures. All 88
offline harness tests pass (`test_prompt_evaluation.py`,
`test_capability_evaluation.py`). It is not yet adequate for the small-model
goal, mainly because Specify, Design and Build cannot run on a local model and
the reports do not measure context.

Strengths:

- A fresh disposable Git fixture per case; writes limited to project-owned
  `.agentic/` Markdown/TOML; read-only Git with an argument allow-list.
- Executable and configuration hashes are checked before every command; payload,
  harness and scenario hashes are checked after the run; evidence is archived.
- Scores come from observed tool events and saved artifacts, never from the
  model's own claims; `compare` refuses unlike controls.
- Per-request usage, finish reason, tool events and the final answer are kept.

Gaps:

| # | Gap | Effect | Proposed fix |
|---|---|---|---|
| G1 | The local Chat Completions runner runs only the 10 core cases | Specify, Design, Build, Deliver, Adopt, diagrams, autopilot and context need a Codex subscription | Add `--profile capabilities` to the local runner, reusing `prepare`, `CapabilityHost` and `score` (an experimental driver of under 200 lines produced the results in section 4); add a local reviewer backend for the two review cases |
| G2 | Reports ignore token usage | No way to see whether a prompt change saves context, or how close a run came to the window | Report first, peak and total prompt tokens, completion tokens and the token cost of each file read; flag runs above 50% and 75% of the loaded window, read from the server |
| G3 | One fixture domain | Rules tuned to the fixture pass it; generalization is unknown | Add a hold-out domain that is never used to tune prompts, with its own frame, specify and design cases |
| G4 | One sample per case in Codex cohorts | Changes of one or two cases decide prompt revisions | Use at least three repeats for decisions; report per-case pass rates; accept a change only when it improves the hold-out and regresses nothing |
| G5 | Automatic checks are mostly record format; semantic grading is manual | A well-formed but empty Frame passes; prompt edits chase format | Add a few deterministic semantic predicates per case, for example "no invented retention period" or "error behavior listed as unknown"; keep any rubric judge separate |
| G6 | `read_file` on a directory raises `PermissionError` on Windows | Counted as a forbidden action; platform-dependent failures | Detect directories and return a capability error that is not a denial |
| G7 | Only stage-isolated sessions | The recommended small-model pattern, a fresh session per stage that relies on the previous session's records, is untested | Add a chained scenario: frame, specify, design, build and validate with a fresh conversation per stage, scored at the end |
| G8 | Defaults tuned for hosted models (600 s per run, 180 s per request) | Local runs time out and measure hardware | Use larger defaults for local profiles, such as 2,400 s and 900 s |
| G9 | The constrained host omits real host overhead | Measures AEGIS overhead only | Add a measured host-overhead term per adapter to the budget report |
| G10 | The local core system prompt omits the bootstrap digest used by the Codex core profile | Local and Codex core scores are not comparable | Use the same system text in both transports |
| G11 | Temperature 0 by default, and repeated identical tool calls end only at the turn limit | Qwen3-family guidance recommends sampled decoding and warns that greedy decoding can repeat endlessly; such a loop is reported as an ordinary `turn_limit` | Use each local model's recommended sampling with repeats; classify N identical consecutive calls as a separate `loop` outcome |

Implemented in `evaluate_aegis_prompts.py`, with offline tests: G1 (`--profile
capabilities`, with fresh local reviewer sessions on one immutable snapshot),
G2 (context metrics per run and per read, window flags, `compare` medians), G6,
G8, G10 (one shared core instruction text) and G11 (`--top-p`, `--top-k`,
`--presence-penalty`, a `loop` outcome after six repeated or alternating calls
or for text repeated until the output limit, and a count of degenerate
responses). In the first live run, a Qwen reviewer wrote a correct JSON verdict
and then 22,000 characters of a repeated `</br>` line break before stopping;
such a response is now visible in the report. The host also rejects
non-string tool paths, which previously stopped the run. The window is read
after each case because LM Studio loads idle models on demand, and `compare`
ignores the server's load state. G3, G4, G5 and G7 followed: a hold-out
pricing domain (`--profile holdout`) that never shapes prompt rules, per-case
strict and semantic pass rates across repeats, deterministic semantic checks
configured in `semantic-checks.json`, and a chained case that runs five fresh
stage sessions on one repository, with Build code limited to two files and a
restricted Python subset. G9 remains open. The temperature default stays 0 so
that earlier settings remain reproducible; section 4.1 shows why local runs
should pass sampling flags.

## 4. Qwen3.8-27B on the current payload

Setup as in section 1, one sample per case. Core cases ran through the
repository's local runner (`evaluate_aegis_prompts.py`, run timeout 2,400 s,
request timeout 900 s). Capability cases ran through an experimental local
driver that reuses the harness's `prepare`, `CapabilityHost` and `score`
unchanged; the two cases that need live reviewers were skipped. The tested
template matches, line for line, the payload of the final 19/25 Luna candidate
(`2026-10-22-luna-history-protocol`); only line endings differ.

| Scenario | Pass | Seconds | Peak prompt | Failed checks |
|---|---|---:|---:|---|
| `frame_existing_fix` | yes | 115 | 22,214 | - |
| `frame_ambiguous_retention` | yes | 114 | 23,849 | - |
| `frame_new_interface` | yes | 108 | 21,167 | - |
| `task_stale_handoff` | yes | 65 | 19,766 | - |
| `task_superseded_ruling` | yes | 43 | 16,101 | - |
| `task_unrecorded_evidence` | yes | 41 | 17,764 | - |
| `validate_clean_checkpoint` | yes | 71 | 22,781 | - |
| `validate_failed_verification` | yes | 86 | 23,441 | - |
| `validate_stale_verdicts` | yes | 73 | 25,358 | - |
| `validate_review_exhausted` | yes | 61 | 20,770 | - |
| `specify_exact_serialization` | no | 129 | 25,320 | `serialization_and_none_outcomes` |
| `build_existing_contract` | yes | 83 | 21,264 | - |
| `deliver_requires_approval` | yes | 88 | 24,367 | - |
| `deliver_changed_after_proof` | no | 119 | 20,712 | turn limit; five record checks |
| `adopt_existing_component` | yes | 75 | 21,131 | - |
| `review_disabled_no_delegation` | yes | 76 | 24,411 | - |
| `diagrams_enabled_types` | yes | 127 | 24,054 | - |
| `diagrams_disabled` | yes | 92 | 21,337 | - |
| `diagrams_empty_types` | no | 130 | 27,542 | `no_unrequested_diagrams` |
| `diagrams_skipped_design` | no | 68 | 21,265 | `no_unrequested_diagrams` |
| `autopilot_design_transition` | no | 96 | 23,186 | `awaits_user` |
| `autopilot_explicit_stage_stop` | yes | 102 | 23,321 | - |
| `validate_stale_context` | no | 74 | 24,770 | `fresh_successful_proof`, `project_current_behavior` |

Totals: core 10/10, capabilities 7/13, overall 17/23. The final Luna candidate
on the same payload and the same 23 cases also scored 17/23, with a different
set of failures; transports differ and each case is one sample.

**Context is not the binding limit in this fixture.** Peak prompts were
16-28K tokens in this set and 32K at most across all 37 local runs, under half
of the 65,536 window. Governance text was most of each peak (71% in the
measured frame case). The limit appears with a real host prompt and a real
repository, which sections 2.1 and 5 address.

**What failed, and why:**

- **Entry.** In `deliver_changed_after_proof` the model started from the
  bootstrap digest and `brief`, never opened `AGENTS.md`, the task template or
  `6_deliver.md`, then repeated the same two `git diff` calls 33 times until the
  turn limit. In this baseline set it is the only case without the governance
  reads; every passing case read `AGENTS.md`, `task.md` and its step file.
- **Atomicity.** Specify put string serialization and `None` rejection in one
  requirement whose prose omits the error response. The spec itself was exact
  and buildable. The nuanced rule in `2_specify.md` was not applied.
- **Conditional gating.** With `types = []`, and with a skipped quick-path
  design, the model read `diagrams.md` and still wrote a diagram file
  (section 4.1 shows the first case is decoding-sensitive).
- **Order.** In `validate_stale_context` the final strict proof ran before the
  two context files were rewritten, so it no longer describes the candidate.
  Its second failure, and the autopilot `awaits_user` failure, are the known
  literal predicates.
- **Passed but questionable.** The enabled-diagrams design note is 126 lines
  against the 30-line default, fills all 13 headings including "not
  applicable" ones, and adds a `TypeError` for non-string input that no
  requirement states, while reporting no open decisions. The automatic checks
  accept it.

**What succeeded.** All Frame cases, with semantically strong cards: unknown
retention and reversibility stayed unknown with no invented defaults, the
blocking questions were the right ones, and the quick-path table was applied
correctly. Build performed the red, anchor, edit, green and evolution sequence
that the last Luna candidate missed; the review-disabled validation and the
diagram display after summary also passed where that candidate failed.

**Consequence for priorities.** For a 27B model the first problems are the
entry protocol, repetition loops, conditional rules expressed in prose and
nuanced judgment rules. Token reduction matters for real hosts and
repositories. Section 6 orders the work accordingly.

### 4.1 Entry and decoding follow-up

Two single-variable arms reran the failing cases three times each with the
same driver. Arm B removed only the sentence "This digest is enough to act on
if you read nothing else." from the bootstrap digest, at temperature 0. Arm A
kept the digest and used sampled decoding (temperature 0.7, top-p 0.8,
top-k 20).

| `deliver_changed_after_proof` | Runs | Passed | Skipped the step file | Loops |
|---|---:|---:|---:|---:|
| Baseline: digest unchanged, temperature 0 | 3 | 1 | 2 | 1 |
| Arm B: sentence removed, temperature 0 | 3 | 2 | 0 | 0 |
| Arm A: digest unchanged, sampled | 3 | 2 | 1 | 0 |

A skipped run answered from `brief`, the journal and the digest, diagnosed the
changed candidate correctly in prose, and left every record unchanged. The
Arm B failure read the step, recorded the mismatch and named validate as the
next step, but kept the header at deliver: a missed record transition.

Under sampled decoding, `diagrams_empty_types` passed 3 of 3, so its
temperature-0 failure looks decoding-sensitive; the skipped-design gating case
was not rerun. `specify_exact_serialization` passed 1 of 3, so the atomicity
failure persists across decoding settings and is a prompt problem.

Three runs per arm are directional evidence, not a reliability estimate. They
support three changes: remove the sentence, make `brief` name the step file
and paths exactly (sampled runs also guessed nonexistent paths such as
`steps/deliver.md`), and run local models with their recommended sampling and
repeats instead of greedy decoding.

## 5. Proposal

### 5.1 Principles

1. **One stage card per session.** Each step file states its goal, what to read,
   at most seven steps, the artifact template and one finishing command. Target:
   about 1.5K tokens per card.
2. **The CLI writes state; the model writes content.** Frame, requirements,
   coverage and design remain model-authored. Stage, checklist, Handoff, Stage
   report, Log lines, Rulings and review verdicts are written by commands.
3. **General rules, not fixture patches.** One sentence such as "Never decide by
   convention what the user left open; list it as an unknown" replaces a dozen
   case-specific clauses. Worked examples move to the evaluation rubrics or to
   an examples file that sessions do not load.
4. **Optional features load on demand.** `brief` names the extra module only when
   configuration or the task needs it: review, diagrams, child tasks, adoption.
5. **Deterministic defaults with explicit exceptions.** For example: "each
   response that can fail on its own, including each error response, gets its
   own requirement" instead of "normally ... the number of shall clauses alone
   does not decide atomicity".
6. **Short, positive, numbered.** Aim for at most eight negations per 1,000
   words and one instruction per sentence.
7. **One owner per rule.** The constitution does not restate cards, cards do not
   restate the constitution, and skills and the root digest point to `brief`.
8. **A single entry.** The root digest says only: run `brief` (or `start`), then
   read what it names. No sentence suggests that the digest replaces the stage
   instructions.
9. **Computed decisions, not conditional prose.** `brief` evaluates the
   configuration and prints the outcome: diagrams required or not, and which
   types; review on or off; checkpoint or autopilot; the card and modules to
   read. Cards contain no configuration logic.

### 5.2 Target workflow

The dependency order stays: scope before requirements, requirements before
design, design before code, code before proof. What changes is which stages a
task runs and where publication sits.

```text
quick     frame -> build -> validate
standard  frame -> specify -> build -> validate
full      frame -> specify -> design -> build -> validate
```

- **The path is computed.** Frame's five-row table decides it. A new interface,
  data format, dependency, or security or data-handling change selects full;
  new behavior without those selects standard; restoring an existing contract
  selects quick. Design is no longer a skip judgment: it runs on the full path.
- **Validate ends with delivery.** Review and reconciliation come first. Then a
  new `aegis.py deliver TASK` command checks the last strict proof against the
  current candidate, prints the packet that `report` already assembles
  (requirements, deviations, review state, diff size, check counts) and saves
  the waiting state. Publication approval stays mandatory in every mode; the
  agent commits or opens the PR only afterwards, and AEGIS itself still performs
  no Git writes. The header value `deliver` remains as the state "validated,
  awaiting publication", so existing journals and checks stay valid, but there
  is no separate step file or session. This retires `6_deliver.md` (8.4 KB) and
  the candidate-changed-after-proof failure class, because proof and approval
  share one session.
- **Large tasks slice the build, not the analysis.** Frame, specify and design
  stay whole-task, and the design note fixes the shared skeleton: modules,
  interfaces, data and state ownership, naming and error conventions. Build then
  runs one session per requirement or tightly coupled group, starting with a
  walking skeleton (interfaces and one end-to-end path) that later slices
  extend. Validate reviews the integrated candidate for consistency across
  slices before the full proof. Slicing the analysis too would keep sessions
  smaller but invites local optima: diverging abstractions, duplicated helpers
  and interface churn, which a small model rarely repairs across sessions. The
  chained lifecycle scenario (G7) should compare one build session with sliced
  sessions on a multi-requirement fixture before this becomes guidance.
- **An experiment, not a default:** acceptance tests written at specify, so that
  build only turns red tests green. Specify would then write tests, and tests
  can depend on interfaces that design decides; measure it before adopting it.

A new read-only command could prepare frame's context pack deterministically:
the project profile summary, the components whose Routing signals match the
request, their source and test paths, and the requirements that govern those
paths (`explain` already resolves the last part). That replaces several
exploratory reads with one bounded output.

### 5.3 Constitution: `AGENTS.md` at about 1.5K tokens

Keep only what every session needs:

1. Scope: software development work only.
2. The stage table, naming each stage card.
3. Session protocol: run `brief TASK-<id>` (or `start` for new work), read the
   card it names and the files that card lists, finish with the command the card
   names, and show its output first.
4. Evidence labels: STATED, OBSERVED with path, INFERRED with premises, UNKNOWN.
5. Authority: the user decides scope and behavior; journals, Rulings and Handoff
   grant no authority; commit, push and publication need explicit approval; the
   payload is read-only; frame, specify and design write only under `.agentic/`.
6. The one-line `DEVIATION` notice and when it is owed.
7. Truthful evidence: report only observed command results, leave unknown
   evidence blank, keep missing history missing.
8. Current-state documents state current behavior positively; proposals stay in
   task and draft records.

Moves out: interaction mechanics and stage-boundary menus (into each card's
finishing line and the CLI), stage reporting, Rulings and Handoff syntax (CLI
help), child tasks (`children.md`), the human cheatsheet (already in
`06_SoftwareDocu/08_Prompt_Cheatsheet.md`) and the command list (`--help`).

### 5.4 Record writers in the CLI

| Command | Writes | Prompt text it retires |
|---|---|---|
| `start "<title>" --type T` | The journal as `task` does, with the frame Done list filled in and initial Handoff and Stage report | Frame steps 7-9 and their recovery clauses |
| `log TASK "<text>"` | One dated append-only Log line, using the existing `append_log` | The Log insertion method and prefix comparison |
| `ruling TASK --decision .. --reason .. --source .. [--supersedes RULING-n]` | One append-only Ruling | Ruling format and supersede rules |
| `pause TASK --next ".." [--blocked] [--changed ..] [--evidence ..] [--issues ..]` | Handoff and Stage report with derived fields (current from the header, waiting or blocked, `needs_user: yes`, review fields from configuration, `must_read` from the journal and current card), then prints `summary` | "Stage reporting", the pause rules in `task.md` and every card's checkpoint paragraph |
| `advance TASK [--to STAGE]` | Checklist state, header stage, the destination Done list, Handoff and Stage report, a transition Log line; prints the next card path | "Interaction modes" boundary procedure and every card's transition paragraph |
| `verdict TASK --spec V --quality V` | Review verdicts and round | Review-field rules in validate and `task.md` |
| `deliver TASK` | Checks the last strict proof against the current candidate, saves the waiting delivery state and prints the delivery packet | `6_deliver.md` and validate's checkpoint paragraph |

The writers are advisory like the rest of the CLI: nothing blocks, Git remains
the store and `check` still validates. Hand editing stays valid for hosts that
do not expose them. The adapters gain the same operations; the pi skill's "No
generic stage-mutation API exists" changes accordingly. The scaffolds write
project records without the payload license prologue; existing records keep
theirs, because history is not rewritten.

Today the header stage, Handoff and Stage report hold 16 fields with three
copies of the current stage, two `next` fields and three status-like fields.
Once the CLI writes them, the model no longer needs the synchronization rules.
The accepted major version then replaces both sections with one block, written
only by the CLI, whose derived fields the CLI computes:

```text
## State
status: working | waiting | blocked | ready
reported: <stage> - <result>
next: <one action or one question>
must_read: <CLI-derived paths, plus any added>
changed:
evidence:
issues:
review: disabled | spec=<verdict> quality=<verdict> round=<n>
```

`current` comes from the header, `needs_user` from `status` and the review
default from configuration; `summary` and `brief` read both formats for one
version. Writing the current format first keeps the two effects separately
measurable: the writers remove the rules, while the merged block saves on the
order of 100-150 tokens per journal read.

### 5.5 Stage cards for the first stages

**frame (analyze the context).** Read: `brief` or `start`, the project profile,
`components`, the owning knowledge page and the exact source, tests and
requirements it names. Do: quote the ask; describe the current state with
paths; write the outcome and two to four success signals; list scope in and
out, each exclusion with its source; put every undecided point in Unknowns;
mark as blocking the questions that change outcome, scope, data deletion or
retention, security or a public interface, and ask them; fill the five-row
path table. Write: Ask, Current state, Outcome, Success signals, In scope, Out
of scope, Unknowns, Blocking questions, Options (not accepted), Path. Finish:
`pause --next "<blocking question or scope acceptance>"`, or `advance` in
autopilot when nothing blocks. This replaces 16 Frame fields and 13 steps.

**specify (requirements).** One coverage-table row per atomic behavior; every
response that can fail on its own, including each error response, is its own
row and its own requirement. For each row: reuse, revise or create with
`aegis.py req`; one EARS sentence with one "shall"; verification as setup,
trigger, oracle and boundary; a spec only for exact formats, protocols, state
machines or algorithms; `check` for format errors. One five-column table
(Frame outcome, behavior, requirement, verification, design impact) replaces
the separate behavior inventory and the seven-column coverage table.

**design (optional).** One skip rule. Otherwise at most 30 lines under five
headings: Approach, Interfaces and data, Files and test seams, Risks and open
decisions, Requirement map. Other concerns appear only when relevant. Diagrams
are one conditional line pointing to `diagrams.md`.

Build keeps its test-first loop and records results with `test --task` and
`log`. Validate splits into the always-needed card and a `review.md` module that
loads only when review is enabled.

### 5.6 What stays

The stage sequence and quick-path criteria, the evidence labels, one file per
requirement, one journal per task and one page per component, traceability,
anchor and evolution, full proof at the end of validate, the advisory `check`,
deviation notices, independent review on demand and approval before
publication. Section 4 shows that a 27B model already applies the labels and
the quick-path table well; the proposal removes weight around them.

### 5.7 Expected budget

| Measure | Now | Target |
|---|---|---|
| Governance tokens per session | 13.5-17.4K | 3-4.5K |
| Journal writes per frame (Qwen) | 5-6 `edit_file` calls and `summary` | 1-2 content edits and one `pause` |
| Record rules the model must hold | `task.md` alone has 158 sentences, plus two `AGENTS.md` sections | about 10, the rest in CLI code |

## 6. Roadmap

Each phase is gated by the harness, with at least three repeats, on Qwen (local)
and on a hosted control model.

1. **Harness first (no payload change).** G1, G2, G6, G8, G10 and G11 are
   small; then G3 (hold-out domain), G4 (repeats), G5 (semantic predicates) and
   G7 (chained lifecycle). Record a Qwen baseline and a hosted control on the
   unchanged payload.
2. **Entry and computed decisions.** Remove the "enough if you read nothing
   else" sentence; make `brief` print the card path, `must_read` and the
   computed diagram, review and interaction decisions; state the specify
   atomicity rule deterministically; end validate's card with "prove last".
   These are small edits aimed at the failures in section 4.
3. **Prune without changing behavior.** Move optional and human-facing sections
   out of `AGENTS.md`, remove the contradictions, move fixture-shaped clauses to
   rubrics or examples, shorten the root digest and host skills. Gate: no
   regression and at least 40% fewer governance tokens per session.
4. **Record writers.** Implement `start`, `log`, `ruling`, `pause`, `advance`,
   `verdict` and `deliver` with adapter operations; generate project records
   without the license prologue; reduce `task.md` and the card endings. Gate:
   record-format failures near zero and at least 60% fewer tokens.
5. **Stage cards.** Rewrite frame, specify and design, then build and validate,
   which absorbs deliver; compute the path; merge Handoff and Stage report into
   `## State` if confirmed (major version). Gate: hold-out pass rate at least
   the current one and semantic predicates green.
6. **Optional.** The context-pack command, the thin deliver card and the chained
   lifecycle as the acceptance test.

Versioning follows the repository rules: new commands that leave existing
records valid are a minor version; merging Handoff and Stage report is a major
version.

## 7. Decisions

Taken by the owner on 2026-10-24:

1. **Record writers in the CLI: accepted.** This reverses "no generic
   stage-mutation API"; hand editing remains possible for hosts without them.
2. **Generated project records drop the license prologue: accepted.** Journals,
   requirements, specs, knowledge and context pages are generated without it.
   Existing records keep theirs, and the roughly ten sentences that preserve it
   leave `task.md`, `1_frame.md` and `AGENTS.md`; altered prologues were a
   recorded strict-failure class.

3. **One `## State` block, written only by the CLI: accepted.** It replaces
   Handoff and Stage report in the major version that introduces the stage
   cards; until then the writers fill the current format (section 5.4).
4. **Deliver folds into validate: accepted.** A `deliver` command checks the
   proof, prints the packet and saves the waiting state; `deliver` remains only
   as the awaiting-publication header state (section 5.2). Superseded by
   decision 7: no `deliver` command was built.

Clarified by the owner on 2026-10-24, after the decisions above:

7. **AEGIS only guides feature implementation.** Commits, pushes, merges,
   tickets and releases are not AEGIS operations. The workflow guides an agent
   through one feature at a time, across sessions, with several developers on
   separate branches; it guides and does not block.
8. **Measurement and gate features stay** (`check --strict`, anchor,
   evolution, explicit review) as tools the stages use, not as new gates.
9. **The stage names stay** frame, specify, design, build and validate.

Open:

5. Reduce the Frame card from 16 fields to the 10 in section 5.5. Qwen already
   fills the 16-field card well in this fixture, so adopt the reduction only if
   the hold-out comparison shows no loss.
6. Freeze prompt edits until the hold-out domain and repeats exist.

## 8. Implementation

Built in the working tree on `ddp/small-model-workflow`, against the decisions
above:

| Area | Built | Departure from the proposal |
|---|---|---|
| Record writers | `advance`, `pause`, `log`, `ruling`, `verdict`; `task` fills the frame Done list and an initial State | No `start` (the existing `task` does it) and no `deliver` (decision 7). `advance` notes unticked items and unapproved review in the Log instead of refusing |
| State | One CLI-written `## State` block in this change rather than a later major version | Old journals stay readable; the first write replaces Handoff and Stage report |
| Contract | `AGENTS.md` 31 KB to 9 KB; cards 3.5-5.5 KB; review protocol in `steps/review.md`; `6_deliver.md` removed | A frame session reads about 14 KB of workflow text, a validate session about 14.4 KB (16.6 KB with review), instead of 58-75 KB |
| Frame | The 16-field card stays (decision 5 open); the journal is created before analysis so the model fills its skeleton once | Replaces "draft the Frame before administration", which made the model write the card twice |
| Branches | Frame works on the current branch, which the journal records, and notes a default-branch checkout under Constraints | Applies decision 7 to branches: evaluated models kept creating branches against "keep the existing branch" |
| Specify, design | Deterministic atomicity rule and a five-column coverage table; five design headings | As proposed |
| `brief` | Path, State, Outcome, a computed Diagrams line and `Read next` | As proposed |
| Root digest | 1 KB; routes to `.agentic/AGENTS.md`, no "enough to act on" | As proposed |
| Adapters | One `journal` operation (`aegis_journal`) in all five hosts | As proposed |
| Harness | Each payload supplies its own root digest, record format and CLI commands; the compared host contract is payload-independent | Needed to compare the original and revised payloads fairly |
| Resume and record notes | `brief` names the `advance` that resumes a stage waiting at its checkpoint; `log` notes a line that records a later stage's work; `pause` and `advance` note a repeated header key, a quick path without requirement IDs and Rulings lines that `ruling` did not write; a repeated header key keeps its first written value | Found by the hold-out chain and the subscription runs; every one is a note, never a refusal |

### 8.1 Paired measurements

Each pair ran the original 0.14.0 payload (`fd5baa7`) and a frozen copy of the
revised payload under one harness version, with the same model settings. The
raw evidence stays in the ignored `.tmp-codex-eval/` folder.

Core profile, local `qwen/qwen3.8-27b` Q4_K_M, 65,536-token window, temperature
0.7, top-p 0.8, top-k 20, two repeats, harness 8:

| Measure | Original | Revised |
|---|---:|---:|
| Strict passes | 20/20 | 20/20 |
| Semantic checks | 20/20 | 20/20 |
| Median peak prompt per case | 22,711 | 9,643 (−58%) |
| Median total prompt per case | 202,966 | 70,798 (−65%) |
| Median seconds per case | 86 | 47 (−46%) |

Core profile, ChatGPT subscription, `gpt-6-luna` at medium reasoning through
Codex CLI 0.159.3, one repeat, harness 9:

| Measure | Original | Revised |
|---|---:|---:|
| Strict passes | 10/10 | 10/10 |
| Median input tokens per case | 255,651 | 130,065 (−49%) |
| Median output tokens per case | 2,064 | 945 (−54%) |
| Median seconds per case | 23.0 | 15.5 (−33%) |

Hold-out profile, local Qwen as above, two repeats each, harness 11. Its cases
never shaped a prompt rule; the chain runs one feature through five fresh
sessions on one repository:

| Measure | Original | Revised |
|---|---:|---:|
| Strict passes | 12/12 | 12/12 |
| Semantic checks | 11/12 | 11/12 |
| Median peak prompt per case | 23,148 | 10,924 (−53%) |
| Median total prompt per case | 240,836 | 103,116 (−57%) |
| Median seconds per case | 104.9 | 69.9 (−33%) |
| Chain, total prompt per run | 1.66-1.70 M | 0.59-0.70 M (−61%) |
| Chain, seconds per run | 527-542 | 307-313 (−42%) |

The final payload through the subscription, core profile, two repeats,
harness 11: 20/20 strict, median input 142,433 tokens (−44% against the
original's 255,651), output 1,075 (−48%) and 16.0 s (−30%). Local Qwen ran the
core profile on the payload before the last notes and the frame-example rule,
harness 10: 20/20 strict, median peak prompt 9,945 and total 66,136. The
frame-example rule, the last change, ran on the six frame cases of both
profiles: Qwen 12/12 strict and 12/12 semantic, two repeats; the subscription
6/6 on the core frame cases, writing `N days` where the user gave no period.

The earlier rounds (harness 6-8) found what the compact text first lost, and
each finding became a general rule rather than a fixture clause: end every
session with `advance` or `pause` and never edit the State by hand; any stop
is a `pause`; validate corrects first and proves once, last; a `check` finding
is a prompt to look; frame writes the chosen path into the header when it
decides it; the `--supersedes` link is the mark, so earlier rulings stay as
written; branches are the developer's; `<command> --help` instead of reading
`aegis.py`; and `task` refuses a bare task ID. The same rounds widened three
scoring predicates that rejected correct behavior: labelled missing-evidence
statements, a tool name given as a program, and an unknown CLI command, which
are now unavailable capabilities rather than forbidden actions.

Harness 10 and 11 brought the hold-out profile into the loop. Its chain found
what a single-stage case cannot: a session that continued past a checkpoint
did the next stage's work without `advance`. The hold-out and subscription
runs also found hand edits that put CLI-owned records out of shape: a second
`requirements:` line hidden by the template's empty one, a free-text note
under Rulings, a Design reported but never written, and a reply that wrote its
own summary block instead of running `pause`. None became a refusal. `brief`
names the `advance` a waiting checkpoint needs; `log` notes a line recorded
before its stage; `pause` and `advance` note an empty stage section, a repeated
header key and Rulings lines that `ruling` did not write; a repeated key keeps
its first written value; the reply starts with the printed block; and a frame
example names an undecided value, such as `N days`, instead of choosing a
number, after both domains invented one. Harness 11 fixed two host defects
behind false failures: the hold-out and capability hosts refused `req`
category aliases the CLI accepts, and `git` repeated as its own first argument
counted as a forbidden write. A third transport effect, fixed in harness 12
after these measurements: `read_file` counted characters, and Qwen once paged
a 7 KB journal 60-400 characters at a time until the turn limit; it now reads
whole lines and reports `total_lines`, `eof` and `next_offset`.

Limits: one or two repeats per case are directional, not a reliability
estimate; the fixtures are synthetic; each route used one model. The hold-out
profile, whose cases never shaped a prompt rule, is the generalization check.

## Appendix A - Disposition of the current files

`AGENTS.md`, section by section (31.1 KB today, about 6 KB proposed):

| Section | Bytes | Disposition |
|---|---:|---|
| Philosophy | 565 | Keep two lines: advisory workflow, Git as the store |
| Scope | 428 | Keep |
| Stages | 716 | Keep the table, naming each card |
| Semantic analysis protocol | 3,250 | Keep the four labels; the analyze, challenge, write and audit cycle becomes each card's step list; quick path moves to frame; write zones become one authority line |
| Where everything lives | 2,006 | Five lines; cards name exact paths |
| Current project context | 3,816 | Three lines; detail moves to the frame and validate cards |
| Resume a task | 2,024 | `brief` prints what to read; two lines remain |
| Optional child tasks | 803 | On-demand `children.md` |
| Interaction modes | 5,274 | `pause` and `advance`; each card's finishing line carries its own choices |
| Journal log | 1,021 | Two lines and `log` |
| Verification efficiency | 1,260 | Build and validate cards |
| Rulings and handoffs | 1,465 | Two lines and the CLI help |
| Stage reporting | 4,339 | `pause` and `advance` print the summary; one line remains |
| Prompt cheatsheet | 2,298 | Human documentation only |
| Commands you will use | 1,172 | Each card names its commands; `--help` |

First stages:

| File | Today | Proposed |
|---|---|---|
| `1_frame.md` | 18.1 KB: 16-field card, 13 steps, recovery and checkpoint mechanics | About 5 KB: 10 fields, seven steps, the path table, one finishing command |
| `2_specify.md` | 8.9 KB: behavior inventory and a seven-column coverage table, nuanced atomicity | About 5 KB: one five-column table, a deterministic atomicity rule, the EARS and verification templates |
| `3_design.md` | 8.7 KB: 13 ordered headings, diagram gating and display rules, record mechanics | About 3 KB: five headings, one computed diagram line, one finishing command |
| `templates/task.md` | 18.5 KB, of which 15 KB of authoring rules | About 3 KB: section skeleton and content examples; state fields written by the CLI |

## Appendix B - Fixture-shaped clauses

| Location | Clause, abridged | Evaluation case |
|---|---|---|
| `1_frame.md:108-111` | Projecting a normalizer's input/output pair onto a new interface is inferred | `frame_new_interface` |
| `1_frame.md:115-118` | A request does not establish existing storage or accumulated data | `frame_ambiguous_retention` |
| `1_frame.md:128-136` | Automatic trigger versus cadence; destructive cleanup targets and recoverability | `frame_ambiguous_retention` |
| `1_frame.md:138-140` | Do not choose error responses, exit codes, formatting, thresholds or reversibility | retention, new interface |
| `1_frame.md:149-152` | Table: absent store; verification without external dependencies | retention, new interface |
| `1_frame.md:158-159` | A manual-only operation cannot satisfy automatic behavior | `frame_ambiguous_retention` |
| `1_frame.md:166-168` | Unknown age basis or threshold for eligibility | `frame_ambiguous_retention` |
| `1_frame.md:207-209`, `259-260` | Existing-contract quick fix IDs in the header; summary omits the restored requirement | `frame_existing_fix` |
| `1_frame.md:238-239` | Exit codes, argument ordering and output formatting affect the contract | `frame_new_interface` |
| `1_frame.md:244-247` | Ask the destructive-policy question first | `frame_ambiguous_retention` |
| `templates/task.md:120-133` | Missing historical red/anchor; fix already present means focused verification next | `task_stale_handoff`, `task_unrecorded_evidence` |
| `templates/task.md:149-155` | Supersede by appending; no backward annotation | `task_superseded_ruling` |
| `templates/task.md:156-166` | Problem versus desired outcome after the tree is fixed | `task_stale_handoff` |
| `5_validate.md:104-115` | A draft requirement may already describe accepted scope | `validate_review_exhausted` |
| `5_validate.md:139-143` | Existing tests can cover a restoration without a test-file diff | `validate_clean_checkpoint` |
| `AGENTS.md:409-417` | Shell unavailability is not a rejected file edit; per-operation permissions | evaluation host tool boundary |
