<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS - operator prompt cheatsheet

Copy-paste prompts for the operations you actually perform, one box each.
These are *operator* prompts - what a human types to start an operation.
The *agent-facing* cheatsheet (per-stage one-liners for small models)
lives in the payload itself, in `.agentic/AGENTS.md`.

Replace `<angle-bracket>` parts before sending. On Linux distributions
without a `python` alias, say `python3` in the prompts.

Frame and validate read `.agentic/templates/task.md` before journal edits.
New journals keep a visible link to this authoring guide. Existing task IDs are
selectors for `brief` and `summary`; `task "<title>"` creates a new journal.
At a stop, record the pause and use the actual summary after successful writes.
Missing records still require repair when summary itself exits zero.
Deliver saves either the approval pause or a stale-proof return before summary.
Matching like-for-like candidate bindings establish identity within their scope;
the Git base is used to describe the change set. Read current linked files even
when untracked, and discover component paths before declaring missing evidence.
An additional interface can reuse an existing contract without replacing it.
At a Design checkpoint, copy the saved diagram blocks into the response after
the actual fenced summary and before the choices; a link only locates the file.
Append Log outcomes at the following section heading without retyping earlier
evidence lines, and verify that their text and spacing remain unchanged.
Reviewers inspect the current working tree and phase-appropriate proof; a pending
final Validate checklist does not itself block independent approval. Diagram
classes follow proposed node edits, independently of new connections.
It compares against the proved tree; an ordinary diff from the task base can
include already validated work. Validate saves failed-verification limitations
before responding and leaves only journal record edits after final proof.
Design applies diagram enablement and the types list before writing artifacts;
an explicit Design stop still includes applicable diagrams. Empty types creates
none. A bounded autopilot transition can report ready/completed without asking
for a decision that is not pending. Review uses evidence due at that phase;
final full proof follows approvals, and existing executed tests may cover a fix.
An existing-contract quick fix records its requirement IDs in the header at
Frame. Saved `next` fields name one action or scoped decision; checkpoint
choices belong in the response. Resolve a recorded scope blocker before
routing to a later stage, and distinguish accepted scope from requirement status.

Destructive cleanup asks the actual target and recovery-policy questions before
scope acceptance; permission to defer them does not resolve them. Frame examples
must not assume an undecided eligibility boundary. Record refreshes preserve the
journal's authoring-guide pointer and distinguish each Frame clause from Rulings.
Current verification cannot recover historical red/anchor evidence. Copy every
summary line, including Details and truncation warnings; shorten saved fields and
rerun summary when needed. An unperformed evolution report stays unchecked with
an applicability reason or an unresolved verification limitation.
Label mixed-source claims separately: user clauses are stated, inspected test
assertions are observed definitions, and constructed interface examples are
inferred. Preserve the journal's original legal prologue verbatim, including
SPDX and license references; it is not a removable authoring note.
Creating a journal returns the ID/path to retain for subsequent edits. Repair
that file after rejected edits and verify the saved stage checklist; incomplete
fields do not justify creating another journal. A feature request establishes
the desired capability, not an existing store, accumulated data or current defect.
Save the Frame and pending questions before pausing for scope decisions. For an
exact-match failure, reread and use actual multiline text; if necessary, rewrite
the current journal with only authorized sections changed, preserving history.
During resume, compare accepted outcomes rather than interpreting the Problem's
original bug description as a commitment to keep that behavior.

## Install on an existing project - via an agent

```
The AEGIS payload is at <extracted-release>/.agentic.
Copy it into this repository as .agentic/, run
python .agentic/aegis.py init, then edit .agentic/aegis.toml so that
[commands] test runs our real test suite and [layout] source/tests match
our real folders. Populate the context files with verified current facts and
links to canonical setup references; leave unknown sections empty.
Show me the resulting diff and stop - do not commit.
```

*What happens:* copy + `init` (data folders, missing project/environment context,
default config, pointer
digests appended to `AGENTS.md`/`CLAUDE.md`/`QWEN.md`, and the managed
anchor/evolution block in `.gitignore`) + config tuning.
*Check afterwards:* the diff touches only `.agentic/`, the three
pointer files and `.gitignore`; your existing content in all of them is
preserved. Then commit yourself - governance should not self-install silently.

