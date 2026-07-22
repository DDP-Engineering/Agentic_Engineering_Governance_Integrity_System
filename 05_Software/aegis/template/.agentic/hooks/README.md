<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Hooks

These scripts are installed with AEGIS and are invoked by every supported
adapter. `workflow_config_bootstrap.py` loads the delivered `aegis.config`
parser; hooks must not parse `workflow.toml` independently or carry fallback
repository policy.

- `guard_read_path.py` applies configured protected-path rules for reads.
- `guard_write_zone.py` applies configured protected paths and write access.
- `secret_scan.py` applies configured secret expressions.
- `delivery_preflight.py` recognizes configured delivery commands.
- `post_tool_evidence.py` records against the selected worktree-local run.

Missing or invalid configuration denies pre-tool actions with the canonical
configuration code and remediation. Disabled or unrestricted modes add no
implicit rules. Keep transport code stdlib-only and free of project secrets.
