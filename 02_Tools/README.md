<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Tools

Repository-level helper scripts and utilities for maintaining, validating, or
packaging the standalone AEGIS project belong here.

- `create_project_from_template.py` - copy the AEGIS payload under
  `05_Software/aegis/template/` into a target project
  directory. It copies the `.agentic/` engine, the `.codex/`, `.claude/`, `.pi/`,
  `.opencode/`, and `.qwen/` adapters, `AGENTS.md`, `CLAUDE.md`, `QWEN.md`,
  `opencode.json`, `CHANGELOG.md`, and the `05_SoftwareDocu/` convention, while
  skipping generated artifacts (`__pycache__`, caches, and the `.pi/` adapter's
  install-on-demand `node_modules/`).

  ```powershell
  python 02_Tools\create_project_from_template.py D:\Path\To\NewProject
  ```

  Pass `--force` to overwrite existing files in the target directory.

