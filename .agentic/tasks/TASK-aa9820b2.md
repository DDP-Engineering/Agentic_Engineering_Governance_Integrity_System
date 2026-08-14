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
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-aa9820b2 — Make impacted test selection runnable

stage: done
type: fix
path: full
requirements: REQ-PLAT-83b50d11, REQ-TEST-2bfb7a86, REQ-TEST-5d8f424b, REQ-TEST-db8d4d31, REQ-PLAT-2e23ac26, REQ-UX-e9952f0f, REQ-FUNC-dcb42072, REQ-TEST-07679fdc, REQ-PLAT-7365bed5, REQ-PLAT-19a2faa6, REQ-REL-bcd7400b, REQ-DATA-71fcf08e, REQ-FUNC-791ebe07
branch: master
base: 0f85d937d0d7c8766a6b51ff81e4abe2f4b05031
opened: 2026-08-14

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [x] journal and report included in the delivery commit
- [x] agreed outcome delivered, normally a PR
- [x] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Log

- 2026-08-14 frame: Scope is making `aegis test --impacted` runnable in AEGIS Light, by giving configured commands their own working directory, rebasing linked test references against it, degrading an oversized reference set instead of emitting an unlaunchable command, and allowing the diff basis to be narrowed for the inner loop.
- 2026-08-14 frame: Excluded are the check catalog, the stage model, the report's merge-base statistic, any hook or gate, the heavy AEGIS and WAEGIS products, and any upgrade of an already-deployed payload.
- 2026-08-14 frame: The full path is required because this adds a configuration key and a command-line option, both externally observable interfaces.
- 2026-08-14 frame: Stayed on `master` because all 38 existing journals in this repository record `branch: master`, so a task branch would break the house convention rather than follow it.
- 2026-08-14 frame: Field evidence from the AudioMancer deployment - 46 of 67 task journals report this command failing, 38 of them with exit 127 - established the defect; the owner approved the three-part fix before this task was opened, so the frame checkpoint is satisfied by that approval.
- 2026-08-14 frame: Expected requirements are one for the configured working directory, one for reference rebasing, one for oversized-set degradation, and one for the selectable diff basis.
- 2026-08-14 specify: The owner expanded scope mid-task to four further defects - the rejected category abbreviation, the stale command syntax in the design record, the untruthful check help, and the close-out commit per task - and all four ship in the same version.
- 2026-08-14 specify: Created REQ-PLAT-83b50d11, REQ-TEST-2bfb7a86, REQ-TEST-5d8f424b, REQ-TEST-db8d4d31, REQ-PLAT-2e23ac26, REQ-UX-e9952f0f and REQ-FUNC-dcb42072, all draft until build links their tests.
- 2026-08-14 specify: Widened REQ-TEST-07679fdc rather than adding a second fallback requirement, because a set too long to launch is the same visible full-suite fallback it already governs.
- 2026-08-14 specify: No requirement covers refreshing the command table in the design record, because a plan document states no product behavior; it is corrected as documentation and named at delivery.
- 2026-08-14 specify: No specification is needed because each behavior is a single configuration key, option, or fallback rule that its requirement states completely.
- 2026-08-14 specify: check reported no finding naming any artifact of this task; its five errors are pre-existing unknown-requirement identifiers in another task's journal, and its warnings are the repository's existing backlog.
- 2026-08-14 design: Chose one `[commands] workdir` key for every command over a per-command working directory (REQ-PLAT-83b50d11), because a repository has one application root in the case that failed, and per-command directories would need a table where a string now suffices.
- 2026-08-14 design: `workdir` joins `timeout` as a reserved key that names configuration rather than a command, so it must be excluded where commands are enumerated for execution and where a command is looked up by name (REQ-PLAT-83b50d11).
- 2026-08-14 design: Rejected storing test references relative to the working directory (REQ-TEST-2bfb7a86); references stay repository-relative so they remain comparable across configurations, and only substitution, which alone knows where the command runs, rebases them.
- 2026-08-14 design: Degradation is a ladder - exact selectors, then distinct test files, then the full suite - measured against a conservative command-length limit (REQ-TEST-5d8f424b, REQ-TEST-07679fdc), because the deployed repository's worst case is 1305 selectors at 166434 characters but only 115 files at 4441 characters.
- 2026-08-14 design: The limit is taken as 8000 characters rather than the 32767 the process creation call enforces, because commands run through a shell whose own line limit is the lower of the two (REQ-TEST-5d8f424b).
- 2026-08-14 design: `--base <revision>` overrides only the diff basis and leaves the coverage and safety rules untouched (REQ-TEST-db8d4d31), so an unknown revision falls back visibly like any other unusable basis.
- 2026-08-14 design: Category abbreviations are added as further keys in the existing alias table and the error message lists canonical folders only, so the fix is data rather than logic (REQ-PLAT-2e23ac26).
- 2026-08-14 design: Test seams are the impacted selection function, the command runner's working directory, the command enumeration, the requirement scaffolder, the parser help, and the delivery step file's prose.
- 2026-08-14 design: Files to touch are the AEGIS Light CLI, its build/deliver step files, its README, the CLI reference, the payload's default configuration comment, the design record's CLI document, and the product test suite.

