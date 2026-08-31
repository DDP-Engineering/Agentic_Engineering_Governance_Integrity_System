<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example — a feature, full workflow

The everyday case: a new user-facing behavior, checkpoint mode (the
default — the agent stops twice: after `frame`, and before the delivery
commit). Between those two stops it does not go quiet: whenever it
records a deviation it also says so, as a single `DEVIATION` line that
never pauses the work and never waits for an answer.

## You say

```
using aegis workflow, implement: export a playlist as an M3U file
```

## Stage 1-3 — frame, specify, design

The agent creates a branch and a journal (`aegis task`), explores
the code, and comes back with the **frame checkpoint**:

> Scope: M3U export only, no PLS; new module `src/export/m3u.py`; full
> path (new user-facing behavior). One requirement proposed:
> "Export playlist as M3U". Proceed?

You answer — trim it, extend it, or just "yes". This is the cheap moment
to course-correct; everything after is mechanical. The agent then writes
the requirement file (`aegis req functional "Export playlist as
M3U"`, then fills prose, verification, paths, tests), a short spec for
the M3U format, and a design note in the journal. No pause — the journal
records each stage transition:

```
- 2026-08-02 frame: scope agreed - M3U only; full path.
- 2026-08-02 specify: created REQ-FUNC-3fa2 + spec.
- 2026-08-02 design: writer joins tracks; forward slashes everywhere.
- 2026-08-02 design: export architecture redrawn with the m3u writer added.
```

That last line is design's other output. Because this feature changes the
shape of the `export` component, the agent opens
`knowledge/export.md` and redraws its `## Architecture` diagram with the
new writer in it — the shape the component will have **after** the change,
marked in one line as the intended shape so nobody mistakes it for code
that already exists. At `validate` the agent checks the built code against
that drawing and removes the mark. You get the before-and-after of a
component for free, in the same file a reader already opens to understand
it, and the picture is never left describing a plan that was abandoned.

Before touching an unfamiliar file, the agent — or you — can ask what
already governs it:

```bash
python .agentic/aegis.py explain src/export/m3u.py
```

## Stage 4 — build (test first)

The step file orders it explicitly: failing test **before** implementation,
with a reproducible red record in the journal.

```
- 2026-08-02 build red: command=`pytest -q tests/export/test_m3u.py::test_roundtrip`; exit=1; expected missing behavior=no module m3u.
```

With the expected failure confirmed, the agent records the repository before
touching implementation:

```bash
python .agentic/aegis.py anchor --task TASK-8b12
```

Then implementation continues until green, with the focused regression as the
fast inner loop:

```bash
python .agentic/aegis.py test --impacted --base HEAD --task TASK-8b12
```

```
test --impacted (1 test ref(s)): exit 0 (0.4s)
```

After implementation, the agent compares the candidate with that anchor:

```bash
python .agentic/aegis.py evolution --task TASK-8b12
```

The output names every added, modified, and removed path as `source`, `tests`,
or `other`. Changes are expected and never make the command fail — but if the
report names something the agent did not expect, that gets a `DEVIATION build:`
line in the conversation as well as in the journal.

The agent runs `aegis check` before leaving the stage and self-corrects
anything it flags (a forgotten `affected_paths` entry, a stray file). A
finding it accepts rather than corrects is spoken, not just logged.

## Stage 5 - validate

The agent reviews the candidate, refreshes its requirements and knowledge page,
and only then runs the full suite and strict check. Naming the task scopes the
diff checks to it and reports a branch mismatch:

```bash
python .agentic/aegis.py check --task TASK-8b12 --strict --run
```

```
run: test started
run: test ok (3.2s)
summary: errors=0 warnings=0 notes=0
result: ok
strict: ok
```

A clean run like that says nothing extra. A run that is not clean does —
say the suite is green but one requirement ends up verified by hand:

```
DEVIATION validate: REQ-UX-91c4 verified by inspection, not by test — the
splash text could be asserted; deferred, so a regression there is silent.
```

One line, mid-run, then it carries on. It is the agent's judgement, not a
`check` finding, which is why it says `DEVIATION` and not `WARN`.

Any correction sends the task back to the appropriate stage and makes this
proof run again. If validation changes a repository file outside `.agentic/`,
the agent reruns `evolution` first so the saved report matches the final
candidate. Once it is current, `stage: deliver` means "validated, not yet
published."

Before pausing or handing the task to another agent, record the latest stage
report in the journal and show the compact view:

```bash
python .agentic/aegis.py summary TASK-8b12
```

For this transition, the report records `stage: validate`, `result: completed`,
and `current: deliver`. The command reads those recorded facts only; it does
not repeat validation, grant delivery approval, or update the journal.

## Stage 6 - deliver

Then the **delivery checkpoint** - the agent shows you the validation evidence
and final diff and waits for your yes before committing / opening the PR. This
stop always happens, even in autopilot: publishing is the outward-facing act.
Every deviation you heard along the way is presented again here, in full — the
notices were notifications, not approvals, so they never shorten this stop.

After approval it generates and reads the report:

```bash
python .agentic/aegis.py report TASK-8b12
```

If the validated candidate changed or needs correction, delivery stops and
returns to `validate`; there is no stage-zone heuristic pretending to know
when a merge-base diff was edited.

## Two commits, so "done" never lies

Delivery lands in two commits, and the order matters:

1. the **delivery commit** — the work, the report, and the journal while
   it still says `stage: deliver`;
2. the PR (or whatever outcome you agreed);
3. the **close-out commit** — `stage: done`, pushed once the outcome
   actually succeeded.

If anything fails in between, the journal stays at `deliver` and the
task stays visible in `status`. A journal marked `done` always means a
delivery that really happened.

## What you can rely on afterwards

The journal and its state sidecars tell the whole story — scope decision, red
test, repository evolution, findings, ticked checklists, and delivery report.
Review is reading those task-owned files plus the diff. And if you stop
mid-task (any stage, any reason):

```bash
python .agentic/aegis.py status
```

names the open task and its stage; the next session - tomorrow, another
PC, another model - continues from the first unticked checklist item.

## Larger feature with two children and one review fix

Suppose a parent owns an export workflow while two non-overlapping branches
implement the encoder and UI. Each branch creates an ordinary child task:

```text
python .agentic/aegis.py task "Build export encoder" --parent TASK-a100
python .agentic/aegis.py task "Add export controls" --parent TASK-a100
```

Each child completes its own requirements, red/green loop, validation, and
checkpoint. Once both branches are visible in the parent checkout, the parent
validates the integrated candidate; child suites are not integration proof.

With review enabled, round 1 may record specification compliance approved and
implementation quality changes required. Append the finding, clear both
verdicts while fixing only that defect, rerun focused proof, and ask both review
questions again in round 2. Only two approvals for the unchanged integrated
candidate allow the existing delivery checkpoint. The default two-fix policy
still has a finite third and final round.
