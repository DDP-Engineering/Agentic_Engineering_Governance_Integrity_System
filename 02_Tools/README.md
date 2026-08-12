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

Release launchers disable Python bytecode writes so running an extracted
package does not add generated files below the product-owned payload.

AEGIS deployment is not maintained as a repository-level helper script.
Deployment-tool behavior and compatibility are documented by the separate
WAEGIS package while that package evolves.

`aegis_acceptance.py` is a separate, standard-library-only release-candidate
evidence inventory and verdict compiler. It validates retained evidence without
executing project commands or changing Git; it does not execute IP-18's platform
or package campaign. Its reviewed JSON catalog contains the 58 AEGIS scenarios.
Records bind evidence to one candidate, scenario, package, and environment;
passing verdicts require retained requirement coverage and verified matrix
evidence, not merely scenario labels or candidate inventory names. Matrix cases
are explicit package and workflow combinations, and are matched only through
the bound candidate identities.

When evidence binds both a package and an environment, their recorded platform
and architecture must agree. Completion reports record the final verdict actor
and timestamp in both JSON and Markdown.
