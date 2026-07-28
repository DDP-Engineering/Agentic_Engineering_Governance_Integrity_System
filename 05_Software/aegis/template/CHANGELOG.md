<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.4.1] - 2026-07-28

### Fixed

- **`.codex/hooks.json` was rejected wholesale by Codex, leaving every guard
  absent on that host.** Codex parses the file with a strict deserializer that
  accepts exactly two top-level keys, `description` and `hooks`; the three
  `_legal`/`_comment*` annotation keys the file carried made it fail with
  ``unknown field `_legal` ``. A rejected hooks file registers *no* hooks at
  all, so the read guard, write-zone guard, secret scan, shell-write guard,
  delivery preflight, and evidence recorder were all silently inactive under
  Codex — tool calls were not blocked, they were never inspected. The file now
  carries a single short `description`; the annotation prose moved to
  `.codex/README.md` and `.agentic/hooks/README.md`. The hook wiring itself is
  unchanged and was already schema-valid (`commandWindows` and `statusMessage`
  are supported Codex fields, and `Bash` is the name Codex gives its shell tool
  in hook events).

### Added

- `.codex/README.md`, documenting the Codex adapter and the two host gates that
  must be cleared before guards run.
- `.agentic/hooks/README.md` gained a "Codex requires trust before hooks run"
  section: Codex loads project-local hooks only for a trusted project, and then
  runs each hook only after it has been reviewed in the `/hooks` panel. Hook
  trust is keyed to the file's content hash, so an AEGIS payload upgrade that
  changes `.codex/hooks.json` returns those hooks to "review required" and they
  stop running until re-reviewed.

### Changed

- `.pi/README.md` no longer claims project trust is "the one behavioral
  difference from the Codex and Claude adapters". Codex requires both a project
  trust step and a per-hook review; only Claude Code needs neither.

## [1.4.0] - 2026-07-25

### Added

- Requirement snapshots carry an optional `spec_ref` naming a companion
  specification file (data structures, interface/message formats, exact dialog
  and copy text, example payloads, worked acceptance examples) so an
  implementation cannot drift from what was analysed while the `requirement`
  sentence stays a single testable behavior. `requirement create` accepts
  `--spec-ref <path>` and `requirement update` accepts `--spec-ref`/
  `--clear-spec-ref`. A non-empty `spec_ref` must resolve to an existing file at
  write time; a later-deleted target is reported as `REQ-SPEC-MISSING` by
  `audit traceability`. Ships `.agentic/requirements/spec_template.md`.
- `resume` command: prints a compact, read-only bootstrap brief (current stage
  and computed next stage, intent, alignment, spec items, checks, recent active
  evidence, and the run's cited requirements resolved with their `spec_ref`) so a
  fresh agent session continues an existing run without prior chat context. The
  `agentic-development` skill gained a matching "Session Resume" step.

### Changed

- **Hard break:** the requirement snapshot schema gains a required `spec_ref`
  key (empty string when unused); snapshots written before this change are
  rejected rather than migrated. The `schema_version` stays `1` — the field
  tracks released format generations, and nothing has been released yet, so it
  is bumped only at the first real release that must migrate live data.
- `agentic-development` and `agentic-adoption` skills restructured into thin
  routers that dispatch to per-stage modules under `reference/` (development:
  intake, alignment, requirement, check, implementation, validation; adoption:
  adoption-intake, adoption-alignment, repo-discovery, component-map,
  component-adoption, baseline-review, adoption-delivery). A session — including
  a resumed one — loads only the current stage's module instead of the whole
  workflow, cutting the always-loaded footprint for small-context runners.

## [1.3.0] - 2026-07-25

### Added

- `guard_shell_write.py`: a pre-tool hook that extends the configured write-zone
  and protected-path policy to file writes performed through the shell
  (`Bash`/`run_shell_command`). It recognizes the common, reliably detectable
  write forms — output redirection (`>`/`>>` and file-descriptor variants),
  `tee`, `cp`/`mv`/`install`, `dd of=`, and `sed -i` — and enforces only on
  targets inside the repository, so writes to `/tmp`, `/dev/null`, and other
  external paths are unaffected. Wired into every adapter's shell matcher
  (Claude Code, Codex, Qwen Code, OpenCode, Pi). This closes a gap where
  `guard_write_zone.py`, wired only to the dedicated editing tools, did not see
  a repository file written via a shell redirection or copy. Best-effort by
  design: the delivery working-tree audit remains the backstop for the tree
  itself. The hook launcher's Node.js requirement is now documented in
  `.agentic/hooks/README.md`.

### Changed

- `INV-7` (clean secrets) also scans `git diff --cached`, so a secret in a
  staged-but-never-committed file in a repository with no `HEAD` yet is caught.
- `secret_scan.py` serializes scanned input with `ensure_ascii=False`, so a
  configured pattern can match a secret containing non-ASCII characters.

### Fixed

- `working_tree` only splits a Git status entry on `" -> "` for rename/copy
  records, so a file whose own name contains that sequence is not misparsed.
- `run.sh` folds a registered runtime path to forward slashes, so a Windows
  interpreter path resolves reliably under Git Bash.

### Removed

- The unused `aegis.paths.is_allowed_path` helper; policy consumers compose
  `relative_to_root`/`contained_relative_path` with `matches_pattern` directly.
