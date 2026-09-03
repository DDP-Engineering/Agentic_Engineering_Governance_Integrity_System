<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 05 - Implementation phases

The original core implementation plan is complete. This document records the
assigned **AEGIS 0.10.0** project and its five host integrations as of
**2026-09-03**. The existing `0.9.1` archives remain the last built delivery
set; assigning a source version does not publish packages to a registry.

## Completed implementation

| Area | Implemented outcome |
|---|---|
| Workflow payload | A managed `.agentic/` payload with the full contract, six ordinary stage files, adoption instructions, a shared evidence-led semantic analysis cycle, and reusable artifact templates. |
| Durable artifacts | Structured Frame cards, atomic Requirement coverage, proportionate task designs, TOML requirements, Markdown specs/knowledge/journals, append-only rulings, replaceable handoffs/stage reports, and anchor/evolution JSON evidence. |
| Companion CLI | Offline-first standard-library `aegis.py` with installation, scaffolding, traceability, configured test execution, reporting, and machine-readable output. |
| Validation | A 21-check advisory catalog, optional strict CI enforcement, impacted-test selection, configured command timeouts, anchors, evolution, and delivery reporting. |
| Coordination | One-level child tasks, bounded `brief`/ `summary` views, explicit review policy, and durable handoff state for cross-session/model work. |
| Host integrations | OpenCode primary/review agents, Codex plugin/skill/review roles, Pi and Qwen extensions, and Claude Code plugin/commands/review agents/hooks. |
| Shared adapter runtime | Eleven operations, checkout-local CLI invocation, candidate comparison, detached verification jobs, duplicate prevention, cancellation and restart recovery. |
| Host package lifecycle | Windows/POSIX launchers, runtime discovery, owned-file installation/update/removal, backups and protection of active/uncertain jobs. |
| Documentation and delivery | User guides in `06_SoftwareDocu/`, planning records, core release builder and separate five-host package builder, with outputs under `07_Delivery/`. |

## Current product boundaries

The runnable implementation remains under:

```text
05_Software/aegis/
  template/.agentic/       installable managed payload
  integrations/
    opencode/              OpenCode resources and setup
    codex/                 Codex marketplace/plugin resources and setup
    pi/                    Pi extension and reviewer launcher
    qwen/                  Qwen extension and MCP entry point
    claude/                Claude marketplace/plugin, MCP and hooks
    shared/                runtime, adapters, workers, lifecycle and vendored libraries
    tests/                 JavaScript behavior tests
  tests/                   Python suite, including integration test wrappers
  README.md                package overview

02_Tools/
  build_aegis_release.py   core release archive and publication-record builder
  build_agent_plugins.mjs  complete five-host package directory builder
```

The root `.agentic/` directory is an installed copy used to govern this
repository. It is not the product source of truth. Update the template first,
then copy the exact managed payload into root or downstream repositories and
run `init`. Host integrations are a separate source tree: their builder copies
shared libraries into each package. Installing raw source as a marketplace
omits those libraries and can cause the missing `lib/bridge.mjs` failure.

## 0.9.1 implementation state

Version 0.9.1 adds the `trace` requirement-register export in Markdown and CSV,
with corrected literal text rendering, omission reporting, and category labels.
The repository's impacted-test command now uses its configured Python runtime.

## 0.10.0 workflow improvements

The working tree strengthens early-stage idea analysis without changing the
six stages, Python CLI syntax, adapter operations, host authentication, or
stage sequence or adapter interface:

- the managed contract defines **Analyze -> Challenge -> Write -> Audit** and
  `STATED`/`OBSERVED`/`INFERRED`/`UNKNOWN` evidence labels;
- Frame writes a durable idea card before branch and journal mechanics and
  treats its checkpoint as scope acceptance rather than implementation;
- Specify builds a behavior inventory and atomic coverage table, uses semantic
  split/reuse rules, derives concrete verification, and escalates exact
  contracts to specs;
- Design uses 30 lines as a default rather than a cap, expands with risk,
  traces decisions and test seams, and keeps proposed architecture in the
  task;
- Validate reconciles that proposal with built code, updates canonical
  current-state component knowledge, and retains the proposal as historical
  evidence;
- Markdown guides and the four affected PowerPoint companions are synchronized.

The final working-tree proof for this change completed **390 tests with two
platform-dependent skips**, Ruff passed, both independent review roles
approved the unchanged candidate, all 43 affected-deck slides were inspected,
and all four template-fidelity checks passed. Local-model execution was
excluded by instruction, so the 64K/offline-model design remains a prompt
contract rather than measured model compliance.

