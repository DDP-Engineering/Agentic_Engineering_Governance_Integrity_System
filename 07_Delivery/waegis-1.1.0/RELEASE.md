<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS 1.1.0 Delivery Package

- **WAEGIS version**: 1.1.0
- **Bundled AEGIS payload**: 2.1.0
- **Compatible AEGIS payload range**: `>=2.0.0,<3.0.0`
- **Optional bundled RepoWise**: 0.37.0, tag `v0.37.0`,
  commit `01b61af7629de9784d9bd713e4488091da79e399`
- **Built**: 2026-07-30
- **Core embedded runtime**: CPython 3.13.13
- **RepoWise sidecar runtime**: CPython 3.12.13

## Artifacts

| File | Bytes | Edition | Target |
| --- | ---: | --- | --- |
| `waegis.pyz` | 1,725,155 | Core | Any OS with Python 3.11+ |
| `waegis-windows-x64.zip` | 24,134,827 | Core | Windows x64 |
| `waegis-linux-x64.tar.gz` | 69,601,792 | Core | Linux x64 |
| `waegis-complete-windows-x64.zip` | 275,761,239 | Complete | Windows x64 |
| `waegis-complete-linux-x64.tar.gz` | 377,343,562 | Complete | Linux x64 |

Complete adds a separately installed, process-isolated RepoWise runtime,
corresponding source ZIP, AGPL and third-party notices, CycloneDX SBOM,
per-file manifest, tree digest, and unpacked-size metadata. Target installation
and deterministic indexing require no downloads.

The Windows and Linux corresponding-source ZIPs have the same SHA-256:

```text
e2e390672618f1f99a23e593c17003147f84f1f023fcc3c1d5aa03d70eb45c31
```

The Complete archives were built and smoke-tested natively on Windows x64 and
Ubuntu 24.04 x64 under WSL2. The release builder then independently verified
all outer hashes, internal application manifests, RepoWise bundle manifests,
source identity, platform identity, and per-file hashes.

## Checksums

```text
d79aa9dd1e5be06a0a11400e624a55a2405eabb5828d9e6f86449687ecc260ee  waegis-complete-linux-x64.tar.gz
a1603a4509f87ed32b9f2ab69fc6b0e2111271298f4a540badff8b0dbf496168  waegis-complete-windows-x64.zip
d3b1044cb3901cbe82885542e2e8ff29b66828b4e2f881445a01a4a01c6c4d39  waegis-linux-x64.tar.gz
cfab8cc9894b37b30ceecfbb1751d0d4e79d903e3d3ea96ae42a95c9693ad290  waegis-windows-x64.zip
c199058ef6ea5a8974668ca774f51af86d30ab6e58e00ffea8ed0a9bf92ffb18  waegis.pyz
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
