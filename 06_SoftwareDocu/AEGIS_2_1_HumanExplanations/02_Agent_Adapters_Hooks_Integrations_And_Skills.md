<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Agent Adapters, Hooks, Integrations, and Skills

This guide explains how AEGIS connects to agent tools. These artifacts do not
replace the AEGIS policy. They let a host tool find the local workflow guidance,
run the shared guards, and record selected tool activity.

## How the pieces fit together

```text
Agent host configuration
        |
        v
Adapter or launcher
        |
        +--> AEGIS skills and workflow guidance
        |
        +--> .agentic/tools/ launcher --> .agentic/hooks/ scripts
                                           |
                                           v
                                  .agentic/workflow.toml
```

`workflow.toml` remains the only live AEGIS policy source. Agent settings,
skills, launchers, and hooks must not create a competing policy.

## Host adapters

WAEGIS copies the relevant adapter material during installation or upgrade. The
host application loads it when the repository is opened or the agent starts.
The repository operator is responsible for any host-side prerequisite, such as
trusting the project or approving a newly changed hook.

| Host | Main installed artifacts | Data stored | Who uses it | Why it is needed |
| --- | --- | --- | --- | --- |
| Codex | `.codex/config.toml`, `.codex/hooks.json`, `.codex/skills/`, `.codex/README.md` | Codex project settings, hook registrations, host-visible skills, and usage notes. | Codex. | Connects Codex to AEGIS instructions, skills, and shared hook scripts. |
| Claude Code | `.claude/settings.json`, `.claude/agents/`, `.claude/skills/`, `.claude/README.md` | Claude hook/settings configuration, agent guidance, skills, and usage notes. | Claude Code. | Connects Claude Code to the same local workflow and guard layer. |
| OpenCode | `.opencode/plugins/agentic-guard.mjs`, `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/`, `.opencode/README.md`, plus root `opencode.json` | Plugin configuration, agent prompt, workflow command shortcuts, skills, and usage notes. | OpenCode. | Loads the AEGIS guard bridge and makes workflow guidance available in OpenCode. |
| Pi | `.pi/settings.json`, `.pi/extensions/agentic-guard/`, `.pi/package.json`, `.pi/README.md` | Pi configuration, TypeScript hook bridge, package metadata, and usage notes. | Pi. | Provides Pi's transport from tool events to the shared AEGIS Python hooks. |
| Qwen Code | `.qwen/settings.json`, `.qwen/commands/`, `.qwen/skills/`, `.qwen/README.md`, plus root `QWEN.md` | Qwen settings, workflow command shortcuts, skills, and usage notes. | Qwen Code. | Makes the AEGIS workflow and safeguards available to Qwen Code. |

Root instruction files such as `AGENTS.md`, `CLAUDE.md`, and `QWEN.md` provide
host-readable workflow guidance. WAEGIS copies their AEGIS payload versions;
repository maintainers may add repository-specific instructions without
changing the shared AEGIS policy contract.

## Hooks

`.agentic/hooks/` contains the shared Python policy scripts. WAEGIS copies them
with the selected AEGIS payload. An adapter invokes them around supported tool
events; AEGIS does not require every human or every tool to use an adapter.

| Hook | Data examined or written | Invoked by | Why it is needed |
| --- | --- | --- | --- |
| `workflow_config_bootstrap.py` | Loads and validates `.agentic/workflow.toml`. | Other hooks. | Ensures all hooks use the same validated policy. |
| `guard_read_path.py` | Requested read path and protected-path policy. | Supported adapter before a read. | Blocks reads of configured protected paths. |
| `guard_write_zone.py` | Requested edit path, protected paths, and write-access policy. | Supported adapter before a dedicated edit/write operation. | Blocks writes outside the permitted policy. |
| `guard_shell_write.py` | Supported shell write operation and its in-repository targets. | Supported adapter before a shell command. | Applies write-zone restrictions even when files are changed through the shell. |
| `secret_scan.py` | Text or paths subject to configured secret patterns. | Supported adapter at its configured hook point. | Detects likely credentials and private keys before they become durable changes. |
| `delivery_preflight.py` | Proposed delivery command and delivery-command patterns. | Supported adapter before a delivery action. | Recognizes and controls actions such as publishing or merging when configured. |
| `post_tool_evidence.py` | Supported tool-event metadata and selected local run. | Supported adapter after a tool action. | Adds limited tool-use evidence to the active AEGIS run. |

