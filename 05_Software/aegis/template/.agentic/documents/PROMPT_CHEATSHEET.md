<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# AEGIS 3.0 Prompt Cheat Sheet

This is a human operator flyer, not an authoritative workflow source and not an agentic delivery contract.
It is not an evidence source. Generated forms, imported graph state, journals,
and durable records are authoritative.

If the workflow is unfamiliar, read [WHY_AEGIS.md](WHY_AEGIS.md) first. Use
[GLOSSARY.md](GLOSSARY.md) for terms and [INVARIANTS.md](INVARIANTS.md) for
the checks reported by verification.

Use short prompts that tell the agent to open the artifact returned by AEGIS.
Detailed feature content belongs in generated files, not CLI arguments.

## Start or Resume

```text
Run `aegis config show --json` to confirm schema 3 and workspace policy. Then
run `aegis run start feature`. Open the returned intake form, draft the
statement, scope hints, and access mode, then stop for my review.
```

```text
Run `aegis run resume`, open the active artifact, summarize imported state and
blockers, and continue only within the current stage.
```

```text
In this fresh session, read AGENTS.md, run `aegis run context --json`, and if
`unavailable_current_artifact` is present run only its recovery command. Never
prepare an already applied stage. Then read only the returned skill, reference,
current form, and retained prior form. Do not read graph.json or journal.jsonl.
```

## Alignment

```text
Prepare the alignment form. Capture your understanding, in/out scope,
assumptions, acceptance criteria, questions with recommended answers, risk, and
planned paths. Do not close the stage.
```

## Requirements

```text
Generate one requirement form per atomic observable contract. Include success,
rejection, boundary, error, state-transition, and non-functional contracts that
apply. Put concrete observable examples in companion specs; keep internal design
out. Apply the collection and stop for approval.
```

## Design

```text
Discuss alternatives with me, then update the authoritative design.md and
design.toml. Cite exact requirement IDs; cover architecture, constraints,
trade-offs, selected design, interfaces/data, compatibility, implementation
sequence, validation, risks, and open decisions. Apply but do not close.
```

## Check

```text
Generate deterministic checks that cite requirements and assert observable
contracts. Identify production/mock/sandbox, flag, role, platform, and
persistence variants; add parity checks where promised. Reproduce a fix as red
evidence before asking to close.
```

## Implementation

```text
Implement only the approved design. Do not rewrite requirements or checks.
Record summary, changed paths, documentation effects, and linked evidence in the
implementation form. Record green evidence after prior red evidence.
```

## Validation

```text
Run `aegis verify run` before reviewing the diff. Resolve deterministic
failures, then review scope, documentation, style, assertions, stale state,
rollback, errors, boundaries, concurrency, idempotency, and secrets. Complete
the validation form and stop for approval.
```

## Delivery

```text
Prepare the delivery form and report. Confirm preflight references and final
handoff decision. Closing delivery must only complete AEGIS state—do not push,
publish, merge, or create a PR unless I ask separately.
```

## Routing and Evidence

```text
Put the requested earlier stage and rationale in the current form's control
section. Apply it and stop for approval.
```

```text
Run `aegis evidence prepare supersede`, complete the generated relationship and
rationale, then apply it. Do not edit graph.json directly.
```

## Configuration

```text
Show the schema-3 interface policy and all five gate groups. Report disabled
groups as disabled, not passed. Do not invent a security command.
```

## Adopt An Existing Project

Use this first prompt after the AEGIS payload has been deployed into an existing
repository. It starts the adoption route, which describes what already exists;
it changes no application behavior.

```text
Run `aegis config validate --json` and `aegis config show --json`, then
`aegis run start adoption`. Open the returned adoption-intake form and complete
the statement, the single adoption slice you propose to adopt first, the access
mode you need and why, and any unresolved questions. Report which policies the
generated workflow.toml leaves inactive. Stop for my approval before
`stage close`.
```

The route continues `adoption-intake → adoption-alignment → repo-discovery →
component-map → component-adoption → baseline-review → adoption-delivery`, one
human approval per stage. Load only the reference for the current stage from the
`agentic-adoption` skill.

## Adoption Discovery

Provider inspection or synchronization is an external deployment-tool action,
not an AEGIS command. Confirm that operation separately before asking the agent
to consume discovery artifacts.

```text
During repo-discovery, report RepoWise validation status and provenance. Use
only current structural proposals, preserve every human-entered field, warn for
advisory unavailability, and block only when the integration is explicitly
required. If provider artifacts are stale, stop and ask the operator to update
them outside AEGIS.
```
