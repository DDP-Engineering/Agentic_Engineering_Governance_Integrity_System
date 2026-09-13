<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Environment guide

## Toolchain

The companion CLI uses Python 3.11 or later and the standard library. Product
verification uses pytest and Ruff. Host integrations use Node.js 22 or later;
Git supplies repository evidence and isolated test fixtures.

## Setup

Follow `06_SoftwareDocu/01_Install_and_Setup.md` for core setup and
`06_SoftwareDocu/Plugin_Installation/README.md` for the selected host integration.
Repository tooling is documented in `02_Tools/README.md`.

## Configuration and services

`.agentic/aegis.toml` owns verification commands and layout for this repository.
Host runtime paths and job caches are configured per installation as documented
in `06_SoftwareDocu/Agent_Plugins.md`.

## Readiness checks

From the repository root, confirm Python, Git and Node.js availability using
`python --version`, `git --version` and `node --version`. Confirm test tools with
`python -m pytest --version` and `python -m ruff --version` before verification.
Follow the selected host's installation guide for host-specific readiness.

## Build and run

The canonical core entry point is
`python 05_Software/aegis/template/.agentic/aegis.py --help`.
The root `.agentic/aegis.py` is the installed payload mirror.
Package build commands and outputs are defined in `02_Tools/README.md`.

## Verification

Use `.agentic/aegis.toml` `[commands]` for canonical test, impacted-test and lint
commands; the default working directory is the repository root. `AGENTS.md`
defines minimum Python compilation, product-suite and CLI verification.
Focused selectors target `05_Software/aegis/tests/` or the integration tests
owned by the changed behavior. Run-specific outcomes belong in task evidence.

## Platform details

The core uses repository-relative forward-slash artifact paths and writes UTF-8
with LF line endings. Host runtime discovery and installation procedures are
documented separately for Windows and Linux in the plugin installation guides.

## Authoritative references

- `.agentic/aegis.toml` — executable verification configuration and layout.
- `AGENTS.md` — repository validation rules and authorization boundaries.
- `05_Software/aegis/README.md` — core and host prerequisites.
- `06_SoftwareDocu/Agent_Plugins.md` — host runtime and verification behavior.
