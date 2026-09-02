<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Validation and evidence CLI

## Purpose

The canonical CLI evaluates repository governance records, runs
repository-configured validation commands, and writes reproducible task
evidence. It is advisory by default and does not enforce a workflow stage,
commit, publish, or access the network.

## Public interface

`check` reports governance, relationship, durable-record, and bounded-review
findings and optionally runs configured commands.
`test` executes a named configured command, optionally recording task evidence.
`report` appends a delivery snapshot. `anchor` fingerprints repository state
for an active task, while `evolution` classifies later changes against it.
`diagram` renders the requirement register as a Mermaid coverage map, to
standard output or to a UTF-8 file. `trace` exports the same register as a
flat traceability matrix in Markdown or comma-separated values. `explain`
reports what governs one repository path and which journals delivered it.

`trace` distinguishes unreadable requirement files from listed records with
validation errors and retains rows when optional knowledge prose is unreadable.
It labels uncertain ownership explicitly, derives categories from the first
folder below `requirements/`, and escapes literal Markdown cell content before
joining list entries. `--format` selects the format independently of the file
suffix; `--out` supplies portable encoding.

## Key behaviors

- `REQ-FUNC-871f7c12` - Evaluate governance records and diff findings.
- `REQ-FUNC-c2a3f774` - Run configured validation commands with explicit
  results.
- `REQ-FUNC-d37ad85a` - Append delivery reporting based on recorded task
  state.
- `REQ-DATA-4304dec0` - Record task-scoped repository evidence anchors.
- `REQ-DATA-7faf94ff` - Compare repository changes with an evidence anchor.
- `REQ-FUNC-6b4ff1ad` - Render the requirement register as a component
  coverage diagram.
- `REQ-FUNC-e46f1d0c` - Narrow that diagram to one component or one task.
- `REQ-FUNC-0f4eb4c5` - Trace a repository path back to the requirements and
  tasks that govern it.
- `REQ-FUNC-7ec58ca7` - Emit the requirement register as a complete, ordered
  traceability record.
- `REQ-FUNC-d3905502` - Serialize that record as Markdown or comma-separated
  values without losing its delimiters or its encoding.
- `REQ-UX-48bb759b` - Lead the delivery report with the deviations the task
  recorded.
- `REQ-FUNC-9514e017` - Project optional independent current-candidate review
  verdicts without treating missing or stale evidence as approval.
- `REQ-FUNC-cbff6478` - Check configured review bounds and block unapproved
  final-round delivery state.
- `REQ-FUNC-7ea14fe4` - Report malformed rulings and stale or invalid handoffs.

## Architecture

Eight commands over one register. Each entry point composes shared readers
rather than owning its own parsing, which is why a finding, a report and a
diagram can never disagree about what the records say. `coverage_class` is
the same rule applied to judgement rather than to parsing: `check` turns its
verdict into findings while `diagram`, `explain` and `trace` turn the same
verdict into a label, so the precedence between a broken link, a by-hand
method and an empty one exists in exactly one place.

The three readers of the whole register differ only in what they narrow.
`diagram` groups it into a picture that stops being legible past a few dozen
nodes; `explain` answers about one path; `trace` narrows nothing and is the
one form that leaves the repository, which is why it is the only one that
owes an escaping and encoding contract.

```mermaid
flowchart TD
    check(["check"])
    test(["test"])
    report(["report"])
    anchor(["anchor"])
    evolution(["evolution"])
    diagram(["diagram"])
    explain(["explain"])
    trace(["trace"])

    cfg["load_config - aegis.toml"]
    scan["scan_requirements / scan_journals - parse the register"]
    diffs["collect_diff - task base, else merge base"]
    runner["run_configured_commands - subprocess, timeouts"]
    manifest["repository_manifest - SHA-256 fingerprints"]
    render["render_diagram - Mermaid text"]
    rows["render_trace_md / render_trace_csv - one row per requirement"]
    covers["match_any - affected_paths cover this path"]
    devs["recorded_deviations - judgement out of the log"]
    bound["bound_stage_report - current recorded review state"]
    review["review_settings - optional bounded review policy"]
    cover["coverage_class - one verdict per record"]

    register[("requirements/ tasks/ knowledge/")]
    evidence[("TASK-id.anchor.json / .evolution.json")]

    check --> cfg
    check --> scan
    check --> diffs
    check --> runner
    check --> cover
    diagram --> cover
    explain --> cover
    trace --> cover
    trace --> scan
    trace --> rows
    test --> cfg
    test --> runner
    report --> scan
    report --> diffs
    report --> bound
    report --> review
    diagram --> scan
    diagram --> render
    explain --> scan
    explain --> covers
    report --> devs
    anchor --> manifest
    evolution --> manifest
    scan --> register
    manifest --> evidence
    evolution --> evidence
```


`explain` runs the register the other way round - a path in, the
requirements covering it out - which is why it needs no reader of its own.
Not shown: the check catalog's individual rules, and the fact that only
`anchor` and `evolution` write outside the journal. Every command here is
advisory - none of them blocks, and none of them commits.

## Files

- `05_Software/aegis/template/.agentic/aegis.py` - Canonical check, command,
  report, anchor, evolution, diagram, and trace implementation.
- `05_Software/aegis/tests/test_check.py` - Governance-check catalog tests.
- `05_Software/aegis/tests/test_run_report.py` - Strict-mode, configured-run,
  test, and reporting tests.
- `05_Software/aegis/tests/test_repo_evolution.py` - Anchor and evolution
  evidence tests.
