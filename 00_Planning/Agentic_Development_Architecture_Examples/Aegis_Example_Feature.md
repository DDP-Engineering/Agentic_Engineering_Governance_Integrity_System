<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Example: Feature

1. `aegis run start feature`; edit intake and close after approval.
2. Capture alignment/acceptance in its form; apply and close.
3. Use `stage add` for atomic observable requirements and companion examples.
4. Discuss alternatives; record selected architecture in authoritative
   `design.md`; cite requirement IDs; apply and close.
5. Generate checks for success, errors, boundaries, state transitions, and
   applicable variants. Record red evidence.
6. Implement only the approved design; record changed paths and green evidence.
7. Run `aegis verify run`, then review diff/documentation/style and close
   validation. Eligible requirements activate automatically.
8. Complete delivery handoff and close. No Git publication occurs.

`--quick` is not available for `feature` (only `fix`/`change`): a new feature
always walks all eight stages. If any gate, invariant, or working-tree finding
blocks a stage close and the human judges it a deliberate exception, record a
one-time reason with `aegis waive add <blocker-id> --reason "..."`; the report
still shows it as `WAIVED`, never as passed. Corrupted or invalid graph/schema
state, lock conflicts, and stale-update conflicts cannot be waived.
