<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  parent        optional top-level TASK-id; blank for an ordinary task
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.

Stage report is one replaceable latest snapshot, not an evidence store.
Use plain one-line fields with no fences or bullets inside that section.
stage is the reported stage; current must match the journal header after any
transition. result is in_progress | completed | paused | blocked | skipped.
Keep all observations and decisions in the append-only Log as well.
Leave unknown fields blank; summary prints not recorded, never an assumed pass.
Refresh after work or decisions even if current has not changed.
-->

# TASK-e7a4791c — Export the requirement register as a traceability matrix

stage: validate
type: feature
path: full
requirements: REQ-FUNC-7ec58ca7, REQ-FUNC-d3905502, REQ-TEST-e38913a7, REQ-UX-62a24243
parent:
branch: task/trace-command
base: ba859befbcd90b2e549ce426007f582af411bf31
opened: 2026-09-02

## Done checklist (current stage)

- [x] diff reviewed against supplied findings and the existing format contract
- [x] knowledge pages, requirements, specifications and documentation updated
- [x] impacted command and focused rendering checks pass
- [ ] resolve CSV policy before completing the final independent verdicts
- [x] final evolution and full strict-check evidence recorded
- [x] remaining warnings, exclusions and decisions explained

## Log

- 2026-09-02 frame: scope is one new read-only CLI command, `trace`, that emits the whole requirement register as a flat traceability table in Markdown or CSV, one row per requirement, carrying id, category, status, coverage class, claiming component, title, requirement prose, verification, spec, and the complete linked test and affected path lists with their counts.
- 2026-09-02 frame: out of scope are any change to the requirement TOML schema, any new field on existing records, `--component` and `--task` scoping (a table does not degrade with size the way the Mermaid diagram does, and spreadsheets filter themselves), a literal requirement-by-test crosstab, native `.xlsx` output, and any third-party dependency.
- 2026-09-02 frame: full path chosen because the work adds an externally observable command, a new CLI interface and two new output formats; none of the quick-path conditions hold.
- 2026-09-02 frame: expected requirements are one for the traceability record itself (content, completeness, deterministic order, coverage class agreeing with `check`, stdout or a named file) and one for the two serializations (Markdown escaping, CSV quoting, Excel-readable encoding), mirroring the existing `diagram` pair REQ-FUNC-6b4ff1ad and REQ-FUNC-e46f1d0c.
- 2026-09-02 frame: no new requirement is proposed for the CLI reference itself; REQ-UX-62a24243 already governs user guidance, and `test_payload_ships_a_complete_cli_reference` already fails until `CLI.md` documents the command.
- 2026-09-02 frame: the register currently holds 35 requirements across 8 categories, so the whole-register table is the useful default.
- 2026-09-02 frame: scope, exclusions, path and the two proposed requirements confirmed by the user at the frame checkpoint.
- 2026-09-02 specify: created REQ-FUNC-7ec58ca7 for the record's content, completeness, ordering and coverage marking, and REQ-FUNC-d3905502 for the two serializations, both `draft` with empty `linked_tests` until build links them.
- 2026-09-02 specify: wrote `.agentic/specs/REQ-FUNC-7ec58ca7.md` because the column set, its two header vocabularies, the escaping rules and the encoding choice are a format that neither requirement's prose can carry without becoming a document.
- 2026-09-02 specify: reused rather than created for the CLI reference - REQ-UX-62a24243 already governs user guidance, so no third requirement was written; both new requirements list `CLI.md` in `affected_paths` instead, matching how REQ-FUNC-1844e18d and REQ-FUNC-6b4ff1ad carry their own documentation.
- 2026-09-02 specify: `trace` reports an unparseable requirement file on stderr and continues rather than dropping it silently or exiting non-zero, because `check` already raises `req-parse` as the authoritative error and an export that under-reports without saying so is the worse failure.
- 2026-09-02 design: design note written under `## Design`; the component is validation-and-evidence-cli and the change adds one entry point plus two renderers, composing the existing readers rather than adding any.
- 2026-09-02 design: revised that page's `## Architecture` to its intended post-change shape - eight commands, a `trace` node reaching `scan_requirements`, `coverage_class` and the new renderers - and marked the diagram as intended-not-yet-built naming this task.
- 2026-09-02 design: the page's diagram already bound the node id `trace` to `match_any`; renamed that node to `covers` so the new command can hold its own name, which is a rename inside one diagram and touches no code.
- 2026-09-02 design: plain `check` reports three `scope-drift` warnings against the other three open journals that are an artifact of measuring an unrelated task branch against the default branch, not findings against this work; `check --task TASK-e7a4791c` is the scope CLI.md prescribes here and reports nothing against this task.
- 2026-09-02 test: test --impacted (5 test ref(s)) exit 1 (0.2s)
- 2026-09-02 build: red recorded before any implementation - `python -m pytest tests/test_run_report.py -k "trace"` failed 10 of 10 new tests with `argparse: invalid choice: 'trace'`, the command not existing; anchor taken at ba859be over 70 files immediately after.
- 2026-09-02 build: one new test passed on the first red run for the wrong reason - `test_trace_rejects_an_unknown_format` caught the SystemExit argparse raises for an unknown command rather than an unknown format - and was tightened to assert the rejected format is named before implementation began.
- 2026-09-02 build: implemented `cmd_trace`, `trace_rows`, `render_trace_md`, `render_trace_csv` and the `flat`/`trace_cell` helpers in the template payload, added the `csv` and `io` imports, and mirrored the file to the root `.agentic/` copy.
- 2026-09-02 build: one test expectation was wrong rather than the code - the first ordering assertion listed REQ-DATA before REQ-FUNC, but the canonical category order is the one `req` documents, functional first; the test was corrected and now also asserts the category sequence directly.
- 2026-09-02 build: documented the command in the template `CLI.md` command summary, its own section and the exit-behavior table, and mirrored that file to the root copy as well.
- 2026-09-02 build: full configured suite green - `python .agentic/aegis.py test` exit 0, 352 passed, 2 skipped, the two skips pre-existing.
- 2026-09-02 build: evolution against the anchor reports exactly the three files design predicted, all modified, none added or removed - template aegis.py and CLI.md as source, test_run_report.py as tests.
- 2026-09-02 build: exercised the command against this repository's own register - 37 requirements, 13 columns, 38 CSV rows, every `test_count` and `path_count` equal to the list beside it, the written CSV carrying a byte-order mark and the written Markdown keeping its em dashes.
- 2026-09-02 validate: review round 1 found a real defect in the Markdown summary - a requirement in a folder outside the documented category set was counted into `by_category` but never printed, because the summary line iterated the canonical list only, so the breakdown did not sum to the total it sat beside; fixed by appending any extra folders after the documented ones, and covered by a new test asserting the counts add up.
- 2026-09-02 validate: review round 1 also failed the configured `lint` command - ruff RUF015 against a single-element slice in that new test - which turned `check --strict --run` red at errors=1 while the plain check stayed at 0; corrected to `next(...)` and re-run green.
- 2026-09-02 validate: knowledge page finished - `trace` added to the public interface, both requirement IDs added to Key behaviors, the Files entry updated, and the intended-shape caveat under the diagram removed now that the code matches it.
- 2026-09-02 validate: both requirements re-read against the built behavior - prose, verification, affected_paths and linked_tests all true of the candidate, and both now `active` with 7 and 4 linked tests respectively.
- 2026-09-02 validate: no manual or inspection verification is owed - both requirements are settled by automated tests - but the command was additionally exercised against this repository's own register as a sanity observation, giving 37 rows over 13 columns with every count matching its list.
- 2026-09-02 validate: final evidence after the last candidate edit - evolution refreshed to the same three modified files, `check --task TASK-e7a4791c --strict --run` exit 0 with `strict: ok`, test ok in 101.5s and lint ok, errors=0 warnings=9 notes=3.
- 2026-09-02 validate: the 9 remaining warnings and 3 notes are all pre-existing and none belong to this task - three `manual-verification` notes on other requirements, and review-state and unticked-deliver warnings on TASK-783dc269, TASK-d2351998 and TASK-ffda5ca3, which sit in deliver independently of this work.
- 2026-09-02 validate: review round 2 recorded both verdicts approved against the fixed candidate; the earlier round is superseded rather than erased, and any further edit invalidates both.
- 2026-09-02 build: DEVIATION build: `test --impacted` exited 1 without executing any test - `test_impacted` in `.agentic/aegis.toml` points `uv run --project 05_Software/aegis` at a directory holding no `pyproject.toml`, so uv resolves no project, warns that `--group dev` has no effect, and reaches an interpreter without pytest - accepted for this task because it is a pre-existing repository configuration defect that fails identically for any task, and because the configured full suite, a superset of the impacted set, ran green at exit 0; the impacted checklist item is left unticked rather than claimed.

