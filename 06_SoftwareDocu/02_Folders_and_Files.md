<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS - folders and files

The core stores workflow records as plain files on your branch. One artifact
is one file. Optional host integrations add local installation records and
verification-job caches outside the repository; those do not replace the
durable journal. This page tours both kinds of state.

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

## Requirements - `requirements/<category>/REQ-<CODE>-<id>.toml`

One file per independently verifiable behavior. Eight category folders:
`functional/ ux/ nfr/ security/ data/ platform/ reliability/ test/`
(codes FUNC, UX, NFR, SEC, DATA, PLAT, REL, TEST). The random 8-hex id
suffix reduces accidental ID collisions between branches, and
creation is exclusive - two racing processes cannot silently produce the
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

Write the prose self-contained - no ticket numbers, no "see TASK-1234"
(`aegis check` flags those patterns).

**When no test can settle it.** Some behaviors are real but unautomatable
- a look-and-see judgement, an install on clean hardware, a printed page.
Start `verification` with `Manual:` or `Inspection:` and name the method:

```toml
verification = "Manual: install on a clean laptop and read the splash screen."
linked_tests = []
```

`check` then records it as `manual-verification` (a NOTE) instead of
counting it among the tests still owed. The prefix alone buys nothing -
it has to say what someone actually does. Use it because the behavior
cannot be automated, never to quiet a warning about a test you could
write; the NOTE stays printed and counted on every run either way. And
when an agent reaches for the prefix in place of a test it could have
written, it says so in the conversation as a `DEVIATION` line, at the
moment it happens rather than at review time.

**Recommended shape: EARS.** Pick the one pattern that fits - ubiquitous
(`The <system> shall <response>.`), event (`When <trigger>, …`), state
(`While <state>, …`), unwanted (`If <condition>, then …`) or optional
(`Where <feature is included>, …`). The point is not the syntax: a
stated trigger or condition is exactly what a test has to *arrange*, so
naming it is what makes the behavior testable. Split responses only when
they can vary, fail, change, or be verified independently; keep clauses
together when they form one inseparable atomic outcome. It is guidance, not
a validated rule; a constraint that reads better plainly is better plainly.
`affected_paths` and `linked_tests` are what make focused regression (`aegis test
--impacted`) and the traceability findings work - keeping them current
pays off immediately.

**Retiring one.** When a behavior is deliberately removed, never delete
the file: set `status = "retired"`, add `Retired <date>: <why>` to the
prose, and keep the id on the retiring task's own journal - that is the
record of what was retired and why. `check` stops applying active-only
rules to it, and the history stays readable. Retiring one is also spoken:
an agent that retires a requirement states it as a `DEVIATION` line as it
does so, because a contract being withdrawn is not something to discover
in a diff afterwards.

## Task journals - `tasks/TASK-<id>.md`

One journal per task. It is the durable **workflow resume point** for
any later session, on any machine, with any model - and it stays after
delivery as the task's historical record.

```markdown
# TASK-8b12 - Export playlist as M3U

stage: build
type: feature
path: full
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
- 2026-08-02 build green: command=`pytest -q tests/export/test_m3u.py::test_roundtrip`; exit=0; M3U round-trip behavior verified.
```

The abbreviated example uses short IDs for readability. Real IDs have eight
hex digits; header values are plain values, without inline comments.

The header block (`key: value` lines under the title) is machine-read by
`status`, `check` and `report` - keep it one key per line with no blank
lines inside. Header lines are edited in place; log lines are only ever
appended. The Log is a concise progress-and-evidence ledger: retain stage
transitions, material changes or decisions, consolidated test results,
blockers, approvals, deviations and delivery outcomes. Do not copy durable
artifact content or record routine searches, edits, tool mechanics, or
corrected command retries.

The other journal sections own their detail: Frame owns scope evidence,
Requirement coverage owns behavior mapping, Design owns implementation choices,
Rulings own durable decisions, Handoff owns the next bounded action, and Stage
report owns the latest boundary snapshot. The Log references material outcomes
from those sections instead of duplicating their contents. During build, retain
one expected red and one final green per meaningful behavior increment, not
every edit-run retry. Refresh Handoff and Stage report when completing a stage,
pausing, blocking, or handing work over rather than after routine tool activity.

