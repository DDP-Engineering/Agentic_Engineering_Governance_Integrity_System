<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 03 — The companion CLI

One file: `.agentic/aegis.py`. Python ≥ 3.11 (for `tomllib`), stdlib only,
no install step — `python .agentic/aegis.py <cmd>` works on Windows and
Linux identically. Kept deliberately small and auditable, but there is no
enforced line ceiling — stability, simplicity of adoption and advisory
behavior are the goals, not a size number.

Design rule: **the CLI is a scaffolder and a reporter, never a gatekeeper.**
Every command exits 0 unless the command itself failed to run. The single
exception is `check --strict`, which is for CI.

## Commands

| Command | What it does |
|---|---|
| `aegis init` | Scaffold `.agentic/` into the current repo (docs, templates, `aegis.toml`); idempotent; this *is* the installer (decision D4). |
| `aegis status` | List open tasks with their stage; with a task ID, show its header, checklist state, and the last log lines. The resume entry point. |
| `aegis task new "<title>" [--type fix]` | Create `tasks/TASK-<id>.md` from the template with a fresh ID, current branch, today's date. |
| `aegis req new <category> "<title>"` | Create a requirement file with a fresh collision-safe ID; print the path. |
| `aegis check [--strict] [--run] [--task ID]` | Run the heuristic catalog (below); print a compact report. `--run` also executes the `[commands]` from `aegis.toml` and includes pass/fail. `--task` scopes diff-based checks to that task's branch. |
| `aegis test [name] [--impacted]` | Convenience runner for a configured command (`test` by default); appends one result line to the task log if a task is named. `--impacted` runs only the focused regression set (below). |
| `aegis report <task>` | Generate the delivery summary (requirements touched, diff stats, check results, checklist state) and append it to the task journal. |

Not included, on purpose: stage transition commands (edit one line in the
journal), waiver commands, evidence commands, adoption commands, doctor,
upgrade machinery (upgrading = re-running `init` from a newer payload and
reviewing the diff — git is the safety net).

## Deployment: init, upgrade, ownership

There is no installer product (decision D4): install = copy
`template/.agentic/` into the repo + `python .agentic/aegis.py init` +
commit. `init` does what a copy cannot:

- Create-or-append the root pointer files (`AGENTS.md`, `CLAUDE.md`,
  `QWEN.md`), respecting existing content. A pointer is a **digest, not
  just a link** (~15 lines: stage one-liners, the resume procedure, the
  path to `.agentic/AGENTS.md`) — a small model that never follows the
  reference still lands the essentials.
- Write a default `aegis.toml` **only if absent** — never overwrite.
- Create the data folders.

Ownership split — the invariant that makes upgrades safe:

- **Payload-owned** (overwrite freely on upgrade): `AGENTS.md`, `steps/`,
  `templates/`, `aegis.py`.
- **User data** (never present in the payload, never touched):
  `requirements/`, `specs/`, `tasks/`, `knowledge/`.
- **Mixed**: `aegis.toml` only — both the copy step and `init` must leave
  an existing one alone.

Upgrade = copy the new payload over, `git diff`, review, commit.
Undo/uninstall = `git restore` / delete `.agentic/` and the pointer
lines. Payload authenticity is the release archive's checksum, verified
once at download — no runtime verification machinery.

## The heuristic check catalog

Each check emits findings at two levels: **warn** (heuristic signal) and
**error** (the file is objectively broken). `--strict` fails only on
errors plus a configurable promotion list.

Format checks (error level):
1. Every requirement TOML parses and has the six required fields.
2. IDs match their filename and category folder; duplicate IDs across the
   tree (the post-merge safety for decision D2).
3. Task journal headers parse; `requirements:` IDs exist.
4. `spec` references resolve to existing files.

Traceability heuristics (warn level):
5. Changed source files (diff vs merge base) not covered by any
   requirement's `affected_paths`.
6. Active requirements with empty `linked_tests`, or linked test files
   that do not exist.
7. Requirements whose `affected_paths` no longer exist on disk (stale).
8. A task in `build`/`validate`/`deliver` whose diff is non-empty but whose linked
   requirements are all untouched (possible scope drift).

Hygiene heuristics (warn level):
9. Secret-pattern grep over the diff (small built-in pattern set plus
   `aegis.toml` extras) — the only survivor of the hook suite (D3).
10. Ticket/run-ID patterns inside requirement prose (self-containment
    rule).
11. Journal in `deliver` with unticked checklist items.
12. Files written outside `source`/`tests`/`.agentic` globs in the diff
    (the write-zone guard, demoted to a report line).
13. Diff modifies source files but modifies no files matching the `tests`
    globs ("source changed with no test changes" — the cheapest TDD
    signal; promotable in strict mode).

Output: one line per finding, `LEVEL  CHECK  path — message`, then a
two-line summary. Plain text, ≤ 100 columns, no color codes by default —
made to be read by small models as much as by humans.

## Focused regression (impacted-test selection)

The same mapping the traceability heuristics use (doc 02) is driven in
reverse to select a regression set, exactly as heavy AEGIS's impact
selection did — but as a convenience, not a gate:

1. Changed files = git diff against the merge base (or `--task`'s branch).
2. Requirements whose `affected_paths` match any changed file are the
   impacted requirements.
3. The union of their `linked_tests` is the focused regression set.

`aegis test --impacted` substitutes that set into a template command from
`aegis.toml`:

```toml
[commands]
test = "pytest -q"
test_impacted = "pytest -q {tests}"   # {tests} = space-joined linked_tests
```

Fallbacks keep it safe and simple: if `test_impacted` is not configured,
or the focused set is empty (no requirement covers the changed files —
which check #5 flags anyway), the full `test` command runs instead, with a
note saying why. The intended rhythm: `--impacted` during `build` for the
fast inner loop, the full suite once at `deliver`.

## CI strict mode (the only hard gate, opt-in)

```
python .agentic/aegis.py check --strict --run
```

in a PR pipeline turns errors (and promoted warnings, via
`[check] strict_promote = ["no-linked-tests", ...]` in `aegis.toml`) into
a failing build. This is where governance actually bites in AEGIS Light:
at the merge boundary, visible to the whole team, instead of at every
keystroke of one agent.

## Explicitly out of scope

No hooks and no adapter wiring (`settings.json`/`hooks.json` are not
touched — nothing to fail closed, nothing for Codex to distrust). No
network access. No state outside the repo tree.

**JSON output** was deferred in 0.1.0 pending "a real consumer"; that
condition was met, so `check --json` and `status --json` now exist. The
contract: one document on stdout, always complete (the human-facing
finding cap does not apply), a `schema` integer in every envelope so a
consumer can refuse an unknown version rather than misparse, exit codes
identical to text mode, and `--run` progress routed to stderr so stdout
stays a single parseable document. It is a second renderer over the same
data structures, not a parallel code path — and a structural test
asserts every `--json` invocation yields exactly one valid document.
