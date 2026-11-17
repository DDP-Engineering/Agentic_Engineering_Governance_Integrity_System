# Changelog

All notable changes to AEGIS are documented in this file.

## [Unreleased]

## [0.16.1] - 2026-11-17

### Fixed

- Read the diff as a plain patch in `check`: with `color.ui=always` or
  `diff.external` set, `secret-in-diff` saw no added lines and stayed silent.
- Drop the removed `advance --path` option and `path:` header line from the
  feature example, the folders guide, the FAQ and the package README.
- Report a pointer file or `.gitignore` that is not UTF-8 as one `init` error
  line naming the file, instead of a traceback.
- Give the OpenCode tools the `no_fallback` and `compact` arguments the other
  hosts already offer and its prompt asks for.
- Keep a `task` title on one line, so a line break in it cannot add header
  fields to the new journal.
- Accept every review round `max_fix_cycles` allows: `verdict`, the State and
  the host adapters stopped at round 6 whatever the configured bound.
- Ship release archives whose documents link only to files in the archive:
  the builder writes the archive README, adds `CHANGELOG-archive.md` and
  reduces links to separately delivered material to their text.
- Fingerprint an uninitialised submodule by the commit the index records;
  `anchor` stored the superproject's HEAD and `evolution` reported a change
  after every commit.
- Keep a finished verification job's exit code and release the checkout lock
  when its closing fingerprint cannot be taken (`candidate_error` says why).
- Restore LF line endings in 32 working-tree files that had drifted to CRLF.
- Correct guide and payload wording that disagreed with the CLI: `explain` on an
  uncovered path, exit codes, review fail-safes, `default_branch`, the settings
  reference and the summary field names.

### Removed

- Drop two `AGENTS.md` rules that named a template changelog and template
  adapter folders this repository does not have.

### Added

- Add `02_Tools/build_aegis_delivery.py`, which archives the host packages and
  the guides and writes the delivery records.

Older releases are in [CHANGELOG-archive.md](CHANGELOG-archive.md).
