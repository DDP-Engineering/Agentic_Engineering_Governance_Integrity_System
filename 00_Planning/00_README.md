<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS implementation overview

Status as of **2026-09-03**: the core is released as **AEGIS 0.9.1**.
Five optional host integrations are implemented under **Unreleased**, using
the existing version. No integration package has been published to a registry.
The runnable product is at `05_Software/aegis/`; the reusable core payload is
`05_Software/aegis/template/.agentic/`; host adapters are under
`05_Software/aegis/integrations/`; user guides are under `06_SoftwareDocu/`.

This directory records the implemented design. If it differs from the
installed payload, `.agentic/aegis.py --help`, `.agentic/AGENTS.md`, and
the payload step files are authoritative. Update this record when the
implementation or workflow contract changes. Integration behavior is defined
by its source, native resources and package guides; it does not add stages or
commands to the Python CLI.

## What AEGIS is

AEGIS is an offline-first, advisory software-development workflow. A small
standard-library Python CLI scaffolds durable files, runs configured commands,
and reports governance findings. The workflow itself is Markdown that an agent
or developer reads and follows.

The core creates no hidden run store, hosted service, hooks, or separate
permission system. Git and ordinary repository files retain workflow history.
The optional integrations add host resources and an explicit local job cache
for detached verification; that cache is operational state, not a replacement
for the repository journal. Claude Code also has bounded advisory hooks.

## Core and host integrations

The host provides the model session and its existing permission system. The
AEGIS adapter reads the nearest Git checkout's installed contract, runs its
local CLI, and returns evidence for the coordinator to record. The coordinator
maintains the journal and follows user authority; no adapter advances stages
or grants Git permission.

| Host | Implemented entry points | Independent review support |
|---|---|---|
| OpenCode | Aegis primary agent, five commands, eleven native tools. | Two read-oriented subagents. |
| Codex | Native plugin, `aegis:aegis` skill and local bridge with eleven operations. | Two custom review-role definitions and bundled review prompts. |
| Pi | Extension, skill, five commands and eleven native tools. | Launcher for separate nonpersistent review processes. |
| Qwen Code | Extension, skill, five commands and eleven local MCP tools. | Two native read-oriented agents. |
| Claude Code | Plugin, workflow skill, five namespaced commands, eleven local MCP tools and two hook event types. | Two native read-tool agents. |

Codex does not receive the five slash commands or an OpenCode-style primary
agent selector. Pi has no built-in subagent facility; its launcher creates
fresh processes. These host differences do not change the workflow contract.

Shared integration code handles runtime discovery, owned installation,
candidate fingerprints, verification jobs, cancellation and recovery. The
package builder includes this code in each distributable. Installers preserve
unrelated host configuration and do not distribute credentials or model
settings. See [artifacts](02_Artifacts_And_Formats.md) for ownership and
[collaboration](04_Collaboration_And_Small_Models.md) for review limits.

## Current model

- Six fixed ordinary stages: `frame -> specify -> design -> build -> validate
  -> deliver`.
- An eligible fix or change may use the recorded quick path:
  `frame -> build -> validate -> deliver`; size alone does not establish
  eligibility. The full criteria are in [workflow](01_Workflow_And_Stages.md).
- Existing-repository adoption is a separate `survey -> components -> close
  -> done` flow, not a seventh ordinary stage.
- Requirements, specifications, journals, knowledge pages, anchors, and
  evolution reports are plain files below `.agentic/`.
- `check` is advisory by default. `check --strict` is the optional CI
  boundary that fails on errors and configured promoted warnings.
- Explicit review is optional policy, not a stage. When enabled it records
  specification-compliance and implementation-quality verdicts with a bounded
  fix-and-re-review loop; ordinary validation remains required either way.
- `brief` is the bounded resume view; `summary` is the narrower projection
  of the latest recorded stage report.

AEGIS applies to software development. Repository maintenance, versioning,
release construction, package publication, and deployment follow the
repository's own procedures rather than opening an AEGIS journal.
Documentation-only updates in this repository are reviewed directly, outside
AEGIS, under the maintainer's scope instruction.

## Planning record

| Document | Current purpose |
|---|---|
| [01_Workflow_And_Stages.md](01_Workflow_And_Stages.md) | Lifecycle, interaction boundaries, review policy, and resume behavior. |
| [02_Artifacts_And_Formats.md](02_Artifacts_And_Formats.md) | Ownership split, directory layout, configuration, and durable formats. |
| [03_Companion_CLI.md](03_Companion_CLI.md) | Core CLI commands, separate host operations, and execution boundaries. |
| [04_Collaboration_And_Small_Models.md](04_Collaboration_And_Small_Models.md) | Branch-based collaboration and bounded re-entry for constrained models. |
| [05_Implementation_Phases.md](05_Implementation_Phases.md) | Released and unreleased implementation, verification scope, and maintenance. |

Start with the [user guide index](../06_SoftwareDocu/00_Index.md) or
[agent package guide](../06_SoftwareDocu/Agent_Plugins.md) for installation.
[Implementation status](05_Implementation_Phases.md) distinguishes verified
backend behavior from unverified Desktop UI and model-driven workflows.