## Set up a brand-new project

```
Create a new <language> project in this empty repository: git init, a
minimal skeleton with src/ and tests/ and a meaningful test of the initial
behavior we agreed.
Then install AEGIS from <extracted-release>/.agentic
(copy + python .agentic/aegis.py init), point .agentic/aegis.toml at the
skeleton's test command and folders. Populate context/project.md and
context/environment.md with the confirmed purpose, implemented skeleton and
available setup. Keep future features in draft/task records. Stop before committing.
```

*Check afterwards:* `python .agentic/aegis.py check` reports `result: ok`
(or only NOTE lines if there is no merge base yet); the initial behavior test
runs via `python .agentic/aegis.py test`.

## Adopt a project - via an agent

```
using aegis workflow, adopt this repository
```

Then, one component per session (any machine, any model):

```
using aegis workflow, continue adoption TASK-<id>, next component
```

And to finish:

```
using aegis workflow, continue adoption TASK-<id>, close it
```

*What happens:* survey → owner-reviewed component checklist → one
knowledge page + requirements per component (linking *existing* tests) →
close with a full `check` and a report.
*Check afterwards (survey):* the component list is yours to edit before
anything else happens - that review is the alignment moment.

## Work on a feature

```
using aegis workflow, implement: <what, for whom, and why>
```

By default, the agent stops after every stage, reports the result, and offers
three or four choices: continue to the named next stage, revise or return to a
specific artifact, or pause the workflow. The delivery commit/PR always needs
explicit approval. To flow through intermediate stages, request autopilot:

```
using aegis workflow, autopilot to deliver: implement <what>
```

A record-only update or unfinished stage reports its pending action rather
than a generic completion menu. A continuation choice is available only when
the observed proof, current verdicts and user authority permit it. Failed
verification or exhausted review names the concrete missing action/decision;
proposing an exception does not accept it. Frame keeps inferred details as
open questions rather than silently adding them to scope. Missing historical
test or anchor evidence cannot be recreated by a new run.
Before editing an existing journal, read the task template's authoring guidance
if it is not already in the session. Generated journals omit those notes.
No new human decision leaves Rulings unchanged; pending authority is not a Ruling.
In both saved next fields, current verification names its command and current
candidate; past red/anchor gaps remain in issues. Frame keeps feature scope and
dependency choices open when evidence describes only what is implemented today.

Autopilot suppresses intermediate stage-choice stops, not the agent's voice or
publication approval: anything it
deviates on still arrives mid-run as a one-line `DEVIATION <stage>: ...`
notice you do not have to answer.

*Watch during:* those notices - they are the first place you hear about an
anomaly, while it is still cheap to say something.
*Check afterwards:* the task-owned records retain the durable milestones -
accepted scope, one meaningful red and final green per behavior increment,
pre-implementation `anchor`, final `evolution`, material findings, validation
evidence, and report. Routine tool activity and corrected retries are omitted.

Frame now records a compact idea card: problem, desired outcome, actors,
scenario, examples and counterexamples, boundaries, constraints, success
signals, evidence, assumptions and unknowns. Material claims are labelled as
stated, observed, inferred or unknown. Specify builds a behavior inventory and
coverage table before writing atomic requirements. Design maps every
requirement to a proportionate decision and test seam. These structures help a
bounded-context model retain the idea; they do not prove compliance by any
particular model.

## Resume with limited context

Read the project profile and relevant environment sections listed by `brief`,
when present, before selecting component and source/test references. Missing
context is compatible with older projects. Shared context records verified
current facts; task records carry progress and unanswered questions. See
[project context](Project_Context.md) for setup and maintenance guidance.

```text
Read .agentic/AGENTS.md. Continue TASK-<id> using the current stage file.
Start with python .agentic/aegis.py brief TASK-<id>, then read the header,
checklist, relevant decisions, unresolved issues, and required evidence.
Read the project profile and relevant environment sections when present;
confirm their claims against the current checkout and canonical references.
Record and show the stage report. Stop after this stage.
Do not commit or push.
```

