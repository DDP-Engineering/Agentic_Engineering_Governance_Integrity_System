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
- Project/environment context and component pages are shared current-state
  documents. Each branch edits only affected facts. After integration, reconcile
  those facts with the combined implementation and established requirements.
  Journals and Git retain decisions/history; draft records hold proposed behavior.
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
3. Read `.agentic/context/project.md` and relevant
   `.agentic/context/environment.md` sections when present, then the current
   step file and Handoff `must_read` paths.
4. Load only linked requirements, specifications, knowledge, source, and tests
   that the current step needs.
5. Read the full journal whenever the brief is shortened, stale, incomplete,
   or the stage requires full history/evidence.

`brief` limits scalar values to 240 characters, active rulings to eight, and
visible children to twenty. `summary` limits each projected field to 240
characters and makes truncation explicit. `status` lists up to twenty open
journals by default; `check` prints up to forty findings unless `--full`
or `--strict` requests all findings.

Brief includes only the two context paths and their file presence. Read selected
references instead of preloading the project. Missing files remain compatible
with legacy projects; empty sections remain valid until facts are established.
Describe actual responsibilities and behavior positively, and keep uncertainty
in the task rather than filling shared documents with speculative features.

These bounds reduce avoidable context use; they are not a tokenizer-specific
context guarantee and never allow an agent to skip required source, evidence,
or full-journal reads. Within an intact session, reuse unchanged documents
already read and inspect changed sections with their relevant earlier decisions
and evidence. Compaction or lost context requires durable re-entry again.
Step files reference the shared reporting/resume instructions instead of copying
them; Handoff remains required and should contain only the next action and
necessary paths, rather than repeated Frame, Design or Log content.

Fresh task, requirement and context scaffolds omit marked authoring notes. Evolution can
return compact paths/statuses/areas while retaining complete fingerprints on disk.
These reduce text volume; actual end-to-end token savings have not been measured.

The prompt contract uses compact records and selective reads for constrained
context. It guarantees neither a tokenizer-specific 64K budget nor model
compliance. Recorded evaluations use their explicitly configured windows;
the recent matched cohorts used 131,072 tokens, which is not independent proof
of server allocation. The design supports bounded work through these structures:

- **Analyze -> Challenge -> Write -> Audit** gives each stage a stable order.
- `STATED`, `OBSERVED`, `INFERRED`, and `UNKNOWN` keep evidence separate from
  assumptions and prevent silent invention.
- The Frame card preserves the original idea, scope, success signals and
  decision-blocking questions across sessions.
- The behavior inventory and Requirement coverage table expose omissions and
  overlap before implementation.
- Design uses 30 lines as a default, not a hard cap, and expands only for
  material interface, state, trust, concurrency, compatibility, migration or
  operational risk.
- The journal Log keeps only stage outcomes, material engineering changes,
  consolidated verification, blockers, approvals, deviations, and delivery;
  it links to dedicated detail instead of repeating it.

These structures aim to preserve intent across sessions; their effect on a model
must be measured. No model is bundled. Representative prompt evaluations now
exercise actual model/tool behavior, but do not establish universal compliance,
small-context acceptance or a complete lifecycle in every native host.

## Recommended session shape

For a constrained model, one stage per session is a practical operating
pattern:

```text
brief -> current context -> current step -> handoff must_read -> first unticked action
-> update Log, Handoff, and Stage report -> summary -> stop
```

The prompt cheatsheet in `.agentic/AGENTS.md` and
`06_SoftwareDocu/08_Prompt_Cheatsheet.md` provides stage-scoped prompts.
Checkpoint mode uses this shape by default for every model. Configured
autopilot may continue through several stages, but the same durable records
must be updated at each pause or transition.

## Decisions, authority, and review

Rulings capture durable decisions already made; they cannot create permission
to commit, push, merge, publish, or broaden scope. Handoff is operational
state, not approval. A Stage report is a current communication snapshot, not
fresh validation.

For a downstream project opting into explicit review:

```toml
[review]
enabled = true
max_fix_cycles = 2
```

This permits one initial pair of independent review verdicts and up to two
fix-and-re-review rounds. It does not create a review stage or replace
`validate`; ordinary semantic review, focused/full proof, strict checking,
and the delivery checkpoint still apply.

The maintainer checkout has no installed `.agentic/aegis.toml`; this example is
not its active configuration. The payload default keeps explicit review off.

Checkpoint mode stops after every stage and presents concrete continue, revise
or return, and pause choices. `[interaction] autopilot = false` is the default,
including for legacy configurations with no interaction table. Autopilot flows
between intermediate stages when configured or explicitly requested. Immediate
`DEVIATION` notices for material scope, implementation, contract, or
verification departures and pre-publication approval remain visible in either
mode. Corrected internal tool
errors are operational detail—neither deviations nor journal events. Expected
red tests are ordinary test-first evidence and are consolidated by meaningful
behavior increment.

## Independent reviewers in each host

The coordinator supplies the same task, scope, candidate digest, changed-file
evidence and requirement links to two independent reviewers. Reviewers inspect
actual files and return `approved` or `changes_required`; the coordinator
records the verdicts and checks that the candidate stayed unchanged. A candidate
change clears both verdicts while preserving consumed rounds and old findings;
new approvals require the next permitted review round. Journal-only boundary
records do not themselves imply a change to the proved source candidate.

Both reviewers receive current linked files, including untracked requirements,
and focused proof due at that phase. Read test definitions as assertions,
executed results as proof and missing historical records as separate limits.
Final full strict verification follows approvals; its pending checklist is not
itself a missing prerequisite for the reviewers. A review verdict grants no
publication authority, and an exhausted final round needs a concrete human
scope/policy decision before further fixes or final proof.

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
own environment. Desktop availability depends on host support for that backend;
a successful CLI installation does not establish GUI plugin support.

Verification reservations are local to the configured shared cache and
checkout. They survive host restarts but do not lock other machines or detect
manually launched test suites. Inspect uncertain processes before restarting
verification. Retain one consolidated material outcome in the journal so
another machine has durable evidence; keep polling detail, retries, and raw
output in the local job cache. Poll at useful intervals, reusing the same job,
rather than repeatedly reopening its unchanged output. Record fresh proof for
the candidate being delivered.

Prepare the project's documented environment before verification, use focused
build tests, and run full strict verification after final edits and review.
An unchanged fingerprint during a cancelled job does not establish that an
earlier successful run covered the final candidate or its environment.

The core works offline. Model-driven host sessions use the user's selected
provider and may require network access. No models are bundled. Package
verification has exercised backend/native resources without model requests;
representative development evaluations separately exercise model-led stage work
and fresh reviewer sessions. They do not test installed plugin discovery, native
custom-role routing, complete workflows in all hosts or small-model reliability.
See the [evaluation guide](../05_Software/aegis/evaluations/README.md) and
[implementation status](05_Implementation_Phases.md) for verification routes
and the distinction between current guidance and recorded evidence.

## Team CI

Teams that need enforcement use the existing CI boundary:

```text
python .agentic/aegis.py check --strict --run
```

This makes objectively broken records, failed configured commands, and selected
promoted warnings fail CI. It does not turn local agent writes into hard
blocks, and it proves only the configured commands that actually ran.