A log line that records a *deviation* - an accepted implementation or evidence
limitation, weakened or skipped verification, a retired requirement, or
unrequested work retained in the diff - has a twin in the conversation: the
agent states it at the same moment as one
`DEVIATION <stage>: <what> - <why>` line. The journal line is still
written; the notice does not replace it. It exists because a journal is
read afterwards, and by then the human has already paid for not knowing.
Corrected search, quoting, patch, path, and other internal tool-use errors are
operational details rather than deviations because they do not change the
candidate, scope, or verification evidence.

A journal can also contain one replaceable `## Stage report` section with
plain one-line `stage`, `result`, `current`, `changed`, `evidence`, `issues`,
`next`, and `needs_user` fields. `summary TASK-<id>` reads it without writing.
The report's stage can be completed while the header already names the next
stage; `current` binds the report to that header. Blank, stale, or shortened
information is explicit, never treated as success. The compact Log remains the
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

## Specs - `specs/REQ-<...>.md`

Free markdown, only when the requirement alone is not enough to build
from (file formats, protocols, dialog text). Referenced by the
requirement's `spec` field; `check` verifies the reference resolves.

## Knowledge - `knowledge/<component>.md`

One plain page per component: Routing, Purpose and boundaries, Public
interface, Invariants, Key behaviors (citing requirement IDs), Architecture,
and Files. A Change map is included when the component has multiple independent
edit-and-test seams. Routing selects the page and points to owned source and
focused tests; it narrows discovery but never replaces exact source-and-test
inspection. The `validate` stage reconciles every affected section. There is
no manifest and no registry - the folder listing is the component list.

**Architecture** holds a Mermaid diagram of that component's own logic -
what a reader has to hold in their head to change it safely, at ten to
fifteen nodes rather than every function. It is written by hand, not derived
from the code: a parser would need writing per language and could only ever
draw what already exists. Adoption draws it once per component while the
source is open. When structure will change, `design` records a proposed
diagram in the task journal without replacing this current-state page;
`validate` reconciles the canonical diagram with what was actually built.

## Reading the register back

Everything above is written once per behavior. Three commands read it in the
other direction, and all derive what they show from the files already in
the repository - no model, no network, no renderer.

`diagram` draws the whole register as one Mermaid flowchart, grouping each
requirement under the component whose knowledge page claims it and colouring
it by how the behavior is verified: a linked test, a declared `Manual:` or
`Inspection:` method, or nothing yet. Requirements no page claims are grouped
apart rather than dropped, so an unclaimed behavior is visible instead of
absent. `--component` and `--task` narrow the picture; `--out` writes the
file as UTF-8.

`trace` writes the whole register as a flat Markdown table or CSV, with one
row per requirement and complete linked-test and affected-path lists. It
reports unreadable requirement files separately from rows with validation
errors. Use `trace --format csv --out docs/traceability-matrix.csv` for a
spreadsheet file with UTF-8 encoding; a `.csv` suffix alone does not select
CSV, and shell redirection retains the console encoding.

`explain <path>` goes the other way still - point it at a file and it reports
every requirement whose `affected_paths` cover it, grouped by component, with
status, coverage, spec, and the journals that delivered them. A directory
covers the files beneath it. A path no requirement covers is said so plainly,
and called a finding when it sits inside your configured source or test globs.

## Configuration - `aegis.toml`

