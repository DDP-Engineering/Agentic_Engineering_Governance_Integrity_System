<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: component-map

**Purpose:** Map the selected repository slice into approved component boundaries.

**Read first:**

- `<workflow> run status`, the discovery form, and the current component-map form.
- `.agentic/components.toml` when it already exists.

**Steps:**

1. Run `<workflow> stage prepare` only when `run status` requests it.
2. Create or update the component manifest with names, paths, status, and
   baseline notes. Record the components and approved slice in the form.
3. Use `<workflow> adoption component-status` and `<workflow> adoption baseline`
   for inspection when available; classify unknown or risky boundaries honestly.
4. Run `<workflow> stage apply`, review the decision, then request human
   approval for `<workflow> stage close`.

**Outputs:**

- A component manifest and an applied component-map form.

**Done when:**

- [ ] [machine] The component manifest, mapped components, and approved slice are recorded.
- [ ] [machine] The component-map decision is approved.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Component adoption needs an approved map or slice.

## If you are stuck

Keep an uncertain boundary unmapped and request a smaller slice; do not expand a
component to make the map appear complete.
