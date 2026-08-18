<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to AEGIS are documented in this file.

## [Unreleased]

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
