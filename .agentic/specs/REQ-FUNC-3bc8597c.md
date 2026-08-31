<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-3bc8597c - Relate optional one-level child tasks to a parent task

## Behavior

`task` accepts an optional `--parent TASK-<8-hex>` argument. The named parent
must be a readable visible top-level journal in the current checkout. A journal
whose own `parent:` header is nonblank cannot be selected, so nesting stops at
one level. Creation writes only the canonical parent ID into the new child's
header; it never edits the parent.

Top-level creation remains unchanged and leaves `parent:` blank. Each child
retains its own branch, base, requirements, stage, evidence, and approvals.
Parent views discover reverse links by scanning readable journals and sorting
matching children by normalized task ID. Hidden branches are not inferred.
Parent validation owns the integrated visible candidate, while every child is
independently governed and validated.

## Data / interface

```text
python .agentic/aegis.py task "Title" --parent TASK-a1b2c3d4
parent: TASK-a1b2c3d4
```

`visible_children(parent_id: str) -> list[tuple[Path, dict]]` returns only
readable journals with a matching normalized `parent` header, ordered by task
ID. Unknown, malformed, self-referential, and nested relationships are
advisory findings during `check`. A done parent with a visible unfinished child
is also reported. Findings say "visible in this checkout".

## Acceptance

- Parent bytes are identical before and after child creation.
- Missing and child-as-parent targets are rejected without creating a journal.
- Top-level creation and legacy journals remain usable.
- No branch, worktree, merge, scheduler, dispatch, or parent mutation occurs.
