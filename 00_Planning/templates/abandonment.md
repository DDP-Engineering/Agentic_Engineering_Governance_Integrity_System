<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Exceptional recovery artifact only. Create as
  .agentic/runs/ABANDON-RUN-<32hex>.md
when the normal Run cannot be safely updated. Normal abandonment stays in
run.md and the active Stage file.
-->

+++
schema = 1
artifact_type = "abandonment"
run_id = "RUN-00000000000000000000000000000000"
recorded_at = 2026-01-01T00:00:00Z
actor = "<actor>"
+++

# Exceptional abandonment - RUN-00000000000000000000000000000000

## Reason

<Mandatory reason the Run is ending without Delivery.>

## Why normal Run state could not be updated

<Unreadable path, invalid state, publication failure, or other exact cause.>

## Last known state

- Stage: <stage or unknown>
- Status: <last known status or unknown>
- Last useful result: <result or unknown>
- Next action before abandonment: <action or unknown>

## Affected paths and preserved diagnostics

- Unreadable or unsafe path: <repository-relative path>
- Diagnostic observation: <fact; do not overwrite the affected file>
- Attachment: <path and SHA-256, or none>

## Outcome

The Run is recorded as abandoned through this exceptional sibling record. No
work is represented as delivered or passed by this record.