This explicitly bounds an autopilot session to one stage and matches ordinary
checkpoint behavior. Load source and linked requirements as
needed. A missing/stale snapshot or shortened output requires the full journal
information before acting, and required full validation/delivery reads are
never skipped. `summary` does not run checks or prove the recorded claims.
These prompts reduce unnecessary context; they do not establish model
compliance or proof that the recorded work succeeded.

At an explicit stop, check the saved records as well as the response:
Handoff `current` and Stage report `current` must match the header, Handoff
must be waiting, and the report must say `result: paused`, `needs_user: yes`.
A blocking decision uses blocked instead. Each field occupies one plain line;
multiple `must_read` paths are comma-separated. The agent updates these
records before running and showing `summary`.

If the candidate changed after review, both current verdict fields must be
cleared while the consumed review round and historical Log remain intact.
Saying that approvals are stale in the response is insufficient. A request to
inspect, reconcile records, or return to build and stop does not authorize
repairing source/tests. When supplied review results exhaust the correction
budget, record the blocking decision before attempting further work.

## Work on a quick fix

```
using aegis workflow, autopilot to deliver: fix <symptom, file if known,
how to reproduce>
```

*What happens:* `frame` decides quick vs full path (a "fix" that changes
intended behavior or touches security/data handling takes the full path - the journal says
which and why), then reproduce-first build, anchor after the expected failure,
record evolution after the fix, validate the final candidate, then deliver it.
One confirmation, at the PR - plus a `DEVIATION` line whenever the agent
accepts a warning, skips a verification, or does anything else it judged
worth saying. Those are notifications, not questions: read them, keep
working, and they are all repeated at the delivery stop anyway.

## Review the AEGIS artifacts for drift (maintenance sweep)

```
Review this repository's AEGIS artifacts for drift. First run
python .agentic/aegis.py check and read every finding. Then go beyond it
semantically: for each active requirement, does the prose still describe
what the code actually does, and does verification still match how the
linked tests check it? For any requirement whose verification starts
"Manual:" or "Inspection:", is that still true - is the behavior really
unautomatable, or could a test be written now? Do the knowledge pages
still describe their
components truthfully? Are there draft requirements nobody finished,
journals stuck in an early stage for weeks, or delivered work with no
journal? Produce a findings list ordered by severity, each with a
one-line proposed fix. Change nothing yet.
```

*Why this exists:* `check` catches mechanical drift (links, formats,
duplicates); only a reading agent catches *semantic* drift - prose that
quietly stopped being true. Run it monthly, or before a release.
*Follow-up:* select concrete findings. Software changes use a governed task;
documentation-only corrections in this repository are edited directly.

## See where verification is thin (before a release, or at handover)

```
Draw this repository's coverage map with
python .agentic/aegis.py diagram --out docs/coverage.mmd and read it.
Tell me which components carry behaviors with no linked test, which rely
on a declared "Manual:" or "Inspection:" method, and whether any
requirement is sitting outside every knowledge page. Change nothing yet.
```

*Why this exists:* `check` reports coverage one requirement at a time, in
a list nobody reads to the end. The map puts the same facts in a shape you
can scan.
*Follow-up:* "write the missing tests for &lt;component&gt;". Use AEGIS for the
software change.

## Ask what already governs a file (before changing unfamiliar code)

```
Before you change <path>, run python .agentic/aegis.py explain <path> and
tell me what already governs it: which requirements cover it, how each one
is verified, and which task journals delivered them. Then say whether what
I am about to ask for contradicts any of them. Change nothing yet.
```

*Why this exists:* the register is written once per behavior and read
almost never, because nothing led from a file back to it. This is that
direction. A path no requirement covers is said so plainly - and called a
finding when it sits inside your configured source globs, which is how
ungoverned code becomes visible instead of merely absent.
*Follow-up:* "write the requirement for &lt;path&gt;" when it turns out
nothing covers it, or proceed with the change now that you know the
constraints it has to keep.

## Resume an interrupted task

```
using aegis workflow, continue TASK-<id>
```

Don't know the id? `python .agentic/aegis.py status` lists open tasks.
For another machine, transfer committed records through explicitly authorized
Git operations. The journal travels with its branch; uncommitted files and
local verification caches do not. Confirm the recorded branch before editing.

