<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery

Local build outputs and tracked publication records for AEGIS, WAEGIS, and
AEGIS Light belong here. Full-AEGIS/WAEGIS version 1 uses only the offline ZIP
builder documented below; AEGIS Light retains its separate release process.

## Current version 1 full-AEGIS/WAEGIS matrix

The intended matrix contains the following eight target-labelled ZIPs. This
table records the local inventory reviewed on 2026-08-13; presence in the
ignored `dist/` directory is local build evidence, not publication evidence.

| Product | Platform | Runtime edition | Exact output name | Local state |
|---|---|---|---|---|
| AEGIS | Windows x86-64 | External | `aegis-1.0.0-windows-x86_64-external-runtime.zip` | **Built** |
| AEGIS | Ubuntu 22.04 x86-64 | External | `aegis-1.0.0-ubuntu-22.04-x86_64-external-runtime.zip` | **Built** |
| AEGIS | Windows x86-64 | Bundled | `aegis-1.0.0-windows-x86_64-with-dependencies.zip` | **Pending** |
| AEGIS | Ubuntu 22.04 x86-64 | Bundled | `aegis-1.0.0-ubuntu-22.04-x86_64-with-dependencies.zip` | **Pending** |
| WAEGIS containing AEGIS | Windows x86-64 | External | `waegis-1.0.0-windows-x86_64-external-runtime.zip` | **Built** |
| WAEGIS containing AEGIS | Ubuntu 22.04 x86-64 | External | `waegis-1.0.0-ubuntu-22.04-x86_64-external-runtime.zip` | **Built** |
| WAEGIS containing AEGIS | Windows x86-64 | Bundled | `waegis-1.0.0-windows-x86_64-with-dependencies.zip` | **Pending** |
| WAEGIS containing AEGIS | Ubuntu 22.04 x86-64 | Bundled | `waegis-1.0.0-ubuntu-22.04-x86_64-with-dependencies.zip` | **Pending** |

The four external-runtime ZIPs are present locally. All four bundled-runtime
ZIPs are absent and pending because `02_Tools/runtime_inputs.toml` marks every
Python and Git input as unsupplied and provides no versions, digests, or archive
paths. No tracked version 1 full-AEGIS/WAEGIS publication record exists in this
checkout.

The platform column is a target contract, not a claim that every archive
contains platform- or architecture-specific executable bytes. In particular,
the current Windows- and Ubuntu-labelled external-runtime AEGIS archives carry
the same portable payload and both `bin/aegis` and `bin/aegis.cmd`; the label
selects launcher/prerequisite expectations and manifest/inventory metadata, and
the `x86_64` inventory field is target metadata. WAEGIS external-runtime
archives select a platform launcher. Future bundled-runtime archives will differ
materially because their locked Python and Git inputs are platform-specific.

## Layout

```text
07_Delivery/
  dist/                     ignored local build output
    <the built version 1 ZIP names listed above>
    <separately managed AEGIS Light outputs>
  aegis-light-<version>/    publication record for the AEGIS Light payload
    RELEASE.md
    SHA256SUMS
    release-manifest.json
```

## AEGIS Light

AEGIS Light delivers as two small archives with byte-identical content
(`aegis-light-<version>.zip` and `.tar.gz`) holding the `.agentic/`
payload, `INSTALL.md`, the product `README.md`, `LICENSE.txt` and the
user guides. It embeds no runtime and is not platform-specific: the two
formats are ergonomic, not different builds.

Build with:

```
python 02_Tools/build_aegis_light_release.py --version <version>
```

The builder verifies the payload inventory, runs the product test suite
and refuses to package a red tree, then writes deterministic archives
(normalized member timestamps, so the same sources reproduce the same
checksums) plus `SHA256SUMS` and `release-manifest.json` into `dist/`,
and copies the checksums and manifest into the tracked publication
record. Write `RELEASE.md` there by hand.

## Full-AEGIS/WAEGIS runtime prerequisites

