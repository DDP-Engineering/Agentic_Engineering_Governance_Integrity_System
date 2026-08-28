<!--
Copyright (c) 2026 DDP Engineering
This project is licensed under the PolyForm Noncommercial License 1.0.0.
Noncommercial use is permitted under the license terms.
Commercial use requires a separate commercial license.
See LICENSE.txt for full terms.
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-->

# Tools

Repository setup, maintenance, and delivery-package scripts live here.

Build the current AEGIS release archives and tracked publication record with:

```text
py -3.12 02_Tools/build_aegis_release.py --version 0.8.0
```

The builder validates the payload inventory, runs the complete product test
suite, and writes reproducible Windows `.zip` and Linux `.tar.gz` archives
under `07_Delivery/dist/`. Checksums and release metadata are written under
`07_Delivery/aegis-<version>/`.
