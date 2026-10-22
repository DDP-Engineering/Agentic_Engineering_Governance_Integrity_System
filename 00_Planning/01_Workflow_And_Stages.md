<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 01 - Workflow and stages

The workflow contract is the installed `.agentic/AGENTS.md` plus one step
file per stage. A task journal records the current stage and evidence; the
CLI does not advance stages on anyone's behalf.

## Scope and operating rule

Use AEGIS for software development that changes the product or tests;
documentation accompanying that implementation stays with the change.
Documentation-only updates in this repository are reviewed directly, outside
AEGIS, under the maintainer's scope instruction. Do not use it for repository-only work,
version assignment, delivery/package construction, publication, or deployment.
Those operations may carry an AEGIS-governed implementation, but are not
themselves a workflow task.

The workflow is advisory. A step can be skipped only by recording the reason
truthfully; `check` reports evidence gaps and configuration issues, while
`check --strict` is the optional CI enforcement boundary.

## Semantic analysis protocol

Frame, Specify, and Design use the shared **Analyze -> Challenge -> Write ->
Audit** cycle. The agent selects relevant evidence, challenges ambiguity and
contradictions, writes the durable stage artifact, and audits the result for
unsupported invention and missing coverage. Material claims are classified as
`STATED`, `OBSERVED`, `INFERRED`, or `UNKNOWN`; observed repository facts cite
paths. This records evidence and decisions without requesting hidden reasoning.

Classify clauses separately. `STATED` carries user words or a cited authoritative
clause without added conclusions. An inspected test definition is `OBSERVED`,
not an executed test. Projecting it into a new interface example is `INFERRED`
and needs its premises. A feature request proves neither a current defect nor
existing storage or accumulated data; unsupported current conditions stay unknown.

An unknown becomes a decision-blocking question only when implementation
cannot proceed safely without an answer. Other unknowns remain explicit in the
Frame, draft requirement/spec, or task design rather than being silently converted into
product behavior.

Save the Frame and pending questions before pausing. Unresolved destructive
targets or recovery policy block scope; permission to defer those questions is
not their answer. On resume, separate the reported Problem from the accepted
Desired outcome. Reuse the created journal after failed edits. An existing-contract
quick fix records governing requirement IDs at Frame.

## Ordinary lifecycle

| Stage | Step file | Implemented responsibility |
|---|---|---|
| `frame` | `steps/1_frame.md` | Read current project context and relevant environment references; analyze the idea and evidence; record scope, constraints, success signals, unknowns and proposed behavior in the Frame card. |
| `specify` | `steps/2_specify.md` | Build a behavior inventory and coverage table; map every atomic behavior to exactly one requirement; derive concrete positive, boundary and failure verification; add a spec for exact contracts that do not fit safely in requirement prose. |
| `design` | `steps/3_design.md` | Record the shortest sufficiently constrained, requirement-linked implementation path; scale depth with interface, state, trust, concurrency, migration and operational risk; preserve material open decisions in the task; draw optional diagrams for the human when `[diagrams] enabled = true`. |
| `build` | `steps/4_build.md` | Write and observe the expected failing test before implementation; carry out declared manual/inspection methods after the change; update traceability and affected context as implementation or setup changes. |
| `validate` | `steps/5_validate.md` | Reconcile project/environment context, component knowledge and active contracts with the candidate and authorized intent; retain proposals in task history; complete final strict verification after edits and review. |
| `deliver` | `steps/6_deliver.md` | Present the unchanged validated candidate, append the delivery report, and act only within granted Git/PR authority. |

A fix or change may take the quick path only when all frame criteria hold:

```text
frame -> build -> validate -> deliver
```

- No new externally observable behavior, interface, data format or dependency.
- An existing requirement already covers the behavior being changed.
- No security- or data-handling behavior is touched; those take the full path.

`frame` records `path: quick` and the eligibility reason. A small diff alone
does not qualify. The quick path does not remove validation, delivery proof,
or approval limits.

For automated requirements, build records the actual failing selector/command,
non-zero exit and expected missing-behavior reason before implementation.
An existing `Manual:` or `Inspection:` verification instead needs a recorded
observation after the change. For governed software work, anchor the starting
tree before implementation, then review evolution after the edits.

If the candidate changes after validation, return to `validate`. Deliver is
not a place to make unvalidated implementation changes.

Deliver compares current and proved candidates using the same binding method
and scope. A task-base diff describes the proposed changes, not edits since
validation. Missing comparable identity evidence requires a precise limitation
without asserting a change; a mismatch requires a saved return to Validate with
its checklist, Handoff and Stage report. Clear stale enabled-review verdicts
without resetting consumed rounds. This journal-only return does not authorize
source repair or verification beyond the requested scope.

For an unchanged proved candidate, save the approval pause before presentation:
header and both `current` fields remain Deliver, Handoff is waiting, Stage report
is paused with `needs_user: yes`, and both `next` fields name the delivery decision.
Reread records and show actual `summary` output before evidence and choices.
Preserve earlier Log text, including whitespace.

