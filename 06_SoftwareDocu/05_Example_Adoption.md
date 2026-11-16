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

The agent reads existing context and canonical setup references, then explores
the repo. Survey populates
`.agentic/context/project.md` and `.agentic/context/environment.md` with verified
current facts, linking existing docs/configuration rather than duplicating them.
Empty sections remain valid; uncertainty stays in the journal. It writes an adoption journal
(`type: adopt`) containing a proposed component list - one checklist
item per component with a one-line scope and its file globs:

```
- [ ] player      - playback engine        (src/player/)
- [ ] library     - track/playlist storage (src/library/)
- [ ] export      - M3U/PLS writers        (src/export/)
- [ ] cli         - command-line frontend  (src/cli.py)
```

**Then it stops and shows you the list**, in both interaction modes:

```bash
python .agentic/aegis.py pause TASK-a1b2 --next "Review the component list: split, merge, rename or drop?"
```

This review is the one that matters: merge components, split them,
exclude `legacy/`. Answer in chat or edit the journal's `## Components` list
directly. When the list is agreed, the agent logs the material boundary changes
and runs `advance` to move the journal from `survey` to `components`.
Committing stays with you, under the repository's own procedures.

## Sessions 2..N - one component at a time

```
continue adoption TASK-a1b2, next component
```

Per component, the agent: reads the code **and its existing tests**
(tests are the best evidence of intended behavior), writes
`knowledge/<component>.md` as a concise route to the owned source and focused
tests, and derives requirements - `active`, with `affected_paths` set to the
component's files and `linked_tests` pointing at the **existing** tests that
already verify each behavior.

The page records the request signals that select the component, its purpose and
boundaries, public interface, load-bearing invariants, current behaviors
and owned files. It adds a change map only when multiple
independent edit-and-test seams would otherwise force broad discovery. This
shortens later orientation; it does not replace reading the exact source and
tests before a change.

Adoption mostly *links* tests; it writes new ones only where a
load-bearing behavior has none (or records the requirement with empty
`linked_tests` - see below). Suspicious behavior and its source/test evidence
belong in a consolidated journal finding or future-task record. Confirm the
intended outcome with the owner before activating a new requirement for that
disputed behavior; preserve existing contracts while investigating. Requirement
prose describes the agreed positive behavior, with investigation history in the
journal. Adoption leaves product changes to their own authorized task.

Each session ends with a ticked checkbox, a `pause` that names the next
component, and a small, readable diff. Useful properties:

- **Pause anytime.** Between sessions the repo is fully usable; being
  4/9 components done blocks nothing - you can even start normal
  feature work in an adopted area immediately.
- **Parallelize.** Colleagues on other branches/PCs each take a subset of
  the components, each with their own adoption journal; one file per
  requirement keeps the merges clean, while one shared journal would not.
- **Bounded context.** Choose components that a session can read end to end.
  This reduces context load; it does not establish model compliance at a
  particular context size.
- **Batch if you like:** "autopilot: adopt the next 3 components, then
  stop and summarize."

## Final session - close

Reconcile the context files and component pages against the surveyed checkout.
Describe actual positive responsibilities and setup, preserve established
contracts, and keep investigation findings and adoption history in the journal.

```
continue adoption TASK-a1b2, close it
```

When the last component is ticked, `advance` moves the journal to `close` (in
checkpoint mode the agent pauses first and waits for you). It runs `aegis check`
over the whole tree, fixes forward what it reports and reviews remaining gaps.
Then it runs `aegis report`, pauses with `--next "Close the adoption?"`, and
when you agree, runs `advance` to `done`. Committing and opening a pull request
follow the repository's procedures, outside AEGIS. After the merge, your
remaining governance debt is not a document - it is the live `check` output:

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
as requiring the named manual method instead of joining the automated-test
backlog. This classification does not establish that anyone performed it;
record the actual action and observed result separately:

```
NOTE   manual-verification  .agentic/requirements/ux/REQ-UX-91c0.toml - by hand: install on a ...
```

Keep the two apart honestly. A test you have not written yet is a
backlog item; a manual method is a decision.

## Adopt only what you need

Total coverage is not required. Adopt the components you actively
change and leave the rest; when an AEGIS task later touches an unadopted
area, `check --task` warns (`uncovered-source`) and that component becomes the
next adoption candidate. Direct changes outside AEGIS raise no such warning.
Incremental is the intended mode, not a compromise.

## Native hosts and interrupted adoption

OpenCode, Codex, Pi, Qwen Code and Claude Code packages can guide the same
adoption journal. Installing a plugin does not adopt a repository automatically.
Resume with `brief TASK-<id>` and read what its `Read next` line names -
`steps/adopt.md`, then the State `must_read` paths - plus the component
checklist and necessary source. `advance` moves the journal through `survey`,
`components`, `close` and `done`, and `pause` records each stop.

Independent review requests are bounded review assignments, not child tasks.
Use child journals only for independently governed development scopes. Keep
host configuration and job caches local to each developer; share the committed
requirements, knowledge pages and journals through authorized Git operations.
