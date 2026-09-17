<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS CLI reference

AEGIS uses one standard-library Python script. Run it from the
repository root:

```text
python .agentic/aegis.py <command>
```

Use `python3` instead of `python` on systems where that is the available
Python 3.11-or-newer command. Paths and examples below are relative to the
repository root.

The CLI scaffolds artifacts, runs configured project commands, and reports
advisory findings. It does not replace the workflow in
`.agentic/AGENTS.md`, edit task stages for you, commit or push. The core
itself makes no network requests; configured project commands may do so.

## Command summary

| Command | Description | When to use |
|---|---|---|
| `init` | Complete installation after copying the payload. | Once during installation, and safely after a payload upgrade. |
| `task` | Create a task journal with a unique ID. | At the start of governed feature, fix, change, or adoption work. |
| `req` | Create a requirement TOML file with a unique ID. | When work needs a new durable requirement. |
| `anchor` | Fingerprint Git-visible repository files for a task. | After the expected red failure and before implementation. |
| `evolution` | Compare the repository with its active task anchor. | After implementation and after any later validation edit. |
| `status` | List open tasks or inspect one journal. | Before starting or resuming work, and whenever the next step is unclear. |
| `brief` | Print a deterministic bounded resume view from durable files. | First when resuming, especially with a small-context model. |
| `components` | List component knowledge titles and page paths. | Before choosing which component page to read. |
| `check` | Run the heuristic governance catalog. | During work for feedback; with `--strict --run` at the validation or CI boundary. |
| `test` | Run a command configured in `.agentic/aegis.toml`. | During build and validation; add `--task` only for a result that belongs in the durable Log. |
| `summary` | Print a compact recorded stage snapshot without writes. | After recording a stage completion, pause, blocker, or handoff; use `brief` first to resume. |
| `report` | Append a delivery summary to a task journal. | After validation and explicit delivery approval, before the delivery commit or PR. |
| `diagram` | Draw the requirement register as a Mermaid coverage map. | In review or handover, when the question is where verification is thin. |
| `trace` | Export the requirement register as a traceability matrix. | In audit, review or handover, when the whole register has to leave the repository. |
| `explain` | Show which requirements and tasks govern one path. | Reading unfamiliar code, or before changing a file you did not write. |

## General help and version

### `--help`

**Description:** Show the top-level commands. Every command and subcommand
also accepts `--help`.

**When to use:** When checking syntax against the installed payload, which is
the authority if another document has drifted.

**Examples:**

```text
python .agentic/aegis.py --help
python .agentic/aegis.py check --help
python .agentic/aegis.py task --help
```

### `--version`

**Description:** Print the installed AEGIS version.

**When to use:** After installation or upgrade, or when reporting an issue.

**Example:**

```text
python .agentic/aegis.py --version
```

## `init`

```text
python .agentic/aegis.py init [--git]
```

**Description:** Finish installing a copied AEGIS payload. It:

- creates `.agentic/requirements/`, `specs/`, `tasks/`, `knowledge/`, and `context/`
  when absent;
- scaffolds `context/project.md` and `context/environment.md` independently
  when absent, preserving existing bytes and stripping marked authoring notes;
- creates a default `.agentic/aegis.toml` only when absent;
- adds or refreshes the managed AEGIS digest in root
  `AGENTS.md`, `CLAUDE.md`, and `QWEN.md`;
- adds or removes the managed anchor/evolution block in the root `.gitignore`
  according to `[records] commit_fingerprints`, and names sidecars that are
  still tracked so a human can untrack them (it never runs `git rm`);
- reports whether Git is installed and whether the directory is a repository;
- preserves project-owned data and an existing `aegis.toml`.

The command is idempotent: running it again does not replace the repository's
configuration or governance records.

Context scaffolds contain headings for current project/setup facts. Populate
them from evidence during frame or adoption and update affected sections when
facts change. See [Project context](Project_Context.md).

When Git is installed but the directory is not a repository, plain `init`
prints the next command without changing Git state. `init --git` explicitly
runs `git init`. If Git is unavailable, AEGIS still installs but reports that
diff checks, impacted selection, anchor, and evolution evidence are disabled.

