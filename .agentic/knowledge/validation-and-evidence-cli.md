<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Validation and evidence CLI

## Routing

Read this page when a request mentions governance findings, strict checks,
configured validation, impacted tests, delivery reports, evidence anchors,
repository evolution, requirement coverage diagrams, traceability exports, or
path explanations. The `[diagrams]` warning in `check` lives here; the design
diagrams that setting turns on belong to the Reusable workflow payload. The
public command signals are `check`, `test`, `report`, `anchor`, `evolution`,
`diagram`, `trace`, and `explain`.

Start implementation inspection in
`05_Software/aegis/template/.agentic/aegis.py`, using the `cmd_<command>` entry
point and the symbols in the Change map. Start verification in the focused test
file named there. The same Python file also contains the Core CLI lifecycle;
requests about `init`, `task`, `req`, `status`, `summary`, or `brief` belong to
that component instead.

## Purpose and boundaries

The canonical CLI evaluates repository governance records, runs
repository-configured validation commands, and writes reproducible task
evidence. Its built-in logic is advisory by default and does not enforce a
workflow stage, commit, publish, or directly access the network. Explicitly
configured child commands retain their own side effects and authority needs.

This component owns evaluation, configured-command execution, evidence
fingerprints, delivery projections, and read-only register views. The Core CLI
lifecycle owns installation, scaffolding, status, summary, and resume views.
The Reusable workflow payload defines the workflow and artifact contracts that
this component evaluates; changing those contracts is not owned here merely
because `check` reports on them.

Eight command entry points reuse shared readers and focused processors.
Coverage precedence lives in one function, `explain` reverses the register from
a path to its requirements, and only `anchor` and `evolution` write evidence
outside the journal.

## Public interface

`check` reports governance and optionally runs configured commands. `test`
executes one configured command and may record its result in a task journal.
`report` appends a delivery snapshot. `anchor` fingerprints Git-visible state;
`evolution` classifies later changes against that anchor. `diagram` renders a
Mermaid coverage map. `trace` exports the complete requirement register as
Markdown or CSV. `explain` reports the requirements and journals governing one
repository path.

`trace` distinguishes unreadable requirement files from listed records with
validation errors and retains rows when optional knowledge prose is unreadable.
It labels uncertain ownership explicitly, derives categories from the first
folder below `requirements/`, and escapes literal Markdown cell content before
joining list entries. `--format` selects the format independently of the file
suffix; `--out` supplies portable encoding.

## Invariants

- `check` remains advisory unless `--strict` is requested; `test` mirrors the
  configured command's exit status.
- Configured repository commands run only through an explicit `test` or
  `check --run` request, with the configured timeout and output handling.
- Built-in AEGIS logic does not advance a workflow stage, commit, publish, or
  directly access the network; child commands launched by `test` or
  `check --run` are not sandboxed by this CLI and may have those side effects.
- `coverage_class` is the single coverage-precedence rule shared by `check`,
  `diagram`, `trace`, and `explain`; their verdicts must not diverge.
- `trace` retains every readable requirement and degrades optional unreadable
  knowledge into explicit ownership uncertainty instead of dropping rows.
- `anchor` and `evolution` describe Git-visible repository state as evidence;
  their fingerprints are reproducible records, not tamper-proof proof.
- Anchor and evolution sidecars are local evidence unless
  `[records] commit_fingerprints` is true; `check` reports a repository whose
  tracked state contradicts that setting and never untracks a file itself.
- `report` projects recorded task state. Missing, malformed, or stale review
  evidence must never become an approval claim.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Governance finding or strict-exit semantics | `run_checks`, `cmd_check`, and the relevant `check_*` rule | `test_check.py`; strict-mode tests in `test_run_report.py` |
| Configuration warning | `CONFIG_SHAPE`, `DIAGRAM_TYPES`, `check_config` | the `test_invalid_*_values_*` group and the diagrams settings tests in `test_check.py` |
| Sidecar tracking finding | `check_fingerprints`, `tracked_fingerprints` | the `test_fingerprints_tracked_*` group in `test_check.py` |
| Configured or impacted test execution | `run_configured_commands`, `impacted_tests`, `cmd_test` | `test_run_report.py::test_run_reports_ok_and_fail_and_feeds_strict` and the `test_test_*` group |
| Delivery report or review/deviation projection | `cmd_report`, `bound_stage_report`, `recorded_deviations` | `test_run_report.py::test_report_leads_with_the_recorded_deviations` and the `test_report_*` group |
| Anchor or evolution evidence | `repository_manifest`, `cmd_anchor`, `cmd_evolution` | `test_repo_evolution.py::test_anchor_records_visible_files_metadata_and_hashes` and `test_repo_evolution.py::test_evolution_classifies_changes_and_retains_compact_history` |
| Coverage class or Mermaid diagram | `coverage_class`, `knowledge_components`, `diagram_scope`, `render_diagram`, `cmd_diagram` | `test_run_report.py::test_every_coverage_class_matches_what_check_reports` and the `test_diagram_*` group |
| Traceability row or export format | `trace_rows`, `render_trace_md`, `render_trace_csv`, `cmd_trace` | the `test_trace_*` group in `test_run_report.py`, especially delimiter, encoding, and unreadable-input cases |
| Path-to-governance explanation | `match_any`, `cmd_explain` | `test_run_report.py::test_explain_traces_a_path_to_its_requirements_and_tasks` |

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
- `REQ-FUNC-cd29e673` - Warn about a non-Boolean `[diagrams] enabled`, a
  non-list `types`, or an unknown diagram type name.
- Report anchor/evolution sidecars whose tracked state contradicts
  `[records] commit_fingerprints`. (no req)

## Files

- `05_Software/aegis/template/.agentic/aegis.py` - All entry points and shared
  processors named in the Change map; this monolithic file also contains the
  separate Core CLI lifecycle component.
- `05_Software/aegis/tests/test_check.py` - Governance-check catalog tests.
- `05_Software/aegis/tests/test_run_report.py` - Strict-mode, configured-run,
  test, and reporting tests.
- `05_Software/aegis/tests/test_repo_evolution.py` - Anchor and evolution
  evidence tests.