## 0.9.0 coordination baseline

Version 0.9.0 introduced the coordinated-workflow capabilities:

- deterministic `brief` resume output distinct from `summary`;
- optional explicit review with `enabled` and `max_fix_cycles`;
- independent specification-compliance and implementation-quality verdicts;
- append-only rulings and stage-bound handoffs;
- visible one-level child tasks;
- expanded check coverage for configuration, manual verification, review
  evidence, stage zones, and command execution;
- synchronized Markdown and presentation documentation.

The root repository deliberately enables explicit review with two permitted
fix cycles. That is repository configuration, not a new workflow stage.

## Integration verification status

The implementation has been checked with real installed AEGIS payloads in
temporary Git fixtures and isolated host profiles. The following are verified
backend/native-resource observations on **Windows and Ubuntu 24.04 under WSL**:

| Host version tested | Observed coverage |
|---|---|
| OpenCode 1.18.18 | Backend registration, agent/command/tool resources and adapter workflow calls. |
| Codex 0.151.0 | Native marketplace/plugin lifecycle, app-server skill discovery and command bridge calls. |
| Pi 0.84.4 | Native extension/skill/command/tool discovery, schema validation, direct status and reviewer launch arguments. |
| Qwen Code 0.22.3 | Native extension inventory, MCP connection/protocol and workflow calls. |
| Claude Code 2.1.259 | Native plugin inventory/loading, MCP connection, direct advisory hook execution and owned lifecycle. |

Shared tests exercise runtime resolution, configuration preservation, owned
content conflicts, tracked output recovery, duplicate prevention, cancellation
and uncertain-worker handling. The [recorded integration implementation proof](../.agentic/tasks/TASK-7616551e.md)
on 2026-09-03 completed the configured Windows product suite with **387 passed,
2 skipped**, Ruff passing and no static-check errors. The two skips concern
Windows symlink availability/semantics; existing older-journal warnings and
the bounded scan of vendored code were recorded as limitations. This is dated
implementation evidence, not a promise that every subsequent checkout is green.

No local or remote model requests were made for those checks. Native Desktop
UI interaction, full model-driven workflows and actual model-led independent
reviews remain unverified. Backend discovery is not GUI acceptance, and declared
tool restrictions do not establish OS isolation. Claude supports native local
Desktop Code sessions sharing its configuration; Desktop WSL plugin sessions
are currently unsupported. Linux Claude Desktop is beta. Host support may
change independently of these packages; consult the
[package guides](../06_SoftwareDocu/Agent_Plugins.md) for setup and current limits.

## Two separate builders

| Builder | Purpose and output |
|---|---|
| `python 02_Tools/build_aegis_release.py --version <x.y.z>` | Builds the core release with a matching changelog/version, validates the 15-file payload, runs the product suite, checks Windows/Linux archive inventories, and writes hashes/metadata under `07_Delivery/aegis-<version>/`. |
| `node 02_Tools/build_agent_plugins.mjs --output <fresh-output-directory>` | Uses the existing core version and assembles five complete host package directories, including shared libraries and launchers. Refuses to overwrite existing host package directories; performs no registry publication or model requests. |

Distribute complete host directories or archives made from them. Installation
records discovered runtime paths for each user's own environment. A package
build does not replace host lifecycle verification or authorize a release.

## Maintenance rules

1. Treat `template/.agentic/` as the source of managed workflow behavior.
2. Update tests when CLI behavior changes; run focused checks first and the
   product suite before release.
3. Update the relevant user and planning documentation in the same change when
   commands, workflow contracts, artifact formats, or configuration change.
4. Keep the template generic. Do not add this repository's task history,
   release entries, or project-specific facts to the downstream starter files.
5. Treat versioning, archive construction, and publication records as
   repository operations. Do not open a workflow journal for the release
   itself.
6. Use the core release builder for versioned core archives and the agent
   package builder for complete integrations. Preserve the existing version
   unless a version assignment is explicitly requested.
7. Keep host setup and shared-runtime changes covered by focused behavior tests,
   then run the configured full suite and strict check on the final candidate.
   Review documentation-only work directly, outside AEGIS; do not create workflow
   journals or tests that assert prose or links for those updates.
8. Record tested host versions and platforms. Keep backend, Desktop UI and
   model-workflow evidence distinct; do not imply unperformed verification.

Future work begins from the current implementation and its tests, not from the
obsolete pre-implementation phase estimates that this document replaces.
