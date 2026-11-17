# Delivery

This folder holds the **AEGIS 0.16.1** delivery archives and build records,
built locally on **2026-11-17** from `166a0b9` plus the uncommitted source
changes recorded in the build records. All download links refer to this local
build. It is not committed, tagged or published yet.

AEGIS 0.16.0 was published on 2026-11-16 under the annotated tag
`aegis-0.16.0`; its records remain in [aegis-0.16.0](aegis-0.16.0/BUILD.md).

## Download the latest built packages

| Package | Windows | Linux |
|---|---|---|
| Core workflow | [ZIP](dist/aegis-0.16.1-windows.zip) | [tar.gz](dist/aegis-0.16.1-linux.tar.gz) |
| OpenCode plugin | [ZIP](dist/agent-plugins-0.16.1/AEGIS-OpenCode-0.16.1-windows.zip) | [tar.gz](dist/agent-plugins-0.16.1/AEGIS-OpenCode-0.16.1-linux.tar.gz) |
| Codex plugin | [ZIP](dist/agent-plugins-0.16.1/AEGIS-Codex-0.16.1-windows.zip) | [tar.gz](dist/agent-plugins-0.16.1/AEGIS-Codex-0.16.1-linux.tar.gz) |
| Pi package | [ZIP](dist/agent-plugins-0.16.1/AEGIS-Pi-0.16.1-windows.zip) | [tar.gz](dist/agent-plugins-0.16.1/AEGIS-Pi-0.16.1-linux.tar.gz) |
| Qwen Code extension | [ZIP](dist/agent-plugins-0.16.1/AEGIS-Qwen-Code-0.16.1-windows.zip) | [tar.gz](dist/agent-plugins-0.16.1/AEGIS-Qwen-Code-0.16.1-linux.tar.gz) |
| Claude Code plugin | [ZIP](dist/agent-plugins-0.16.1/AEGIS-Claude-Code-0.16.1-windows.zip) | [tar.gz](dist/agent-plugins-0.16.1/AEGIS-Claude-Code-0.16.1-linux.tar.gz) |

The [documentation ZIP](dist/AEGIS-Documentation-0.16.1.zip) contains the
delivered `06_SoftwareDocu/` guide tree plus the license. Open `00_Index.md`
after extraction. Maintainer planning under `00_Planning/` remains in the
source repository; its current hashes and local changes are retained in the
build records.

## Install

For a target project, extract a core archive and follow `INSTALL.md`. The
workflow needs Python 3.11+; no runtime is embedded. Journals from earlier
versions need no migration. The `0.16.1` section of `CHANGELOG.md` lists the changes.

For a host integration, extract its complete archive and open
`INSTALLATION_GUIDE.md`, which links to the included Markdown and PDF manuals.
Run `Install-AEGIS.cmd` on Windows or `sh install.sh` on Linux. Existing users
should run `node setup.mjs update` from the new package using the same profile
options, then restart their host. See the
[package-set installation guide](dist/agent-plugins-0.16.1/INSTALL.md).

Each user supplies their own supported host application, account/provider
access, Node.js 22+, Python 3.11+ and Git. Share original archives, not installed
profiles or `runtime.json`.

## Verification and checksums

The full product suite passed: **529 passed, 2 skipped** (symlink cases that
Windows does not support). All 13 archives passed the SHA-256 check. The 75
packaged JavaScript modules and the Linux launcher permission bits were
verified, and the packaged CLI reports 0.16.1. No models were called or real host profiles changed during the
build. Native host installation, Desktop acceptance and Linux execution were
not run.

Use [SHA256SUMS](dist/SHA256SUMS) to verify all archives. See the
[build record](aegis-0.16.1/BUILD.md) and
[complete manifest](aegis-0.16.1/delivery-manifest.json) for details. Earlier
deliveries' records remain in [aegis-0.16.0](aegis-0.16.0/BUILD.md),
[aegis-0.15.0](aegis-0.15.0/BUILD.md) and
[aegis-0.14.0](aegis-0.14.0/BUILD.md).

## Layout and rebuild

```text
07_Delivery/
  dist/
    aegis-0.16.1-windows.zip
    aegis-0.16.1-linux.tar.gz
    AEGIS-Documentation-0.16.1.zip
    SHA256SUMS
    agent-plugins-0.16.1/
  aegis-0.16.1/
```

From the repository root, `py -3.12 02_Tools/build_aegis_release.py --version
0.16.1` builds core archives and records for the assigned source version.
`python 02_Tools/build_aegis_delivery.py --version 0.16.1` then builds the host
and documentation archives and the delivery records.
