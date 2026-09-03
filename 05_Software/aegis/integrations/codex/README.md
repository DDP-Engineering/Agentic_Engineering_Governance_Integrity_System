<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS for Codex

A native Codex plugin containing the AEGIS skill, local workflow bridge and independent specification/quality review definitions. It works with local Codex CLI and Desktop hosts that support plugins, skills and custom agents. It does not add an OpenCode-style primary-agent menu.

## Install

Prerequisites: Codex CLI with `plugin add`/local marketplace support (verified target 0.151.0), Node.js 22+, Python 3.11+ and Git. Extract the assembled package. Linux: `sh install.sh`. Windows: run `Install-AEGIS.cmd`. Both support `node setup.mjs install`.

Installation uses CODEX_HOME (default ~/.codex). It copies a local marketplace there, installs two TOML review roles under agents/, and calls the native Codex CLI to register/install AEGIS. It preserves unrelated config and credentials. Use `--codex-home PATH` for another host configuration and `--codex PATH` for a custom CLI executable or codex.js launcher. Installation refuses a same-name marketplace from another source rather than replace it.

Open a new Codex task after installation and select the **aegis:aegis** skill, or request: **Use the AEGIS skill to inspect the current project and show its task status.** The skill is also available for automatic selection where its description matches. Each project must already contain its own standard AEGIS installation.

Two review roles request read-only sandbox defaults; the effective host settings and live overrides remain authoritative. Where the host does not expose custom role names, the skill delegates separate fresh reviews with the bundled prompts and reports the permission limitations. Review roles do not pin models.

## Maintenance

`node setup.mjs doctor` verifies runtimes and the Codex CLI without invoking models. `node setup.mjs update` refreshes owned files and native registration; `node setup.mjs uninstall` unregisters and removes owned files. Run these from an extracted distribution, passing the same custom CODEX_HOME when needed. Edited files and active/uncertain job locks prevent replacement/removal. Ownership covers both the local marketplace and the actual native plugin cache returned by Codex, including added or missing files. Preserve custom edits separately before retrying. Native CLI registration errors are reported explicitly; after fixing the cause, rerun update to finish registration; if registration changed the cache before failing, preserve and reconcile that reported cache conflict first.

Installation records a stable job cache. Change it with `node setup.mjs update --cache PATH` after jobs finish; a conflicting AEGIS_CACHE runtime override is rejected so lifecycle checks cannot miss the active cache.

The plugin bridge invokes the selected checkout's AEGIS CLI. It maintains no separate task database. The script role flag is a cooperative guard, not authenticated caller identity. All user/Git authority and installed workflow checkpoints remain in effect. No provider credentials, subscription changes or model requests occur during installation/doctor checks.

Shared runtime behavior and verified platform limits are documented in 06_SoftwareDocu/Agent_Plugins.md in the AEGIS repository. Native UI and a full model-driven workflow require separate verification.
