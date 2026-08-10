<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Current-state summary stored at .agentic/runs/<run-id>/run.md by default.
Stage details live in the eight sibling Stage files. The local context pointer
selects the Run only; this file's current_stage selects the working Stage.
-->

+++
schema = 1
artifact_type = "run"
id = "RUN-00000000000000000000000000000000"
status = "active" # active | delivered | abandoned
current_stage = "intake"
work_type = "feature" # feature | change | quick_fix | bug_fix
profile = "full" # full | short
opened_at = 2026-01-01T00:00:00Z
updated_at = 2026-01-01T00:00:00Z
opened_branch = "<branch name or detached>"
requirement_ids = []
component_ids = []

[[stages]]
sequence = 1
name = "intake"
path = "01-intake.md"
status = "active"
updated_at = 2026-01-01T00:00:00Z

[[stages]]
sequence = 2
name = "alignment"
path = "02-alignment.md"
status = "pending"
updated_at = 2026-01-01T00:00:00Z

[[stages]]
sequence = 3
name = "requirement"
path = "03-requirement.md"
status = "pending"
updated_at = 2026-01-01T00:00:00Z

[[stages]]
sequence = 4
name = "design"
path = "04-design.md"
status = "pending" # Use omitted when the selected profile excludes Design.
updated_at = 2026-01-01T00:00:00Z

[[stages]]
sequence = 5
name = "check"
path = "05-check.md"
status = "pending"
updated_at = 2026-01-01T00:00:00Z

[[stages]]
sequence = 6
name = "implementation"
path = "06-implementation.md"
status = "pending"
updated_at = 2026-01-01T00:00:00Z

[[stages]]
sequence = 7
name = "validation"
path = "07-validation.md"
status = "pending"
updated_at = 2026-01-01T00:00:00Z

[[stages]]
sequence = 8
name = "delivery"
path = "08-delivery.md"
status = "pending"
updated_at = 2026-01-01T00:00:00Z
+++

# RUN-00000000000000000000000000000000 - <one-line title>

## Ticket input

<!-- Preserve verbatim for the life of the Run. -->

```text
<ticket text>
```

## Intent

<Restate the requested outcome and affected repository area.>

## Current scope

- Included: <agreed included work>
- Excluded: <explicit exclusions>
- Open questions: <questions or none>

## Execution instruction

- Actor: <developer or AI agent>
- Developer instruction affecting interaction: <for example, complete through Delivery without intermediate prompts, or none>

## Scope-change log

<!-- Append; never rewrite the original ticket or earlier interpretations. -->

| Time (UTC) | Previous interpretation | New interpretation | Actor and reason | Affected artifacts |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<previous>` | `<new>` | `<actor; reason>` | `<paths or IDs>` |

## Stage summary

| Stage | Status | Result | Updated |
|---|---|---|---|
| Intake | active | <current concise result> | 2026-01-01T00:00:00Z |
| Alignment | pending | | |
| Requirement | pending | | |
| Design | pending | | |
| Check | pending | | |
| Implementation | pending | | |
| Validation | pending | | |
| Delivery | pending | | |

## Change attribution

- Baseline branch and revision: <observed values>
- Pre-existing working changes: <paths and states, or none>
- Changes first observed during this Run: <paths or none>
- Changes adopted into scope: <paths or none>
- Uncertain authorship: <paths or none>

## Current handoff

- Current Stage: `01-intake.md`
- Durable context: <what the next session must know>
- Next action: <the first next action>
- Blockers: <none, or facts that require external input>

## Terminal outcome

<Active. When delivered, summarize the approved outcome in 08-delivery.md.
When normally abandoned, record the reason, actor, and last useful state here.>

## Run event history

<!-- Append only. Detailed work events remain in their owning Stage. -->

| Time (UTC) | Actor | Event | Result |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `run_opened` | `<initial state>` |
