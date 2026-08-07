<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AGENTS.md

This repository uses AEGIS 2.1, a human-approved, file-first engineering
workflow. Treat `.agentic/workflow.toml` as the only AEGIS policy source.

New to AEGIS? Read `.agentic/documents/WHY_AEGIS.md` first, then use
`.agentic/documents/GLOSSARY.md` and `.agentic/documents/INVARIANTS.md` as
references. When integrating another branch's AEGIS state, follow
`.agentic/documents/MERGE_AND_REBASE.md` before resolving or validating it.

## Policy Validation and Diagnosis

Every AEGIS command, including `run context`, validates the configured workflow
before it acts. If configuration is missing or invalid, correct it and use
`<workflow> config validate --json` to confirm the repair. Use
`<workflow> config show --json` only for explicit policy diagnosis; it is not a
fresh-session bootstrap input and must not be added to the bounded context pack.

Do not infer fallback policy when configuration is missing or invalid. AEGIS
policy supplements host, sandbox, approval, and operating-system controls. Use
`--run <run-id>` only when an operation must pin a run explicitly.

`<workflow>` means the project-local wrapper:

```text
.\.agentic\tools\run.ps1
bash .agentic/tools/run.sh
```

An installed `aegis` or `python -m aegis` is also valid.

## Resuming In A Fresh Session

A session that did not run the earlier stages can reconstruct the current stage
from repository state without reading the graph or journal. Use this bounded
bootstrap sequence:

```text
1. Read AGENTS.md.
2. Run `<workflow> run context --json`.
3. If `unavailable_current_artifact` is present, run only its recovery command.
   Run `<workflow> stage prepare` only when that command is named; never
   prepare an already applied stage.
4. Read only the skill, reference, current form, and retained previous form
   named in required_reads.
5. Perform only the reported current stage and stop at stage close for human approval.
```

`run context` is the normal first AEGIS command in a fresh session. Its
versioned response names only the selected stage's router/reference and bounded
form inputs; it omits evidence, requirements, reports, configuration, and other
run-history data. Use `run status` only for detailed diagnosis.

- If `unavailable_previous_stage_artifacts` is non-empty, use its named
  recovery command instead of guessing from internal state.
- Treat the current form's state and the current-stage reference as the
  authoritative work boundary. If the form is already prepared or applied, do
  not prepare a new revision merely to resume it.
- Before applying or closing, use the stage-specific command in the reference
  when evidence or verification remains outstanding.

Depending on the stage, the named inputs may include the preceding retained
form, requirements/specs, the approved design, imported checks, component
documentation, or the source files being changed.

Do not read `graph.json` or `journal.jsonl` to recover context. They are the
run's internal state and its append-only audit trail; they can be substantially
larger than the focused stage inputs. Read them only when diagnosing AEGIS
itself.

Retained-form review depends on `[interface] stage_form_retention` keeping forms
after import (`latest` or `versioned`). Under `discard`, use `stage show` and the
durable artifacts named by the stage reference because the imported form is
deleted.

## Standard Lifecycle

The full-run order is:

`intake → alignment → requirement → design → check → implementation → validation → delivery`

The `alignment` and `design` stages are distinct: alignment establishes the
problem contract; design establishes the approved solution.

Start with `<workflow> run start <feature|fix|change>` or resume with
`<workflow> run resume`. Open the returned artifact.

Every stage follows:

```text
<workflow> stage prepare
# edit generated TOML and referenced Markdown
<workflow> stage apply
<workflow> stage show
# review imported state and ask for explicit human approval
<workflow> stage close
```

Use `stage add` only for additional atomic requirements or checks. The CLI
generates all durable IDs. Statements, scope, access changes, routing decisions,
requirements, checks, design, and evidence belong in generated forms, not flags.

`stage close` is the authoritative approval boundary. Host plan mode may help
the design conversation but cannot approve AEGIS state.

