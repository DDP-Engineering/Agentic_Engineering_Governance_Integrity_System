<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agent integrations

## Routing

Read this page when a request mentions OpenCode, Codex, Pi, Qwen Code, Claude
Code, host commands or skills, the shared operation bridge, detached jobs,
reviewer launchers, integration installation, native cache ownership, or agent
plugin assembly. For cross-host operation semantics start in
`05_Software/aegis/integrations/shared/operations.mjs` and `adapter.mjs`; for a
host-specific resource or lifecycle change start in that host's directory.
Use the focused wrapper named in the Change map, which runs the underlying
JavaScript behavior suite.

Changes to workflow stages, artifact templates, or the canonical CLI belong to
the Reusable workflow payload or Core CLI pages. Delivery publication and
version assignment are repository operations; `02_Tools/build_agent_plugins.mjs`
only assembles the already-versioned packages.

## Purpose and boundaries

Provide native OpenCode, Codex, Pi, Qwen Code and Claude Code entry points to repository-installed AEGIS without duplicating its contract or durable task state.

## Public interface

OpenCode: Aegis primary agent, two review agents, five /aegis commands, eleven typed tools. Codex: aegis:aegis skill, two installed review-role definitions, local scripts/aegis.mjs operation bridge. Pi: native tools/commands, AEGIS skill and separate read-tool reviewer launcher. Qwen: native extension with skill, commands, two review agents and a local stdio MCP server. Claude Code: native marketplace, five namespaced commands, workflow skill, two Read/Grep/Glob reviewers, bounded advisory hooks and shared local MCP. Package setup exposes install/update/uninstall/doctor. The repository builder assembles complete packages with the existing project version.

## Invariants

- Operations that delegate workflow behavior invoke the selected checkout's
  installed `.agentic/aegis.py`; `read` reads bounded installed files,
  `candidate` and `diff` inspect Git, and `job` reads or cancels integration
  cache state. None owns a second workflow contract or durable journal.
- Static operations remain read-only; tracked verification starts explicitly,
  returns a job identifier, and exposes recorded completion rather than
  claiming synchronous success.
- Shared job reservations survive host restarts, reject duplicates, preserve
  uncertain live-process state, and cancel the complete descendant tree.
- Reviewer prompts request independent bounded review, while the host's actual
  permission system remains authoritative. Codex review-role flags are
  cooperative checks, not authentication.
- Install, update, and uninstall change only owned resources, preserve user
  configuration, and refuse unsafe conflicts or active-job replacement;
  `doctor` remains read-only.
- Package assembly preserves the declared AEGIS version and performs no model
  request or publication.

## Change map

| Change requested | Start with | Focused verification |
|---|---|---|
| Cross-host operation name, schema, or dispatch | `shared/operations.mjs`, `shared/adapter.mjs`, and `shared/bridge.mjs` | `test_agent_integrations.py::test_adapter_behavior` plus the affected host wrapper |
| Detached job persistence, duplicate prevention, or cancellation | `shared/adapter.mjs`, `shared/worker.mjs`, and `shared/process-tree.mjs` | `test_agent_integrations.py::test_adapter_behavior` |
| OpenCode or Codex resources and registration | `integrations/opencode/` or `integrations/codex/` | `test_agent_integrations.py::test_opencode_behavior`, `::test_codex_behavior`, and `::test_install_behavior` |
| Pi or Qwen resources, review, or stdio protocol | `integrations/pi/`, `integrations/qwen/`, and `shared/mcp.mjs` | the matching tests in `test_additional_integrations.py` |
| Claude resources, hooks, protocol, cache, or lifecycle | `integrations/claude/` and `shared/native-cache.mjs` | the matching test in `test_claude_integrations.py` |
| Runtime discovery or owned-file installation | `shared/runtime.mjs`, `shared/install.mjs`, `shared/host-setup.mjs`, and the host `setup.mjs` | runtime/install wrappers in `test_agent_integrations.py`, `test_additional_integrations.py`, or `test_claude_integrations.py` |
| Complete five-host package assembly | `02_Tools/build_agent_plugins.mjs` | build wrappers in the three Python integration test files |

## Key behaviors

- REQ-FUNC-ffc5802a and REQ-FUNC-1ca0ff21: backend config-hook registration with existing profile preservation.
- REQ-FUNC-92f78e33: native Codex marketplace/skill discovery and packaged bridge.
- REQ-SEC-16e8890a: independent review prompts and host-dependent read-only controls.
- REQ-DATA-5e4bf048: nearest checkout and its own installed CLI, with schema-1 parsing.
- REQ-REL-0ef6add6: persistent jobs, duplicate prevention, restart recovery and full descendant cancellation.
- REQ-PLAT-a3ae118a and REQ-REL-7a97428b: owned-file installation, backups, native Codex cache hashing, conflict and active-job refusal; installed runtime cache changes require the installer and check both previous and requested cache reservations.
- REQ-PLAT-af657d59: runtime discovery and checks without model requests.

- REQ-FUNC-0549bf24 and REQ-SEC-88bf2840: native Pi operations and fresh reviewer sessions with read tools.
- REQ-FUNC-52d2e370 and REQ-FUNC-f976517c: Qwen native resources and local MCP lifecycle/tool calls.
- REQ-PLAT-81e13664, REQ-REL-2de0ed39 and REQ-PLAT-15c09d6e: five-host assembly and Pi/Qwen owned-file lifecycle.

- REQ-FUNC-10f16f5c, REQ-FUNC-fc5a06d3, REQ-FUNC-f82635e2: native Claude resources, shared stdio transport and bounded context hooks.
- REQ-PLAT-53de04ad and REQ-REL-61e3e7c7: native Claude user registration with owned cache hashing, same-version refresh and failure recovery.

## Files

- `05_Software/aegis/integrations/opencode/` - Plugin entry,
  config/commands/prompts, and installer.
- `05_Software/aegis/integrations/codex/` - Marketplace, native plugin,
  skill/reference/role files, script bridge, and installer.
- `05_Software/aegis/integrations/pi/` - Native entry, skill, reviewer
  launcher/prompts, and setup.
- `05_Software/aegis/integrations/qwen/` - Native manifest,
  commands/skill/agents, stdio server, and setup.
- `05_Software/aegis/integrations/claude/` - Native plugin, hooks, stdio MCP,
  cache ownership, and installer.
- `05_Software/aegis/integrations/shared/` - Operations, adapter, worker,
  runtime, bridge, process tree, owned-file lifecycle, and vendored libraries.
- `05_Software/aegis/integrations/tests/` - JavaScript behavior suites.
- `05_Software/aegis/tests/test_agent_integrations.py` - OpenCode, Codex,
  shared adapter, runtime, review, and install wrappers.
- `05_Software/aegis/tests/test_additional_integrations.py` - Pi, Qwen,
  protocol, installation, and assembly wrappers.
- `05_Software/aegis/tests/test_claude_integrations.py` - Claude resources,
  hooks, protocol, lifecycle, ownership, and assembly wrappers.
- `02_Tools/build_agent_plugins.mjs` - Offline standalone package assembly.
- `06_SoftwareDocu/Agent_Plugins.md` - Install, behavior, distribution, and
  verification boundaries.
