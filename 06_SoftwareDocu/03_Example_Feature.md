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
journal (`aegis task`), and saves the Frame before presenting the checkpoint.
The following scope is illustrative: M3U-only, the new module and path rules
are proposals to confirm, rather than facts implied by the short request:

> Scope: M3U export only, no PLS; new module `src/export/m3u.py`; full
> path (new user-facing behavior). One requirement proposed:
> "Export playlist as M3U". Proceed?

You answer - trim it, extend it, or just "yes". This accepts scope; it does
not claim implementation. The agent then builds a behavior inventory and
Frame-to-requirement coverage table, writes the requirement file (`aegis req
functional "Export playlist as M3U"`), adds a short exact-format spec, and
records a proportionate design with requirement links and test seams. Each
stage ends with its own report and choices before the journal advances:

After the chosen transition, the agent reads the next step file named directly
in the current step's instructions, such as `.agentic/steps/3_design.md` after
Specify. The quick path and correction returns name their destination files too.

```
- 2026-08-02 frame: scope agreed - M3U only; full path.
- 2026-08-02 specify: created REQ-FUNC-3fa2 + spec.
- 2026-08-02 design: writer joins tracks; forward slashes everywhere.
```

The proposal stays in the task: `knowledge/export.md` keeps describing the
current code until validate reconciles it with the reviewed implementation.
With `[diagrams] enabled = true`, design would also draw the new writer as a
Mermaid structure diagram in `tasks/diagram_TASK-8b12.md` and show it at the
design checkpoint; this example runs with the default, so it draws none.

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

Update directly affected docstrings, usage examples, and setup instructions
with the implementation. Record material discoveries and design changes in
the task journal. Component knowledge is reconciled during Validate; update
relevant facts earlier only when another agent needs them for a handoff.

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

The agent reviews the candidate and resolves implementation corrections, then
updates or creates affected component knowledge pages against the code and
tests. It migrates touched legacy pages. It also reconciles affected
requirements, project context, and environment guidance. The current documents
describe the built positive behavior and actual setup. History and proposals
remain in task records; an established contract is preserved when a defect
needs correction. If `[review] enabled = true`, obtain both independent verdicts for the
same candidate within the configured round limit. Reviewers read current files,
including untracked records, and the focused proof due at this phase. The
not-yet-run final strict check is not a reason to withhold a review verdict.
Then run final proof once
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

Before the **delivery checkpoint**, the agent compares the current candidate
with the recorded validated candidate using the same binding method and scope.
A task-base diff describes the proposed changes, not edits since validation.
If identity is unresolved, it records the missing evidence without claiming a
change. If proof is stale, it saves the return to Validate and clears stale
enabled-review verdicts while retaining consumed rounds. These are journal-only
updates; they do not authorize source repair or another verification run.

For an unchanged proved candidate, it saves the approval pause at `deliver`:
Handoff is waiting, Stage report is paused with `needs_user: yes`, and both
`next` fields name the pending delivery decision. It rereads those saved records,
runs `summary`, and presents its actual output before the delivery evidence.
Historical Log text stays unchanged; the new outcome is appended once.

At the checkpoint, the agent shows you the validation evidence
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
