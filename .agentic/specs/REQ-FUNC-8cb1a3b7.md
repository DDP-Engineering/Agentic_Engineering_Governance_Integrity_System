<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-8cb1a3b7 - Report status, index, freshness and capability separately

This spec is the CodeGraph response protocol, version 1. It is also referenced
by REQ-FUNC-29d6c038, REQ-FUNC-e8436251, REQ-FUNC-af6434a9, REQ-FUNC-569a1a97,
REQ-UX-461978be, REQ-FUNC-a8ece064, REQ-FUNC-41815b22, REQ-FUNC-ab604fdb,
REQ-FUNC-a603d692, REQ-FUNC-d6ef4d32, REQ-FUNC-359c2a92, REQ-FUNC-81588d5e,
REQ-FUNC-ff30861f, REQ-NFR-17c50caa, REQ-FUNC-ff8000c4, REQ-PLAT-dc7bdd06,
REQ-FUNC-c88e2b22 and REQ-FUNC-40ac076a.

## Behavior

Every operation writes exactly one JSON object to standard output, except a
configuration error, which is one line on standard error and exit 1. An
unexpected failure is status `error` with reason `internal`. Progress
goes only to standard error, and read operations write nothing to standard
error on success. Three views exist:

- `--json`: the envelope with `results` and `details`; no `text`.
- `--text-envelope` (used by AEGIS): the envelope with `text` holding the
  compact text rendering; `results` and `details` are omitted.
- neither (standalone default): the plugin prints the compact text itself, not
  JSON.

### Envelope

| Field | Type | Meaning |
|---|---|---|
| `schema` | int | Always `1`; shared with the AEGIS JSON envelopes. |
| `provider` | string | Always `"codegraph"`. |
| `protocol` | int | The answered protocol version; `1` here. |
| `plugin_version` | string or null | Version from the plugin's `MANIFEST.json`; null in core-produced responses. |
| `action` | string | The operation: `scope`, `status`, `check`, `find`, `file`, `symbol`, `callers`, `refs`, `index`. |
| `status` | string | Outcome of this request (table below). |
| `reason` | string or null | Machine reason for any non-`ok` status. |
| `message` | string or null | One human line for any non-`ok` status, including the fallback advice. |
| `index` | string or null | Database state (table below); null in core-produced responses and when the plugin refuses the protocol version before reading its configuration. |
| `freshness` | string or null | Freshness (table below); null when no generation exists and in core-produced responses. |
| `indexing_supported` | bool or null | Whether this Python has matching natives; null in core-produced responses. |
| `python_support` | string or null | `tested` or `untested` when `indexing_supported` is true, else null. |
| `snapshot` | string or null | 32 hexadecimal characters of the served generation, or null. |
| `generation` | int or null | Generation counter of the served snapshot, or null. |
| `indexed_at` | string or null | UTC time the served generation was published, ISO 8601 with `Z`. |
| `results` | list | Records for the action (`--json` view). |
| `details` | object | Action-specific fields (`--json` view). |
| `text` | string | Compact text rendering (`--text-envelope` view). |
| `has_more` | bool | More records exist than were returned. |
| `next_page` | string or null | Page token when `has_more` is true and paging applies. |

Core-produced responses are the two the AEGIS core answers without starting
the plugin: `disabled` (reason `not_enabled`) and `unavailable` (reason
`plugin_missing`). Their text view is two lines,
`CodeGraph | <action> | <status> | <reason>` and the message.

### Status values

| `status` | When |
|---|---|
| `ok` | The request was served, including with zero results. |
| `ambiguous` | A name or ID prefix matches several symbols where one was required; `results` lists the choices. |
| `not_found` | Unknown symbol ID, unmatched prefix, or a path that is not indexed. |
| `expired` | A page token from another snapshot. |
| `unavailable` | The index cannot serve the request; `index` and `reason` say why. Also `scope_missing` and `plugin_missing`. |
| `disabled` | CodeGraph is not enabled; produced by the AEGIS core. |
| `error` | The request failed: invalid request, page token from another request, protocol mismatch, inventory failure, corruption, a refused write precondition, cancellation, or a failed indexing run. |

