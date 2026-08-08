<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Durable Governance State

This guide covers the durable knowledge AEGIS keeps about a repository. These
artifacts describe the repository's current approved behavior, boundaries, and
adoption status. They are different from `.agentic/runs/`, which records the
temporary history of one workflow execution.

## Domain overview

| Location | Represents | Main creator or publisher | Why it is durable |
| --- | --- | --- | --- |
| `.agentic/components.toml` | Component map. | Human approves; agents may propose; AEGIS reads it. | Component boundaries remain useful across many workflows. |
| `.agentic/requirements/` | Current behavioral contracts and companion specifications. | AEGIS requirement workflow publishes records after human-guided work. | Requirements remain the current contract after the originating run ends. |
| `.agentic/knowledge/` | Human-readable component understanding. | Human or agent writes from reviewed understanding. | Explains how a component works for future maintainers and agents. |
| `.agentic/reports/adoption/` | Curated adoption summaries. | Human or agent writes from reviewed adoption evidence. | Preserves baseline conclusions beyond the run that produced them. |

## Component map

`.agentic/components.toml` maps meaningful capabilities to their repository
assets. A component is a coherent unit of behavior; it is not necessarily one
folder, one class, or one service.

The installation payload creates an empty `[components]` table. During
adoption, an agent may propose component boundaries, but a human approves them
before AEGIS relies on the map for baseline or scope decisions.

Each component appears as `[components.<component-id>]`.

| Field | Data stored | Populated by | Why it is needed |
| --- | --- | --- | --- |
| `paths` | Repository-relative file paths and glob patterns owned by the component. | Human-approved component mapping. | Identifies which implementation and related assets belong to the capability. |
| `tests` | Focused test files or test roots for the component. | Human/agent during mapping and adoption. | Connects the component to direct verification. |
| `criticality` | Human severity hint, commonly `low`, `medium`, or `high`. | Human or team responsible for the component. | Focuses adoption and review attention on more consequential components. |
| `adoption_status` | Current baseline maturity, defaulting to `unknown` when omitted. | Human-approved adoption work. | Shows whether ordinary behavior-changing work is safe for the component under the configured baseline policy. |
| `owner` | Team, role, or maintainer label. | Human or team. | Identifies accountability and an escalation path. |
| `notes` | Concise boundary, risk, evidence, or special-handling context. | Human or agent, reviewed by a human. | Captures context that does not fit in a path or status field. |

### Adoption status

| Status | Meaning |
| --- | --- |
| `unknown` | Boundary is not yet understood. |
| `discovered` | Component has been found and roughly mapped. |
| `characterized` | Responsibilities, paths, risks, and checks are described. |
| `baseline-usable` | Requirements, tests, and documentation are sufficient for normal behavior-changing work. |
| `baseline-strict` | The component has stronger coverage or review expectations. |

### Component bundles

`[bundles.<bundle-id>]` groups related components only when they legitimately
need to be adopted together. A bundle does not remove the members' separate
identities.

| Field | Data stored | Populated by | Why it is needed |
| --- | --- | --- | --- |
| `components` | Required list of existing component identifiers. | Human-approved adoption mapping. | Identifies the bounded set that must move together. |
| `reason` | Why separate adoption would be misleading or unsafe. | Human or agent, then human-reviewed. | Makes the exception to component-by-component adoption explicit. |
| `adoption_status` | Optional bundle-level baseline maturity. | Adoption work. | Records the readiness of the combined concern. |
| `approved` | Human-approval flag, defaulting to `false`. | Human reviewer. | Prevents an unapproved bundle from satisfying baseline checks. |

Bundle use is additionally controlled by `adoption.allow_component_bundles` and
`adoption.max_bundle_components` in `workflow.toml`.

## Requirements and companion specifications

`.agentic/requirements/` is the canonical durable contract store. It contains
one complete current TOML snapshot per independently verifiable behavior.
Requirements are grouped by category: `functional`, `ux`, `non_functional`,
`security`, `data_privacy`, `platform`, `release`, and `testing`.

The category directories, `README.md`, `spec_template.md`, and an initially
empty `coverage_waivers.txt` are copied by WAEGIS at installation. Actual
requirement records are created or revised through AEGIS requirement-stage
forms. The workflow validates the record and publishes it atomically, so a
partially written contract does not become the current durable state.

Each requirement file is named `REQ-<CATEGORY-CODE>-<UUID>.toml` and stores:

