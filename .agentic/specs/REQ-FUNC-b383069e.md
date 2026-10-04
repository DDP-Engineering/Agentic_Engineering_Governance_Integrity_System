<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-b383069e - Dispatch knowledge-graph queries to the plugin

This spec is the dispatch and configuration contract between the AEGIS CLI and
the CodeGraph plugin. It is also referenced by REQ-FUNC-b303507f,
REQ-FUNC-8b15c62d, REQ-FUNC-f5d5ee3d, REQ-SEC-c7e64a0e, REQ-REL-53d13fb2,
REQ-REL-0e1c6d89, REQ-FUNC-e780b270, REQ-FUNC-d1994267, REQ-FUNC-48ff6d8e,
REQ-SEC-68f1bb5d, REQ-FUNC-baa92928, REQ-FUNC-43a76b41 and REQ-FUNC-3a18929b.
The response envelope itself is defined in `specs/REQ-FUNC-8cb1a3b7.md`.

## Behavior

### Commands

| AEGIS command | Plugin operation | Positional target | Time limit key |
|---|---|---|---|
| `know_graph` | `status` | none | `timeout_seconds` |
| `know_graph_check` | `check` | none | `check_timeout_seconds` |
| `know_graph_find NAME` | `find` | name text | `timeout_seconds` |
| `know_graph_file PATH` | `file` | repository path normalized by the core's `repo_path_arg` | `timeout_seconds` |
| `know_graph_symbol ID` | `symbol` | symbol ID or prefix | `timeout_seconds` |
| `know_graph_callers ID` | `callers` | symbol ID or prefix | `timeout_seconds` |
| `know_graph_refs ID` | `refs` | symbol ID or prefix | `timeout_seconds` |
| `know_graph_index [--rebuild]` | `index` | none | `index_timeout_seconds` |

Every command accepts `--json`. `know_graph_find`, `know_graph_file`,
`know_graph_callers` and `know_graph_refs` also accept `--limit N`,
`--max-bytes N` and `--page TOKEN`; `know_graph_symbol` accepts `--limit N` and
`--max-bytes N`. An option a command does not accept is an argparse usage
error (exit 2) and starts nothing.
`know_graph_index` accepts `--rebuild` and `--json`. A missing required target
is an argparse usage error (exit 2) and starts nothing.

### Dispatch sequence

1. Load `.agentic/aegis.toml`. If `[codegraph]` is absent or `enabled` is not
   `true`, print the core-produced `disabled` response (reason `not_enabled`)
   and exit 0. Nothing else happens.
2. Validate the core-owned keys (table below). An invalid value is a one-line
   error and exit 1.
3. Resolve `database` against the root and validate it (see "Database path").
   A violation is a one-line error naming `[codegraph] database` and exit 1.
4. If `<root>/.agentic/plugins/codegraph/codegraph.py` is not a file, print the
   core-produced `unavailable` response with reason `plugin_missing` and exit 0.
5. Build the argument array and start the plugin (see "Plugin command line").
6. Read standard output up to the output cap while waiting up to the time limit
   (see "Bounded execution").
7. Validate the response (see "Validation") and print it: with `--json` the
   plugin's JSON document unchanged; otherwise the envelope's `text` field.
8. Exit with the mapped code (see "Exit codes").

Commands other than the eight above never read `[codegraph]` beyond the
advisory shape check of `check`, never start the plugin and never open the
database.

### Plugin command line

```text
<sys.executable> -I -B -X utf8 <root>/.agentic/plugins/codegraph/codegraph.py
    <operation>
    --root <absolute root>
    --config <absolute root>/.agentic/aegis.toml
    --database <absolute database path>
    --protocol 1
    (--json | --text-envelope)
    [--limit N] [--max-bytes N] [--page TOKEN]
    [--rebuild] [--watch-stdin] [--deadline SECONDS]
    [-- <target>]
```

- The core passes `--json` when the operator asked for JSON, and
  `--text-envelope` otherwise; in both cases the plugin answers with one JSON
  envelope on standard output, carrying either `results` or `text`.
- `--watch-stdin` is passed for `index` only. `--deadline` is passed for
  `check` and `index` when their limit is positive, set to 80% of that limit
  so the plugin's own answer (for example freshness `unknown`) arrives before
  the core has to stop it.
- The target always follows `--`, so a target starting with `-` is data.
- `shell=False`; the working directory is the root. On POSIX the plugin starts
  in a new session (`start_new_session=True`), the prerequisite of `kill_tree`.

### Bounded execution

- Read operations: standard input is `DEVNULL`; standard error is collected up
  to 4 KiB and shown only in a failure message.
- `index`: standard input is a pipe the core holds open until it exits and
  never writes; standard error is inherited so progress reaches the operator.
- Standard output is read on a separate thread into a buffer limited to
  `OUTPUT_CAP = 65536` bytes. Reaching the cap stops reading, terminates the
  plugin's tree with `kill_tree`, and fails with
  `error: CodeGraph output exceeded 65536 bytes`.
- When the time limit expires, the core terminates the plugin's tree with
  `kill_tree`, waits for it, and fails with
  `error: CodeGraph <operation> stopped after <N>s time limit`.
- The tree is killed before the core waits for the plugin, so on POSIX its
  process group is still reachable. When `kill_tree` reports that the tree could
  not be killed and either the plugin is still running or a descendant still
  holds its standard output, the message adds
  `; some of its child processes may have survived`, and a pipe that a
  surviving descendant still holds is left to process exit rather than closed,
  so the core never waits on it.
  `index_timeout_seconds = 0` means no limit.
- Neither failure touches the database folder.

### Validation

