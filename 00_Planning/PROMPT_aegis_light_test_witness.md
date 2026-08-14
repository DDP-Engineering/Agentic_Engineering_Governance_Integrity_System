<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Implementation prompt — AEGIS Light test-integrity witness

You are implementing one feature in **AEGIS Light**, a single-file, stdlib-only
governance CLI. Work only in this repository. Do not touch full AEGIS
(`05_Software/aegis/`) or WAEGIS. Everything you need is under
`05_Software/aegis-light/`.

## Background you need

AEGIS Light guides an agent through stages: **frame → specify → design → build
→ validate → deliver**. The whole tool is `05_Software/aegis-light/template/.agentic/aegis.py`
(~2000 lines, Python ≥ 3.11, stdlib only). It is invoked as
`python .agentic/aegis.py <command>` from a target repo's root. It locates its
own `.agentic` from `__file__`, never from the working directory.

The **build** stage is test-first: the agent writes a test, watches it fail
("red"), records the failure, then implements until it passes ("green"). Today
that red record is **agent-authored prose** in the task journal `## Log`
(`.agentic/steps/4_build.md`, step 4 — it literally says *"This is an
agent-authored journal record, not independent proof."*). Nothing verifies it.

**The gap:** an agent can write a test, watch it go red, then quietly **edit the
test** so the trivial implementation passes — a fake red-to-green. The journal
would still read as a clean pass.

## What to build

A **test-integrity witness**: AEGIS itself hashes the test and source files at
the red moment, then at check time re-hashes and reports whether any **test file
changed after the witness was taken**. Because AEGIS computes the hashes (never
the agent), the agent cannot forge them. This is **detection, not prevention** —
it never blocks; it surfaces a warning and asks the agent to record why.

### Design posture (do not violate)

- **Advisory / non-blocking.** Findings are WARN/NOTE and never change the exit
  code except under the existing `--strict` + `[check] strict_promote` path,
  exactly like every other check in this tool.
- **Read-only git.** Reuse the existing read-only helpers. Never `git add`,
  stage, commit, or otherwise mutate the tree or index.
- **stdlib only.** You will need to add `import hashlib`. Nothing else new.
- **Windows and Linux.** Use the existing path/encoding conventions
  (`rel()`, forward-slash storage, UTF-8, LF).
- **Do not bloat the journal.** The hash maps live in a **sidecar JSON file**,
  never inline in `TASK-<id>.md`.

## Part 1 — `witness` command

Add a subcommand:

```
python .agentic/aegis.py witness --task TASK-<id>
```

Behavior:

1. Validate the task via the existing `read_journal(args.task)` (gives the
   journal and its parsed header; raises the one-line `UserError` on a bad id).
2. Determine the file sets from `[layout]` globs in `aegis.toml`
   (`cfg_table(cfg, "layout")` → `source`, `tests`; default `["src/"]`,
   `["tests/"]`). List **git-visible files** (tracked + untracked, non-ignored)
   under each glob. Reuse `run_git("ls-files", ...)` and `untracked_files()` —
   do not walk the filesystem directly, so `.gitignore` is honored the same way
   the rest of the tool honors it. Match paths with the existing `match_any()`.
3. Compute `sha256` of each file's bytes. Build two maps: `tests: {path: sha}`
   and `source: {path: sha}` (repo-relative, forward-slash keys, sorted).
4. Compute the **"source already differs from base"** signal: using the task's
   `base:` header commit, call the existing `collect_diff(cfg, base)` and record
   the changed files that match the source globs. If non-empty at witness time,
   red may not have been genuine (implementation already in place).
5. Write the sidecar file **`.agentic/tasks/TASK-<id>.witness.json`** (next to
   the journal; validate it stays inside `.agentic/tasks/` the same way
   `read_journal` does). Contents:

```json
{
  "schema": 1,
  "task": "TASK-<id>",
  "created": "YYYY-MM-DD",
  "base": "<commit or ''>",
  "head": "<git_head() at witness>",
  "source_already_differs": ["src/foo.py"],
  "tests":  {"tests/test_x.py": "<sha256>"},
  "source": {"src/x.py": "<sha256>"}
}
```

6. Print a one-line human summary, e.g.
   `witnessed 3 test file(s), 5 source file(s) at 1a2b3c4` (and, if
   `source_already_differs` is non-empty, a second line warning that source
   already differs from the task base). Support `--json` for a machine summary
   consistent with the existing `emit_json` envelope (`schema` = `JSON_SCHEMA`).
7. Re-running `witness` overwrites the sidecar (the agent may legitimately
   rewrite the test before implementing). This is acceptable; the
   `source_already_differs` signal is what catches a witness taken *after*
   implementation.

## Part 2 — integrity check at check time

Add one entry to the `CHECKS` catalog tuple (keep the existing shape
`(slug, description)`; the slug is stable vocabulary — never rename later):

```
("test-integrity", "test files are unchanged since the red witness was taken"),
```

Add the comparison to the check pipeline. It runs **only when a `--task` is in
scope and that task's sidecar exists** (no sidecar → emit nothing, so every
existing repo and the quick path stay unaffected). Put the logic where the
other task-scoped, diff-based checks live (`check_diff(...)`, called from
`run_checks(...)`), and gate it on `scope` being present. For the scoped task:

