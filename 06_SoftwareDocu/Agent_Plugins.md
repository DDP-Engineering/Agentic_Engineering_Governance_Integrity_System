<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS agent plugins

The integrations under `05_Software/aegis/integrations/` add host-native entry points to the existing AEGIS workflow. OpenCode has a primary Aegis agent, two read-only review subagents, five commands and eleven typed tools. Codex has the native `aegis` plugin, its namespaced `aegis:aegis` skill, a local command bridge, and two custom review-role definitions. Pi supplies five native commands, eleven tools, a skill and a fresh reviewer-session launcher. Qwen Code supplies a native extension with five commands, the skill, two review agents and eleven local MCP tools. Claude Code supplies five
namespaced commands, a workflow skill, two read-tool review agents, eleven
local MCP operations and bounded advisory hooks.

All five invoke the selected Git checkout's `.agentic/aegis.py`. The checkout's installed contract and task journal remain authoritative. No integration replaces the reusable template, changes Git authority, configures providers, nor copies API keys or the author's model settings.

## Build and distribute

From the repository root, with Node.js 22 or later:

```sh
node 02_Tools/build_agent_plugins.mjs
```

The builder creates `07_Delivery/agent-plugins-unreleased/aegis-opencode/` `aegis-codex/`, `aegis-pi/`, `aegis-qwen/` and `aegis-claude/`. It refuses an existing host package directory to avoid mixing contents; the parent output directory may already exist. Use `--output PATH` for a fresh set of package destinations. All packages include their needed JavaScript libraries, shared runner, license notices and Windows/POSIX launchers. The version is read from the existing AEGIS version declaration; building these integrations does not assign a product release.

Share the appropriate complete directory or its ZIP. The OpenCode package also exports an npm-compatible entry point, but no package has been published to a registry. Runtime requirements are Node.js 22+, Python 3.11+, Git and the target host; Codex installation also requires the Codex CLI with local plugin marketplace support.

No network access is needed to assemble or copy the package. Host commands may use their own registry/cache initialization; this package makes no model requests. The vendored libraries are documented in `shared/vendor/README.md`.

## Installation and use

After extracting the chosen package, run `sh install.sh` on Linux, `Install-AEGIS.cmd` on Windows, or `node setup.mjs install` on either platform. Use `node setup.mjs doctor` for runtime and registration checks; `update` and `uninstall` manage the owned installation. Each package README explains its host-specific arguments.

For recipient-facing, illustrated walkthroughs, start with the
[combined installation manual](Plugin_Installation/00_AEGIS_Plugin_Installation_Manual.md)
or choose a host-specific Markdown/PDF guide from
[Plugin_Installation/README.md](Plugin_Installation/README.md). The figures use
sanitized isolated-install evidence; the Claude guide marks its current package
check separately because Claude Code was unavailable during the documentation
refresh.

OpenCode installs into its configuration directory and adds `plugins/aegis-package.js`. Agent and command registration happens through a config hook, preserving the existing JSON/JSONC bytes. Conflicting AEGIS definitions are refused. After restarting the backend, select Aegis and use `/aegis-status` or `/aegis-start <request>`. CLI and Desktop share the configuration when they use the same backend; remote servers and WSL require their own installation.

Codex installs a local marketplace under CODEX_HOME and uses native `codex plugin marketplace add` and `codex plugin add`. The supplied catalog is named `personal`; a different configured source with that name is refused. Resolve that conflict explicitly without replacing another marketplace. Review TOML files go under CODEX_HOME/agents. Open a new task to load the `aegis:aegis` skill. Install the complete built
package: its `plugins/aegis/lib/bridge.mjs` is copied by the builder and is not
present in a raw source-only plugin installation. Codex does not provide the same primary-agent dropdown as OpenCode. A compatible Codex installation discovers the skill through the standard plugin mechanism; the skill requests independent review delegation when the project's review policy enables it.

