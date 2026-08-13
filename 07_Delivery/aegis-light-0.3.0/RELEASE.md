<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light 0.3.0 Delivery Package

- **AEGIS Light version**: 0.3.0
- **Previous release**: 0.2.0
- **Built**: 2026-08-13
- **Runtime**: none embedded; Python 3.11 or newer is required
- **Platform**: platform-independent payload
- **Dependencies**: Python standard library only

This release sharpens the agent/developer collaboration loop without adding
blocking runtime machinery.

## Changes

- Automated red evidence in the task journal now records the exact test
  selector or command, its non-zero exit, and the expected missing-behavior
  failure reason.
- The final workflow is split into `validate` and publish-only `deliver`.
  Validation may reconcile the candidate and proves it last; delivery does not
  edit it and returns to validation if it changes.
- Delivery deliberately has no default write zone because a merge-base diff
  cannot reliably attribute an edit to the stage that introduced it.
- Task and requirement creation now use the flat CLI forms
  `aegis task "<title>"` and `aegis req <category> "<title>"`.
  The former nested `task new` and `req new` forms are not supported.
- The payload now ships `.agentic/CLI.md`, a complete command reference with
  descriptions, examples, exit behavior, and guidance on when to use each
  command.

Existing project data and `.agentic/aegis.toml` remain project-owned and are
not included in the payload. Upgrade by copying the payload-owned files,
running `python .agentic/aegis.py init`, reviewing the diff, and committing
through the repository's normal workflow.

## Artifacts

| File | Bytes | Edition | Target |
| --- | ---: | --- | --- |
| `aegis-light-0.3.0.zip` | 85,228 | Payload | Any OS with Python 3.11+ |
| `aegis-light-0.3.0.tar.gz` | 65,135 | Payload | Any OS with Python 3.11+ |

Each archive contains the exact 15-file `.agentic/` payload, `INSTALL.md`,
the product README and license, and ten Markdown user guides under `docs/`.
The archive formats contain the same files and differ only as containers.

## Checksums

```text
5ec30c8e06c46f5d3945209e01d6bbfc03ad1240abd32afc85d5b9de65a08050  aegis-light-0.3.0.zip
c688b3b79fa9930afe93020580df5fc70e25c4be19fb749e3e943e0ac6200f9e  aegis-light-0.3.0.tar.gz
```

The binaries remain Git-ignored in `07_Delivery/dist/`. The adjacent tracked
`SHA256SUMS` and `release-manifest.json` identify this local build.

## Validation

- Product suite: 173 passed, 1 skipped on Windows.
- Payload inventory: exact at 15 files.
- Release manifest version: 0.3.0.
- Both archives contain `.agentic/CLI.md` and
  `docs/09_CLI_Reference.md`.
- Installed repository payload: byte-for-byte equal to the source payload.
- Installed CLI compilation, version, `task --help`, and `req --help`: passed.
- Repository-owned `.agentic` configuration and governance records: unchanged
  across deployment (107 files, aggregate fingerprint verified).
