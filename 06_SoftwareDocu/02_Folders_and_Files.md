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
  steps/           stage, review and diagram guides   (payload)
  templates/       scaffolding sources                (payload)
  aegis.toml       your configuration                 (yours)
  requirements/    the durable contracts              (yours)
  specs/           optional per-requirement specs     (yours)
  tasks/           journals; sidecars git-ignored     (yours)
  knowledge/       one page per component             (yours)
  context/
    project.md     current project orientation        (yours)
    environment.md current setup and verification     (yours)
```

The split matters: **payload** files are replaced on upgrade; **yours**
are never shipped in a payload and never overwritten.

## Templates and generated records

Newly scaffolded tasks, requirements, and context files omit the payload
license header and the explicitly marked instruction-only notes; they belong to
the project. The full guidance remains in the managed templates; durable fields
and unmarked data are preserved. Existing records are not rewritten or
compacted, so older ones keep their license header. Markdown templates mark
notes with `<!-- AEGIS:TEMPLATE` and a standalone `-->`; requirement templates
use `# AEGIS:TEMPLATE-BEGIN` and `# AEGIS:TEMPLATE-END`.

## Project context - `context/`

`project.md` holds current purpose, users, responsibilities, supported operation,
established constraints, and component entry points. `environment.md` holds
current toolchain/setup routes, configuration names, readiness checks, and
build/verification references. Both are project-owned Markdown with stable
headings, scaffolded independently only when absent. Commands and layout values
stay canonical in `aegis.toml`; existing setup docs are linked rather than copied.

Read the profile at frame/resume and relevant environment sections before setup
or verification. Populate from current evidence during frame/adoption; update
affected sections as facts change and reconcile them at validate. An absent or
partial file is compatible with ordinary work. See [Project context](Project_Context.md).

Project documents, component pages, and active requirements/specs describe
current behavior positively, including meaningful failure responses. They are
current-state guides rather than histories or inventories of absent features.
Draft requirements/specs carry agreed proposed behavior; journals, Git and the
changelog carry decisions and history. An implementation mismatch calls for
investigation or an authorized change, not an easier replacement contract.
After another branch is integrated, re-check these current-state claims against
the checkout; another branch's plans are not facts here.

## Requirements - `requirements/<category>/REQ-<CODE>-<id>.toml`

One file per independently verifiable behavior. Eight category folders:
`functional/ ux/ nfr/ security/ data/ platform/ reliability/ test/`
(codes FUNC, UX, NFR, SEC, DATA, PLAT, REL, TEST). The random 8-hex id
suffix reduces accidental ID collisions between branches, and
creation is exclusive - two racing processes cannot silently produce the
same file. (Examples in these docs use short ids for readability.) Change an
existing requirement or spec only within your task's scope, so parallel
branches merge cleanly.

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
the file: set `status = "retired"`, append one `Retired <date>: <why>` line to
its prose, and keep its id on the retiring task's `requirements:` line. Keep
the behavior statement itself as a traceable contract; the authorization and
any fuller reasoning stay in the retiring task's journal, and another task's
journal is never edited. Current project and component summaries describe
active behavior. `check` applies its status-aware rules to retired records.
Retiring one is also spoken:
an agent that retires a requirement states it as a `DEVIATION` line as it
does so, because a contract being withdrawn is not something to discover
in a diff afterwards.

## Task journals - `tasks/TASK-<id>.md`

One journal per task, on that task's branch. It is the durable **workflow
resume point** for any later session, on any machine, with any model - and it
stays after the task closes as its historical record. Edit only your own
task's journal; a parallel branch carries its own.

```markdown
# TASK-8b12 - Export playlist as M3U

stage: build
type: feature
path: full
interaction: checkpoint
requirements: REQ-FUNC-3fa2
parent:
branch: feature/m3u-export
base: 41e9f55
opened: 2026-08-02

## Done checklist (current stage)

- [x] each automated increment has a red line before its implementation and a
      green line after; each manual one a logged observation
- [ ] anchor recorded before implementation; evolution reviewed after
- [ ] focused tests green, with the command and its scope logged

## Log

- 2026-08-02 frame: journal opened
- 2026-08-02 frame: completed; next specify - scope accepted
- 2026-08-02 specify: completed; next design
- 2026-08-02 design: completed; next build
- 2026-08-02 build: red: pytest -q tests/export/test_m3u.py::test_roundtrip exit 1 - no M3U writer (REQ-FUNC-3fa2)
- 2026-08-02 build: green: pytest -q tests/export/test_m3u.py::test_roundtrip exit 0 (REQ-FUNC-3fa2)

## Rulings

- RULING-001 | date=2026-08-02 | decision=M3U only, no PLS | reason=user answer | source=user | supersedes=none

## State

status: ready
reported: design - completed
next: start build: read .agentic/steps/4_build.md
must_read: .agentic/tasks/TASK-8b12.md, .agentic/steps/4_build.md
changed: design section written
evidence: check exit 0
issues:
spec_compliance: disabled
implementation_quality: disabled
review_round:
```

