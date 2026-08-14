<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to AEGIS are documented in this file.

## [Unreleased]

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

## [0.4.0] - 2026-08-14

### Added

- Advisory task workflow with requirements, specifications, knowledge pages,
  structured checks, focused test selection, and machine-readable reporting.
