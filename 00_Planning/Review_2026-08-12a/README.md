<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS version 1 review — second pass, 2026-08-12a

**Status:** Review record
**Reviewed:** `05_Software/aegis`, `05_Software/waegis`, `02_Tools`, `07_Delivery`,
shipped payload templates and host adapters
**Against:** `AEGIS_PRODUCT_REQUIREMENTS.md` (226 `PR-*`),
`AEGIS_FUNCTIONAL_SPECIFICATION.md`, `AEGIS_ARTIFACT_MODEL.md`,
`AEGIS_CLI_MACHINE_PROTOCOL.md`, `AEGIS_IMPLEMENTATION_PLAN.md`,
`AEGIS_ACCEPTANCE_PLAN.md`
**Tree:** local `master`, uncommitted working tree, 213 tests green
(AEGIS 185, WAEGIS 16, tools 12) on Python 3.12
**Method:** static reading plus live field tests in throwaway repositories created
from the real payload. Every finding marked *reproduced* was executed. Nothing in
the repository was modified by this review.

## Relationship to `Review_2026-08-12`

That pack (`F-01`..`F-22`) is the first pass and remains the work list. This pack
does not restate it. It does three things the first pass could not:

1. **Verifies the in-flight remediation.** `F-03`, `F-04`, `F-05`, `F-09` and
   `F-13` are confirmed fixed by execution. `F-01` and `F-02` are confirmed sound
   *as written* — and both are shown to be insufficient for the property they
   exist to protect. See `G-01` and `G-04`.
2. **Walks all 226 `PR-*` requirements** rather than sampling. See
   `REQUIREMENTS.md`.
3. **Reports what the first pass did not reach** — 53 findings, none overlapping
   `F-01`..`F-22`.

Findings here are numbered `G-nn` so the two packs never collide.

## Verdict

**AEGIS v1 does what it was designed to do.**

The non-blocking posture is real and measured: an entirely empty Run reaches
`delivered` in 16 operations, exit 0 at every step, carrying 46 visible findings.
Atomic publication survives `os._exit(137)` at all four checkpoints with no partial
file and no stray temporary. Upgrade-then-remove is byte-identical on every
non-payload file. Offline and no-telemetry are proven statically *and* by a runtime
audit hook over nine live operations: network = 0, home = 0. AEGIS's entire Git
surface is four read-only verbs; WAEGIS's is `git init --quiet`. Branch-parallel
Runs merge with zero conflicts. Deleting the payload leaves the host project's own
suite passing.

Of 226 requirements, **19 are clearly unmet** — under 10%, concentrated in two
places: guidance that was designed but never shipped, and Adoption, which was
scoped out. The rest are met or partially met.

**One class of problem should not ship**, and it is the one the product exists to
prevent: in four places AEGIS records something that did not happen.

## The finding that matters

`F-01` shut the red door. **The green door is open and reaches the identical end
state.** A gutted test can be delivered as a clean red-to-green, certified by the
very block that was added to stop authors lying about it. Full reproduction in
`G-01`.

`F-01`'s remediation is correct and should land. But it does not close the finding
it describes, and the first pack reads as though it does. Do not mark the
red-before-green work complete on `F-01` alone.

The remedy stays detection-only, consistent with the product posture: record
whether a green was executed or merely reported, and have the Delivery record say
`fingerprint comparison: not performed` when no AEGIS-launched green exists. No
gate. No prevention.

## What to fix

Ranked by one principle: **AEGIS is allowed to be incomplete; it is not allowed to
lie or trap.**

| | Finding | Problem |
|---|---|---|
| 1 | `G-01` | A reported green bypasses the fingerprint comparison; a gutted test delivers clean |
| 2 | `G-02` | `--selection` records `failed` for a suite that passes, under the shipped default |
| 3 | `G-04` | The zone comparison walks the whole repository, so AEGIS accuses its own pytest cache |
| 4 | `G-05` | The Delivery record omits open findings — 46 of them, beneath prose reading "no findings" |
| 5 | `G-13` | Delivery is unreachable without reading the runtime Python source |
| 6 | `G-14` | One corrupt `run.md` hides every Run from `run-list` |

Items 1–4 are the same defect wearing four faces: the record asserts something that
did not happen. Item 3 matters for sequencing — `F-02`'s fix landed in
`_fingerprints`, but the identical defect sits untouched in the zone path. **Do not
close `F-02` without checking `workspace.py:300`.**

