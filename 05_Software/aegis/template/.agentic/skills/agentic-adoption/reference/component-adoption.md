<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: component-adoption

**Purpose:** Capture durable component knowledge without changing runtime behaviour.

**Read first:**

- `<workflow> run status`, the approved component map, and the current form.
- Component documentation, requirements, tests, and ownership for the selected slice.

**Steps:**

1. Run `<workflow> stage prepare` only when `run status` requests it.
2. Work only in the approved component scope. Use
   `<workflow> adoption scope-check <paths>` when the manifest is available.
3. Update component documentation, requirement links, known tests, and adoption
   notes. Add existing behavioural contracts with `<workflow> stage add --category <category>`.
4. Record adopted components, paths, documentation, links, gaps, and behaviour
   status. Stop if runtime behaviour would need to change.
5. Run `<workflow> stage apply`, review it, then request human approval for
   `<workflow> stage close`.

**Outputs:**

- Applied adoption metadata and optional Planned requirements for the slice.

**Done when:**

- [ ] [machine] The approved component scope, documentation, links, and gaps are recorded.
- [ ] [machine] The adoption preserves runtime behaviour.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Move behaviour changes to a standard development run.

## If you are stuck

If scope-check reports an unmapped path, return to component-map or request an
approved scope change; do not use adoption to implement the change.
