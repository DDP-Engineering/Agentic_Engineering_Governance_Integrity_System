<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-REL-1eeb1914 - Publish each index generation atomically

This spec defines CodeGraph's storage folder, write preconditions, locking,
publication, recovery, rebuild and cancellation. It is also referenced by
REQ-FUNC-7e74dacf, REQ-SEC-57e210bb, REQ-SEC-135c0df0, REQ-REL-6f924213,
REQ-REL-b96977c7, REQ-REL-4277bfc7, REQ-REL-bd1529a5, REQ-REL-0858819d,
REQ-REL-10dc6424 and REQ-SEC-db558433.

## Behavior

### Storage folder

All CodeGraph writes happen in `<root>/.agentic/knowledge/codegraph/`:

| File | Purpose |
|---|---|
| `NAME.sqlite` | The database (default `codegraph.sqlite`). |
| `NAME.sqlite-journal` | SQLite's rollback journal, present only during or after an interrupted write. |
| `codegraph.lock` | The writer lock file; created once, never deleted, renamed or recreated by indexing. |
| `.codegraph-rebuild-<16 hex>.tmp` and its `-journal` | A rebuild in progress. |

The plugin never writes Python bytecode: AEGIS starts it with `-B`, and the
entry point sets `sys.dont_write_bytecode = True` before importing its own
modules when started without it.

### Indexing sequence

Every `index` run, incremental or rebuild, performs these steps in order:

1. **Paths and configuration.** Validate the database path and settings. No
   filesystem change.
2. **Git state and scope.** When `git rev-parse --is-inside-work-tree` succeeds in the
   root, `git check-ignore -q` must report the database file, the lock file
   and a temporary-file name as ignored, and `git ls-files -z` for the storage
   folder must be empty. Otherwise return `error` with reason
   `destination_not_ignored` or `destination_tracked` and a message naming the
   remedy (add the ignore rule, or `git rm --cached` the listed files). No
   filesystem change. Without Git, or outside a work tree, this step is
   skipped. A configuration that can select nothing returns `scope_missing`
   here too, before anything is created.
3. **Writer lock.** Create the storage folder if needed, open `codegraph.lock`
   (creating it if absent) and take an exclusive non-blocking lock:
   `msvcrt.locking(fd, LK_NBLCK, 1)` on byte 0 on Windows,
   `fcntl.flock(fd, LOCK_EX | LOCK_NB)` on Ubuntu. Failure returns `error`
   with `index` `busy`. The descriptor is not inheritable, and extraction
   workers start with the `spawn` method, so no child shares the lock.
4. **Ownership.** If the database file exists, read its first 100 bytes. It
   must start with `SQLite format 3\0` and carry `application_id`
   `0x43474731` (big-endian at offset 68). Otherwise return `error` with
   reason `foreign_database` and leave the file untouched.
5. **Plugin identity.** Record the plugin-content identity: SHA-256 over the
   sorted list of (relative path, size, SHA-256 of content) for every file in
   the plugin folder except `__pycache__`, `.pytest_cache` and `.ruff_cache`
   folders and `.pyc` files.
6. **Inventory and cleanup.** Select the files to index, and delete any
   `.codegraph-rebuild-*` file a killed build left behind; holding the lock
   makes them stale.
7. **Recover, update or build** as below. An existing database with a
   supported schema is updated in place; a missing database, an unsupported
   schema and `--rebuild` all take the rebuild path, so an interrupted first
   build leaves no file at the target.

The lock is released when the run ends or its process exits for any reason.

### Incremental update and publication

- Open the database read-write (`journal_mode=DELETE`, `synchronous=FULL`).
  Opening it lets SQLite roll back a hot journal: that is recovery. Nothing
  deletes a journal file by hand.
