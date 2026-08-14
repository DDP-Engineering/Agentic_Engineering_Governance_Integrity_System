<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Engineering Governance & Integrity System

This repository develops AEGIS: a repository-local, advisory workflow for
agent-driven software development. It provides durable requirements,
specifications, task journals, knowledge pages, and an optional strict CI check.

The product source is at `05_Software/aegis/`; its reusable payload is
`05_Software/aegis/template/.agentic/`. User guides and design records are in
`06_SoftwareDocu/` and `00_Planning/`.

## Development validation

```powershell
python -m pytest -q 05_Software/aegis/tests
python 05_Software/aegis/template/.agentic/aegis.py --help
```

AEGIS uses the Python standard library and supports Python 3.11 and newer.
