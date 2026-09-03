<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 04 - Collaboration and small-model support

AEGIS uses ordinary Git collaboration for durable workflow records. Branches
carry source changes and the governance files needed to understand them.
Optional host integrations add review entry points and shared local job
tracking; they do not synchronize uncommitted work between machines.

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

The AEGIS CLI does not create branches, worktrees, merges, or remote pushes.
A coding agent may perform Git operations when the applicable workflow and
user authority allow them; a journal, plugin or review verdict grants no
additional authority.

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

## Independent reviewers in each host

The coordinator supplies the same task, scope, candidate digest, changed-file
evidence and requirement links to two independent reviewers. Reviewers inspect
actual files and return `approved` or `changes_required`; the coordinator
records the verdicts and checks that the candidate stayed unchanged. Any edit
invalidates both verdicts and requires the next permitted review round.

| Host | Implemented review mechanism | Access boundary |
|---|---|---|
| OpenCode | Two native review subagents. | Read-oriented tool policies; mutations remain coordinator operations. |
| Codex | Two custom review-role TOMLs; bundled prompts support fresh delegated reviewers if custom roles are unavailable. | Roles request read-only sandbox settings; bridge `--role reviewer` is a cooperative guard, not authenticated identity. |
| Pi | `review.mjs` launches a separate nonpersistent process for each role. | Read/grep/find/list tools, with extensions, skills, context files and prompt templates disabled. |
| Qwen Code | Two native agents with plan approval mode. | Read/search/list tools; no shell or mutating MCP tools in their declared tool list. |
| Claude Code | `aegis:spec-review` and `aegis:quality-review`. | Read/Grep/Glob tools; the plugin does not rely on unsupported agent-local permission, hook or MCP fields. |

Host settings, effective permissions and live overrides still determine actual
access. Prompt instructions and declared tool lists are not an OS sandbox or
a guarantee of model compliance. Pi has no built-in subagents: its fresh
review process uses the supplied `--model` or the host's saved default, which
may differ from an interactive session's current selection.

## Accounts, machines and verification

Each user installs the built package into their own host profile and uses that
host's existing authentication and model configuration. The package contains
no author's API key, subscription session or model selection. Authentication
and provider eligibility remain the host/provider's responsibility.

Windows and Linux packages use the same workflow and shared runtime. CLI and
Desktop share resources only when they use the same supported backend and
configuration. Remote backends and WSL CLI sessions need installation in their
own environment. Claude Desktop WSL plugin sessions are currently unsupported.

Verification reservations are local to the configured shared cache and
checkout. They survive host restarts but do not lock other machines or detect
manually launched test suites. Inspect uncertain processes before restarting
verification; record relevant outcomes in the journal so another machine has
durable evidence rather than relying on local cache access.

The core works offline. Model-driven host sessions use the user's selected
provider and may require network access. No models are bundled. Package
verification has exercised backend/native resources without model requests;
complete model-led workflows and reviewer behavior, including small-model
compliance, remain unverified. See
[implementation status](05_Implementation_Phases.md) for the tested versions.

## Team CI

Teams that need enforcement use the existing CI boundary:

```text
python .agentic/aegis.py check --strict --run
```

This makes objectively broken records, failed configured commands, and selected
promoted warnings fail CI. It does not turn local agent writes into hard
blocks, and it proves only the configured commands that actually ran.
