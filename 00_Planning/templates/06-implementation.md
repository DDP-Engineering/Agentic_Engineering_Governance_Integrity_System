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
stage = "implementation"
sequence = 6
status = "pending" # pending | active | completed | skipped | omitted
started_at = ""
updated_at = 2026-01-01T00:00:00Z
completed_at = ""
attachments = []
+++

# 06 - Implementation

## Stage instruction

Implement the agreed behavior to make the recorded red tests green. Record what
changed and attribute newly observed files carefully. Re-fingerprint the tests
and report every difference from Check; do not prevent or hide legitimate test
corrections.

## Inputs

- Requirements: <IDs>
- Design: <summary or omitted>
- Recorded red evidence: <labels>
- Test fingerprints at red: <paths and digests>

## Implementation changes

| Path | Change | Requirements | Component | Attribution |
|---|---|---|---|---|
| `<path>` | `<concise change>` | `<REQ-IDs>` | `<COMP-ID>` | `<this Run | pre-existing | uncertain>` |

## Test integrity comparison

| Test path | Red fingerprint | Current fingerprint | Changed? | Explanation or finding |
|---|---|---|---|---|
| `<test path>` | `<sha256>` | `<sha256>` | `<yes | no>` | `<reason or finding label>` |

## Implementation evidence

| Label | Time (UTC) | Command/selector and working directory | Exit | Observed result | Attachment |
|---|---|---|---:|---|---|
| `GREEN1` | 2026-01-01T00:00:00Z | `<command; cwd>` | `<code>` | `<concise result>` | `<path or none>` |

## Component documentation review

| Component | Behavior/interface/file-set changed? | Documentation action | Result |
|---|---|---|---|
| `<COMP-ID>` | `<yes | no>` | `<updated | reviewed | finding>` | `<result>` |

## Findings

| Label | Severity | Observation and consequence | Disposition |
|---|---|---|---|
| `F1` | `<severity>` | `<including any changed test>` | `<disposition>` |

## Decisions

| Time (UTC) | Decision | Actor | Target | Reason or conditions |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<approved | rejected | exception_approved>` | `<actor>` | `<target>` | `<reason or conditions>` |

## Outputs and handoff

- Implementation result: <concise result>
- Changed tests requiring a recorded decision: <paths or none>
- Next action: <first Validation action>
- Resume context: <what another session needs>

## Event history

| Time (UTC) | Actor | Event | Result or correction |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `<event>` | `<result>` |
