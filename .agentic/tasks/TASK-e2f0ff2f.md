<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-e2f0ff2f — Deviation notices surface anomalies in the conversation when they occur

stage: done
type: change
path: full
requirements: REQ-UX-ccb4ca06
branch: master
base: 45958c2b43b94e8c63beeff73e4c1ea994889506
opened: 2026-08-18

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
      (outcome is a staged working tree; the operator makes the commit)
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Design

The change is prose in the payload and nothing else. `aegis.py` gains no
command, no flag and no config key, so the notice carries no enforcement -
which is the point: it is guidance the agent follows, in the same way the red
record and the anchor are guidance it follows (REQ-UX-ccb4ca06).

**Where the concept lives.** `AGENTS.md` `## Interaction modes` today holds
two ideas, checkpoint and autopilot, and both are about *stopping*. The
deviation notice is a third idea that is deliberately not a stop, so it
belongs beside them rather than inside either. It states the trigger set, the
one-line shape, and the rule that a notice never pauses the work and is never
suppressed by autopilot - the same "both modes" treatment the deliver stop
already has.

**Where the instruction attaches.** Three step files already tell the agent to
record an anomaly; each gains a clause telling it to say the same thing:
`4_build.md` step 10 where an accepted `check` warning is logged,
`5_validate.md` step 5 where a manual method stands in for a test and step 9
where a non-zero exit or an unrun command is recorded, and `6_deliver.md`
step 3, which gains the opposite guarantee - notices supplement the delivery
presentation and never replace it, so a human who missed a notice mid-flight
still meets it in the aggregate.

**Interface change.** One user-visible string shape,
`DEVIATION <stage>: <what> - <why accepted, or what it costs>`. `DEVIATION`
was chosen over `WARNING` because `check` already prints `WARN` and `NOTE`
severity labels, and an agent-authored `WARNING` line would be
indistinguishable from a tool finding at a glance - worst exactly where the
trigger is "an accepted check warning".

**Data decisions.** None. No file format changes, nothing is written to disk
by the notice, and the journal log lines that already record these anomalies
keep their existing shape. The notice is the conversational twin of a journal
line, not a replacement for it.

**Rejected alternative - make deviations stop the work.** A stop would
guarantee the human sees each one, but six trigger classes across four stages
would turn a two-checkpoint workflow into a per-stage approval treadmill,
which is the exact outcome `## Interaction modes` exists to prevent. Notify
and continue keeps the flow and still removes the silence.

**Also rejected - a `Done checklist` item per stage.** A conversational act
leaves no artifact, so ticking it proves nothing and invites the box-checking
the workflow avoids elsewhere. The checklists are left untouched.

**Test seam (REQ-UX-ccb4ca06).**
`05_Software/aegis/tests/test_structure.py`, following the existing
payload-prose pattern of `test_red_evidence_is_precise_prose`: read
`PAYLOAD / "AGENTS.md"` and the three step files and assert the required
phrases are present. `PAYLOAD` resolves to
`05_Software/aegis/template/.agentic`, so the test binds the canonical payload;
the dogfood copy under `.agentic/` is updated identically by hand because no
test enforces that the two stay in sync.

**Files expected to change.** The four payload files under
`05_Software/aegis/template/.agentic/` and their four counterparts under
`.agentic/`; `test_structure.py`; `VERSION` in both copies of `aegis.py` for
the 0.6.0 bump; `CHANGELOG.md`; this journal and the requirement.

## Log

- 2026-08-18 frame: scope is a payload prose change that adds a third
  interaction concept - a **deviation notice** the agent states in the
  conversation at the moment it logs an anomaly, rather than only writing it
  to the journal for the deliver checkpoint to reveal.
- 2026-08-18 frame: the notice is a notification, not a stop - it is stated
  and the work continues - and it applies in both checkpoint and autopilot
  mode, because autopilot is where unreported anomalies cost the most.
- 2026-08-18 frame: agreed format is `DEVIATION <stage>: <what> - <why
  accepted, or what it costs>`; the operator chose `DEVIATION` over
  `ANOMALY` and over `WARNING`, the latter rejected because `check` already
  emits `WARN`/`NOTE` labels and the collision would blur tool findings with
  agent judgement.
- 2026-08-18 frame: agreed trigger set is six - an accepted `check` warning,
  a non-zero exit or a skipped/unrun verification command, an `anchor` or
  `evolution` report that does not match expectation, a `Manual:`/
  `Inspection:` method standing in for an automatable test, a requirement
  retired, and diff review finding unrequested work.
- 2026-08-18 frame: in scope are `AGENTS.md` and the step files `4_build.md`,
  `5_validate.md` and `6_deliver.md`, in both the canonical payload at
  `05_Software/aegis/template/.agentic/` and the byte-identical dogfood copy
  at `.agentic/`; plus a new requirement, a new assertion in
  `05_Software/aegis/tests/test_structure.py`, the `VERSION` bump and
  `CHANGELOG.md`.