## Proportional Quick Lifecycle

When the human describes a genuinely small fix or change, offer the
proportional route explicitly:
`small scope - suggest: aegis run start fix --quick`. Use `change --quick` for
a small non-fix behavior change. The quick modifier is invalid for feature and
adoption runs.

A quick run retains four real stages and an explicit human close at each one:

`intake -> implementation -> validation -> delivery`

Closing intake journals one `run.stages_bypassed` record that marks alignment,
requirement, design, and check as `bypassed` by the quick run type. Run status,
the validation summary, and `report.md` repeat that state; bypassed never means
passed or waived.

Because a quick run has no requirement, design, or ordinary check collection
stage, INV-1, INV-2, INV-8, and INV-10, plus the standalone traceability and
coverage audits, report `not-applicable`. New quick runs still evaluate INV-3:
each registered check needs a recorded red result before its green result.
Only historical quick graphs without the persisted policy report INV-3 as
`legacy-not-applicable`.

At quick implementation, run `<workflow> check create`, fill the generated
definition with the command and optional path/variants/concerns, then run
`<workflow> check register` before changing source. Requirement and
specification citations stay empty because this proportional path has no
collection stages. Record a real red result, make the bounded repair, then
record green through `<workflow> check prepare`/`<workflow> check record` or
`<workflow> check run <check-id>`. Put every active green check-evidence ID in
`linked_check_evidence` before applying the implementation form. Manual,
invented, missing, superseded, or other-stage evidence never satisfies this
quick-check contract.

Quick runs cannot route into a bypassed stage. If scope grows, preserve the
recorded context and restart as a full run with `aegis run start <fix|change>`.
The optional `[quick.changed_paths]` policy can emit this guidance after
implementation closes when the unique changed-path count exceeds `max_paths`.
Its modes are `disabled` and `advise`; absence means `disabled` with a retained
default threshold of 10, and an advisory never blocks or changes the run.

## Stage Contracts

- The alignment, requirement, design, and check contracts below apply only
  when those stages are present in the selected run profile.
- Intake captures intent, scope hints, and access mode.
- Alignment captures understanding, scope, assumptions, observable acceptance
  criteria, questions and recommendations, risks, and planned paths.
- Requirements define atomic externally observable contracts. Internal
  structures, algorithms, boundaries, and sequencing belong in design.
- Design is authoritative in `.agentic/runs/<run-id>/design.md`; it must cite
  unchanged requirement snapshots and record an explicit selected option.
- Checks cite requirement IDs and assert observable behavior. Every full run —
  feature, fix, or change alike — requires reproducing red evidence before
  implementation.
- Implementation follows the approved design and records changed paths,
  documentation effects, and linked evidence in its form.
- Validation runs `<workflow> verify run` before interpretive diff review.
  Successful validation closure activates green Planned requirements.
- Delivery records the final handoff decision. Closing it completes AEGIS state
  but never pushes, publishes, merges, or creates a pull request.

## Check and Evidence Policy

The prepared stage captures `interface.check_execution`.

- External mode: `<workflow> check prepare`, run commands externally, complete
  `evidence.toml`, then `<workflow> check record`.
- Managed mode: `<workflow> check run [<check-id>...]`.
- Manual evidence: `<workflow> evidence prepare <add|supersede>`, edit the
  generated form, then `<workflow> evidence apply`.

Never use the command path for the other mode. Never fabricate IDs.

## Verification

`<workflow> verify run` performs impact analysis, enabled deterministic gates,
invariants, traceability, coverage, and working-tree review, then writes the
validation summary.

Gate order is build, typecheck, lint, test, security. Each group is independently
`disabled` or `enforce`; disabled means disabled, never passed. Security executes
only explicitly configured deterministic tooling and is not an authoritative
security-assurance claim.

An exact active waiver neutralizes only its named blocker for the selected run
and current digest-pinned state. The underlying check still failed: summaries
and reports must show `WAIVED`, with the reason and timestamp, never `passed`.

