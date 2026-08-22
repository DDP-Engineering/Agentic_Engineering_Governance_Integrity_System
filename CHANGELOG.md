<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to AEGIS are documented in this file.

## [Unreleased]

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
