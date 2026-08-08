<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Tools

Repository-level helper scripts and utilities for maintaining, validating, or
packaging the standalone AEGIS project belong here.

Generate an optional AEGIS 3.0 start-guide PDF from a documentation environment
that already provides ReportLab:

```powershell
python .\02_Tools\generate_start_guide_pdf.py
```

The generator performs no dependency installation or network access. It uses
ReportLab plus the Windows Arial and Consolas fonts, so the render command is a
Windows documentation-maintenance operation rather than an AEGIS runtime
dependency. Its maintained Markdown source is
`05_Software/aegis/template/.agentic/documents/How_To_Start_A_New_Project.md`.
The default PDF output is local, ignored build material under
`02_Tools/generated/`; it is not part of the copied template.

AEGIS deployment is not maintained as a repository-level helper script.
Deployment-tool behavior and compatibility are documented by the separate
WAEGIS package while that package evolves.
