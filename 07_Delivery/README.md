# Delivery

This folder holds the **AEGIS 0.16.0** delivery archives and build records,
built locally on **2026-11-16** from `835ce72` plus the source changes recorded
in the build records, committed unchanged as `18f556b`. All download links
refer to this local build.

It was published on 2026-11-16 under the annotated tag `aegis-0.16.0`, on the
delivery-record commit `cb7459d`, as a release on the Gitea origin and on the
GitHub mirror (`DDP-Engineering/Agentic_Engineering_Governance_Integrity_System`).
Each release carries the 13 archives and a `SHA256SUMS` with bare file names;
its hashes are those of [dist/SHA256SUMS](dist/SHA256SUMS).

## Download the latest built packages

| Package | Windows | Linux |
|---|---|---|
| Core workflow | [ZIP](dist/aegis-0.16.0-windows.zip) | [tar.gz](dist/aegis-0.16.0-linux.tar.gz) |
| OpenCode plugin | [ZIP](dist/agent-plugins-0.16.0/AEGIS-OpenCode-0.16.0-windows.zip) | [tar.gz](dist/agent-plugins-0.16.0/AEGIS-OpenCode-0.16.0-linux.tar.gz) |
| Codex plugin | [ZIP](dist/agent-plugins-0.16.0/AEGIS-Codex-0.16.0-windows.zip) | [tar.gz](dist/agent-plugins-0.16.0/AEGIS-Codex-0.16.0-linux.tar.gz) |
| Pi package | [ZIP](dist/agent-plugins-0.16.0/AEGIS-Pi-0.16.0-windows.zip) | [tar.gz](dist/agent-plugins-0.16.0/AEGIS-Pi-0.16.0-linux.tar.gz) |
| Qwen Code extension | [ZIP](dist/agent-plugins-0.16.0/AEGIS-Qwen-Code-0.16.0-windows.zip) | [tar.gz](dist/agent-plugins-0.16.0/AEGIS-Qwen-Code-0.16.0-linux.tar.gz) |
| Claude Code plugin | [ZIP](dist/agent-plugins-0.16.0/AEGIS-Claude-Code-0.16.0-windows.zip) | [tar.gz](dist/agent-plugins-0.16.0/AEGIS-Claude-Code-0.16.0-linux.tar.gz) |

The [documentation ZIP](dist/AEGIS-Documentation-0.16.0.zip) contains the
delivered `06_SoftwareDocu/` guide tree plus the license. Open `00_Index.md`
after extraction. Maintainer planning under `00_Planning/` remains in the
source repository; its current hashes and local changes are retained in the
build records.

## Install

For a target project, extract a core archive and follow `INSTALL.md`. The
workflow needs Python 3.11+; no runtime is embedded. Journals from earlier
versions need no migration; a `path:` line left by the removed quick path is
ignored. The `0.16.0` section of `CHANGELOG.md` lists the changes.

For a host integration, extract its complete archive and open
`INSTALLATION_GUIDE.md`, which links to the included Markdown and PDF manuals.
Run `Install-AEGIS.cmd` on Windows or `sh install.sh` on Linux. Existing users
should run `node setup.mjs update` from the new package using the same profile
options, then restart their host. See the
[package-set installation guide](dist/agent-plugins-0.16.0/INSTALL.md).

Each user supplies their own supported host application, account/provider
access, Node.js 22+, Python 3.11+ and Git. Share original archives, not installed
profiles or `runtime.json`.

## Verification and checksums

The full product suite passed: **521 passed, 2 skipped** (symlink cases that
Windows does not support). All 13 archives passed inventory, byte and SHA-256
checks. The 75 packaged JavaScript modules, their 82 relative static imports
and the Linux launcher permission bits were verified, and the packaged CLI
reports 0.16.0. No models were called or real host profiles changed during the
build. Native host installation, Desktop acceptance and Linux execution were
not run.

Use [SHA256SUMS](dist/SHA256SUMS) to verify all archives. See the
[build record](aegis-0.16.0/BUILD.md) and
[complete manifest](aegis-0.16.0/delivery-manifest.json) for details. Earlier
deliveries' records remain in [aegis-0.15.0](aegis-0.15.0/BUILD.md) and
[aegis-0.14.0](aegis-0.14.0/BUILD.md).

## Layout and rebuild

```text
07_Delivery/
  dist/
    aegis-0.16.0-windows.zip
    aegis-0.16.0-linux.tar.gz
    AEGIS-Documentation-0.16.0.zip
    SHA256SUMS
    agent-plugins-0.16.0/
  aegis-0.16.0/
```

From the repository root, `py -3.12 02_Tools/build_aegis_release.py --version
0.16.0` builds core archives and records for the assigned source version.
`node 02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>`
assembles the five complete host packages for archiving.
