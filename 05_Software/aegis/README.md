<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS package

This package develops and tests the exact AEGIS version 1 runtime delivered at
`template/.agentic/aegis/cli/src/aegis/`. There is no second runtime copy.

The central operation registry owns all 49 AEGIS command names, input schemas,
help, examples, availability, and dispatch. Human output and one-line JSON use
the same presentation-neutral result and the version 1
`aegis.machine.response` envelope. Human output labels the selected Run, Stage,
outcome, guidance, and durable artifact locations while summarizing large nested
data. Each human finding retains its severity, code, observation, consequence,
and artifact path on independently bounded lines; JSON mode retains the complete
machine envelope.

Implemented behavior includes:

- canonical configuration/artifact codecs, safe repository paths, exact
  payload verification, and cohesive recoverable publication;
- multiple durable Runs with one local selected context and eight self-owned
  Stage documents for full and short profiles;
- Stage evidence, findings, dispositions, decisions, exceptions, attachments,
  skips, revisits, scope changes, Delivery, and abandonment;
- current-only Requirements, Specifications, Components, trace validation,
  and impacted-test selection;
- configured shell-free tests, lints, and audits with pass, fail, timeout,
  cancellation, launch-error, large-output, red-fingerprint, and Git integrity
  evidence; and
- bounded Adoption journals and thin shared host-adapter resources for direct
  CLI, Claude Code, Codex, Qwen Code, OpenCode, and Pi use.

Default policy is advisory and non-blocking. Findings never manufacture a pass
and never perform developer-owned outward Git actions.

`config-validate` inspects pending `.agentic/.runtime/transactions/TXN-*`
material before any recovery-capable path read. It returns up to ten
informational findings with recognizable repository-relative transaction paths,
the total and reported counts, and an explicit truncation flag. Validation does
not parse, recover, or rewrite this material, including malformed entries;
ordinary authoritative reads retain the existing verified lazy rollback or
roll-forward recovery behavior.

`stage-complete` evaluates the selected full/short profile's expectations from
durable Run, Stage, configuration, and project state. Every included Stage
reports canonical sections still left as `None`; Check distinguishes a missing
red witness, an unexpected pass, an incomplete or late witness, and a complete
`exception_approved`; Alignment, Requirement, and Design expose missing current
approval; Implementation reports missing green evidence when red applies; and
Validation reports each configured command without a recorded outcome. These
findings are published atomically with Stage completion and do not approve or
advance the Stage. Short Runs omit Design only and retain the same Check,
Implementation, Validation, and Delivery truthfulness rules.

Run, Specification, and Component files use their canonical Markdown templates
as their persisted schema. TOML front matter contains identities and compact
tabular relationships; readable Markdown sections contain the authoritative
current content. A Component persists each Requirement and its behavior as one
atomic `requirement_links` relationship rendered in a single Markdown bullet;
`component.show` derives its compatibility `requirement_ids` projection from
those links. Components require one role for every member file and a
description for every linked test. The runtime does not hide or duplicate these
artifacts inside an escaped JSON front-matter field.

`component-create` and `component-update` accept
`requirement_links: [{"requirement_id": "REQ-...", "behavior": "..."}]` and
reject the former positional `requirement_ids` plus `behaviors` machine fields
as `invalid_input`. Existing schema-1 Component documents remain readable when
their legacy front-matter Requirement list agrees with the atomic rendered
pairs; disagreement is `malformed_state`, never a guessed reassignment. Drift
review accepts only the `behavior`, `interfaces`, `dependencies`, `files`, and
optional `finding` keys. Each review axis is `yes`, `no`, or `uncertain`;
omitted axes become explicit `uncertain` values, and unknown keys or values are
rejected before publication.

Component creation and update record a deterministic SHA-256 baseline for each
declared member whose exact bytes are readable at review time. Component and
trace validation report advisory `component_drift` when current readable bytes
differ or a legacy readable member has no baseline, while missing members keep
their specific finding. Validation never rewrites the Component; an explicit
Component update refreshes its baseline. Stage resume reads keep drifted
Component context available and add `resume_reference_stale` instead of
silently presenting it as current.

