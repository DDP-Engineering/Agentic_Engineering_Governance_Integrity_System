<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 02 - Artifacts and formats

AEGIS stores its durable workflow state as ordinary UTF-8 Markdown, TOML,
and JSON files in the repository. The core needs no database or service.
Optional host integrations keep separate, explicit local installation and job
records; those records do not replace the authoritative task journal.

## Installed layout and ownership

```text
.agentic/
  AGENTS.md, CLI.md, LICENSE.txt, aegis.py    managed payload
  steps/                                      managed workflow instructions
  templates/                                  managed artifact scaffolds
  aegis.toml                                  repository-owned configuration
  requirements/                               repository-owned durable contracts
  specs/                                      repository-owned optional detail
  tasks/                                      repository-owned journals and JSON evidence
  knowledge/                                  repository-owned component pages
  context/project.md, context/environment.md   repository-owned current context
```

Exactly 18 files are managed by the payload: `AGENTS.md`, `CLI.md`,
`LICENSE.txt`, `aegis.py`, eight step files (six stages, adoption and the
optional design diagram guide), and six templates. A payload
upgrade replaces only those managed files. It preserves `aegis.toml`,
requirements, specs, tasks, anchors, evolution reports, knowledge pages, and
current project/environment context. `init` scaffolds each missing context
file; existing files retain their bytes. Context and component pages describe
current positive facts. Draft/task records hold proposals; journals and Git
retain history.
Run `python .agentic/aegis.py init` after a payload update to refresh the
managed root digests in `AGENTS.md`, `CLAUDE.md`, and `QWEN.md`.

## Current project context

For the current-context format and lifecycle, see
[Project context](../06_SoftwareDocu/Project_Context.md). Both files use UTF-8
Markdown with stable headings. The profile holds purpose, responsibilities,
supported operation, constraints and entry points; the environment guide links
toolchain, setup, readiness and verification. `aegis.toml` and existing setup
documents remain canonical for commands and values.

Frame/adoption populates confirmed facts. Build updates affected facts as changes
become real; validate reconciles current context, component pages and active
contracts. Pause/resume state stays in the journal/Handoff. Brief exposes file
presence only. Shared current documents retain one positive behavior statement,
including meaningful error/security responses, rather than alternatives or
change history. Suspected defects belong in task findings pending clarification.

## Integration packages and installed files

Integration source lives under `05_Software/aegis/integrations/`. Each host
has native resources such as manifests, agents, skills, commands or extension
code. Qwen and Claude also have MCP registration; Claude has hook definitions.
The shared JavaScript runtime is maintained once under `shared/`.

`02_Tools/build_agent_plugins.mjs` assembles complete package directories and
copies shared code into `lib/`. Codex and Claude place it within
`plugins/aegis/lib/`; OpenCode, Pi and Qwen place it at package root. Raw source
folders are not complete installable packages: registering one as a marketplace
can leave `lib/bridge.mjs` missing.

Installers add an owned-file manifest, `.aegis-<host>-installation.json`, plus
installation locks/backups in the selected host configuration directory. They
record discovered local executable paths and the chosen job cache in
`runtime.json`. These are machine-specific records, not credentials or portable
team configuration; distribute the original built package instead of copying
someone's installed profile.

| Host | Default configuration root | Main owned resources |
|---|---|---|
| OpenCode | `OPENCODE_CONFIG_DIR`, otherwise `$XDG_CONFIG_HOME/opencode` or `~/.config/opencode` | Package and plugin loader; agents/commands registered through its config hook. |
| Codex | `CODEX_HOME` or `~/.codex` | Local `aegis-marketplace`, review TOMLs under `agents/`, and native plugin cache. |
| Pi | `PI_CODING_AGENT_DIR` or `~/.pi/agent` | `extensions/aegis`. |
| Qwen Code | `QWEN_HOME` or `~/.qwen` | `extensions/aegis`. |
| Claude Code | `CLAUDE_CONFIG_DIR` or `~/.claude` | Local `aegis-marketplace` and native plugin cache. |

Package setup supports explicit profile/runtime paths. Update and removal
validate owned content and refuse unsafe collisions or active/uncertain jobs;
they preserve unrelated settings. Codex and Claude also validate their native
AEGIS caches, refusing added, edited or missing content. The 18-file core
payload and each host package have separate update procedures.

## Verification job cache

All integrations default to `$XDG_CACHE_HOME/aegis/integrations` or
`~/.cache/aegis/integrations`. Job JSON records and output logs hold checkout
identity, process IDs, timestamps, exit status and candidate fingerprints.
Reservations prevent adapters sharing that cache from launching duplicate
checkout verification. Uncertain worker state retains the reservation for
inspection; manually launched suites are outside this protection.

Installed runtime settings bind the cache location. Change it with installer
`update --cache PATH`; lifecycle checks inspect the stored and requested caches.
A conflicting `AEGIS_CACHE` environment override is refused for an installed
package. Job logs remain after uninstall. This cache supports operational
recovery. Raw progress and command output stay in that cache; only material
findings, decisions, blockers, and consolidated validation outcomes belong in
the repository journal.

