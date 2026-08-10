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
stage = "requirement"
sequence = 3
status = "pending" # pending | active | completed | skipped | omitted
started_at = ""
updated_at = 2026-01-01T00:00:00Z
completed_at = ""
attachments = []
+++

# 03 - Requirement

## Stage instruction

Express one behavior per Requirement, with its confirmation stated separately.
Use EARS phrasing when it improves clarity, not as a mandatory form. Link each
Requirement directly to impacted implementation files and real project tests,
or record a concrete manual-test method. Create a Specification only when the
Requirement alone is not buildable.

## Inputs from Alignment

- Agreed scope: <scope>
- Profile: <full | short>
- Relevant existing Requirements: <IDs or none>

## Requirement artifact changes

| Requirement | Action | One behavior | Confirmation | Specification |
|---|---|---|---|---|
| `<REQ-ID>` | `<created | updated | deleted | unchanged>` | `<summary>` | `<automated or manual>` | `<path or none>` |

## Traceability

| Requirement | Impacted files | Real tests or manual method | Risk purposes |
|---|---|---|---|
| `<REQ-ID>` | `<paths>` | `<paths/selectors or method>` | `<happy_path plus risk-based depth>` |

## Risk-based test depth decision

- Behavior risk: <impact, likelihood, complexity, and failure cost>
- Beyond happy path: <boundary, edge, negative, failure path, or none>
- Rationale: <why this depth is proportionate>

## Gaps and uncertainties

- <Missing coverage, uncertain impacted file, or none>

## Evidence

| Label | Time (UTC) | Validation performed | Observed result | Attachment |
|---|---|---|---|---|
| `E1` | 2026-01-01T00:00:00Z | `<schema/link validation>` | `<result>` | `<path or none>` |

## Findings

| Label | Severity | Observation and consequence | Disposition |
|---|---|---|---|
| `F1` | `<severity>` | `<finding>` | `<disposition>` |

## Decisions

| Time (UTC) | Decision | Actor | Target | Reason or conditions |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<approved | rejected | exception_approved>` | `<actor>` | `<target>` | `<reason or conditions>` |

## Outputs and handoff

- Project artifacts published: <paths>
- Requirement result: <concise result>
- Next action: <first Design or Check action>
- Resume context: <what another session needs>

## Event history

| Time (UTC) | Actor | Event | Result or correction |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `<event>` | `<result>` |