- 2026-09-02 validate: the user supplied further review findings and authorized applicable corrections on task/trace-command without commits or pushes; return to build and invalidate both previous verdicts while preserving review round 2.
- 2026-09-02 build: confirmed misleading unreadable counts, multiline list cells, Markdown markup loss, unreadable knowledge-page aborts, nested category labels, collapsed summary paragraphs, a broken CLI option table, missing release and user documentation, and incomplete CLI-reference coverage; remaining export-contract claims are assessed against the existing specification before changing behavior.
- 2026-09-02 build: repository maintenance separately corrected test_impacted to use the installed plain Python runtime and aligned the root AGENTS.md validation command; this configuration repair creates no software task of its own.
- 2026-09-02 build: the earlier claim that impacted tests fail for every task was too broad, because TASK-783dc269 records successful runs using UV_PYTHON; the earlier claim that the structural CLI-reference test already guarded trace was also incorrect because its command list was hardcoded.

- 2026-09-02 build red: command=`python -m pytest -q tests/test_run_report.py -k 'trace_counts_only_omitted or trace_uses_the_category or trace_keeps_rows'` from 05_Software/aegis; exit=1 with 3 failed; expected missing behavior=two omitted files counted as six findings, nested/root files labeled sub/requirements, and invalid UTF-8 knowledge aborting the export.
- 2026-09-02 build: DEVIATION build: the three regression failures are intentional pre-fix evidence; an assertion was adjusted to avoid depending on the summary dash glyph while retaining the incorrect file-count check.
- 2026-09-02 build: the installed bundled GFM renderer reproduced the backslash-plus-pipe column shift; the planned correction escapes literal cell content before inserting renderer-owned list breaks.

