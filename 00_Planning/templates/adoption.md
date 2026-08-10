<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Incremental project-owned adoption state stored as ADOPT-<32hex>.md under the
Adoptions path selected in .agentic/config.toml. Preserve gaps and uncertainty;
never invent requirements or coverage to make adoption appear complete.
-->

+++
schema = 1
artifact_type = "adoption"
id = "ADOPT-00000000000000000000000000000000"
status = "active" # active | completed | abandoned
component_id = ""
opened_at = 2026-01-01T00:00:00Z
updated_at = 2026-01-01T00:00:00Z
requirement_ids = []
+++

# Adoption - <component or bounded area>

## Scope

<Identify the one component or bounded discovery area.>

## Observed implementation

- `<repository-relative path>` - <observed responsibility or behavior>

## Observed tests

- `<real test path and optional selector>` - <behavior and files covered>

## Derived project artifacts

- Component: `<COMP-ID or pending>`
- Requirements: `<REQ-IDs or pending>`
- Specifications: `<paths or none>`

## Traceability established

| Requirement | Impacted files | Real project tests |
|---|---|---|
| `<REQ-ID>` | `<path>` | `<test path and optional selector>` |

## Unresolved gaps

- <Unknown behavior, missing test, uncertain ownership, or dangling link.>

## Resume state

- Completed discovery: <work that need not be repeated>
- Current artifacts: <repository-relative paths>
- Current gaps: <unresolved items>
- Next action: <first action for the next session>

## Event history

<!-- Append; do not rewrite earlier events. -->

| Time (UTC) | Actor | Event | Result |
|---|---|---|---|
| 2026-01-01T00:00:00Z | `<actor>` | `<factual event>` | `<result>` |

