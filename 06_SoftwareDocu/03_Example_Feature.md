<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example - a feature, full workflow

The everyday case: a new user-facing behavior in checkpoint mode. This is the
default: the agent stops after every stage with concrete continue, revise or
return, and pause choices. Each stop is recorded with `pause` and each
continuation with `advance`; both print a summary block that the agent shows
before its explanation. Between those stops it does not go quiet: whenever it
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
what it inferred, and what remains unknown. It works on the current branch,
which you created for the feature (AEGIS records the branch and never creates
or switches one unless you ask), creates a journal (`aegis task`), saves the
Frame and records the checkpoint:

```bash
python .agentic/aegis.py pause TASK-8b12 --next "Accept the framed scope and continue to specify?" --changed "Frame card written"
```

`pause` prints the summary block, which the agent shows first:

```text
Stage:        frame - paused
Task:         TASK-8b12
Current:      frame
Requirements: not recorded
Changed:      Frame card written
Evidence:     not recorded
Issues:       not recorded
Next:         Accept the framed scope and continue to specify?
Needs user:   yes
```

The block continues with the review fields and the journal path. The
following scope is illustrative: M3U-only, the new module and path rules
are proposals to confirm, rather than facts implied by the short request:

> Scope: M3U export only, no PLS; new module `src/export/m3u.py`; full
> path (new user-facing behavior). One requirement proposed:
> "Export playlist as M3U". Proceed?

You answer - trim it, extend it, or just "yes". This accepts scope; it does
not claim implementation. The settled question becomes a ruling, and the
continuation records the path:

```bash
python .agentic/aegis.py ruling TASK-8b12 --decision "M3U only, no PLS" --reason "user answer" --source user
python .agentic/aegis.py advance TASK-8b12 --path full --reason "scope accepted"
```

The agent then builds a behavior inventory and Frame-to-requirement coverage
table, writes the requirement file
(`aegis req functional "Export playlist as M3U"`), adds a short exact-format
spec, and records a proportionate design with requirement links and test
seams. Each stage ends with its own `pause`, summary and choices before the
next `advance`.

`advance` names the next step file to read, such as
`.agentic/steps/3_design.md` after specify. The quick path and correction
returns name their destination files too. The Log records each transition:

```
- 2026-08-02 frame: journal opened
- 2026-08-02 frame: completed; next specify - scope accepted
- 2026-08-02 specify: completed; next design
- 2026-08-02 design: completed; next build
```

The proposal stays in the task: `knowledge/export.md` keeps describing the
current code until validate reconciles it with the reviewed implementation.
With `[diagrams] enabled = true`, design would also draw the new writer as a
Mermaid structure diagram in `tasks/diagram_TASK-8b12.md` and show it at the
design checkpoint; this example runs with the default, so it draws none, and
`brief` says `Diagrams: none (disabled)`.

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
with a reproducible red record in the journal:

```bash
python .agentic/aegis.py log TASK-8b12 "red: pytest -q tests/export/test_m3u.py::test_roundtrip exit 1 - no module m3u (REQ-FUNC-3fa2)"
```

