<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS

**Agentic Engineering Governance & Integrity System**

AEGIS is a repository-local, offline-first workflow for agent-driven software
development. It gives an agent and its human collaborator a durable way to
record requirements, implementation decisions, validation evidence, and
delivery boundaries—without a hosted service, database, hooks, model API, or
automatic Git actions.

The workflow is advisory by default: it helps people and agents notice gaps;
it does not silently block work or grant authority to commit, push, publish,
or deploy. An optional strict check provides a CI boundary when a project
wants one.

## Highlights

- **Plain, portable records:** requirements in TOML; specifications, journals,
  rulings, handoffs, and knowledge pages in Markdown; anchors and evolution
  evidence in JSON.
- **A practical workflow:** six stages—`frame`, `specify`, `design`, `build`,
  `validate`, and `deliver`—plus a proportionate quick path for small changes.
- **Agent-friendly continuity:** deterministic `brief` and `summary` views,
  durable handoffs, and optional one-level child tasks support cross-session
  and multi-agent work.
- **Evidence, not theatre:** configured tests, impacted-test selection,
  anchors, evolution reports, and 21 advisory checks keep the work auditable.
- **Optional explicit review:** repositories can enable independent
  specification-compliance and implementation-quality verdicts with a bounded
  fix-and-re-review loop. Review never replaces ordinary validation.

Current release: **0.9.0**. See the [changelog](CHANGELOG.md) for changes.

## Install AEGIS in a repository

Copy the reusable payload from this repository into the target repository:

```text
05_Software/aegis/template/.agentic/  ->  <your-repository>/.agentic/
```

Then run this from the target repository root:

```bash
python .agentic/aegis.py init
```

`init` creates missing AEGIS data folders, creates `aegis.toml` only when it
does not already exist, and adds managed guidance blocks to `AGENTS.md`,
`CLAUDE.md`, and `QWEN.md`. It never initializes Git unless you explicitly
ask it to:

```bash
python .agentic/aegis.py init --git
```

For the complete setup, configuration, and upgrade guidance, see
[Install and setup](06_SoftwareDocu/01_Install_and_Setup.md).

## First use

Tell your coding agent to use the workflow, for example:

```text
using aegis workflow, implement <your change>
```

Useful commands from the governed repository root:

```bash
python .agentic/aegis.py status
python .agentic/aegis.py brief TASK-<id>
python .agentic/aegis.py check
python .agentic/aegis.py test --impacted --task TASK-<id>
```

`brief` is the richer bounded resume view; `summary` is the compact projection
of the most recently recorded stage report. The authoritative command syntax
is always available through `python .agentic/aegis.py --help`.

## Repository layout

| Path | Purpose |
|---|---|
| [`00_Planning/`](00_Planning/) | Implemented design record and maintenance boundaries. |
| [`01_Documentation/`](01_Documentation/) | Repository standards, including code style. |
| [`02_Tools/`](02_Tools/) | Workspace-maintenance and release-building scripts. |
| [`03_Hardware/`](03_Hardware/) and [`04_HardwareDocu/`](04_HardwareDocu/) | Hardware-related material and supporting documentation. |
| [`05_Software/aegis/`](05_Software/aegis/) | AEGIS product source, template payload, tests, and product README. |
| [`06_SoftwareDocu/`](06_SoftwareDocu/) | User guides, examples, team setup, FAQ, prompt cheatsheet, and CLI reference. |
| [`07_Delivery/`](07_Delivery/) | Versioned archives, checksums, manifests, and publication records. |
| [`.agentic/`](.agentic/) | This repository's installed AEGIS instance and its durable governance records. |

The reusable product payload is
[`05_Software/aegis/template/.agentic/`](05_Software/aegis/template/.agentic/).
It is the source of truth for managed AEGIS files. The root [`.agentic/`](.agentic/)
is an installed copy used to govern this repository; it also contains
repository-owned configuration and records that must not be overwritten during
an upgrade.

## Environment and development setup

AEGIS runs on **Python 3.11 or newer** and uses only the Python standard
library at runtime. Git is strongly recommended: without it, AEGIS still
works, but diff-based checks, impacted-test selection, anchors, and evolution
reports cannot run.

For product development, create an isolated environment and install `pytest`
from your approved package source or local cache:

```powershell
Set-Location 05_Software/aegis
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install pytest
python -m pytest -q tests
python template/.agentic/aegis.py --help
```

On macOS or Linux, activate the environment with
`source .venv/bin/activate`. The runtime payload itself has no package-install
step.

## Validation and releases

For changes to the AEGIS product, run the product suite from
`05_Software/aegis/`:

```bash
python -m pytest -q tests
python template/.agentic/aegis.py --help
```

Versioning and release construction are repository operations, not AEGIS task
stages. Maintainers build verified Windows and Linux archives from the
repository root with:

```powershell
py -3.12 02_Tools/build_aegis_release.py --version <x.y.z>
```

The builder validates the 15-file managed payload, runs the product suite,
checks both archive inventories, and writes checksums and release metadata
under `07_Delivery/`.

## Documentation

Start with the [user documentation index](06_SoftwareDocu/00_Index.md). It
covers installation, the file layout, feature and quick-fix examples,
repository adoption, team CI, the FAQ, prompt cheatsheet, and full CLI
reference.

When the user documentation differs from the installed payload, the payload
(`.agentic/AGENTS.md`, its stage files, and `aegis.py --help`) is authoritative.

## License

AEGIS is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.txt).
Commercial use requires a separate license; see the license file for contact
details and terms.
