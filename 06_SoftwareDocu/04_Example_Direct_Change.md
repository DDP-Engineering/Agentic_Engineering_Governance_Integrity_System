# Example - direct changes and the admission rule

AEGIS records requirements so that a later change cannot silently break them.
That record is worth its cost only for durable product rules. Every other
change is made directly: no task journal, no requirement, no knowledge update.
The rule sits in the root guidance that `init` writes and in the `## Scope`
section of `.agentic/AGENTS.md`, so the agent decides before it opens any
AEGIS file.

## The rule

AEGIS governs changes that add or change a **durable product rule**: logic,
data, security, performance, integrations, or a product-wide UI rule such as
a theme, layout system, accessibility or interaction convention. A rule
applies to a class of things, and a later change could break it; a test
should catch that.

Other changes are made directly:

- a bug fix that restores intended behavior;
- a local UI adjustment: one element's position, spacing, wording or style;
- a refactor with no behavior change;
- a test, documentation or tooling fix.

A fix that contradicts an active requirement, adds behavior, or touches
security or data handling is a change, and uses AEGIS. Your explicit choice
always wins: "using AEGIS" or "without AEGIS" in the request settles it.
Otherwise the agent starts with one line that names its choice, so you can
redirect it:

```text
LANE: direct - moves one button; no product rule changes
```

## Examples

| Request | Lane | Why |
|---|---|---|
| Move the Save button to the left | direct | one element's position, a value rather than a rule |
| Use a blue background everywhere and make all buttons yellow | AEGIS | a product-wide UI rule; every new screen must follow it, and a test checks it |
| The CSV export drops its last row | direct, with a regression test | restores intended behavior |
| The orders endpoint does not check the caller's role | AEGIS | security handling |
| Move the primary button left, while an active requirement keeps primary actions on the right | AEGIS | contradicts an active requirement |
| Paginate the Tickets table, 25 rows per page | AEGIS | new behavior |

## Making a direct change

Follow the repository's own practice: reproduce, change, run the focused
tests, and let the commit message say why. Add a regression test for a logic
bug. Nothing under `.agentic/` changes. Commits, pushes and pull requests stay
with you, as for any AEGIS task.

A direct change leaves no requirement behind, and that is expected:
`check` reports `uncovered-source` only for a task's own diff
(`check --task TASK-<id>`), and `explain` states an uncovered path plainly
without calling it a defect.

## A fix that still uses AEGIS

A security or data-handling fix, or any fix you ask AEGIS to govern, walks the
ordinary stages. When existing requirements already cover the behavior, frame
puts their IDs on the journal's `requirements:` line, and specify and design
record why they are skipped:

```sh
python .agentic/aegis.py advance TASK-c3d1a2b4 --reason "scope accepted"
python .agentic/aegis.py advance TASK-c3d1a2b4 --skipped --reason "REQ-SEC-3fa2c1d4 covers the fix"
python .agentic/aegis.py advance TASK-c3d1a2b4 --skipped --reason "one file, no new interface"
```

Build then writes the failing test first and validate closes the task with the
final proof, exactly as in the [feature example](03_Example_Feature.md). The
IDs and commands are a worked example, not recorded results.