`requirement-create` and `requirement-update` persist an automated Requirement
even when its test list is empty or has no happy-path link, and return the
resulting `missing_happy_path` and other traceability findings with the created
or updated artifact. Missing supplied tests remain advisory findings. Malformed
or unsafe supplied test links remain `invalid_input`, and manual Requirements
still require a concrete `manual_method`. Create, update, direct validation, and
`trace-validate` also report `forbidden_requirement_identifier` for each of the
title, behavior, or confirmation fields containing a canonical `RUN-<32hex>` or
`REQ-<32hex>` identity or an uppercase ticket-like identifier. The Requirement
is preserved unchanged; the warning names the field and matched identifiers so
the author can replace provenance with self-contained prose.

`trace-validate` collects linked test paths across every current Requirement,
then enumerates every configured test root through the tracked-plus-unignored
workspace view. Its deliberately small test-file heuristic recognizes
`test_*.*`, `*_test.*`, `*.test.*`, and `*.spec.*`; it skips `__init__.py`,
`conftest.py`, bytecode, hidden/cache directories, and common generated output
directories. Each recognizable unlinked file receives one deterministic
`unlinked_test` advisory with its exact repository-relative path. A missing or
unreadable configured root produces `test_enumeration_incomplete` instead of a
false claim of complete coverage. Component linkage is not required.

All TOML read paths recursively normalize valid datetime, date, and time values
to stable protocol strings without rewriting project artifacts. A malformed
TOML artifact remains preserved and returns its repository-relative path.

Closed-enum rejections for Requirement status, priority, verification kind and
test purposes, plus decision values and evidence kinds, include every accepted
literal in the structured error's sorted `details.allowed` list. Structural
test-link and covered-file errors retain their existing fields without
presenting purpose choices as an unrelated remedy.

Delivery completion uses the latest decision whose target is `delivery`; a
later rejection supersedes an earlier approval and leaves the Run active.
When either terminal precondition is missing, the structured error points to
the exact `decision.add` approval or `stage.set_section` `terminal_result`
correction and returns one bounded atomic next action.

On completion, Delivery also adds an AEGIS-owned `recorded_state` section
derived from structured Run and Stage facts. It reports skipped or omitted
Stages and reasons, waiver escapes, non-passing executions, passing test
evidence with executed or reported provenance, and every durable impacted or
full-suite selection with selected tests, fallback reasons, and actual linked
execution mode. Check content changes and repository-state changes remain
visible from their durable findings even when author-written Delivery prose
denies them. Red-before-green state distinguishes a skipped Check, an underlying
recorded witness, the valid completed-Check witness or approved-exception
conclusion, and whether a later executed green exists. It also reports tests
changed after red evidence, whether fingerprint comparison was performed, the
total number of open findings, counts by severity, and sorted Stage names
containing them, including findings produced while Delivery completion is
evaluated. Evidence recorded by `execution.run` has `provenance = "executed"`;
evidence submitted through `evidence.add` has `provenance = "reported"`,
regardless of caller input. When Check records more than one red witness, later
Implementation and Validation test executions compare current Git-visible test
fingerprints with every usable witness and report the deterministic union of
changed paths; revisiting Check does not replace or mutate earlier evidence.
Author-written Delivery sections remain unchanged, and completion remains
advisory and non-blocking. Callers cannot replace `recorded_state` through
`stage.set_section`.

`stage.complete` reports `evaluated_expectation_count` as the number of clean
or failing section, approval, red/green, and configured-command expectations
actually evaluated; it is independent of the number of findings produced.
Implicit Stage transitions, profile changes, attachments, Requirements,
Components, and trace-selection events inherit the Run's durable actor. An
operation that accepts an actor continues to preserve the caller-supplied
value, and Runs without an explicit actor retain the `operator` default.