- An unsupported `user_version` (schema) switches to the rebuild path.
- Inventory, hash and extract outside any database transaction.
- Publish in one `BEGIN IMMEDIATE` transaction: replace the facts of changed,
  failed, deleted and excluded files, insert new files' facts, re-resolve
  candidate links against the whole symbol inventory, write the input
  manifest (file hashes, manifest hashes, configuration digest, extractor
  revisions), a new random 128-bit snapshot ID, the incremented generation
  and the publication time.
- Immediately before `COMMIT`, recompute the plugin identity; a difference
  rolls back and returns `error` with reason `plugin_changed`.
- Cancellation is checked again after re-resolution, before the manifest is
  written. Any failure or cancellation before `COMMIT` rolls back; the previous
  generation stays readable.

### Rebuild

Triggered by `--rebuild`, an unsupported schema or a missing database. The new
generation number continues from the replaced database's, when it is readable.

1. Build into `.codegraph-rebuild-<16 hex>.tmp` with `application_id` set
   first, commit, close, and validate (`PRAGMA integrity_check` returns `ok`,
   application ID and `user_version` match).
2. If the target exists (already ownership-checked), open it read-write once so
   SQLite recovers any hot journal, then close it.
3. A journal still beside the target after that open (the file is damaged,
   SQLite did not treat the journal as hot, or the database file is already
   gone) belongs to a file that is being discarded: delete it before step 4.
4. `os.replace(temporary, target)`. On Windows a sharing conflict with an open
   reader is retried up to 20 times at 100 ms intervals; still failing returns
   `error` with reason `replace_failed`.
5. On any failure, delete the temporary file and its journal and keep the old
   database.

### Readers

- Open with a URI built from the absolute path (`Path.as_uri()` plus
  `?mode=ro`), `uri=True`, then `PRAGMA query_only=1` and a 200 ms busy
  timeout. A missing file is reported as `index` `missing` without opening it.
- `SQLITE_READONLY_ROLLBACK` (via `sqlite3.Error.sqlite_errorname`) maps to
  `needs_recovery`; `SQLITE_BUSY` and its extended codes to `busy`; a header
  without the CodeGraph application ID, or an unsupported `user_version`, to
  `incompatible`.
- Readers serve the last committed generation while an indexer extracts,
  builds a temporary database or holds SQLite's RESERVED lock.

### Cancellation

- With `--watch-stdin`, a daemon thread reads a private duplicate of standard
  input until end-of-file and then sets the run's cancellation event; standard
  input itself is redirected to the null device first, so no child process
  (Git, extraction workers) inherits the watched pipe.
- With `--deadline S`, the event is set S seconds after the run started.
- The event is checked between files, while waiting for an extraction
  worker and after re-resolution; on cancellation the indexer terminates its workers. A cancelled run
  rolls back and returns `error` with reason `cancelled` or `deadline`.

## Data / interface

| Constant | Value |
|---|---|
| SQLite `application_id` | `0x43474731` |
| SQLite `user_version` (schema) | `1` |
| Reader busy timeout | 200 ms |
| Windows replace retries | 20 at 100 ms |

## Examples

- A run starting while another holds the lock returns
  `{"status": "error", "index": "busy", "reason": "busy"}` at once.
- Killing an indexer after it inserted facts but before `COMMIT` leaves a hot
  journal; `find` then returns `unavailable` with `index` `needs_recovery`, and
  the next `index` recovers and publishes.

## Acceptance

- Steps 1 and 2 leave the filesystem unchanged when they refuse.
- Concurrency, interruption, recovery, rebuild and cancellation fixtures behave
  as specified on Windows and Ubuntu.
- A full-tree comparison shows that only the storage folder changes.

## Assumptions and open decisions

- Confirmed on Windows and Ubuntu: a read-only connection reports a hot
  journal as `SQLITE_READONLY_ROLLBACK`, and a read-write open rolls it back.
- Confirmed on Windows and Ubuntu: `git check-ignore` reports a file inside an
  ignored folder as ignored even when the folder does not exist yet.
- The storage folder must be on a local filesystem.