For `index`, every plugin-produced outcome other than a published generation is
`error` (the core's `disabled` and `plugin_missing` answers keep their status); the
`index` field still reports the database state (for example `busy`).

### Index, freshness and capability values

| Field | Value | Meaning |
|---|---|---|
| `index` | `ready` | A compatible completed generation is readable. |
| | `missing` | No database file exists. |
| | `incompatible` | Not a CodeGraph database, or an unsupported schema or extractor revision. |
| | `busy` | SQLite still reports busy after the reader's busy timeout, or another indexer holds the writer lock. |
| | `needs_recovery` | SQLite reports a hot journal a read-only connection cannot roll back. |
| `freshness` | `current` | `check` found the scope identical to the recorded manifest. |
| | `stale` | `check` found differences. |
| | `unknown` | `check` was interrupted, timed out, or sources changed during it. |
| | `not_fully_checked` | Every other operation that serves a generation. |

### Reasons

`not_enabled`, `plugin_missing`, `missing`, `incompatible`, `busy`,
`needs_recovery`, `scope_missing`, `protocol`, `invalid_request`,
`page_token_mismatch`, `not_found`, `ambiguous`, `expired`, `inventory_failed`, `destination_not_ignored`,
`destination_tracked`, `foreign_database`, `plugin_changed`, `cancelled`,
`deadline`, `indexing_unsupported`, `replace_failed`, `internal`.

### Records

- **Symbol**: `id` (32 hex), `kind` (`module`, `class`, `function`, `method`,
  `parameter`, `variable`), `name`, `qualified_name`, `signature`, `path`,
  `start` and `end` (`{"line": int, "column": int}`, both 1-based, columns in
  Unicode code points), `role` (`source` or `test`), `language`, `citation`
  (`current` or `stale`), `display_id` (the shortest unique prefix of at least
  10 characters) and `depth` (nesting below the module).
- **Reference**: `kind` (`call`, `import`, `read`, `write`), `label`
  (`direct-syntax`, `lexical-binding`, `candidate`, `unresolved`, `external`),
  `path`, `line`, `column`, `spelling`, `target` (symbol ID or null),
  `from` (ID of the enclosing symbol or null), `from_display`, `from_name`
  (qualified name of the enclosing symbol, or null with `from`), `citation`;
  on `symbol`, `callers` and `refs` answers `subject` (the full ID of the
  target symbol the record answers for) and `subject_display`; `symbol`
  neighbors add `relation`.

### Actions

| Action | `results` | `details` |
|---|---|---|
| `scope` | none | `patterns`, `inventory`, `totals` (`files`, `bytes`), `by_role`, `by_language`, `skipped` (reason to count), `manifests` |
| `status` | none | `available`, `scope` counts, `languages`, `inventory`, `database_folder` (`ignored`: bool or null, `tracked`: list) |
| `check` | none | `added`, `changed`, `deleted`, `failed`, `manifests_changed` (each bounded), `config_changed` (bool) |
| `find` | symbols in rank order | none |
| `file` | the file's symbols in source order, each with `depth` | `path`, `role`, `language`, `extraction` (`complete`, `partial`, `failed`), `reason` |
| `symbol` | neighbor references, each with `relation` (`caller`, `callee`, `reference`) | `targets`: the number of distinct targets; `symbol`: the symbol record, or with several targets `symbols`: their records in request order |
| `callers` | linked incoming calls | `candidates`: candidate callers; `targets`: the number of distinct targets |
| `refs` | identifier references | `targets`: the number of distinct targets |
| `index` | none | `files` (`indexed`, `reused`, `partial`, `failed`, `skipped`), `symbols`, `references`, `elapsed_ms` |

### Several targets

`symbol`, `callers` and `refs` take one to 20 symbol IDs or ID prefixes;
more than 20 return `error` with reason `invalid_request`. `find` and `file`
take exactly one target.

- Every target is resolved before any record is read, in request order. The
  first target that is malformed, unknown or ambiguous answers for the whole
  request - `error` (`invalid_request`), `not_found` or `ambiguous` with that
  target's choices - and its message names the target.
- Targets that resolve to the same symbol are answered once, at the first
  position.
- Records follow the targets in request order, then the action's own
  ordering. `callers` pages one sequence per target - its linked calls, then
  its candidate calls - and the targets' sequences follow each other;
  offsets count records across all targets.
- `symbol` windows its neighbors across all targets at the limit, as for one
  target, and is not paged.

### Ranking for `find`

Exact qualified name, then exact simple name, then case-sensitive name prefix,
then case-insensitive identifier word (words split on `_` and lower-to-upper
case changes), then path substring. Ties sort by role (`source` first), path,
start line and ID.

### Budgets

- At most `limit` records (default `[codegraph] max_results`, 20) and at most
  `max_bytes` bytes (default `max_output_bytes`, 8192; never above 32768) of
  serialized output in the chosen view, metadata included.
- A request may set `--limit` 1 through 200 and `--max-bytes` from 512; other
  values return `error` with reason `invalid_request`. A larger byte budget is
  treated as 32768.
- Records are dropped from the end until the output fits; a record is never
  cut at a boundary, and one paged record always stays even when it alone
  exceeds the budget, so `next_page` always moves forward. If that record is
  still over the budget, its `signature`, `qualified_name`, `name`,
  `spelling` and `from_name` are cut to 511 characters plus `…`; paths and
  IDs are never cut. Dropping sets `has_more` and, for paged actions,
  `next_page`. `check`'s lists, an ambiguous answer's choices and a `symbol`
  answer's `symbols` (after its neighbors) are shortened the same way; a
  target in `symbols` stays while a kept neighbor answers for it.
- `file`, `callers` and `refs` fetch `limit + 1` rows to decide `has_more`, and
  `symbol` reads at most `limit + 1` neighbors across its targets;
  `find` ranks the rows its SQL filter matched in memory, then slices.
- `callers` pages one sequence: linked calls first, then candidate calls,
  each in path, line and column order; offsets count records of both.
- Every answer reads within one transaction, so all its rows come from one
  generation; `check` ends that transaction before it hashes source files.

### Paging

`next_page` is an opaque base64url string encoding the snapshot ID, a
16-hexadecimal digest of the action, the target (for IDs, every resolved
target ID in request order), ordering and limit, and the offset. A token whose snapshot differs from the served one returns `expired`;
a token whose digest differs from the current request returns `error` with
reason `page_token_mismatch`; an undecodable token returns `error` with
`invalid_request`. Paging applies to `find`, `file`, `callers` and `refs`.

### Protocol version

The plugin supports protocol version 1 and answers in it. Any other requested
version returns `status` `error`, `reason` `protocol`, `protocol` 1 and
`details.supported` `[1]`.

### Compact text

```text
CodeGraph | <action> | <status> | index=<index> | freshness=<freshness> | snapshot=<first 10 hex> gen=<n>
<record lines>
shown=<n> | more=<yes|no>[ | next=<token>]
<message line when there is a message>
```

Symbol line: `<qualified_name><signature tail> | <path>:<start line>-<end line> | id=<prefix>`,
where `<prefix>` is the shortest unique ID prefix of at least 10 characters.
Reference line: `<label> <kind> <spelling> | <path>:<line> | from=<from_name> id=<prefix>`,
or `from=-` when no symbol contains the reference. When `details.targets` is
above 1, each reference line carries ` | for=<prefix of its subject>`, before
any ` (changed since indexing)`; `callers` lists linked calls, then candidates;
a `symbol` answer prints each target's symbol line followed by that target's
neighbors, and a neighbor whose target line is not shown after the groups.
An ambiguous answer lists its choices as symbol lines. `status` adds
`indexing: supported (<tested|untested>)` or `indexing: unsupported`.
A stale citation appends ` (changed since indexing)`.

## Examples

```text
CodeGraph | find | ok | index=ready | freshness=not_fully_checked | snapshot=5c0d2e9a41 gen=3
scope.select_files(config, inventory) | codegraph/scope.py:41-77 | id=8f31c2a90b
shown=1 | more=no

CodeGraph | find | unavailable | index=missing | freshness=- | snapshot=- gen=-
shown=0 | more=no
No CodeGraph index yet. Run know_graph_index, or use ordinary search.
```

```text
CodeGraph | callers | ok | index=ready | freshness=not_fully_checked | snapshot=5c0d2e9a41 gen=3
caller: lexical-binding call derive_run_id | adore/orchestrator.py:2723 | from=adore.orchestrator.Orchestrator._run_id id=cc6a51a850 | for=18b88b36ba
candidate: candidate call self._run_id | adore/orchestrator.py:696 | from=adore.orchestrator.Orchestrator._pick_ticket id=afa1dd4300 | for=cc6a51a850
shown=2 | more=no
```

An empty successful search renders `shown=0 | more=no` with status `ok`.

## Acceptance

- A fixture response exists for every action and every `status`, `index` and
  `freshness` value, and validates against these rules.
- Text and JSON renderings of the same fixture agree.
- Budgets, ranking and paging behave as specified on a high fan-out fixture.

## Assumptions and open decisions

- Path filters, kind filters and role filters for `find` are deferred; page
  tokens therefore bind action, targets, ordering and limit only.
- `from_name` is the enclosing symbol's full qualified name, not a name
  relative to the module, so it is unambiguous without the path; the longer
  line means fewer records fit a byte budget.
