# AEGIS for Claude Code

One portable plugin for Claude Code CLI on Windows/Linux and the Code experience in Claude Desktop. Each person uses their own Claude Code account/provider and model selection. The package contains no account, token, API key or author-specific runtime path.

## Install

Use the **complete assembled `aegis-claude` package**, not this repository's source folder. Building copies the shared runtime into `plugins/aegis/lib`; installing a raw source marketplace produces missing-library errors.

Prerequisites: Claude Code CLI **2.1.259+**, Node.js **22+**, Python **3.11+**, and Git. Install Claude Code and sign in using your own account first. The plugin adds workflow resources; it does not supply a Claude subscription or API access. Target repositories need their own installed `.agentic/aegis.py` payload.

Extract the archive. On Windows, double-click `Install-AEGIS.cmd`; on Linux run `sh install.sh`. Both invoke the same installer. Or, from the extracted directory:

```sh
node setup.mjs install
node setup.mjs doctor
```

The installer registers the local `aegis-claude` marketplace and `aegis@aegis-claude` in user scope, preserving unrelated host settings. It copies the complete package under `~/.claude/aegis-marketplace`; you can remove the extracted archive directory afterward. `CLAUDE_CONFIG_DIR` is respected. It stores this user's discovered runtime paths only in the installed copy.

If discovery needs assistance:

```sh
node setup.mjs install --host-cli /absolute/path/to/claude --node /absolute/path/to/node --python /absolute/path/to/python3 --config-dir /chosen/claude-config --cache /chosen/aegis-jobs
```

On Windows quote paths with spaces, and supply `claude.exe` or its JavaScript entry rather than a `.cmd`/`.ps1` shim. When configuring another person, run setup as that person. Do not copy an installed profile or `runtime.json` to another machine; share the original package and run its installer there.

## Use

Restart Claude Code and open a repository in the CLI or Desktop **Code** tab. CLI and Desktop discover the same user installation when they use the same configuration directory and local execution environment. In the prompt box:

- `/aegis:start <software request>` loads the installed workflow and starts or resumes appropriate work.
- `/aegis:resume TASK-<id>` restores the durable task context.
- `/aegis:status` inspects current workflow state.
- `/aegis:check TASK-<id>` runs static checks, not the full test suite.
- `/aegis:validate TASK-<id>` starts tracked final verification and follows its result.

The `aegis:workflow` skill guides the coordinator. Independent `aegis:spec-review` and `aegis:quality-review` agents have Read/Grep/Glob tools and no pinned model. The local MCP server exposes status, resume, read, summary, check, scaffold, evidence, candidate, diff, run and job. Claude prefixes their names with `mcp__plugin_aegis_aegis__`. Normal host permissions and MCP consent apply; no permission bypass is installed.

SessionStart and selected PreToolUse hooks provide bounded advisory workflow context. They do not edit files, approve actions, or enforce the entire workflow. They are inactive outside a governed checkout and preserve the distinction between software development and packaging/repository-only operations.

## Update and remove

From the **new complete package**, run `node setup.mjs update`. For removal use `node setup.mjs uninstall`. Supply the same `--config-dir` when using a custom profile. Stop or inspect active AEGIS jobs before lifecycle changes. Restart Claude after an update; same-version updates refresh the actual native cache.

Owned marketplace files and native cache contents are hashed. Edited, missing, additional, linked or unowned files cause a refusal. A catalog name pointing elsewhere or a separate project/local installation also requires resolving that conflict first. Preserve customizations outside the managed payload before retrying; the installer does not discard them or blindly adopt them. Updates preserve a disabled plugin's state, including recovery after a failed registration.

Previous owned files are backed up beneath the selected config directory's `aegis-install-backups`. Job logs and Claude persistent plugin data remain after uninstall. A native registration error is reported as incomplete, never as success; correct the reported cause and rerun `update`. An unexpected partial native cache can require preserving those files before retrying. Python/Git/Claude must remain available to the lifecycle checker.

## Platform and verification boundaries

Claude Desktop for Linux is currently beta on supported Ubuntu/Debian systems; use the CLI on other distributions. Desktop plugins work with local Code sessions and supported SSH environments. **Desktop WSL sessions currently do not support plugins**; run Claude Code CLI inside WSL with a separate Linux installation instead. A Windows installation does not configure WSL, an SSH host or a cloud environment automatically. This is a Code workflow plugin, not a Chat or Cowork connector.

Verified with Claude Code 2.1.259 on Windows and Ubuntu 24.04 under WSL: native manifest/resource validation, component inventory, MCP connection, direct hook execution, actual checkout tool calls, owned-file protection, same-version update and uninstall. Unit tests also cover malformed tool input, bounded hooks, catalog collisions and failed registration recovery. No local or remote inference was used. Desktop GUI interaction, model-driven review quality and full model-led workflows remain unverified; native CLI/backend checks do not establish GUI acceptance.

Primary references: [plugins](https://code.claude.com/docs/en/plugins-reference), [hooks](https://code.claude.com/docs/en/hooks), [Desktop plugins and environment limits](https://code.claude.com/docs/en/desktop), [Linux Desktop beta](https://code.claude.com/docs/en/desktop-linux).
