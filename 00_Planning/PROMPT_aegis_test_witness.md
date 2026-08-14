<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Implementation plan — repository anchor and evolution tracking

## Purpose

AEGIS records repository evolution around implementation without preventing
work. After the expected red test, `anchor` fingerprints the repository.
After implementation, `evolution` reports what was added, modified, or removed.
The records are descriptive and can be replaced by the operator; they are not
tamper-proof evidence and do not prove that the red test was genuine.

## Commands

```text
python .agentic/aegis.py anchor --task TASK-<id> [--json]
python .agentic/aegis.py evolution --task TASK-<id> [--json]
```

Both commands validate the task and record its observed stage. They operate on
tracked and untracked, non-ignored Git-visible files, excluding `.agentic/**`.
Configured layout globs classify paths as `source`, `tests`, or `other`.

## Records

The active `.anchor.json` sidecar stores a UTC timestamp, generated anchor ID,
HEAD, layout globs, file kinds, paths, and streamed SHA-256 fingerprints. The
`.evolution.json` sidecar keeps compact completed-pair reports containing UTC
times, stages, HEAD values, counts, and changed paths with before/after
identities. Re-running evolution refreshes the report for the active anchor;
starting a new pair retains prior completed summaries.

Git-ignored caches and outputs are absent. Symlinks are hashed by link identity
without following external targets. Submodules are represented by their
checked-out commit. Renames intentionally appear as removal plus addition.

## Advisory behavior

Detected changes never fail `anchor`, `evolution`, or an ordinary check.
`check --task` emits only a NOTE for a missing anchor or incomplete pair. An
invalid state file is a warning. Missing Git, invalid task IDs, or incomplete
fingerprinting produce a concise command error and no partial record.

## Workflow placement

1. Write or update the automated test and confirm the expected red failure.
2. Run `anchor` before implementation.
3. Implement and run the required tests.
4. Run `evolution` and review all changed paths.
5. Rerun `evolution` after any validation edit so the saved report describes
   the final candidate.

For work without an automated red test, run `anchor` immediately before the
first implementation edit. The commands work in every stage but are not
required around documentation-only stages.

## Constraints

- Standard library and read-only Git inspection only.
- No staging, commits, branch changes, network calls, or project test execution.
- No filesystem walk outside the Git-visible file inventory.
- State is written only beside the selected task journal.
