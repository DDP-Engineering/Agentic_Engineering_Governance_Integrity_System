# AEGIS agent plugins

The integrations under `05_Software/aegis/integrations/` add host-native entry points to the existing AEGIS workflow. OpenCode has a primary Aegis agent, two read-only review subagents, five commands and twelve typed tools. Codex has the native `aegis` plugin, its namespaced `aegis:aegis` skill, a local command bridge, and two custom review-role definitions. Pi supplies five native commands, twelve tools, a skill and a fresh reviewer-session launcher. Qwen Code supplies a native extension with five commands, the skill, two review agents and twelve local MCP tools. Claude Code supplies five
namespaced commands, a workflow skill, two read-tool review agents, twelve
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
[Plugin_Installation/README.md](Plugin_Installation/README.md). The guides describe current installation procedures and verification scopes.
Dated package and host results remain in task/build records.

OpenCode installs into its configuration directory and adds `plugins/aegis-package.js`. Agent and command registration happens through a config hook, preserving the existing JSON/JSONC bytes. Conflicting AEGIS definitions are refused. After restarting the backend, select Aegis and use `/aegis-status` or `/aegis-start <request>`. CLI and Desktop share the configuration when they use the same backend; remote servers and WSL require their own installation.

Codex installs a local marketplace under CODEX_HOME and uses native `codex plugin marketplace add` and `codex plugin add`. The supplied catalog is named `personal`; a different configured source with that name is refused. Resolve that conflict explicitly without replacing another marketplace. Review TOML files go under CODEX_HOME/agents. Open a new task to load the `aegis:aegis` skill. Install the complete built
package: its `plugins/aegis/lib/bridge.mjs` is copied by the builder and is not
present in a raw source-only plugin installation. Codex does not provide the same primary-agent dropdown as OpenCode. A compatible Codex installation discovers the skill through the standard plugin mechanism; the skill requests independent review delegation when the project's review policy enables it.

Pi installs into `PI_CODING_AGENT_DIR/extensions/aegis` (default `~/.pi/agent/extensions/aegis`). Its skill is discovered through the extension. Five native commands dispatch workflow operations; only `aegis-start` sends a model request. Pi has no built-in subagents: `review.mjs` starts separate nonpersistent review processes with read-oriented tools. This is not an OS sandbox; real reviews use the configured model and are outside model-free package tests.

Qwen installs into `QWEN_HOME/extensions/aegis` (default `~/.qwen/extensions/aegis`). Native discovery loads the Markdown commands, skill, context and two read-oriented agents. Its MCP server runs with the workspace as its working directory and the installed Node path. `qwen extensions list` shows resources and `qwen mcp list` checks connection. Qwen slash commands are model prompts. Existing settings bytes remain unchanged for both hosts; use `--config-dir`, `--host-cli`, `--python`, `--node` and `--cache` when needed.

Runtime paths discovered by installation are stored in each package's `runtime.json`. The bridge can override executable paths with AEGIS_NODE and AEGIS_PYTHON. Installed packages reject a different AEGIS_CACHE value: change the recorded cache with installer `update --cache PATH` after verification finishes; update/removal checks both the previous and requested caches for reservations. AEGIS_CACHE is available for unpacked packages without installed runtime settings. Git must remain discoverable to the backend. Defaults store jobs under XDG_CACHE_HOME/aegis/integrations or ~/.cache/aegis/integrations so all integrations share duplicate-run detection; keep all installations on the same cache for this protection.

Codex and Claude ownership records include the native plugin cache returned by registration, in addition to the local marketplace and review roles. Update/removal refuses edited, missing or added files in that native AEGIS cache; a pre-existing unowned native cache also blocks installation. Preserve custom changes separately before retrying. The installation backup contains the previous package, roles and ownership record; job logs remain in the recorded cache.

An earlier unmanaged OpenCode setup may use explicit AEGIS configuration entries
and another cache. Preserve its custom changes and remove conflicting entries
separately before installing this package; migration is not automatic.

## Runtime and permission boundaries

