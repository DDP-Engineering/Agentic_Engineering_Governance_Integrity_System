<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Workflow Run Records

This guide explains the evidence AEGIS creates for one workflow execution. A
run record answers, “What happened, what was approved, what was checked, and
what is the current result of this particular piece of work?”

It is different from durable governance state. Requirements, component maps,
knowledge pages, and curated adoption reports remain useful after a run ends;
the run folder preserves how a specific decision or result was reached.

## Run folder

`.agentic/runs/` is empty immediately after installation. AEGIS creates a
subfolder when a workflow begins:

```text
.agentic/runs/<workflow-kind>-<timestamp>-<short-id>/
```

| Artifact | Represents | Data stored | Created or updated by | Why it is needed |
| --- | --- | --- | --- | --- |
| `graph.json` | Current state snapshot of the run. | Intent, stages, approvals, evidence, decisions, and current completion state. | AEGIS workflow commands. | Gives tools and people one current, machine-readable source of run state. |
| `journal.jsonl` | Append-only event timeline. | One timestamped JSON event per line. | AEGIS workflow commands and supported post-tool evidence hook. | Preserves the order in which run state changed. |
| `stages/` | Forms and retained revisions for each workflow stage. | Stage submissions, control decisions, revision digests, and imported state. | AEGIS creates form structure; agents/humans fill forms; AEGIS applies and closes them. | Records exactly what was prepared, approved, and used at each workflow boundary. |
| `validation-summary.json` | Consolidated validation result. | Impact, gates, invariants, audits, working-tree review, and regression selection. | AEGIS when `aegis verify run` executes. | Gives a concise, reproducible validation result without requiring readers to interpret every raw artifact. |
| `report.md` | Readable run report. | Run intent, progress, evidence, validation, blockers, and handoff information. | AEGIS when a run report is rendered. | Provides a human-friendly summary of the detailed machine-readable run record. |

## Run types and stages

The run intent selects a fixed stage sequence. Individual runs have separate
forms, revisions, evidence, and statuses even when they use the same sequence.

| Run type or profile | Ordered stages |
| --- | --- |
| Full `feature`, `fix`, or `change` run | `intake` -> `alignment` -> `requirement` -> `design` -> `check` -> `implementation` -> `validation` -> `delivery` |
| `adoption` run | `adoption-intake` -> `adoption-alignment` -> `repo-discovery` -> `component-map` -> `component-adoption` -> `baseline-review` -> `adoption-delivery` |
| Quick `fix` or `change` run | `intake` -> `implementation` -> `validation` -> `delivery` |

The fixed sequence exists so the workflow can distinguish an intentionally
bypassed stage from a completed one and can verify that important decisions
occur before dependent work.

## The run graph

`graph.json` is a living snapshot, not an append-only history.

| Field | Data stored | Populated by | Why it is needed |
| --- | --- | --- | --- |
| `schema_version` | Run-graph format version. | AEGIS when the run starts. | Allows strict loading of the graph. |
| `run_id` | Stable identifier for this run. | AEGIS when the run starts. | Connects every folder, form, event, and summary to one execution. |
| `intent` | Intent ID, kind, statement, scope hint, status, and creation time. | Human or agent provides the intent; AEGIS records it. | Records why the workflow exists. |
| `stage` | Current stage name. | AEGIS as stages advance. | Shows what work is currently expected. |
| `complete` | Whether the run reached completion. | AEGIS at closure. | Separates a finished record from an in-progress one. |
| `access_mode` | Approved repository access level. | Initial intent and controlled stage decisions. | Makes permitted working scope explicit. |
| `alignment` | Shared understanding, scope, assumptions, criteria, risk, questions, and proceed/pause decision. | Alignment-stage form, applied by AEGIS. | Prevents implementation from proceeding on an unclear or unapproved understanding. |
| `change_units` | Work-unit IDs and their touched paths. | Implementation-stage forms, applied by AEGIS. | Gives a stable unit for impact and evidence mapping. |
| `design` | Design-stage output when required; otherwise absent or `null`. | Design-stage form, applied by AEGIS. | Keeps design choice connected to the run when policy requires one. |
| `spec_items` | Specification items associated with the run. | Requirement/design workflow, applied by AEGIS. | Links detailed acceptance material to the work. |
| `checks` | Planned deterministic checks and their requirement/specification citations. | Check-stage item forms, applied by AEGIS. | Makes verification intentional and traceable. |
| `evidence` | Check and gate evidence records. | AEGIS gate/verification commands and supported hooks. | Preserves objective outcomes used by later stages. |
| `decisions` | Explicit decisions recorded in the workflow. | AEGIS from stage actions and decision forms. | Keeps choices visible instead of burying them in prose. |
| `stage_records` | Status and current applied content for every prepared stage. | AEGIS as forms are prepared, applied, approved, revised, and closed. | Connects stage status to exact form content and integrity data. |

