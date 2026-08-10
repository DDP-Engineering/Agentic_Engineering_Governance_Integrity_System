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
stage = "validation"
sequence = 7
status = "pending" # pending | active | completed | skipped | omitted
started_at = ""
updated_at = 2026-01-01T00:00:00Z
completed_at = ""
attachments = []
+++

# 07 - Validation

## Stage instruction

Use Requirement-to-impacted-file-to-test traceability to select the relevant
regression tests. Prefer the safely determined impacted set for speed. If the
set is unsafe or incomplete, run the full configured suite and state why.
Record actual outcomes, manual checks, findings, waivers, and test-integrity
results without converting them into blockers.

## Inputs

- Requirements: <IDs>
- Changed implementation files: <paths>
- Changed test files: <paths or none>
- Implementation evidence: <labels>

## Impacted-test selection

| Changed file | Requirement | Selected test path/selector | Selection reason |
|---|---|---|---|
| `<path>` | `<REQ-ID>` | `<test>` | `<traceability link>` |

- Selection completeness: <safe and complete | uncertain | incomplete>
- Full-suite fallback used: <yes | no>
- Fallback reason: <reason or not applicable>

## Automated validation evidence

| Label | Time (UTC) | Command/selector and working directory | Exit | Observed result | Attachment |
|---|---|---|---:|---|---|
| `VAL1` | 2026-01-01T00:00:00Z | `<command; cwd>` | `<code>` | `<passed, failed, or launch error with details>` | `<path or none>` |

## Manual validation evidence

| Label | Time (UTC) | Actor | Procedure | Expected | Actual |
|---|---|---|---|---|---|
| `MAN1` | 2026-01-01T00:00:00Z | `<actor>` | `<steps>` | `<expected>` | `<actual>` |

## Test integrity conclusion

- Tests changed between red and green: <paths or none>
- Recorded decision: <accepted correction, unexplained change, or none>
- Related findings: <labels or none>

## Findings

| Label | Severity | Observation and consequence | Disposition |
|---|---|---|---|
| `F1` | `<severity>` | `<finding>` | `<disposition>` |

## Decisions

| Time (UTC) | Decision | Actor | Target | Reason or conditions |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<approved | rejected | exception_approved>` | `<actor>` | `<target>` | `<reason or conditions>` |

## Outputs and handoff

- Validation result: <concise honest result>
- Unresolved risk: <risk or none>
- Next action: <first Delivery action>
- Resume context: <what another session needs>

## Event history

| Time (UTC) | Actor | Event | Result or correction |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `<event>` | `<result>` |
