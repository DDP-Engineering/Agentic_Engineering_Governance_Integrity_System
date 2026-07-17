<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS Lifecycle Live Verification

Date: 2026-07-16  
Host: Windows 11 x64  
WAEGIS: 0.1.0 source checkout  
AEGIS baseline: 0.4.0

## Result

The core lifecycle completed successfully in isolated real Git repositories.
Every scripted command used `--json`; each invocation emitted one JSON
envelope and performed no prompting.

| Journey | Evidence | Result |
|---|---|---|
| `new` | Empty target to verified bootstrap commit, real payload and wrappers | Pass |
| `adopt` | Existing Python Git repo to committed `chore/aegis-adoption` branch | Pass |
| `configure` | Changed owned `alignment_enabled` field, smoke verified, manifest metadata last | Pass with expected empty-gate warnings |
| `repair` | Deleted managed documentation file restored from matching payload bytes | Pass; repository returned clean |
| `upgrade` | Synthetic compatible payload 0.4.1 auto-applied, smoke verified, manifest updated last | Pass |
| rollback | Synthetic 0.4.2 payload intentionally broke `run.ps1` | Pass; exit 2, `rolled_back=true`, managed-file and manifest hashes exactly restored |
| rerun | Re-applied the already-installed 0.4.1 payload | Pass; fresh no-op classification and verification |
| `analyze` | Current manifest, zero drift, installed adapters, configuration proposals | Pass |
| `doctor` | Typed findings and repair actions | Pass with expected empty-gate warning exit 1 |

The live analysis also confirmed that managed `.agentic` and adapter source is
excluded from project-language and source-root proposals.

## Schema decision

There is one current install-manifest and journal layout, both numbered `1`.
All current fields are mandatory. Earlier partial layouts are rejected; no
schema migration, compatibility reader, or restamp path was exercised or
implemented.

## Still open

- Repeat the lifecycle on Ubuntu 22.04 x64.
- Exercise the remote-clone and corporate proxy branch on a real network.
- Repeat on clean Windows and Ubuntu virtual machines from release archives.
- Record a process-termination recovery journey in addition to the automated
  transaction-recovery tests.

