<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

This folder holds local AEGIS build outputs and tracked publication records.

## Layout

```text
07_Delivery/
  dist/                 ignored local build output
  aegis-<version>/      tracked publication record
    RELEASE.md
    SHA256SUMS
    release-manifest.json
```

AEGIS releases are platform-labelled workflow payload archives: a Windows
`.zip` and a Linux `.tar.gz`. They contain the `.agentic/` workflow,
documentation, and license material; no runtime is embedded and no separate
deployment product is required.