Each `stage_records` entry includes the stage name, form `artifact` path,
revision number, retention mode, prepared/applied/closed timestamps, status,
summary, digest, control information, unresolved questions, and the full
applied stage payload. The digest lets AEGIS detect whether the exact recorded
revision has changed.

## Event journal

`journal.jsonl` uses JSON Lines: every line is one independent complete event.

| Field | Data stored | Populated by | Why it is needed |
| --- | --- | --- | --- |
| `time` | UTC event timestamp. | AEGIS or supported post-tool evidence hook. | Orders the history without relying on file timestamps. |
| `event` | Stable event name. | AEGIS or supported hook. | Lets tools and reviewers identify what occurred. |
| `data` | Event-specific JSON object. | AEGIS or supported hook. | Carries only the detail needed for that event. |

| Typical event | Data recorded | Why it is needed |
| --- | --- | --- |
| `run.started` | Kind, access mode, initial statement, and scope hint. | Establishes the run's beginning. |
| `stage.prepared` | Stage, form artifact path, revision, retention mode, and check-execution mode. | Records creation of editable stage material. |
| `stage.applied` | Stage, revision, and integrity digest. | Records which exact form content became active. |
| `stage.approved` | Stage, revision, and approver. | Records human approval. |
| `stage.closed` | Closure of a stage. | Marks completion of the workflow boundary. |
| `stage.set` | New current stage. | Records progression through the lifecycle. |
| `access_mode.set` | Changed access mode and reason. | Makes access escalation explicit. |
| `verification.completed` | Validation-summary path and outcome. | Connects the final verification event to its summary. |
| `agentic.tool` | Limited observed tool metadata: tool name, tool-use ID, and response presence. | Adds evidence that supported tool activity occurred without storing full tool content. |

The journal is the timeline. `graph.json` is the latest state reconstructed
from workflow actions. Neither replaces the stage forms or detailed evidence.

## Stage forms and revisions

AEGIS creates a stage form before a stage can be applied. An agent or human
fills it, AEGIS validates and applies it, and a human explicitly approves a
stage before closure. If a form needs correction, AEGIS retains the original
and creates a numbered revision instead of silently overwriting approved
content.

```text
stages/<stage-name>/<stage-name>.toml
stages/<stage-name>/revisions/0001/<stage-name>.toml
stages/<stage-name>/revisions/0001/digest.json
stages/<stage-name>/revisions/0002/...
```

The common identity fields in every form are `schema_version`, `run_id`,
`stage`, and `revision`. Regular single-form stages also have a `[control]`
table: `requested_access_mode`, `access_rationale`, `route_to`,
`route_rationale`, `summary`, and `unresolved_questions`.

`requirement` and `check` are collection stages: they have a shared control
form plus one item form per requirement or check. Item forms use the common
identity fields but do not repeat the control table.

