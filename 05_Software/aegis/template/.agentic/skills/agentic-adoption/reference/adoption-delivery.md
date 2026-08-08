<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: adoption-delivery

**Purpose:** Produce an adoption handoff without a Git or publication action.

**Read first:**

- `<workflow> run status`, baseline review, and the current adoption-delivery form.
- The reports and evidence recorded by the preceding stages.

**Steps:**

1. Run `<workflow> stage prepare` only when `run status` requests it.
2. Run `<workflow> verify invariants`, `<workflow> verify traceability`,
   `<workflow> verify coverage`, `<workflow> verify working-tree`, and
   `<workflow> adoption baseline` as applicable.
3. Record report and preflight references, the component/baseline summary,
   follow-up slices, risks, and handoff decision. Runtime behaviour changes block this stage.
4. Run `<workflow> stage apply`, review it, then request human approval for
   `<workflow> stage close`.

**Outputs:**

- An approved adoption handoff and report references.

**Done when:**

- [ ] [machine] The adoption report and preflight references are recorded.
- [ ] [machine] The handoff decision is approved.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Adoption completes through an explicit handoff.

## If you are stuck

Record a remaining gap and its follow-up slice. Do not push, publish, merge, or
change application behaviour from this stage.