```
- 2026-08-02 build: red: pytest -q tests/export/test_m3u.py::test_roundtrip exit 1 - no module m3u (REQ-FUNC-3fa2)
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
transcript. After the increment is stable, the agent records one consolidated
green line that names the final focused command and the requirement it proves:

```bash
python .agentic/aegis.py log TASK-8b12 "green: test --impacted --base HEAD --no-fallback exit 0 (REQ-FUNC-3fa2)"
```

Update directly affected docstrings, usage examples, and setup instructions
with the implementation. Record material discoveries and design changes with
`log`. Component knowledge is reconciled during validate.

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
finding it accepts rather than corrects is spoken, not just logged. Then it
records the checkpoint:

```bash
python .agentic/aegis.py pause TASK-8b12 --next "Continue to validate?" --evidence "test --impacted --base HEAD --no-fallback exit 0"
```

It offers the choices: continue, change the implementation or tests, return to
design or specify, or stop. When you continue, it runs `advance`.

## Stage 5 - validate

The agent reviews the candidate and resolves implementation corrections, then
updates or creates affected component knowledge pages against the code and
tests. It migrates touched legacy pages. It also reconciles affected
requirements, project context, and environment guidance. The current documents
describe the built positive behavior and actual setup. History and proposals
remain in task records; an established contract is preserved when a defect
needs correction. A wrong assumption goes back instead of being patched around:
`advance TASK-8b12 --to <specify|design|build> --reason "<what>"` records the
return and waits for you.

If `[review] enabled = true`, the agent follows `.agentic/steps/review.md`: it
obtains both independent verdicts for the same candidate within the configured
round limit and records them with `verdict`. Reviewers read current files,
including untracked records, and the focused proof due at this phase. The
not-yet-run final strict check is not a reason to withhold a review verdict.
Then run final proof once
through the strict check with its eligible configured commands;
`check --task TASK-8b12 --dry-run` shows what it will run first. Naming the
task scopes the diff checks to it and reports a branch mismatch:

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
candidate change requires fresh proof. If validation changes a repository file
outside `.agentic/`, the agent reruns `evolution` first so the saved report
matches the final candidate.

The agent logs the result once and appends the closing report:

```bash
python .agentic/aegis.py log TASK-8b12 "final: check --task TASK-8b12 --strict --run exit 0; test ran; no warnings"
python .agentic/aegis.py report TASK-8b12
```

`report` records the journal state, linked requirements, diff size, check
counts, checklist completion and review policy; it is a snapshot, so the agent
reruns it if the candidate or checklist changes. Then comes the **closing
checkpoint**:

```bash
python .agentic/aegis.py pause TASK-8b12 --next "Close the task?" --evidence "check --task TASK-8b12 --strict --run exit 0"
```

The agent shows you the summary, the final proof, accepted warnings and the
changed files. Every deviation you heard along the way is presented again here,
in full - the notices were notifications, not approvals, so they never shorten
this stop. Your choices: close, return to build for corrections, revisit the
scope, or stop. When you close it:

```bash
python .agentic/aegis.py advance TASK-8b12
```

The journal reaches `stage: done`, and its State's `next` line reads
"implementation guidance complete; commit, push and integration belong to the
developer". In autopilot, a passing proof goes straight to that `advance`; a
failing one pauses the task as blocked instead.

## After done - the developer commits

AEGIS ends at `done`. Committing, pushing, opening a pull request and merging
follow your repository's procedures and your instructions; they are not AEGIS
steps. Commit the journal, with the report it now holds, together with the
work, so the task record travels with the branch. Never treat a frame
approval, review verdict or request to continue as authority to commit, push,
merge or publish. An edit after the proof needs fresh review and proof.

## What you can rely on afterwards

The task-owned records collectively retain the durable story: accepted scope,
rulings, one meaningful red and final green per behavior increment, repository
evolution, material findings, stage transitions, and the closing report. They
intentionally omit routine searches, edits, tool mechanics, and corrected
retries. Review those records with the diff. And if you stop
mid-task (any stage, any reason):

```bash
python .agentic/aegis.py status
```

finds the open task ID. Then run `brief TASK-8b12`, confirm the branch matches
its `Branch/base` line, read what its `Read next` line names - the current step
file, then the State `must_read` paths - and continue the first unticked
action. Transfer committed records with separately authorized Git operations;
uncommitted changes do not travel with a branch.

## Larger feature with two children and one review fix

Suppose a parent owns an export workflow while two non-overlapping branches
implement the encoder and UI. Each branch creates an ordinary child task:

```text
python .agentic/aegis.py task "Build export encoder" --parent TASK-a100
python .agentic/aegis.py task "Add export controls" --parent TASK-a100
```

Each child completes its own requirements, red/green loop, validation, and
closing checkpoint. Once both branches are visible in the parent checkout, the
parent validates the integrated candidate; child suites are not integration
proof. After integration, the parent re-checks current-state claims against
its own checkout.

With review enabled, round 1 may record specification compliance approved and
implementation quality changes required:

```bash
python .agentic/aegis.py verdict TASK-a100 --spec approved --quality changes_required --round 1
python .agentic/aegis.py advance TASK-a100 --to build --reason "<the quality finding>"
```

The return clears both verdicts and keeps the consumed round. The agent logs
the finding, fixes only that defect, reruns focused proof, returns to validate
with `advance`, and asks both review questions again in round 2. Only two
approvals for the unchanged integrated candidate let validate continue to the
final proof. The default two-fix policy still has a finite third and final
round; changes still required there pause the task as blocked for your decision.

## Using a host integration

Use the host's AEGIS entry point from [Agent_Plugins.md](Agent_Plugins.md).
It reads this same checkout's workflow; it does not create a separate process
for governance. Its `journal` operation writes the same `advance`, `pause`,
`log`, `ruling` and `verdict` records through the installed CLI. Long
verification runs use the shared `run`/`job` operations.
After a restart, inspect the existing job and its logs before launching another
suite. An exit-zero result is not final proof if its candidate fingerprint
changed during the run. Local cache records do not travel with the branch.

All IDs and test outputs above are illustrative. They are not verification
results for a shipped M3U implementation.
