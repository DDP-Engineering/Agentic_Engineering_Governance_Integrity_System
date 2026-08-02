<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 02 — Artifacts and formats

Everything is a plain file, committed on the branch. One artifact = one
file. No run store, no evidence store, no schema versions beyond a single
integer per format.

## Directory layout (in the adopting repo)

```
.agentic/
  AGENTS.md                  # entry point (doc 01)
  steps/                     # stage step files (doc 01)
  aegis.py                   # companion CLI, single file (doc 03)
  aegis.toml                 # small config (below)
  requirements/
    functional/REQ-FUNC-3fa2.toml
    security/REQ-SEC-91c0.toml
    ...                      # eight category folders, created on demand
  specs/
    REQ-FUNC-3fa2.md         # optional, referenced by the requirement
  tasks/
    TASK-8b12.md             # one journal per task; kept after delivery
  knowledge/
    export.md                # one plain page per component, no manifest
  templates/
    requirement.toml  spec.md  task.md  component.md
```

## `aegis.toml` — the whole configuration

Deliberately tiny. No modes, no policy classes, no per-gate enforcement.

```toml
schema = 1

[commands]                # used by `aegis test` and `aegis check --run`
test = "pytest -q"
lint = "ruff check ."     # optional; any key here is just a named command

[layout]
source = ["src/"]         # globs; used by traceability heuristics
tests  = ["tests/"]

[check]                   # optional tuning of heuristics, all advisory
secret_patterns_extra = []
ignore = ["**/fixtures/**"]
```

## Requirement format

TOML (stdlib-readable via `tomllib`), one file per requirement. Random
hex-suffix IDs (decision D2) so parallel branches never collide:
`REQ-<CAT>-<8 hex>` as implemented (examples below use short ids for
readability). Categories keep the 2.x eight:
FUNC, UX, NFR, SEC, DATA, PLAT, REL, TEST.

```toml
schema = 1
id = "REQ-FUNC-3fa2"
title = "Export playlist as M3U"
status = "active"            # draft | active | retired
requirement = """
One requirement = one independently verifiable behavior, written
self-contained (no ticket numbers, no run IDs, no cross-references
that need external context to understand).
"""
verification = "How a human or agent confirms this behavior holds."
affected_paths = ["src/export/m3u.py"]
linked_tests   = ["tests/export/test_m3u.py::test_roundtrip"]
spec = "specs/REQ-FUNC-3fa2.md"   # optional
priority = "normal"               # optional: low | normal | high
rationale = ""                    # optional
created = 2026-08-02
updated = 2026-08-02
```

Required: `schema, id, title, status, requirement, verification`.
Everything else optional — `aegis check` warns on empty `linked_tests` for
`active` requirements but nothing blocks. The self-contained-prose rule
from 2.x is kept as a documented rule (and a heuristic: `check` flags
ticket-pattern strings like `#123`, `JIRA-`, `TASK-` inside requirement
prose).

## Spec format

Free markdown, one file, recommended sections (template-provided, not
validated): Behavior, Data/Interface, Examples, Acceptance. A spec exists
only when the requirement alone is not enough to build from.

## Component knowledge

One plain markdown page per component under `knowledge/`, named after the
component (`knowledge/export.md`). No `components.toml`, no manifest, no
baseline guard — the 2.x machinery is gone; the *content* stays, because a
one-page "how this works" is exactly what a small-context model should
load instead of re-reading a component's source.

Template sections (`templates/component.md`, recommended not validated):
**Purpose** (2–3 sentences), **Public interface** (entry points, formats),
**Key behaviors** (with requirement IDs where they exist), **Files** (the
paths that make up the component).

Wiring is one step, not a stage: `5_deliver.md` instructs "if this task
materially changed a component's behavior, update or create its page."
A staleness heuristic (knowledge pages whose listed files no longer
exist) may join the check catalog as #14 later; 0.1.0 ships without it.

## Task journal format

Markdown with a small key-value header the CLI can parse with a regex —
no YAML library needed, trivially editable by hand or by a 20B model.

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
- 2026-08-02 frame: scope agreed — M3U only, no PLS. Quick path rejected
  (new user-facing behavior → full path).
- 2026-08-02 specify: created REQ-FUNC-3fa2.
- 2026-08-02 build: test_roundtrip red as expected (missing module).
```

The journal is append-mostly: header lines change, log lines only get
added. It stays after delivery as the run's historical record (the 2.x
report/evidence trail collapses into this one file).

## Traceability model

Links live only on the requirement (`affected_paths`, `linked_tests`) and
on the task (`requirements:`). From these, `aegis check` derives
everything heuristically at read time — there is no link database:

- diff → requirements: changed files (git diff against the merge base)
  matched against every requirement's `affected_paths`.
- requirements → tests: `linked_tests` entries must resolve to existing
  files (test-ID suffixes after `::` are not verified — heuristic).
- task → requirements: IDs in the journal header must exist.

Unmatched changed source files produce a warning ("no requirement covers
src/x.py"), not a block. That is the heuristic heart of AEGIS Light:
the signal is always produced, the human/agent decides.

The same mapping, driven in reverse, powers focused regression: changed
files → impacted requirements → the union of their `linked_tests` is the
test set `aegis test --impacted` runs (doc 03). Keeping `affected_paths`
and `linked_tests` current is therefore not just bookkeeping — it is what
makes the fast inner loop possible.