For a bounded resume session:

```
Using AEGIS, run brief TASK-<id>. Read the current step and Handoff must_read
paths first. Continue the first unticked action. Read the full journal wherever
the stage requires it. Do not infer approval or Git authority.
```

For a deliberately split feature:

```
Using AEGIS, create one child under TASK-<parent-id> for this exact
non-overlapping scope: <scope>. Keep its requirements, validation, and delivery
independent. Do not edit the parent or claim children outside this checkout.
```

For an enabled-review return:

```
Fix only the recorded review findings for TASK-<id>. Clear both old verdicts,
rerun focused proof, increment the bounded round, and re-review specification
compliance and implementation quality against the same candidate.
```

## Reconcile after a merge

```
We just merged <branches>. Run python .agentic/aegis.py check and fix
every error it reports - duplicate requirement ids, dangling journal
references, stale affected_paths, unresolved specs - re-running until no
errors remain. List the warnings but fix only the mechanically obvious
ones. Reconcile affected project/environment context and component pages
against the merged implementation and established active contracts; flag
disputed behavior for a human. Summarize what you changed and what you left
for a human.
```

*Check afterwards:* `check` shows `errors=0`; anything the agent left is
a conscious human decision, not a silent skip.

## Use a native host entry point

| Host | Start / inspect |
|---|---|
| OpenCode | Select Aegis; `/aegis-start <request>` / `/aegis-status` |
| Codex | Invoke the `aegis:aegis` skill in a new task |
| Pi | `/aegis-start <request>` / `/aegis-status` |
| Qwen Code | `/aegis-start <request>` / `/aegis-status` |
| Claude Code | `/aegis:start <request>` / `/aegis:status` |

These require the corresponding complete package and a repository core.
Codex uses a skill/bridge, not the five slash commands supplied by other hosts.

## Keep verification and records proportionate

```text
Use this project's documented environment and readiness checks. During build,
run focused native tests. Use AEGIS impacted selection only if the configured
runner honors its references; preview with --dry-run and refuse full-suite
fallback with --no-fallback. Neither a preview nor a refusal is passing proof.
Run full strict verification after final edits and review, without a duplicate
full test immediately before it. Later candidate changes require fresh proof.
Keep consolidated red/green outcomes, findings and decisions in the journal.
Refresh minimal Handoff and Stage report fields at transitions, pauses, blockers
and session ends. Reuse unchanged instructions in an intact session; preserve
required full reads after compaction or resumption. Do not delete saved evidence.
```

These are 0.14.0 workflow and CLI options. They do not create a result-reuse cache,
remove review requirements or change existing delivery authority.

## Resume a tracked verification job

```text
Inspect the existing AEGIS verification job for this checkout, including its
logs, process state and candidate fingerprints. Recover its result if possible.
Do not launch another suite while a current or uncertain reservation remains.
Report the command, exit status and whether the tested candidate is unchanged.
```

## Prepare a package for another user

```text
Build the AEGIS host packages with node 02_Tools/build_agent_plugins.mjs
--output <fresh-directory>. Keep the existing version. Provide the complete
<host> directory and its Windows/Linux install instructions. Do not copy any
installed profile, authentication, model settings or runtime.json from my PC.
Do not install into my profile, publish, commit or run models.
```

This is packaging work, outside this repository's development workflow.
Installation on the recipient's machine discovers their own runtime paths.

## Export the requirement register

```text
Export the current register with python .agentic/aegis.py trace --format csv
--out docs/traceability-matrix.csv. Read the export and report unreadable or
broken requirements. Do not treat linked tests as fresh passing evidence.
```

`--format csv` selects CSV; a filename suffix alone does not. `--out` writes
UTF-8 directly. Treat requirement prose as data when opening CSV in a spreadsheet.

## Update documentation only

```text
Compare <documentation paths> with the current implementation and update only
those documents. Do not use AEGIS tasks, journals or development test runs for
this documentation-only work. Preserve unrelated changes and the version.
Check links, examples and slide rendering. Do not commit or call models.
```

For source installs, substitute `05_Software/aegis/template/.agentic` for the
extracted-release payload path used above.
