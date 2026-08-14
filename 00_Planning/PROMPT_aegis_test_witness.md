<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Implementation prompt — AEGIS test-integrity witness

You are implementing a feature in **AEGIS**, the single-file, standard-library
governance CLI at `05_Software/aegis/template/.agentic/aegis.py`.

Follow the workflow stages: frame, specify, design, build, validate, and
deliver. Record a failing test command and its expected missing behavior before
the implementation, then retain the passing command as validation evidence.
Add tests below `05_Software/aegis/tests/` and run:

```powershell
cd 05_Software/aegis
python -m pytest -q
```
