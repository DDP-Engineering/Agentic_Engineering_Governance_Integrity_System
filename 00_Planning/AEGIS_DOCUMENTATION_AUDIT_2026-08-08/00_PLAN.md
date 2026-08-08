<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Documentation Audit Plan

## Objective

Audit every maintained document that describes the runnable Heavy AEGIS
implementation, correct stale current guidance, and give historical or
externally owned material an explicit disposition.

This audit does not execute an AEGIS workflow. It is ordinary repository
maintenance performed in an isolated Git worktree.

## Scope

The inventory contains 125 artifacts:

- 124 tracked Markdown, text, or presentation files covering AEGIS root
  guidance, the Heavy AEGIS package and copied template, direct software
  documentation, and AEGIS-related planning records;
- the Python generator that renders the optional start-guide PDF.

WAEGIS implementation and documentation are excluded because WAEGIS is under
active redesign. AEGIS-Light, delivery bundles, miscellaneous local material,
and immutable JSON pilot evidence are also excluded. Mixed AEGIS/WAEGIS
documents are reviewed only far enough to classify them; their WAEGIS-owned
instructions are deferred rather than guessed or rewritten.

## Audit Method

1. Freeze the branch, worktree status, and AEGIS 3.0 implementation baseline.
2. Inventory tracked documentation and assign each artifact one disposition.
3. Check Markdown links, paths, commands, versions, schema claims, retention
   defaults, adapter mappings, template genericity, and text encoding.
4. Compare maintained workflow guidance with the CLI parser, configuration,
   source contracts, and focused tests.
5. Correct stale current material while preserving historical evidence.
6. Add focused regressions for branding, catalog integrity, template hygiene,
   and generated-document placement.
7. Run focused and broad AEGIS-only validation plus CLI and Python checks.

## Acceptance Criteria

- Every inventory group has an explicit current, updated, historical, or
  deferred disposition.
- Maintained AEGIS entry points identify the 3.0 payload and contain no obsolete
  2.x deployment-tool compatibility range.
- Documented development-stage commands remain real parser contracts.
- Copied template documentation stays generic and free of fixed project
  measurements or generated binaries.
- Historical AEGIS 2.1 material remains available but cannot be mistaken for
  the current contract.
- No WAEGIS source or documentation is changed.
- Validation results and residual risks are recorded without committing or
  pushing automatically.