Standard output must decode as UTF-8 and parse as exactly one JSON object with
`schema == 1`, `provider == "codegraph"`, `protocol == 1`, `action` equal to the
requested operation and `status` from the protocol vocabulary; without
`--json` the envelope must also carry the `text` view. Empty standard output
is reported as `error: CodeGraph failed without an answer: <last line of the
plugin's standard error>`. Any other violation
prints `error: CodeGraph protocol failure: <what>` on standard error, nothing on
standard output, and exits 1.

### Exit codes

| Response | Exit |
|---|---|
| `status` `ok`, `ambiguous`, `not_found`, `expired`, `unavailable`, `disabled` | 0 |
| `status` `error` | 1 |
| invalid configuration, database path, time-out, output cap, protocol failure, failed launch | 1 |
| argparse usage error | 2 |

The standalone plugin uses the same mapping for its own exit code.

## Data / interface

### `[codegraph]` configuration

| Key | Type | Default | Validated by | Rule |
|---|---|---|---|---|
| `enabled` | bool | `false` | core | only `true` enables |
| `database` | string | `.agentic/knowledge/codegraph/codegraph.sqlite` | core and plugin | see "Database path" |
| `max_results` | int | `20` | core | 1 to 200 |
| `max_output_bytes` | int | `8192` | core | 512 to 32768 |
| `timeout_seconds` | int | `5` | core | positive |
| `check_timeout_seconds` | int | `30` | core | positive |
| `index_timeout_seconds` | int | `0` | core | zero or positive; 0 means no limit |
| `include` | list of strings | `[]` | plugin | layout patterns |
| `exclude` | list of strings | `[]` | plugin | layout patterns; wins over `include` |
| `include_untracked` | bool | `true` | plugin | |
| `index_tests` | bool | `true` | plugin | |
| `python_import_roots` | list of strings | `[]` | plugin | repository-relative folders |
| `max_file_bytes` | int | `1048576` | plugin | positive |
| `parse_timeout_seconds` | int | `10` | plugin | positive |

Core-validated keys join `CONFIG_SHAPE`, so `check` reports a wrong type as a
`config` warning and the default config documents them, commented out.

### Database path

The resolved path must be `<root>/.agentic/knowledge/codegraph/NAME.sqlite`,
where `NAME` matches `[A-Za-z0-9_-]+`. Resolution follows symlinks and
junctions on every existing component; the resolved parent must equal
`<resolved root>/.agentic/knowledge/codegraph`, so a link that moves the storage
folder or the database elsewhere is rejected. The folder itself need not exist
yet.

### Scope selection

- Matching reuses the AEGIS rules exactly: an entry ending in `/` matches that
  folder and everything under it; an entry containing `*`, `?` or `[` matches
  with case-sensitive `fnmatchcase` over the whole path; any other entry
  matches the exact path or the folder of that name.
- Selected = matches (`layout.source` or, when `index_tests`, `layout.tests` or
  `include`) and matches none of `exclude`, the built-in exclusions, or the
  installed root `.agentic/` (any path starting with `.agentic/`).
- Built-in exclusions are any path component equal to `.git`, `node_modules`,
  `__pycache__`, `.venv`, `venv`, `.tox`, `.mypy_cache`, `.pytest_cache`,
  `.ruff_cache`, `dist`, `build`, `.eggs`, or ending in `.egg-info`.
- Role is `test` for files matching `layout.tests`, otherwise `source`.
  Language is `python` for `.py` and `.pyi`; other selected files are
  inventoried as `unsupported`. `pyproject.toml` and `setup.cfg` are manifests.
- Skip reasons: `too-large` (over `max_file_bytes`), `binary` (a NUL byte in
  the first 8 KiB), `unsupported`. Excluded files are simply not selected.
- When nothing can be selected - `layout.source` and `include` empty or
  absent, and `layout.tests` empty, absent or switched off by
  `index_tests = false` - `scope` and `check` return status `unavailable` and `index` returns status
  `error` (every `index` outcome other than a published generation is an
  error), each with reason `scope_missing`, a message suggesting `[layout]` or
  `include`, and no file written.

### Inventory

- `git rev-parse --is-inside-work-tree` run in the root decides the mode. Git
  missing, or the root not inside a work tree, selects the filesystem walk.
- Git mode lists `git ls-files --cached -z` plus, when `include_untracked`,
  `git ls-files --others --exclude-standard -z`, and omits paths missing on
  disk. A failing listing returns status `error` with reason `inventory_failed`.
- Filesystem mode walks only the literal leading folders of the selection
  patterns (the root for a pattern starting with a wildcard), pruning built-in
  exclusions, and reports `inventory=filesystem`.

## Examples

```text
python .agentic/aegis.py know_graph_find OrderRepository
-> <python> -I -B -X utf8 <root>/.agentic/plugins/codegraph/codegraph.py find
   --root <root> --config <root>/.agentic/aegis.toml
   --database <root>/.agentic/knowledge/codegraph/codegraph.sqlite
   --protocol 1 --text-envelope -- OrderRepository

python .agentic/aegis.py know_graph_find -- -weird
-> ... find ... --text-envelope -- -weird

[codegraph] database = "src/index.sqlite"
-> error: [codegraph] database must be a NAME.sqlite file directly inside .agentic/knowledge/codegraph/   (exit 1)
```

## Acceptance

- Every row of the command table dispatches as specified, verified with a
  recording stub.
- Disabled, plugin-missing, invalid-path, time-out, output-cap and
  protocol-failure cases produce the specified output and exit codes and start
  no process where specified.
- Core-validated keys appear in `CONFIG_SHAPE` and, commented, in the default
  configuration.

## Assumptions and open decisions

- `OUTPUT_CAP` of 64 KiB leaves room for a 32 KiB response plus envelope and
  JSON escaping; build may lower it if measurements show a tighter bound.
- The filesystem walk follows no symlinked folders.