- 2026-08-18 frame: out of scope is any change to `aegis.py` behavior - the
  notice is guidance only, there is no new command, no config key and no
  enforcement, consistent with the advisory philosophy; also out of scope are
  the `Done checklist` lists, deliberately left alone because a conversational
  act cannot be honestly ticked as an artifact.
- 2026-08-18 frame: full path, because this adds externally observable agent
  behavior that no existing requirement covers.
- 2026-08-18 frame: stayed on `master` rather than opening a task branch, and
  this is a deviation from step 4 of `1_frame.md` - the operator instructed
  that nothing be committed or pushed, so the candidate stays uncommitted in
  the working tree and a branch would carry no commits and record a
  misleading `branch:` header.
- 2026-08-18 frame: version will be 0.6.0, chosen by the operator, because
  the contract every agent follows changes even though no code does.
- 2026-08-18 frame: expected one new requirement - the agent states a
  deviation in the conversation when it records one, in both interaction
  modes.
- 2026-08-18 frame: operator confirmed the scope, the `DEVIATION` name, the
  six triggers and the 0.6.0 version across the framing exchange, so the
  checkpoint stop is satisfied without a further pause.
- 2026-08-18 specify: created REQ-UX-ccb4ca06 as one behavior - the workflow
  instructs the agent to state each recorded deviation in the conversation,
  in both interaction modes, as one line naming stage, departure and cost.
- 2026-08-18 specify: no spec written - the requirement names the format and
  the trigger points completely, so there is nothing left that a spec would
  answer.
- 2026-08-18 specify: `check` errors=0 warnings=0 notes=3; all three notes are
  pre-existing manual-verification notices on unrelated requirements.
- 2026-08-18 build red: command=`python -m pytest -q
  test_structure.py::test_deviation_notices_are_stated_when_recorded_not_only_at_delivery`
  from `05_Software/aegis/tests`; exit=1; expected missing behavior=
  `AssertionError: assert 'Deviation notices' in ...` - the payload AGENTS.md
  carries no deviation-notice section at all.
- 2026-08-18 design: recorded the placement beside the two interaction modes,
  the three step-file attachment points, the `DEVIATION`-over-`WARNING` naming
  reason, and the two rejected alternatives - stopping on each deviation, and
  adding a checklist item per stage.
- 2026-08-18 build: anchor recorded after the red and before the first
  implementation edit - 72 files at 45958c2, 2026-08-18T08:29:30Z.
- 2026-08-18 build: added the `## Interaction modes` deviation-notice block to
  the canonical payload `AGENTS.md`, and the attaching clauses to `4_build.md`
  step 10, `5_validate.md` steps 5 and 9, and `6_deliver.md` step 3.
- 2026-08-18 build: bumped `VERSION` to 0.6.0 in the canonical payload
  `aegis.py`, then mirrored all five changed payload files into the dogfood
  `.agentic/` copy; all eight payload files verified byte-identical again.
- 2026-08-18 build: the first green run still failed on
  `notices supplement this presentation` because the phrase wraps across a
  line in `6_deliver.md`; the test was wrong about wrapping, not about
  behavior, so it now normalizes whitespace with `" ".join(text.split())`,
  the pattern `test_deliver_folds_close_out_into_a_local_only_delivery`
  already uses. The asserted phrases are unchanged.
- 2026-08-18 build: `evolution --task TASK-e2f0ff2f` reports 7 modified files,
  0 added, 0 removed, matching the design note; it does not and cannot list
  the four mirrored files under `.agentic/`, because anchor and evolution
  exclude AEGIS's own state by design, so the report undercounts this
  candidate by four files that `git diff` does show.
- 2026-08-18 build: full suite `python -m pytest -q 05_Software/aegis/tests` -
  202 passed, 2 skipped, exit 0; the 0.6.0 bump broke no version assertion.
- 2026-08-18 build: REQ-UX-ccb4ca06 set to `active` with its linked test
  recorded; `affected_paths` name the four canonical payload files only, since
  the dogfood copy is an install of that payload rather than a second source.
- 2026-08-18 validate: diff reviewed hunk by hunk against the frame scope -
  12 modified files, 4 untracked task artifacts; the five payload edits are
  additive prose, the test is additive, and nothing touches error paths,
  portability, secrets or security surface.
- 2026-08-18 validate: updated `.agentic/knowledge/reusable-workflow-payload.md`
  with REQ-UX-ccb4ca06, the one component whose behavior this task changed.
- 2026-08-18 validate: defect found and fixed - `linked_tests` recorded the
  selector as `tests/test_structure.py::...`, which `check` flagged
  `no-linked-tests` because the path must be repository-root relative; it now
  reads `05_Software/aegis/tests/test_structure.py::...` and the warning is
  gone.
