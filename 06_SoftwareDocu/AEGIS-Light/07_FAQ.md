<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light — FAQ

## What if the agent just ignores the workflow?
Then it can — nothing stops it, and that is a design decision, not a
gap. What you get instead of prevention is *visibility*: a task with no
journal, a journal with no red-test line, a diff with no test changes —
all of it shows up in one `aegis check` run and in the journal (or its
absence) at review time. In practice, agents given clear numbered step
files follow them; the ones that don't leave fingerprints. And if your
team wants a real stop, that's what `check --strict` in CI is for — at
the merge, visible to everyone, not in the agent's inner loop.

## How is this different from AEGIS 2.x?
Same ideas — staged lifecycle, durable requirements, linked tests,
focused regression, delivery reports. None of the machinery: no hooks,
no gate modes, no waivers, no evidence forms, no run store, no
schema-3 policy file. 2.x *enforces* (and is the right tool where
enforcement is a requirement); Light *advises and records*. They are
separate products; Light is not an upgrade path.

## Which agents and models work?
Anything that can read a file and run a shell command: Claude Code,
Codex CLI, Qwen Code, OpenCode, or a bare local-model harness. The
workflow is deliberately sized so one stage of one task fits a
32k-context local model (Qwen3-27B, gpt-oss-20B class): the docs an
agent must read for one step total under ~9k tokens. A common split:
frontier model for frame/specify/design, local model for build.

## Can I stop mid-task and continue later / elsewhere / with another model?
Yes — that is the core mechanic, not a feature. The journal
(`.agentic/tasks/TASK-<id>.md`) is the only run state and it is
committed. On another machine: push the branch from the old machine,
then `git fetch`, check out the task branch the journal records, run
`python .agentic/aegis.py status`, open the stage's step file, and
continue at the first unticked checklist item.

## Does it work without git?
Yes, degraded: the five diff-based checks report one NOTE line each and
skip; everything else (formats, links, journals, commands) still works.
With git but no remote: fully functional — the diff basis is the merge
base against your local `master`/`main`.

## Does it phone home / need the network?
No. Stdlib-only Python, no network calls, no state outside your repo.
Offline is a first-class environment.

## Windows or Linux?
Both, identically — same commands, same outputs. Generated files use LF
and forward slashes everywhere, so mixed-OS teams don't churn diffs.

## What does `check` actually check?
Fifteen heuristics: five error-level (broken TOML, id mismatches and
duplicates, unparseable journals, dangling spec references, and `--run`
having executed nothing at all) and ten warning-level (uncovered changed
source, missing linked tests, stale paths, scope drift, secrets in the
diff, ticket references in requirement prose, unticked deliver
checklists, files outside the layout, source changed without test
changes, and malformed `aegis.toml` keys). `check --help` lists every
slug. It always exits 0; only `--strict` (CI) turns errors and promoted
warnings into a failing exit.

## Do I have to write requirements for everything?
No. Adopt incrementally (doc 05), or not at all for areas you never
touch. The `uncovered-source` warning tells you when a change lands in
an area with no requirement — that's a signal to add one, not a
punishment.

## What are the pauses? Can I turn them off?
Two by default: after `frame` (scope confirmation) and before the
delivery commit/PR. Say "autopilot to deliver" and only the pre-PR stop
remains. The pauses are conversational instructions, not mechanisms —
your agent CLI's own permission system is unaffected and unchanged.

## Can another tool consume this?
Yes: `check --json` and `status --json` print one JSON document on
stdout — always complete (the human-facing finding cap never applies),
with a `schema` integer so your integration fails loudly on a contract
change instead of misparsing. Exit codes are identical to text mode, and
`--run` progress goes to stderr so stdout stays parseable. Parse that
rather than scraping the human output.

## Is my data locked in?
It's markdown and TOML in your repo. Deleting `.agentic/` is a complete
uninstall; keeping just `requirements/` as documentation is also fine.
There is nothing proprietary to migrate out of.

## Where do I report a gap between these docs and the behavior?
The behavior is defined by the payload (`AGENTS.md`, the step files,
`aegis.py --help`); these docs are the guided tour. If they disagree,
the payload wins — and the doc gets fixed.
