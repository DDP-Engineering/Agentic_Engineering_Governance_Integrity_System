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
