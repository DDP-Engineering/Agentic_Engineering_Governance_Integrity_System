<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light — plan overview

Status: **IMPLEMENTED** — phases P1–P5 complete and hardened through
three external review rounds; P6 (pilot) is the remaining phase. The
built product lives at `05_Software/aegis-light/`; user documentation at
`06_SoftwareDocu/AEGIS-Light/`. This plan is kept as the design record —
where it and the payload disagree, the payload is authoritative.
Date: 2026-08-02.
Name: **AEGIS Light** (ratified 2026-08-02, decision D0; alternatives
considered: LAEGIS, PELTA, Companion AEGIS).

## Why

AEGIS 2.1 is a governance *enforcer*: ~13,500 lines of CLI, ~1,200 lines of
hooks across 7 scripts, 8 blocking stages, 5 enforced gate groups, 9
verification dimensions, waiver machinery, evidence forms, and a run graph.
Every deviation is a blocking point. For a solo developer or a small team who
just wants an agent to build software *with* discipline rather than *under*
guard, this is unattractive: the ceremony costs more than the risk it retires.

The early AEGIS payloads (0.5.0-era) were closer to the right weight:
markdown requirements, a small CLI, a few hooks. AEGIS Light returns to that
weight class deliberately, and goes further: **no hooks at all, nothing
blocks the agent mid-flight**.

This is a fresh product, not a migration. **No backward compatibility** with
the 2.x payload, its schemas, its run store, or its CLI surface. It does not
replace AEGIS 2.x — heavy AEGIS remains the right tool where enforcement is
a requirement; Light is the tool where guidance is enough.

Note: `00_Planning/WAEGIS_V2_PLAN/` is a different effort (slimming the
*installer wizard* while keeping the heavy payload). This plan slims the
*payload itself*.

## Thesis

> The workflow lives in agent instructions, not in enforcement machinery.
> Git is the state store, the sync layer, and the undo.
> Checks are advisory signals the agent reads and self-corrects against;
> the only hard gate is at merge time, in CI, if the team wants one.

Concretely:

1. **Guidance over enforcement.** The lifecycle is defined in an
   `AGENTS.md` plus one short markdown file per stage — plain steps any
   agent (Claude Code, Codex, Qwen Code, a local model) can follow. No
   PreToolUse/PostToolUse hooks, no permission denials, no fail-closed
   transports.
2. **Advisory by default.** One command, `aegis check`, runs every
   heuristic (traceability, links, formats, secrets, staleness) and prints
   a compact report. It always exits 0. `--strict` exists for CI only.
3. **Git as the transaction and collaboration layer.** All state —
   requirements, specs, task journals — is plain files committed on the
   branch. Resume = read the task file. Another machine = pull. Undo =
   git restore. (Same thesis the WAEGIS V2 plan ratified for the wizard.)
4. **Small-model friendly.** Every file an agent must read for one step
   fits comfortably in a 32k-context session (Qwen3-27B, gpt-oss-20B).
   Cross-file consistency is the CLI's job, not the context window's.
5. **One artifact = one file.** Merge-friendly by construction; parallel
   branches touch disjoint files.

## What is kept from AEGIS

- A staged lifecycle (condensed: see `01_Workflow_And_Stages.md`).
- Requirements as durable, verifiable, self-contained statements (TOML,
  one file each) with categories, linked tests, and affected paths.
- Optional per-requirement specs (markdown).
- Component knowledge pages (plain markdown under `.agentic/knowledge/`,
  one per component — the content survives; the `components.toml`
  manifest and baseline-guard machinery do not).
- Traceability: diff → requirements → tests, reported heuristically.
- Test-first as a *recommended practice* in the build stage.
- A delivery report and a task journal.
- Windows + Linux, all major agent CLIs.

## What is deliberately dropped

All 7 hook scripts and every adapter hook wiring; the gates engine, gate
modes, and waiver system; evidence forms and the evidence store; stage
forms and the run graph; the invariants engine; red-before-green
*enforcement* (kept as guidance); the 7-stage adoption flow (replaced by a
one-page adoption step); the `workflow.toml` schema-3 policy system; the
WAEGIS wizard as a prerequisite (install is a copy + `aegis init`).

## Product goals (the measure of success — not size metrics)

1. A good **companion** governance system: advises, records, never blocks.
2. **Simple to adopt**: copy one folder, run `aegis init`, read one page.
3. **Stable**: stdlib-only single-file CLI, no external dependencies, no
   hooks, plain-file artifacts that survive tool churn.
4. **Windows and Linux**, identical behavior.
5. **Online and offline agents**: frontier CLIs and local small models
   (32k context) are both first-class operators.
6. **Interruptible**: any session can stop at any point; a later session
   — any machine, any model — resumes from the task journal.
7. **Team-deployable**: developers on separate branches and computers;
   merges stay clean by construction (one artifact = one file,
   collision-free IDs).
8. **Easy to understand**: an engineer reads `AGENTS.md` once and knows
   the whole system.

Smallness serves these goals — small docs fit small contexts, a small
CLI stays auditable — and the design keeps everything lean, but there is
**no enforced line ceiling**. What P5 enforces structurally instead is
the *philosophy*: no hooks, no enforcement machinery, stdlib-only, and
advisory-by-default (`check` exits 0 without `--strict`).

## Plan documents

- `01_Workflow_And_Stages.md` — the agent-oriented stage model, step files,
  quick path, session resume.
- `02_Artifacts_And_Formats.md` — directory layout, requirement/spec/task
  formats, traceability model.
- `03_Companion_CLI.md` — the advisory CLI: commands, heuristic check
  catalog, strict/CI mode.
- `04_Collaboration_And_Small_Models.md` — multi-user/multi-branch/
  multi-machine model; context budgets for 32k–256k local models.
- `05_Implementation_Phases.md` — agent-ready implementation phases with
  acceptance criteria.

## Decision points (owner ratification needed)

- **D0 — Name and location. RATIFIED 2026-08-02:** name **AEGIS Light**,
  payload name `aegis-light`, new tree at `05_Software/aegis-light/`,
  versioning starts at 0.1.0.
- **D1 — Stage model.** Recommended: 5 stages (frame, specify, design,
  build, deliver) with a 3-stage quick path. Alternative: keep the eight
  2.x stage names as thin step files.
- **D2 — Requirement IDs.** Recommended: short random suffix
  (`REQ-FUNC-3fa2`) so parallel branches never collide. Alternative:
  sequential numbers plus a post-merge duplicate check.
- **D3 — Secret scan.** Recommended: keep it, but only as an advisory
  heuristic inside `aegis check` (never a hook).
- **D4 — Installer.** Recommended: no wizard; install = copy
  `template/.agentic/` + `aegis init` (pointer files, default config,
  data folders); upgrade = re-copy payload-owned files + `git diff`
  review (ownership split in doc 03). WAEGIS stays with the heavy
  payload only.