## Project-configured verification

`.agentic/context/project.md` describes the project's current purpose,
responsibilities, constraints and implementation entry points.
`.agentic/context/environment.md` links current setup and verification guidance.
Populate verified facts during frame or adoption, update affected sections when
facts change, and reconcile at validate. For a new project, add responsibilities
as they are implemented; draft/task records hold planned behavior.

Project documents, component pages and active requirements/specs state current
positive behavior, including meaningful security and failure responses. Journals,
Git and the changelog hold history. A conflict with an established requirement
calls for investigation or an authorized change, not a weaker replacement rule.
Missing or partial context is compatible with the advisory workflow.

Before testing in a new checkout, follow the project's documented readiness
checks from the environment guide and its canonical references for runtimes,
dependencies, services and working directory. Diagnose
missing prerequisites directly. AEGIS supplies no automatic installer or
framework-specific test adapter; setup stays within existing user authority.

During build, use the smallest native command that proves the behavior increment.
Where the configured runner honors selectors, preview and run with:

```text
python .agentic/aegis.py test --impacted --base HEAD --dry-run
python .agentic/aegis.py test --impacted --base HEAD --no-fallback
```

A preview executes nothing and is not proof. Unavailable selection with
`--no-fallback` exits without running tests; choose a focused project command
or defer full verification. The flag cannot make a runner that ignores selectors
focused. Existing callers without it retain full-suite fallback.

Schedule `check --task TASK-<id> --strict --run` after final edits and review.
Avoid a separate full `test` immediately beforehand or an impacted run that
expands to the same full suite. Relevant failures or subsequent candidate
changes require fresh proof. Ordinary prose corrections require semantic and
traceability review rather than an automatic extra runtime run. This scheduling
is agent guidance, not a CLI execution quota or a cache of reusable test results.

Current proof cannot recreate an unrecorded red result or build-start anchor.
Do not create an anchor at Validate to conceal that history gap. Leave an
unperformed evolution item unchecked with its applicability reason or remaining
limitation. Reading test assertions, finding linked tests and receiving static
check exit zero are not test passes. Existing executed tests may verify a repair
when their actual cases and results establish the restored contract.

## Interaction boundaries

Checkpoint mode is the default. It stops after every stage, presents the stage
report and three or four concrete choices, and waits before advancing. Choices
name the next stage, a specific revision or earlier-stage route, and pausing the
workflow. The delivery boundary separately requires explicit authority for the
stated commit or pull request.

The optional `[interaction] autopilot` Boolean in `.agentic/aegis.toml`
defaults to `false`, including when the table or key is missing. An invalid
value also fails safe to off. Autopilot flows between intermediate stages but
does not suppress external authority or the delivery boundary. New journals
record the resolved mode; an explicit user instruction may override the
configured default for that task. Neither child tasks, stage reporting,
rulings, handoffs, nor review adds a stop beyond these configured boundaries.

An explicit stage stop still applies in autopilot. A bounded transition with no
pending human decision may finish ready/completed with `needs_user: no`. Save
pauses or blockers before reporting; saved `next` fields name one action or
scoped decision, while the checkpoint menu belongs in the response.

### Optional Design diagrams

Require the TOML Boolean `[diagrams] enabled = true` and substantive Design.
Missing/non-list `types` defaults to `["structure"]`; `types = []` creates no file
or link. Unknown names are ignored; a list with no known type draws nothing.
The quick path or skipped Design draws nothing. Classify structure nodes from
proposed node edits independently of edges: a new connection does not make an
unchanged reused node changed.

Checkpoint responses show the actual fenced summary, every saved diagram heading
and complete Mermaid block, then choices. Autopilot saves diagrams and reports
their path in `changed`, without displaying blocks or adding a stop. An explicit
Design stop still completes applicable artifacts and keeps the header at Design;
it does not select checkpoint display.

Record material accepted deviations immediately and say them in the
conversation:

```text
DEVIATION <stage>: <what> - <why accepted, or what it costs>
```

A deviation exists only when the candidate, agreed scope, design or contract,
or confidence in required verification materially departs from what was
planned. Examples include retaining an implementation outside the agreed
design, weakening or skipping required verification, retiring a requirement,
accepting unexpected candidate files, or retaining unrequested work found in
review.

Corrected shell quoting, failed searches, rejected atomic patches, mistyped
paths, transient command failures, expected red tests, and unrelated findings
are operational details rather than deviations because they do not change the
candidate, scope, or evidence.

## Component knowledge discovery

`python .agentic/aegis.py components` gives agents a deterministic, read-only
list of component titles and repository-relative knowledge-page paths. Frame,
Specify, and Design use it when the relevant page is not already known;
Build and Validate use it only when an additional unnamed component is
discovered; adoption uses it to avoid duplicate pages. The command interprets
titles only, creates no registry or metadata, and leaves the page's Routing
section, exact source, and focused tests authoritative.

