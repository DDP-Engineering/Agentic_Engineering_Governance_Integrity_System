<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS

Status: Scaffold (task T0.1).

**WAEGIS** is the guided wizard that configures and deploys the AEGIS platform
(the `05_Software/aegis/template/` payload) into a target repository, in a way a
person with no repo-setup knowledge can follow. It is a **separate package** from
the AEGIS payload and is **never copied into that payload** (AD-1).

Design and task breakdown live in
`00_Planning/WAEGIS_Wizard_Implementation_Plan.md`.

## Principles

- Stdlib-only, Python >= 3.11, offline-first; all subprocess and network access
  sits behind injectable runner interfaces so tests run offline (AD-3).
- Deterministic core; the optional AI advisor is proposed last and never
  required (AD-5).
- Every mutation is planned, previewed, and verified; runs are journaled and
  safe to abort and re-run (AD-8).

## Planned commands (CLI contract, plan §5)

```text
waegis new    TARGET [--answers F] [--dry-run] [--non-interactive] [--json] [--payload PATH]
waegis adopt  TARGET [--answers F] [--dry-run] [--non-interactive] [--json] [--payload PATH]
waegis analyze --repo PATH [--json]
waegis doctor  --repo PATH [--json]        # exit 0 healthy / 1 warnings / 2 failures
waegis upgrade --repo PATH [--dry-run] [--json] [--payload PATH]
waegis version
waegis self-update [--source URL|PATH] [--check-only]
waegis gui     [--port N]
```

In this scaffold every subcommand is a stub that prints "not implemented" and
exits with code 2. Later tasks (M1 onward) replace the stubs with real command
handlers. Exit codes are part of the public contract from 0.1.0 (AD-9).

## Development

From this folder, use the project dev dependency group so pytest and lint tools
come from the repository configuration:

```powershell
uv sync --group dev
uv run --group dev python -m pytest -q tests
python -m waegis --help
```

## Package layout

```text
src/waegis/
  __init__.py  __main__.py  cli.py  version.py
  engine/   step.py  catalog.py  runner.py  journal.py  plan.py
  io/       prompts.py  answers.py  console.py  reports.py
  probes/   machine.py  tools.py  network.py
  payload/  manifest.py  copier.py  locate.py
  repo/     gitops.py  analyze.py  workflow_toml.py
  commands/ new.py  adopt.py  analyze.py  doctor.py  upgrade.py
tests/
```

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See `LICENSE.txt` for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
