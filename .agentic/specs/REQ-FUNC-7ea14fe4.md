<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-7ea14fe4 - Preserve durable rulings and handoffs

## Behavior

New task journals provide an append-only `## Rulings` decision history and one
replaceable `## Handoff` resume snapshot. Legacy journals may omit both.
Rulings are never edited or deleted; a later valid ruling supersedes an earlier
one. Active rulings are valid records not superseded by a later valid record.
Rulings record decisions but cannot grant authority or override newer user
instructions, repository rules, or external boundaries.

Handoff is refreshed at every stage transition, pause, blocker, or session end.
It records only the current stage, readiness, one next action, minimum files to
read, and blockers. The append-only log retains evidence and history; the
handoff is the current worker snapshot and the stage report remains the
user-facing result.

## Data / interface

```text
## Rulings

- RULING-001 | date=YYYY-MM-DD | decision=... | reason=... | source=user | supersedes=none

## Handoff

current:
status:
next:
must_read:
blockers:
```

Ruling IDs are unique `RULING-` plus three decimal digits. Keys occur exactly
in the shown order; `source` is `user`, `repository`, `requirement`, or
`technical`; values cannot contain `|`; `supersedes` is `none` or a prior ID.
Malformed records yield bounded diagnostics without hiding valid records.
Handoff has only the five known fields, `status` is `ready`, `waiting`, or
`blocked`, and `current` must match the journal header stage.

## Acceptance

- Valid rulings retain journal order and supersession does not mutate history.
- Duplicate, malformed, or unknown-supersession records are advisory findings.
- Blank scaffolds are accepted and stale handoffs are reported.
- A fresh worker can identify one next action and its minimum durable sources.
