<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

This folder holds the current AEGIS 0.10.0 delivery archives and publication/build records, rebuilt on **2026-09-03**.

## Download the current packages

| Package | Windows | Linux |
|---|---|---|
| Core workflow | [ZIP](dist/aegis-0.10.0-windows.zip) | [tar.gz](dist/aegis-0.10.0-linux.tar.gz) |
| OpenCode plugin | [ZIP](dist/agent-plugins-0.10.0/AEGIS-OpenCode-0.10.0-windows.zip) | [tar.gz](dist/agent-plugins-0.10.0/AEGIS-OpenCode-0.10.0-linux.tar.gz) |
| Codex plugin | [ZIP](dist/agent-plugins-0.10.0/AEGIS-Codex-0.10.0-windows.zip) | [tar.gz](dist/agent-plugins-0.10.0/AEGIS-Codex-0.10.0-linux.tar.gz) |
| Pi package | [ZIP](dist/agent-plugins-0.10.0/AEGIS-Pi-0.10.0-windows.zip) | [tar.gz](dist/agent-plugins-0.10.0/AEGIS-Pi-0.10.0-linux.tar.gz) |
| Qwen Code extension | [ZIP](dist/agent-plugins-0.10.0/AEGIS-Qwen-Code-0.10.0-windows.zip) | [tar.gz](dist/agent-plugins-0.10.0/AEGIS-Qwen-Code-0.10.0-linux.tar.gz) |
| Claude Code plugin | [ZIP](dist/agent-plugins-0.10.0/AEGIS-Claude-Code-0.10.0-windows.zip) | [tar.gz](dist/agent-plugins-0.10.0/AEGIS-Claude-Code-0.10.0-linux.tar.gz) |

The [documentation ZIP](dist/AEGIS-Documentation-0.10.0.zip) contains the full `06_SoftwareDocu/` tree: **19 Markdown guides, eight PowerPoint decks, six installation PDFs and 11 figures**, plus the license. Open `00_Index.md` after extraction.

## Install

For a target project, extract a core archive and follow `INSTALL.md`. The workflow needs Python 3.11+; no runtime is embedded.

For a host integration, extract its complete archive and open `INSTALLATION_GUIDE.md` or `INSTALLATION_GUIDE.pdf`. Run `Install-AEGIS.cmd` on Windows or `sh install.sh` on Linux. Existing users should run `node setup.mjs update` from the new package using the same profile options, then restart their host. See the [package-set installation guide](dist/agent-plugins-0.10.0/INSTALL.md).

Each user supplies their own supported host application, account/provider access, Node.js 22+, Python 3.11+ and Git. Share the original archives, not installed profiles or `runtime.json`.

## Verification and checksums

The full product suite passed: **390 passed, 2 skipped** for Windows symlink limitations. All 13 archives passed inventory, byte and SHA-256 checks. Packaged JavaScript syntax and relative imports passed, and Linux launchers carry execute permission. No models were called and no real host profile was changed. Desktop GUI, native host installation and model-driven workflows were not run.

Use [SHA256SUMS](dist/SHA256SUMS) to verify all archives. See the [build record](aegis-0.10.0/BUILD.md) and [complete manifest](aegis-0.10.0/delivery-manifest.json) for details.

## Layout and rebuild

```text
07_Delivery/
  dist/
    aegis-0.10.0-windows.zip
    aegis-0.10.0-linux.tar.gz
    AEGIS-Documentation-0.10.0.zip
    SHA256SUMS
    agent-plugins-0.10.0/
  aegis-0.10.0/
```

From the repository root, `python 02_Tools/build_aegis_release.py --version 0.10.0` rebuilds the core archives and records. `node 02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>` assembles the five complete host packages for archiving.
