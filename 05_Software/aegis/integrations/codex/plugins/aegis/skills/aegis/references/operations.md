# Local bridge operations

Invoke `node <absolute-plugin-path>/scripts/aegis.mjs <operation> --root <checkout>` with these arguments:

| Operation | Arguments | Effect |
|---|---|---|
| status | optional `--task ID`, `--all` | Recorded tasks and active job |
| resume | `--task ID` | Brief plus branch check; no persistent task selection across processes |
| read | `--document contract\|cli\|config\|step\|journal`, task for step/journal | Installed instructions or task evidence |
| summary | `--task ID` | Recorded State summary |
| check | optional task and `--strict` | Static checks, no tests |
| scaffold | `--kind task --title TEXT --type feature\|fix\|change\|adopt`, optional `--parent ID` | New task record |
| scaffold | `--kind requirement --task ID --category functional\|ux\|nfr\|security\|data\|platform\|reliability\|test --title TEXT` | New requirement record |
| evidence | `--action anchor\|evolution\|report --task ID` | Evidence through the installed CLI |
| journal | `--action advance --task ID`, optional `--to STAGE`, `--skipped`, `--reason TEXT`, `--next TEXT` | Stage transition, Done checklist, Log line and State |
| journal | `--action pause --task ID --next TEXT`, optional `--blocked` | Stop for the user in the State |
| journal | `--action log --task ID --text TEXT` | One dated Log line |
| journal | `--action ruling --task ID --decision TEXT --reason TEXT --source user\|repository\|requirement\|technical`, optional `--supersedes RULING-NNN` | One appended Ruling |
| journal | `--action verdict --task ID`, optional `--spec V`, `--quality V`, `--round N` | Explicit review verdicts in the State |
| candidate | none | Git-visible candidate fingerprint |
| diff | optional `--base REF`, `--path PATH` | Tracked diff, status and untracked names |
| run | `--kind validate --task ID` | Final configured strict validation |
| run | `--kind test --task ID`, optional command/impacted/base | Configured test command |
| job | optional `--id ID`; `--action cancel` requires ID | Progress or deliberate cancellation |

`advance` and `pause` also accept `--read PATHS` (comma-separated), `--changed TEXT`, `--evidence TEXT` and `--issues TEXT`, and print the summary. The installed CLI records the decision; it never judges whether a stage's work is done.

`--role reviewer` refuses scaffold, evidence, journal, run and cancellation. Role flags do not establish caller identity; the host sandbox and explicit instructions provide the permission boundary.

Candidate fingerprints exclude `.agentic/tasks/` and Python bytecode. Ignored files, external inputs and submodule contents need separate review. Outputs are JSON records describing observations, not unconditional success declarations. Each call requires the real repository root and, where needed, the full task identifier.

Focused testing can pass `--impacted --no-fallback` to `run --kind test` when the
installed payload supports it; refusal records no successful test proof. Inspect
selection without creating a job using the payload CLI's `test --impacted --base
HEAD --dry-run` on one line. For a compact evolution response, pass `--compact` to
`evidence --action evolution`; the saved hashes remain complete. Optional flags
are never added to calls against older payloads automatically.
