<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Example: Bug Fix

For “a sandbox adapter leaves stale state after rollback”:

1. Start `fix`; align on the exact production/sandbox contract.
2. Create an observable requirement for rollback and stale-state cleanup.
3. Design the internal change and parity behavior; approve `design.md`.
4. Add a check that uses the failing sandbox path and asserts response shape,
   rollback, and absence of stale state. Record actual failure as red.
5. Implement the approved cleanup; run the same check green and parity variants.
6. Impact analysis runs linked checks first and full regression if the adapter is
   shared, cross-cutting, or untraced.
7. Deterministic verification precedes diff review; validation closure activates
   the requirement; delivery closure records handoff only.

For a small, well-understood fix like this, start with
`aegis run start fix --quick` instead: it collapses to
intake → implementation → validation → delivery (four closes, not eight),
journals alignment/requirement/design/check as `bypassed` rather than
skipping them silently, and reports the collapsed stages' invariants and
audits as not applicable rather than passed. Gates, secrets scanning, scope
advisories, and working-tree review still run for real. If the fix later
turns out to need real requirement/design work, route back to a full run.