- 2026-09-02 build: content regressions now pass (3 passed); the completed original anchor was replaced before implementation with the resumed review baseline, preserving its earlier evolution reports.
- 2026-09-02 build red: command=`python -m pytest -q tests/test_run_report.py -k 'trace_markdown_list or trace_markdown_keeps_literal or trace_summary_uses'` from 05_Software/aegis; exit=1 with 5 failed; expected missing behavior=multiline entries split rows, backslashes expose delimiters, markup changes literal prose, and the summary lacks singular wording and paragraph separation.
- 2026-09-02 build: DEVIATION build: the five serialization failures are intentional pre-fix evidence for REQ-FUNC-d3905502.

- 2026-09-02 build: DEVIATION build: the new installed-copy guard intentionally failed against the unsynchronized implementation, then passed after mirroring; a stale re import left by replacing the Markdown splitter caused lint exit 1 and was removed before the clean rerun.
- 2026-09-02 build: focused trace validation passed 21 cases, and structural validation passed 8 cases including mutation checks that remove each previously unguarded command section; Ruff passed after removing the unused import.
- 2026-09-02 build: the additional CSV CR/LF control passed without a production change, confirming that the standard CSV writer already quotes embedded line endings correctly.
- 2026-09-02 build: reused REQ-TEST-e38913a7 for the installed-copy guard and REQ-UX-62a24243 for documentation corrections; no new requirement or task is needed for these supplied findings.
- 2026-09-02 build: a bundled GFM renderer and HTML parser verified 13 columns, exact literal markup and Unicode, list breaks confined to cells, and separate summary paragraphs; isolated subprocesses confirmed the documented cp1252 stdout limitation, correct UTF-8-BOM --out files, and format-independent output suffixes.
- 2026-09-02 build: the security fix-finding skill's independent read-only investigation confirmed raw formula prefixes and a same-count semicolon-list collision, but no spreadsheet execution or code execution was demonstrated; the requested CSV-policy choice remains open because neutralization and reversible lists change the explicit raw-value contract.

- 2026-09-02 build: corrected configured command `python .agentic/aegis.py test --impacted --base HEAD` executed five mapped files and exited 0 with 365 passed and 2 skipped in 100.4s; the skips concern Windows symlink semantics and unavailable symlink creation.
- 2026-09-02 build: build corrections completed and the task returned to validate; source, tests, documentation and requirement links were reviewed, with CSV policy explicitly unresolved rather than silently changing the accepted format.
- 2026-09-02 validate: syntax compilation, CLI --help, Ruff and diff whitespace checks passed; package README, the folder guide, the detailed CLI reference and Unreleased entries were inspected against the actual trace interface under REQ-UX-62a24243.
- 2026-09-02 validate: DEVIATION validate: accept the two pre-existing platform-dependent symlink skips; no Linux or live Excel verification was performed, and no claim of formula neutralization or lossless CSV list decoding is made.

