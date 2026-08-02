<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light 0.1.0

A **companion** governance system for agent-driven software development.
It gives any coding agent — a frontier CLI or a local small model — a
staged workflow with requirements, specs, tests, traceability and an
audit trail, without ever blocking the agent: no hooks, no gates, no
waivers. The workflow lives in plain instructions the agent reads; one
small stdlib-only CLI scaffolds artifacts and reports heuristic findings
the agent self-corrects against. The only hard gate is `check --strict`,
and only if a team wires it into CI.

AEGIS Light is a separate product from AEGIS 2.x (the enforcing stack).
It shares the ideas — staged lifecycle, durable requirements, linked
tests, focused regression — and none of the machinery.

## Goals

1. A good companion: advises, records, never blocks.
2. Simple to adopt: copy one folder, run `init`, read one page.
3. Stable: single-file CLI, standard library only (Python ≥ 3.11),
   plain-file artifacts that survive tool churn.
4. Windows and Linux, identical behavior.
5. Online and offline agents: Claude Code, Codex CLI, Qwen Code,
   OpenCode, or a local 32k-context model — all first-class operators.
6. Interruptible: any session can stop anywhere; a later session on any
   machine, with any model, resumes from the task journal.
7. Team-deployable: developers on separate branches and computers;
   one artifact = one file with collision-free IDs keeps merges clean.
8. Easy to understand: read `.agentic/AGENTS.md` once and you know the
   whole system.

## Install

Copy `template/.agentic/` into the target repository, then:

```bash
python .agentic/aegis.py init
```

`init` creates the data folders, a default `aegis.toml` (only if
absent — never overwritten), and digest-style pointer files
(`AGENTS.md`, `CLAUDE.md`, `QWEN.md`) at the repo root, appended under
markers without clobbering existing content. Commit, done. Edit
`.agentic/aegis.toml` to point `[commands] test` and `[layout]` at your
project.

Upgrade = copy the newer payload-owned files over (`AGENTS.md`,
`steps/`, `templates/`, `aegis.py`) and review the `git diff`. Your data
(`requirements/`, `specs/`, `tasks/`, `knowledge/`, `aegis.toml`) is
never part of the payload. Uninstall = delete `.agentic/` and the
pointer blocks.

## Use

Tell your agent:

```
using aegis workflow, implement feature X
```

The agent walks the stages — frame → specify → design → build →
deliver (small fixes: frame → build → deliver) — driven by one step
file per stage under `.agentic/steps/`. By default it pauses twice: after
`frame` (scope confirmation) and before the delivery commit/PR; say
"autopilot to deliver" to skip the first. Every decision, red test,
check finding and ticked checklist lands in the task journal
(`.agentic/tasks/TASK-<id>.md`) — the audit trail and the resume point.

## CLI

| Command | Purpose |
|---|---|
| `init` | Finish installation in a repo (idempotent). |
| `task new "<title>" [--type]` | Open a task journal. |
| `req new <category> "<title>"` | Scaffold a requirement file. |
| `status [TASK-id] [--all] [--json]` | List open tasks, or show one — the resume entry point. |
| `check [--task ID] [--run] [--strict] [--full] [--json]` | The 15-check heuristic catalog; advisory, always exits 0 — `--strict` (CI) exits 1 on errors and promoted warnings; `--run` also executes the configured verification commands. |
| `test [name] [--impacted] [--task ID]` | Run a configured command; `--impacted` runs only the tests linked to requirements the diff touches. |
| `report <task>` | Append the delivery summary to the task journal. |

**Machine-readable output.** `check --json` and `status --json` print one
JSON document on stdout — always complete (never capped), carrying a
`schema` integer so a consumer fails loudly on a contract change instead
of misparsing. Exit codes are unchanged, and under `--json` the live
`--run` progress goes to stderr so stdout stays parseable. A *usage or
configuration error* (unknown task id, unreadable config) is reported the
same way as in text mode — one line on stderr, exit 1, and **empty
stdout**: a consumer never receives a half-written document, but it must
treat empty stdout as an error rather than as an empty result.

## Layout (inside the adopting repo)

```
.agentic/
  AGENTS.md      the contract        steps/       one file per stage
  aegis.py       the CLI             templates/   scaffolding sources
  aegis.toml     the config          requirements/  specs/  tasks/  knowledge/
```

## Development

```bash
python -m pytest tests -q
```

The suite covers the CLI, all 15 checks against fixture repos (git and
git-less), the runner/report commands, and structural guards that keep
the philosophy honest: no hook/waiver/transaction machinery, stdlib-only
imports, advisory-by-default exit codes, license headers everywhere.

## License

PolyForm Noncommercial 1.0.0 — see `template/.agentic/LICENSE.txt`.
Commercial use requires a separate commercial license.
