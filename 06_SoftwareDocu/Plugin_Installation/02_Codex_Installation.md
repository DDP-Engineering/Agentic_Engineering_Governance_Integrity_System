# Install AEGIS for Codex

**Source version:** named in the supplied package manifest
**Applies to:** complete packages assembled from the matching source
**Platforms:** Windows and Linux; environment limits are called out below
**Audience:** each person installing AEGIS in their own host profile

This guide installs the complete AEGIS package for Codex in the user's host profile. Repository Git operations and package publication require their own authority.

![Five-step installation flow for Codex](assets/02_Codex_flow.png)

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

Select the complete package for this host and operating system from the supplied delivery. Extract the archive completely. The resulting folder is named `aegis-codex` and must contain `setup.mjs`, `Install-AEGIS.cmd`, `install.sh`, `README.md` and `lib/` or `plugins/aegis/lib/`.

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

The owned package is copied beneath `CODEX_HOME` (normally `~/.codex`), including a local AEGIS marketplace, native plugin cache and two review-role files. Unrelated configuration and credentials are preserved. If automatic discovery needs help, use:

```text
node setup.mjs install --codex-home <codex-home> --codex <codex-executable-or-codex.js>
```

Executable and profile paths may contain spaces; quote them in the active shell.

## 3. Restart and find AEGIS

Start a **new Codex task** in the target repository. Invoke the namespaced **`aegis:aegis` skill**, or ask: “Use the AEGIS skill to inspect this project and show its task status.” Codex does not add an OpenCode-style primary-agent selector.

The plugin is available in supported Codex app and CLI environments that read the same `CODEX_HOME`. A fresh task is needed for discovery. The current Codex plugin browser can display installed plugins; this package’s installer performs its local marketplace registration through the Codex CLI.


## 4. Verify without invoking a model

From the extracted package directory run:

```text
node setup.mjs doctor
```

`node setup.mjs doctor` reports Codex, the `aegis` plugin and skill, both review roles, and `models_invoked: false`.
`doctor` checks runtime and registration metadata. It does not prove that Desktop has rendered the plugin or that a model-led workflow is correct. For acceptance, open a fresh session in a disposable governed repository, confirm the AEGIS resources are visible, and perform only a user-authorized workflow with the user’s selected provider.

## 5. Update or remove

Extract the replacement package into a new directory, then use the same profile arguments as the original installation:

```text
node setup.mjs update
node setup.mjs uninstall
```

Update and removal refuse edited/missing owned files and active or uncertain verification jobs. Preserve customizations outside the managed package. A Windows installation does not configure WSL; install separately inside each environment.

## Troubleshooting

1. If the skill is missing, close the current task, restart Codex and open a new task.
2. A different marketplace named `personal` is preserved and causes installation to stop. Resolve that catalog-name conflict explicitly.
3. Install the built archive. A raw source directory lacks the copied `plugins/aegis/lib/bridge.mjs`.
4. If Node.js, Python or Git is not found from Desktop, rerun `install`/`update` with absolute `--node`, `--python` and applicable profile/host paths.
5. If update reports an owned-file conflict, preserve the changed files, restore the installed package to a known state, then retry. Do not delete the ownership record to bypass the check.

## What success looks like

- `node setup.mjs doctor` exits successfully and reports `models_invoked: false`.
- A new Codex session discovers the documented AEGIS resources.
- The target repository contains its own `.agentic/aegis.py` and `python .agentic/aegis.py status --json` succeeds.
- The user’s host authentication and model choice remain their own.

## Primary references

- [OpenAI plugins](https://learn.chatgpt.com/docs/plugins)
- [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins)

For AEGIS-specific behavior, use the supplied package's `README.md`, the installed core contract and [agent plugin guide](../Agent_Plugins.md). Dated verification evidence belongs in [delivery records](../../07_Delivery/README.md), separately from these setup instructions.
