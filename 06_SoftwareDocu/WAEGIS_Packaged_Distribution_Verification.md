<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS Packaged Distribution Verification

Date: 2026-07-16  
Build host: Windows 11 x64  
WAEGIS: 0.1.0

## Built and verified

The repository-native builder downloaded and SHA-256 verified the two pinned
CPython 3.13.13 runtime assets from python-build-standalone release `20260510`,
then produced:

| Artifact | Size | Verification |
|---|---:|---|
| `waegis-0.1.0.pyz` | 1,245,558 bytes | External release hash and `version --json` smoke pass |
| `waegis-0.1.0-windows-x64.zip` | 23,789,577 bytes | Internal archive manifest and external release hash pass |
| `waegis-0.1.0-linux-x64.tar.gz` | 69,268,907 bytes | Internal archive manifest and external release hash pass |

The output also contains `release-manifest.json` and `SHA256SUMS`.

## No-system-Python Windows smoke

The Windows application archive was extracted and executed with `PATH` empty.
`waegis.cmd version --json` returned exit 0 with packaging type
`windows-x64-application-archive`. Its embedded interpreter was atomically
registered in an isolated WAEGIS home.

With the same empty `PATH`, the bundled AEGIS `.agentic/tools/run.ps1 --help`
resolved that registered interpreter and returned exit 0. This verifies the
WAEGIS and deployed AEGIS CLI path without system Python on Windows.

The build also exercised Linux symlink materialization on the Windows build
host. Relative runtime links are written as ordinary files, avoiding Windows
link privileges and `CopyFile2` sharing failures.

## Still open

- Execute the Linux archive on a clean Ubuntu 22.04 x64 machine.
- Repeat both archives on clean machines with no system Python installed.
- Exercise guard hooks through each supported adapter on those clean machines.

Network self-update is not part of this release. Archives are distributed
side-by-side manually until authenticated release signatures are designed.

