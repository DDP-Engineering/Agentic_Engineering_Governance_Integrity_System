<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

This folder holds the **AEGIS 0.13.0** delivery archives and build records.
The core pair and the documentation ZIP were rebuilt on **2026-09-17** to carry
the review-bound and fingerprint-record changes; the ten host-integration
packages are unchanged from the **2026-09-10** build. All current download links
refer to this version.

## Download the latest built packages

| Package | Windows | Linux |
|---|---|---|
| Core workflow | [ZIP](dist/aegis-0.13.0-windows.zip) | [tar.gz](dist/aegis-0.13.0-linux.tar.gz) |
| OpenCode plugin | [ZIP](dist/agent-plugins-0.13.0/AEGIS-OpenCode-0.13.0-windows.zip) | [tar.gz](dist/agent-plugins-0.13.0/AEGIS-OpenCode-0.13.0-linux.tar.gz) |
| Codex plugin | [ZIP](dist/agent-plugins-0.13.0/AEGIS-Codex-0.13.0-windows.zip) | [tar.gz](dist/agent-plugins-0.13.0/AEGIS-Codex-0.13.0-linux.tar.gz) |
| Pi package | [ZIP](dist/agent-plugins-0.13.0/AEGIS-Pi-0.13.0-windows.zip) | [tar.gz](dist/agent-plugins-0.13.0/AEGIS-Pi-0.13.0-linux.tar.gz) |
| Qwen Code extension | [ZIP](dist/agent-plugins-0.13.0/AEGIS-Qwen-Code-0.13.0-windows.zip) | [tar.gz](dist/agent-plugins-0.13.0/AEGIS-Qwen-Code-0.13.0-linux.tar.gz) |
| Claude Code plugin | [ZIP](dist/agent-plugins-0.13.0/AEGIS-Claude-Code-0.13.0-windows.zip) | [tar.gz](dist/agent-plugins-0.13.0/AEGIS-Claude-Code-0.13.0-linux.tar.gz) |

The [documentation ZIP](dist/AEGIS-Documentation-0.13.0.zip) contains the
delivered `06_SoftwareDocu/` guide tree plus the license. Open `00_Index.md`
after extraction. Maintainer-only files in that folder, such as the workflow
overhead analysis, are not delivered and are not listed in the index.

## Install

For a target project, extract a core archive and follow `INSTALL.md`. The
workflow needs Python 3.11+; no runtime is embedded.

For a host integration, extract its complete archive and open
`INSTALLATION_GUIDE.md`, which links to the included Markdown and PDF manuals.
Run `Install-AEGIS.cmd` on
Windows or `sh install.sh` on Linux. Existing users should run
`node setup.mjs update` from the new package using the same profile options,
then restart their host. See the [package-set installation guide](dist/agent-plugins-0.13.0/INSTALL.md).

Each user supplies their own supported host application, account/provider
access, Node.js 22+, Python 3.11+ and Git. Share original archives, not installed
profiles or `runtime.json`.

## Verification and checksums

The full product suite passed: **449 passed, 2 skipped** for Windows
symlink limitations. The three rebuilt archives passed inventory, byte and
SHA-256 checks, and the ten carried-forward archives matched their recorded
SHA-256 values. Packaged JavaScript syntax, relative imports and Linux launcher
permissions were verified in the 2026-09-10 build of those unchanged archives.
The three updated decks were verified from their slide XML, not by rendering. No
models were called and no real host profile was changed. Desktop GUI, native
host installation and model-driven workflows were not run.

Use [SHA256SUMS](dist/SHA256SUMS) to verify all archives. See the
[build record](aegis-0.13.0/BUILD.md) and
[complete manifest](aegis-0.13.0/delivery-manifest.json) for details.

## Layout and rebuild

```text
07_Delivery/
  dist/
    aegis-0.13.0-windows.zip
    aegis-0.13.0-linux.tar.gz
    AEGIS-Documentation-0.13.0.zip
    SHA256SUMS
    agent-plugins-0.13.0/
  aegis-0.13.0/
```

From the repository root, `python 02_Tools/build_aegis_release.py --version
0.13.0` builds core archives and records for the assigned source version. `node
02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>` assembles
the five complete host packages for archiving.