| Key | Meaning |
|---|---|
| `[commands] test` | Your full test suite; used by `aegis test` and `check --run`. |
| `[commands] test_impacted` | Template for focused regression; `{tests}` is replaced by the impacted test refs. |
| `[commands] <name>` | More named commands, such as lint or build; `check --run` executes eligible entries. |
| `[commands] timeout` | Optional fallback limit in seconds. No limit is applied by default. |
| `[timeouts] <name>` | Per-command limit; takes precedence over `[commands] timeout`. Only a positive integer sets a limit. |
| `[commands] workdir` | Repository-relative directory in which commands run. |
| `[layout] source / tests` | Globs that tell the heuristics what is code and what is test. |
| `[layout] docs` | Optional documentation globs accepted by the layout check; still secret-scanned, not counted as code, tests, or stage write zones. |
| `[zones] <stage>` | What that stage may write besides `.agentic/` - `"source"`, `"tests"`, or nothing. Omit a stage to leave it unconstrained. |
| `[check] ignore` | Globs excluded from every check. |
| `[check] secret_patterns_extra` | Extra regexes for the secret scan. |
| `[check] strict_promote` | Warning slugs that `check --strict` (CI) treats as errors. |
| `[check] run` | Restricts which `[commands]` entries `check --run` executes; without it, side-effect-looking names (deploy/migrate/publish/…) are skipped. |
| `[review] enabled / max_fix_cycles` | Optional explicit review policy: `enabled` defaults to `false`; `max_fix_cycles` is 0-5 and defaults to 2. |

When enabled, each review round needs two independent verdicts: specification
compliance and implementation quality. One initial round plus at most
`max_fix_cycles` fix-and-re-review rounds is allowed. Clear both verdicts after
a candidate change and obtain both approvals for the same candidate. Review
off never disables ordinary semantic review or validation.

Task headers may include a blank `parent:` or one visible top-level task ID.
Child journals stay independently governed; the parent file is not rewritten.
`## Rulings` contains append-only `RULING-001` records with date, source,
decision, reason, and optional supersession. `## Handoff` is one replaceable
stage-bound block with `current`, `next`, `must_read`, `blockers`, and `status`.
The Stage report carries optional independent review verdicts and a bounded
round. Legacy journals may omit all of these fields.

**Integrating another tool?** `check --json`, `status --json`, `anchor --json`,
and `evolution --json` print one
JSON document on stdout - complete (never capped), with a `schema`
integer to version the contract, unchanged exit codes, and `--run`
progress on stderr. Parse that instead of scraping the human output.

This is a configuration overview. The [CLI reference](09_CLI_Reference.md)
describes command selection, base resolution, timeouts and output contracts.
Reserved command settings and the `test_impacted` template are not separate
commands for `check --run` to execute.

## Optional host installation and job state

| Host | Default profile root (override shown first) |
|---|---|
| OpenCode | `OPENCODE_CONFIG_DIR`, otherwise `XDG_CONFIG_HOME/opencode` or `~/.config/opencode` |
| Codex | `CODEX_HOME` or `~/.codex` |
| Pi | `PI_CODING_AGENT_DIR` or `~/.pi/agent` |
| Qwen Code | `QWEN_HOME` or `~/.qwen` |
| Claude Code | `CLAUDE_CONFIG_DIR` or `~/.claude` |

Complete built packages contain host resources and shared runtime libraries.
An installed `runtime.json` records local executable/cache paths; ownership
records identify files the installer may update or remove. Codex and Claude
also register a native plugin cache. Distribute the built package, not an
installed profile or its machine-specific settings. Authentication stays with
each user's host.

Verification-job metadata and logs default to
`XDG_CACHE_HOME/aegis/integrations` or `~/.cache/aegis/integrations`. Jobs can
survive a host restart. Resume the existing job before starting another suite;
duplicate detection applies only to adapters using the same cache and checkout.
Externally launched tests are outside that reservation mechanism.

The integration candidate fingerprint includes Git-visible files but excludes
task journals/evidence and Python bytecode. The core `anchor` inventory excludes
all of `.agentic/`; these are different inventories. Neither includes ignored
files or proves test quality. Integration fingerprints also exclude external
inputs and submodule contents.

Update/removal checks owned files and job reservations, and retains cached job
logs. Use installer `update --cache PATH` to change an installed cache after
jobs finish; conflicting `AEGIS_CACHE` overrides are rejected. See
[Agent_Plugins.md](Agent_Plugins.md) for lifecycle and recovery details.
