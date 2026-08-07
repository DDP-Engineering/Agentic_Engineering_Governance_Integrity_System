<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Upgrading AEGIS 1.x to 2.x

`How_To_Start_A_New_Project.md` §10 states that an in-place AEGIS 1.x → 2.x
upgrade is unsupported and that a fresh 2.x deployment should be made "after
preserving project-owned artifacts deliberately" — without saying which
artifacts those are. This document is that missing procedure: what to keep,
what to replace, and the one config edit in between.

There is no `waegis upgrade` command and none is planned; a 1.x installation
and a 2.x installation are two independent deployments joined by copying the
project-owned artifacts below from the old one into the new one.

## What is payload-owned (replace) vs. project-owned (preserve)

| Payload-owned — replace with the new 2.x deployment | Project-owned — copy forward unchanged |
|---|---|
| `.agentic/cli/`, `.agentic/tools/`, `.agentic/hooks/`, `.agentic/documents/`, `.agentic/skills/`, `.agentic/integrations/` | `.agentic/requirements/` |
| `.agentic/LICENSE.txt` | `.agentic/components.toml` |
| The five host-adapter directories (`.claude/`, `.codex/`, `.qwen/`, `.pi/`, `.opencode/`) | `.agentic/knowledge/` |
| `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `opencode.json` | `.agentic/reports/` |
| | `.agentic/specs/` |
| | `.agentic/runs/` |

Payload-owned material is whatever a fresh `waegis new` / `waegis adopt` would
generate on its own — deploy the new version of it and discard the 1.x copy
outright rather than diffing the two. Project-owned material is what the
project authored inside that structure — deploy the new payload first, then
copy each project-owned path from the 1.x checkout into the new tree,
overwriting the payload's placeholder copies where one exists (for example an
empty `.agentic/components.toml`).

`.agentic/runs/` is listed as project-owned for continuity, but see
"Requirement snapshots carry over untouched" below for the one exception: a
run in flight under the 1.x schema cannot be resumed by the 2.x CLI and should
be finished or abandoned on the 1.x deployment before cutting over.

## The schema-2 → schema-3 config delta

`.agentic/workflow.toml` is project-owned, so it survives the copy — but it
was written against schema 2 and the 2.x CLI's `config validate` rejects
anything that is not `schema_version = 3` outright (`CONFIG-SCHEMA-UNSUPPORTED`
— AEGIS does not migrate configurations for you). The delta is two mechanical
edits:

1. **Bump the version.**

   ```toml
   schema_version = 3
   ```

2. **Add the `[interface]` table.** Schema 2 had no file-first interface
   policy to declare; schema 3 requires one:

   ```toml
   [interface]
   stage_form_retention = "latest"    # "versioned" | "latest" | "discard"
   check_execution = "external"       # "external" | "managed"
   ```

3. **Split the single `[gates]` table into one `[gates.<group>]` table per
   group.** Schema 2 configured all gate commands under one `[gates]` table;
   schema 3 requires a separate table per group, each with its own `mode` and
   `commands`:

   ```toml
   [gates.build]
   mode = "disabled"
   commands = []

   [gates.typecheck]
   mode = "disabled"
   commands = []

   [gates.lint]
   mode = "disabled"
   commands = []

   [gates.test]
   mode = "disabled"
   commands = []

   [gates.security]
   mode = "disabled"
   commands = []
   ```

   Carry each group's prior `mode` and `commands` into its own table; nothing
   about gate *policy* changed, only how it is declared.

Run `aegis config validate` after each edit — the error messages name the
offending key, its current value, and the expected shape one at a time, so
expect to iterate a few rounds rather than getting everything right in one
pass. That is expected, not a sign the migration is going wrong.

## Requirement snapshots carry over untouched

**The requirement store needs no migration.** Every `schema_version = 1`
requirement TOML under `.agentic/requirements/` reads cleanly under the 2.x
CLI, and `aegis requirement list` returns them unmodified — durable
requirement records are versioned independently of the workflow config schema
and were not part of the 2.x schema change. Copy `.agentic/requirements/`
forward as-is; there is nothing to convert.

## After the copy

1. Run `aegis config validate` and resolve each reported key in turn until it
   reports `status: ok`.
2. Run `aegis requirement list` and confirm the expected count of legacy
   requirements is present.
3. Start (or resume, if one was already in flight before the cutover) a run on
   the new deployment as usual.
