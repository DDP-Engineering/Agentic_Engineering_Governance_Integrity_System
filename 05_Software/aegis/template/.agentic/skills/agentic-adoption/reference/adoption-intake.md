<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: adoption-intake

**Purpose:** Record one safe adoption slice before inspecting or changing it.

**Read first:**

- `<workflow> run status` and the current adoption-intake form.
- The repository instructions and configured workflow policy.

**Steps:**

1. Start with `<workflow> run start adoption`, or resume the selected run.
2. Run `<workflow> stage prepare` only when `run status` reports it as `next`.
3. Record the adoption slice, any explicitly approved bundle and rationale,
   access mode, summary, and unresolved questions.
4. Run `<workflow> stage apply`, review the imported state, then request human
   approval for `<workflow> stage close`.

**Outputs:**

- An applied adoption-intake form that bounds the discovery work.

**Done when:**

- [ ] [machine] The form records the adoption slice, bundle rationale, and access mode.
- [ ] [machine] The imported adoption-intake form has a digest.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Every adoption run begins with a recorded slice.

## If you are stuck

If the slice is unclear or would change runtime behaviour, stop and ask for a
smaller adoption slice or a standard development run.