**When to use:** Immediately after copying `.agentic/` into a repository.
Run it again after copying a newer payload so the root digests match the
installed workflow.

**Example:**

```text
python .agentic/aegis.py init
python .agentic/aegis.py init --git
```

Afterward, edit `.agentic/aegis.toml` so `[commands]`, `[layout]`, optional
`[interaction]`, `[records]`, and `[check]` settings describe the repository.

## `task`

```text
python .agentic/aegis.py task "<title>" [--type {feature,fix,change,adopt}] [--parent TASK-<id>]
```

**Description:** Create `.agentic/tasks/TASK-<id>.md` from the task
template. The journal receives a collision-resistant ID, the current date,
the current Git branch when available, `stage: frame`, and the interaction mode
resolved from `aegis.toml`. The new path is printed on stdout.

The default type is `feature`. Accepted types are:

| Type | Use for |
|---|---|
| `feature` | New user-visible or system capability. |
| `fix` | Correction of confirmed faulty behavior. |
| `change` | Maintenance or behavior change that is not best described as a feature or fix. |
| `adopt` | Bringing an existing repository under AEGIS. |

**When to use:** At the beginning of a new governed unit of work, after first
using `status` to ensure an existing open journal does not already cover it.

**Examples:**

```text
python .agentic/aegis.py task "Export audit report" --type feature
python .agentic/aegis.py task "Handle empty configuration" --type fix
python .agentic/aegis.py task "Adopt inventory service" --type adopt
```

The CLI creates the journal but does not advance its stage. Follow the
relevant step file and edit the journal as instructed.

`--parent` creates only a child-side link to an existing top-level task.
Nested children are rejected, the parent journal is unchanged, and every child
keeps independent branch/base, requirements, validation, and delivery state.
Reverse lookup reports children visible in the current checkout only. Parent
validation owns the integrated candidate.

New task and requirement records omit explicitly marked template-only authoring
notes while retaining their license and data fields. Existing records are never
rewritten. Inspect the templates when their full field guidance is needed.

## `anchor`

```text
python .agentic/aegis.py anchor --task TASK-<id> [--json]
```

Record a UTC-timestamped fingerprint of every tracked or untracked,
non-ignored repository file except `.agentic/**`. The anchor includes the task
stage, HEAD, layout globs, `source`/`tests`/`other` categories, file kinds,
paths, and SHA-256 hashes. Regular files are streamed in chunks; symlinks use
their link identity and submodules use their checked-out commit. Generated
Python bytecode under `__pycache__/`, plus `.pyc` and `.pyo` files, is always
excluded. Run it after the expected red test and before implementation, or
immediately before the first implementation edit when no automated red test
applies. Replacing an anchor without a completed evolution is allowed but
reported visibly. Both sidecars stay out of git by default; see
`[records] commit_fingerprints`.

## `evolution`

```text
python .agentic/aegis.py evolution --task TASK-<id> [--json] [--compact]
```

Compare the current repository with its active task anchor and report added,
modified, and removed paths as `source`, `tests`, or `other`. Successful
comparisons always exit zero regardless of changes. Compact completed-pair
reports are retained; rerunning evolution refreshes the active pair. Renames
appear as one removal and one addition. A previously visible untracked file
that becomes ignored after anchoring appears removed from the monitored state.

These records describe repository evolution. They are not tamper-proof and do
not prove that the red test or implementation was honest.

`check --task` adds a `repo-evolution` NOTE when the active pair is missing or
incomplete. Missing records never become warnings. Malformed or task-mismatched
state files are warnings, but an ordinary non-strict check still exits zero.

For evolution, `--compact --json` emits paths, statuses and areas without the
before/after hashes. The saved evolution file remains complete; ordinary `--json`
output retains its existing schema and detail.

## `req`

```text
python .agentic/aegis.py req <category> "<title>"
```

**Description:** Create a requirement TOML file from the requirement template.
The file receives a collision-resistant requirement ID and the current
creation/update date. Its path is printed on stdout.

Accepted categories and aliases:

The abbreviation printed inside a requirement ID is always accepted as its
own category name, so `func` and `functional` do the same thing.

