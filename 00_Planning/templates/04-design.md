<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

+++
schema = 1
artifact_type = "stage"
run_id = "RUN-00000000000000000000000000000000"
stage = "design"
sequence = 4
status = "pending" # pending | active | completed | skipped | omitted
started_at = ""
updated_at = 2026-01-01T00:00:00Z
completed_at = ""
attachments = []
+++

# 04 - Design

## Stage instruction

Describe the smallest solution that satisfies the agreed Requirements. Cite the
Requirements it serves, the Components and files it affects, important
alternatives, risks, and how the design will be checked. For a short profile,
record this Stage as `omitted`, not `skipped`.

## Inputs

- Requirements: <IDs>
- Specifications: <paths or none>
- Components: <IDs>

## Proposed solution

<Concise solution design.>

## Requirement coverage

| Requirement | Design decision | Affected Components and files |
|---|---|---|
| `<REQ-ID>` | `<decision>` | `<COMP-IDs and paths>` |

## Interfaces, data, and failure behavior

- Interfaces changed: <details or none>
- Data/state changed: <details or none>
- Failure behavior: <details or none>

## Alternatives and risks

- Alternative considered: <alternative and why not selected>
- Implementation risk: <risk and mitigation>
- Validation risk: <risk and response>

## Evidence

| Label | Time (UTC) | Review or inspection | Observed result | Attachment |
|---|---|---|---|---|
| `E1` | 2026-01-01T00:00:00Z | `<review>` | `<result>` | `<path or none>` |

## Findings

| Label | Severity | Observation and consequence | Disposition |
|---|---|---|---|
| `F1` | `<severity>` | `<finding>` | `<disposition>` |

## Decisions

| Time (UTC) | Decision | Actor | Target | Reason or conditions |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<approved | rejected | exception_approved>` | `<actor>` | `<target>` | `<reason or conditions>` |

## Outputs and handoff

- Design result: <concise result or profile omission>
- Component drift review expected: <components and triggers>
- Next action: <first Check action>
- Resume context: <what another session needs>

## Event history

| Time (UTC) | Actor | Event | Result or correction |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `<event>` | `<result>` |
