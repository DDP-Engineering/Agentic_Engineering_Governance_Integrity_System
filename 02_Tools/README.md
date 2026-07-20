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

  Pass `--force` to overwrite existing files in the target directory,
  `--dry-run` to preview the copied files without writing, and
  `--existing-repo` to require the target directory to already exist
  (adoption of an existing repository).

  Since task T3.2 the script is a thin wrapper over the WAEGIS
  manifest-aware copier (`05_Software/waegis/src/waegis/payload/copier.py`).
  The flags and messages are unchanged, with one new side effect: every real
  (non-dry-run) copy also writes `<target>/.agentic/install-manifest.json`
  recording the payload version and the sha256 of every copied file, which is
  what enables `waegis analyze`/`doctor`/`upgrade` to manage the install
  later. `--dry-run` writes nothing, including no manifest. An overwrite
  refusal now happens before any file is written, so a refused run leaves the
  target untouched.

