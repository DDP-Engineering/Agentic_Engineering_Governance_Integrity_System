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
stage = "delivery"
sequence = 8
status = "pending" # pending | active | completed | skipped | omitted
started_at = ""
updated_at = 2026-01-01T00:00:00Z
completed_at = ""
attachments = []
+++

# 08 - Delivery

## Stage instruction

Summarize the delivered work so the developer can judge it without
reconstructing the Run. Be concise but expose scope differences, actual
evidence, test changes, unresolved findings, and every escape hatch used.
Delivery ends at an approved recorded outcome; AEGIS performs no commit, push,
tag, merge, pull request, or outward-facing Git preflight.

## Requested and delivered outcome

- Ticket outcome requested: <concise request>
- Outcome delivered: <concise result>
- Scope differences: <none, or differences with actor and reason>

## Project artifact changes

| Type | Path or ID | Change |
|---|---|---|
| Requirement | `<REQ-ID>` | `<created, updated, deleted, or unchanged>` |
| Specification | `<SPEC path>` | `<created, updated, deleted, or unchanged>` |
| Component | `<COMP-ID>` | `<created, updated, deleted, or reviewed>` |
| Test | `<real test path>` | `<created, updated, or selected>` |

## Implementation changes

- <Path and concise behavior change>

## Evidence summary

| Claim | Evidence label and owning Stage | Actual result |
|---|---|---|
| Red before implementation | `<05-check.md RED1>` | `<result or approved non-applicability>` |
| Green after implementation | `<06-implementation.md GREEN1>` | `<result>` |
| Impacted regression validation | `<07-validation.md VAL1>` | `<result>` |
| Manual verification | `<07-validation.md MAN1 or none>` | `<result>` |

## Test integrity

- Test files changed between red and green: <paths or none>
- Developer judgement: <accepted, unresolved, or not applicable>
- Findings: <labels and Stage paths or none>

## Findings and residual risk

| Finding | Owning Stage | Disposition | Delivery consequence |
|---|---|---|---|
| `<label>` | `<stage path>` | `<open, resolved, accepted, waived, not_applicable>` | `<consequence>` |

## Skips, waivers, and omitted stages

| Stage | Type and target | Actor | Mandatory reason | Recorded outcome |
|---|---|---|---|---|
| `<stage>` | `<skip, waiver, or profile omission>` | `<actor>` | `<reason>` | `<skipped, waived, or omitted; never passed>` |

## Component drift review

- Components reviewed: <IDs>
- Documentation current: <yes | no | uncertain>
- Remaining findings: <labels or none>

## Delivery decision

| Time (UTC) | Decision | Actor | Scope | Reason or conditions |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<approved | rejected>` | `<actor>` | `<this delivery>` | `<reason or conditions>` |

## Terminal result

- Run outcome: <delivered, or active after rejection>
- Developer-owned next action: <commit, further work, or other action outside AEGIS>
- Atomic terminal publication: <Delivery completed and `run.md` delivered, or not completed after rejection>

## Event history

| Time (UTC) | Actor | Event | Result or correction |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `<event>` | `<result>` |