## Configuration

`aegis.toml` is written once by `init` and belongs to the repository
thereafter. The implemented configuration surface is:

| Section | Keys and behavior |
|---|---|
| `[commands]` | `test` is the full suite; `test_impacted` may use `{tests}`; any other plain name is available to `check --run`. `timeout` is the default per-command limit and `workdir` selects an application subdirectory. |
| `[timeouts]` | Optional per-command limits overriding `[commands] timeout`. A timeout means the command proved nothing; it is not reported as a test failure. |
| `[layout]` | `source`, `tests`, and optional `docs` globs drive traceability/layout checks. `default_branch` can select the diff base. |
| `[review]` | Exact Boolean `enabled` (default `false`) and integer `max_fix_cycles` from 0 through 255 (default 2). |
| `[records]` | Exact Boolean `commit_fingerprints` (default `false`). While false, `init` maintains a managed `.gitignore` block that excludes the anchor/evolution sidecars; true removes that block so they are committed with the journal. |
| `[interaction]` | Boolean `autopilot` defaults to `false`, including a missing table/key. Checkpoint mode presents choices after every stage; publication authority applies in both modes. |
| `[diagrams]` | Exact Boolean `enabled` defaults to `false`, including a missing table/key. `types` lists `structure`, `sequence` or `state` and defaults to `["structure"]`. When enabled, design draws Mermaid diagrams of the proposed implementation for the human; nothing checks them. |
| `[zones]` | Optional per-stage source/test write allowances beyond `.agentic/`; findings are advisory. |
| `[check]` | `ignore`, `secret_patterns_extra`, `strict_promote`, and optional `run` command allow-list. |

Example:

```toml
schema = 1

[commands]
test = "python -m pytest -q"
test_impacted = "python -m pytest -q {tests}"
lint = "python -m ruff check src"
timeout = 1800

[timeouts]
test = 5400

[layout]
source = ["src/"]
tests = ["tests/"]
docs = ["docs/", "README.md"]

[review]
enabled = true
max_fix_cycles = 2

[check]
ignore = []
secret_patterns_extra = []
strict_promote = ["no-linked-tests"]
```

The commands are examples for a Python project, not built-in runner choices.
Each project owns toolchain setup and a runner that understands its linked
references. `test --dry-run` previews the selected command and working directory;
`test --impacted --no-fallback` refuses unavailable selection. Neither a preview
nor a refusal writes test evidence. These are invocation options, not new TOML
keys. Unsupported selector suffixes may broaden to a validated file reference;
unsafe file paths still require a project-native command.

## Lean generated records

`task`, `req` and context scaffolding in `init` omit marked authoring notes.
Markdown templates use `<!-- AEGIS:TEMPLATE` blocks with a standalone closing `-->`;
requirement templates use `# AEGIS:TEMPLATE-BEGIN` / `# AEGIS:TEMPLATE-END`.
The complete field guidance stays in the managed templates. Licenses, durable
fields and unmarked data are preserved. Existing journals and requirements are
not compacted or rewritten, and their data formats are unchanged.

## Requirements and specifications

Active contracts describe the implemented behavior positively, with explicit
triggers and responses for important error/security cases. Draft records hold
agreed proposals. Resolve spec open decisions before activation and retain their
decision trail in the journal. Retired records remain available for traceability
and are excluded from current behavior summaries. Preserve established contracts
when implementation disagrees; resolve the finding or obtain change authority.

One TOML requirement expresses one independently verifiable behavior:

```toml
schema = 1
id = "REQ-FUNC-3fa2c1d4"
title = "Export playlist as M3U"
status = "active"
requirement = "When an export is requested, the system shall write one M3U file."
verification = "tests/export/test_m3u.py::test_export"
affected_paths = ["src/export/m3u.py"]
linked_tests = ["tests/export/test_m3u.py::test_export"]
spec = "specs/REQ-FUNC-3fa2c1d4.md"
```

The required fields are `schema`, `id`, `title`, `status`,
`requirement`, and `verification`. `affected_paths` and
`linked_tests` power coverage and impacted-test selection. A verification
starting with `Manual:` or `Inspection:` explicitly records a non-test
method. `spec`, `priority`, `rationale`, `created`, and `updated`
are optional.

Requirements live in their category folder and use the matching prefix:
`FUNC`, `UX`, `NFR`, `SEC`, `DATA`, `PLAT`, `REL`, or `TEST`.

Split responses only when they can vary, fail, change, or be verified
independently. Keep clauses together when they form one inseparable atomic
observable outcome. A broad Frame outcome may therefore produce several
atomic behavior rows, while each atomic behavior maps to exactly one
requirement. Reuse an existing requirement only when actor/system, trigger or
state, response, constraints, and observable result match semantically.

Verification is derived from setup, trigger or input, action, observable
oracle, a relevant boundary or failure, and the honest automation method. The
final TOML field may be concise, but it must name the observation that settles
the behavior rather than restating requirement prose.

