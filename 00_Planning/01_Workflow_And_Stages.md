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

Use AEGIS for software development that changes the product or tests;
documentation accompanying that implementation stays with the change.
Documentation-only updates in this repository are reviewed directly, outside
AEGIS, under the maintainer's scope instruction. Do not use it for repository-only work,
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
| `build` | `steps/4_build.md` | Write and observe the expected failing test before implementation for automated requirements; carry out declared manual/inspection methods after the change; keep traceability links current. |
| `validate` | `steps/5_validate.md` | Reconcile the candidate, update knowledge, run focused and full proof, strict checks, and review evidence. |
| `deliver` | `steps/6_deliver.md` | Present the unchanged validated candidate, append the delivery report, and act only within granted Git/PR authority. |

A fix or change may take the quick path only when all frame criteria hold:

```text
frame -> build -> validate -> deliver
```

- No new externally observable behavior, interface, data format or dependency.
- An existing requirement already covers the behavior being changed.
- No security- or data-handling behavior is touched; those take the full path.

`frame` records `path: quick` and the eligibility reason. A small diff alone
does not qualify. The quick path does not remove validation, delivery proof,
or approval limits.

For automated requirements, build records the actual failing selector/command,
non-zero exit and expected missing-behavior reason before implementation.
An existing `Manual:` or `Inspection:` verification instead needs a recorded
observation after the change. For governed software work, anchor the starting
tree before implementation, then review evolution after the edits.

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
`implementation_quality` verdicts for the same candidate, using `approved` or
`changes_required`. An edit invalidates both verdicts. The policy permits one
initial review plus up to `max_fix_cycles` fix-and-re-review rounds, then
requires human direction.

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

## Executing through a host integration

The host's AEGIS agent or skill reads root guidance, the installed contract,
the named task's brief/journal and its current stage. A session-local task
pointer is only a convenience; restarting a host or changing branches requires
rechecking durable state. Codex bridge calls are stateless, so callers supply
the task identifier on each task-scoped operation.

Host `check` operations run static checks only. An advisory exit of zero is
not evidence that tests passed. Host `run` starts either a configured test
command or final `check --task ID --strict --run --json`, returning a job ID.
The coordinator polls `job`, reads the actual output and exit code, checks
whether the candidate changed during execution, and records the result.
Cancellation and interrupted-worker recovery retain enough state to inspect
uncertain processes before another run is allowed.

Claude's `SessionStart` and AEGIS-run `PreToolUse` hooks supply bounded context
and reminders. They do not write journal state, approve tools, run tests or
advance the task. Host review agents return evidence to the coordinator;
their verdicts do not substitute for final configured verification.

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
limited to child journals present in the current checkout. A reviewer session
is not automatically a child task: review of a candidate and independently
scoped implementation work have different records and responsibilities.
