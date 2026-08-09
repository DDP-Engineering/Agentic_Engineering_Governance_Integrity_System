<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light — operator prompt cheatsheet

Copy-paste prompts for the operations you actually perform, one box each.
These are *operator* prompts — what a human types to start an operation.
The *agent-facing* cheatsheet (per-stage one-liners for small models)
lives in the payload itself, in `.agentic/AGENTS.md`.

Replace `<angle-bracket>` parts before sending. On Linux distributions
without a `python` alias, say `python3` in the prompts.

## Install on an existing project — via an agent

```
The AEGIS Light payload is at <path-to-release>/template/.agentic.
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
Then install AEGIS Light from <path-to-release>/template/.agentic
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

*Check afterwards:* the journal (`.agentic/tasks/TASK-<id>.md`) tells the
whole story — scope, red-test line, findings, report.

## Work on a quick fix

```
using aegis workflow, autopilot to deliver: fix <symptom, file if known,
how to reproduce>
```

*What happens:* `frame` decides quick vs full path (a "fix" that changes
intended behavior gets promoted to the full path — the journal says
which and why), then reproduce-first build, then deliver. One
confirmation, at the PR.

## Review the AEGIS artifacts for drift (maintenance sweep)

```
Review this repository's AEGIS Light artifacts for drift. First run
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