## Design

- Interface (REQ-PLAT-83b50d11, REQ-TEST-db8d4d31): one new configuration key
  `[commands] workdir`, and one new option `test --impacted --base <revision>`.
  Nothing existing changes shape, so a repository that sets neither behaves
  exactly as it does today.
- Data (REQ-TEST-2bfb7a86): `linked_tests` stay repository-relative on disk.
  Rebasing happens only while building the command; a reference that does not
  lie under `workdir` is treated as unusable and takes the documented fallback
  rather than being silently passed through.
- Degradation ladder (REQ-TEST-5d8f424b, REQ-TEST-07679fdc): substitute exact
  selectors; if the resulting command exceeds the length limit, substitute each
  distinct test file once; if it still exceeds it, run the full configured test
  command and say why. Each step prints its reason.
- Alternative rejected (REQ-TEST-5d8f424b): capping the set at a fixed number of
  selectors was rejected because reference length varies by an order of
  magnitude between repositories, so a count cannot predict whether the command
  will launch; the command's own length can.
- Alternative rejected (REQ-FUNC-dcb42072): dropping the close-out commit
  entirely was rejected, because when delivery pushes or opens a pull request the
  outcome can still fail after the commit, and only a later commit can record
  truthfully that it did not.
- Test seams: `impacted_tests` and `cmd_test` for selection and substitution,
  `run_command` for the working directory, `runnable_commands` for the reserved
  key, `cmd_req` for categories, the argument parser for help text, and reading
  `6_deliver.md` for the close-out rule.

### Design - second scope (timeouts and the task base)

- Interface (REQ-PLAT-7365bed5, REQ-PLAT-19a2faa6): `[commands] timeout` keeps
  its name but changes meaning - absent or zero now means no limit, and a
  positive value still limits. Per-command limits live in a new top-level
  `[timeouts]` table keyed by command name, falling back to the shared value.
- Alternative rejected (REQ-PLAT-19a2faa6): naming per-command limits inside
  `[commands]`, as `timeout_test`, was rejected because that table's keys are
  command names, so every new form of it has to become another reserved word
  and a repository could no longer name a command freely.
- Behavior change acknowledged (REQ-PLAT-7365bed5): a repository that relied on
  the shipped 1800-second limit to stop a runaway command loses that stop. That
  is the intended direction - the tool must not manufacture a failure - and the
  repository can restore any limit it actually wants in one line.
- Data (REQ-REL-bcd7400b): a stopped command becomes its own finding name
  rather than sharing `command-failed`, so a report can never read as though a
  suite was executed and judged when it was cut off. It stays an error, because
  a proof that did not finish is not a proof.
- Data (REQ-DATA-71fcf08e): the journal header gains `base: <commit>`, written
  once at creation. The header parser already accepts any `key: value` line, so
  this needs no parsing change and older journals stay valid.
- Alternative rejected (REQ-DATA-71fcf08e): deriving the task base from the
  `opened:` date, or from the first commit that touched the journal file, was
  rejected because both are guesses that break as soon as history is rebased,
  while the commit itself is exact and costs one line.
- Interface (REQ-FUNC-791ebe07): `report` and `check --task` pass that recorded
  commit into the diff machinery this task already made revision-aware, and the
  report labels which basis it used, so a reader can tell the two apart.
- Test seams: `command_timeout` for the shared default, a new per-command
  lookup, `execute_commands` for the stopped-command finding, `cmd_task` for
  writing the base, and `cmd_report` plus the task-scoped check path for
  consuming it.

