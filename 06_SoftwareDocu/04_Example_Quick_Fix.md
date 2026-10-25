<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example - a quick fix, autopilot

The quick path is `frame -> build -> validate -> done`. It omits specify
and design only when the fix meets the installed frame step's eligibility
rules. Autopilot skips intermediate stage-choice checkpoints; it preserves
deviation notices and review policy, and a decision-blocking question still
stops it with `pause --blocked`.

## You say

```text
Using AEGIS, autopilot through validate: fix "Usgae" in the existing CLI help
heading in src/cli/help.py. Restore the "Usage" heading required by
REQ-UX-3fa2c1d4. Do not change options, interfaces or help behavior.
```

This example restores an existing requirement. It changes no public interface,
data format, dependency, security behavior or data handling. A crash involving
playlist parsing or export data is not an automatic quick-path candidate.

## Frame: establish eligibility

Open a journal with `--type fix`, record the existing requirement on the
header's `requirements:` line and explain why the bounded correction qualifies,
with the path criteria table in `Path and reason`. If investigation finds a
broader behavior change, take the full path instead and record the scope
change. A task's title or expected line count does not decide its path. With
no blocking question, autopilot records the path and moves on without a stop:

```sh
python .agentic/aegis.py advance TASK-c3d1a2b4 --path quick --reason "restores REQ-UX-3fa2c1d4; no new behavior"
```

## Build: reproduce, link, anchor, fix

Write a regression that asserts the actual help heading. Record the exact red
command, nonzero exit and expected failure ("Usgae" instead of "Usage") with
`log TASK-c3d1a2b4 "red: <command> exit 1 - <expected failure> (REQ-UX-3fa2c1d4)"`.
An environment or fixture failure is not evidence that the behavior is missing.
Update the requirement's paths and linked tests before impacted selection:

```toml
affected_paths = ["src/cli/help.py"]
linked_tests = ["tests/cli/test_help.py::test_heading"]
```

Then capture the red-test state before changing implementation:

```sh
python .agentic/aegis.py anchor --task TASK-c3d1a2b4
```

Prepare the project's documented test environment. The commands below assume
its impacted runner honors the linked references. Preview selection with
`test --impacted --base HEAD --dry-run` if needed. If `--no-fallback` refuses
selection, use a native focused command; it did not run tests or record proof.

Correct the heading, run focused proof and inspect the repository changes:

```sh
python .agentic/aegis.py test --impacted --base HEAD --no-fallback
python .agentic/aegis.py evolution --task TASK-c3d1a2b4
```

Run edit-test retries without `--task`. Once the correction is stable, log one
consolidated green line for the focused regression, then finish the stage with
`advance TASK-c3d1a2b4 --evidence "<focused command> exit 0"`. The requirement
remains the durable contract; the journal explains this repair.
The IDs, paths and commands are a worked example, not recorded test results.

## Validate: review the final candidate

Review the change and its tests against the existing contract. Reconcile affected
project/environment context and component descriptions with the candidate,
leaving unchanged sections untouched. Current prose states actual behavior;
the journal carries repair history. Refresh evolution after any
later candidate edit. If explicit review is enabled, follow
`.agentic/steps/review.md`: obtain both independent verdicts against current
files and focused proof before the final full run; the review policy below
defines the bounded rounds. Run final configured proof once:

```sh
python .agentic/aegis.py check --task TASK-c3d1a2b4 --strict --run
```

This executes the eligible configured commands, including the full suite when
configured for it. Do not start an identical suite separately just before this
command. With a host integration, use tracked verification and inspect the
existing job after an interruption before retrying.

An accepted finding or omitted verification is both logged and spoken as a
`DEVIATION validate: <what> - <reason and limitation>` notice. Do not describe
checks as clean while accepting an unresolved finding.

## Review policy

With `[review] enabled = false` (the default), semantic review and focused and
full verification still apply. When enabled, each round requires independent
specification-compliance and implementation-quality verdicts for the same
candidate, recorded with `verdict`. `max_fix_cycles = 0` allows one round and
no autonomous fix/re-review cycle. The default of 2 permits at most three
rounds. Changes still required on the final round pause the task as blocked
for a human decision.

## Close: report, then done

Log the final result once, run `report TASK-c3d1a2b4` and read what it
appends. When the proof passed, autopilot closes the task:

```sh
python .agentic/aegis.py advance TASK-c3d1a2b4 --evidence "check --task TASK-c3d1a2b4 --strict --run exit 0"
```

A failed proof instead records
`pause TASK-c3d1a2b4 --blocked --next "<the failure to resolve>"` and stops.
The agent then presents the summary, the candidate, the validation evidence
and every deviation. Committing and opening
a pull request follow the repository's procedures and your instructions; they
are not AEGIS steps, and autopilot does not grant them.

The result is a proportionate record of the repair: the requirement, red/green
proof, anchor/evolution and the closing report. The quick path promises no fixed
completion time. Documentation-only maintenance is outside this repository's
AEGIS workflow and does not need a quick-fix journal.
