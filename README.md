<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Engineering Governance & Integrity System

This repository develops AEGIS version 1 and its separate WAEGIS operator
application. The current clean-break contracts are the Product Requirements,
Release Scope, Functional Specification, Artifact Model, CLI Machine Protocol,
Technical Architecture, Acceptance Plan, and Implementation Plan under
`00_Planning/`.

AEGIS is the repository-local, advisory engineering workflow payload. Its
canonical delivered source and product resources live below
`05_Software/aegis/template/.agentic/aegis/`. Project configuration, rules,
Requirements, Components, tests, Adoptions, and Runs remain repository-owned
siblings and are never payload upgrade material.

WAEGIS is the independent, standard-library-only lifecycle application under
`05_Software/waegis/`. It remains outside target repositories and uses explicit
digest-authorized plans for local Git initialization, installation, upgrade,
and removal. It exposes no stage, commit, branch, tag, merge, push, or pull
request operation.

## Repository layout

- `00_Planning/` — authoritative version 1 product and acceptance contracts.
- `01_Documentation/` — repository-wide engineering and code style.
- `02_Tools/` — repository support tools.
- `05_Software/aegis/` — canonical AEGIS payload source and package tests.
- `05_Software/waegis/` — separate WAEGIS package and lifecycle tests.
- `05_Software/release_tools/` — offline archive build and inspection tooling.
- `06_SoftwareDocu/` — deeper current implementation guidance and retained
  historical material.

## Development validation

Run each package from its own directory:

```powershell
uv run --group dev python -m pytest -q tests
uv run --group dev ruff check .
```

AEGIS and WAEGIS runtime code use only the Python standard library and support
Python 3.11 or later. Release tooling builds deterministic external-runtime
archives from repository content. Dependency-including archives require real,
locally supplied Python 3.12 and Git archives whose versions and SHA-256
digests are populated in the runtime-input lock; the checked-in lock truthfully
records that those release inputs are not supplied.

Release acceptance is a later, explicit campaign. The current implementation
does not claim real downstream-repository acceptance, supported-host sessions,
Ubuntu execution, bundled-runtime execution, network-denied package execution,
or the final `AC-*` matrix.