Pi installs into `PI_CODING_AGENT_DIR/extensions/aegis` (default `~/.pi/agent/extensions/aegis`). Its skill is discovered through the extension. Five native commands dispatch workflow operations; only `aegis-start` sends a model request. Pi has no built-in subagents: `review.mjs` starts separate nonpersistent review processes with read-oriented tools. This is not an OS sandbox; real reviews use the configured model and are outside model-free package tests.

Qwen installs into `QWEN_HOME/extensions/aegis` (default `~/.qwen/extensions/aegis`). Native discovery loads the Markdown commands, skill, context and two read-oriented agents. Its MCP server runs with the workspace as its working directory and the installed Node path. `qwen extensions list` shows resources and `qwen mcp list` checks connection. Qwen slash commands are model prompts. Existing settings bytes remain unchanged for both new hosts; use `--config-dir`, `--host-cli`, `--python`, `--node` and `--cache` when needed.

Runtime paths discovered by installation are stored in each package's `runtime.json`. The bridge can override executable paths with AEGIS_NODE and AEGIS_PYTHON. Installed packages reject a different AEGIS_CACHE value: change the recorded cache with installer `update --cache PATH` after verification finishes; update/removal checks both the previous and requested caches for reservations. AEGIS_CACHE is available for unpacked packages without installed runtime settings. Git must remain discoverable to the backend. Defaults store jobs under XDG_CACHE_HOME/aegis/integrations or ~/.cache/aegis/integrations so all integrations share duplicate-run detection; keep all installations on the same cache for this protection.

Codex and Claude ownership records include the native plugin cache returned by registration, in addition to the local marketplace and review roles. Update/removal refuses edited, missing or added files in that native AEGIS cache; a pre-existing unowned native cache also blocks installation. Preserve custom changes separately before retrying. The installation backup contains the previous package, roles and ownership record; job logs remain in the recorded cache.

An earlier unmanaged OpenCode setup may use explicit AEGIS configuration entries
and another cache. Preserve its custom changes and remove conflicting entries
separately before installing this package; migration is not automatic.

## Runtime and permission boundaries

The shared adapter resolves the nearest Git checkout, checks that its AEGIS payload is local, and uses argument arrays rather than interpolating user text into a shell. Commands inside the target project's AEGIS configuration retain that project's execution semantics.

OpenCode tools use its permission API and constrain mutation to the coordinator. Review agents deny arbitrary tools and allow the read operations they need. The Codex command bridge supplies `--role reviewer` to refuse mutation and cancellation, but a role flag is not authenticated identity. Codex review roles request read-only sandbox defaults; the host's effective policy and live overrides still govern access. Prompt instructions do not guarantee compliance or stronger isolation.

Every Codex bridge call is stateless. Supply the task identifier explicitly for task-scoped operations. A new process or restarted session resumes from the durable journal rather than from an adapter database. OpenCode keeps an in-memory resume pointer and a compaction reminder; branch changes invalidate it.

## Verification jobs

A detached Node worker runs the actual configured test command or final `check --task ID --strict --run --json`. It stores a job ID, output, process IDs, timestamps, exit code and before/after candidate fingerprints. Another adapter instance returns the existing checkout job instead of starting a duplicate. External manually launched suites are outside that lock; inspect them separately.

Cancellation terminates the descendant process tree. Linux handling includes separate sessions created by AEGIS for configured tests. Missing/interrupted workers retain uncertain reservations for process/log inspection. Never delete an uncertain lock merely to force another test run. A successful command with a changed candidate is explicitly marked and cannot establish final proof.

The fingerprint covers Git-visible tracked and untracked non-ignored files, except task journals/evidence and Python bytecode. It excludes ignored files, external inputs and submodule contents; it is a review aid, not a tamper-proof attestation.

## Verification status

