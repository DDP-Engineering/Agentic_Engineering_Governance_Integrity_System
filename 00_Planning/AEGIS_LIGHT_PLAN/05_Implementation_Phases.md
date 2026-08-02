<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 05 — Implementation phases

Six phases, each sized for one agent session with a clear acceptance
check. Fresh tree at `05_Software/aegis-light/` (D0 ratified); nothing is
imported from the 2.x payload — text may be *rewritten* from it, code may
not be copied. Total effort estimate: 4–6 focused sessions plus a pilot.

Repo layout for the product itself:

```
05_Software/aegis-light/
  template/.agentic/        # the payload that `aegis init` copies
  tests/                    # pytest suite incl. structural budget tests
  README.md
```

## P1 — Workflow docs (the product's core)

Write `AGENTS.md`, the six step files (`1_frame` … `5_deliver`, `adopt`),
and the four templates (`requirement.toml`, `task.md`, `spec.md`,
`component.md`), following docs 01/02 of this plan. `5_deliver.md` must
include the component-knowledge update step; `adopt.md` must describe the
three-phase flow (survey / per-component / close) from doc 01.

*Acceptance:* every step file follows the fixed skeleton; `AGENTS.md`
≤ 150 lines and defines the two interaction modes (checkpoint default,
autopilot) with their stop points; total docs ≤ 1,200 lines; a cold read of `AGENTS.md` alone is
enough to know where every artifact lives and how to resume a task.

## P2 — CLI core: scaffolding and state reading

`aegis.py` with `init`, `task new`, `req new`, `status`; `aegis.toml`
parsing; ID generation (collision-checked against existing files);
journal header parser (regex-based); all paths `pathlib`, LF output.

*Acceptance:* on Windows and Linux, `init` into an empty repo then
`task new` + `req new` + `status` round-trips; `init` creates-or-appends
the digest-style root pointer files (`AGENTS.md`, `CLAUDE.md`, `QWEN.md`)
without clobbering existing content; re-running `init` is a no-op on
user-edited files and never overwrites an existing `aegis.toml`; the
payload-owned vs user-data ownership split from doc 03 is honored; unit
tests for ID and header parsing.

## P3 — Check engine

The 13-check heuristic catalog from doc 03: format checks, diff-based
traceability (merge-base via `git merge-base`, pure subprocess), hygiene
checks, the finding line format, and the summary.

*Acceptance:* fixture repo in tests exercises every check both firing and
silent; `check` always exits 0; output lines match the documented format;
runtime < 2 s on a 1,000-file repo.

## P4 — Strict mode, runner, report

`check --strict` with `strict_promote`; `--run` executing `[commands]`
with timeout and captured tail; `aegis test` including `--impacted`
focused-regression selection (changed files → impacted requirements →
union of `linked_tests`, with full-suite fallback); `aegis report`
appending the delivery summary to a journal.

*Acceptance:* strict exit codes correct for error/promoted-warning/clean;
a killed command reports and does not corrupt the journal; report content
matches doc 02's journal example structure.

## P5 — Structural guards and packaging

Anti-regrowth tests (idea borrowed from the WAEGIS V2 plan, minus size
policing — there is no line-count test; see the product goals in doc 00):
forbidden identifiers in `aegis.py` (`hook`, `waiver`, `evidence_form`,
`transaction`, `journal_store`, `permissionDecision`), forbidden imports
(anything outside the standard library), and a test asserting `check`
never exits non-zero without `--strict`. Add a `.gitignore` for the tree
(`__pycache__/`, `.pytest_cache/`). Write `README.md` for the tree
against the eight product goals; version 0.1.0.

*Acceptance:* full suite green on Windows + Linux (CI or manual on both);
the guard tests fail when a hook file, a non-stdlib import, or a
non-strict non-zero exit is introduced on purpose (verify by mutation,
then revert).

## P6 — Pilot and calibration

Adopt AEGIS Light in one small real repo (candidate: one of the Mancer
projects on a throwaway branch) and run one full-path feature task and one
quick-path fix task end-to-end — at least the build stage driven by a
local model (Qwen3-27B class) to validate the doc-04 context budgets.

*Acceptance:* both tasks delivered with journals telling the whole story;
a written friction list; every doc-04 budget line verified against real
token counts; plan documents updated with what changed.

## Non-goals for 0.1.0

No WAEGIS integration, no adapter hook files, no upgrade tooling beyond
re-`init`, no RepoWise integration, no PDF/report exports. Revisit only
after the pilot proves the core loop.

JSON output was on this list until a real consumer appeared; `check
--json` and `status --json` now ship (doc 03 records the contract).