| Input | Stored category and ID prefix |
|---|---|
| `functional`, `func` | `functional`, `REQ-FUNC` |
| `ux` | `ux`, `REQ-UX` |
| `nfr`, `non_functional` | `nfr`, `REQ-NFR` |
| `security`, `sec` | `security`, `REQ-SEC` |
| `data`, `data_privacy` | `data`, `REQ-DATA` |
| `platform`, `plat` | `platform`, `REQ-PLAT` |
| `reliability`, `rel`, `release` | `reliability`, `REQ-REL` |
| `test`, `testing` | `test`, `REQ-TEST` |

**When to use:** During specification when no existing requirement expresses
the intended behavior. Update or reuse an existing requirement instead when
it already owns the behavior.

**Examples:**

```text
python .agentic/aegis.py req functional "Export reports as JSON"
python .agentic/aegis.py req security "Reject unsigned packages"
python .agentic/aegis.py req reliability "Restore interrupted uploads"
```

The generated file is a scaffold. Complete its statement, rationale,
acceptance criteria, affected paths, and verification links before treating it
as active.

## `status`

```text
python .agentic/aegis.py status [TASK-<id>|<id>] [--all] [--json]
```

**Description:** Without a task ID, list task journals that are not
`stage: done`. With an ID, show that journal's header, checklist progress,
recent log entries, and the step file to open next. The short hexadecimal ID
is accepted with or without the `TASK-` prefix.

Options:

| Option | Effect |
|---|---|
| `--all` | Include journals whose stage is `done`. |
| `--json` | Emit one complete schema-versioned JSON document on stdout. |

**When to use:** Before opening new work, when resuming after an interruption,
or when handing work to another developer or agent.

**Examples:**

```text
python .agentic/aegis.py status
python .agentic/aegis.py status --all
python .agentic/aegis.py status TASK-8b12
python .agentic/aegis.py status 8b12 --json
```

## `summary`

```text
python .agentic/aegis.py summary <TASK-id|id>
```

**Description:** Print a compact recorded stage snapshot without writing files,
running checks/tests, consulting Git, or changing workflow state. Existing
`status` output and JSON are unchanged; `report` remains the journal-writing
delivery command. Use `summary` after updating a stage report; use `brief` first
when resuming.

The journal may contain one optional `## Stage report` section with plain
one-line fields (no bullets or code fences inside the actual section):

```text
stage: specify
result: completed
current: design
changed: requirements created; IDs are on the journal header
evidence: check exit 0; tests not run at this stage
issues: none recorded
next: follow 3_design.md
needs_user: no
```

`stage` is the reported stage; `current` must equal the journal header after
any transition. Use canonical ordinary/adoption stages, not display aliases.
`result` accepts `in_progress`, `completed`, `paused`, `blocked`, or `skipped`.
The other fields contain the agent's recorded observations and decisions;
blank values print `not recorded`. Add a concise Log line only when the boundary
or outcome is durable; do not duplicate the whole Stage report. Replace only
this latest-view section.

Output fields, in order: **Stage, Task, Current, Requirements, Changed,
Evidence, Issues, Next, Needs user, Spec compliance, Implementation quality,
Review round, Details**. Stage combines the reported
stage and result; Current and Requirements come from the journal header.
Details points to the full journal. Each value is at most 240 characters,
including a visible `[truncated; read journal]` marker for omitted detail.
If any value is shortened, Needs user directs full-journal review before
proceeding, even if the record said no. This is a character bound, not a
model-specific token guarantee.

Missing records and incomplete or mismatched stage bindings suppress recorded
outcomes and next-action claims and direct journal review. Unknown stages or
results, duplicate sections/fields, unknown keys, and malformed record lines
exit 1 with an error and no partial stdout. Old journals need no migration.
Commented and fenced examples outside the live section do not supply report
facts; literal comment markers in inline code and fence info stay literal.

The output is an agent-authored snapshot, **not fresh proof or an approval**.
A matching stage cannot detect subsequent source edits: refresh the record
after new work, evidence, deviations, or decisions even within one stage.
Read omitted details and unresolved issues before acting. Normal checkpoints,
full validation/delivery reads, and immediate deviation notices still apply.

## `brief`

```text
python .agentic/aegis.py brief <TASK-id|id>
```

