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
stage = "intake"
sequence = 1
status = "active" # pending | active | completed | skipped | omitted
started_at = 2026-01-01T00:00:00Z
updated_at = 2026-01-01T00:00:00Z
completed_at = ""
attachments = []
+++

# 01 - Intake

## Stage instruction

Start from the ticket text. Read `.agentic/config.toml`, optional
`.agentic/rules.md`, the relevant Component documents, and the Requirements and
real tests linked by those Components. Inspect only enough repository state to
restate the ask, identify the affected area, and expose uncertainty. Do not
require the developer to pre-digest the ticket.

## Inputs

- Ticket source: `run.md`
- Rules read: <path or none>
- Repository revision and branch observed: <values>
- Pre-existing working changes: <paths and states, or none>

## Configured project paths

- Requirements: <configured path>
- Components: <configured path>
- Tests: <configured path or paths>
- Adoptions: <configured path>
- Runs: <configured path>

## Relevant project knowledge

| Component | Why relevant | Requirements read | Tests read | Drift or gap |
|---|---|---|---|---|
| `<COMP-ID>` | `<reason>` | `<REQ-IDs>` | `<paths/selectors>` | `<none or finding>` |

## Restated ask

<Restate the requested outcome in plain, testable language.>

## Initially affected repository area

- Components: <IDs or unknown>
- Implementation paths: <paths or unknown>
- Requirements: <IDs or to be created>
- Tests: <paths/selectors or to be created>

## Facts and uncertainties

- <Relevant fact or uncertainty>

## Evidence

| Label | Time (UTC) | Procedure or command | Observed result | Attachment |
|---|---|---|---|---|
| `E1` | 2026-01-01T00:00:00Z | `<inspection>` | `<result>` | `<path or none>` |

## Findings

| Label | Severity | Observation and consequence | Disposition |
|---|---|---|---|
| `F1` | `<info | warning | high>` | `<finding>` | `<open | resolved | accepted | waived | not_applicable>` |

## Decisions

| Time (UTC) | Decision | Actor | Target | Reason or conditions |
|---|---|---|---|---|
| 2026-01-01T00:00:00Z | `<approved | rejected | exception_approved>` | `<actor>` | `<target>` | `<reason or conditions>` |

## Outputs and handoff

- Intake result: <concise result>
- Information carried to Alignment: <scope and questions>
- Next action: <first Alignment action>
- Resume context: <everything a new session needs that is not in linked files>

## Event history

<!-- Append corrections and events; do not erase earlier facts. -->

| Time (UTC) | Actor | Event | Result or correction |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `stage_started` | `<result>` |
