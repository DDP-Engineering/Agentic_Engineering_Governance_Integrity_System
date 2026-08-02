<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example — a quick fix, autopilot

The other everyday case: a small bug, you want it gone with minimum
ceremony. The quick path (`frame → build → deliver`) skips the specify
and design stages; autopilot skips the frame stop.

## You say

```
using aegis workflow, autopilot to deliver: fix the crash when the
playlist is empty (IndexError in src/export/m3u.py)
```

## What the agent does, without stopping

**frame (seconds, not a session):** opens the journal with `--type fix`,
records the proportionality decision — and this is a real decision, not
a rubber stamp:

```
- 2026-08-02 frame: quick path - crash fix, no behavior change,
  covered by existing REQ-FUNC-3fa2.
```

A fix that *changes* intended behavior would take the full path instead;
the step file tells the agent how to choose, and the journal makes the
choice reviewable.

**build:** reproduces first — a failing test that hits the empty-playlist
case — then the one-line fix, then:

```bash
python .agentic/aegis.py test --impacted --task TASK-c3d1
```

```
test --impacted (2 test ref(s)): exit 0 (0.5s)
```

The new test gets appended to the existing requirement's
`linked_tests` — the fix strengthens the contract instead of floating
free.

**deliver:** full suite, `check --task TASK-c3d1 --strict --run`,
`report TASK-c3d1`,
knowledge page untouched (no material behavior change — the journal says
so). Then the one stop autopilot always keeps:

> Ready to commit: 1 file fixed, 1 test added, checks clean. The report
> is in the journal. Commit and open the PR?

## Total cost

One prompt, one confirmation, and a paper trail: even for a ten-minute
fix you keep a journal with the red-test evidence and the delivery
report. That's the point of the quick path — proportional ceremony,
never zero ceremony.

## When *not* to use it

New behavior, changed behavior, anything touching security or data
handling → full path. If you ask for autopilot on something that turns
out bigger than described, a well-behaved agent notes it in frame and
asks anyway — and the journal shows whether it did.
