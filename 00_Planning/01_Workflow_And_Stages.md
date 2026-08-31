<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 01 - Workflow and stages

The workflow contract is the installed `.agentic/AGENTS.md` plus one step
file per stage. A task journal records the current stage and evidence; the
CLI does not advance stages on anyone's behalf.

## Scope and operating rule

Use AEGIS for software work that changes the product, tests, or its
implementation-facing documentation. Do not use it for repository-only work,
version assignment, delivery/package construction, publication, or deployment.
Those operations may carry an AEGIS-governed implementation, but are not
themselves a workflow task.

The workflow is advisory. A step can be skipped only by recording the reason
truthfully; `check` reports evidence gaps and configuration issues, while
`check --strict` is the optional CI enforcement boundary.

## Ordinary lifecycle

| Stage | Step file | Implemented responsibility |
|---|---|---|
| `frame` | `steps/1_frame.md` | Agree scope, exclusions, authority limits, path, and open the journal. |
| `specify` | `steps/2_specify.md` | Create or update durable requirements and a spec when the requirement alone is not buildable. |
| `design` | `steps/3_design.md` | Record a short, requirement-linked design for non-trivial work. |
| `build` | `steps/4_build.md` | Establish the expected red result where practical, implement, and keep traceability links current. |
| `validate` | `steps/5_validate.md` | Reconcile the candidate, update knowledge, run focused and full proof, strict checks, and review evidence. |
| `deliver` | `steps/6_deliver.md` | Present the unchanged validated candidate, append the delivery report, and act only within granted Git/PR authority. |

A small fix or change may take the quick path:

```text
frame -> build -> validate -> deliver
```

`frame` records `path: quick` and why the omitted specification/design work
is proportionate. The quick path does not remove validation, delivery proof,
or approval limits.

If the candidate changes after validation, return to `validate`. Deliver is
not a place to make unvalidated implementation changes.

## Interaction boundaries

Checkpoint mode is the default. It asks at two meaningful boundaries:

1. End of `frame`: confirm scope, selected path, and requirements.
2. Before a delivery commit or pull request: present the validated candidate
   and proof for explicit authority.

An explicit autopilot request suppresses the first stop, not external
authority or the delivery boundary. Neither child tasks, stage reporting,
rulings, handoffs, nor review add a new ordinary approval checkpoint.

Record accepted deviations immediately and say them in the conversation:

```text
DEVIATION <stage>: <what> - <why accepted, or what it costs>
```

Examples include accepting a `check` warning, a failed/skipped verification,
unexpected anchor/evolution evidence, or a manual verification method standing
in for an automatable test.

## Explicit review is policy, not a stage

The optional `[review]` configuration controls explicit review evidence:

```toml
[review]
enabled = false
max_fix_cycles = 2
```

When enabled, review records independent `spec_compliance` and
`implementation_quality` verdicts for the same candidate. An edit invalidates
both verdicts. The policy permits one initial review plus up to
`max_fix_cycles` fix-and-re-review rounds, then requires human direction.

The current repository enables this policy with `max_fix_cycles = 2`.
Disabling it skips only the explicit verdict contract and bounded loop; it
never skips semantic review, knowledge updates, full validation, strict checks,
or the delivery checkpoint.

## Durable resume state

The task journal is the durable history. Its append-only `## Log` records
observations and decisions. New journals also support:

- **Rulings:** append-only durable decisions; a later ruling supersedes an
  earlier ruling by ID instead of rewriting history.
- **Handoff:** one replaceable, stage-bound resume snapshot with `current`,
  `status`, `next`, `must_read`, and `blockers`.
- **Stage report:** one replaceable current snapshot of result, changes,
  evidence, issues, next action, and optional review fields.

Resume safely:

1. Run `python .agentic/aegis.py status` when the task ID is unknown.
2. Run `python .agentic/aegis.py brief TASK-<id>`.
3. Read the current step file and the Handoff `must_read` paths.
4. Read the full journal wherever detail is omitted, stale, unresolved, or
   required by the current stage; then continue at the first unticked item.

`brief` never proves the recorded state is still true. `summary` is useful
after a stage report is written, but it is narrower still and never replaces
required journal, source, or evidence reads.

## Adoption and child tasks

Existing-repository adoption follows `steps/adopt.md`:

```text
survey -> components -> close -> done
```

It produces requirements and knowledge from observed code and tests, then
checks the resulting register. It is not an ordinary-stage shortcut.

Large work may use optional one-level child tasks. A child keeps its own
journal, branch/base, requirements, evidence, validation, and delivery
checkpoint. The child has the only `parent:` link; creating it never rewrites
the parent. The parent validates the integrated candidate, and visibility is
limited to child journals present in the current checkout.
