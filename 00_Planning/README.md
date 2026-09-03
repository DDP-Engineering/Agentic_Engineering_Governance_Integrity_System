<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Planning

These documents describe the current implementation, not an unbuilt roadmap.
As of **2026-09-03**, the core is released as **AEGIS 0.9.1**; the OpenCode,
Codex, Pi, Qwen Code and Claude Code integrations are implemented under
**Unreleased**, retaining the existing version.

- [Overview](00_README.md) — core workflow, host integrations and source boundaries.
- [Workflow and stages](01_Workflow_And_Stages.md) — lifecycle, quick-path criteria,
  review policy, resume state and host execution.
- [Artifacts and formats](02_Artifacts_And_Formats.md) — repository records,
  managed payload, host installations, job cache and derived exports.
- [Companion CLI](03_Companion_CLI.md) — Python commands, separate adapter
  operations and their read/write boundaries.
- [Collaboration and small models](04_Collaboration_And_Small_Models.md) —
  durable re-entry, independent review, user profiles and verification limits.
- [Implementation status](05_Implementation_Phases.md) — completed capabilities,
  tested environments, remaining checks, builders and maintenance rules.

The runnable product is at `05_Software/aegis/`. The managed core source is
`template/.agentic/`; host implementations are in `integrations/`. When a
planning note differs from the installed workflow, the contract, step files
and CLI help are authoritative. Host source/resources define adapter behavior.

For setup and usage, start with the [root README](../README.md),
[user documentation](../06_SoftwareDocu/00_Index.md), or
[agent packages](../06_SoftwareDocu/Agent_Plugins.md).