- 2026-08-14 build red: command=`python -m pytest -q tests/test_run_report.py -k "workdir or collapses or too_long or base_option" tests/test_cli_core.py -k "... or abbreviations"`; exit=1; expected missing behavior=11 failed - no `[commands] workdir` is honored, references are not rebased, `COMMAND_LENGTH_LIMIT` does not exist, `--base` is not a known option, and `req rel` is rejected as an unknown category.
- 2026-08-14 build red: command=`python -m pytest -q tests/test_structure.py::test_deliver_folds_close_out_into_a_local_only_delivery tests/test_structure.py::test_check_help_makes_no_unconditional_zero_exit_promise`; exit=1; expected missing behavior=2 failed - the delivery step still requires a close-out commit unconditionally, and the source still contains the phrase "always exits 0".
- 2026-08-14 build: Implemented `[commands] workdir` with `command_workdir`, a `cwd` argument on `run_command` used by both the runner and `check --run`, `RESERVED_COMMAND_KEYS` so the key is never executed, and an advisory `config` finding when it does not resolve.
- 2026-08-14 build: Implemented `rebase_ref` and the `COMMAND_LENGTH_LIMIT` ladder in `fit_impacted` - exact selectors, then distinct test files, then the caller's full-suite fallback - and split `diff_base` out of `collect_diff` so `--base` can select a revision.
- 2026-08-14 build: Two of my own new tests were themselves wrong and were corrected rather than the product - one asserted a phrase the step file wraps across lines, and one hard-coded a length limit that depends on the interpreter path, so it now computes the limit from the same template.
- 2026-08-14 build: Version raised to 0.4.0, which turned the release-builder expectations red until they were updated to the new version and archive prefix.
- 2026-08-14 build: Full product suite green - 186 passed, 1 skipped in 68.39s - and `python -m py_compile template/.agentic/aegis.py` exited 0.
- 2026-08-14 build: Manual observation for the reported field failure - built a throwaway repository shaped like the one that failed (application under `app/`, real pytest, `workdir = "app"`), and `test --impacted` ran `python -m pytest -q tests/test_calc.py::test_add tests/test_calc.py::test_add_negative` from `app/` and exited 0 where the old shape exited 127.
- 2026-08-14 build: Manual observation for the basis - on a branch the merge-base run selected 2 references, `--base HEAD` on the same clean tree fell back to the full suite, an uncommitted edit brought it back to 2 references, and `--base nope` printed `unknown base revision 'nope' - running the full test command`.
- 2026-08-14 build: Manual observation for the reserved key - `check --run` reported only `run: test ok` with no attempt to execute `workdir`.
- 2026-08-14 build: Payload and user documentation reconciled - `CLI.md`, `AGENTS.md`, `4_build.md`, `6_deliver.md`, the default configuration comment, the product README, the user guides, and the design record's CLI document.
- 2026-08-14 validate: Updated the AEGIS Light component knowledge page, which still described version 0.3.0 and the `task new` and `req new` spellings that the previous version had already removed.
- 2026-08-14 validate: Reviewed the diff hunk by hunk - 17 files, 617 insertions, 74 deletions - and found no change outside the agreed scope; the only behavior a repository sees without opting in is the corrected help text, since `workdir` and `--base` both default to today's behavior.
- 2026-08-14 validate: Portability reviewed - the working directory is passed to the existing subprocess call rather than by changing the process directory, rebasing uses pure `PurePosixPath` arithmetic with forward slashes, and the length limit is a plain character count, so Windows and Linux behave identically.
- 2026-08-14 validate: Security reviewed - the existing shell-metacharacter and repository-escape rules still run before any rebasing, and a reference that leaves the working directory is refused rather than passed through, so no new string can reach the shell.
- 2026-08-14 validate: This checkout is shared with another agent whose uncommitted work touches `05_Software/aegis/`, `05_Software/waegis/`, five `00_Planning/AEGIS_*.md` documents, `00_Planning/templates/05-check.md`, and `02_Tools/build_aegis_release.py`; none of it belongs to this task and none of it was modified here.
- 2026-08-14 validate: `CHANGELOG.md` is a shared file that already carried that agent's unstaged entries before this task began, so committing the whole file would publish their unfinished work; the delivery must stage a path list rather than everything.
- 2026-08-14 validate: Accepted `uncovered-source` for `AGENTS.md` and `steps/4_build.md` under `--task`, because that lens deliberately measures coverage against this task's own requirements and both files are owned by existing requirements repository-wide.
- 2026-08-14 validate: Accepted `uncovered-source` for `CLI.md` as pre-existing debt - no requirement anywhere in this repository lists it, and the structural test asserting the CLI reference is unlinked too - and raised it as a separate task rather than widening this one.
- 2026-08-14 validate: Accepted `outside-layout` for the product README and the five user-guide documents, because documentation for this change necessarily lives outside the source and test globs.
- 2026-08-14 validate: Accepted the plain `check` run's `stage-zone` findings, which attribute this diff to the unrelated open adoption journal at stage `close`; the task-scoped run shows none, because `validate` has no write zone.
- 2026-08-14 validate: The five strict errors are pre-existing unknown requirement identifiers in TASK-44bbb4ad's journal header, owned by another task; they fail `--strict` on this branch today and would fail CI regardless of this change.
- 2026-08-14 validate: Returned to `specify` because the owner added two further defects rather than because validation found a flaw - the shipped command timeout and the delivery report's diff basis - and new behavior needs requirements before implementation, not a patch at proof time.
- 2026-08-14 validate: Stopped the in-flight `check --strict --run` before editing, because its last chained command runs the AEGIS Light suite against the very payload files this task is about to change, and a proof read mid-edit would describe no real tree; its partial reading of 6 errors and 106 warnings is discarded rather than reported.
- 2026-08-14 specify: Scope now also covers an unlimited shipped timeout, per-command timeout overrides, a truthful outcome for a command stopped by a timeout, and a recorded task base commit that the delivery report and task-scoped checks diff against.
- 2026-08-14 specify: The owner restricted this task to AEGIS Light, so the identical defects in the independent AEGIS and WAEGIS products, and TASK-44bbb4ad's invalid requirement identifiers, stay untouched and out of scope.
- 2026-08-14 specify: The unlimited default and the per-command override are not new policy - the independent heavy product already ratified both in REQ-PLAT-cff1cf5e and REQ-PLAT-a4fcb436, so this aligns AEGIS Light with a decision the owner already made elsewhere.
- 2026-08-14 specify: Created REQ-PLAT-7365bed5, REQ-PLAT-19a2faa6, REQ-REL-bcd7400b, REQ-DATA-71fcf08e and REQ-FUNC-791ebe07.
- 2026-08-14 specify: `req plat` and `req rel` were rejected while creating them, because this repository still runs the 0.3.0 payload - a live demonstration of the abbreviation defect this task fixes, and a reminder that the fix reaches a repository only when the payload is upgraded there.
- 2026-08-14 build red: command=`python -m pytest -q tests/test_run_report.py tests/test_cli_core.py -k "no_time_limit or per_command_limit or stopped_command or recorded_task_base or records_the_commit or records_no_commit"`; exit=1; expected missing behavior=6 failed - the shipped default is still a 1800-second limit rather than none, `[timeouts]` is not read, a stopped command is still reported as `command-failed`, `git_head` does not exist, and the report still measures against the merge base.
- 2026-08-14 build: `command_timeout` now takes a command name, reads `[timeouts]` before `[commands] timeout`, and returns None for absent, zero, negative and unreadable values, so a limit exists only where one was asked for.
- 2026-08-14 build: `run_command` returns a fourth value saying the limit ended the command, because exit 124 alone cannot distinguish that from a command choosing to exit 124, and a caller reporting whether anything was proven must not guess.
- 2026-08-14 build: `git_head` was added and `cmd_task` writes `base:` into the journal from it, with the template carrying the key so the header keeps its shape and an empty value leaves no trailing space.
- 2026-08-14 build: `check_diff` and `cmd_report` now take the diff basis from that header, and the report names which basis it used so the two forms cannot be confused.
- 2026-08-14 build: `command-timeout` and the previously undeclared `command-failed` were added to the catalog, which is now nineteen; the help text derives its own count so the number it announces can no longer disagree with the list it prints.
- 2026-08-14 build: Twenty monkeypatched `collect_diff` stubs in the suite were widened to accept the revision argument, and three existing tests were rewritten because this task deliberately changes what they asserted - the 1800-second default, the seventeen-check count, and a stopped command reported as a failure.
- 2026-08-14 build: Two of my own new tests were wrong again and were corrected rather than the product - one expected the report to exclude the task journal from its own diff, and one used the test suite's `git` helper as though it returned output.
- 2026-08-14 build: Full product suite green - 192 passed, 1 skipped in 80.92s - and `python -m py_compile template/.agentic/aegis.py` exited 0.
- 2026-08-14 build: Manual observation for the recorded base - in a throwaway repository on a branch carrying one earlier unrelated commit, `task` wrote `base:` equal to `git rev-parse HEAD`, and `report` then measured 2 files changed against `diff vs task base 702b746` where the same journal without the header measured 3 against `diff vs merge base`, the extra file being the earlier commit's.
- 2026-08-14 build: Manual observation for the limits - with `[timeouts] slow = 2` the run printed `run: slow stopped at its 2s limit (2.3s) - nothing proven` and one `command-timeout` error, while `quick` ran unlimited and passed; with that entry removed the same command was still running after 12 seconds and was ended by an external kill, confirming AEGIS applied no limit of its own.
- 2026-08-14 validate: Backfilled this journal's own `base:` with the commit it started from, which git confirms is still HEAD because nothing has been committed during the task; the value is inert in this repository until its payload is upgraded, since the installed 0.3.0 ignores the key.
- 2026-08-14 validate: Reviewed the second scope's diff against the first - the timeout change is the only one that alters behavior for a repository that configures nothing, and it removes a limit rather than adding one, so no command can newly be stopped.
- 2026-08-14 validate: Portability reviewed - the limit is passed to the existing wait call as None rather than a number, which is the documented way to wait without a deadline on both platforms, and the recorded base is a plain commit id with no path handling.
- 2026-08-14 validate: The final proof is the product's own suite - 192 passed, 1 skipped in 92.57s - plus `py_compile` and a version smoke reporting 0.4.0, all after the last edit.
- 2026-08-14 validate: The repository-wide `check --strict --run` was deliberately not used as the proof, because its configured command chains the independent AEGIS and WAEGIS suites, which this task is scoped out of and which carry another agent's uncommitted work; an earlier attempt was stopped for that reason and its partial reading is not reported.
- 2026-08-14 validate: `check --task TASK-aa9820b2 --strict` exits 1 solely on the five pre-existing unknown requirement identifiers in TASK-44bbb4ad's journal, which this task must not edit; its 106 warnings are the repository's existing backlog plus the documentation-layout findings already accepted above.
- 2026-08-14 validate: Effect on CI stated honestly - a strict gate on this branch fails today because of those five identifiers, and this change neither causes nor repairs that.
- 2026-08-14 deliver: The owner approved delivery as a repository-local commit of the AEGIS Light files only, with `CHANGELOG.md` deliberately left out because 77 of its 124 added lines are another agent's unfinished entries that this task must not publish; no push and no pull request were authorized.
- 2026-08-14 deliver: The owner confirmed there was no third item behind the empty bullet in the request, so scope closes here.
- 2026-08-14 deliver: Read the appended report; its `78 file(s) changed, 2867 line(s) added` counts the other agent's uncommitted work as well, because the installed 0.3.0 payload measures from the merge base and ignores the `base:` header this task adds - the defect itself, demonstrated on its own delivery, and it will read correctly here only once this payload is installed.
- 2026-08-14 deliver: The committed scope is 32 AEGIS Light files - the payload, its tests, its product and user documentation, the design record, this journal, and twelve requirement files - with `CHANGELOG.md` and every file of the independent AEGIS and WAEGIS products deliberately left in the working tree.
- 2026-08-14 close-out: Delivered as one repository-local commit with no push and no pull request, so nothing could fail after it and the close-out is carried by that same commit under the rule this task introduced; no remote was contacted.

