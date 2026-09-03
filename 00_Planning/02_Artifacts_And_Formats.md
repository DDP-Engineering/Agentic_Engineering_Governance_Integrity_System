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
```

Exactly 15 files are managed by the payload: `AGENTS.md`, `CLI.md`,
`LICENSE.txt`, `aegis.py`, seven step files, and four templates. A payload
upgrade replaces only those managed files. It preserves `aegis.toml`,
requirements, specs, tasks, anchors, evolution reports, and knowledge pages.
Run `python .agentic/aegis.py init` after a payload update to refresh the
managed root digests in `AGENTS.md`, `CLAUDE.md`, and `QWEN.md`.

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
AEGIS caches, refusing added, edited or missing content. The 15-file core
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
recovery; durable findings, decisions and validation evidence still belong in
the repository journal.

## Configuration

`aegis.toml` is written once by `init` and belongs to the repository
thereafter. The implemented configuration surface is:

| Section | Keys and behavior |
|---|---|
| `[commands]` | `test` is the full suite; `test_impacted` may use `{tests}`; any other plain name is available to `check --run`. `timeout` is the default per-command limit and `workdir` selects an application subdirectory. |
| `[timeouts]` | Optional per-command limits overriding `[commands] timeout`. A timeout means the command proved nothing; it is not reported as a test failure. |
| `[layout]` | `source`, `tests`, and optional `docs` globs drive traceability/layout checks. `default_branch` can select the diff base. |
| `[review]` | Exact Boolean `enabled` (default `false`) and integer `max_fix_cycles` from 0 through 5 (default 2). |
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

## Requirements and specifications

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
Specs are optional Markdown detail used only when a requirement is not enough
to implement safely.

## Journals, evidence, and knowledge

A task journal has a machine-readable header followed by a current checklist
and append-only log. Its header records `stage`, `type`, `path`,
`requirements`, optional `parent`, `branch`, `base`, and `opened`.

The journal may additionally hold:

- `## Rulings`: append-only `RULING-001` records with date, decision,
  reason, source, and optional `supersedes`.
- `## Handoff`: replaceable resume fields `current`, `status`, `next`,
  `must_read`, and `blockers`.
- `## Stage report`: replaceable latest result with changes, evidence,
  issues, next action, user need, and review fields.

`anchor --task` writes `TASK-<id>.anchor.json`, a SHA-256 starting-point
fingerprint. `evolution --task` writes the corresponding
`TASK-<id>.evolution.json` comparison. These are durable inspection
evidence, not a replacement for review.

Each component page under `knowledge/` documents purpose, public interface,
key behaviors, architecture, and files. Validate updates a materially changed
component page. It is intentionally a navigable folder, not a separate
component manifest.

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