Specs are optional Markdown detail used when exact build behavior needs a
schema, wire or file format, protocol, state machine, non-obvious algorithm,
multi-step interaction, compatibility rule, migration, or detailed error
semantics. Specs retain material assumptions and open decisions instead of
silently resolving them.

## Journals, evidence, and knowledge

A task journal has a machine-readable header followed by a current checklist
and append-only log. Its header records `stage`, `type`, `path`,
`requirements`, optional `parent`, `branch`, `base`, and `opened`.

The Log is a compact progress-and-evidence ledger, not an activity transcript.
It keeps stage transitions; material scope, implementation, or test changes;
consolidated automated or manual verification; blockers; approvals;
deviations; and delivery outcomes. Routine searches, reads, edits, tool
mechanics, corrected command retries, and content already held in another
durable artifact stay out. Existing entries remain append-only when the
logging contract changes.

Build normally records one reproducible red result and one final focused green
result per meaningful behavior increment, grouping requirements that share a
test seam. Inner-loop retries are not journal events. Validate records one
consolidated final result and retains an earlier failed gate only when it
exposed a candidate problem, caused an implementation or test change, or
remains an accepted limitation.

Current journals also provide durable semantic sections:

- `## Frame`: problem, desired outcome, actors, scenario, examples and
  counterexamples, scope, constraints, success signals, evidence,
  assumptions, unknowns, decision-blocking questions, proposed behaviors,
  and path reason.
- `## Requirement coverage`: one row per atomic behavior, linking the broad
  Frame outcome to its requirement, positive case, boundary or failure,
  verification, and design decision or `no design impact`.
- `## Design`: proportionate implementation decisions, traceability, test
  seams, risks, open decisions, and expected files, plus one link to
  `diagram_TASK-<id>.md` when design diagrams are enabled.

The journal may additionally hold:

- `## Rulings`: append-only `RULING-001` records with date, decision,
  reason, source, and optional `supersedes`.
- `## Handoff`: replaceable resume fields `current`, `status`, `next`,
  `must_read`, and `blockers`.
- `## Stage report`: replaceable latest result with changes, evidence,
  issues, next action, user need, and review fields.

These sections divide ownership deliberately: Frame holds detailed scope,
Requirement coverage holds behavior mapping, Design and specs hold technical
choices, Rulings hold durable decisions, Handoff holds resume state, and Stage
report holds the latest communication snapshot. The Log references those
records instead of copying them. Stage report and Handoff refresh at stage
transitions, pauses or session ends, and blockers—not after routine work.

`anchor --task` writes `TASK-<id>.anchor.json`, a SHA-256 starting-point
fingerprint. `evolution --task` writes the corresponding
`TASK-<id>.evolution.json` comparison. These are durable inspection
evidence, not a replacement for review. `evolution --compact --json` omits
before/after hashes from the response and retains paths, statuses, areas and
counts. The saved comparison remains complete; ordinary `--json` retains its
existing detail. Anchor coverage and storage have not been narrowed. Both
sidecars are excluded from Git by default through the managed `.gitignore`
block `init` maintains, so the journal's recorded evolution line is the shared
evidence.

Each component page under `knowledge/` routes matching requests through
selection signals to the component's owned source and focused tests. It records
purpose and boundaries, public interface, invariants, key behaviors, and files;
components with multiple independent edit-and-test
seams also carry a change map. The route narrows discovery, while exact source
and tests remain authoritative. The no-argument `components` command derives a
deterministic catalogue from each page's first level-one title, or filename
stem fallback, and lexical repository-relative path. It does not parse body
sections, create metadata, or maintain a separate registry.

Design keeps its proposal in the task and leaves component pages unchanged;
validate reconciles them with the built code. When `[diagrams] enabled = true`,
design also draws the proposal as Mermaid diagrams in
`tasks/diagram_TASK-<id>.md` for the human. Nothing checks or reconciles that
file. The knowledge directory remains intentionally navigable without a
separate component manifest; `components` is a read-only projection of the
pages already present.

## Derived traceability

AEGIS derives relationships from durable references instead of maintaining a
link database:

```text
changed path -> affected_paths -> requirement -> linked_tests
task journal -> requirements -> requirements/specs/knowledge
```

The mapping supports `check`, `diagram`, `explain`, `trace`, and
`test --impacted`. Missing coverage is reported as a finding; it does not
silently create a replacement requirement or test.

`trace --format md` and `trace --format csv` export the requirement register,
including coverage, verification, tests, affected paths and ownership.
Output goes to stdout unless `--out PATH` is supplied. Exported Markdown/CSV is
a derived snapshot; edit requirements and regenerate it instead of treating
the export as a second register. `trace` has no JSON mode.

Integration candidate fingerprints cover Git-visible tracked and untracked
non-ignored files, excluding task journals/evidence and Python bytecode. They
do not cover ignored files, external inputs or submodule contents. Reviewers
must read journals separately; fingerprints are change-detection aids, not
tamper-proof attestations.