Hooks return an allow/deny response on standard output; they do not use their
exit status as the policy decision. Adapter launchers fail closed when a hook
starts but cannot run correctly. The operational prerequisites are still
important: start the host from the repository root, ensure the required runtime
is available, and complete any host trust or hook-review step.

## Shared tool launcher

`.agentic/tools/` is the small shared transport layer used by adapters. The
adapter passes a host-specific tool event to the launcher; the launcher starts
the matching Python hook and converts its result into the host tool's hook
protocol. WAEGIS copies this code with the payload so each adapter follows the
same launch and failure-handling contract.

## Optional integrations

`.agentic/integrations/` stores configuration for optional tools that are not
part of the core AEGIS workflow. The standard payload currently includes
`repowise.toml`.

| Artifact or field group | Represents and stores | Created or updated by | Why it is needed |
| --- | --- | --- | --- |
| `repowise.toml` | Optional Repowise policy: schema version, provider, mode, source, supported version range, artifact/state paths, and Git-head/working-tree matching requirements. | Generated or updated by WAEGIS only when the optional integration is selected; initially copied with disabled defaults. | Lets AEGIS inspect external repository knowledge only under an explicit, locally recorded policy. |
| `.repowise/` (when present) | External Repowise knowledge-graph artifact and state data. | Repowise, not AEGIS. | Supplies optional discovery information. AEGIS treats it according to the integration policy, normally as advisory evidence. |

An optional integration does not become an independent authority over the
repository. Its state can be stale or unavailable; the AEGIS workflow records
that condition instead of silently assuming the integration is current.

## Skills

`.agentic/skills/` contains reusable, human-readable instructions for agent
work. WAEGIS copies the canonical skill material, and host adapter folders
expose compatible copies to the agent tools that support project-local skills.
Skills guide an agent through a workflow; they do not themselves grant access,
run commands, or override `workflow.toml`.

| Skill | What it guides | Why it is needed |
| --- | --- | --- |
| `agentic-adoption` | Existing-repository adoption: discovery, component mapping, baseline review, and adoption handoff. | Gives agents the correct non-behavior-changing adoption sequence. |
| `agentic-development` | Standard feature, fix, and change workflows. | Guides intake, requirements, design, checks, implementation, validation, and delivery. |
| `agentic-delivery` | Delivery and handoff preparation. | Helps agents collect the required review and verification record before handoff. |
| `documentation-audit` | Review of documentation quality and consistency. | Helps keep durable documentation aligned with the system. |
| `python-codestyle-audit` | Python style and documentation review. | Applies the repository's Python engineering conventions. |
| `regression-traceability` | Requirement/test traceability and regression selection. | Helps agents choose and explain focused versus full validation. |
| `write-component-documentation` | Creation and updating of component knowledge pages. | Makes component knowledge consistent with the supplied template. |

## Ownership summary

- **WAEGIS** deploys the versioned adapters, hooks, launchers, integration
  defaults, and skills.
- **The host agent tool** loads its own adapter files and calls hooks when its
  protocol supports them.
- **AEGIS hooks and CLI** enforce or record the policy defined by
  `workflow.toml`.
- **The repository operator** enables integrations, chooses local policy, and
  completes host-specific trust or hook-review requirements.
- **Agents and reviewers** follow the skills and workflow guidance; a skill is
  guidance, not an automatic permission.