Configured tests, lints, and audits may execute during any active Stage. Tests
remain expected during Check, Implementation, and Validation; lints and audits
remain expected during Validation. An execution outside its expected Stage
window records the actual command evidence and outcome unchanged, adds an open
`execution_outside_expected_stage` warning naming the command, actual Stage,
and expected window, and does not block continuation or Stage completion.
Check failures remain the only executions that create red witnesses, and only
Implementation or Validation test executions compare fingerprints with them.
When a direct pytest executable or pytest/`unittest discover` module launched
by a recognized Python executable exits 5 because it collected or executed no
tests, AEGIS records compatibility outcome `launch_error`,
`engineering_conclusion = "unknown"`, the retained exit status, and an explicit
no-tests reason. Merely passing `-m pytest` or `-m unittest` to another tool does
not trigger this interpretation. Such evidence remains advisory and can never
become a red witness. Exit 5 from unrelated commands remains a completed
failure, and genuine failing tests retain normal red-witness behavior.

Impacted selection includes only existing tests below configured test roots
with safe selectors. An invalid linked test selects the configured full suite
and records the exact fallback reason. When a configured test command uses
`unittest discover`, `execution.run` preserves that command unchanged, executes
the full suite, and records effective `selection_mode = "full"` plus
`selection_fallback_reasons`; pytest and direct-unittest commands still receive
their selected test arguments. Native host guidance invokes the flat CLI token
`stage-show`; adapter and machine responses continue to identify the operation
as `stage.show`. The loadable project starters are
`.claude/skills/aegis/SKILL.md`, `.codex/skills/aegis/SKILL.md`,
`.opencode/agents/aegis.md`, `.pi/skills/aegis/SKILL.md`, and
`.qwen/commands/aegis.md`; each uses its host's metadata and discovery path.
Manifest-owned canonical copies live under
`.agentic/aegis/adapters/starters/` so WAEGIS can create project-owned copies
without treating them as replaceable payload files.

Ordinary project-knowledge, entry, attachment, trace-selection, and
execution mutations require the Run's current Stage to be `active`; completed
Stage bytes remain unchanged until an explicit lifecycle transition starts or
revisits work. A delivered or abandoned Run rejects every Run and Stage
mutation even if the local context pointer selects it; `run.show` and
`stage.show` remain available. Run abandonment is available during an active
Stage and between Stages. If the current Stage is unreadable but `run.md`
remains a canonical active Run, exceptional abandonment atomically marks that
Run abandoned, creates the sibling record naming the unreadable Stage, clears
the local pointer, and preserves the Stage bytes exactly. If `run.md` itself is
unreadable, AEGIS preserves it and records only the sibling abandonment and
pointer update without fabricating a normal Run update. Revisiting an earlier
Stage returns a different active later Stage to pending so the forward path
remains resumable. Every
Markdown artifact reader accepts only the exact
integer schema version 1 and reports `unsupported_schema` without rewriting
unsupported input. Imported automated evidence must record a command or
selector, working directory, operational outcome, consistent exit status,
concise observed result, and the tests covered by the claim. Manual evidence
continues to record actor, procedure, expected observation, and actual
observation.

JSON mode requires `--expected-revision` for every operation that replaces a
pre-existing Run, Stage, Requirement, Specification link, Component, or
Adoption value. The token is the exact-byte `sha256:` revision returned by the
corresponding read operation. Global options, including
`--expected-revision`, precede the flat command token; a misplaced known global
option remains invalid and reports that canonical placement. A missing token is
`invalid_input` with exit 2;
a stale token is `state_conflict` with exit 4 and leaves every target byte
unchanged. Both errors return that Run, Stage, Requirement, Component, or
Adoption read as their one corrective `next_actions` entry. Unique-identity
creates, read-only operations, the disposable Run selection pointer, and
exceptional abandonment of unreadable Run state are exempt because they do not
replace a caller-observed authoritative value. When exceptional abandonment
can still update a readable Run summary, an omitted token uses the revision
loaded by that fallback; an explicitly supplied stale token refuses the whole
atomic publication.
After repository resolution, structured errors retain any truthfully readable
target or selected Run, target or current Stage, and relevant current revision.
An unreadable or unresolved target is never invented; selected current context
is used only when it can be read independently.
Human mode retains its existing load-and-publish behavior. Configured command
execution checks a supplied Stage revision before launching the process.
Stage completion likewise rejects a stale Stage revision before expectation
evaluation or publication. Completion evaluation never invokes configured
tests, lints, audits, or validation commands; the existing Check repository
comparison remains read-only and cannot stage, restore, commit, or otherwise
mutate Git state.

