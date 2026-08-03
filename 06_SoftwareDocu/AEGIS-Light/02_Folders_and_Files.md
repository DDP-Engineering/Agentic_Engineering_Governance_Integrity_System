<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light — folders and files

Everything AEGIS Light knows is a plain file committed to your branch.
One artifact = one file. No database, no run store, no state outside the
repo. This page tours `.agentic/` with a filled-in example per format.

```
.agentic/
  AGENTS.md        the contract your agent reads      (payload)
  aegis.py         the CLI                            (payload)
  LICENSE.txt      license text                       (payload)
  steps/           one instruction file per stage     (payload)
  templates/       scaffolding sources                (payload)
  aegis.toml       your configuration                 (yours)
  requirements/    the durable contracts              (yours)
  specs/           optional per-requirement specs     (yours)
  tasks/           task journals - the run state      (yours)
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
rules to it, and the history stays readable.

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

- [x] failing test written and observed red
- [ ] implementation green
- [ ] links updated

## Log

- 2026-08-02 frame: scope agreed - M3U only, no PLS; full path.
- 2026-08-02 specify: created REQ-FUNC-3fa2.
- 2026-08-02 test: test --impacted (1 test ref(s)) exit 1 (0.4s)
```

The header block (`key: value` lines under the title) is machine-read by
`status`, `check` and `report` — keep it one key per line with no blank
lines inside. Header lines are edited in place; log lines are only ever
appended, one sentence each.

## Specs — `specs/REQ-<...>.md`

Free markdown, only when the requirement alone is not enough to build
from (file formats, protocols, dialog text). Referenced by the
requirement's `spec` field; `check` verifies the reference resolves.

## Knowledge — `knowledge/<component>.md`

One plain page per component: Purpose, Public interface, Key behaviors
(citing requirement IDs), Files. The `deliver` stage asks the agent to
update the page of any component it materially changed. There is no
manifest and no registry — the folder listing is the component list.

## Configuration — `aegis.toml`

| Key | Meaning |
|---|---|
| `[commands] test` | Your full test suite; used by `aegis test` and `check --run`. |
| `[commands] test_impacted` | Template for focused regression; `{tests}` is replaced by the impacted test refs. |
| `[commands] <anything>` | More named commands (lint, build...); `check --run` executes them all. |
| `[commands] timeout` | Seconds allowed per command (default 1800). |
| `[layout] source / tests` | Globs that tell the heuristics what is code and what is test. |
| `[check] ignore` | Globs excluded from every check. |
| `[check] secret_patterns_extra` | Extra regexes for the secret scan. |
| `[check] strict_promote` | Warning slugs that `check --strict` (CI) treats as errors. |
| `[check] run` | Restricts which `[commands]` entries `check --run` executes; without it, side-effect-looking names (deploy/migrate/publish/…) are skipped. |

**Integrating another tool?** `check --json` and `status --json` print one
JSON document on stdout — complete (never capped), with a `schema`
integer to version the contract, unchanged exit codes, and `--run`
progress on stderr. Parse that instead of scraping the human output.

That is the whole configuration surface.
