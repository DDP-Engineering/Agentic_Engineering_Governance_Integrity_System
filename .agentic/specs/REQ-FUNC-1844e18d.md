<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Compact recorded stage summaries

## Interface

`python .agentic/aegis.py summary TASK-<id>` prints one plain text block.
The short hexadecimal ID also works through the existing journal reader.
No files are written, commands executed, checks run, or approvals granted.
Existing `status`, its JSON schema, and the append-only delivery `report`
command retain their behavior.

## Journal record

An optional single `## Stage report` section contains plain one-line fields:

```text
stage: specify
result: completed
current: design
changed: requirements created; IDs are on the journal header
evidence: format check exit 0; tests not run at this stage
issues: none recorded
next: follow 3_design.md
needs_user: no
```

`stage` identifies what is being reported; `current` binds the snapshot to
the current journal header. Both use existing ordinary/adoption stage names.
`result` is `in_progress`, `completed`, `paused`, `blocked`, or `skipped`.
Other fields are explicit agent-authored observations, not independent proof.
Blank fields print `not recorded`. The section is a replaceable latest view;
decisions, evidence, and transitions remain append-only in `## Log`.
Blank scaffold fields are valid and never claim the frame is complete.

## Safety and output

Output order is Stage, Task, Current, Requirements, Changed, Evidence, Issues,
Next, Needs user, Details. Stage combines recorded stage and result. Current
always comes from the journal header; Requirements comes from that header.
Details points to the full journal and identifies the view as recorded state.
Missing records, missing stage/current bindings, or a current-stage mismatch
produce explicit missing/incomplete/stale notices, suppress the record's
claims and next-action/approval text, and direct the reader to the journal.
A matching stage does not establish freshness against source edits: the agent
must refresh the record after new work, outcomes, deviations, or decisions.
An unknown stage/result, unknown or duplicate field, duplicate section, or
malformed nonblank record line is an error with exit 1 and empty stdout.
Commented/fenced examples outside the live section cannot supply facts or
conflict with it; code-span literals and fence info do not start comments.

Each displayed value is at most 240 characters, including a visible
`[truncated; read journal]` suffix when shortened. Whitespace/control
characters cannot forge output lines. If anything is shortened, Needs user
directs review of the complete journal before proceeding, even when the
record says no; an omission is never a clean result. The ten-line view is
bounded in characters, not a guarantee about any model's tokenizer.

## Verification

Extend existing copied-payload CLI tests for complete, partial, missing,
stale, malformed and duplicate records, adoption and quick-path transitions,
single-stage pauses, bounded output, unknown task rejection, and read-only
operation without Git/configuration/subprocess dependencies.
Model obedience and actual 64K-context performance require separate runs
with the user's model; deterministic CLI tests do not establish either.