External-runtime archives require exactly the prerequisites written inside each
archive's `PREREQUISITES.md` and `ARCHIVE_INVENTORY.json`:

- Python 3.12 available to the launcher.
- Git with porcelain-v2 support available to the launcher.

The launchers probe compatible existing executables and do not install or
configure either prerequisite. AEGIS and WAEGIS runtime code is standard-
library-only. Missing Python or Git is reported through the product response;
it is not repaired or downloaded.

Bundled-runtime builds require local Python and Git ZIP inputs for the selected
platform. Each `02_Tools/runtime_inputs.toml` entry must set `supplied = true`
and provide an exact version, SHA-256 digest, and local `archive_path`. Python
must be an exact 3.12 release. Windows inputs must contain `python.exe` and
`cmd/git.exe`; Ubuntu inputs must contain `bin/python3` and `bin/git`. The
builder verifies the locked digests and safe archive paths, then places those
runtimes privately inside the product ZIP. It performs no download and makes no
global runtime or Git change.

## Build and inspect

Run the standard-library builder from the repository root. These are the exact
commands for the eight outputs:

```powershell
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product aegis --platform windows-x86_64
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product aegis --platform ubuntu-22.04-x86_64
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product aegis --platform windows-x86_64 --with-dependencies
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product aegis --platform ubuntu-22.04-x86_64 --with-dependencies
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product waegis --platform windows-x86_64
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product waegis --platform ubuntu-22.04-x86_64
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product waegis --platform windows-x86_64 --with-dependencies
python 02_Tools/build_aegis_release.py build --repository . --output 07_Delivery/dist --product waegis --platform ubuntu-22.04-x86_64 --with-dependencies
```

Inspect one built archive without extracting it:

```powershell
python 02_Tools/build_aegis_release.py inspect 07_Delivery/dist/aegis-1.0.0-windows-x86_64-external-runtime.zip
```

`inspect` checks safe unique member paths, the exact internal inventory, member
sizes and SHA-256 digests, runtime-edition consistency, and the absence of a
persistent virtual-environment marker. It does not execute the product or its
prerequisites.

## Verification and publication boundary

The four present external-runtime ZIPs were last written on 2026-08-12 and have
internal version 1 inventories. They predate current working-tree changes, so
`inspect` establishes their internal integrity but not equality with the
current source candidate. The four absent bundled-runtime ZIPs cannot be built
truthfully until the local runtime lock is complete. The current
`dist/SHA256SUMS` and `dist/release-manifest.json` describe AEGIS Light 0.3.0
only; they are not full-AEGIS/WAEGIS version 1 publication evidence.

The builder creates and inspects one local archive at a time. It does not run
the full AEGIS or WAEGIS suites, execute supported-host acceptance, create an
external checksum set or publication record, sign an artifact, upload a file,
or publish a release. A release claim therefore requires separate retained
test, host, digest, approval, and publication evidence. No such publication
action is implied by files in ignored `dist/`.

## Advisory posture

AEGIS version 1 records findings, evidence, skips, waivers, and uncertain work
for review. Its default workflow remains advisory and non-blocking; it is not a
CI system or a security control and does not guarantee hook, read, write-zone,
secret, shell, delivery, or evidence enforcement. WAEGIS prepares explicit
local lifecycle plans and deploys the AEGIS payload, but it does not turn those
findings into security guarantees or publish releases.

## Tracked publication records

The tracked publication-record directories currently present here are
`aegis-light-0.2.0/` and `aegis-light-0.3.0/`. They belong to the separately
managed AEGIS Light delivery described above. There is currently no tracked
full-AEGIS/WAEGIS version 1 publication record in this checkout.

## Delivery References

- `../02_Tools/README.md` documents the current builder and local matrix state.
- `../05_Software/aegis/README.md` documents the current AEGIS CLI and workflow.
- `../05_Software/waegis/README.md` documents current WAEGIS lifecycle behavior.
- `../06_SoftwareDocu/AEGIS_V1_IMPLEMENTATION.md` documents implementation and
  acceptance boundaries.
