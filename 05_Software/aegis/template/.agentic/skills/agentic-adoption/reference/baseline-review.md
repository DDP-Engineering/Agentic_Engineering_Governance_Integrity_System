<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: baseline-review

**Purpose:** Classify the adopted slice against its configured engineering baseline.

**Read first:**

- `<workflow> run status`, the component-adoption form, and the current form.
- The component manifest, baseline policy, and recorded requirements and tests.

**Steps:**

1. Run `<workflow> stage prepare` only when `run status` requests it.
2. Run `<workflow> adoption baseline` when available and review ownership,
   mapped paths, known gates, and traceability.
3. Classify gaps as blocking, follow-up, or accepted legacy risk. Record the
   approved decision; preserve behaviour-changing work for a development run.
4. Run `<workflow> stage apply`, review it, then request human approval for
   `<workflow> stage close`.

**Outputs:**

- An applied baseline review with a safe next-step decision.

**Done when:**

- [ ] [machine] Reviewed components and remaining baseline gaps are classified.
- [ ] [machine] The baseline-review decision is approved.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Delivery needs an explicit baseline assessment.

## If you are stuck

Leave a legacy gap visible as a follow-up or accepted risk. Do not hide it by
changing scope or by enabling a stricter policy before its seed work is recorded.