`brief` is a read-only deterministic resume view built only from durable
workspace files. It never calls Git, runs commands, writes state, advances a
stage, or infers approval. Its fixed order is Task, Stage, Branch/base, Parent,
Requirements, Context, Checklist, Stage report, Interaction, Review, Active rulings, Handoff,
Visible children, and Details. Scalars are limited to 240 characters, active
rulings to eight, and visible children to twenty, with explicit omission and
stale-data markers. Two calls against unchanged files are byte-identical.

Context lists the project profile and environment guide paths as `present` or
`not recorded`; it reads neither body and creates nothing. Missing files are
supported. Read the profile and relevant environment sections before following
their selected references; presence alone establishes neither accuracy nor
completeness.

Resume with `brief`, then read the current step and handoff `must_read` paths.
Use `summary` for the latest bound stage-report projection and the full journal
for complete history and evidence.

## `components`

```text
python .agentic/aegis.py components
```

`components` reads `.agentic/knowledge/*.md` titles and prints one
tab-separated bounded printable title and lexical repository-relative path per
component, ordered by path. It uses the first level-one heading, falling back
to the filename stem so a headingless page remains discoverable. It does not
parse body sections. It rejects a link that resolves outside the knowledge
directory, a resolution loop, or a non-printable catalogue path without
partial output. An empty catalogue prints
`no component knowledge pages`. The command accepts no arguments and writes
nothing.

Use the list to choose which page to read during governed work or to inventory
existing pages during adoption. It does not infer ownership, select a page, or
replace Routing, exact source, or focused tests.

## Coordinated workflow records

Optional child links, Rulings, Handoff, and review fields are backward
compatible. Rulings use this append-only form:

```text
- RULING-001 | date=2026-08-31 | decision=<decision> | reason=<reason> | source=user | supersedes=none
```

`source` is `user`, `repository`, `requirement`, or `technical`. Supersession appends a new ruling;
it never rewrites history or expands authority. Handoff is one replaceable
stage-bound block with `current`, `next`, `must_read`, `blockers`, and a
`ready`, `waiting`, or `blocked` status.

```toml
[interaction]
autopilot = false
```

Missing or invalid `autopilot` values mean off. Checkpoint mode stops after
every stage and presents the applicable choices. Autopilot flows between
intermediate stages but does not bypass publication approval. New journals
record the resolved `interaction: checkpoint|autopilot` mode; an explicit user
instruction may override the configured default for that task.

```toml
[review]
enabled = false
max_fix_cycles = 2
```

Review is optional; validation and delivery approval are not. When enabled,
`spec_compliance` and `implementation_quality` are independent current-
candidate verdicts (`approved` or `changes_required`) and `review_round` is
bounded by `1 + max_fix_cycles`. Any candidate change invalidates both
verdicts. Exhaustion blocks with `needs_user: yes`. `max_fix_cycles` accepts
integers 0 through 255; invalid types or values warn and fail safe.

```toml
[records]
commit_fingerprints = false
```

Anchor and evolution sidecars are local evidence by default: `init` keeps a
marked block in the root `.gitignore` that excludes them, and the journal log
line remains the durable record. Set `commit_fingerprints = true` and rerun
`init` to remove the block and commit the sidecars with the journal. `check`
reports `fingerprints-tracked` when the repository disagrees with the setting.
AEGIS never untracks files; `init` prints the `git rm --cached` command.

## `check`

```text
python .agentic/aegis.py check [--task TASK-<id>] [--strict] [--run] [--full] [--json]
```

**Description:** Run the advisory check catalog over requirements, journals,
configuration, and the Git diff against the resolved default branch. Findings
are `ERROR`, `WARN`, or `NOTE`.

Without `--strict`, findings do not block work and the command exits zero.
Read them and correct real issues or record why a finding does not apply.

Set optional `[layout] docs` globs for documentation outside source/tests,
for example `docs = ["docs/", "README.md", "CHANGELOG.md"]`. These paths
remain in secret scanning and the diff; they do not count as source, tests,
or stage write zones. Existing source/tests matches still apply if globs
overlap. The default empty list preserves existing layout checks.
An unticked delivery checklist remains a warning even when delivery is
intentionally on hold; a pause is not evidence that its items are complete.