Items 5 and 6 are traps. Both block forward motion with no honest way through,
which is what this product was built not to do.

Three more in the same spirit, all cheap: `G-15` (`requirement-create` *refuses*
where an advisory finding already exists and is unreachable), `G-09` (exceptional
abandonment leaves `run.md` reading `active`, so an abandoned Run can be
re-selected and worked on), and `G-16` (`stage-show` at Delivery advertises
commands `execution-run` then refuses).

Everything else in `FINDINGS.md` is real but optional. It is recorded so it is not
rediscovered a third time, not because it is a backlog.

## The one theme behind the rest

Roughly two-thirds of the remaining findings are a single unmade decision: **the
guidance was designed and never shipped.**

| | Bytes / count |
|---|---:|
| Shipped stage-instruction prose, all 8 stages | **1,856 chars** |
| `00_Planning/templates/` stage templates | 22,412 |
| Shipped as a fraction of designed | **8.3%** |
| Operations requiring `--expected-revision` | 24 of 56 |
| …that mention it in help | **0** |
| Operations requiring `--input` | 21 |
| …that document a `data` field | **0** |
| `grep aegis.machine.input` over everything shipped | **0 hits** |
| Closed enums gating input | 6 |
| …that enumerate their values in help or `error.details` | **0** |

Measured end to end: driving AEGIS to Delivery using **only** what ships hit **17
points of insufficiency** — 9 requiring the runtime Python source, 4 requiring a
planning document that is not delivered, 3 blind trial-and-error, 1 unworkaroundable.
Two of the source reads are hard blocks: without them the terminal state is
unreachable.

That is one product decision, not thirty bugs. It is also the decision that most
directly serves what AEGIS is for.

## What to delete rather than build

Some unmet requirements are the code being right and the specification being wrong.
Cutting these removes work without removing value:

- **PR-REQ-002** (EARS phrasing). No trace anywhere in the payload. Mandating a
  grammar is ceremony, and the requirement is `Should`.
- **PR-ADOPT-002/003/004** (automatic component, requirement and test discovery).
  Deliberately out of scope. Record the deferral in a release record rather than
  carrying three permanent `NOT MET` rows.
- **PR-TRACE-012/013/014/015/016**. Agent-guidance prose that cannot be verified by
  any test. These are guidance, not requirements, and should live in the stage
  instructions the product actually ships.
- **PR-WORKFLOW-005 / FS-PROFILE-003** (the `short` profile). As shipped it removes
  Design only — 6 of 52 sections. It is not a proportional path. Real
  proportionality already comes from `stage.skip`, which works and is fully
  exercised. Either make `short` genuinely short or drop the claim.

## How to use this pack

`FINDINGS.md` keeps the first pack's seven-field shape for every S1 and S2 entry, so
an agent can implement one alone:

- **Severity** — S1 critical, S2 high, S3 medium, S4 low.
- **Scope** — Defect / Obstruction / Truthfulness / Deferred.
- **Where** — file and line.
- **Reproduce** — what was executed.
- **Why** — the requirement clause at stake.
- **Change** — the smallest edit that satisfies it.
- **Do not** — the adjacent work that must stay out.

S3 and S4 entries are compact: where, what, why, fix.

Take one finding per Run. Do not batch `G-01` with anything.

## Scope rule

The standing project constraint applies: on full AEGIS, only defects and workflow
obstructions justify a change. No refactors, no added hardening, no new gates —
escape hatches are preferred over gates. Where a requirement asks for prevention,
this pack proposes detection instead, every time.

## Two numbers to carry into every change

- Shipped agent guidance is **8.3%** of what was designed.
- **32–42%** of every `stage-show` response is truncation bookkeeping emitted when
  nothing was truncated — 5,356 of 12,725 bytes on an empty Run's Intake read.

Neither is a bug. Both decide whether the product is pleasant to use. Prefer changes
that move them in the right direction, and never make them worse.

## A note on review volume

This is the sixth AEGIS review since late July, and each has landed on roughly
twenty findings while the actual trend line improved — 190 tests green at the first
pass, 213 now, with five `F-*` items verifiably fixed. A constant finding rate
against improving software is an artifact of the review method, not a property of
the code. Read the verdict and the six-item list. The rest is a record.

## Contents

| Document | Purpose |
|---|---|
| `README.md` | This document — verdict and action list |
| `FINDINGS.md` | All 53 findings with reproductions |
| `REQUIREMENTS.md` | All 226 `PR-*` verdicts, plus `IP-*` slice status |
