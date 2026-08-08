<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Installation Payload and Configuration

WAEGIS 3 copies the generic AEGIS 3 payload into a repository and generates
the repository-specific workflow policy. WAEGIS remains outside the target;
AEGIS runtime and governance state remain inside it.

## Installed layers

| Artifact | Purpose | Authority |
|---|---|---|
| `.agentic/cli/` | Local stdlib-only AEGIS CLI implementation and package metadata. | Managed payload. |
| `.agentic/tools/` | Shell, PowerShell, Python, and Node launch bridges. | Managed payload. |
| `.agentic/hooks/` | Shared policy guards and evidence hooks used by adapters. | Managed payload. |
| `.agentic/documents/` | Version-matched workflow and operator references. | Managed payload. |
| `.agentic/skills/` and host adapters | Shared procedures and host bindings. | Managed except when an adoption conflict is explicitly retained. |
| `.agentic/workflow.toml` | Live repository-specific AEGIS schema-3 policy. | Generated; only `configure` regenerates WAEGIS-owned fields. |
| `.agentic/requirements/`, knowledge, reports, runs, and workspace state | Durable project governance and runtime data. | Seeded/project-owned after creation. |
| `.agentic/install-manifest.json` | WAEGIS schema-2 success receipt and ownership baseline. | Written last by WAEGIS after validation. |

The payload inventory is closed, canonical, case-unique, and hashed before a
plan is shown. Interpreter caches, test state, dependency directories, package
metadata, and coverage output are not payload members.

## Manifest schema 2

The manifest has exactly these top-level fields:

| Field | Meaning |
|---|---|
| `manifest_version` | Closed receipt schema; currently `2`. |
| `payload_version` | Installed AEGIS semantic version. |
| `payload_digest` | Digest of the complete verified payload inventory. |
| `installed_at` | UTC publication timestamp. |
| `installed_by` | Exact WAEGIS version that published the receipt. |
| `mode` | `new`, `adopt`, `configure`, `repair`, or `upgrade`. |
| `files` | Canonical path map of size, SHA-256, and one disposition. |
| `configuration` | Allowlisted answers, generator version, and generated workflow hash. |

The manifest is not a progress journal. Its existence means the copied AEGIS
wrapper already passed help, configuration validation, and coherent run-status
smoke. It is published atomically after every other approved file.

Each `files` record has one initial ownership disposition:

- `managed`: WAEGIS may repair or three-way-upgrade the path;
- `generated`: configuration output; only `configure` may regenerate it;
- `seeded`: created only when absent, then repository-owned;
- `kept-local`: project bytes retained during a conflict;
- `sidecar`: payload review copy beside a retained conflict.

A hash records observed baseline bytes; it does not override the disposition.
Only `managed` grants automatic repair/upgrade authority.

## Configuration ownership

`workflow.toml` remains the one policy source AEGIS reads. WAEGIS owns a
deliberately narrow set of ordinary installation answers, such as language,
repository roots, selected gates, quick changed-path policy, and explicitly
interviewed guardrail settings. Comments, advanced keys, gate timeout,
`impacted_command`, and other non-owned policy survive configuration changes.
The real AEGIS parser remains the final authority on whether the resulting
schema-3 combination is valid.

`configuration.answers` contains only allowlisted normalized WAEGIS-owned
answers. `configuration.generator_version` identifies the generator and
`configuration.workflow_sha256` binds the generated workflow bytes. It stores
no clone URL, credential, arbitrary environment value, or RepoWise lifecycle
configuration.

## Responsibility boundary

- WAEGIS installs and performs ownership-limited maintenance after explicit
  operator consent.
- AEGIS reads policy and records governed workflow state and evidence.
- Repository operators own policy decisions, project data, staging, commits,
  delivery, and optional external integrations.
- Host adapters invoke the shared payload; they are not independent policy
  sources.
