<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example — adopting an existing repository

Adoption gives a legacy repo its requirement register, knowledge pages
and traceability — derived from what the code and tests already do. It
is three kinds of sessions, interruptible anywhere, spread over as many
days as you like.

## Session 1 — survey

After install (doc 01), you say:

```
using aegis workflow, adopt this repository
```

The agent explores the repo and writes an adoption journal
(`type: adopt`) containing a proposed component list — one checklist
item per component with a one-line scope and its file globs:

```
- [ ] player      - playback engine        (src/player/)
- [ ] library     - track/playlist storage (src/library/)
- [ ] export      - M3U/PLS writers        (src/export/)
- [ ] cli         - command-line frontend  (src/cli.py)
```

**Then it stops and shows you the list.** This review is the one that
matters: merge components, split them, exclude `legacy/`. Answer in
chat or edit the journal file directly — it's just markdown. Commit.

## Sessions 2..N — one component at a time

```
continue adoption TASK-a1b2, next component
```

Per component, the agent: reads the code **and its existing tests**
(tests are the best evidence of intended behavior), writes
`knowledge/<component>.md`, draws that page's `## Architecture` diagram
while the source is still open, and derives requirements — `active`, with
`affected_paths` set to the component's files and `linked_tests`
pointing at the **existing** tests that already verify each behavior.

The diagram is the cheapest it will ever be in this session, and it is a
drawing of what the code **does**, not what it should do: a shape nobody
can explain is a finding for the journal, not something to tidy away in
the picture. Where the agent cannot tell which way a dependency points, it
leaves the arrow out and says so underneath rather than guessing. For a
legacy component this often ends up being the only architecture document
that has ever existed for it.
Adoption mostly *links* tests; it writes new ones only where a
load-bearing behavior has none (or records the requirement with empty
`linked_tests` — see below). Suspicious behavior is adopted as-is and
noted in the journal as a future task, never silently "fixed".

Each session ends with a ticked checkbox and a small, readable diff.
Useful properties:

- **Pause anytime.** Between sessions the repo is fully usable; being
  4/9 components done blocks nothing — you can even start normal
  feature work in an adopted area immediately.
- **Parallelize.** Colleagues on other branches/PCs each take a
  component; one file per requirement keeps the merges clean.
- **Small models welcome.** One component per session is sized for a
  64K-context local model.
- **Batch if you like:** "autopilot: adopt the next 3 components, then
  stop and summarize."

## Final session — close

```
continue adoption TASK-a1b2, close it
```

`aegis check` over the whole tree, dangling links and duplicates fixed,
`aegis report`, PR. After the merge, your remaining governance debt is
not a document — it is the live `check` output:

```
WARN   no-linked-tests  .agentic/requirements/functional/REQ-FUNC-91c0.toml - empty linked_tests
```

Every such warning is a backlog item that stays visible on every future
run until someone closes it. Nothing blocks; nothing is forgotten.

Behavior that no test could *ever* settle is a different case, and
adoption meets plenty of it — a legacy dialog's wording, an installer's
behavior on a clean machine. Give those a `verification` starting
`Manual:` or `Inspection:` that names the method, and they are recorded
as verified by hand instead of joining the test backlog:

```
NOTE   manual-verification  .agentic/requirements/ux/REQ-UX-91c0.toml - by hand: install on a ...
```

Keep the two apart honestly. A test you have not written yet is a
backlog item; a manual method is a decision.

## Adopt only what you need

Total coverage is not required. Adopt the components you actively
change and leave the rest; when a task later touches an unadopted area,
`check` warns (`uncovered-source`) and that component becomes the next
adoption candidate. Incremental is the intended mode, not a compromise.
