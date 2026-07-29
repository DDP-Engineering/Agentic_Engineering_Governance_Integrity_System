<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Tools

Repository-level helper scripts and utilities for maintaining, validating, or
packaging the standalone AEGIS project belong here.

Regenerate the maintained AEGIS 2.0 start-guide PDF with the bundled
documentation runtime:

```powershell
python .\02_Tools\generate_start_guide_pdf.py
```

The generator is offline and uses ReportLab plus the Windows Arial and Consolas
fonts. Its Markdown source and PDF output are both under
`05_Software/aegis/template/.agentic/documents/`.

AEGIS deployment is not maintained as a repository-level helper script. Use
the separate WAEGIS package under `05_Software/waegis/`:

```powershell
waegis new D:\Path\To\NewProject
waegis adopt D:\Path\To\ExistingRepo
```

WAEGIS owns preview, conflict handling, manifest generation, configuration,
verification, repair, and upgrade. The shared manifest-aware payload copier is
implemented in `05_Software/waegis/src/waegis/payload/copier.py`.
