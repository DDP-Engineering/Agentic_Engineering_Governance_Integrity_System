<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS package

This package develops and tests the exact AEGIS version 1 runtime delivered at
`template/.agentic/aegis/cli/src/aegis/`. There is no second runtime copy.

The central operation registry owns all 48 AEGIS command names, input schemas,
help, examples, availability, and dispatch. Human output and one-line JSON use
the same presentation-neutral result and the version 1
`aegis.machine.response` envelope.

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
relationships; readable Markdown sections contain the authoritative current
content. Components require one role for every member file and a description
for every linked test. The runtime does not hide or duplicate these artifacts
inside an escaped JSON front-matter field.

Delivery completion uses the latest decision whose target is `delivery`; a
later rejection supersedes an earlier approval and leaves the Run active.
Impacted selection includes only existing tests below configured test roots
with safe selectors. An invalid linked test selects the configured full suite
and records the exact fallback reason. Native host guidance invokes the flat
CLI token `stage-show`; adapter and machine responses continue to identify the
operation as `stage.show`.

Ordinary project-knowledge, entry, attachment, trace-selection, execution, and
abandonment mutations require the Run's current Stage to be `active`; completed
Stage and Run bytes remain unchanged until an explicit lifecycle transition
starts or revisits work. Every Markdown artifact reader accepts only the exact
integer schema version 1 and reports `unsupported_schema` without rewriting
unsupported input. Imported automated evidence must record a command or
selector, working directory, operational outcome, consistent exit status,
concise observed result, and the tests covered by the claim. Manual evidence
continues to record actor, procedure, expected observation, and actual
observation.

JSON mode requires `--expected-revision` for every operation that replaces a
pre-existing Run, Stage, Requirement, Specification link, Component, or
Adoption value. The token is the exact-byte `sha256:` revision returned by the
corresponding read operation. A missing token is `invalid_input` with exit 2;
a stale token is `state_conflict` with exit 4 and leaves every target byte
unchanged. Unique-identity creates, read-only operations, the disposable Run
selection pointer, and exceptional abandonment of unreadable Run state are
exempt because they do not replace a caller-observed authoritative value.
Human mode retains its existing load-and-publish behavior. Configured command
execution checks a supplied Stage revision before launching the process.
Stage completion likewise rejects a stale Stage revision before expectation
evaluation or publication. Completion evaluation never invokes configured
tests, lints, audits, or validation commands; the existing Check repository
comparison remains read-only and cannot stage, restore, commit, or otherwise
mutate Git state.

`stage-show` returns `aegis.stage.resume_context` schema 1: a bounded Run
summary, the requested Stage's exact revision and durable state, Run/Stage-
referenced Requirements and Specifications, directly referenced or trace-linked
Components, derived affected files and tests, optional `.agentic/rules.md`, and
the configured test roots, applicable commands, risk threshold, and protected
path patterns. Explicit `--run` or `--stage` inspection does not change the
selected-Run pointer. Missing, unreadable, or stale references remain visible
as findings and unavailable entries rather than disappearing or being
reconstructed.

At each durable Run or Stage mutation, AEGIS compares a read-only Git snapshot
with the Run opening baseline. It preserves dirty-start state, records later
observed paths without claiming authorship, and reports branch, revision, or
index transitions as non-blocking attribution uncertainty. A path becomes
adopted only when a `scope-revise` record explicitly names an already observed
path in `affected_work`; reads such as `run-show` and `stage-show` never update
attribution state.

Every bounded text or collection reports total, returned, and omitted size plus
its truncation state. Full-profile output includes at most 16 Requirements, 12
Components, 64 derived files, 64 tests, and 24 applicable commands; short-
profile output uses 8, 6, 32, 32, and 12 respectively. The returned `budget`
object declares all text and nested-collection caps. Ordering is stable, long
text is cut at a line/word boundary, and the envelope sets `truncated` with a
Stage `details_ref` whenever any context field is incomplete. Command arguments
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
supports Python 3.11 or later.

## Invocation

Global options precede the flat command:

```text
aegis --repo C:\path\to\installed-project --format json stage-show
aegis --repo C:\path\to\installed-project --format json --expected-revision sha256:<64-lowercase-hex> stage-set-section --input section.json
aegis --repo C:\path\to\installed-project run-create --input ticket.json
aegis --repo C:\path\to\installed-project execution-run --category tests --name project
```

Structured input files and stdin use `aegis.machine.input` schema version 1.
No operator-producible input or repository state is emitted as a traceback.
