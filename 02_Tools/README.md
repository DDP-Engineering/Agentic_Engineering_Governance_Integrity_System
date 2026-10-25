<!--
Copyright (c) 2026 DDP Engineering
This project is licensed under the PolyForm Noncommercial License 1.0.0.
Noncommercial use is permitted under the license terms.
Commercial use requires a separate commercial license.
See LICENSE.txt for full terms.
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-->

# Tools

Repository setup, maintenance, and delivery-package scripts live here.

## Prompt evaluation

`evaluate_aegis_prompts.py` runs isolated AEGIS prompt scenarios against an
explicitly selected local Chat Completions server: `--profile core` for the ten
original cases, `--profile capabilities` for the fifteen capability cases with
fresh local reviewer sessions, and `--profile holdout` for a pricing domain that
never motivates prompt rules, including a chained five-session lifecycle whose
code writes `evaluate_aegis_holdout.py` restricts to a Python subset. It
preserves the payload, records model/tool evidence and context use per run and
per file read, reports configured semantic checks and per-case pass rates
beside the strict checks, and checks observable workflow outcomes. See the
[evaluation guide](../05_Software/aegis/evaluations/README.md) for baseline
commands, limits, saved evidence and controlled comparisons. Its offline
behavior tests are in `05_Software/aegis/tests/test_prompt_evaluation.py` and
`test_holdout_evaluation.py`.

The default `--max-tokens` is 16,384 per response, shared by reasoning and
visible output on models that count both. Deadlines default to 2,400 seconds
per case and 900 per request or reviewer session, suited to a local 27B model.
`--top-p`, `--top-k`, `--presence-penalty` and `--reasoning-effort` are sent
only when set; `--reasoning-effort` turns on thinking where the server supports
it (LM Studio: `reasoning_effort`), and the reasoning is never sent back with
the history. Repeated
identical tool calls, or text repeated until the output limit, end a session as
`loop`; finished responses with repeated text are counted as degenerate.
Changing budgets, sampling or the loaded context window requires a fresh
control for a strict thinking or model comparison. Each evaluated payload
supplies its own root digest, journal record format and CLI commands, so an
original and a revised payload stay comparable under one host contract.

The host documents its bounded read-only Git syntax in the model tool schema,
including scoped diffs, historical file reads and limited logs. Unavailable
read options return supported capabilities and are scored separately from
forbidden mutations. Missing-evidence scoring accepts explicit negative
execution statements and still checks actual command events. A changed harness
requires fresh original/revised runs; historical scores are not a substitute.

`evaluate_aegis_subscription.py` runs either the unchanged ten-case `core`
profile or the fifteen-case `capabilities` profile through an explicit native
Codex executable with existing ChatGPT authentication. It records model,
reasoning, configured context, output-limit availability, usage and time, with
30-second session pauses and bounded generic429 backoff. The additional
`evaluate_aegis_capabilities.py` and `evaluate_aegis_stages.py` fixtures cover
all eight step prompts, actual independent reviewer sessions, diagrams,
autopilot and context reconciliation. Build execution is AST-constrained;
Deliver stops before publication. Historical result records were removed at
the owner's request; the evaluation guide identifies the new paired collection.

## Package builders

Run the commands below from the repository root. Core release construction and
agent plugin assembly are separate operations:

| Script | Output | Verification performed by the builder |
|---|---|---|
| `build_aegis_release.py` | Core Windows/Linux archives and release records. | Managed payload inventory, complete product test suite and archive inventories. |
| `build_agent_plugins.mjs` | Five complete host package directories. | Assembly only; no test suite or host validation. |

## Core release archives

Build the current AEGIS release archives and tracked publication record with:

```text
py -3.12 02_Tools/build_aegis_release.py --version 0.15.0
```

On Linux, use `python3` in place of `py -3.12`. The build environment needs
Python 3.11+, `pytest`, Git and Node.js 22+ for the integration tests included in
the product suite. See the [development setup](../README.md#environment-and-development-setup).

`--version` must match the payload's existing `VERSION` declaration and have a
dated entry in the root changelog. The builder does not assign a new version.

The builder validates the 18-file payload, runs the complete product test
suite, and writes reproducible Windows `.zip` and Linux `.tar.gz` archives
under `07_Delivery/dist/`. Checksums and release metadata are written under
`07_Delivery/aegis-<version>/` as `SHA256SUMS`, `release-manifest.json` and
`RELEASE.md`. Rebuilding the same version replaces those generated outputs;
it does not publish them remotely.

## Agent plugin packages

With Node.js 22 or later, assemble the packages with:

```sh
node 02_Tools/build_agent_plugins.mjs
```

The default output is `07_Delivery/agent-plugins-unreleased/`, containing:

```text
aegis-opencode/
aegis-codex/
aegis-pi/
aegis-qwen/
aegis-claude/
```

Choose a fresh location for another build:

```sh
node 02_Tools/build_agent_plugins.mjs --output 07_Delivery/agent-plugins-next
```

The builder refuses to overwrite an existing `aegis-<host>` package directory.
An existing parent output directory is allowed if its package directories do
not already exist. After an interrupted build, use a fresh output location to
avoid mixing incomplete and complete packages.

Each package includes its native host resources, shared JavaScript libraries,
license notices, `install.sh` and `Install-AEGIS.cmd`. Shared libraries are
copied into `plugins/aegis/lib/` for Codex and Claude, and `lib/` for OpenCode,
Pi and Qwen. Raw integration source directories are not complete installable
packages; registering them directly can leave `lib/bridge.mjs` missing.

This script produces directories, not ZIP or tar archives. Share the complete
host directory or an archive made from it. The builder reads the existing core
version, uses vendored dependencies without fetching packages, and does not run
tests, invoke models, install into host profiles or publish to a registry.
The integration manifests take the assigned version from the core payload.

Recipients install the built package in their own environment, retaining their
own account, model and permissions. See the
[agent package guide](../06_SoftwareDocu/Agent_Plugins.md) for prerequisites,
installation, update/removal and verification limits.