The abbreviated example uses short IDs for readability and leaves out the
Frame, Requirement coverage and Design sections and the rest of the checklist.
Real IDs have eight hex digits; header values are plain values, without inline
comments. New journals carry no license header.

The CLI writes the header `stage:` line, the Done checklist, the Log, the
Rulings and the State:

| When | Command |
|---|---|
| A stage is finished | `advance TASK-<id>` (`--path quick` at frame, `--skipped` for a skipped stage) |
| Work must go back | `advance TASK-<id> --to <stage> --reason "<why>"` |
| You stop, or need the user | `pause TASK-<id> --next "<one action or question>"` (`--blocked` when a decision blocks) |
| A durable event happens | `log TASK-<id> "<decision, verification result, discovery or deviation>"` |
| A question is settled | `ruling TASK-<id> --decision "..." --reason "..." --source user` |
| Explicit review returns | `verdict TASK-<id> --spec <verdict> --quality <verdict>` |

The agent edits Frame, Requirement coverage and Design directly, ticks Done
checklist items as they are met, and edits the header lines `type`, `path`,
`interaction`, `requirements` and `parent` in place - one `key: value` per
line, no blank lines or comments inside the header block, which `status`,
`brief`, `summary`, `check` and `report` read. Earlier Log lines and Rulings
are never edited: `log` and `ruling` only append, and a changed decision is a
new ruling with `--supersedes RULING-<old-id>`.

The Log is a concise progress-and-evidence ledger: stage transitions (written
by `advance`), material changes or decisions, consolidated test results (`log`,
or `test --task`), blockers, approvals and deviations. `log` prefixes each line
with the date and the current stage. Do not copy durable artifact content or
record routine searches, edits, tool mechanics, or corrected command retries.

The other journal sections own their detail: Frame owns scope evidence,
Requirement coverage owns behavior mapping, Design owns implementation choices,
Rulings own durable decisions, and State owns the latest status and next
action. The Log references material outcomes from those sections instead of
duplicating their contents. During build, retain one expected red and one final
green per meaningful behavior increment, not every edit-run retry.

`advance` and `pause` refresh the State when a stage completes, the work pauses
or blocks, or a session ends, not after routine tool activity. Keep their
one-line `--changed`, `--evidence` and `--issues` values short; evidence names
the commands actually run and their exit codes. Do not repeat Frame, Design or
Log content there. In an intact session, reuse unchanged instructions already
read. After compaction or lost context, follow the required resume and
full-journal reads again.

A log line that records a *deviation* - an accepted implementation or evidence
limitation, weakened or skipped verification, a retired requirement, or
unrequested work retained in the diff - has a twin in the conversation: the
agent states it at the same moment as one
`DEVIATION <stage>: <what> - <why>` line. `log` still writes the journal
line; the notice does not replace it. It exists because a journal is
read afterwards, and by then the human has already paid for not knowing.
Corrected search, quoting, patch, path, and other internal tool-use errors are
operational details rather than deviations because they do not change the
candidate, scope, or verification evidence.

The `## State` block is one replaceable section of plain one-line fields:
`status`, `reported`, `next`, `must_read`, `changed`, `evidence`, `issues`,
`spec_compliance`, `implementation_quality` and `review_round`. `status` is
`working`, `waiting`, `blocked`, `ready` or `done`; `waiting` and `blocked`
mean the user is needed. `reported` names the last reported stage and its
result (`in_progress`, `completed`, `paused`, `blocked` or `skipped`); the
current stage is always the header's `stage:` line. `advance`, `pause` and
`verdict` print it as the summary block, and `summary TASK-<id>` prints it
again without writing. Blank, stale, or shortened information is explicit,
never treated as success. The compact Log remains the append-only history; the
latest State is not independent or fresh proof. At the end of validate,
`report` appends a dated closing report (`## Delivery report`) to the journal.

Journals written by an earlier version keep their `## Handoff` and
`## Stage report` sections; `brief`, `summary`, `check` and `report` read
either format, and the first State write replaces the two old sections. See
the CLI reference for allowed values and output limits.

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
editable files, not tamper-proof evidence. By default they stay out of git:
`init` maintains a marked block in the root `.gitignore` for both sidecars,
and the journal log line is the durable record. `[records]
commit_fingerprints = true` removes that block so they travel with the
journal.

