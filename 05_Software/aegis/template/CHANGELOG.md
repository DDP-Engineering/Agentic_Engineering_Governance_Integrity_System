<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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