- 2026-09-02 validate: final `python .agentic/aegis.py check --task TASK-e7a4791c --strict --run --json` exited 0; strict passed, full tests 369 passed and 2 skipped in 105.86s, configured test exit 0 in 106.5s, and lint exit 0 in 0.2s.
- 2026-09-02 validate: final evolution records the expected eight modified source/test/documentation files since the resumed anchor, with no added or removed files; installed managed files match the template and HEAD remains ba859befbcd90b2e549ce426007f582af411bf31 on task/trace-command, with nothing staged, committed or pushed.
- 2026-09-02 validate: DEVIATION validate: accept 9 advisory warnings for this paused snapshot, comprising 8 existing review/delivery warnings on other journals and 1 current-task incomplete-review warning while the CSV policy remains undecided; the 3 manual-verification notes remain informational, with changed user guidance inspected directly.
- 2026-09-02 validate: DEVIATION validate: an optional read assumed template/CHANGELOG.md existed and raised FileNotFoundError; the path is absent on this branch and no downstream starter was added or changed.
- 2026-09-02 validate: pause with all implemented corrections tested; preserve the two existing CSV behaviors pending the user's requested choice, do not spend or reset another explicit review round, and do not advance to deliver with unresolved CSV-policy findings.

## Design

Component: validation-and-evidence-cli. One new entry point beside `diagram`
and `explain` — no new reader, no new dependency, no repository write beyond
what `--out` names.

Interface (REQ-FUNC-7ec58ca7, REQ-FUNC-d3905502): `trace [--format {md,csv}]
[--out PATH]`, defaulting to `md` on standard output. `cmd_trace` composes the
existing `scan_requirements`, `knowledge_components` and `coverage_class`, then
hands finished rows to `render_trace_md` or `render_trace_csv`. Collection is
split from serialization because that is exactly the seam along which the two
requirements fail independently — a correct record can still be destroyed by
the format it is written in.

Data (REQ-FUNC-d3905502): no schema change, no new field on any record. The
column list, both header vocabularies, the escaping rules and the encodings
live in `specs/REQ-FUNC-7ec58ca7.md` rather than here — they belong to the
behavior, not to this task.

Rejected: one row per requirement-and-test pair, reusing `render_diagram`'s
grouping. That is the literal traceability-matrix shape, but it turns 35
requirements into roughly 200 rows with repeating requirement fields, and
every count in the file then needs de-duplication before it can be read. A
crosstab stays available later as a third `--format`.

Test seams — `05_Software/aegis/tests/test_run_report.py`, beside the diagram
tests, which already build a register fixture holding one requirement of every
coverage class:

- REQ-FUNC-7ec58ca7: one row per requirement, category-then-id order, counts
  equal to their neighbouring lists, coverage equal to `check`'s verdict, an
  unclaimed requirement still carried, and a byte-identical second run.
- REQ-FUNC-d3905502: both renderers over prose carrying `|`, `,`, `"`, a line
  break and a non-ASCII character — CSV round-trips through `csv.reader`,
  Markdown keeps its column count, written bytes decode as declared.

Files: template `.agentic/aegis.py` and `.agentic/CLI.md`, each with its
hand-kept root `.agentic/` mirror (byte-identical today), `test_run_report.py`,
and this component's knowledge page.

Architecture: the page's diagram already binds the node id `trace` to
`match_any`. Renamed to `covers` so the new command node can hold the name.

## Review findings