Exact-operation help derives the global `--expected-revision <sha256>` argument,
the corresponding `run.show`, `stage.show`, `requirement.show`,
`component.show`, or `adoption.show` read, and a parser-valid example from the
same revision policy used by dispatch. Operations that accept `--input` also
return a `machine_input` help object containing the fixed
`aegis.machine.input` envelope, operation identifier, accepted `data` fields,
types, required flags, choices, and cross-field constraints. This metadata is
available through `help-show --operation <id>` and `<command> --help`; it does
not change the input parser or mutation contract.
`next_actions.arguments` keys use the target operation's canonical dispatcher
input names. Registry argument metadata maps each key to its positional or
named CLI spelling; for example, the `stage_name` input maps to the positional
Stage of `stage-start` and `stage-revisit`, and to `--stage` for `stage-show`.
The actions remain structured inputs, never shell command strings.

`run-list`, `requirement-list`, `component-list`, and `adoption-list` return at most twenty
items in their existing stable order. When `has_more` is true, pass the emitted
decimal `next_cursor` back as `--cursor <token>` to continue at that item
offset. Cursors are canonical non-negative integer strings; malformed,
negative, or beyond-end offsets return `invalid_input` on `cursor`.
An unreadable Run does not block `run-list` or hide other Runs: its position in
the page is retained as an `unreadable` entry with the Run identity and actual
repository-relative path, without inferred Run details or file repair.
Likewise, `adoption-list` discovers sorted journal identities directly from the
configured Adoption directory, reports status, Component, repository-relative
path, revision, and compact resume counts/action, and retains an `unreadable`
entry without hiding healthy journals or rewriting any Adoption.

`run-set-profile` retains the required `--profile full|short` option and also
requires structured `actor` and `reason` fields through `--input`. A successful
change appends the same truthful before/after profile, actor, and reason event
to Run history and Design history; missing attribution, invalid transitions,
and stale revisions leave both artifacts unchanged.

`stage-show` returns `aegis.stage.resume_context` schema 1: a bounded Run
summary, the requested Stage's exact revision and durable state, Run/Stage-
referenced Requirements and Specifications, directly referenced or trace-linked
Components, derived affected files and tests, optional `.agentic/rules.md`, and
the configured test roots, applicable commands, risk threshold, and protected
path patterns. Explicit `--run` or `--stage` inspection does not change the
selected-Run pointer. Missing, unreadable, or stale references remain visible
as findings and unavailable entries rather than disappearing or being
reconstructed. The response proposes one atomic `next_actions` continuation:
record the next open section or complete active work, start the next pending
Stage after completion or skip, return from historical inspection to the
current Stage, or read the terminal Run.

Stage sections, evidence, findings, decisions, and escapes occur once as
top-level bounded collections. `stage_state` carries only the Stage status,
revision, timestamps, work-applied flag, and the otherwise unique bounded
attachment and event histories. Structured Run stages, scope changes,
attribution records, Stage entries, configured commands, and command arguments
remain JSON objects and lists rather than JSON text embedded in the decoded
response, so callers do not perform a second decode and human JSON remains
readable.

Each shipped Stage workflow also supplies up to four concise `common_findings`
and four structured `recovery_actions`. A Run snapshots this guidance when it
is created, and `stage-show` exposes it in `data.guidance` without evaluating
or enforcing it. Actions identify an existing operation and describe when and
how it can help; they remain advisory, do not block Stage completion, and do
not add automatic transitions.

At each durable Run or Stage mutation, AEGIS compares a read-only Git snapshot
with the Run opening baseline. It preserves dirty-start state, records later
observed paths without claiming authorship, and reports branch, revision, or
index transitions as non-blocking attribution uncertainty. A path becomes
adopted only when a `scope-revise` record explicitly names an already observed
path in `affected_work`; reads such as `run-show` and `stage-show` never update
attribution state.

