<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS — folders and files

Everything AEGIS knows is a plain file committed to your branch.
One artifact = one file. No database, no run store, no state outside the
repo. This page tours `.agentic/` with a filled-in example per format.

```
.agentic/
  AGENTS.md        the contract your agent reads      (payload)
  CLI.md           complete CLI reference             (payload)
  aegis.py         the CLI                            (payload)
  LICENSE.txt      license text                       (payload)
  steps/           one instruction file per stage     (payload)
  templates/       scaffolding sources                (payload)
  aegis.toml       your configuration                 (yours)
  requirements/    the durable contracts              (yours)
  specs/           optional per-requirement specs     (yours)
  tasks/           journals + anchor/evolution state  (yours)
  knowledge/       one page per component             (yours)
```

The split matters: **payload** files are replaced on upgrade; **yours**
are never shipped in a payload and never overwritten.

## Requirements — `requirements/<category>/REQ-<CODE>-<id>.toml`

One file per independently verifiable behavior. Eight category folders:
`functional/ ux/ nfr/ security/ data/ platform/ reliability/ test/`
(codes FUNC, UX, NFR, SEC, DATA, PLAT, REL, TEST). The random 8-hex id
suffix makes collisions between branches statistically irrelevant, and
creation is exclusive — two racing processes cannot silently produce the
same file. (Examples in these docs use short ids for readability.)

```toml
schema = 1
id = "REQ-FUNC-3fa2"
title = "Export playlist as M3U"
status = "active"            # draft | active | retired
requirement = """
Exporting a playlist writes one M3U file containing every track path,
in playlist order, using forward slashes on all platforms.
"""
verification = "Run the linked test; it round-trips a 3-track playlist."
affected_paths = ["src/export/m3u.py"]
linked_tests = ["tests/export/test_m3u.py::test_roundtrip"]
spec = "specs/REQ-FUNC-3fa2.md"   # optional
created = 2026-08-02
updated = 2026-08-02
```

Write the prose self-contained — no ticket numbers, no "see TASK-1234"
(`aegis check` flags those patterns).

**When no test can settle it.** Some behaviors are real but unautomatable
— a look-and-see judgement, an install on clean hardware, a printed page.
Start `verification` with `Manual:` or `Inspection:` and name the method:

```toml
verification = "Manual: install on a clean laptop and read the splash screen."
linked_tests = []
```

`check` then records it as `manual-verification` (a NOTE) instead of
counting it among the tests still owed. The prefix alone buys nothing —
it has to say what someone actually does. Use it because the behavior
cannot be automated, never to quiet a warning about a test you could
write; the NOTE stays printed and counted on every run either way. And
when an agent reaches for the prefix in place of a test it could have
written, it says so in the conversation as a `DEVIATION` line, at the
moment it happens rather than at review time.

**Recommended shape: EARS.** Pick the one pattern that fits — ubiquitous
(`The <system> shall <response>.`), event (`When <trigger>, …`), state
(`While <state>, …`), unwanted (`If <condition>, then …`) or optional
(`Where <feature is included>, …`). The point is not the syntax: a
stated trigger or condition is exactly what a test has to *arrange*, so
naming it is what makes the behavior testable. Two "shall" clauses means
two behaviors — split them. It is guidance, not a validated rule; a
constraint that reads better plainly is better plainly. `affected_paths` and
`linked_tests` are what make focused regression (`aegis test
--impacted`) and the traceability findings work — keeping them current
pays off immediately.

**Retiring one.** When a behavior is deliberately removed, never delete
the file: set `status = "retired"`, add `Retired <date>: <why>` to the
prose, and keep the id on the retiring task's own journal — that is the
record of what was retired and why. `check` stops applying active-only
rules to it, and the history stays readable. Retiring one is also spoken:
an agent that retires a requirement states it as a `DEVIATION` line as it
does so, because a contract being withdrawn is not something to discover
in a diff afterwards.

## Task journals — `tasks/TASK-<id>.md`

One journal per task. It is the **only** run state: the resume point for
any later session, on any machine, with any model — and it stays after
delivery as the task's historical record.

```markdown
# TASK-8b12 — Export playlist as M3U

stage: build
type: feature            # feature | fix | change | adopt
path: full               # full | quick
requirements: REQ-FUNC-3fa2
branch: feature/m3u-export
opened: 2026-08-02

## Done checklist (current stage)

- [x] exact red command, non-zero exit, and expected failure recorded
- [ ] implementation green
- [ ] links updated

## Log

- 2026-08-02 frame: scope agreed - M3U only, no PLS; full path.
- 2026-08-02 specify: created REQ-FUNC-3fa2.
- 2026-08-02 build red: command=`pytest -q tests/export/test_m3u.py::test_roundtrip`; exit=1; expected missing behavior=no M3U writer exists.
```

The header block (`key: value` lines under the title) is machine-read by
`status`, `check` and `report` — keep it one key per line with no blank
lines inside. Header lines are edited in place; log lines are only ever
appended, one sentence each.

A log line that records a *deviation* — an accepted warning, a skipped
verification, a retired requirement, unrequested work in the diff — has a
twin in the conversation: the agent states it at the same moment as one
`DEVIATION <stage>: <what> — <why>` line. The journal line is still
written; the notice does not replace it. It exists because a journal is
read afterwards, and by then the human has already paid for not knowing.

