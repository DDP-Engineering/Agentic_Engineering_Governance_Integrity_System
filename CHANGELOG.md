<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to AEGIS are documented in this file.

## [Unreleased]

### Changed

- The root pointer digest written by `init` now names the `know_graph` commands,
  conditional on `[codegraph] enabled = true`.
- CodeGraph answers name the function, class or module containing each
  reference (`from=<qualified name> id=<id>`, JSON `from_name`).
- `know_graph_symbol`, `know_graph_callers` and `know_graph_refs` take up to 20
  IDs and answer them in one response, in the order given.

## [0.14.0] - 2026-10-04

### Added

- Optional CodeGraph add-on (`05_Software/aegis/plugins/codegraph/`): eight
  `know_graph` commands answer bounded Python navigation questions from a local
  index; off by default (`[codegraph] enabled`).
- `[records] commit_fingerprints` (default `false`): `init` maintains a
  managed block in the root `.gitignore` that keeps anchor and evolution
  sidecars out of git, removes it when the setting is `true`, and names
  sidecars that are still tracked without running any git write. A new
  `fingerprints-tracked` check reports a repository that disagrees with the
  setting.
- Document every configuration setting with the value `init` writes and the
  behavior that applies when the key is absent, in the installation guide and
  as a new settings slide in its deck.

### Changed

- Use repo-relative paths in workflow transitions, instructions, CLI guidance,
  and host prompts so agents can open the intended files from the checkout root.
- Reconcile component knowledge and architecture in validate before final review
  and proof; update during build only when needed for an agent handoff.
- Accept `[review] max_fix_cycles` from 0 through 255 instead of 0 through 5;
  the default stays 2 and total review rounds remain `1 + max_fix_cycles`.
- Name `[layout] default_branch` in the configuration `init` writes and in
  the configuration guide, so every key the CLI reads is discoverable from
  the generated file.
- State how the default branch resolves where the CLI reference relies on it.
- Carry `[layout] default_branch` and `[interaction] autopilot` into the
  configuration table of the Folders & Files guide and deck.

### Fixed

- On Windows, the CLI and CodeGraph no longer run a `git.exe` or `taskkill.exe`
  placed in the repository; both now start programs found on PATH outside it.

## [0.13.0] - 2026-09-10

### Added

- Project-owned project/environment context scaffolds and compact resume pointers.

### Changed

- Align planning and user guides with current context behavior and keep dated
  verification history in task/build records; refresh installation PDFs.
- Keep project, component, and active behavior documentation current and positive;
  record proposals and investigation history in draft/task records.

- Default to a user choice checkpoint after every workflow stage, with optional
  project-configured autopilot that never bypasses publication approval.

## [0.12.0] - 2026-09-08

### Added

- Add test command previews and opt-in refusal of full-suite fallback, plus
  compact evolution responses that preserve complete saved evidence.

### Fixed

- Broaden unsupported test-name selectors to validated file references without
  interpolating their text into shell commands.

### Changed

- Prefer project-native focused build tests and one final full validation;
  omit template-only scaffold notes and repeated stage instructions.

- Make task journals compact progress-and-evidence ledgers by consolidating
  verification and excluding routine tool activity and duplicated artifacts.

## [0.11.0] - 2026-09-04

### Added

- Add a read-only `components` command that lists component knowledge titles
  and paths for low-context navigation.

### Changed

- Limit `DEVIATION` notices to material scope, implementation, contract, or
  verification departures; corrected internal tool errors are operational detail.

- Turn component knowledge pages into concise implementation routes with
  selection signals, boundaries, invariants and focused change-and-test seams.

## [0.10.0] - 2026-09-03

### Added

- Added portable Claude Code AEGIS plugin resources, bounded context hooks,
  local MCP tools and Windows/Linux owned lifecycle.

- Portable Pi and Qwen Code AEGIS extensions with native tools/commands,
  independent review support and configuration-preserving Windows/Linux setup.

- Portable OpenCode and Codex integrations with AEGIS agents/skills, independent
  review roles, safe local installation and shared tracked verification.

### Changed

- Strengthen Frame, Specify and Design with evidence classification, durable
  idea capture, behavior-coverage checks, concrete verification guidance, and
  complexity-proportionate design that keeps proposals separate from current
  component knowledge.

