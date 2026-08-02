<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 04 — Collaboration and small-model support

## Multiple users, branches, machines

There is no shared server and no shared database: the branch *is* the
workspace. Everything AEGIS Light knows lives in committed files, so the
normal git workflow already gives us multi-user, multi-machine governance:

- **Parallel work never collides by construction.** One task = one journal
  file; one requirement = one file with a random-suffix ID. Two people on
  two branches create disjoint files. The only shared-file merges are
  edits to the *same* requirement, which is a real conflict a human should
  see anyway.
- **Post-merge reconciliation is a check, not a ceremony.** After merging,
  `aegis check` on the target branch flags duplicate IDs, dangling links,
  and requirements whose `affected_paths` diverged. Fix-forward.
- **Cross-machine continuation** is just `git pull` + `aegis status` +
  the three-line resume procedure from `AGENTS.md`. Nothing is stored in
  worktree-local state, user home directories, or platform-specific paths.
- **Windows/Linux parity**: pure-stdlib Python, `pathlib` throughout,
  forward slashes in all stored paths, LF line endings in all generated
  files, no Node launcher, no shell-specific hook transports.

Team hardening, strictly opt-in and outside the agent's inner loop:
CI `check --strict` on PRs (doc 03), and ordinary branch protection.
AEGIS Light adds no protection mechanisms of its own.

## Small local models (Qwen3-27B, gpt-oss-20B, 32k–256k context)

The heavy stack assumes a frontier model that can hold policy, forms, and
long tool transcripts. AEGIS Light is designed so that **one stage of one
task is a complete unit of work for a 32k-context session**:

Context budget for a `build`-stage session (worst case, ~tokens):

| Item | Budget | How it is held |
|---|---|---|
| `AGENTS.md` | ≤ 2.5k | fixed size, reviewed when edited |
| Current step file | ≤ 1.5k | one file per stage, fixed size |
| Task journal | ≤ 1.5k | grows append-only; `status` prints the header, the checklist and the **last 5 log lines**, so what a session loads stays flat even when the file is long |
| Linked requirements (2–3 × ~0.4k) | ≤ 1.5k | one file each, read on demand |
| One spec | ≤ 1.5k | optional |
| `aegis check` / `status` output | ≤ 0.5k in the steady state | `check` prints at most 40 findings (`--full`, implied by `--strict`, shows all); `status` lists at most 20 open tasks. A freshly adopted or neglected repo can exceed the budget on its **first** runs — that backlog is the point — but the capped output keeps even that readable |
| **Workflow overhead total** | **≤ 9k** | |

That leaves ~20k+ of a 32k window for actual code and test content —
workable; with 128k–256k configured, comfortable. Rules that make this
hold:

1. **Never require the whole register in context.** Cross-file consistency
   (links, duplicates, coverage) is computed deterministically by
   `aegis check`; the model only reads the report.
2. **Stage docs are self-contained.** A session that loads only
   `AGENTS.md` + one step file + one journal has everything it needs — no
   chained references into policy documents.
3. **CLI output is model-food.** Short, plain, stable line format, no
   tables wider than 100 chars, no ANSI. A 20B model can quote a finding
   line verbatim into the journal.
4. **The journal is the handoff protocol between sessions and between
   models.** Recommended split for weak models: run *one stage per
   session*, end every session by updating the journal. A frontier model
   can do frame/specify/design; the local model does build; either does
   deliver.
5. **Journal growth is bounded**: log lines are one sentence; when a
   journal exceeds ~120 lines the deliver step archives detail into the
   report section rather than growing the log.

The prompt cheatsheet in `AGENTS.md` gives per-stage one-liners sized for
small models, e.g.:

```
Read .agentic/AGENTS.md. Continue TASK-8b12 (stage build): follow
.agentic/steps/4_build.md, then update the task journal.
```
