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
stage = "check"
sequence = 5
status = "pending" # pending | active | completed | skipped | omitted
started_at = ""
updated_at = 2026-01-01T00:00:00Z
completed_at = ""
attachments = []
+++

# 05 - Check

## Stage instruction

Create or select the tests that confirm the Requirements, using the configured
project test roots. Record actual failing evidence before implementation and
fingerprint the exact bytes of every relevant test file. If red-before-green is
genuinely inapplicable, record an exception decision, its actor, and its reason.

## Inputs

- Requirements and linked tests: <IDs and paths/selectors>
- Design: <summary or omitted>
- Configured test roots: <paths>

## Test work

| Test path and selector | Action | Requirements | Covered files | Risk purposes |
|---|---|---|---|---|
| `<path>::<selector>` | `<created | updated | selected>` | `<REQ-IDs>` | `<paths>` | `<purposes>` |

## Recorded red evidence

| Label | Time (UTC) | Command/selector and working directory | Exit | Observed failure | Attachment |
|---|---|---|---:|---|---|
| `RED1` | 2026-01-01T00:00:00Z | `<command; cwd>` | `<code>` | `<concise actual failure>` | `<path or none>` |

### Test fingerprints at red

| Evidence | Test path | SHA-256 of exact bytes |
|---|---|---|
| `RED1` | `<test path>` | `<64 lowercase hex>` |

## Red-before-green decision

- Applicable: <yes | no>
- If no, decision: `exception_approved`
- Actor: <developer or instructed AI agent>
- Mandatory reason when excepted: <reason>
- Alternative confirmation when excepted: <method>

## Findings

| Label | Severity | Observation and consequence | Disposition |
|---|---|---|---|
| `F1` | `<severity>` | `<finding>` | `<disposition>` |

## Decisions

| Time (UTC) | Decision | Actor | Target | Reason or conditions |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<approved | rejected | exception_approved>` | `<actor>` | `<target>` | `<reason or conditions>` |

## Outputs and handoff

- Check result: <concise result>
- Tests protected by recorded fingerprints: <paths>
- Next action: <first Implementation action>
- Resume context: <what another session needs>

## Event history

| Time (UTC) | Actor | Event | Result or correction |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `<event>` | `<result>` |
