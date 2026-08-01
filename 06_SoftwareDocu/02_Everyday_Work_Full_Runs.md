<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Everyday Work: Full Runs

This note explains what it actually feels like to build a feature or fix a
bug through AEGIS on a normal day, once it is already installed and
configured. It covers the standard, full eight-stage lifecycle. A separate
note covers the shorter path for genuinely small changes and how to bypass a
blocked step when that is the right call.

## The shape of a run

Everything AEGIS governs happens inside one **run**. A run is one feature, one
fix, or one change, tracked from intake to delivery as a sequence of
**stages**:

```text
intake -> alignment -> requirement -> design -> check -> implementation -> validation -> delivery
```

Every stage follows the same four-step loop:

```text
<workflow> stage prepare
# edit the generated TOML/Markdown file(s)
<workflow> stage apply
# review the imported state, then get explicit human approval
<workflow> stage close
```

- `prepare` creates (or reconstructs) the current stage's form file(s) on
  disk.
- You (or your agent, on your behalf) fill them in.
- `apply` validates every file in the stage directory and imports it into the
  run's authoritative state. It does **not** advance the run — a mistake
  caught here can still be fixed and re-applied.
- `close` is the one step that always needs your explicit approval. It
  journals that approval, advances to the next stage, and prepares it.

Nothing in AEGIS advances past a stage without that human `close`. An agent
can draft every form, run every command, and recommend closing — but the
approval itself is yours.

## Starting a run

```text
<workflow> run start feature
<workflow> run start fix
<workflow> run start change
```

This creates and selects a new run, prepares its intake form, and returns the
form's path. A sensible first prompt to an agent looks like:

```text
Run `<workflow> config show --json` to confirm the active policy. Then run
`<workflow> run start feature`. Open the returned intake form, draft the
statement, scope hints, and access mode, then stop for my review.
```

If you already have a run in progress, resume it instead of starting a new
one:

```text
<workflow> run resume
```

`run resume` opens the active artifact and reports where the run stands —
current stage, imported revision, and any blockers — without changing
anything.

## Walking the eight stages

**Intake.** You state what you want done: the statement, any scope hints, and
the access mode the work needs (how much of the repository it is allowed to
touch). This is the seed everything downstream cites back to.

**Alignment.** Before any code is discussed, AEGIS captures shared
understanding: what's in scope, what's explicitly out, the assumptions being
made, acceptance criteria, open questions (each with a recommended answer),
an assessed risk level, and the paths expected to change. This stage exists
so a misunderstanding surfaces before requirements are written, not after
implementation.

**Requirement.** Every requirement is one atomic, independently verifiable,
observable contract — not an implementation detail. A typical prompt:

```text
Generate one requirement form per atomic observable contract. Include
success, rejection, boundary, error, state-transition, and non-functional
contracts that apply. Put concrete observable examples in a companion spec;
keep internal design out. Apply the collection and stop for approval.
```

Requirement mutations only ever happen through this stage's forms — nothing
elsewhere in AEGIS edits a requirement directly. Each one gets a durable,
UUID-backed ID and an optional companion spec file for detailed examples that
would make the requirement sentence itself unwieldy.

**Design.** The internal "how": alternatives considered, the selected
approach, interfaces and data shapes, compatibility choices, and the intended
implementation sequence, all citing exact requirement IDs. The design lives
in one authoritative Markdown document for the run; `apply` records its
digest and the digests of every requirement it cites, so a later change to
either one flags the approval as stale.

**Check.** Deterministic, requirement-linked checks are written before the
implementation that should pass them. For a fix, this stage must first
reproduce the actual defect as failing (red) evidence — proving the bug is
real and observable before touching any code. There are two ways to run a
check:

```text
# external mode — you or your agent run the command, then record it
<workflow> check prepare
# run the command(s), fill in evidence.toml
<workflow> check record

# managed mode — AEGIS runs the command itself
<workflow> check run
<workflow> check run <check-id>...
```

Which mode applies is a workspace configuration choice, not a per-run one.

**Implementation.** Only the approved design gets implemented — this stage
does not get to rewrite requirements or checks it disagrees with; disagreement
routes back through an earlier stage's control section instead. Closing
implementation requires both the earlier red evidence and new green evidence
for the same check, proving the fix or feature actually works.

**Validation.** Deterministic verification always runs first, before any
human reads a diff:

```text
<workflow> verify run
```

This performs impact analysis (which requirements and checks the change
touches), every enabled quality gate in a fixed order (build, typecheck,
lint, test, security), invariant checks, traceability and coverage audits,
and a working-tree review — then writes a validation summary. Only after
that does the human-led review happen: the actual diff, documentation
effects, style, and anything the deterministic pass cannot judge on its own.

**Delivery.** The final handoff: preflight references, remaining risks, and
the human decision to hand the work off. Closing delivery marks the AEGIS run
complete. It is deliberately inert beyond that — no Git push, no pull
request, no merge, no publication. Any of those is a separate, explicitly
requested action outside AEGIS's own scope.

## Adding more than one item to a stage

The requirement and check stages can hold a collection, not just one item.
Use `stage add` to create another item's form within the same stage before
applying:

```text
<workflow> stage add
```

`apply` then validates and imports the entire collection together, once every
file in it is ready.

## Routing back to an earlier stage

If work in a later stage reveals that an earlier decision was wrong — a
requirement was incomplete, the design missed a constraint — the correct move
is not to quietly patch the earlier artifact. Every generated form carries a
control section for exactly this: record the requested earlier stage and the
reason, apply it, and get explicit approval before AEGIS actually routes
back. This keeps the run's history honest about what changed and why, rather
than hiding a late-discovered gap.

## What the human is actually approving

At each `stage close`, you are not approving "this looks fine at a glance." A
useful mental model: you are approving that the artifact on disk — the actual
TOML/Markdown AEGIS just validated and imported — correctly represents the
decision made, and that it's safe to let the run move forward on that basis.
Everything downstream (checks, implementation, verification, delivery) will
cite back to exactly what was closed here, digest-pinned where it matters
(design and requirements). That is also why an agent's plan-mode discussion,
however thorough, does not substitute for the imported artifact and the close
approval itself — only those are authoritative.