The shared adapter resolves the nearest Git checkout, checks that its AEGIS payload is local, and uses argument arrays rather than interpolating user text into a shell. Commands inside the target project's AEGIS configuration retain that project's execution semantics.

OpenCode tools use its permission API and constrain mutation to the coordinator. Review agents deny arbitrary tools and allow the read operations they need. The Codex command bridge supplies `--role reviewer` to refuse mutation and cancellation, but a role flag is not authenticated identity. Codex review roles request read-only sandbox defaults; the host's effective policy and live overrides still govern access. Prompt instructions do not guarantee compliance or stronger isolation.

Every Codex bridge call is stateless. Supply the task identifier explicitly for task-scoped operations. A new process or restarted session resumes from the durable journal rather than from an adapter database: `resume` reads the task's `brief`, and the agent then reads what its `Read next` line names. OpenCode keeps an in-memory resume pointer and a compaction reminder; branch changes invalidate it.

Agents edit Frame, Requirement coverage and Design natively and tick the Done checklist. Everything else in the journal is written through the coordinator-only `journal` operation (`aegis_journal`), which calls the installed CLI: `advance` finishes a stage, `pause` stops for the user, `log` and `ruling` record events and decisions, and `verdict` records explicit review results. `advance` and `pause` print the summary block. The CLI records the agent's decision; it never judges whether a stage's work is done. With the Codex bridge, the same writes use `journal --action advance|pause|log|ruling|verdict`.

Reviewers read the full named journal and current linked files, including
untracked scope. They inspect existing assertions and focused execution evidence
before approval; final full strict proof follows both approvals. Pending final
checklist items alone are not defects. Where the role exposes a candidate
operation, it runs before inspection and after the final read; Git metadata is
supplementary. Read-only hosts that reserve fingerprints to the coordinator keep
that existing responsibility. The coordinator records both verdicts with the
`journal` operation's `verdict` action; reviewers return findings and maintain
no records. None of these instructions expands permissions.

## Verification jobs

A detached Node worker runs the actual configured test command or final `check --task ID --strict --run --json`. It stores a job ID, output, process IDs, timestamps, exit code and before/after candidate fingerprints. Another adapter instance returns the existing checkout job instead of starting a duplicate. External manually launched suites are outside that lock; inspect them separately.

Cancellation terminates the descendant process tree. Linux handling includes separate sessions created by AEGIS for configured tests. Missing/interrupted workers retain uncertain reservations for process/log inspection. Never delete an uncertain lock merely to force another test run. A successful command with a changed candidate is explicitly marked and cannot establish final proof.

The fingerprint covers Git-visible tracked and untracked non-ignored files, except task journals/evidence and Python bytecode. It excludes ignored files, external inputs and submodule contents; it is a review aid, not a tamper-proof attestation.

## Verification methods and evidence

Verify the candidate at the scope needed for the change:

1. Use isolated package tests to check assembled resources, syntax/imports,
   runtime discovery, configuration preservation and owned lifecycle.
2. Run `node setup.mjs doctor` in the selected installed environment to check
   runtime and registration metadata.
3. Open a fresh host session to check the actual visible agents, skills and
   commands for that backend/profile.
4. Exercise a model-led workflow or independent reviews only with the user's
   chosen provider and authorization.

Each result applies to its recorded candidate and environment. Package/backend
checks establish resource and protocol behavior; Desktop and model-led acceptance
require their own observations. Keep commands, exits, tested host versions and
limitations in task/build records rather than a running history in this guide.
Recorded evidence is retained in the source repository's `07_Delivery/` build
records and Git history. A distributed host package does not include the
maintainer checkout's task journals.

## Current repository context

Host-facing instructions read the installed contract's current-context guidance.
At frame/resume, open `.agentic/context/project.md` and relevant
`context/environment.md` sections when present, then select component,
requirement, source and test references. Brief lists context paths and presence,
not their bodies. Existing projects remain compatible with missing context.

Project/component documents and active contracts describe current positive
behavior and actual setup. Draft/task records hold proposals; journals and Git
retain history. Populate facts during frame/adoption, update affected sections
as implementation/setup changes, and reconcile at validate. Configuration
values and commands remain canonical in `aegis.toml`. See
[Project context](Project_Context.md).

