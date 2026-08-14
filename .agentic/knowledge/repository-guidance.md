<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Repository guidance

## Purpose

Repository guidance explains both how downstream users operate AEGIS and how
maintainers develop, validate, package, and document AEGIS itself. It is
human-facing reference material, reviewed by inspection rather than through
tests that assert prose or layout.

## Public interface

New users begin with `06_SoftwareDocu/00_Index.md`, then installation and the
relevant workflow example. Maintainers use the root README and AGENTS guidance
for product location, validation, style, documentation, tooling, and delivery
boundaries.

## Key behaviors

- `REQ-UX-62a24243` - Guide AEGIS installation, operation, and adoption.
- `REQ-PLAT-8e0b2623` - Document repository boundaries and delivery process.

## Files

- `README.md` and `AGENTS.md` - Product boundary and maintainer contract.
- `00_Planning/` - Design rationale and implementation records.
- `01_Documentation/Code_Style.md` - Source and documentation style.
- `02_Tools/README.md` - Release builder instructions.
- `06_SoftwareDocu/` - User installation, operation, examples, FAQs, prompts,
  and CLI reference.
- `07_Delivery/README.md` - Delivery-output and publication-record layout.