- Align the root overview and planning documents with the core workflow, five
  host integrations, package ownership and verified implementation limits.

## [0.9.1] - 2026-09-02

### Added

- Read-only `trace` command exports the complete requirement register as Markdown
  or CSV, with coverage, ownership, verification, tests and affected paths.

### Fixed

- Use the configured Python runtime for this repository's impacted tests.

## [0.9.0] - 2026-08-31

### Added

- Added optional one-level child tasks, deterministic bounded briefs, and durable rulings and handoffs for coordinated offline work.
- Added optional independent review verdicts with configurable bounded fix and re-review cycles.

## [0.8.0] - 2026-08-28

### Added

- Read-only `summary` command for compact recorded stage reports, with explicit
  missing/stale state and visible output limits.
- Optional documentation layout globs avoid stray-file warnings while keeping
  documentation in secret scanning.

### Changed

- Standardize stage reports and summary-first resume instructions for limited
  context, preserving existing approvals and full validation requirements.

## [0.7.2] - 2026-08-22

### Fixed

- The delivery report harvests a deviation only where the marker carries a
  real workflow stage (`DEVIATION <stage>: ...` or its ` - ` spelling). 0.7.1
  accepted any word after the marker, so ordinary prose about deviations - and
  a journal quoting the marker itself - was listed in the report as recorded
  judgement.

- The delivery report no longer drops a deviation written on a line of its
  own. 0.7.1 harvested only `- ` bullets, so the exact unbulleted shape
  `AGENTS.md` prints in its own contract block was invisible to `report`.

- `diagram` and `explain` now classify coverage by the outcome `check` reaches
  for the same record, through one shared classifier rather than a second
  reading. 0.7.1 pivoted on whether a linked file existed while `check`
  pivoted on whether `linked_tests` was non-empty, so a requirement whose only
  linked test had been deleted was drawn as deliberate hand-verification, and
  a draft was drawn as an uncovered behavior.

### Added

- Two coverage classes, so each one maps onto a single `check` outcome:
  `broken` for a requirement whose linked test does not resolve, matching the
  `no-linked-tests` warning, and `draft` for a record `check` is deliberately
  silent about. The `diagram` CLI reference now tabulates every class against
  the finding it stands for.

### Changed

- Clarify that AEGIS governs software development only; repository and
  package or delivery operations follow the repository's own procedures.

- Produce separately named Windows ZIP and Linux tar.gz delivery archives.

## [0.7.1] - 2026-08-22

### Fixed

- `explain` now matches a directory against its own trailing-slash
  `affected_paths` entry, instead of calling the governed directory ungoverned.

- `explain` normalizes `.` and `..` segments in a relative path, so equivalent
  spellings of one file give one answer, and rejects a path that escapes the
  repository or carries a drive letter the platform did not read as absolute.

- The delivery report harvests only marker-shaped deviations
  (`DEVIATION <stage> - ...`), not sentences that mention the word, and no
  longer re-counts its own earlier reports on a second run.

- Wrapped `## Done checklist` items are rejoined when a journal is parsed, so
  `report` and `status` no longer cut an item at the line break.

- `diagram` calls a requirement tested only when its linked test file exists,
  the same judgement `check` makes, and gives colliding component names
  distinct Mermaid subgraph ids.

- `diagram --component` with `--task` now exits 1 with one error line, matching
  the documented exit behavior for an expected CLI error.

- Repaired a corrupted Windows path example in the `explain` CLI reference.

## [0.7.0] - 2026-08-21

### Added

- Add the `explain` command: given a repository path it reports every
  requirement whose `affected_paths` cover it, grouped under the component
  whose knowledge page claims each one, with status, coverage and spec, then
  the task journals that list them. A directory entry covers the files
  beneath it, absolute and native-separator paths are accepted, and a path no
  requirement covers is stated plainly - and called a finding when it sits
  inside the configured source or test globs. The register was written once
  per behavior and read almost never because nothing led from code back to
  it; this is that direction.

- Carry each component's architecture in its knowledge page. The component
  template gains an `## Architecture` section holding a Mermaid diagram of
  that component's own logic; adoption draws one per component while its
  source is still open, `design` revises it to the shape the change will
  produce and labels it as intended, and `validate` reconciles it with the
  built code and drops that label. Authored rather than derived, so it works
  in any language and can show a shape that does not exist yet.