Options:

| Option | Effect |
|---|---|
| `--task TASK-<id>` | Scope diff-based checks to the named task. |
| `--strict` | Exit 1 for errors, failed `--run` commands, and warnings promoted in `aegis.toml`; also implies `--full`. |
| `--run` | Also execute eligible `[commands]` entries from `aegis.toml`. |
| `--full` | Print every finding instead of capping human-readable output at 40. |
| `--json` | Emit one complete schema-versioned JSON document on stdout; `--run` progress goes to stderr. |

**When to use:**

- use plain `check` during specification, design, and build for inexpensive
  feedback;
- use `--task` when a shared branch contains unrelated changes;
- use `--strict --run` after the final candidate is stable or in CI;
- use `--json` only when a script needs structured results.

**Examples:**

```text
python .agentic/aegis.py check
python .agentic/aegis.py check --task TASK-8b12
python .agentic/aegis.py check --task TASK-8b12 --strict --run
python .agentic/aegis.py check --strict --full
python .agentic/aegis.py check --json
```

`--run` proves only the commands it actually executes. Read the printed
`run:` lines, especially when `[check] run` restricts the configured
command set.

## `test`

```text
python .agentic/aegis.py test [name] [--impacted] [--no-fallback] [--dry-run] [--base <rev>] [--task TASK-<id>]
```

**Description:** Run a command from the `[commands]` table in
`.agentic/aegis.toml`. The default command name is `test`. Output streams
live, and the AEGIS process returns the executed command's exit code.

Options:

| Argument or option | Effect |
|---|---|
| `name` | Run that configured command, for example `test` or `lint`. |
| `--impacted` | For the default `test` command, substitute linked impacted tests into the configured `test_impacted` template. |
| `--no-fallback` | With `--impacted`, exit 1 without running or recording test evidence when selection is unavailable. |
| `--dry-run` | Preview the command and working directory without execution or journal writes; exit zero is not test proof. |
| `--base <rev>` | Take the diff against that revision instead of the merge base. `--base HEAD` selects only uncommitted work. |
| `--task TASK-<id>` | Validate the task ID before running and append every invocation's result and duration to its journal. Use only for deliberate durable evidence. |

If impact selection cannot produce a focused set, AEGIS explains why
and falls back to the full `test` command unless `--no-fallback` was requested.
`--no-fallback` requires `--impacted`. `--impacted` cannot be combined
with a command name other than `test`.

Without `--base`, the diff runs from the merge base with the default branch,
so everything the branch has changed since it forked counts. The default branch
is `[layout] default_branch` when set, else whatever `origin/HEAD` points at,
else a local `master`, else a local `main`. That is the
right basis for reviewing a branch and the wrong one for an edit-run loop on
a long-lived branch, where it can select most of the suite. Use `--base HEAD`
during build to select only what you have not committed yet.

Omit `--task` from ordinary edit-test retries. Add it only when the invocation
is the consolidated red, final green for a meaningful behavior increment, or
final validation result that should remain in the durable Log.

Unsupported selector suffixes, including test names containing spaces or quotes,
are discarded in favor of their validated test file. Unsafe or repository-escaping
file paths are never interpolated. Multiple references to a broadened file become
one file argument. AEGIS supplies references; the configured runner must honor
both file and exact-selector input. It does not translate between test frameworks.
Paths with spaces still require a project-native command rather than interpolation.

A focused set that would make the command longer than the platform can launch
is not an error: AEGIS reduces it to one entry per distinct test file,
says so, and only falls back to the full suite if even that is too long and
`--no-fallback` was not requested. With that flag, it refuses execution instead.

**When to use:**

- use a focused project-native command, or `test --impacted --base HEAD --no-fallback`, during build;
- use `check --task TASK-<id> --strict --run` once after final edits and review; do not precede it with another full `test`;
- use `test <name>` for other configured read-only checks such as linting.

**Examples:**

```text
python .agentic/aegis.py test
python .agentic/aegis.py test --impacted
python .agentic/aegis.py test --impacted --base HEAD --dry-run
python .agentic/aegis.py test --impacted --base HEAD --no-fallback
python .agentic/aegis.py test --task TASK-8b12
python .agentic/aegis.py test lint
```

