# AEGIS for Qwen Code

Portable native workflow extension for Windows and Linux. Requires Node.js 22+, Python 3.11+, Git and Qwen Code. The target checkout must already contain its installed `.agentic/aegis.py`. No credentials, model weights or machine-specific paths ship in this package; installation discovers and records local runtimes.

## Install

Extract the complete package. On Windows run `Install-AEGIS.cmd`; on Linux run `sh install.sh`. Both execute the same command available on either platform:

```text
node setup.mjs install
```

The installer writes owned resources under `QWEN_HOME/extensions/aegis` (default `~/.qwen/extensions/aegis`) and preserves the existing settings file. Restart Qwen Code, open the intended Git checkout and use `/aegis-start <software request>`. The five commands are `/aegis-start`, `/aegis-resume TASK-<id>`, `/aegis-status [TASK-<id>]`, `/aegis-check [TASK-<id>]` and `/aegis-validate TASK-<id>`. The AEGIS skill and twelve workflow operations are also available.

Optional arguments accept absolute executable/configuration paths:

```text
node setup.mjs install --config-dir <host-config> --host-cli <executable-or-JavaScript-entry> --python <python-executable> --node <node-executable> --cache <shared-job-cache>
node setup.mjs doctor
node setup.mjs update
node setup.mjs uninstall
```

`doctor` probes runtimes and host version and reports the declared resources; native command discovery remains a host check. Use `--host-cli` when a global CLI shim cannot be resolved. Windows `.cmd`, `.bat` and `.ps1` shims are intentionally not executed; provide the executable or JavaScript CLI entry instead. If executables move, supply their new paths with `update`.

Update from a freshly extracted newer package using the same `--config-dir`. Owned-file hashes are checked before using stored runtime settings; edited or missing files cause refusal. Preserve custom edits separately and restore the owned package before updating/removing it. Active or uncertain verification reservations block update/removal. Installation backups and job logs are retained; unrelated configuration and added user files are preserved. Uninstall does not require Python or the host CLI to remain available.

Use the same job-cache path across AEGIS host installations for duplicate-run protection. The default is `XDG_CACHE_HOME/aegis/integrations` or `~/.cache/aegis/integrations`. Change it through `setup.mjs update --cache`, after jobs finish; an installed package rejects a conflicting `AEGIS_CACHE`. WSL, remote backends and other operating systems need their own installation and runtime paths.

## Workflow and boundaries

The checkout's contract, steps and durable journal define the workflow. Static check commands do not run tests. Validation returns a tracked job ID; poll its results and logs. Host restarts do not stop detached verification. Commands do not grant commit, push or publication authority, and this package does not initialize or upgrade the managed AEGIS payload.

Install/update/uninstall through this package's setup script to retain its ownership and active-job checks. Host-native package managers can load the resources but do not apply these lifecycle protections; do not mix installation methods for the same extension.

The package uses the user's configured provider/model and does not set authentication or pin a model. Host permissions govern execution; prompts cannot guarantee compliance. No local or remote model was invoked during package verification.

## Qwen review agents and tools

The extension supplies two native agents, `aegis-spec-review` and `aegis-quality-review`, with `approvalMode: plan` and a read/search tool allowlist. The main conversation coordinates AEGIS. The coordinator prepares the review packet/diff and compares candidate fingerprints; the reviewers do not have a shell or mutating MCP tools. No model is specified in the agent definitions.

The local MCP server uses standard input/output only and binds to `${workspacePath}`. The installed manifest pins the discovered Node path. It exposes twelve schema-validated tools and needs no network listener. Respect any host trust or consent prompt. Run `qwen extensions list` to inspect resources and `qwen mcp list` to check connection. Slash commands are native Markdown prompt commands, so executing them normally uses the configured model.

Native discovery and MCP connection were checked with Qwen Code 0.22.3 on Windows and Ubuntu 24.04. Earlier versions and a complete model-driven review workflow have not been verified.

License: PolyForm Noncommercial License 1.0.0; see LICENSE.txt and THIRD-PARTY-NOTICES.txt.
