<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Self-Governed AEGIS/WAEGIS Release

An AEGIS-governed release is retained evidence, not a structural-test result.
The repository root must first contain an approved AEGIS installation and valid
`.agentic/workflow.toml`. A release run must then retain its requirements,
selected design, checks/evidence, validation summary, delivery report, graph,
and journal.

As of 2026-07-30, this repository root has no `.agentic/` installation.
Therefore no root AEGIS release run exists for the current AEGIS 2.1.0 /
WAEGIS 1.1.0 release. Installing the workflow would create a substantial
governance artifact set and requires an explicit adoption decision; release
hygiene tests do not substitute for that evidence.

## Proposed Adoption

After an operator approves root adoption and prepares a reviewed complete
answers file, run from the repository root:

```powershell
uv run --project 05_Software/waegis --group dev python -m waegis adopt . `
  --payload 05_Software/aegis/template `
  --answers <approved-adoption-answers.toml> `
  --non-interactive `
  --dry-run

uv run --project 05_Software/waegis --group dev python -m waegis adopt . `
  --payload 05_Software/aegis/template `
  --answers <approved-adoption-answers.toml> `
  --non-interactive `
  --yes
```

Review the dry-run plan before the approved mutation. Do not reuse an answers
file until its roots, gates, guardrails, interface policy, and optional
RepoWise policy have been checked against the current repository.

## Proposed Release Run

After adoption, run the project-local wrapper from the repository root:

```powershell
.\.agentic\tools\run.ps1 config validate --json
.\.agentic\tools\run.ps1 config show --json
.\.agentic\tools\run.ps1 run start change
.\.agentic\tools\run.ps1 stage prepare
```

Edit the returned intake form, then use this exact stage lifecycle:

```powershell
.\.agentic\tools\run.ps1 stage apply
.\.agentic\tools\run.ps1 stage close
.\.agentic\tools\run.ps1 stage prepare
```

Repeat `apply`, human-approved `close`, and `prepare` through alignment,
requirement, design, check, implementation, validation, and delivery. Use
`stage add` for each additional atomic requirement or check. At the check stage,
use the command selected by `interface.check_execution`:

```powershell
# external mode
.\.agentic\tools\run.ps1 check prepare
# run the prepared command, complete evidence.toml
.\.agentic\tools\run.ps1 check record

# managed mode
.\.agentic\tools\run.ps1 check run
```

Before closing validation and delivery:

```powershell
.\.agentic\tools\run.ps1 verify run
.\.agentic\tools\run.ps1 delivery show
```

The retained run must cite the AEGIS and WAEGIS version-hygiene tests, both full
package suites, CLI help checks, lint/static checks, template cache scan, and
release-package verification. Closing delivery records the handoff only; Git
commit, push, publication, and issue closure remain separate human-approved
actions.