- Add the `diagram` command: it draws the requirement register as a Mermaid
  flowchart, grouping each requirement under the component whose knowledge
  page claims it and coloring it by whether a linked test, a declared
  `Manual:`/`Inspection:` method, or nothing yet verifies the behavior.
  Requirements no page claims are grouped apart instead of dropped, so an
  unclaimed behavior is visible rather than absent. `--component` and
  `--task` narrow the picture, which a register past a few dozen entries
  needs; `--out` writes UTF-8 explicitly, because a console under a legacy
  code page mangles the characters on the way out. Everything drawn is read
  from files already in the repository: no model, no network, no renderer.

### Changed

- Lead the delivery report with the deviations the task recorded, above the
  diff size and check totals, and say plainly when none were recorded. A
  warning count tells an approver how much happened, never which judgement
  calls were made on their behalf, and the delivery checkpoint is the one
  moment the workflow guarantees a human is reading.
- Rejoin wrapped log lines when parsing a journal, so a deviation survives the
  margin and `status` stops printing half-sentences.

## [0.6.0] - 2026-08-18

### Added

- Add deviation notices to the interaction modes: the agent now states an
  anomaly in the conversation at the moment it records one, as a single
  `DEVIATION <stage>:` line, instead of leaving the journal to reveal it at
  the delivery checkpoint. A notice never pauses the work, waits for no
  reply, and is not suppressed by autopilot. The build, validate and deliver
  steps name the points that raise one - an accepted `check` warning, a
  non-zero exit or a skipped verification, an unexpected `anchor` or
  `evolution` report, a manual method standing in for an automatable test, a
  retired requirement, and unrequested work found in diff review - and
  delivery still presents every deviation in full, because a notice informs
  but never approves.

### Changed

- Carry the deviation notice into the digest `init` writes into `CLAUDE.md`,
  `AGENTS.md` and `QWEN.md`. The digest is what an agent acts on when it reads
  nothing else, so omitting the rule there would have left every downstream
  repository silent by default.
- Update the user guides for deviation notices: the FAQ gains a "What is a
  `DEVIATION` line?" entry and separates the agent's spoken judgement from
  `check`'s own `WARN`/`NOTE` findings, the checkpoint and autopilot
  walkthroughs now show a notice arriving mid-run, and the autopilot guidance
  states that it suppresses the frame stop but never the notices.

### Fixed

- Clear the repository lint failure so `check --strict --run` exits 0. The
  payload gains explicit `check=False` on the two `subprocess.run` calls that
  already read `returncode`, a single `startswith` tuple, parenthesized
  implicit string concatenations, `re.MULTILINE` in place of `re.M`, and
  sorted imports; no behavior changes. Two findings are suppressed with a
  stated reason rather than "fixed": the journal date stays on the local
  calendar, and the capture sink is a deliberately long-lived handle.

## [0.5.0] - 2026-08-14

### Added

- Add advisory `anchor` and `evolution` commands that fingerprint Git-visible
  repository files around implementation, retain compact timestamped change
  reports, and add NOTE-only scoped-task guidance when records are missing.
- Add Git availability and repository detection to `init`, with explicit
  opt-in repository creation through `init --git`.

### Changed

- Consolidated the repository around AEGIS. The former lightweight package,
  documentation, workflow markers, and release record now use the AEGIS name.

### Fixed

- Treat Boolean command timeout values as invalid instead of converting
  `true` into a one-second limit.
- Apply `[check] ignore` to unscanned secret-diff gaps, and scan added content
  lines beginning with two literal plus signs.
- Keep impacted-test selection and repository evolution stable when Python
  creates `.pyc`/`.pyo` files or `__pycache__/` directories under source roots.
- Restore `validate` to the quick-path sequence in the frame-stage guidance.
- Flush the `test` command announcement before child output, identify malformed
  journals by filename in human status output, and correct small workflow and
  CLI reference inconsistencies.
- Migrate legacy `AEGIS-LIGHT` managed guidance markers during `init` and
  collapse duplicate old/new blocks left by an interrupted upgrade.

## [0.4.0] - 2026-08-14

### Added

- Advisory task workflow with requirements, specifications, knowledge pages,
  structured checks, focused test selection, and machine-readable reporting.