- 2026-08-18 validate: `check --task TASK-e2f0ff2f --strict --run` - exit 1,
  errors=1 warnings=2 notes=3, strict exit 1. This is **not** green and is not
  recorded as green.
- 2026-08-18 validate: the one error is `command-failed (run) - lint exit 1`,
  and it is pre-existing, not introduced here. Measured directly: `ruff check
  05_Software/aegis` reports 35 errors on the current tree and, with this
  task's changes stashed, 35 errors on the untouched base - the same count, so
  this task adds none. 23 of the 35 are in the payload `aegis.py`, which this
  task changes by one character. The task's own test file carries two, both
  `I001` import-order findings that predate it.
- 2026-08-18 validate: effect on CI stated honestly - any pipeline running
  `check --run` or `--strict` on this repository already fails on lint today
  and will keep failing after this task; this task neither fixes nor worsens
  that, and cleaning up ruff belongs to its own task.
- 2026-08-18 validate: `run: test ok (98.0s)` - the full suite passed inside
  the same proof, 202 passed and 2 skipped when run directly.
- 2026-08-18 validate: two warnings accepted. `uncovered-source` on the payload
  `aegis.py` is the `VERSION = "0.6.0"` bump, which is release bookkeeping
  rather than a behavior, so no requirement claims the file. `outside-layout`
  on `CHANGELOG.md` is structural - the changelog cannot sit inside a source or
  test glob.
- 2026-08-18 deliver: the operator instructed that nothing be committed or
  pushed, so the outcome is the validated candidate left uncommitted in the
  working tree; no commit, no PR, no release tag, and `report` is therefore not
  run, because it appends a delivery record for an approved delivery that has
  not happened.
- 2026-08-18 deliver: the 0.6.0 version is carried in `CHANGELOG.md` and in
  both copies of `aegis.py`.
- 2026-08-18 deliver: operator asked for a delivery archive, so
  `python 02_Tools/build_aegis_release.py --version 0.6.0` was run - payload
  verified at 15 files, the complete product suite passed inside the build at
  202 passed and 2 skipped, and it wrote `aegis-0.6.0.zip` (101,009 bytes) and
  `aegis-0.6.0.tar.gz` (80,119 bytes) to the untracked `07_Delivery/dist/`,
  with the tracked publication record `RELEASE.md`, `SHA256SUMS` and
  `release-manifest.json` under `07_Delivery/aegis-0.6.0/`.
- 2026-08-18 deliver: updated
  `.agentic/knowledge/release-builder-and-delivery-records.md`, whose Files
  list still named `07_Delivery/aegis-0.5.0/` as the current publication
  record.
- 2026-08-18 deliver: operator confirmed delivery and asked for the task to be
  closed, the files staged, and the commit left for them to make; nothing is
  committed or pushed by this session.
- 2026-08-18 deliver: the report's `checks: errors=0 warnings=6 notes=3` is a
  report-time snapshot without `--run`, so it does not contradict the
  validation proof - `check --strict --run` exited 1 on the pre-existing lint
  failure, and that remains the honest closing evidence.
- 2026-08-18 deliver: the report counts 21 files against base 45958c2 because
  it includes the four task artifacts and the three publication-record files
  written after validation; the archives under `07_Delivery/dist/` are
  untracked and are not part of the commit.
- 2026-08-18 deliver: closed at `stage: done` with the whole candidate staged
  and no commit made, so the final checklist item is carried by the operator's
  commit rather than by a close-out of this session's own.
- 2026-08-18 post-delivery note, outside this task and outside the workflow at
  the operator's instruction: the pre-existing lint failure recorded above was
  afterwards fixed, and `check --strict --run` now exits 0 with lint ok. The
  validate entries stand as written - they were true when written - but a
  reader should not conclude from them that the repository is still red.
- 2026-08-18 deliver: deviation notices were given in the conversation for the
  pre-existing lint failure, the two accepted warnings, the wrong
  `linked_tests` path found at validate, the `.agentic/` blind spot in the
  evolution report, and the task branch not opened - exercising the very rule
  this task adds, on the task that adds it.
- 2026-08-18 validate: evolution was not refreshed after the validate edits,
  and does not need to be - every file validation touched (the requirement, the
  knowledge page, this journal) lives under `.agentic/`, which anchor and
  evolution exclude by design; the 7-file report still describes the candidate
  outside `.agentic/`.

## Delivery report (2026-08-18)

- stage: deliver; type: change; path: full; branch: master
- requirements:
  - REQ-UX-ccb4ca06 - The agent shall state a deviation in the conversation when it records one
- diff vs task base 45958c2: 21 file(s) changed, 1039 line(s) added
- checks: errors=0 warnings=6 notes=3
- checklist: 2/6 done; open: delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the
