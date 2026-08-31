<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 02 - Artifacts and formats

AEGIS stores its durable state as ordinary UTF-8 Markdown, TOML, and JSON
files in the repository. There is no database, service, or hidden evidence
store.

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

The mapping supports `check`, `diagram`, `explain`, and
`test --impacted`. Missing coverage is reported as a finding; it does not
silently create a replacement requirement or test.