## Explicit review is policy, not a stage

The optional `[review]` configuration controls explicit review evidence:

```toml
[review]
enabled = false
max_fix_cycles = 2
```

When enabled, review records independent `spec_compliance` and
`implementation_quality` verdicts for the same candidate, using `approved` or
`changes_required`. A candidate change invalidates both verdicts while retaining
the consumed round and historical findings. The policy permits one
initial review plus up to `max_fix_cycles` fix-and-re-review rounds, then
requires human direction.

This source checkout has no installed policy; the example shows payload defaults.
An installed project's actual configuration determines whether review runs.
Disabling it skips only the explicit verdict contract and bounded loop; it
never skips semantic review, knowledge updates, full validation, strict checks,
or the delivery checkpoint.

Reviewers inspect current linked files, including untracked scope, and focused
proof due at that phase. Semantic corrections and current documentation precede
review; final full strict proof follows both approvals. Its pending checklist is
not itself a reason to reject a review. With `max_fix_cycles = 0`, only the initial
round is allowed. An unresolved final round needs the specific human scope/policy
decision; proposing an exception does not accept it.

## Durable resume state

The task journal is the durable history. Its append-only `## Log` is a compact
progress-and-evidence ledger, not an execution transcript. It records stage
transitions, material engineering or scope changes, consolidated verification,
blockers, approvals, deviations, and delivery outcomes. Routine tool use,
corrected retries, and detail already held by requirements, designs, Rulings,
Handoff, or the Stage report do not belong there. New journals also support:

- **Rulings:** append-only durable decisions; a later ruling supersedes an
  earlier ruling by ID instead of rewriting history.
- **Handoff:** one replaceable, stage-bound resume snapshot with `current`,
  `status`, `next`, `must_read`, and `blockers`.
- **Stage report:** one replaceable current snapshot of result, changes,
  evidence, issues, next action, and optional review fields.

Read task-template authoring guidance before Frame or Validate journal edits
unless already read in the intact session. Preserve the original legal prologue
and visible guide pointer. Append each material Log outcome once at the following
section heading without retyping prior evidence; compare its saved prefix with
the original before summary. Use plain one-line header/record values. Repair a
rejected edit in the same journal rather than creating another task.

Resume safely:

1. Run `python .agentic/aegis.py status` when the task ID is unknown.
2. Run `python .agentic/aegis.py brief TASK-<id>`.
3. Read the project profile and relevant environment sections when present,
   then the current step file and Handoff `must_read` paths. Confirm relevant
   claims against this checkout; context-file presence alone is not evidence.
4. Read the full journal wherever detail is omitted, stale, unresolved, or
   required by the current stage; then continue at the first unticked item.

`brief` never proves the recorded state is still true. `summary` is useful
after a stage report is written, but it is narrower still and never replaces
required journal, source, or evidence reads. In an intact session, reuse
unchanged instructions and documents already read. After compaction or lost
context, follow the resume procedure and required full reads. Step files point
to the shared reporting/resume contract. Handoffs still refresh at transitions,
pauses, blockers and session ends; update their short fields without repeating
the Frame, Design or Log.

## Executing through a host integration

The host's AEGIS agent or skill reads root guidance, the installed contract,
the named task's brief/journal and its current stage. A session-local task
pointer is only a convenience; restarting a host or changing branches requires
rechecking durable state. Codex bridge calls are stateless, so callers supply
the task identifier on each task-scoped operation.

Host `check` operations run static checks only. An advisory exit of zero is
not evidence that tests passed. Host `run` starts either a configured test
command or final `check --task ID --strict --run --json`, returning a job ID.
The coordinator polls `job`, reads the actual output and exit code, checks
whether the candidate changed during execution, and records the result.
Cancellation and interrupted-worker recovery retain enough state to inspect
uncertain processes before another run is allowed.

Claude's `SessionStart` and AEGIS-run `PreToolUse` hooks supply bounded context
and reminders. They do not write journal state, approve tools, run tests or
advance the task. Host review agents return evidence to the coordinator;
their verdicts do not substitute for final configured verification.

## Adoption and child tasks

Existing-repository adoption follows `steps/adopt.md`:

```text
survey -> components -> close -> done
```

Survey populates current project/environment context from verified repository
facts. Component sessions describe actual positive responsibilities and agreed
behavior from source and tests. Suspected defects and investigation evidence
belong in the journal; confirm intent before activating a disputed new
requirement and preserve existing contracts while investigating. Close reconciles
the context, knowledge pages and register. Adoption keeps its own lifecycle.

Large work may use optional one-level child tasks. A child keeps its own
journal, branch/base, requirements, evidence, validation, and delivery
checkpoint. The child has the only `parent:` link; creating it never rewrites
the parent. The parent validates the integrated candidate, and visibility is
limited to child journals present in the current checkout. A reviewer session
is not automatically a child task: review of a candidate and independently
scoped implementation work have different records and responsibilities.
