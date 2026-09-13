<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example - a feature, full workflow

The everyday case: a new user-facing behavior in checkpoint mode. This is the
default: the agent stops after every stage with concrete continue, revise or
return, and pause choices. Between those stops it does not go quiet: whenever it
records a deviation it also says so, as a single `DEVIATION` line that
never pauses the work and never waits for an answer.

## You say

```
using aegis workflow, implement: export a playlist as an M3U file
```

## Stage 1-3 - frame, specify, design

The agent first analyzes the request and selected repository evidence. It
reads `.agentic/context/project.md` and relevant environment-guide sections when
present, follows their component/source/test references, and verifies current
claims against this checkout. Missing context can be populated incrementally
with known facts. Proposed export behavior stays in task/draft records until
implemented. It
records a Frame card that separates what you stated, what it observed in files,
what it inferred, and what remains unknown. It then establishes a suitable task
branch unless current instructions require the existing branch, creates a
journal (`aegis task`), and comes back with the **frame checkpoint**:

> Scope: M3U export only, no PLS; new module `src/export/m3u.py`; full
> path (new user-facing behavior). One requirement proposed:
> "Export playlist as M3U". Proceed?

You answer - trim it, extend it, or just "yes". This accepts scope; it does
not claim implementation. The agent then builds a behavior inventory and
Frame-to-requirement coverage table, writes the requirement file (`aegis req
functional "Export playlist as M3U"`), adds a short exact-format spec, and
records a proportionate design with requirement links and test seams. Each
stage ends with its own report and choices before the journal advances:

```
- 2026-08-02 frame: scope agreed - M3U only; full path.
- 2026-08-02 specify: created REQ-FUNC-3fa2 + spec.
- 2026-08-02 design: writer joins tracks; forward slashes everywhere.
- 2026-08-02 design: proposed export architecture records the m3u writer in the task.
```

That last line is design's other output. Because the feature changes the
`export` component's shape, the task Design carries a compact proposed
architecture with the new writer. The canonical `knowledge/export.md`
diagram continues to describe current code during implementation. At
`validate`, the agent reconciles that page with what was actually built, so a
reader never has to distinguish a proposed diagram from current knowledge.

Before touching an unfamiliar file, the agent - or you - can ask what
already governs it:

```bash
python .agentic/aegis.py explain src/export/m3u.py
```

## Stage 4 - build (test first)

First prepare the project's documented test environment and confirm readiness.
The pytest references in this example assume a runner that honors them. Preview
selection with `test --impacted --base HEAD --dry-run` when needed; a preview is
not proof. If selection is unavailable or the runner ignores it, use a native
focused command rather than repeatedly falling back to the full suite.

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

Keep the requirement's `affected_paths` and `linked_tests` current before
selecting focused tests. Then implement until green, using focused regression
as the inner loop:

```bash
python .agentic/aegis.py test --impacted --base HEAD --no-fallback
```

```
test --impacted (1 test ref(s)): exit 0 (0.4s)
```

Inner-loop retries omit `--task`, so they do not turn the journal into a command
transcript. After the increment is stable, record one consolidated green result
that names the final focused command and verified behavior.

After implementation, the agent compares the candidate with that anchor:

```bash
python .agentic/aegis.py evolution --task TASK-8b12
```

The output names every added, modified, and removed path as `source`, `tests`,
or `other`. Changes are expected and never make the command fail. Reconcile an
unexpected path first. Use a `DEVIATION build:` line only if the final candidate
retains a material scope, design, implementation, or evidence departure; a
surprising report that is corrected is ordinary development work.

The agent runs `aegis check` before leaving the stage and self-corrects
anything it flags (a forgotten `affected_paths` entry, a stray file). A
finding it accepts rather than corrects is spoken, not just logged.

## Stage 5 - validate

The agent reviews the candidate and reconciles affected requirements, project
context, environment guidance and component knowledge. The current documents
describe the built positive behavior and actual setup. History and proposals
remain in task records; an established contract is preserved when a defect
needs correction. If `[review] enabled = true`, obtain both independent verdicts for the
same candidate within the configured round limit. Then run final proof once
through the strict check with its eligible configured commands. Naming the task scopes the
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

A clean run like that says nothing extra. A run that is not clean does -
say the suite is green but one requirement ends up verified by hand:

```
DEVIATION validate: REQ-UX-91c4 verified by inspection, not by test - the
splash text could be asserted; deferred, so a regression there is silent.
```

One line, mid-run, then it carries on. It is the agent's judgement, not a
`check` finding, which is why it says `DEVIATION` and not `WARN`.

Corrections to executable behavior, tests or verification configuration need
relevant focused proof before the final full run. Prose-only corrections need
semantic and traceability review, not an extra runtime run of their own. Schedule
full strict verification after all edits and review; a failure or a later
candidate change requires fresh proof for the candidate handed to deliver.
If validation changes a repository file outside `.agentic/`, the agent reruns
`evolution` first so the saved report matches the final
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
Every deviation you heard along the way is presented again here, in full - the
notices were notifications, not approvals, so they never shorten this stop.

After approval it generates and reads the report:

```bash
python .agentic/aegis.py report TASK-8b12
```

If the validated candidate changed or needs correction, delivery stops and
returns to `validate`; there is no stage-zone heuristic pretending to know
when a merge-base diff was edited.

## Close out according to the approved outcome

For an outcome that can fail after the work commit, such as a push or PR:

1. Commit the approved work and report with the journal still at `deliver`.
2. Perform the explicitly approved push/PR or other outcome.
3. Only after success, record `stage: done` and commit the close-out with the
   required Git authority. A failed outcome stays at `deliver`.

For a **local commit-only outcome**, the current deliver step allows closing
the journal before that same commit. A second commit is unnecessary. Never
treat a frame approval, review verdict or request to continue as authority to
commit, push, merge or publish.

## What you can rely on afterwards

The task-owned records collectively retain the durable story: accepted scope,
one meaningful red and final green per behavior increment, repository evolution,
material findings, stage outcomes, and delivery report. They intentionally omit
routine searches, edits, tool mechanics, and corrected retries. Review those
records with the diff. And if you stop
mid-task (any stage, any reason):

```bash
python .agentic/aegis.py status
```

finds the open task ID. Then run `brief TASK-8b12`, confirm the branch, read the
current stage, Handoff paths and required full journal, and continue the first
unticked action. Transfer committed records with separately authorized Git
operations; uncommitted changes do not travel with a branch.

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

## Using a host integration

Use the host's AEGIS entry point from [Agent_Plugins.md](Agent_Plugins.md).
It reads this same checkout's workflow; it does not create a separate process
for governance. Long verification runs use the shared `run`/`job` operations.
After a restart, inspect the existing job and its logs before launching another
suite. An exit-zero result is not final proof if its candidate fingerprint
changed during the run. Local cache records do not travel in a Git handoff.

All IDs and test outputs above are illustrative. They are not verification
results for a shipped M3U implementation.
