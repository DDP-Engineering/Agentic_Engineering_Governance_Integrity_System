<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Tools

Repository-level helper scripts and utilities for maintaining, validating, or
packaging the standalone AEGIS project belong here.

Offline AEGIS and WAEGIS archive construction and inspection use the standalone
standard-library script `build_aegis_release.py`. Its dependency-including
editions read exact local Python and Git inputs from `runtime_inputs.toml`.

```powershell
python 02_Tools/build_aegis_release.py build --repository . --output dist --product aegis --platform windows-x86_64
python 02_Tools/build_aegis_release.py inspect dist/aegis-1.0.0-windows-x86_64-external-runtime.zip
```

AEGIS deployment is not maintained as a repository-level helper script.
Deployment-tool behavior and compatibility are documented by the separate
WAEGIS package while that package evolves.
