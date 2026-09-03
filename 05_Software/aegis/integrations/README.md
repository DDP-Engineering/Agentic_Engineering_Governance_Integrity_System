<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agent integrations

Host-specific packages for OpenCode, Codex, Pi, Qwen Code and Claude Code share the installed-AEGIS adapter, tracked verification worker, runtime discovery and owned-file installation logic.

- `opencode/`: primary agent, reviewers, commands, typed tools and loader installation.
- `codex/`: local marketplace, native plugin skill, review roles, command bridge and Codex CLI registration.
- `pi/`: native commands/tools, workflow skill, fresh reviewer launcher and auto-discovery installation.
- `qwen/`: native extension resources, two review agents, local MCP server and auto-discovery installation.
- `claude/`: native marketplace, commands/skill/review agents, hooks, MCP and owned installation.
- `shared/`: reusable implementation copied into each standalone build.
- `tests/`: executable Node behavior checks, included in the repository pytest suite through `test_agent_integrations.py` and `test_additional_integrations.py`.

Build from the repository root with `node 02_Tools/build_agent_plugins.mjs`. Source directories are not complete installable distributions until the builder copies the shared implementation into each package. See [Agent plugins](../../../06_SoftwareDocu/Agent_Plugins.md) for installation, distribution, behavior and verified limits.
