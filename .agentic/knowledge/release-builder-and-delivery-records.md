<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Release builder and delivery records

## Purpose

The release builder validates the canonical payload and product suite, then
creates deterministic portable archives and a tracked publication record.
It packages AEGIS itself; it does not deploy a runtime service or modify a
downstream repository.

## Public interface

Run `py -3.12 02_Tools/build_aegis_release.py --version <version>`. The
requested version must match the payload CLI and have a dated changelog entry.
Archives are written to `07_Delivery/dist/`; checksums and metadata are written
to `07_Delivery/aegis-<version>/`.

## Key behaviors

- `REQ-REL-59983fe5` - Build deterministic versioned delivery archives.
- `REQ-REL-d875f7a3` - Reject inconsistent release metadata before output.
- `REQ-REL-858e8cac` - Validate the payload and product suite before assembly.

## Files

- `02_Tools/build_aegis_release.py` - Deterministic archive and record builder.
- `02_Tools/README.md` - Builder invocation and output contract.
- `07_Delivery/README.md` - Delivery-record layout.
- `07_Delivery/aegis-0.6.0/` - Current tracked publication record.
- `05_Software/aegis/tests/test_release_builder.py` - Isolated builder
  characterization tests.
