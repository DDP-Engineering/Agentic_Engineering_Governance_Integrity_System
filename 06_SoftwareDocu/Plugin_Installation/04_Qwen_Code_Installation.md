<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Install AEGIS for Qwen Code

**Applies to:** AEGIS 0.9.1 working-tree plugin package (Unreleased)
**Platforms:** Windows and Linux; environment limits are called out below
**Audience:** each person installing AEGIS in their own host profile

This guide installs the complete AEGIS package for Qwen Code. It does not publish the plugin or modify the selected project’s Git history.

![Five-step installation flow for Qwen Code](assets/04_Qwen_Code_flow.png)

*Figure 1. Use the package that matches the host and operating system; then verify it before opening a governed repository.*

## Before you begin

AEGIS has two separate parts:

1. The **core workflow** belongs in every target Git repository as `.agentic/`.
2. The **host plugin** belongs in each user’s harness profile and provides the AEGIS entry points.

Install the core from `aegis-0.9.1-windows.zip` or `aegis-0.9.1-linux.tar.gz`. Copy its `.agentic/` directory to the repository root, then run:

```text
python .agentic/aegis.py init
```

Use `python3` on Linux when that is the available command. Git, Python 3.11+ and Node.js 22+ must be visible to the harness. Install and authenticate the host application with the user’s own account/provider first. The AEGIS package includes no subscription, API key, model configuration or machine-specific runtime settings.

Verify the archive digest against `07_Delivery/dist/SHA256SUMS`. Do not use a raw integration source directory: only the assembled delivery archive contains the complete shared library.


## 1. Choose and extract the package

Use `AEGIS-Qwen-Code-0.9.1-unreleased-windows.zip` on Windows or `AEGIS-Qwen-Code-0.9.1-unreleased-linux.tar.gz` on Linux. Extract the archive completely. The resulting folder is named `aegis-qwen` and must contain `setup.mjs`, `Install-AEGIS.cmd`, `install.sh`, `README.md` and `lib/` or `plugins/aegis/lib/`.

Do not run installation from inside the ZIP viewer. Open a terminal in the extracted package directory.

## 2. Install for this user

Windows users can double-click `Install-AEGIS.cmd`. Linux users can run:

```sh
sh install.sh
```

The equivalent command on both platforms is:

```text
node setup.mjs install
```

The owned package is copied beneath `QWEN_HOME/extensions/aegis` (normally `~/.qwen/extensions/aegis`). Unrelated configuration and credentials are preserved. If automatic discovery needs help, use:

```text
`node setup.mjs install --config-dir <qwen-config> --host-cli <qwen-executable-or-cli.js>`
```

Executable and profile paths may contain spaces; quote them in the active shell.

## 3. Restart and find AEGIS

Restart Qwen Code in the target repository. Use `qwen extensions list` to see resources and `qwen mcp list` to check the local MCP connection. A session provides `/aegis-start`, `/aegis-resume`, `/aegis-status`, `/aegis-check` and `/aegis-validate` plus two review agents.

The AEGIS package installs into the Qwen Code harness. If using the Qwen Code Companion in VS Code, restart the Qwen session after installation; the Companion itself is a separate IDE integration.


## 4. Verify without invoking a model

From the extracted package directory run:

```text
node setup.mjs doctor
```

`node setup.mjs doctor` reports Qwen Code, five commands, eleven tools, two reviewers and `models_invoked: false`. The evidence image below comes from an isolated Windows profile using Qwen Code 0.23.0.

![Recorded package installation evidence for Qwen Code](assets/04_Qwen_Code_evidence.png)

*Figure 2. Recorded, sanitized command/package evidence from 2026-09-03. Paths are replaced with placeholders; results are not simulated.*

`doctor` checks runtime and registration metadata. It does not prove that Desktop has rendered the plugin or that a model-led workflow is correct. For acceptance, open a fresh session in a disposable governed repository, confirm the AEGIS resources are visible, and perform only a user-authorized workflow with the user’s selected provider.

## 5. Update or remove

Extract the replacement package into a new directory, then use the same profile arguments as the original installation:

```text
node setup.mjs update
node setup.mjs uninstall
```

Update and removal refuse edited/missing owned files and active or uncertain verification jobs. Preserve customizations outside the managed package. A Windows installation does not configure WSL; install separately inside each environment.

## Troubleshooting

1. On Windows, `--host-cli` must name the executable or JavaScript CLI entry, not a shell shim.
2. If the MCP connection is absent, rerun `doctor`, check `qwen mcp list`, and restart Qwen Code.
3. Do not mix this owned-file installer with another installation of the same extension.
4. If Node.js, Python or Git is not found from Desktop, rerun `install`/`update` with absolute `--node`, `--python` and applicable profile/host paths.
5. If update reports an owned-file conflict, preserve the changed files, restore the installed package to a known state, then retry. Do not delete the ownership record to bypass the check.

## What success looks like

- `node setup.mjs doctor` exits successfully and reports `models_invoked: false`.
- A new Qwen Code session discovers the documented AEGIS resources.
- The target repository contains its own `.agentic/aegis.py` and `python .agentic/aegis.py status --json` succeeds.
- The user’s host authentication and model choice remain their own.

## Primary references

- [Qwen Code extensions](https://github.com/QwenLM/qwen-code/blob/main/docs/users/extension/introduction.md)
- [Qwen Code overview](https://github.com/QwenLM/qwen-code/blob/main/docs/users/overview.md)

For AEGIS-specific behavior, the packaged `README.md`, `06_SoftwareDocu/Agent_Plugins.md` and `07_Delivery/aegis-0.9.1/BUILD.md` are authoritative for this working-tree build.
