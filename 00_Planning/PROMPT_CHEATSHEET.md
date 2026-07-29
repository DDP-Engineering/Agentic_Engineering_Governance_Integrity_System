<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# AEGIS 2.0 Planning Prompt Cheat Sheet

## Session

```text
Validate schema 3, show interface and all five gate groups, then run
`aegis run resume`. Open the returned artifact and do only the current stage.
```

## Stage Prompts

```text
Intake: prepare the form and capture statement, scope hints, and access mode.
Stop before apply.
```

```text
Alignment: capture understanding, in/out scope, assumptions, acceptance,
questions with recommended answers, risk, planned paths, and decision. Apply
but do not close.
```

```text
Requirement: generate one form per atomic observable contract, including errors,
boundaries, state transitions, and applicable non-functional dimensions. Use
companion specs for observable examples; reserve internals for design.
```

```text
Design: discuss alternatives with me, then update authoritative design.md and
metadata. Cite requirement IDs and cover architecture, constraints, trade-offs,
selected option, components, interfaces/data, compatibility, sequence,
validation, risks, and open decisions. Apply and stop for approval.
```

```text
Check: create deterministic requirement-linked checks. Reproduce a fix red
before implementation. Cover applicable runtime/flag/role/platform/adapter
variants and parity, cleanup, rollback, errors, boundaries, concurrency, and
idempotency.
```

```text
Implementation: follow the approved design, do not mutate requirements/checks,
and record changed paths, documentation effects, and green evidence after red.
```

```text
Validation: run `aegis verify run` before diff review. Resolve deterministic
failures, complete documentation/style/manual review, apply, and stop.
```

```text
Delivery: prepare the handoff/report, apply, and close only after approval.
Do not push, publish, merge, or create a PR.
```

Routing and access changes go in the current form’s control section. Evidence
addition/supersession uses generated `evidence prepare` forms. Models never
invent IDs or edit the graph directly.