## Delivery report (2026-08-14)

- stage: deliver; type: fix; path: full; branch: master
- requirements:
  - REQ-PLAT-83b50d11 - Run configured commands in a configured working directory
  - REQ-TEST-2bfb7a86 - Rebase impacted test references to the command working directory
  - REQ-TEST-5d8f424b - Reduce an oversized impacted set to its test files
  - REQ-TEST-db8d4d31 - Select the impacted diff basis
  - REQ-PLAT-2e23ac26 - Accept requirement category abbreviations
  - REQ-UX-e9952f0f - State check exit behavior truthfully in help
  - REQ-FUNC-dcb42072 - Fold close-out into delivery when publication cannot fail
  - REQ-TEST-07679fdc - Focused regression with safe fallback
  - REQ-PLAT-7365bed5 - Impose no automatic command time limit
  - REQ-PLAT-19a2faa6 - Override the time limit per configured command
  - REQ-REL-bcd7400b - Report a command stopped by its time limit as unproven
  - REQ-DATA-71fcf08e - Record the commit a task started from
  - REQ-FUNC-791ebe07 - Diff task reporting against the recorded task base
- diff vs merge base: 78 file(s) changed, 2867 line(s) added
- checks: errors=5 warnings=107 notes=0
- checklist: 1/6 done; open: validation evidence, diff, exclusions, and outcome presented; delivery confirmed by the human; journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the
