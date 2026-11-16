# Changelog

All notable changes to AEGIS are documented in this file.

## [Unreleased]

## [0.16.0] - 2026-11-16

### Removed

- Remove the quick path and `advance --path`; every task walks one stage order,
  and an older journal's `path:` line no longer changes it.

### Added

- Add an admission rule: AEGIS governs durable product rules only; bug fixes,
  local UI adjustments and refactors are made directly, without a journal.
- Add the `context-size` (`[context] page_kb`: `init` writes 24, no setting
  means no budget) and `duplicate-heading` checks for context and knowledge pages.
- Add the direct-changes guide and slide deck, replacing the quick-fix guide.
- Add `REUSE.toml`, which declares the repository's licensing in one place.
- Add `01_Documentation/Releases.md` for versions and the changelog; older
  releases move to `CHANGELOG-archive.md`.

### Changed

- Run `uncovered-source` only with `check --task`, since direct changes need
  no requirement; `explain` no longer calls an uncovered path a finding.
- Make frame record the requirements that already cover the work, so specify
  can be skipped for them.
- Shorten the payload license header to a two-line SPDX tag; other files drop
  their license header.
- Stop stating the current version in guides, decks and installation PDFs;
  `aegis.py --version` prints it.
- Point the root `CLAUDE.md` and `QWEN.md` at `AGENTS.md` instead of repeating
  a workflow digest.
- Slim the code style (no banners, section markers or `@` docstring tags; add
  JavaScript rules) and apply it to the existing Python code.

Older releases are in [CHANGELOG-archive.md](CHANGELOG-archive.md).
