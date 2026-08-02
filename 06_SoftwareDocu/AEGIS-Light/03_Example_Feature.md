<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example — a feature, full workflow

The everyday case: a new user-facing behavior, checkpoint mode (the
default — the agent stops twice: after `frame`, and before the delivery
commit).

## You say

```
using aegis workflow, implement: export a playlist as an M3U file
```

## Stage 1-3 — frame, specify, design

The agent creates a branch and a journal (`aegis task new`), explores
the code, and comes back with the **frame checkpoint**:

> Scope: M3U export only, no PLS; new module `src/export/m3u.py`; full
> path (new user-facing behavior). One requirement proposed:
> "Export playlist as M3U". Proceed?

You answer — trim it, extend it, or just "yes". This is the cheap moment
to course-correct; everything after is mechanical. The agent then writes
the requirement file (`aegis req new functional "Export playlist as
M3U"`, then fills prose, verification, paths, tests), a short spec for
the M3U format, and a design note in the journal. No pause — the journal
records each stage transition:

```
- 2026-08-02 frame: scope agreed - M3U only; full path.
- 2026-08-02 specify: created REQ-FUNC-3fa2 + spec.
- 2026-08-02 design: writer joins tracks; forward slashes everywhere.
```

## Stage 4 — build (test first)

The step file orders it explicitly: failing test **before**
implementation, and the red run noted in the journal.

```
- 2026-08-02 build: test_roundtrip red as expected (no module m3u).
```

Then implementation until green, with the focused regression as the fast
inner loop:

```bash
python .agentic/aegis.py test --impacted --task TASK-8b12
```

```
test --impacted (1 test ref(s)): exit 0 (0.4s)
```

The agent runs `aegis check` before leaving the stage and self-corrects
anything it flags (a forgotten `affected_paths` entry, a stray file).

## Stage 5 — deliver

Full suite (not just impacted), the advisory report, the knowledge page,
and the delivery summary. Naming the task scopes the diff checks to it
and reports a branch mismatch:

```bash
python .agentic/aegis.py check --task TASK-8b12 --strict --run
python .agentic/aegis.py report TASK-8b12
```

```
run: test started
run: test ok (3.2s)
summary: errors=0 warnings=0 notes=0
result: ok
strict: ok
report appended to .agentic/tasks/TASK-8b12.md
```

Then the **delivery checkpoint** — the agent shows you the report and
waits for your yes before committing / opening the PR. This stop always
happens, even in autopilot: publishing is the outward-facing act.

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

The journal tells the whole story — scope decision, red test, findings,
ticked checklists, delivery report. Review is reading one markdown file
plus the diff. And if you stop mid-task (any stage, any reason):

```bash
python .agentic/aegis.py status
```

names the open task and its stage; the next session — tomorrow, another
PC, another model — continues from the first unticked checklist item.
