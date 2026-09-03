<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

This folder holds local AEGIS delivery archives and publication/build records. The current set was rebuilt on **2026-09-03**, keeping version **0.9.1**. Host integrations remain **Unreleased**; building these packages does not publish a new product version.

## Download the current packages

| Package | Windows | Linux |
|---|---|---|
| Core workflow | [ZIP](dist/aegis-0.9.1-windows.zip) | [tar.gz](dist/aegis-0.9.1-linux.tar.gz) |
| OpenCode plugin | [ZIP](dist/agent-plugins-0.9.1/AEGIS-OpenCode-0.9.1-unreleased-windows.zip) | [tar.gz](dist/agent-plugins-0.9.1/AEGIS-OpenCode-0.9.1-unreleased-linux.tar.gz) |
| Codex plugin | [ZIP](dist/agent-plugins-0.9.1/AEGIS-Codex-0.9.1-unreleased-windows.zip) | [tar.gz](dist/agent-plugins-0.9.1/AEGIS-Codex-0.9.1-unreleased-linux.tar.gz) |
| Pi package | [ZIP](dist/agent-plugins-0.9.1/AEGIS-Pi-0.9.1-unreleased-windows.zip) | [tar.gz](dist/agent-plugins-0.9.1/AEGIS-Pi-0.9.1-unreleased-linux.tar.gz) |
| Qwen Code extension | [ZIP](dist/agent-plugins-0.9.1/AEGIS-Qwen-Code-0.9.1-unreleased-windows.zip) | [tar.gz](dist/agent-plugins-0.9.1/AEGIS-Qwen-Code-0.9.1-unreleased-linux.tar.gz) |
| Claude Code plugin | [ZIP](dist/agent-plugins-0.9.1/AEGIS-Claude-Code-0.9.1-unreleased-windows.zip) | [tar.gz](dist/agent-plugins-0.9.1/AEGIS-Claude-Code-0.9.1-unreleased-linux.tar.gz) |

The [documentation ZIP](dist/AEGIS-Documentation-0.9.1.zip) contains the full `06_SoftwareDocu/` tree: **19 Markdown guides, eight PowerPoint decks, six installation PDFs and 11 figures**, plus the license. Open `00_Index.md` after extraction. The core archives include the 12 top-level Markdown guides; the separate documentation ZIP supplies the slide companions and illustrated host installation manuals. References from the guides to repository source directories require the repository checkout.

## Install

For a target project, extract a core archive and follow its `INSTALL.md`. The workflow needs Python 3.11+; no runtime is embedded.

For a host integration, extract its complete archive and open its included
`INSTALLATION_GUIDE.md` or `INSTALLATION_GUIDE.pdf`. Then run
`Install-AEGIS.cmd` on Windows or `sh install.sh` on Linux. Existing users
should run `node setup.mjs update` from the new package with the same custom
profile options, then restart their host. See the
[package-set installation guide](dist/agent-plugins-0.9.1/INSTALL.md).

Each user supplies their own supported host application, account/provider access, Node.js 22+, Python 3.11+ and Git. Share the original archives, not installed profiles or `runtime.json`. CLI and Desktop support depends on the host's plugin facilities and execution environment; see [Agent plugins](../06_SoftwareDocu/Agent_Plugins.md) for platform limits.

## Verification and checksums

The core builder's full product suite passed: **387 passed, 2 skipped** for Windows symlink limitations. All 13 archives passed inventory/content checks. The core was extracted and initialized on Windows and Ubuntu 24.04 under WSL; all five extracted plugin bridges passed on Windows. Linux plugin extraction and POSIX launchers passed, but Linux bridge execution was not repeated because Node.js 22+ was absent from that test environment PATH. No models were called, and Desktop GUI/model-led workflows were not tested.

Use [SHA256SUMS](dist/SHA256SUMS) from the `dist/` directory to verify all archives. On Linux: `sha256sum -c SHA256SUMS`. On Windows: compare `Get-FileHash -Algorithm SHA256 <archive>` with the listed digest. See the [build record](aegis-0.9.1/BUILD.md) and [complete manifest](aegis-0.9.1/delivery-manifest.json) for source hashes and verification details.

## Layout and rebuild

```text
07_Delivery/
  dist/                           ignored, current distributable files
    aegis-0.9.1-windows.zip
    aegis-0.9.1-linux.tar.gz
    AEGIS-Documentation-0.9.1.zip
    SHA256SUMS
    agent-plugins-0.9.1/           ten archives, install guide and checksums
  aegis-0.9.1/                     publication/build records
    RELEASE.md
    BUILD.md
    SHA256SUMS
    DELIVERY_SHA256SUMS
    release-manifest.json
    delivery-manifest.json
```

From the repository root, `python 02_Tools/build_aegis_release.py --version 0.9.1` runs the product suite and rebuilds the core archives/records. `node 02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>` assembles the five complete host packages; it does not create archives or checksum records. Archive each complete host folder for distribution and refresh the delivery checksums after rebuilding. The documentation ZIP copies the current Markdown and PowerPoint files without regenerating slides.

Intermediate `probe`, `before-review`, `final` and older `unreleased` output folders were backed up and removed during this refresh. Use a fresh temporary staging directory for future experiments; keep `dist/` for the current deliverables.
