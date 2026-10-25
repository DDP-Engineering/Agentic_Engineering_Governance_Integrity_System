<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Install AEGIS for Pi

**Source version:** AEGIS 0.14.0
**Applies to:** complete packages assembled from the matching source
**Platforms:** Windows and Linux; environment limits are called out below
**Audience:** each person installing AEGIS in their own host profile

This guide installs the complete AEGIS package for Pi in the user's host profile. Repository Git operations and package publication require their own authority.

![Five-step installation flow for Pi](assets/03_Pi_flow.png)

*Figure 1. Use the package that matches the host and operating system; then verify it before opening a governed repository.*

## Before you begin

AEGIS has two separate parts:

1. The **core workflow** belongs in every target Git repository as `.agentic/`.
2. The **host plugin** belongs in each user’s harness profile and provides the AEGIS entry points.

Use the core payload from the supplied release, or `05_Software/aegis/template/.agentic/` when installing from this source checkout. Copy `.agentic/` to the target repository root, then run:

```text
python .agentic/aegis.py init
```

`init` creates each missing `context/project.md` and `context/environment.md` and preserves existing project files. Populate verified current purpose, responsibilities and setup during frame/adoption. Keep proposals in draft/task records and history in journals/Git. Configure actual verification commands and layout in `.agentic/aegis.toml`; see [Project context](../Project_Context.md).

Use `python3` on Linux when that is the available command. Git, Python 3.11+ and Node.js 22+ must be visible to the harness. Install and authenticate the host application with the user’s own account/provider first. The AEGIS package includes no subscription, API key, model configuration or machine-specific runtime settings.

Verify an archive against the checksum manifest supplied with that delivery. Use a complete assembled package with its shared libraries. The package manifest and README identify the actual version and supported installation options.


## 1. Choose and extract the package

Select the complete package for this host and operating system from the supplied delivery. Extract the archive completely. The resulting folder is named `aegis-pi` and must contain `setup.mjs`, `Install-AEGIS.cmd`, `install.sh`, `README.md` and `lib/` or `plugins/aegis/lib/`.

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

The owned package is copied beneath `PI_CODING_AGENT_DIR/extensions/aegis` (normally `~/.pi/agent/extensions/aegis`). Unrelated configuration and credentials are preserved. If automatic discovery needs help, use:

```text
node setup.mjs install --config-dir <pi-config> --host-cli <pi-executable-or-cli.js>
```

Executable and profile paths may contain spaces; quote them in the active shell.

## 3. Restart and find AEGIS

Restart Pi in the target repository. Use `/aegis-status`, `/aegis-start <software request>`, `/aegis-resume TASK-<id>`, `/aegis-check` and `/aegis-validate TASK-<id>`. Pi supplies a skill and twelve workflow operations; it does not add an OpenCode-style primary-agent selector.

Pi is a terminal harness. Install separately in Windows, Linux, WSL, SSH or other environments because each has its own configuration and executable paths.


## 4. Verify without invoking a model

From the extracted package directory run:

```text
node setup.mjs doctor
```

`node setup.mjs doctor` reports Pi, five commands, twelve tools and `models_invoked: false`.
`doctor` checks runtime and registration metadata. It does not prove that Desktop has rendered the plugin or that a model-led workflow is correct. For acceptance, open a fresh session in a disposable governed repository, confirm the AEGIS resources are visible, and perform only a user-authorized workflow with the user’s selected provider.

## 5. Update or remove

Extract the replacement package into a new directory, then use the same profile arguments as the original installation:

```text
node setup.mjs update
node setup.mjs uninstall
```

Update and removal refuse edited/missing owned files and active or uncertain verification jobs. Preserve customizations outside the managed package. A Windows installation does not configure WSL; install separately inside each environment.

## Troubleshooting

1. On Windows, `--host-cli` must name the executable or JavaScript CLI entry, not a `.cmd`, `.bat` or `.ps1` shim.
2. If the commands are absent, confirm the files exist below `PI_CODING_AGENT_DIR/extensions/aegis`, then restart Pi.
3. Pi review helpers start separate sessions and use the user’s configured model; `doctor` does not start them.
4. If Node.js, Python or Git is not found from Desktop, rerun `install`/`update` with absolute `--node`, `--python` and applicable profile/host paths.
5. If update reports an owned-file conflict, preserve the changed files, restore the installed package to a known state, then retry. Do not delete the ownership record to bypass the check.

## What success looks like

- `node setup.mjs doctor` exits successfully and reports `models_invoked: false`.
- A new Pi session discovers the documented AEGIS resources.
- The target repository contains its own `.agentic/aegis.py` and `python .agentic/aegis.py status --json` succeeds.
- The user’s host authentication and model choice remain their own.

## Primary references

- [Pi documentation](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/index.md)
- [Pi packages and extensions](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md)

For AEGIS-specific behavior, use the supplied package's `README.md`, the installed core contract and [agent plugin guide](../Agent_Plugins.md). Dated verification evidence belongs in [delivery records](../../07_Delivery/README.md), separately from these setup instructions.
