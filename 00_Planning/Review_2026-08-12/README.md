<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS version 1 review — 2026-08-12

**Status:** Review record, ready for implementation
**Reviewed:** `05_Software/aegis`, `05_Software/waegis`, `02_Tools`, payload templates
**Against:** `AEGIS_PRODUCT_REQUIREMENTS.md`, `AEGIS_FUNCTIONAL_SPECIFICATION.md`,
`AEGIS_ARTIFACT_MODEL.md`, `AEGIS_CLI_MACHINE_PROTOCOL.md`,
`AEGIS_IMPLEMENTATION_PLAN.md`, `AEGIS_ACCEPTANCE_PLAN.md`, `00_Planning/templates/`
**Method:** static reading plus live field tests against real installs created by
`waegis install-apply`. Every finding marked *reproduced* was executed, not inferred.

## Contents

| Document | Purpose |
|---|---|
| `FINDINGS.md` | Every finding, with a concrete implementation for each |
| `DESIGN_RED_BEFORE_GREEN.md` | How red-before-green becomes unfakeable and honestly skippable |
| `DESIGN_FINGERPRINT_SCOPE.md` | What the test fingerprint covers, and the role of `.gitignore` |

## State at review time

Working: 190 tests green (AEGIS 166, WAEGIS 14, tools 10) on Python 3.12.13;
`ruff` clean on both packages; tests exercise the exact delivered payload bytes;
all 48 AEGIS operations implemented; the 56-operation catalog matches the protocol
document; a full ticket-to-Delivery run completes by hand; the non-blocking posture
is real — an empty Stage completes with findings and exit 0, there are no hooks
anywhere, and AEGIS runs only `symbolic-ref`, `rev-parse`, and `status`.

Not working: the red-before-green witness can be fabricated through a public
operation, which defeats the product's central promise. That single defect outranks
everything else in this pack.

## How to use this pack

Each finding is written to be implemented by an AI agent working alone. Every entry
carries the same seven fields:

- **Severity** — S1 critical, S2 high, S3 medium, S4 low.
- **Scope** — see the scope rule below.
- **Where** — the file and line to change.
- **Reproduce** — commands that show the current behavior.
- **Why** — the requirement or plan clause at stake.
- **Change** — the specific edit. Do the smallest thing that satisfies it.
- **Prove** — the test to add, with its intended name.
- **Do not** — the adjacent work that must stay out of the change.

Take one finding per Run. Do not batch S1 with anything else.

## Scope rule

This project applies a standing constraint: on full AEGIS, only defects and
workflow obstructions justify a change. No refactors, no added hardening, no new
gates — escape hatches are preferred over gates. Each finding is therefore
classified:

- **Defect** — the code contradicts a stated requirement or its own documentation.
  Implement.
- **Obstruction** — the code traps a developer or agent with no honest way forward.
  Implement.
- **Truthfulness** — a document claims something the software does not do. Correct
  the document, not the software.
- **Deferred** — real, but outside the constraint or awaiting an owner decision.
  Do not implement without explicit instruction.

A finding classified `Deferred` is recorded so it is not rediscovered. It is not a
work item.

## Suggested order

1. **F-01** — unfakeable red witness. Two lines, and nothing else matters until it is
   done.
2. **F-02**, **F-03** — the fingerprint scope and a Delivery report that records what
   actually happened. These complete the integrity story F-01 starts.
3. **F-04**, **F-05**, **F-07**, **F-13** — the obstructions: a Run that cannot be
   abandoned, a Stage stranded by revisit, a default test command that cannot pass, a
   delivered Run that reopens.
4. **F-08** through **F-12** — protocol and contract breaks. **F-11** and the first
   half of **F-19** belong in one Run; both edit the same help metadata, and together
   they are what lets an agent drive AEGIS without reading the runtime source.
5. **F-17**, **F-18** — documentation truthfulness. Cheap, and they stop the record
   drifting further from the software.
6. **F-14**, **F-19** through **F-22** — guidance and developer experience. Largest
   product effect per line changed, but none of it is a correctness risk.

**F-06** is withdrawn. **F-16** is deferred pending an owner decision. Neither is a
work item.

## This pack has been pruned once

Every proposed implementation was re-challenged with one question: *what is the
smallest change that removes the defect?* The answers moved a long way.

- The fingerprint fix lost a built-in denylist, a new configuration key and a
  reporting finding. It is now one call to `git ls-files`, because the repository's
  own `.gitignore` was always sufficient.
- The red-witness fix lost a new `provenance` field and three of its four steps. It
  is now a two-line strip loop.
- One finding was withdrawn as overstated, one deferred as not-a-defect, and three
  that offered "either this or that" now name one option.

Both design documents record what the first draft got wrong, not just the conclusion.
That is deliberate: an implementing agent that reads only the conclusion tends to
rebuild the discarded version. If a change starts growing past what its finding
describes, stop and re-read the **Do not** field — it is almost always already
written down there.

## One thing to keep in view

The product exists to guide a model and accompany a developer. Two measurements
from the field test are worth carrying into every change:

- What ships as guidance is 1,908 bytes of one-sentence Stage instructions, against
  22,412 bytes of structured per-Stage guidance in `00_Planning/templates/`. The
  guidance content of the templates was never implemented.
- A single `stage-show` at Delivery returns roughly 10,500 tokens for a trivial Run,
  about 29 percent of it duplicated between `stage_state` and the top-level keys.

Neither is a bug. Both decide whether the product is pleasant to use. Prefer changes
that move those numbers in the right direction, and never make them worse.
