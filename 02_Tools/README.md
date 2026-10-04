<!--
Copyright (c) 2026 DDP Engineering
This project is licensed under the PolyForm Noncommercial License 1.0.0.
Noncommercial use is permitted under the license terms.
Commercial use requires a separate commercial license.
See LICENSE.txt for full terms.
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-->

# Tools

Repository setup, maintenance, and delivery-package scripts live here.

Run the commands below from the repository root. Core release construction and
agent plugin assembly are separate operations:

| Script | Output | Verification performed by the builder |
|---|---|---|
| `build_aegis_release.py` | Core Windows/Linux archives and release records. | Managed payload inventory, complete product test suite and archive inventories. |
| `build_agent_plugins.mjs` | Five complete host package directories. | Assembly only; no test suite or host validation. |

## Core release archives

Build the current AEGIS release archives and tracked publication record with:

```text
py -3.12 02_Tools/build_aegis_release.py --version 0.14.0
```

On Linux, use `python3` in place of `py -3.12`. The build environment needs
Python 3.11+, `pytest`, Git and Node.js 22+ for the integration tests included in
the product suite. See the [development setup](../README.md#environment-and-development-setup).

`--version` must match the payload's existing `VERSION` declaration and have a
dated entry in the root changelog. The builder does not assign a new version.

The builder validates the 17-file payload, runs the complete product test
suite, and writes reproducible Windows `.zip` and Linux `.tar.gz` archives
under `07_Delivery/dist/`. Checksums and release metadata are written under
`07_Delivery/aegis-<version>/` as `SHA256SUMS`, `release-manifest.json` and
`RELEASE.md`. Rebuilding the same version replaces those generated outputs;
it does not publish them remotely.

## Agent plugin packages

With Node.js 22 or later, assemble the packages with:

```sh
node 02_Tools/build_agent_plugins.mjs
```

The default output is `07_Delivery/agent-plugins-unreleased/`, containing:

```text
aegis-opencode/
aegis-codex/
aegis-pi/
aegis-qwen/
aegis-claude/
```

Choose a fresh location for another build:

```sh
node 02_Tools/build_agent_plugins.mjs --output 07_Delivery/agent-plugins-next
```

The builder refuses to overwrite an existing `aegis-<host>` package directory.
An existing parent output directory is allowed if its package directories do
not already exist. After an interrupted build, use a fresh output location to
avoid mixing incomplete and complete packages.

Each package includes its native host resources, shared JavaScript libraries,
license notices, `install.sh` and `Install-AEGIS.cmd`. Shared libraries are
copied into `plugins/aegis/lib/` for Codex and Claude, and `lib/` for OpenCode,
Pi and Qwen. Raw integration source directories are not complete installable
packages; registering them directly can leave `lib/bridge.mjs` missing.

This script produces directories, not ZIP or tar archives. Share the complete
host directory or an archive made from it. The builder reads the existing core
version, uses vendored dependencies without fetching packages, and does not run
tests, invoke models, install into host profiles or publish to a registry.
The integration manifests take the assigned version from the core payload.

Recipients install the built package in their own environment, retaining their
own account, model and permissions. See the
[agent package guide](../06_SoftwareDocu/Agent_Plugins.md) for prerequisites,
installation, update/removal and verification limits.