Example configuration:

```toml
[commands]
test = "python -m pytest -q"
test_impacted = "python -m pytest -q {tests}"
lint = "python -m ruff check ."
```

When the application lives below the repository root, set `workdir` rather
than putting a directory change inside the commands:

```toml
[commands]
workdir = "app"
test = "python -m pytest -q"
test_impacted = "python -m pytest -q {tests}"
```

Every configured command then runs in `app/`, and the repository-relative
paths stored in `linked_tests` are rewritten to match before substitution. A
command that changes directory itself would instead resolve those paths a
second time, against the directory it just moved into, and find nothing.
`workdir` and `timeout` configure how commands run and are never executed as
commands themselves.

### Time limits

Nothing is limited by default. A limit low enough to stop a suite the
repository considers healthy would report a failure that never happened, so a
command runs until it finishes unless you ask for a limit:

```toml
[commands]
test = "python -m pytest -q"
lint = "python -m ruff check ."
timeout = 0          # the shared default; 0 or absent means no limit

[timeouts]
test = 5400          # this command only, overriding the shared default
lint = 120
```

`[timeouts] <name>` wins over `[commands] timeout`, so a suite measured in
tens of minutes and a linter measured in seconds no longer have to share one
number. Zero, negative, and unreadable values all mean no limit.

A command stopped by its limit is reported as `command-timeout`, separately
from `command-failed`, and its message says that nothing was proven. Both are
errors, because an unfinished proof is not a proof - but a report must never
suggest that a suite ran and was judged when it was cut off instead.

Command strings are executed by the platform shell. Keep them repository-owned
and review configuration changes like code.

## `report`

```text
python .agentic/aegis.py report <TASK-id|id>
```

**Description:** Append a dated delivery report to a task journal. The report
records the journal state, linked requirement titles, diff size, check counts,
checklist completion, review policy, and bound current verdicts. Missing,
malformed, or stale verdict evidence is never approval. Repeated runs do not replace
history.

**When to use:** In the delivery stage after validation evidence is final and
the concrete delivery action is explicitly authorized, before committing or
opening the pull request. Read the appended report before
delivery; it is a snapshot, so rerun it if the candidate or checklist changes.

The diff is measured from the commit the journal's `base:` header records -
the commit that was checked out when the task was created - and the report
names that basis, for example `diff vs task base 41e9f55`. A journal without
that header falls back to the merge base with the default branch and says
`diff vs merge base`, which on a branch carrying earlier work counts that work
as this task's own. `check --task` uses the same basis, so the two agree.
Leave `base:` alone once it is written; changing it changes what every later
report claims the task did.

**Examples:**

```text
python .agentic/aegis.py report TASK-8b12
python .agentic/aegis.py report 8b12
```

## `diagram`

```text
python .agentic/aegis.py diagram [--component NAME] [--task TASK-id] [--out PATH]
```

**Description:** Draw the requirement register as a Mermaid flowchart. Each
requirement becomes a node grouped under the component whose knowledge page
lists it in `## Key behaviors`, colored by the outcome `check` reaches for
that same record:

| Class | An active requirement where | `check` reports |
|---|---|---|
| `tested` | every entry in `linked_tests` resolves to a file | nothing |
| `manual` | nothing is linked and `verification` names a `Manual:` or `Inspection:` method | NOTE `manual-verification` |
| `broken` | something is linked but at least one entry does not resolve | WARN `no-linked-tests` |
| `uncovered` | nothing is linked and no method is named | WARN `no-linked-tests` |
| `draft` | - the requirement is still `status = "draft"` | nothing |
| `retired` | - the behavior was withdrawn | nothing |

`broken` outranks `manual`: a record that claims a test which is not there is
making a claim, and the claim is the finding. `draft` and `retired` are the
two `check` is deliberately silent about, and they are drawn apart from
`uncovered` so a behavior nobody has written yet is not read as one nobody
verifies. Requirements no page claims are grouped last under
`(no knowledge page)` rather than dropped.