| Supplied finding | Assessment and disposition |
|---|---|
| Listed files reported unreadable | Fixed: distinguish readable validation findings from omitted files and count omitted paths once. |
| Stdout encoding and BOM | Reproduced, but explicitly specified as best-effort console output; retain the contract and document --out as the portable file path. |
| Newlines in Markdown list entries | Fixed: flatten and escape each entry before inserting cell-local breaks. |
| Backslash before a pipe | Fixed: numeric character references preserve literal content and prevent GFM column shifts; tested with a real renderer. |
| Unreadable knowledge aborts export | Fixed for trace: warn and retain rows; mark uncertain ownership as knowledge incomplete. Other readers retain their existing error behavior. |
| Nested category is misidentified | Fixed in trace: first folder below requirements, or no-category marker at its root; broader scanner placement policy is unchanged. |
| HTML and inline markup alter prose | Fixed: serialize literal Markdown cell text, preserving source markup as visible text. |
| CSV formula interpretation | Confirmed raw formula prefixes reach exported cells; no spreadsheet execution demonstrated. Decision pending because neutralization changes the explicit raw-value contract; documented without claiming mitigation. |
| Summary soft break and singular | Fixed: separate paragraphs and singular wording for one requirement. |
| Output suffix differs from format | Existing explicit contract: md defaults independently of suffix. Retained and clarified; no new inference or rejection policy. |
| CSV semicolon-list ambiguity | Confirmed two distinct two-entry lists can produce identical display cells. Decision pending because reversible encoding changes the specified joiner; documented without claiming lossless decoding. |
| CLI pipe-escaping table breaks | Fixed: removed the raw pipe from the option table and described literal escaping. |
| Missing changelog and user documentation | Fixed: Unreleased entry, package README, folder guide and detailed CLI reference now include trace. |
| Hardcoded CLI-reference command list | Fixed: derive command sections from parser choices; mutation tests detect all five previously omitted sections. |
| Installed/template drift is unguarded | Added byte-equality guards for aegis.py and CLI.md; demonstrated the guard failing before synchronization and passing afterwards. |

## Rulings

<!-- Append decisions here; never edit history. Supersede with a new ruling.
- RULING-001 | date=YYYY-MM-DD | decision=<decision> | reason=<reason> | source=user | supersedes=none
source: user | repository | requirement | technical
-->

- RULING-001 | date=2026-09-02 | decision=name the command `trace` and title its artifact a Requirements Traceability Matrix | reason=the linked view is called a traceability report or matrix across Xray, codebeamer, Polarion and DOORS, `register` is risk-management vocabulary no requirements tool uses, `matrix` alone would oversell a row-per-requirement table that is not the crosstab, and `report` is already the delivery command | source=user | supersedes=none
- RULING-002 | date=2026-09-02 | decision=CSV column headers are the requirement TOML key names, Markdown column headers are human labels | reason=the CSV is the machine and diff artifact and is self-describing against the source records, the Markdown is what a reviewer or assessor reads | source=technical | supersedes=none
- RULING-003 | date=2026-09-02 | decision=neither format truncates any value | reason=`summary` and `brief` bound their output because they are resume views for context-limited agents, whereas a traceability export is a durable artifact whose whole point is completeness, and a clipped affected-path list would be read as the whole list | source=technical | supersedes=none
- RULING-004 | date=2026-09-02 | decision=one spec at specs/REQ-FUNC-7ec58ca7.md is referenced by both new requirements instead of one spec each | reason=there is a single output format, and splitting it would either duplicate the column table or make each half depend on reading the other; the spec names both owners in its opening lines so the shared reference is not mistaken for a stray link | source=technical | supersedes=none

- RULING-005 | date=2026-09-02 | decision=correct only applicable supplied review findings on task/trace-command; do not commit or push | reason=the user explicitly authorized local corrections and prohibited publication | source=user | supersedes=none

## Handoff

<!-- Replace these fields with the latest minimal resume snapshot.
status: ready | waiting | blocked
-->

current: validate
status: waiting
next: decide whether CSV retains raw fields and display-list joining or adopts formula protection and reversible list encoding
must_read: .agentic/steps/5_validate.md, .agentic/specs/REQ-FUNC-7ec58ca7.md, .agentic/tasks/TASK-e7a4791c.md
blockers: CSV contract decision required; commits and pushes prohibited

## Stage report

stage: validate
result: paused
current: validate
changed: 11 supplied findings corrected; local impacted-test command repaired; 2 documented behaviors retained
evidence: impacted 365 passed, 2 skipped; full suite 369 passed, 2 skipped; lint and strict check exit 0; GFM rendering verified
issues: 2 CSV contract decisions remain; 9 advisory warnings (8 other journals, 1 incomplete current review); Linux and live Excel untested
next: choose raw CSV semantics or spreadsheet protection and reversible lists
needs_user: yes - the existing spec requires raw fields and semicolon joining
spec_compliance:
implementation_quality:
review_round: 2