Run linked checks first. Use full regression for shared, cross-cutting, or
untraced changes. Cover relevant variants, response shapes, stale-state cleanup,
rollback, errors, boundaries, concurrency, and idempotency.

When `[gates.test].impacted_command` is an explicit argv prefix, run
`<workflow> verify impact --run` after reviewing the impact report. AEGIS adds
the resolved linked-test selectors as separate argv values with no shell. It
uses focused mode only for complete, safe coverage; otherwise it prints the
fallback reason and executes every configured full test command. A focused or
fallback request that cannot launch any command is `nothing-ran`, not a pass.

## Recorded Waivers

When a process blocker should be overcome once, show the human the exact
blocker ID from `<workflow> waive list` and offer:

```text
<workflow> waive add <blocker-id> --reason "<human-approved reason>"
```

Adding a waiver is an explicit human approval act, like `stage close`. Do not
invoke it autonomously. Reasons are mandatory; IDs are exact and CLI-discovered;
there are no wildcard, bulk, or force forms. Waivers belong to one run, are
minted and journaled by AEGIS, and become stale when their digest-pinned blocker
state changes.

Structural integrity failures are never waiver targets: malformed or
closed-schema state, persistence-lock conflicts, and stale-update conflicts
must be corrected or retried. A waiver does not skip importing a stage or
create a shortened lifecycle; only the declared quick profile shortens one.

## Adoption

Adoption retains its ordered stages but uses the same
`prepare → apply → close` lifecycle:

`adoption-intake → adoption-alignment → repo-discovery → component-map → component-adoption → baseline-review → adoption-delivery`

Adoption does not change application behavior. Use the `agentic-adoption` skill
for stage-specific guidance.

## Repository State

- Durable requirement snapshots live under `.agentic/requirements/`.
- The worktree-local run pointer is
  `.agentic/.workspace/state/current_run`; never stage `.agentic/.workspace/`.
- Transient forms follow the retention captured at stage preparation.
  `design.md`, requirement snapshots/specifications, graph state, evidence,
  journals, validation summaries, and delivery reports remain durable.
- Route earlier or request access changes only through the current form control
  section with a rationale. Routing to requirement or design invalidates design
  approval.

## Changing Direction Mid-Run

Discovering that a contract is wrong is normal work, not a failure. Set
`control.route_to` to an earlier stage and `control.route_rationale` in the
current form, then `aegis stage apply` and `aegis stage close`. Routing takes
effect at close.

Closing with a route is not an approval of the stage you are leaving, so the
evidence that stage would have produced is not demanded. Blockers shaped
`<check-id> is missing prior red evidence` and
`<check-id> has no active green evidence` are deferred, and the deferred list is
written to the `stage.routed` journal event as `blockers_deferred`. Structural
and control validity are still enforced: the route must name an earlier stage in
this run's lifecycle, it needs a rationale, and every non-evidence blocker still
stands.

Routing to `requirement` or `design` invalidates design approval. Requirement
`status` and `created_on` are durable and survive a re-apply, so going back
costs no lifecycle history.

If the run itself should not continue at all, end it with
`aegis run abandon --reason "<text>"` rather than leaving it open.

## Component Documentation Contract

Add or update `.agentic/knowledge/components/*.md` when a component is new or
its responsibilities, boundaries, interfaces, data, dependencies, or workflow
integration materially change. Follow the component template and update the
component index. Component documents complement requirements, design, and
checks; they replace none of them.

## Stop Format

```text
Stage: <stage>
Artifact: <path or none>
Imported revision: <number or none>
Evidence: <ids/results or none>
Blockers: <none or exact blockers>
Needs human: approve close, revise, route earlier, add a recorded waiver for <blocker-id> where offered, or abandon the run with `aegis run abandon --reason "<text>"`
Next command: <exact command>
```
