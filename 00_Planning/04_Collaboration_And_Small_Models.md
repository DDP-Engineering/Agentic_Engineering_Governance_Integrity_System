<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 04 - Collaboration and small-model support

AEGIS uses ordinary Git collaboration rather than a separate coordination
service. Branches carry source changes and the durable governance files needed
to understand them.

## Branches, machines, and child tasks

- One task has one journal; one requirement has one TOML file with a
  collision-resistant ID. Independent work normally produces independent
  files, reducing merge collisions.
- A task journal records its branch and base commit. A task can be resumed on
  another machine only after its branch and journal are available there; an
  uncommitted worktree never transfers by itself.
- `anchor` and `evolution` make the task's observed change boundary
  reviewable. They are evidence files, not locks.
- `check` after merge is the reconciliation tool: it can expose duplicate
  IDs, dangling references, uncovered paths, stale links, and scope drift.
- Child tasks are opt-in and only one level deep. Their `parent:` links are
  child-side, each child keeps independent evidence, and the parent validates
  the integrated candidate. Only children visible in the current checkout are
  reported.

AEGIS does not create branches, worktrees, merges, or remote pushes. Those are
explicit repository operations with separate authority.

## Durable re-entry for constrained models

The bounded resume sequence is designed for interrupted work and small-context
models:

1. Run `status` if the task identifier is unknown.
2. Run `brief TASK-<id>`.
3. Read the current step file and the Handoff `must_read` paths.
4. Load only linked requirements, specifications, knowledge, source, and tests
   that the current step needs.
5. Read the full journal whenever the brief is shortened, stale, incomplete,
   or the stage requires full history/evidence.

`brief` limits scalar values to 240 characters, active rulings to eight, and
visible children to twenty. `summary` limits each projected field to 240
characters and makes truncation explicit. `status` lists up to twenty open
journals by default; `check` prints up to forty findings unless `--full`
or `--strict` requests all findings.

These bounds reduce avoidable context use; they are not a tokenizer-specific
context guarantee and never allow an agent to skip required source, evidence,
or full-journal reads.

## Recommended session shape

For a constrained model, one stage per session is a practical operating
pattern:

```text
brief -> current step -> handoff must_read -> first unticked action
-> update Log, Handoff, and Stage report -> summary -> stop
```

The prompt cheatsheet in `.agentic/AGENTS.md` and
`06_SoftwareDocu/08_Prompt_Cheatsheet.md` provides stage-scoped prompts.
A larger model may continue through several stages, but the same durable
records must be updated at each pause or transition.

## Decisions, authority, and review

Rulings capture durable decisions already made; they cannot create permission
to commit, push, merge, publish, or broaden scope. Handoff is operational
state, not approval. A Stage report is a current communication snapshot, not
fresh validation.

The current repository enables explicit review:

```toml
[review]
enabled = true
max_fix_cycles = 2
```

This permits one initial pair of independent review verdicts and up to two
fix-and-re-review rounds. It does not create a review stage or replace
`validate`; ordinary semantic review, focused/full proof, strict checking,
and the delivery checkpoint still apply.

Checkpoint mode retains the end-of-frame and pre-delivery approval boundaries.
Autopilot can suppress the frame stop only when the user requests it. Immediate
`DEVIATION` notices remain visible in conversation in either mode.

## Team CI

Teams that need enforcement use the existing CI boundary:

```text
python .agentic/aegis.py check --strict --run
```

This makes objectively broken records, failed configured commands, and selected
promoted warnings fail CI. It does not turn local agent writes into hard
blocks, and it proves only the configured commands that actually ran.
