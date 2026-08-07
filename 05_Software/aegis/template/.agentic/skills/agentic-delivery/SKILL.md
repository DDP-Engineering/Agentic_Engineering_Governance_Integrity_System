---
name: agentic-delivery
description: AEGIS delivery-stage validation and human handoff. Use for final reports and for separately approved Git push, PR, merge, or publication work.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Delivery

# Stage: delivery

**Purpose:** Produce a reviewed handoff and mark the run complete without
pushing, publishing, merging, or opening a pull request.

**Read first:**

- `AGENTS.md`, then `<workflow> run context --json` for the selected run.
- Only `required_reads`: the named delivery router, current form, and retained
  previous form.
  If `unavailable_current_artifact` is present, run only its recovery command;
  never prepare an already applied stage. Use `run status` only for detailed
  diagnosis.

**Steps:**

1. Run `<workflow> stage prepare` only when `run context` names it.
2. If validation is not closed, complete it first: run `<workflow> verify run`,
   review its summary and the diff, apply the validation form, and request its
   human close approval.
3. Complete the delivery form with preflight and report references, remaining
   risks, and the handoff decision. Run `<workflow> delivery show` and
   `<workflow> delivery report`.
4. Run `<workflow> stage apply`, review the imported state, then request human
   approval for `<workflow> stage close`.

**Outputs:**

- An approved delivery handoff and final run report.

**Done when:**

- [ ] [machine] The preflight and delivery report references are recorded.
- [ ] [machine] The handoff decision is approved.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Every standard run completes through a delivery handoff.

## If you are stuck

Record a remaining risk or route back through the control form. After AEGIS
completion, stage only explicitly intended paths and request separate, explicit
approval before every outward action.
