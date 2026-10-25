<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS for OpenCode

This package registers Aegis, its two review subagents, five workflow commands and twelve bounded tools in the OpenCode backend. CLI/TUI and Desktop use that backend registration. Each target repository must already have its own standard AEGIS `.agentic` installation.

## Install

Extract the assembled package. Install Node.js 22+, Python 3.11+, Git and OpenCode first. Linux: `sh install.sh`. Windows: double-click `Install-AEGIS.cmd`. Both platforms can run `node setup.mjs install`.

The installer copies owned files and one loader into the OpenCode config directory without rewriting its JSON/JSONC config. Existing AEGIS agent/command definitions must be removed separately before installation; the earlier personal adapter is not migrated automatically. Use `--config-dir PATH` for a custom or project `.opencode` directory. Default discovery respects OPENCODE_CONFIG_DIR and XDG_CONFIG_HOME.

Restart the backend used by OpenCode. Choose **Aegis** from the agent selector, then use `/aegis-status`, `/aegis-start <request>`, `/aegis-resume TASK-<id>`, `/aegis-check` or `/aegis-validate TASK-<id>`. In the noninteractive CLI, use `opencode run --agent aegis "request"`; this invokes the user's configured model. The new agent does not pin a provider or model.

The package exports `index.mjs` for OpenCode plugin loading. Its JavaScript dependencies are bundled; no npm download is required. It is private and has not been published to a registry. Use either local installation or a package entry, never both.

## Maintenance

Run `node setup.mjs doctor` to check local dependencies and registrations without models. Use `node setup.mjs update` from a newly extracted package, or `node setup.mjs uninstall` to remove owned files. Pass the same custom config directory when applicable. Edited files and active/uncertain jobs stop update/removal. Backups, logs and unrelated files remain.

Installers record Node/Python executable paths for Desktop. Git must be on the backend PATH. Set executable paths with installer `--node PATH` and `--python PATH`, or AEGIS_NODE/AEGIS_PYTHON at runtime. Change an installed job cache with `node setup.mjs update --cache PATH` after verification finishes; a different runtime AEGIS_CACHE value is rejected. AEGIS_CACHE can select a cache for unpacked packages without installed runtime settings. Windows and WSL have separate configurations; remote Desktop connections need installation on the server.

Source and deeper behavior documentation are in 05_Software/aegis/integrations and 06_SoftwareDocu/Agent_Plugins.md in the AEGIS repository. Consult the release verification record for actual checks: backend verification alone does not establish native Desktop or model-driven workflow correctness.