Everything in the drawing is read from files already in the repository, so
the command needs no model, no network, and no renderer - the output is text
that Git diffs and that Markdown viewers draw for themselves. It writes no
repository state.

**When to use:** In review, when handing a component to someone else, or
whenever the question is where verification is thin rather than what one
requirement says. `check` remains the authority on findings; this is the same
data arranged to be looked at, and every class above maps onto one of its
outcomes rather than reaching a second opinion.

**Options:**

| Option | Effect |
|---|---|
| `--component NAME` | Restrict to one knowledge page, named by file stem or by heading. |
| `--task TASK-id` | Restrict to the requirements listed in that journal's header. |
| `--out PATH` | Write the diagram to a file as UTF-8, creating parent folders, instead of printing it. |

A whole-register diagram stops being readable somewhere past a few dozen
requirements. Narrow it before that point rather than after. An unknown
component or task is an error, not an empty diagram.

`--out` exists because printing is not portable: a console under a legacy
code page mangles the characters on the way out, and a diagram that renders
differently per platform is not a durable artifact. Redirecting stdout to a
file inherits the same problem; `--out` does not.

**Examples:**

```text
python .agentic/aegis.py diagram
python .agentic/aegis.py diagram --component core-cli-lifecycle
python .agentic/aegis.py diagram --task TASK-8b12
python .agentic/aegis.py diagram --out docs/coverage.mmd
```

## `trace`

```text
python .agentic/aegis.py trace [--format {md,csv}] [--out PATH]
```

**Description:** Export the whole requirement register as a flat traceability
matrix - one row per requirement, whatever its status. Each row carries the
identifier, category, status, coverage class, claiming component, title,
statement, verification method, spec reference, and the complete linked-test
and affected-path lists with their counts.

The coverage class is the same verdict `check` and `diagram` reach for that
record, read from the one shared classifier rather than derived again.

Rows are ordered by category - in the order the `req` table above lists them -
and then by identifier, so two runs over unchanged files produce identical
bytes. Nothing is truncated in either format: `summary` and `brief` bound
their output because they are resume views for a context-limited reader, while
this is a durable artifact whose point is completeness.

A requirement file that does not parse is named on stderr and left out of the
table rather than dropped in silence, and the Markdown summary counts it. The
exit status stays 0; `check` is the authority on findings and already reports
that file as a `req-parse` error.

Readable files with validation errors remain listed; their warnings are
separate from omitted-file counts. Category is the first folder below
`requirements/`, including for nested files; a file directly in that root is
marked `(no category)`. An unreadable knowledge page is warned about without
discarding requirement rows, and otherwise unclaimed rows are marked
`(knowledge incomplete)` because ownership could not be fully determined.

| Option | Effect |
|---|---|
| `--format md` | A Markdown table under separate coverage and category summary paragraphs. Escapes literal text, including pipes and markup; flattens whitespace within each list entry, then joins entries with `<br>`. Files use UTF-8. |
| `--format csv` | Header row and data only. Standard CSV quoting; joins list columns with `; `. Files use UTF-8 with a byte-order mark. |
| `--out PATH` | Write to a file, creating parent folders, instead of printing. The suffix does not select the format; use `--format csv` for CSV. |

The CSV header names are the requirement TOML keys, so the file is
self-describing against the records it came from. The Markdown headers are
human labels, because that is the copy a reviewer or an assessor reads.

CSV preserves field values without formula neutralization. A spreadsheet may
interpret text beginning with `=`, `+`, `-` or `@` as a formula; import the CSV
with columns treated as text when reviewing untrusted records. The BOM controls
encoding, not cell interpretation. Joined lists are display values, not a
reversible list encoding: an entry containing `; ` is indistinguishable from
that separator. Counts describe the source entries, not a split on `; `.

`--format csv --out` writes a byte-order mark because that is what stops a
spreadsheet application guessing the system code page; the register already
holds characters that guess wrongly. As with `diagram`, `--out` exists because
printing is not portable - a console under a legacy code page mangles the
characters on the way out, and redirecting stdout to a file inherits the same
problem.

**When to use:** In an audit, a review, or a handover, when someone needs the
whole register outside the repository - the third reader of the same data.
`diagram` groups it into a picture that stops being legible past a few dozen
requirements, `explain` answers about one path, and this narrows nothing.