A journal can also contain one replaceable `## Stage report` section with
plain one-line `stage`, `result`, `current`, `changed`, `evidence`, `issues`,
`next`, and `needs_user` fields. `summary TASK-<id>` reads it without writing.
The report's stage can be completed while the header already names the next
stage; `current` binds the report to that header. Blank, stale, or shortened
information is explicit, never treated as success. The full log remains the
append-only history; the latest report is not independent or fresh proof.
See the CLI reference for allowed values and output limits.

Each task can also own two schema-1 JSON sidecars:

- `TASK-<id>.anchor.json` is the active pre-implementation baseline. It stores
  the observed stage and HEAD, configured layout globs, file categories, kinds,
  paths, and SHA-256 identities.
- `TASK-<id>.evolution.json` retains compact reports for completed pairs. Each
  report stores timestamps, stages, HEAD values, aggregate counts, and only the
  added, modified, or removed paths with before/after identities.

The inventory comes from Git: tracked and untracked non-ignored files are
included, while `.agentic/**`, ignored caches/build outputs, `__pycache__/`,
`.pyc`, and `.pyo` files are excluded. The records describe change; they are
editable repository files, not tamper-proof evidence.

## Specs — `specs/REQ-<...>.md`

Free markdown, only when the requirement alone is not enough to build
from (file formats, protocols, dialog text). Referenced by the
requirement's `spec` field; `check` verifies the reference resolves.

## Knowledge — `knowledge/<component>.md`

One plain page per component: Purpose, Public interface, Key behaviors
(citing requirement IDs), Architecture, Files. The `validate` stage asks the
agent to update the page of any component it materially changed. There is no
manifest and no registry — the folder listing is the component list.

**Architecture** holds a Mermaid diagram of that component's own logic —
what a reader has to hold in their head to change it safely, at ten to
fifteen nodes rather than every function. It is written by hand, not derived
from the code: a parser would need writing per language and could only ever
draw what already exists. Adoption draws it once per component while the
source is open; `design` revises it to the shape a change will produce and
marks it as intended; `validate` reconciles it with what was actually built
and removes that mark.

## Reading the register back

Everything above is written once per behavior. Two commands read it in the
other direction, and both derive what they show from the files already in
the repository — no model, no network, no renderer.

`diagram` draws the whole register as one Mermaid flowchart, grouping each
requirement under the component whose knowledge page claims it and colouring
it by how the behavior is verified: a linked test, a declared `Manual:` or
`Inspection:` method, or nothing yet. Requirements no page claims are grouped
apart rather than dropped, so an unclaimed behavior is visible instead of
absent. `--component` and `--task` narrow the picture; `--out` writes the
file as UTF-8.

`explain <path>` goes the other way still — point it at a file and it reports
every requirement whose `affected_paths` cover it, grouped by component, with
status, coverage, spec, and the journals that delivered them. A directory
covers the files beneath it. A path no requirement covers is said so plainly,
and called a finding when it sits inside your configured source or test globs.

## Configuration — `aegis.toml`

| Key | Meaning |
|---|---|
| `[commands] test` | Your full test suite; used by `aegis test` and `check --run`. |
| `[commands] test_impacted` | Template for focused regression; `{tests}` is replaced by the impacted test refs. |
| `[commands] <anything>` | More named commands (lint, build...); `check --run` executes them all. |
| `[commands] timeout` | Seconds allowed per command (default 1800). |
| `[layout] source / tests` | Globs that tell the heuristics what is code and what is test. |
| `[layout] docs` | Optional documentation globs accepted by the layout check; still secret-scanned, not counted as code, tests, or stage write zones. |
| `[zones] <stage>` | What that stage may write besides `.agentic/` — `"source"`, `"tests"`, or nothing. Omit a stage to leave it unconstrained. |
| `[check] ignore` | Globs excluded from every check. |
| `[check] secret_patterns_extra` | Extra regexes for the secret scan. |
| `[check] strict_promote` | Warning slugs that `check --strict` (CI) treats as errors. |
| `[check] run` | Restricts which `[commands]` entries `check --run` executes; without it, side-effect-looking names (deploy/migrate/publish/…) are skipped. |
| `[review] enabled / max_fix_cycles` | Optional explicit review policy: `enabled` defaults to `false`; `max_fix_cycles` is 0–5 and defaults to 2. |

When enabled, review allows one initial verdict plus up to `max_fix_cycles`
fix-and-re-review rounds. Review off never disables ordinary validation.

Task headers may include a blank `parent:` or one visible top-level task ID.
Child journals stay independently governed; the parent file is not rewritten.
`## Rulings` contains append-only `RULING-001` records with date, source,
decision, reason, and optional supersession. `## Handoff` is one replaceable
stage-bound block with `current`, `next`, `must_read`, `blockers`, and `status`.
The Stage report carries optional independent review verdicts and a bounded
round. Legacy journals may omit all of these fields.

**Integrating another tool?** `check --json`, `status --json`, `anchor --json`,
and `evolution --json` print one
JSON document on stdout — complete (never capped), with a `schema`
integer to version the contract, unchanged exit codes, and `--run`
progress on stderr. Parse that instead of scraping the human output.

That is the whole configuration surface.
