<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

This folder holds the **AEGIS 0.14.0** delivery archives and build records,
rebuilt locally on **2026-10-22** from `9e3d870` plus the
delivery-preparation changes recorded in the manifest. All download links refer
to this local rebuild. It contains the current experimental prompt revisions.

## Download the latest built packages

| Package | Windows | Linux |
|---|---|---|
| Core workflow | [ZIP](dist/aegis-0.14.0-windows.zip) | [tar.gz](dist/aegis-0.14.0-linux.tar.gz) |
| OpenCode plugin | [ZIP](dist/agent-plugins-0.14.0/AEGIS-OpenCode-0.14.0-windows.zip) | [tar.gz](dist/agent-plugins-0.14.0/AEGIS-OpenCode-0.14.0-linux.tar.gz) |
| Codex plugin | [ZIP](dist/agent-plugins-0.14.0/AEGIS-Codex-0.14.0-windows.zip) | [tar.gz](dist/agent-plugins-0.14.0/AEGIS-Codex-0.14.0-linux.tar.gz) |
| Pi package | [ZIP](dist/agent-plugins-0.14.0/AEGIS-Pi-0.14.0-windows.zip) | [tar.gz](dist/agent-plugins-0.14.0/AEGIS-Pi-0.14.0-linux.tar.gz) |
| Qwen Code extension | [ZIP](dist/agent-plugins-0.14.0/AEGIS-Qwen-Code-0.14.0-windows.zip) | [tar.gz](dist/agent-plugins-0.14.0/AEGIS-Qwen-Code-0.14.0-linux.tar.gz) |
| Claude Code plugin | [ZIP](dist/agent-plugins-0.14.0/AEGIS-Claude-Code-0.14.0-windows.zip) | [tar.gz](dist/agent-plugins-0.14.0/AEGIS-Claude-Code-0.14.0-linux.tar.gz) |

The [documentation ZIP](dist/AEGIS-Documentation-0.14.0.zip) contains the
delivered `06_SoftwareDocu/` guide tree plus the license. Open `00_Index.md`
after extraction. Maintainer-only files in that folder, such as the workflow
overhead analysis, are not delivered and are not listed in the index.
Maintainer planning under `00_Planning/` remains in the source repository; its
current hashes and local changes are retained in the build records.

## Install

For a target project, extract a core archive and follow `INSTALL.md`. The
workflow needs Python 3.11+; no runtime is embedded.

For a host integration, extract its complete archive and open
`INSTALLATION_GUIDE.md`, which links to the included Markdown and PDF manuals.
Run `Install-AEGIS.cmd` on
Windows or `sh install.sh` on Linux. Existing users should run
`node setup.mjs update` from the new package using the same profile options,
then restart their host. See the [package-set installation guide](dist/agent-plugins-0.14.0/INSTALL.md).

Each user supplies their own supported host application, account/provider
access, Node.js 22+, Python 3.11+ and Git. Share original archives, not installed
profiles or `runtime.json`.

## Verification and checksums

The final full product suite passed: **548 passed, 2 skipped**.
The initial repository-deployment-dependent failures and their removal at the
user's request are retained in the build record. All 13 archives passed
inventory, byte and SHA-256 checks. The 74 packaged JavaScript modules,
81 static relative imports and Linux launcher permission bits were verified.
Documentation was refreshed: seven decks, ten changed slides rendered and
visually inspected, layout/package checks passed, and 108 local links checked.
The six installation PDFs remain current and unchanged. Documentation QA and
the software-suite result are retained from the preceding build after source
hash comparison; this rebuild reran packaging, syntax and archive checks.
No models were called or real host profiles changed. Native host installation,
Desktop acceptance and Linux execution were not run.

Use [SHA256SUMS](dist/SHA256SUMS) to verify all archives. See the
[build record](aegis-0.14.0/BUILD.md) and
[complete manifest](aegis-0.14.0/delivery-manifest.json) for details.

## Layout and rebuild

```text
07_Delivery/
  dist/
    aegis-0.14.0-windows.zip
    aegis-0.14.0-linux.tar.gz
    AEGIS-Documentation-0.14.0.zip
    SHA256SUMS
    agent-plugins-0.14.0/
  aegis-0.14.0/
```

From the repository root, `python 02_Tools/build_aegis_release.py --version
0.14.0` builds core archives and records for the assigned source version. `node
02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>` assembles
the five complete host packages for archiving.