Every `scope-revise` also appends one open advisory finding to the current
Stage. The finding preserves the caller's `affected_work`, names every Stage
that is `completed` or `skipped` at revision time, and snapshots the Run's
current Requirement and Component identities. Empty sets remain explicit. The
current Stage and Run publish atomically while prior Stage status and artifacts
remain unchanged; the finding is returned by the operation and survives normal
artifact codec, `run-show`, and `stage-show` reads.

Check-stage working-file snapshots follow Git's tracked-plus-unignored view of
the repository. Ignored generated files such as test caches are not persisted
or reported as out-of-zone changes, while tracked files remain observed even if
a later ignore rule matches them. Check completion compares both exact-byte
working-file digests and per-path Git classification states. A path changed
before Check and staged, renamed, or deleted during Check is therefore named,
while an unchanged pre-existing dirty classification is not repeated. Configured
test roots and AEGIS-owned Run/runtime paths remain excluded, and the generic
repository-state warning remains advisory.

Schema 1 uses a compact bounded-value union. Text that fits its declared budget
is a string; truncated text is an object with `content`, exact
`total_characters`, `returned_characters`, and `omitted_characters`, and
`truncated = true`. A collection that fits is a list; a truncated collection is
an object with `items`, exact `total_count`, `returned_count`, and
`omitted_count`, and `truncated = true`. Complete values carry no zero-valued
accounting wrapper. Requirement, Component, discovery, and other manually
assembled context summaries use the same compact rule while retaining useful
non-accounting fields.

Full-profile output still includes at most 16 Requirements, 12 Components, 64
derived files, 64 tests, and 24 applicable commands; short-profile output still
uses 8, 6, 32, 32, and 12 respectively. The always-present `budget` object
declares every unchanged text and nested-collection cap. Ordering is stable,
long text is cut at a line/word boundary, and any nested omission makes the
envelope set `truncated = true` with the Stage `details_ref`. Command arguments
that look like secret values are redacted, and Stage reads do not run commands,
inspect live Git state, publish artifacts, or require `--expected-revision`.

## Development

```powershell
uv run --group dev python -m pytest -q tests
uv run --group dev ruff check template/.agentic/aegis/cli/src tests
uv run --group dev python -B -m aegis --help
uv run --group dev python -B -m aegis --format json version-show
```

Runtime dependencies are limited to the Python standard library. The package
supports Python 3.12.

External-runtime wrappers prefer a bundled runtime, then probe an exact Python
3.12 as `python3.12`, Windows `py -3.12`, `python3`, or `python`. This accepts
venv, pyenv, and conda environments without widening the 3.12 pin. If no
compatible interpreter exists, the wrapper returns the normal human response
or one-line JSON `missing_prerequisite` envelope with exit code 5 and empty
stderr. Once Python is available, missing Git uses the same response boundary;
repository-free help and version operations do not require Git.

## Invocation

Global options precede the flat command:

```text
aegis --repo C:\path\to\installed-project --format json stage-show
aegis --repo C:\path\to\installed-project --format json --expected-revision sha256:<64-lowercase-hex> stage-set-section --input section.json
aegis --repo C:\path\to\installed-project run-create --input ticket.json
aegis --repo C:\path\to\installed-project --expected-revision sha256:<64-lowercase-hex> run-set-profile --profile short --input profile-change.json
aegis --repo C:\path\to\installed-project execution-run --category tests --name project
```

Structured input files and stdin use `aegis.machine.input` schema version 1.
Host guidance therefore directs agents to inspect `help-show` before composing
any `--input` document, then to follow the Stage instruction, common findings,
recovery actions, and bounded next actions returned by `stage-show`. Approvals,
skips, and waivers must be recorded explicitly; outward Git actions remain
developer-owned and outside AEGIS.
When a file supplied through `--input` cannot be read, decoded, or parsed as
UTF-8 JSON, the structured `invalid_input` error names that exact supplied path.
Standard-input failures remain pathless because no file path was supplied.
No operator-producible input or repository state is emitted as a traceback.