| Field | Data stored | Populated by | Why it is needed |
| --- | --- | --- | --- |
| `schema_version` | Requirement-record format version. | AEGIS requirement workflow. | Allows strict, safe parsing of the record. |
| `id` | Stable category-prefixed UUID requirement identifier. | AEGIS requirement workflow. | Preserves identity when the wording or verification changes. |
| `category` | Requirement dimension, such as functional or security. | Human-guided stage form. | Ensures all applicable behavior dimensions are considered. |
| `status` | `Planned`, `Active`, or `Retired`. | AEGIS workflow, based on publication and validation state. | Distinguishes future, current, and superseded contracts. |
| `priority` | `Must`, `Should`, or `Could`. | Human-guided stage form. | Communicates importance and delivery expectations. |
| `requirement` | One concise, testable behavioral statement. | Human or agent, reviewed through the requirement workflow. | Defines the durable promise precisely enough to verify. |
| `rationale` | Why the behavior is required. | Human or agent. | Retains the reason for a contract after project context changes. |
| `verification` | Automated, manual, or inspection verification method. | Human-guided stage form. | Makes acceptance observable rather than implied. |
| `spec_ref` | Optional repository-relative companion-specification path. | Requirement workflow author. | Links detailed acceptance material without overloading the one-sentence contract. |
| `affected_paths` | Complete current set of relevant implementation paths. | Requirement workflow author. | Lets AEGIS calculate the behavioral impact of changed files. |
| `linked_tests` | Complete current set of exact test selectors. | Requirement workflow author. | Provides direct evidence and focused regression selection. |
| `created_on` | UTC creation time. | AEGIS requirement workflow. | Establishes record history. |
| `last_updated` | UTC latest-publication time. | AEGIS requirement workflow. | Shows when the current contract last changed. |

### Companion specifications

A requirement stays short and testable. A companion `*.spec.md` file holds
detail that would make that statement too long: data structures, interface
formats, exact messages, examples, and worked acceptance cases.

| Artifact | Data stored | Created by | Why it is needed |
| --- | --- | --- | --- |
| `spec_template.md` | Reusable Markdown structure for detailed specifications. | Copied by WAEGIS at installation. | Gives detailed specs a consistent, readable format. |
| `<requirement-id>.spec.md` | Detail for one requirement, when needed. | Requirement workflow author, normally created with the requirement. | Makes an implementation precise while keeping the requirement contract concise. |

Feature and change work should normally create a companion specification. A
small fix may omit it only when the requirement statement is already complete.
When `spec_ref` is set, AEGIS requires the target file to exist.

## Coverage waivers

`coverage_waivers.txt` is a temporary, explicit exception list for pre-existing
legacy source files that do not yet have requirement coverage. It stores one
repository-relative source-file path per non-comment line.

| Aspect | Explanation |
| --- | --- |
| Created by | WAEGIS creates the initially empty file at installation. A human-approved adoption activity may add a legacy path. |
| Read by | AEGIS coverage audit. |
| Effect | Suppresses only the missing requirement-coverage finding for that exact file. |
| Reason | Allows adoption to progress without pretending an uncovered legacy module is already fully governed. |
| Removal | Remove the line as soon as the file has an Active, test-linked requirement. AEGIS reports a stale waiver if the path becomes covered or is no longer coverable. |

It is not a skipped test, a general process waiver, or permission to leave new
behavior unspecified. New feature and fix work should create requirements and
verification instead.

## Knowledge workspace

`.agentic/knowledge/` holds human-readable technical understanding. Its
component pages explain a mapped capability's purpose, responsibilities,
implementation flow, dependencies, inputs/outputs, data contracts, workflow
integration, usage, validation, and known limitations.

| Artifact | Data stored | Created or updated by | Why it is needed |
| --- | --- | --- | --- |
| `knowledge/components/component_template.md` | Recommended headings for a component explanation. | Copied by WAEGIS. | Keeps component knowledge consistent and complete. |
| `knowledge/components/index.md` | Navigable list of component knowledge pages. | Copied by WAEGIS, then maintained by documentation authors. | Makes component knowledge discoverable. |
| `knowledge/components/<component>.md` | Reviewed explanation for one approved component. | Human or agent during component characterization/adoption; reviewed by a human. | Preserves technical context that does not belong in the structured component map or a terse requirement. |

Component pages are not generated automatically from source code and are not
created merely because a component-map entry exists. They are written once the
component boundary is understood and reviewed. The component map is the
machine-readable boundary; the knowledge page is the human explanation.

## Curated adoption reports

`.agentic/reports/adoption/` holds durable, readable summaries of adoption
conclusions. They may cover repository discovery, component mapping, component
adoption, baseline review, or adoption delivery.

| Artifact | Data stored | Created or updated by | Why it is needed |
| --- | --- | --- | --- |
| `README.md` | Report purpose, privacy limitations, and use guidance. | Copied by WAEGIS. | Defines the archive's contract. |
| `adoption_report_template.md` | Reusable report structure. | Copied by WAEGIS. | Helps reports consistently state scope, evidence, risks, baseline rationale, and follow-ups. |
| `adoption-<run-id>-<subject>.md` | Reviewed adoption conclusion, evidence summary, local-scope findings, baseline rationale, and follow-ups. | Human or agent from adoption evidence; reviewed before treating it as durable. | Preserves an understandable conclusion after the detailed run data becomes inconvenient to read. |

Reports must not include secrets, credentials, personal data, or
machine-specific details. They summarize evidence, but do not replace
`components.toml` as the source of truth for component names, paths, tests,
bundles, and baseline status.

## Ownership summary

- **WAEGIS** creates the initial durable-workspace structure and templates.
- **AEGIS** validates and atomically publishes structured requirement records,
  then reads all durable state for impact, traceability, coverage, and baseline
  checks.
- **Agents** may draft maps, requirements, knowledge, and reports.
- **Humans and responsible teams** approve component boundaries, adoption
  readiness, local policy, and the conclusions that become trusted durable
  knowledge.
