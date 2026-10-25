<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Planning

These documents describe the implemented **AEGIS 0.14.0** source: the core
workflow, five host integrations, artifact contracts and verification routes.
The core provides stage-by-stage user choices, configurable autopilot with
publication approval, focused verification, compact records and bounded resume
views. Project/environment context and component pages describe current positive
facts; draft/task records hold proposals and journals/Git retain history.

Delivery packages and their build records live under `07_Delivery/`. Version
assignment, package construction and publication are separate operations.
Release history belongs in the root changelog; these guides explain current
behavior and are updated with the implementation.

The maintainer checkout does not contain a root `.agentic/` deployment. Paths
under `.agentic/` here describe an installed downstream project. Repository
`AGENTS.md` defines maintenance rules; the template is the canonical core source.

Development evaluations cover all eight step files, shared guidance, actual
reviewer sessions, diagrams, autopilot and context updates. Coverage does not
establish universal model compliance or improvement from every prompt revision.
See [implementation status](05_Implementation_Phases.md#prompt-evaluation-status)
for comparisons and remaining limits.

- [Overview](00_README.md) — core workflow, host integrations and source boundaries.
- [Workflow and stages](01_Workflow_And_Stages.md) - semantic analysis protocol,
  lifecycle, quick-path criteria, review policy, resume state and host execution.
- [Artifacts and formats](02_Artifacts_And_Formats.md) — repository records,
  managed payload, host installations, job cache and derived exports.
- [Companion CLI](03_Companion_CLI.md) — Python commands, separate adapter
  operations and their read/write boundaries.
- [Collaboration and small models](04_Collaboration_And_Small_Models.md) -
  bounded semantic records, durable re-entry, independent review, user
  profiles and verification limits.
- [Implementation status](05_Implementation_Phases.md) — implemented capabilities,
  evaluation results, proposed follow-ups, verification limits and builders.
- [Small-model workflow proposal](06_Small_Model_Workflow_Simplification.md) —
  diagnosis, harness assessment, a Qwen3.8-27B baseline and a proposed
  simplification; not implemented.

The runnable product is at `05_Software/aegis/`. The managed core source is
`template/.agentic/`; host implementations are in `integrations/`. When a
planning note differs from the installed workflow, the contract, step files
and CLI help are authoritative. Host source/resources define adapter behavior.

For setup and usage, start with the [root README](../README.md),
[user documentation](../06_SoftwareDocu/00_Index.md), or
[agent packages](../06_SoftwareDocu/Agent_Plugins.md).
