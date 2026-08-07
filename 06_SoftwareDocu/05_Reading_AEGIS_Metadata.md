<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Reading AEGIS Metadata

Every stage you close leaves something behind on disk. This note is a map of
where to actually look when you want to answer a question like "what did we
actually approve here?", "what does the audit trail say happened?", or "where
is the evidence for this check?" — without having to guess file names or dig
through the CLI source.

## Finding the run you're looking at

AEGIS tracks which run is "current" for your worktree in one small pointer
file:

```text
.agentic/.workspace/state/current_run
```

It holds exactly one line: the active run's ID. This file is worktree-local
and Git-ignored — it is not part of the durable record, just a convenience so
you don't have to pass `--run <run-id>` on every command. Pin a different
run explicitly at any time with the global `--run` flag without touching
this pointer.

Everything that actually matters about a run lives under:

```text
.agentic/runs/<run-id>/
```

## What you're looking at while a stage is open: the stage directory

```text
.agentic/runs/<run-id>/stages/<stage>/
```

This is where the *transient* forms for whichever stage is currently active
live — the file(s) `stage prepare` generated and you're editing before
`apply`/`close`. Most stages write one file named after themselves
(`intake.toml`, `alignment.toml`, `implementation.toml`, `validation.toml`,
`delivery.toml`, and the same pattern for every adoption stage). The two
stages that can hold a *collection* of items — `requirement` and `check` —
instead write a `stage.toml` control form plus one numbered item file each
(`requirement-001.toml`, `check-001.toml`, and so on). The design stage
writes its control form here (`design.toml`) but keeps the actual
authoritative document one level up, directly under the run:

```text
.agentic/runs/<run-id>/design.md
```

Two more transient file types can appear inside a stage directory when
you're recording evidence: `evidence.toml` (external check red/green
results) and `manual-evidence.toml` (manual evidence add/supersede forms).
Both are described further below.

Whether anything survives here after a stage closes depends entirely on the
configured `stage_form_retention` policy. The shipped policy is
`stage_form_retention = "latest"`: `discard` deletes the form, `latest` leaves
the final version in place until the next `prepare` overwrites it, and
`versioned` keeps every closed revision under a
`revisions/` subfolder, each with its own `digest.json`. None of this
affects the durable record described below — retention only governs the
convenience copy.

## The durable record: `graph.json`

```text
.agentic/runs/<run-id>/graph.json
```

This is the one authoritative file for the run's entire state. Every
`apply`/`close` you perform ultimately updates it. If you want to know "what
does AEGIS currently believe is true about this run," this is the file, not
any transient form. Its top-level shape:

| Field | What it holds |
| --- | --- |
| `run_id`, `stage` | The run's identity and current stage. |
| `intent` | The intake record: statement, scope hints, status. |
| `access_mode` | `standard` or `repo-wide`. |
| `alignment` | The closed alignment record, or empty until that stage closes. |
| `design` | The closed design record (citing the authoritative `design.md`). |
| `spec_items` | Every closed requirement. |
| `checks` | Every closed check. |
| `evidence` | Every evidence record — see below. |
| `change_units` | Recorded implementation change units. |
| `decisions` | Recorded routing/control decisions. |
| `stage_records` | Per-stage bookkeeping: revision numbers, approval history. |
| `profile` | Present only for a quick run (`"quick"`); absent entirely for a full run. |
| `waivers` | Present only when at least one waiver has been recorded. |

You will rarely read this file by hand for everyday work — `run status`,
`stage show`, and `verify status` all summarize it — but it's the ground
truth behind every one of those summaries.

## The audit trail: `journal.jsonl`

```text
.agentic/runs/<run-id>/journal.jsonl
```

This is an append-only log: one JSON object per line, each with exactly
three fields — `time` (UTC), `event` (a stable name), and `data`
(event-specific detail). If `graph.json` tells you *what's currently true*,
the journal tells you *what happened and when*, including things the current
state doesn't retain on its own — every approval, every routing decision,
every recorded reason.

Events worth knowing when you're reading this file: `stage.prepared`,
`stage.applied`, and `stage.approved` mark the normal lifecycle; `run.
stages_bypassed` fires once, at intake close, for a quick run, and names
every stage it bypassed and why; `stage.routed` records an explicit route
back to an earlier stage; `waiver.added` records who waived what and their
stated reason; `evidence.recorded` / `evidence.add` / `evidence.supersede`
track evidence changes; `check.output` and `gate.output` carry a bounded tail
of a command's actual stdout/stderr; `verification.completed` marks a
finished `verify run`; `run.completed` marks delivery close.

## Evidence: two layers

The durable record of every piece of evidence — whatever produced it — lives
as an entry in `graph.json`'s `evidence` list: an ID (`E-NNNN`), its kind
(test-run, diff, scan, gate, decision, or note), its result (pass/fail/info),
a summary, and whether it's still active or has been superseded.

Where that evidence came from differs by mode:

- **External check evidence** is recorded through
  `stages/<stage>/evidence.toml` — one result row per check, with the exact
  command, result, exit status, and output log — before being folded into
  `graph.json`. The transient form is then retained, versioned, or deleted
  according to `stage_form_retention`; the shipped `latest` policy leaves the
  final form in place.
- **Managed check evidence** (`check run`) has no intermediate form at all:
  AEGIS runs the command itself, writes the full output to
  `.agentic/runs/<run-id>/evidence/logs/<check-id>-<stage>.log`, and records
  the result directly.
- **Manual evidence** (used by quick runs, and any time evidence needs to be
  attached without a formal check) goes through
  `stages/<stage>/manual-evidence.toml`.
- **Gate evidence** (from `verify run`) has no separate log file — its
  output tail lives only in the journal's `gate.output` event, while the
  pass/fail record itself lands directly in `graph.json`.

## Verification and delivery output

```text
.agentic/runs/<run-id>/validation-summary.json
```

Written by `verify run`. Contains the full deterministic verification
result: which regression selection ran, every gate's outcome in execution
order, invariant results, traceability and coverage audits, the working-tree
review, and — for a quick run — the explicit profile and bypassed-stage
list. This is what the human diff review is supposed to happen *after*
reading, not before.

```text
.agentic/runs/<run-id>/report.md
```

Written by `delivery report`. A single readable Markdown document
summarizing the whole run: intent and alignment, the stage-by-stage
lifecycle, requirements, the design, checks and their evidence, invariant
and traceability results, a link back to the validation summary, any
waivers, adoption baseline notes where relevant, and the handoff decision.
If you only read one file to understand "what did this run actually do,"
this is the one built for exactly that.

## What isn't run-specific

Two records exist independently of any single run, because they describe the
repository itself rather than one piece of work done to it:

```text
.agentic/components.toml
.agentic/requirements/<category>/REQ-<CODE>-<uuid>.toml
```

`components.toml` is the current component map — the durable answer to "what
are the meaningful units of this repository and what's their adoption
status," edited only through adoption/requirement-stage forms, never by hand
mid-run. Requirements live one folder per category (`functional`, `ux`,
`non_functional`, `security`, `data_privacy`, `platform`, `release`,
`testing`) under `.agentic/requirements/`, each an independently verifiable
contract with its own UUID-backed ID — these are what every run's
requirement stage cites and, on successful validation, activates.
