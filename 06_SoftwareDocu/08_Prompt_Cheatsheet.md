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

## Install on an existing project - via an agent

```
The AEGIS payload is at <extracted-release>/.agentic.
Copy it into this repository as .agentic/, run
python .agentic/aegis.py init, then edit .agentic/aegis.toml so that
[commands] test runs our real test suite and [layout] source/tests match
our real folders. Show me the resulting diff and stop - do not commit.
```

*What happens:* copy + `init` (data folders, default config, pointer
digests appended to `AGENTS.md`/`CLAUDE.md`/`QWEN.md`) + config tuning.
*Check afterwards:* the diff touches only `.agentic/` and the three
pointer files; your existing pointer content is preserved. Then commit
yourself - governance should not self-install silently.

## Set up a brand-new project

```
Create a new <language> project in this empty repository: git init, a
minimal skeleton with src/ and tests/ and a meaningful test of the initial
behavior we agreed.
Then install AEGIS from <extracted-release>/.agentic
(copy + python .agentic/aegis.py init), point .agentic/aegis.toml at the
skeleton's test command and folders, and stop before committing.
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

Two stops by default: after `frame` (scope confirmation - the cheap
moment to say "not that, this") and before the delivery commit/PR.
Trust the scope already? Suppress the first stop:

```
using aegis workflow, autopilot to deliver: implement <what>
```

Autopilot suppresses the frame *stop*, not the agent's voice: anything it
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

```text
Read .agentic/AGENTS.md. Continue TASK-<id> using the current stage file.
Start with python .agentic/aegis.py brief TASK-<id>, then read the header,
checklist, relevant decisions, unresolved issues, and required evidence.
Record and show the stage report. Stop after this stage.
Do not commit or push.
```

This explicitly bounds the session to one stage; it does not change ordinary
checkpoint or autopilot behavior. Load source and linked requirements as
needed. A missing/stale snapshot or shortened output requires the full journal
information before acting, and required full validation/delivery reads are
never skipped. `summary` does not run checks or prove the recorded claims.
These prompts reduce unnecessary context; they do not establish model
compliance or proof that the recorded work succeeded.

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
requirement is sitting outside every knowledge page. Then, for each
component you flagged, open its knowledge page and tell me whether its
"## Architecture" diagram still matches the code. Change nothing yet.
```

*Why this exists:* `check` reports coverage one requirement at a time, in
a list nobody reads to the end. The map puts the same facts in a shape you
can scan, and asking about the architecture diagrams in the same pass
catches the one kind of drift `check` cannot see - a hand-drawn picture
that quietly stopped being true.
*Follow-up:* "write the missing tests for &lt;component&gt;" or "redraw the
architecture for &lt;component&gt;". Use AEGIS for the software change;
a documentation-only redraw is direct maintenance in this repository.

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
ones. Summarize what you changed and what you left for a human.
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