- Re-list and re-hash the current **test** files (same globs, same git-visible
  rule as `witness`).
- For each test path in the sidecar whose current sha **differs** → `WARN`
  `test-integrity`: `"<path> changed after the red witness — record why in ## Log"`.
- For each test path in the sidecar now **missing** → `WARN` `test-integrity`:
  `"<path> was removed after the red witness"`.
- New test files not in the sidecar → `NOTE` `test-integrity`:
  `"<path> added after the red witness"` (informational; adding tests is fine).
- If `source_already_differs` was non-empty → `WARN` `test-integrity`:
  `"source already differed from the task base when the witness was taken — the red may not have been genuine"`.

All advisory. A team that wants CI to fail on a moved test lists
`test-integrity` in `[check] strict_promote` — the existing machinery handles it
with no extra code.

## Part 3 — wire it into the workflow prose

- **`.agentic/steps/4_build.md`**: insert a new step immediately after the agent
  confirms the test fails for the right reason and *before* it implements:
  *"Run `python .agentic/aegis.py witness --task TASK-<id>` to record the
  red-state fingerprints. AEGIS hashes the test and source files itself; this is
  the independent record the journal line is not."* Add a matching
  `## Done when` line. Keep the existing agent-authored red log line — the two
  are complementary (the log says *why* it failed; the witness proves the test
  did not move).
- **`.agentic/steps/5_validate.md`**: note that `check` now reports
  `test-integrity`, and that a flagged test change must be explained in `## Log`
  or reverted.
- If a short digest of the workflow is duplicated anywhere in the payload
  (e.g. `AGENTS.md`), keep it consistent, but do not expand it.

## Part 4 — tests

Add tests under `05_Software/aegis-light/tests/` (match the style of
`test_check.py` and `test_cli_core.py`; they build throwaway git repos). Cover:

1. `witness` writes the sidecar with correct sha256 for known test/source files.
2. After `witness`, editing a test file → `check --task` reports one
   `test-integrity` WARN for that file; exit stays 0.
3. After `witness`, leaving tests unchanged → no `test-integrity` finding.
4. Removing a witnessed test → WARN; adding a new test → NOTE.
5. `source_already_differs`: witness taken when a source file already differs
   from base → WARN at check time.
6. No sidecar present → `check --task` emits no `test-integrity` finding
   (backward compatible), and the quick path (no `--task`) is unaffected.
7. `test-integrity` in `[check] strict_promote` makes `check --strict --task`
   exit 1 on a moved test; absent from the list, it exits 0.

Run the existing suite and keep it green:

```bash
cd 05_Software/aegis-light && python -m pytest -q
```

## Constraints — do not

- Do not make anything block or change a non-strict exit code.
- Do not run project tests, lints, or audits from `witness` — it only hashes.
- Do not mutate git (`add`/`commit`/`stash`) or write outside
  `.agentic/tasks/`.
- Do not add a third-party dependency.
- Do not store the hash maps inside the task journal markdown.
- Do not rename existing check slugs or change existing envelopes.

## Known residual (state it in a code comment, do not try to fix)

The agent controls *when* it calls `witness`. A test that was weak from birth,
or a witness taken after implementation, is only partially caught (by
`source_already_differs`). This is the same blind spot full AEGIS has; the
mechanism raises the cost of the common cheat (moving a test after red), it does
not make honesty provable.

## Definition of done

- `witness` command implemented, with `--task` and `--json`.
- Sidecar `.agentic/tasks/TASK-<id>.witness.json` written as specified.
- `test-integrity` check added, task-scoped, no-sidecar-safe, advisory,
  strict-promotable.
- `4_build.md` and `5_validate.md` updated.
- New tests added; full `aegis-light` suite green.
- One-line summary of what changed, ready for the task journal.
