<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 01 — Workflow and stages

The lifecycle is defined entirely in markdown the agent reads: one entry
document (`AGENTS.md`) and one short step file per stage. There is no stage
state machine in code — the *task journal* records which stage a task is in,
and the agent (or human) moves it forward by editing one line.

## Stage model (recommended, decision D1)

AEGIS uses six stages:

| # | Stage | Absorbs from 2.x | Purpose (one line) |
|---|---|---|---|
| 1 | `frame` | intake + alignment | Understand the ask, agree scope, open the task journal. |
| 2 | `specify` | requirement | Write or update the requirement(s) and, when useful, a spec. |
| 3 | `design` | design | A short design note for non-trivial work; cite requirement IDs. |
| 4 | `build` | check + implementation | Tests first (recommended), then implementation, until green. |
| 5 | `validate` | validation | Review the candidate, update requirements and knowledge, then run `aegis check` and the full test suite as the final action. |
| 6 | `deliver` | delivery | Present the unchanged validated candidate, append the report, commit/PR, and close out truthfully. |

**Quick path** (small fixes/changes): `frame → build → validate → deliver`. The agent
decides proportionality in `frame` and records the choice in the task
journal — no profile flag, no enforcement, just a recorded decision.

**Adoption** of an existing repo is not a separate seven-stage flow; it is
one step file (`steps/adopt.md`) describing three phases:

- **Survey (one session).** After `aegis init`, the agent proposes a
  component breakdown heuristically (directory structure, entry points,
  import clusters, existing docs) and writes it into an adoption task
  journal (`type: adopt`): one checklist item per component with a
  one-line scope and file globs. **The owner reviews and edits this list
  before anything else happens** — that is the alignment moment, replacing
  the four discovery/alignment stages of 2.x adoption.
- **Per component (one session each — sized for a 32k local model).**
  Read the component's code and its *existing tests* (tests are the
  primary evidence of intended behavior); write the knowledge page;
  derive requirements (`active`, `affected_paths` = the component's
  files, `linked_tests` = the existing tests that already verify each
  behavior — adoption mostly links tests, it does not write them); add
  specs only where a requirement alone is not buildable. Real behavior
  with no test gets either a characterization test now (recommended for
  load-bearing behavior) or an empty `linked_tests`, which check #6 then
  flags on every run — those warnings are the post-adoption backlog.
  Behavior that looks *wrong* is adopted as-is and noted in the journal
  as a future task, never silently canonized. Tick the component off.
- **Close.** `aegis check` over the whole tree, fix-forward, `aegis
  report`, PR.

The survey checklist makes adoption interruptible, parallelizable
(different people, branches, or models each take a component; one file
per requirement keeps their merges clean), and incremental — adopt only
the components you actively change; check #5 warns when an unadopted
area is touched.

## The step files

```
.agentic/
  AGENTS.md            # entry point, ≤ 150 lines
  steps/
    1_frame.md         # each ≤ 120 lines
    2_specify.md
    3_design.md
    4_build.md
    5_validate.md
    6_deliver.md
    adopt.md
```

`AGENTS.md` contains: the philosophy paragraph, the stage table, where
artifacts live, the resume procedure, and a prompt cheatsheet (one line per
stage). Agent CLIs that read `AGENTS.md` natively (Codex, Qwen Code) pick it
up directly; for Claude Code, `CLAUDE.md` contains one line pointing at it.

Every step file has the same fixed skeleton, so a small model always knows
what it is looking at:

```markdown
# Stage N — <name>
**Purpose:** one or two sentences.
**Read first:** the task journal; <specific other files>.
**Steps:** numbered, concrete, imperative. 5–10 items.
**Outputs:** the files this stage creates or updates.
**Done when:** a checklist the agent copies into the task journal and ticks.
**Skip when:** the proportionality rule for this stage.
```

Example — `4_build.md` steps (illustrative):

1. Re-read the task journal and the linked requirement(s).
2. For each requirement, write or extend a test that fails for the right
   reason. Run it; record the exact selector or command, non-zero exit, and
   expected missing-behavior reason in the journal (red-before-green is
   recommended, not enforced).
3. Implement until the new tests pass; use `aegis test --impacted` as the
   fast inner loop (it runs only the tests linked to requirements whose
   `affected_paths` you touched — the focused regression from 2.x, kept).
4. Add each touched source path to the requirement's `affected_paths` and
   each new test to `linked_tests` (this is what keeps `--impacted`
   selecting the right regression set).
5. Run `aegis check`; fix what the report flags or note in the journal why
   a warning is accepted.
6. Update the journal: tick the done-checklist, set `stage = deliver`.

## Interaction modes (defined in `AGENTS.md`)

The entry prompt is simply: `using aegis workflow, implement feature X`
(AGENTS.md-native CLIs need nothing more; the cheatsheet gives the
explicit `Read .agentic/AGENTS.md …` form for small models). How often
the agent stops for confirmation is a prompt-level choice between two
modes the instructions define — not a mechanism:

- **Checkpoint mode (default):** two conversational stops, not one per
  stage — at the end of `frame` (scope, chosen path, proposed
  requirements; the cheap moment to course-correct) and before the
  `deliver` commit/PR (report + `aegis check` results presented for a
  yes). The middle stages flow through; the journal records every
  transition regardless.
- **Autopilot:** "… autopilot to deliver" suppresses the frame stop too;
  the pre-PR stop remains, because publishing is the outward-facing act.

These pauses are conversational and orthogonal to the harness's own
permission model (Claude Code permission modes, Codex sandbox approvals
still apply underneath). Autopilot loses no auditability: the journal
still shows the scope decision, the red-test line, check findings, and
ticked checklists after the fact.

## Session resume and stage handoff

The task journal (`.agentic/tasks/TASK-<id>.md`, see doc 02) is the only
state. The resume procedure in `AGENTS.md` is three lines:

1. Open the task journal named in the prompt (or `aegis status` to list
   open tasks).
2. Read `stage:` and the log; open `steps/<stage>.md`.
3. Continue at the first unticked item.

Because the journal is a committed file, resume works across sessions,
across days, across machines, and across *models* — a large model can frame
and specify, a local 27B model can build, and either can validate and deliver. Each stage
is sized so one stage fits in one small-model session (see doc 04).

## What "blocking" becomes

| Earlier approach | AEGIS approach |
|---|---|
| Hook denies a write | Step file says where things go; `aegis check` flags strays |
| Gate must pass to advance | "Done when" checklist in the step file, ticked in the journal |
| Waiver record | A one-line note in the journal: "accepted warning X because Y" |
| Evidence form | The journal log line (free text, timestamped) |
| Enforced red-before-green | Recommended practice in `4_build.md`, noted in the journal |
| Delivery preflight hook | `deliver` step runs `aegis check --strict` before the PR |

The honest trade: a careless agent *can* skip steps. The mitigations are
(a) the journal makes skipping visible in review, (b) `aegis check` makes
it visible in one command, and (c) CI `--strict` makes it a merge blocker
if — and only if — the team opts in.
