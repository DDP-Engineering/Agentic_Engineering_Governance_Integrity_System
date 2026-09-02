<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-7ec58ca7 — the traceability record format

This spec defines one output format and is referenced by two requirements:
REQ-FUNC-7ec58ca7 owns the record's content and ordering, REQ-FUNC-d3905502
owns its two serializations. They are separated because a record can be
complete and still be destroyed by the format it is written in, and the two
fail independently.

## Behavior

`trace` reads the requirement register, the knowledge pages, and nothing
else. It runs no command, consults no Git state, reaches no network, and
writes no repository state beyond the file `--out` names. Two runs over
unchanged files produce identical bytes.

Every requirement file under `.agentic/requirements/` contributes exactly one
row, whatever its status — a retired behavior and a draft one are part of the
register's history and their absence would misreport it. Rows are ordered by
category in the canonical order below, then by identifier ascending, so the
ordering never depends on filesystem enumeration.

A requirement file that fails to parse contributes no row. It is named on
standard error and counted in the Markdown summary, never dropped silently:
an export that quietly under-reports is worse than one that admits a gap.
The exit status stays 0, because `check` is the authority on findings and
already raises `req-parse` as an error for the same file.

Readable files with schema, field, status or identifier errors still contribute
rows. Their findings are reported as validation errors on listed files and
never increase the count of omitted files. Omitted files are counted once each.

An unreadable knowledge page is reported on stderr without aborting the
export. Readable pages still supply ownership; other rows are marked
`(knowledge incomplete)` instead of claiming that no page owns them.

### Categories, in order

`functional`, `ux`, `nfr`, `security`, `data`, `platform`, `reliability`,
`test` — the order `CLI.md` documents for `req`. A category with no
requirements is still reported in the Markdown summary with a count of zero,
so an empty security or NFR register is visible rather than absent.

### Coverage

The `coverage` value is whatever `coverage_class()` returns for that record:
`tested`, `manual`, `broken`, `uncovered`, `draft` or `retired`. `trace`
never re-derives it. The classifier is shared with `check` and the coverage
diagram precisely so that three readers of one record cannot disagree.

## Data / interface

```text
python .agentic/aegis.py trace [--format {md,csv}] [--out PATH]
```

`--format` defaults to `md`. Without `--out` the text goes to standard
output; with it, the file is written and its path is printed, parent folders
created as needed. The file suffix does not infer or override `--format`.
An unrecognized format is an argparse error and exit 1.

### Columns

Thirteen, in this order. The CSV header is the requirement TOML key name, so
the artifact is self-describing against its source records; the Markdown
header is the human label, because that is the copy an assessor reads.

| # | CSV header | Markdown header | Value |
|---|---|---|---|
| 1 | `id` | Requirement ID | `id` |
| 2 | `category` | Category | first folder below `requirements/`; `(no category)` for a file directly in that root |
| 3 | `status` | Status | `status` |
| 4 | `coverage` | Coverage | `coverage_class()` |
| 5 | `component` | Component | the readable knowledge page claiming it, else `(no knowledge page)` or `(knowledge incomplete)` when pages could not be read |
| 6 | `title` | Title | `title` |
| 7 | `requirement` | Requirement | `requirement`, whitespace-collapsed |
| 8 | `verification` | Verification | `verification`, whitespace-collapsed |
| 9 | `spec` | Spec | `spec`, or empty |
| 10 | `test_count` | Tests | number of `linked_tests` entries |
| 11 | `linked_tests` | Verified By | every `linked_tests` entry |
| 12 | `path_count` | Files | number of `affected_paths` entries |
| 13 | `affected_paths` | Implemented In | every `affected_paths` entry |

Whitespace collapse is `" ".join(text.split())` — the idiom `explain`
already uses — which also removes the line breaks that TOML multi-line
strings carry.

**Nothing is truncated, in either format.** `summary` and `brief` bound
their values because they are resume views for context-limited agents. This
is a durable artifact whose purpose is completeness; a clipped
`affected_paths` list reads as the whole list and misleads the reader it was
written for.

### Markdown

A summary block with separate coverage and category paragraphs, then one
table. Each scalar and each list entry is whitespace-collapsed and literal
inline markup is escaped with numeric character references, including pipes,
backslashes, HTML delimiters, ampersands, emphasis and link markers. Entries
are escaped before list columns join them with renderer-owned `<br>` breaks.
Source text cannot add a row, column, HTML element or inline formatting.
Written UTF-8, `\n` line endings.

```text
# Requirements Traceability Matrix

35 requirements - tested 28, manual 3, broken 1, uncovered 2, draft 1, retired 0

by category - functional 20, ux 5, nfr 0, security 0, data 2, platform 2, reliability 3, test 3

| Requirement ID | Category | Status | Coverage | ... |
|---|---|---|---|---|
| REQ-DATA-4304dec0 | data | active | tested | ... |
```

A count of unreadable requirement files is appended to the first summary line
when any exist.

### CSV

One header row, then the data — no summary block, no preamble, so a
spreadsheet's autofilter and sort apply to the whole file. Written through
the standard library `csv` writer with `lineterminator="\n"`, which quotes
and doubles quotes per RFC 4180. List columns join their entries with `; `.

CSV preserves data without neutralizing spreadsheet formulas. Consumers must
import untrusted text as text; BOM and CSV quoting do not control spreadsheet
formula interpretation. List cells are display strings: `; ` inside an entry
cannot be distinguished from the separator. Their counts describe source list
entries, not a reversible split of the displayed cell.

Written **`utf-8-sig`**. The BOM is what makes Excel on Windows read the
file as UTF-8 rather than guessing the system code page; the register
already contains em dashes, so guessing wrongly is not hypothetical. The
BOM is written only for `--out`; standard output is left as the console's
own stream, the same best-effort path `diagram` takes and the same reason
`--out` exists.

## Examples

A requirement whose statement contains the delimiters of both formats:

```toml
requirement = "The tool shall accept a, b or c — never \"d\" | \"e\"."
```

CSV — one field, quoted, inner quotes doubled, comma and bar carried whole:

```text
id,category,status,coverage,component,title,requirement,...
REQ-FUNC-00000000,functional,active,tested,core-cli-lifecycle,Accept operands,"The tool shall accept a, b or c — never ""d"" | ""e"".",...
```

Markdown — the bar escaped so the row keeps its columns:

```text
| REQ-FUNC-00000000 | functional | active | tested | ... | The tool shall accept a, b or c — never "d" &#124; "e". | ... |
```

A register with no requirement files at all emits the header row (CSV) or the
summary block and an empty table (Markdown), states `0 requirements`, and
exits 0.

## Acceptance

- Every requirement file appears exactly once; the row count equals the file
  count minus the files reported unreadable on standard error.
- Row order is category-then-identifier, and a second run byte-matches the
  first.
- Each row's `coverage` equals what `check` reports for that same record.
- `test_count` and `path_count` equal the number of entries actually written
  in their neighbouring columns, on every row.
- CSV output parses back through `csv.reader` to the same field values and
  row count when prose contains `,`, `"`, `|` and a line break.
- Markdown output keeps one table row per requirement, with its column count
  intact, for the same prose.
- A file written with `--out` decodes to the original characters as the
  encoding its format declares.
- A requirement no knowledge page claims is carried, marked
  `(no knowledge page)`, not dropped.