Checks use temporary Git fixtures with the real AEGIS payload and isolated host configuration directories. They include Windows and Ubuntu 24.04 under WSL, OpenCode 1.18.18 backend registration, Codex 0.151.0 installation and app-server skill discovery, owned-file lifecycle, runtime resolution, output recovery, duplicate prevention and cancellation of configured subprocesses. Pi 0.84.4 and Qwen Code 0.22.3 were also checked on Windows and Ubuntu 24.04: native resources, Pi schema validation/direct status, Qwen MCP connection, protocol framing and actual workflow calls, review-launch arguments and lifecycle protection. The canonical task journal records the final commands and outcomes.

No local or remote model requests are used for these checks. Native Desktop UI interaction and a complete model-driven workflow remain unverified; common backend registration must not be described as GUI verification. For native desktop acceptance, open a fresh project session, confirm the agent/skill choices, and run an approved task with the user's chosen provider.

Primary references: [OpenCode plugins](https://opencode.ai/docs/plugins/), [OpenCode config](https://opencode.ai/docs/config/), [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins), and [Codex custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Additional primary references: [Pi extensions](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md), [Pi packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md), [Qwen Code](https://github.com/QwenLM/qwen-code), and [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## Claude Code

The fifth package provides `/aegis:start`, `/aegis:resume`, `/aegis:status`, `/aegis:check` and `/aegis:validate`, a workflow skill, two independent read-tool review agents, eleven local MCP operations and bounded advisory hooks. Each installing user retains their own authentication, model and permissions. It supports Windows/Linux CLI and native local Desktop Code sessions sharing that user configuration; Desktop WSL plugin sessions are currently unsupported. Linux Desktop is beta on supported Ubuntu/Debian distributions.

Install the complete built package with its launcher or `node setup.mjs install`; do not register raw source directories as marketplaces. The installed copy includes `plugins/aegis/lib/bridge.mjs` and all runtime dependencies. Update/uninstall preserve unrelated settings, plugin data and job logs, and refuse changed owned files or active/uncertain jobs. Claude CLI 2.1.259+, Node 22+, Python 3.11+ and Git are required. See the [Claude package guide](../05_Software/aegis/integrations/claude/README.md) for profile options, troubleshooting and verification boundaries.

Claude Code 2.1.259 native loading, inventory, MCP connection, direct hook execution and lifecycle were verified in isolated Windows and Ubuntu 24.04 profiles without model requests. Desktop UI and model-led workflow/review behavior remain unverified.

## Host entry points at a glance

| Host | User entry | Review mechanism |
|---|---|---|
| OpenCode | Primary **Aegis**; `/aegis-start`, `/aegis-resume`, `/aegis-status`, `/aegis-check`, `/aegis-validate` | Two read-only review subagents |
| Codex | Namespaced `aegis:aegis` skill and local bridge; no equivalent primary-agent selector | Two custom role definitions, delegated when policy enables review |
| Pi | `/aegis-start`, `/aegis-resume`, `/aegis-status`, `/aegis-check`, `/aegis-validate` | Fresh nonpersistent reviewer processes |
| Qwen Code | Same five hyphenated commands via its extension | Two read-oriented agents |
| Claude Code | `/aegis:start`, `/aegis:resume`, `/aegis:status`, `/aegis:check`, `/aegis:validate`; `aegis:workflow` skill | `aegis:spec-review` and `aegis:quality-review` |

The eleven shared operations are `status`, `resume`, `read`, `summary`, `check`,
`scaffold`, `evidence`, `candidate`, `diff`, `run` and `job`. They are host
adapter operations, not extra `aegis.py` subcommands. Review instructions do not
replace final configured verification or authorize commits, pushes or PRs.

Claude's `SessionStart` and `PreToolUse` hooks provide bounded advisory context;
they do not mutate task journals or implement a general enforcement sandbox.
Each user's chosen host/provider remains responsible for authentication and
model access. No recipient needs the package author's sign-in.

This guide describes the assigned **0.10.0** source and recorded implementation
checks. The version assignment did not rerun model workflows, install into real
user profiles, rebuild delivery packages, or publish to a registry. The last
delivery archives are generated separately under `07_Delivery/`.
