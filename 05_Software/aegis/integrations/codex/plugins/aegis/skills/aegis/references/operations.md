<!--
Copyright (c) 2026 DDP Engineering
Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Local bridge operations

Invoke `node <absolute-plugin-path>/scripts/aegis.mjs <operation> --root <checkout>` with these arguments:

| Operation | Arguments | Effect |
|---|---|---|
| status | optional `--task ID`, `--all` | Recorded tasks and active job |
| resume | `--task ID` | Brief plus branch check; no persistent task selection across processes |
| read | `--document contract\|cli\|config\|step\|journal`, task for step/journal | Installed instructions or task evidence |
| summary | `--task ID` | Recorded Stage report |
| check | optional task and `--strict` | Static checks, no tests |
| scaffold | `--kind task --title TEXT --type feature\|fix\|change`, optional `--parent ID` | New task record |
| scaffold | `--kind requirement --task ID --category functional\|ux\|nfr\|security\|data\|platform\|reliability\|test --title TEXT` | New requirement record |
| evidence | `--action anchor\|evolution\|report --task ID` | Evidence through the installed CLI |
| candidate | none | Git-visible candidate fingerprint |
| diff | optional `--base REF`, `--path PATH` | Tracked diff, status and untracked names |
| run | `--kind validate --task ID` | Final configured strict validation |
| run | `--kind test --task ID`, optional command/impacted/base | Configured test command |
| job | optional `--id ID`; `--action cancel` requires ID | Progress or deliberate cancellation |

`--role reviewer` refuses scaffold, evidence, run and cancellation. Role flags do not establish caller identity; the host sandbox and explicit instructions provide the permission boundary.

Candidate fingerprints exclude `.agentic/tasks/` and Python bytecode. Ignored files, external inputs and submodule contents need separate review. Outputs are JSON records describing observations, not unconditional success declarations. Each call requires the real repository root and, where needed, the full task identifier.

Focused testing can pass `--impacted --no-fallback` to `run --kind test` when the
installed payload supports it; refusal records no successful test proof. Inspect
selection without creating a job using the payload CLI's `test --impacted --base
HEAD --dry-run` on one line. For a compact evolution response, pass `--compact` to
`evidence --action evolution`; the saved hashes remain complete. Optional flags
are never added to calls against older payloads automatically.