Every primary stage form also begins with a deterministic completion checklist
rendered as TOML comments. The checklist is presentation guidance only: it
does not add TOML keys or alter the imported form payload. Its machine items
name the command that records or verifies the condition, and its human items
name an explicit approval boundary. Collection-stage guidance appears once in
`stage.toml`, never in each requirement or check item. The matching standard,
adoption, and delivery references are checked projections of the same CLI-owned
stage contract, so their `Done when` lists cannot drift from generated forms.

| Stage | Stage-specific fields and purpose |
| --- | --- |
| `intake` | `statement` defines requested work; `scope_hints` gives initial boundaries; `access_mode` requests repository access. |
| `alignment` | `understanding`, `in_scope`, `out_of_scope`, `assumptions`, `acceptance_criteria`, `questions`, `recommended_answers`, `planned_paths`, `risk`, and `decision` establish approved understanding. |
| `requirement` item | `id`, `category`, `priority`, `requirement`, `rationale`, `verification`, `spec_ref`, `affected_paths`, and `linked_tests` define one publishable behavioral contract. |
| `design` | `document`, `cited_requirement_ids`, and `selected_option` connect design to requirements and record the selected approach. |
| `check` item | `id`, `level`, `cites_requirement`, `cites_spec`, `command`, `path`, `contract_variants`, `concerns`, and `parity_targets` define one intended verification check. |
| `implementation` | `change_unit_id`, `changed_paths`, `documentation_effects`, and `linked_check_evidence` record implementation scope and evidence. |
| `validation` | `deterministic_verification`, `diff_review`, `documentation_review`, `style_review`, `manual_evidence`, and `approved_supersessions` record validation and human review. |
| `delivery` | `preflight`, `report`, and `decision` record handoff readiness and decision. |
| `adoption-intake` | `statement`, `adoption_slice`, `bundle_components`, `bundle_rationale`, and `access_mode` scope the adoption work. |
| `adoption-alignment` | Uses the same fields as `alignment` for adoption-specific understanding. |
| `repo-discovery` | `source_roots`, `test_roots`, `requirement_roots`, `documentation_roots`, `gate_commands`, `candidate_components`, `external_dependencies`, `entry_points`, `existing_tests`, `discovery_evidence`, `repowise_warnings`, and `repowise_status` record observed repository facts. |
| `component-map` | `manifest`, `components`, `approved_slice`, and `approval_decision` record the proposed and approved component boundaries. |
| `component-adoption` | `adopted_components`, `changed_paths`, `documentation`, `requirement_links`, `remaining_gaps`, and `behavior_changed` record a component's adoption work. |
| `baseline-review` | `reviewed_components`, `blocking_gaps`, `follow_up_gaps`, `accepted_legacy_risks`, and `decision` record baseline readiness. |
| `adoption-delivery` | Uses the same `preflight`, `report`, and `decision` fields as `delivery`. |

## Evidence records

Evidence records live in `graph.json` and are referred to by stage forms and
validation. They may represent a gate result, a check result, or another
recorded verification activity.

| Field | Data stored | Populated by | Why it is needed |
| --- | --- | --- | --- |
| `id` | Stable evidence identifier, such as `E-0001`. | AEGIS. | Lets forms and reports cite exact evidence. |
| `kind` | Evidence type, such as gate or check. | AEGIS. | Explains how the evidence should be interpreted. |
| `stage` | Stage that recorded the evidence. | AEGIS. | Connects evidence to the workflow boundary that relied on it. |
| `status` | Active or superseded state. | AEGIS and approved workflow actions. | Keeps prior evidence visible without treating it as current. |
| `result` | Outcome, such as pass or fail. | AEGIS from check/gate execution or recorded external result. | Supplies the factual outcome used by validation. |
| `summary` | Short human-readable result description. | AEGIS or workflow author. | Lets a reviewer understand evidence without opening raw output. |
| `created_at` | UTC record time. | AEGIS. | Establishes evidence timing. |
| `command`, `gate_name`, `check_id`, `path`, `output_log`, `exit_status`, `failure_kind` | Optional execution and attribution details. | AEGIS from configured or recorded check execution. | Makes the result reproducible and attributable. |
| `superseded_by`, `supersede_reason` | Replacement relationship and reason. | Human-approved workflow action, recorded by AEGIS. | Prevents older evidence from silently disappearing. |