Primary references: [OpenCode plugins](https://opencode.ai/docs/plugins/), [OpenCode config](https://opencode.ai/docs/config/), [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins), and [Codex custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Additional primary references: [Pi extensions](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md), [Pi packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md), [Qwen Code](https://github.com/QwenLM/qwen-code), and [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## Claude Code

The fifth package provides `/aegis:start`, `/aegis:resume`, `/aegis:status`, `/aegis:check` and `/aegis:validate`, a workflow skill, two independent read-tool review agents, twelve local MCP operations and bounded advisory hooks. Each installing user retains their own authentication, model and permissions. It supports Windows/Linux CLI and native local Desktop Code sessions sharing that user configuration; Desktop WSL plugin sessions are currently unsupported. Linux Desktop is beta on supported Ubuntu/Debian distributions.

Install the complete built package with its launcher or `node setup.mjs install`; do not register raw source directories as marketplaces. The installed copy includes `plugins/aegis/lib/bridge.mjs` and all runtime dependencies. Update/uninstall preserve unrelated settings, plugin data and job logs, and refuse changed owned files or active/uncertain jobs. Claude CLI 2.1.259+, Node 22+, Python 3.11+ and Git are required. See the [Claude package guide](../05_Software/aegis/integrations/claude/README.md) for profile options, troubleshooting and verification boundaries.


## Host entry points at a glance

| Host | User entry | Review mechanism |
|---|---|---|
| OpenCode | Primary **Aegis**; `/aegis-start`, `/aegis-resume`, `/aegis-status`, `/aegis-check`, `/aegis-validate` | Two read-only review subagents |
| Codex | Namespaced `aegis:aegis` skill and local bridge; no equivalent primary-agent selector | Two custom role definitions, delegated when policy enables review |
| Pi | `/aegis-start`, `/aegis-resume`, `/aegis-status`, `/aegis-check`, `/aegis-validate` | Fresh nonpersistent reviewer processes |
| Qwen Code | Same five hyphenated commands via its extension | Two read-oriented agents |
| Claude Code | `/aegis:start`, `/aegis:resume`, `/aegis:status`, `/aegis:check`, `/aegis:validate`; `aegis:workflow` skill | `aegis:spec-review` and `aegis:quality-review` |

The twelve shared operations are `status`, `resume`, `read`, `summary`, `check`,
`scaffold`, `evidence`, `journal`, `candidate`, `diff`, `run` and `job`. They are
host adapter operations, not extra `aegis.py` subcommands; `journal` and
`evidence` call the installed CLI's journal writers and evidence commands.
Review instructions do not replace final configured verification or authorize
commits, pushes or PRs. AEGIS ends when validate closes the task; Git
publication follows the repository's procedures and the user's instructions.

Claude's `SessionStart` and `PreToolUse` hooks provide bounded advisory context;
they do not mutate task journals or implement a general enforcement sandbox.
Each user's chosen host/provider remains responsible for authentication and
model access. No recipient needs the package author's sign-in.

This guide describes the current source. Complete packages are built
separately under `07_Delivery/`; use the manifest and README of the package
actually supplied. Source changes take effect in an installed host through its
normal package update procedure.

## Focused verification options

The shared run operation accepts `no_fallback: true` with `kind: test` and
`impacted: true`; the CLI bridge spells the flags `--impacted --no-fallback`.
Selection failure exits without starting the full configured test command. Use a
project-native focused command when the installed payload lacks this option or
the project runner ignores selectors. `kind: validate` rejects selection overrides
and retains complete final verification. Preview directly with the supporting
payload's `test --impacted --base HEAD --dry-run`; previews do not create jobs or
record passing evidence.

The evidence operation accepts `compact: true` for evolution only (`--compact` in
the bridge). Its response omits hashes while its on-disk evidence stays complete.
Both options are explicit so normal operations remain compatible with older
payloads. Installed personal plugins are updated only through their normal release
and installation process; changing source does not upgrade them automatically.
