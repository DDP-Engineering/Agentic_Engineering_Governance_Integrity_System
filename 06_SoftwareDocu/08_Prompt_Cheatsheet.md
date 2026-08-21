<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS — operator prompt cheatsheet

Copy-paste prompts for the operations you actually perform, one box each.
These are *operator* prompts — what a human types to start an operation.
The *agent-facing* cheatsheet (per-stage one-liners for small models)
lives in the payload itself, in `.agentic/AGENTS.md`.

Replace `<angle-bracket>` parts before sending. On Linux distributions
without a `python` alias, say `python3` in the prompts.

## Install on an existing project — via an agent

```
The AEGIS payload is at <path-to-release>/template/.agentic.
Copy it into this repository as .agentic/, run
python .agentic/aegis.py init, then edit .agentic/aegis.toml so that
[commands] test runs our real test suite and [layout] source/tests match
our real folders. Show me the resulting diff and stop — do not commit.
```

*What happens:* copy + `init` (data folders, default config, pointer
digests appended to `AGENTS.md`/`CLAUDE.md`/`QWEN.md`) + config tuning.
*Check afterwards:* the diff touches only `.agentic/` and the three
pointer files; your existing pointer content is preserved. Then commit
yourself — governance should not self-install silently.

## Set up a brand-new project

```
Create a new <language> project in this empty repository: git init, a
minimal skeleton with src/ and tests/ and one passing placeholder test.
Then install AEGIS from <path-to-release>/template/.agentic
(copy + python .agentic/aegis.py init), point .agentic/aegis.toml at the
skeleton's test command and folders, and stop before committing.
```

*Check afterwards:* `python .agentic/aegis.py check` reports `result: ok`
(or only NOTE lines if there is no merge base yet); the placeholder test
runs via `python .agentic/aegis.py test`.

## Adopt a project — via an agent

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
anything else happens — that review is the alignment moment.

## Work on a feature

```
using aegis workflow, implement: <what, for whom, and why>
```

Two stops by default: after `frame` (scope confirmation — the cheap
moment to say "not that, this") and before the delivery commit/PR.
Trust the scope already? Suppress the first stop:

```
using aegis workflow, autopilot to deliver: implement <what>
```

Autopilot suppresses the frame *stop*, not the agent's voice: anything it
deviates on still arrives mid-run as a one-line `DEVIATION <stage>: ...`
notice you do not have to answer.

*Watch during:* those notices — they are the first place you hear about an
anomaly, while it is still cheap to say something.
*Check afterwards:* the journal and its task sidecars have the whole story -
scope, exact red command and exit, pre-implementation `anchor`, final
`evolution`, findings, validation evidence, and report.

## Work on a quick fix

```
using aegis workflow, autopilot to deliver: fix <symptom, file if known,
how to reproduce>
```

*What happens:* `frame` decides quick vs full path (a "fix" that changes
intended behavior gets promoted to the full path — the journal says
which and why), then reproduce-first build, anchor after the expected failure,
record evolution after the fix, validate the final candidate, then deliver it.
One confirmation, at the PR — plus a `DEVIATION` line whenever the agent
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
"Manual:" or "Inspection:", is that still true — is the behavior really
unautomatable, or could a test be written now? Do the knowledge pages
still describe their
components truthfully? Are there draft requirements nobody finished,
journals stuck in an early stage for weeks, or delivered work with no
journal? Produce a findings list ordered by severity, each with a
one-line proposed fix. Change nothing yet.
```

*Why this exists:* `check` catches mechanical drift (links, formats,
duplicates); only a reading agent catches *semantic* drift — prose that
quietly stopped being true. Run it monthly, or before a release.
*Follow-up:* pick findings from the list and say "fix 1, 3 and 4" — each
non-trivial fix becomes a normal task with a journal.

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
catches the one kind of drift `check` cannot see — a hand-drawn picture
that quietly stopped being true.
*Follow-up:* "write the missing tests for &lt;component&gt;" or "redraw the
architecture for &lt;component&gt;" — each becomes a normal task.

## Ask what already governs a file (before changing unfamiliar code)

```
Before you change <path>, run python .agentic/aegis.py explain <path> and
tell me what already governs it: which requirements cover it, how each one
is verified, and which task journals delivered them. Then say whether what
I am about to ask for contradicts any of them. Change nothing yet.
```

*Why this exists:* the register is written once per behavior and read
almost never, because nothing led from a file back to it. This is that
direction. A path no requirement covers is said so plainly — and called a
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
On another machine: push the branch from the old machine first — the
journal travels with its branch, and the agent verifies the branch
matches the journal before touching anything.

## Reconcile after a merge

```
We just merged <branches>. Run python .agentic/aegis.py check and fix
every error it reports — duplicate requirement ids, dangling journal
references, stale affected_paths, unresolved specs — re-running until no
errors remain. List the warnings but fix only the mechanically obvious
ones. Summarize what you changed and what you left for a human.
```

*Check afterwards:* `check` shows `errors=0`; anything the agent left is
a conscious human decision, not a silent skip.