## Validation summary

`validation-summary.json` is written by `aegis verify run`. It is a concise
summary, not raw command output.

| Field | Data stored | Populated by | Why it is needed |
| --- | --- | --- | --- |
| `schema_version`, `run_id`, `generated_at` | Summary format, run identity, and UTC creation time. | AEGIS verification. | Identifies and timestamps a valid result. |
| `sequence` | Evaluation order: impact, gates, invariants, traceability, coverage, working-tree. | AEGIS verification. | Makes the validation process explicit. |
| `regression_selection` | Chosen strategy and its reasons. | AEGIS from impact analysis. | Explains focused versus full regression. |
| `impact` | Per-changed-path requirements, tests, coverage, and regression recommendation. | AEGIS impact analysis. | Links code changes to behavioral consequences. |
| `gates` | Build/typecheck/lint/test/security status and commands. | AEGIS from configuration and gate evidence. | Summarizes deterministic quality checks. |
| `security_note` | Limitation of the configured security gate. | AEGIS verification. | Prevents a tool result from being claimed as complete security assurance. |
| `invariants` | Rule ID, name, holds, policy, and explanatory message. | AEGIS invariant evaluation. | Shows whether governance conditions hold. |
| `traceability`, `coverage` | Audit findings, optionally annotated with exact active waivers. | AEGIS audits. | Shows broken requirement/test/spec links or coverage gaps. |
| `working_tree` | Tracked entries, untracked paths, and blocking policy findings. | AEGIS Git/guardrail audit. | Evaluates the actual change set, not only planned paths. |
| `human_diff_review` | Initial human-review marker, normally `pending`; human review is recorded in the validation-stage form. | AEGIS writes the marker; human supplies review content in the form. | Keeps automated checks distinct from human judgment. |
| `run_profile`, `bypass_status`, `bypassed_stages` | Quick-run-only information when applicable. | AEGIS from run-stage schema. | Makes reduced lifecycle behavior explicit. |
| `waived` | Present when eligible findings have active exact waivers. | AEGIS from waiver state. | Makes an exception visible rather than calling it a pass. |

### Regression selection and impact

`regression_selection` contains `mode` (`focused` or `full`),
`linked_tests_first`, `full_regression_reasons`, and `untraced_paths`. AEGIS
selects full regression for untraced paths, cross-cutting changes, or an impact
result that recommends it.

Every `impact` item has `file`, `requirements`, `linked_tests`, `uncovered`,
and `full_regression_recommended`. It answers: “This file changed; which
promised behavior and direct tests are affected?”

### Invariants

Each invariant entry has `id`, `name`, `holds`, `policy`, and `message`. The
standard rules cover coverage, citation, red-before-green evidence, regression,
scope, evidence existence, clean secrets, durable green requirements,
component baseline scope, and required solution design. Policy distinguishes
blocking, advisory, and non-waivable failures.

## Run report

`report.md` is rendered from the current graph, configuration, and validation
result. AEGIS creates it on the explicit report command; a human reads it as a
convenient summary. It includes the run purpose and stage state, evidence,
validation result, adoption baseline information when relevant, blockers, and
the handoff's next command. It does not publish, merge, push, or create a pull
request.

## Ownership summary

- **AEGIS** creates run folders, graph state, journal events, form revisions,
  evidence IDs, validation summaries, and rendered run reports.
- **Agents and humans** fill stage forms, propose requirements/designs/checks,
  and record contextual evidence.
- **Humans** approve stage closure, component/adoption decisions, and any
  permitted exact waiver.
- **Supported adapters** may add limited post-tool evidence, but do not replace
  the AEGIS workflow or create an independent run history.
