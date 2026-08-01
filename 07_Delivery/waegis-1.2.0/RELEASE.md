<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS 1.2.0 Delivery Package

- **WAEGIS version**: 1.2.0
- **Bundled AEGIS payload**: 2.1.0
- **Compatible AEGIS payload range**: `>=2.0.0,<3.0.0`
- **Optional bundled RepoWise**: 0.37.0, tag `v0.37.0`,
  commit `01b61af7629de9784d9bd713e4488091da79e399`
- **Built**: 2026-08-01
- **Core embedded runtime**: CPython 3.13.13
- **RepoWise sidecar runtime**: CPython 3.12.13

This release carries the AudioMancer real-deployment corrections (DPT-F01
through DPT-F09): the Windows RepoWise exclusion-argument fix, adoption
answer persistence with `workflow.toml` reconstruction, bounded redacted
failed-gate evidence, explicit non-interactive decision keys
(`accept_failing_gates`, `adopt_over_existing_install`,
`accept_nested_repository` — see the Migration note in the root
`CHANGELOG.md`), doctor visibility of accepted failing gates, configure
human/JSON parity, Windows gate-command splitting, `RUN-POINTER-MISSING`
recovery guidance, and the deployment self-containment contract
(`source-only` / `external-runtime` / `offline-bundled-runtime`).

## Artifacts

| File | Bytes | Edition | Target |
| --- | ---: | --- | --- |
| `waegis.pyz` | 694,872 | Core | Any OS with Python 3.11+ |
| `waegis-windows-x64.zip` | 24,252,966 | Core | Windows x64 |
| `waegis-linux-x64.tar.gz` | 69,088,764 | Core | Linux x64 |
| `waegis-complete-windows-x64.zip` | 266,460,040 | Complete | Windows x64 |

**No Linux Complete edition ships in this release** (owner decision,
2026-08-01): the 1.2.0 validation cycle was run on Windows only, so neither
the Linux test suite execution nor the natively built
`waegis-complete-linux-x64.tar.gz` are part of this delivery. Core Linux
remains included but Linux-unvalidated for this version. When Linux parity
is wanted, build and smoke-test the Complete archive natively (the 1.1.0
Linux Complete was built under Ubuntu 24.04 x64 on WSL2) and re-issue the
record.

Complete adds a separately installed, process-isolated RepoWise runtime,
corresponding source ZIP, AGPL and third-party notices, CycloneDX SBOM,
per-file manifest, tree digest, and unpacked-size metadata. Target
installation and deterministic indexing require no downloads.

The Windows corresponding-source ZIP SHA-256:

```text
0d6788d7ad44040c6a08c706b6dd2a6750559a9e82723ade44cb12154666fdcb
```

The Complete archive was built and verified on Windows x64. The release
builder independently verified all outer hashes, internal application
manifests, RepoWise bundle manifests, source identity, platform identity,
and per-file hashes.

## Checksums

```text
ec3a5ba675f19248ab62dd68f4efc9c55660f18f86e5eed84aea1091d7c4479c  waegis-complete-windows-x64.zip
49f8fc28b33200d2644e653c2195fbff203d6d1bd03066b32e798f9ea9e7cfcb  waegis-linux-x64.tar.gz
4d84bcd1582b5815183b0eda52a6857458afac3812574f45bf7e0e43cfabe605  waegis-windows-x64.zip
c6f672e3c4fee9d8d29066a6d4e9f887623da661c19cc616e3d43584b8301f28  waegis.pyz
```

The binaries remain Git-ignored in `07_Delivery/dist/`. This tracked record
identifies the locally built release.

## Verify

From `05_Software/waegis/`:

```powershell
python packaging/build_release.py `
  --output ..\..\07_Delivery\dist `
  --verify-only
```

Before public or commercial combined distribution, review and satisfy the
RepoWise AGPL-3.0-or-later obligations described in
`../REPOWISE_COMPLETE_DELIVERY.md`.