When `[diagrams] enabled = true`, design also writes `diagram_TASK-<id>.md`
beside the journal: Mermaid diagrams of the proposed implementation for the
human, linked once from `## Design` and shown at the design checkpoint. The
file is committed with the journal. Checkpoint responses include the saved
blocks after the summary; autopilot reports the path without displaying them.
`types = []` creates no file or link, and a skipped Design creates none.
No stage, review or `check` finding depends on it, and journal discovery
(`TASK-*.md`) never reads it.

`evolution --compact --json` omits before/after hashes from the response while
retaining changed paths, statuses, areas and counts. Saved evolution reports
retain their full evidence. Ordinary `--json` output is unchanged; compact
output does not shrink the anchor inventory or delete saved metadata.

## Specs - `specs/REQ-<...>.md`

The linked requirement's status distinguishes agreed draft behavior from an
implemented active contract. Resolve open decisions before activation and keep
their history in the journal. Active prose describes current positive outcomes,
including meaningful failure responses.

Free markdown, only when the requirement alone is not enough to build
from (file formats, protocols, dialog text). Referenced by the
requirement's `spec` field; `check` verifies the reference resolves.

## Knowledge - `knowledge/<component>.md`

One plain page per component: Routing, Purpose and boundaries, Public
interface, Invariants, Key behaviors (citing requirement IDs), and Files. A
Change map is included when the component has multiple independent
edit-and-test seams. Routing selects the page and points to owned source and
focused tests; it narrows discovery but never replaces exact source-and-test
inspection. Design leaves pages unchanged; validate updates or creates affected
pages against the reviewed code and tests, before explicit review and the
final proof. Change a page only within your task's scope, section by section,
so parallel branches merge cleanly. There is no manifest and no registry - the
folder listing is the component list, and `components` prints it.

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

Each key's default value and its behavior when absent are in the
[settings reference](01_Install_and_Setup.md#settings-reference).

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
| `[layout] default_branch` | The ref every diff is measured from. Without it the base is `origin/HEAD`, then a local `master`, then a local `main`. |
| `[zones] <stage>` | What that stage may write besides `.agentic/` - `"source"`, `"tests"`, or nothing. Omit a stage to leave it unconstrained. |
| `[check] ignore` | Globs excluded from every check. |
| `[check] secret_patterns_extra` | Extra regexes for the secret scan. |
| `[check] strict_promote` | Warning slugs that `check --strict` (CI) treats as errors. |
| `[check] run` | Restricts which `[commands]` entries `check --run` executes; without it, side-effect-looking names (deploy/migrate/publish/…) are skipped. |
| `[interaction] autopilot` | `false` stops at every completed stage and presents the next choices; `true` flows between stages through validate. AEGIS never commits or publishes in either mode. |
| `[review] enabled / max_fix_cycles` | Optional explicit review policy: `enabled` defaults to `false`; `max_fix_cycles` is 0-255 and defaults to 2. With `true`, validate follows `steps/review.md`. |
| `[diagrams] enabled / types` | `enabled = true` has design draw Mermaid diagrams of the proposed implementation into `tasks/diagram_TASK-<id>.md`; it defaults to `false`. `types` lists any of `structure`, `sequence`, `state` and defaults to `["structure"]`. |
| `[records] commit_fingerprints` | `false` keeps anchor/evolution sidecars out of git through a managed `.gitignore` block that `init` maintains; `true` removes the block so they are committed with the journal. |

When enabled, each review round needs two independent verdicts, recorded with
`verdict`: specification compliance and implementation quality. One initial
round plus at most `max_fix_cycles` fix-and-re-review rounds is allowed. Any
candidate change invalidates both verdicts; a return with `advance --to build`
clears them while keeping the consumed round, and historical findings stay in
the Log. Obtain both approvals for the same candidate. Review off never
disables ordinary semantic review or validation. Reviewers inspect current
files and phase-appropriate focused proof; final full strict proof follows both
approvals.

Task headers may include a blank `parent:` or one visible top-level task ID.
Child journals stay independently governed; the parent file is not rewritten.
`## Rulings` contains append-only `RULING-001` records with date, decision,
reason, source, and optional supersession, written by `ruling`. `## State` is
the one replaceable block, written by `advance`, `pause` and `verdict`; it
carries the optional review verdicts and a bounded round. Older journals keep
`## Handoff` and `## Stage report` until the first State write replaces them.

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
