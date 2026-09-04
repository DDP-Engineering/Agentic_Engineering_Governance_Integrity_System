<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Example - adopting an existing repository

Adoption gives a legacy repo its requirement register, knowledge pages
and traceability - derived from what the code and tests already do. It
is three kinds of sessions, interruptible anywhere, spread over as many
days as you like.

## Session 1 - survey

After install (doc 01), you say:

```
using aegis workflow, adopt this repository
```

The agent explores the repo and writes an adoption journal
(`type: adopt`) containing a proposed component list - one checklist
item per component with a one-line scope and its file globs:

```
- [ ] player      - playback engine        (src/player/)
- [ ] library     - track/playlist storage (src/library/)
- [ ] export      - M3U/PLS writers        (src/export/)
- [ ] cli         - command-line frontend  (src/cli.py)
```

**Then it stops and shows you the list.** This review is the one that
matters: merge components, split them, exclude `legacy/`. Answer in
chat or edit the journal file directly. Record the approved component list;
committing or publishing still requires explicit Git authority.

## Sessions 2..N - one component at a time

```
continue adoption TASK-a1b2, next component
```

Per component, the agent: reads the code **and its existing tests**
(tests are the best evidence of intended behavior), writes
`knowledge/<component>.md` as a concise route to the owned source and focused
tests, draws that page's `## Architecture` diagram while the source is still
open, and derives requirements - `active`, with `affected_paths` set to the
component's files and `linked_tests` pointing at the **existing** tests that
already verify each behavior.

The page records the request signals that select the component, its purpose and
boundaries, public interface, load-bearing invariants, current behaviors,
architecture and owned files. It adds a change map only when multiple
independent edit-and-test seams would otherwise force broad discovery. This
shortens later orientation; it does not replace reading the exact source and
tests before a change.

The diagram is the cheapest it will ever be in this session, and it is a
drawing of what the code **does**, not what it should do: a shape nobody
can explain is a finding for the journal, not something to tidy away in
the picture. Where the agent cannot tell which way a dependency points, it
leaves the arrow out and says so underneath rather than guessing. For a
legacy component this often ends up being the only architecture document
that has ever existed for it.
Adoption mostly *links* tests; it writes new ones only where a
load-bearing behavior has none (or records the requirement with empty
`linked_tests` - see below). Suspicious behavior is adopted as-is and
noted in the journal as a future task, never silently "fixed".

Each session ends with a ticked checkbox and a small, readable diff.
Useful properties:

- **Pause anytime.** Between sessions the repo is fully usable; being
  4/9 components done blocks nothing - you can even start normal
  feature work in an adopted area immediately.
- **Parallelize.** Colleagues on other branches/PCs each take a
  component; one file per requirement keeps the merges clean.
- **Bounded context.** Choose components that a session can read end to end.
  This reduces context load; it does not establish model compliance at a
  particular context size.
- **Batch if you like:** "autopilot: adopt the next 3 components, then
  stop and summarize."

## Final session - close

```
continue adoption TASK-a1b2, close it
```

Set `stage: close`, run `aegis check` over the whole tree, resolve mechanical
errors and review remaining gaps. With explicit delivery authority, generate
`aegis report`, commit the adoption record and perform the agreed outcome.
The adoption step records `stage: done` only after the outcome succeeds;
otherwise leave it at `close`. After the merge, your remaining governance debt is
not a document - it is the live `check` output:

```
WARN   no-linked-tests  .agentic/requirements/functional/REQ-FUNC-91c0.toml - empty linked_tests
```

Every such warning is a backlog item that stays visible on every future
run until someone closes it. The report keeps those gaps visible; it does not prove complete behavioral
coverage or replace review of the backlog.

A visual legibility judgment or a clean-machine installation check may need
manual verification. Literal dialog wording can often be tested automatically;
do not classify it as manual merely because a test has not been written. Give those a `verification` starting
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

## Native hosts and interrupted adoption

OpenCode, Codex, Pi, Qwen Code and Claude Code packages can guide the same
adoption journal. Installing a plugin does not adopt a repository automatically.
Resume with `brief TASK-<id>`, read `steps/adopt.md`, the component checklist,
current Handoff and necessary source. Record `survey`, `components`, `close`
and `done` according to the adoption step.

Independent review requests are bounded review assignments, not child tasks.
Use child journals only for independently governed development scopes. Keep
host configuration and job caches local to each developer; share the committed
requirements, knowledge pages and journals through authorized Git operations.
