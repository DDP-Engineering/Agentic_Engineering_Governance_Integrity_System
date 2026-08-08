<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: adoption-alignment

**Purpose:** Agree the adoption outcome, boundaries, risks, and decision.

**Read first:**

- `<workflow> run status`, the adoption-intake form, and the current form.
- Only source needed to distinguish discovered behaviour from desired behaviour.

**Steps:**

1. Run `<workflow> stage prepare` only when `run status` requests it.
2. Record understanding, in/out scope, assumptions, acceptance criteria,
   questions and recommendations, planned paths, risk, and decision.
3. Keep discovery facts separate from any requested future behaviour.
4. Run `<workflow> stage apply`, review it, then request human approval for
   `<workflow> stage close`.

**Outputs:**

- An applied adoption-alignment form with an explicit safe boundary.

**Done when:**

- [ ] [machine] The form records adoption scope, acceptance criteria, risks, and a decision.
- [ ] [machine] The imported adoption-alignment form has a digest.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Adoption still requires an explicit boundary.

## If you are stuck

Route back through the control form when discovery invalidates the recorded
scope; do not broaden the slice silently.
