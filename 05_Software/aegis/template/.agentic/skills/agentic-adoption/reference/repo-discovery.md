<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: repo-discovery

**Purpose:** Inventory repository facts needed to adopt one bounded slice.

**Read first:**

- `<workflow> run status`, the adoption-alignment form, and the current form.
- Only configured roots and local metadata needed for the selected slice.

**Steps:**

1. Run `<workflow> stage prepare` only when `run status` requests it.
2. Inventory source, test, requirement, and documentation roots; gates,
   components, dependencies, entry points, existing tests, and evidence.
3. Use `<workflow> verify traceability` and `<workflow> verify coverage` when
   useful. Record facts; do not change application behaviour.
4. Run `<workflow> stage apply`, review it, then request human approval for
   `<workflow> stage close`.

**Outputs:**

- An applied discovery form that supports component mapping.

**Done when:**

- [ ] [machine] Repository roots, gates, components, dependencies, and evidence are recorded.
- [ ] [machine] The imported discovery form has a digest.
- [ ] [human] The human approves stage close.

**Skip when:** Never. A component map needs recorded repository facts.

## If you are stuck

Record an unknown or inaccessible area as evidence and a question; request
broader access instead of inferring repository-wide facts.
