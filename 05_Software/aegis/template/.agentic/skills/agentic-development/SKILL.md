---
name: agentic-development
description: File-first AEGIS workflow for full feature, fix, and change runs across intake, alignment, requirement, design, check, implementation, validation, and delivery, plus proportional four-stage quick runs for small fixes and changes.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Development

For the purpose of the workflow and its vocabulary, read
`.agentic/documents/WHY_AEGIS.md` and `.agentic/documents/GLOSSARY.md` before
starting an unfamiliar run. Use `.agentic/documents/INVARIANTS.md` when
verification reports an `INV-*` result.

Use AEGIS as an eight-stage, file-first full lifecycle:

`intake → alignment → requirement → design → check → implementation → validation → delivery`

The human approves every transition. Host plan mode may support discussion but
does not replace the imported design or `stage close` approval journal.

## Starting a New Run

The run-start command validates the workflow configuration before it acts. Use
`<workflow> config validate --json` after a configuration repair and
`<workflow> config show --json` only for explicit policy diagnosis; neither is
a fresh-session bootstrap step.

Start or resume:

   ```text
   <workflow> run start <feature|fix|change>
   <workflow> run start <fix|change> --quick
   <workflow> run resume
   ```

Open the returned artifact. Do not encode statements, paths, decisions, or
evidence in CLI flags.

## Fresh Stage Sessions

When resuming work without prior chat history, read `AGENTS.md`, run
`<workflow> run context --json`, then read only its `required_reads`: named
skill, reference, current form, and retained previous form. If
`unavailable_current_artifact` is present, run only its recovery command; never
prepare an already applied stage.
`run context` is bounded and read-only; use `run status` only for detailed diagnosis. Never read `graph.json` or
`journal.jsonl` for ordinary stage recovery.

When the human describes a genuinely small fix, offer the route explicitly:
`small scope - suggest: aegis run start fix --quick`. A quick run is valid only
for `fix` and `change`, and its real lifecycle is intake, implementation,
validation, and delivery, with an explicit human close at every transition.

At intake close AEGIS journals alignment, requirement, design, and check as
`bypassed` by run type. Treat that as its own visible state, never as passed or
waived. The absent-stage invariants and audits report `not-applicable`; intake,
changed-path and evidence capture, enabled gates, secrets and working-tree
review, scope analysis, delivery reporting, and the four human closes remain
real. If scope grows, restart a full run and carry the recorded context forward.

For a new quick implementation, run `<workflow> check create`, complete the
run-local definition, and run `<workflow> check register` before changing
source. Record a real red result, make the bounded repair, then record green
through the captured external or managed path. Link every active green
registered-check evidence ID in `linked_check_evidence` before `stage apply`.
Manual, invented, superseded, or other-stage evidence does not satisfy this
quick-check contract.

## Stage Lifecycle

For every stage:

```text
<workflow> stage prepare
# edit the generated TOML/Markdown
<workflow> stage apply
<workflow> stage show
# request explicit human approval
<workflow> stage close
```

Use `stage add` for another atomic requirement or check in a full run. `stage apply` imports
the complete collection only after every file validates. Access changes and
human-approved earlier routing belong in the generated control section.

Load only the current reference:

| Stage | Reference |
| --- | --- |
| intake | `reference/intake.md` |
| alignment | `reference/alignment.md` |
| requirement | `reference/requirement.md` |
| design | `reference/design.md` |
| check | `reference/check.md` |
| implementation | `reference/implementation.md` |
| validation | `reference/validation.md` |
| delivery | `$agentic-delivery` |

## Non-Negotiable Rules

- Requirements define observable contracts; design owns internal structures,
  boundaries, algorithms, compatibility choices, and implementation sequence.
- Every full run — feature, fix, or change alike — needs a reproducing red
  check before implementation. New quick runs require the same red-before-green
  evidence for their registered run-local checks; only historical quick graphs
  without the persisted policy are `legacy-not-applicable`.
- Record red and green check evidence through the configured external or managed
  path. Never invent IDs; AEGIS generates them.
- Do not edit check artifacts during implementation. Route back through a stage
  control form when the contract or check is wrong.
- Run deterministic verification before interpretive diff review.
- `stage close` at delivery completes AEGIS state only. It does not push,
  publish, merge, or create a pull request.
- For an eligible process blocker, offer the human the exact ID reported by
  `<workflow> waive list`. Only after explicit approval, record one run-local
  waiver with `<workflow> waive add <blocker-id> --reason "<reason>"`.
- Never treat a waiver as a pass. Preserve the failure as `WAIVED` with its
  reason and timestamp. Schema, graph, persistence-lock, and stale-update
  integrity failures are not waiver targets.
- Never treat a quick-run bypass as a waiver or a pass. Preserve `bypassed` in
  status, validation, and delivery reporting.

## Stop Format

```text
Stage: <stage>
Artifact: <path>
Imported revision: <number>
Evidence: <ids and results>
Blockers: <none or exact blockers>
Needs human: approve close, revise artifact, route earlier, add a recorded waiver for <blocker-id> where offered, or abandon the run with `aegis run abandon --reason "<text>"`
Next command: <exact command>
```
