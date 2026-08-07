<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Quick Runs and Bypassing AEGIS

AEGIS's full eight-stage lifecycle is deliberately thorough. Not every change
deserves that much ceremony — a one-line config fix, a typo, a genuinely
small bug does not need a design document. AEGIS has two first-class,
honestly-reported ways to move faster: **quick runs**, which shorten the
lifecycle itself, and **waivers**, which let you override one specific
blocked check when you have a real reason to. Both are designed so that
taking the shortcut is always visible in the record — never silently passed
off as if the full process happened.

## Quick runs: the proportional profile

```text
<workflow> run start fix --quick
<workflow> run start change --quick
```

`--quick` is valid only for `fix` and `change`. A `feature` or `adoption` run
cannot use it — those return a typed blocked response immediately rather than
silently ignoring the flag. The idea: a genuinely new feature or an adoption
effort is exactly the kind of work the full lifecycle exists for; a quick run
is for work that is small by nature, not work someone wants to rush.

A quick run keeps a shorter, explicit sequence:

```text
intake -> implementation -> validation -> delivery
```

Alignment, requirement, design, and check are not skipped quietly — at
intake close, AEGIS journals all four as `bypassed`, together with the human
approver, the intake revision, and the reason, in one recorded event. Every
later surface — run status, the validation summary, the delivery report —
repeats this state explicitly. Nothing ever reports bypassed work as
"passed." The four stages that do still run — intake, implementation,
validation, and delivery — each keep their full prepare/apply/close
lifecycle and still need your explicit approval at every close.

A natural way to offer this to a human: when the described work is genuinely
small, an agent should say so explicitly rather than defaulting to a full
run:

```text
small scope - suggest: <workflow> run start fix --quick
```

## What still applies during a quick run

Skipping alignment/requirement/design/check does not mean skipping
everything:

- **Changed paths and check evidence still matter.** New quick implementation
  begins with `<workflow> check create`; fill the run-local definition, then
  `<workflow> check register` before changing source. Requirement and
  specification citations are intentionally empty on this proportional path.
  Record a real red result, make the repair, then record green through
  `<workflow> check prepare`/`<workflow> check record` or
  `<workflow> check run <check-id>`. Link every active green check-evidence ID
  in `linked_check_evidence` before applying implementation. Manual evidence,
  invented IDs, superseded IDs, and other-stage evidence cannot substitute for
  a registered quick check.
- **Enabled gates, secrets scanning, and working-tree review still run** at
  validation, exactly as they would in a full run.
- **Red-before-green still applies to new quick runs.** The run-local check
  definition preserves the reproducing red result even though the ordinary
  check collection stage is bypassed. Only a historical quick graph that lacks
  the persisted policy reports INV-3 as `legacy-not-applicable`.
- **Requirement/check/design-dependent invariants and audits report
  `not-applicable`** with a null result — again, an honest "this doesn't
  apply here," never a silent pass.

## An optional guard against quick runs growing too large

A workspace can optionally configure a proportionality check so a quick run
does not quietly grow into something that should have been a full run:

```toml
[quick.changed_paths]
mode = "advise"
max_paths = 10
```

`mode` is `disabled` or `advise` (there is no `enforce` — this is guidance,
not a gate). If the table is absent entirely, the effective default is
`disabled` with a retained threshold of 10 paths. In `advise` mode, closing
quick-run implementation with more unique changed paths than the configured
maximum returns a `QUICK-SCOPE-ADVISORY` result and a suggestion to carry the
current context into a full `<workflow> run start fix` (or `change`) instead.
It never blocks the close, never re-routes the run, and never mutates
anything on its own — it is exactly what its name says: advice.

## Waivers: overriding one specific blocked check

Sometimes a check, gate, or invariant fails for a reason you understand and
have decided to accept for this run — a known, already-tracked issue in code
you are not touching, for instance. AEGIS supports recording that decision
explicitly instead of forcing you to either fix something unrelated or get
stuck:

```text
<workflow> waive list
<workflow> waive add <blocker-id> --reason "<human-approved reason>"
```

`waive list` reports every currently eligible blocker's exact ID, any
already-active waivers, and the complete run-local waiver history, each
classified as `active`, `stale`, or `inactive`. Eligible IDs include failing
invariants (for example `INV-10`), enforced gate failures (`gate:test`),
per-check red-before-green failures (`red-before-green:<check-id>`), and
specific stage, traceability, coverage, or working-tree findings.

`waive add` records one explicit human approval. The reason must contain real
text — an empty or whitespace-only reason is rejected — and the blocker ID
must be exact and currently eligible; there is no wildcard, bulk, or forced
waiver. AEGIS mints a `WVR-<uuid>` record, appends it to the run's state, and
journals a separate `waiver.added` event with who approved it and why.

A useful prompt shape for an agent facing an eligible blocker:

```text
This run has an eligible process blocker: <blocker-id>. Show me its exact ID
and the failure it covers from `<workflow> waive list`. Do not record a
waiver until I explicitly approve one, with a real reason.
```

### What a waiver does — and does not — do

A waiver neutralizes the *blocking* behavior of one specific failure. It does
not rewrite what actually happened:

- The underlying invariant still reports `holds=false`. The gate still has
  its failing evidence attached. Audit findings remain exactly as found.
- Every summary and the delivery report render the item as `WAIVED`, with
  its original reason and timestamp — never as `passed`.
- A waiver is scoped to the run and the exact blocker state at the moment it
  was recorded, including a digest of the pinned content it covers. If that
  content later changes — for example, the design a waived `INV-10` covered
  gets revised — the waiver goes stale and the blocker returns. You cannot
  waive something once and have it silently keep covering a moving target.
- A waiver does not shorten a run's lifecycle. Only an explicit `--quick`
  start does that. Waiving a blocker inside a full run does not turn it into
  a quick run, and it does not synthesize a stage that was never actually
  applied.

### What can never be waived

A narrow set of failures protect the integrity of AEGIS's own state, not the
correctness of your change — and are never eligible for a waiver at all:

- Malformed, unsupported, or closed-schema workflow, graph, stage, evidence,
  requirement, or integration state, including corrupted run identity or
  selection data.
- A live persistence-lock conflict.
- A stale graph or requirement mutation (someone else's write raced yours).
- Any atomic-publication or journal-integrity failure.

These never appear in `waive list` at all. If you hit one, the fix is to
correct the underlying state or retry the operation — there is no override,
because overriding it would mean trusting a record AEGIS can no longer
verify is intact.

## Why this is "guide, not gate"

Both mechanisms exist for the same reason: AEGIS should never be a wall you
have to work around quietly. A quick run and a waiver are both fully visible,
fully attributed, and fully honest about what they are — a documented
shortcut and a documented override, never a hidden pass. The alternative —
an agent editing files to route around a check, or silently skipping a stage
— is exactly what these features exist to make unnecessary.