**Examples:**

```text
python .agentic/aegis.py trace
python .agentic/aegis.py trace --format csv
python .agentic/aegis.py trace --out docs/traceability-matrix.md
python .agentic/aegis.py trace --format csv --out docs/traceability-matrix.csv
```

## `explain`

```text
python .agentic/aegis.py explain <path>
```

**Description:** Report what governs one repository path. Lists every
requirement whose `affected_paths` cover it - a directory entry covers the
files beneath it, and a glob is matched case-sensitively so Windows and Linux
agree - grouped under the component whose knowledge page claims each
requirement, with its status, how it is verified, and its spec where it has
one. Then the task journals whose `requirements:` header lists any of them.

The path may be repo-relative or absolute, with native or forward separators.
A path no requirement covers is reported plainly, and said to be a finding
when it sits inside the configured `source` or `tests` globs - ungoverned
code in a governed area is worth knowing about.

**When to use:** Reading unfamiliar code and asking "why is this here, and
what am I allowed to change?". It is the register read backwards: `req` and
`check` write the traceability, this is how a human spends it.

**Examples:**

```text
python .agentic/aegis.py explain src/export/m3u.py
python .agentic/aegis.py explain src/export/
python .agentic/aegis.py explain C:\repo\src\export\m3u.py
```

## Exit behavior and machine-readable output

| Situation | Exit behavior |
|---|---|
| `init`, `task`, `req`, `anchor`, `evolution`, `status`, `summary`, `brief`, `components`, `report`, `diagram`, `trace`, or `explain` succeeds | Exit 0. `evolution` still exits 0 when it finds changes. |
| Usage, missing task, invalid configuration, or another expected CLI error | One error line on stderr and exit 1. |
| Plain `check` finds errors or warnings | Exit 0; it remains advisory. |
| `check --strict` finds a strict failure | Exit 1. |
| `test` runs a configured command | Return that command's exit code. |
| A configured command is stopped by its time limit | Exit 124, reported as proving nothing. |

For `check --json`, `status --json`, `anchor --json`, and `evolution --json`,
successful stdout contains exactly one JSON document with a `schema` integer.
On a usage or configuration error, stdout is empty and the error is written to
stderr; consumers must treat empty stdout as failure, not as an empty result.

## Commands intentionally not provided

AEGIS has no command for stage transitions, approvals, waivers, evidence
forms, commits, pushes, upgrades, or uninstalling. Those actions remain visible
plain-file or Git operations:

- edit the task journal to advance a stage according to its step file;
- upgrade by copying the newer payload, running `init`, and reviewing the
  diff;
- uninstall by removing the payload and its managed root pointer blocks;
- commit and publish only through the repository's normal Git workflow.

## Optional integration operations are a separate interface

The OpenCode, Codex, Pi, Qwen Code and Claude Code packages call the installed
core and provide the following shared operations. These are **not additional
`aegis.py` subcommands**; host wrappers expose them as native tools, MCP tools
or the Codex command bridge.

| Operation | Purpose |
|---|---|
| `status` | Inspect the checkout's workflow state. |
| `resume` | Resolve a task and read its bounded re-entry context. |
| `read` | Read allowed workflow artifacts. |
| `summary` | Read the recorded stage report. |
| `check` | Run advisory/static governance inspection. |
| `scaffold` | Create supported task/requirement artifacts as coordinator. |
| `evidence` | Work with core anchor/evolution records. |
| `candidate` | Fingerprint the review candidate. |
| `diff` | Inspect candidate changes. |
| `run` | Start or recover a tracked verification job. |
| `job` | Inspect job output/state or request permitted cancellation. |

The bridge does not grant stronger permissions than its host. Codex bridge
calls are stateless: provide the task ID on every task-scoped call. Follow the
package's documented argument schema rather than guessing `aegis.py` syntax.
Host `setup.mjs install/update/doctor/uninstall` handles package lifecycle;
the core `init` only installs/refreshes repository workflow files.

See [Agent_Plugins.md](Agent_Plugins.md) for host entry points, runtime paths,
ownership checks, shared job caches and verification limitations.
