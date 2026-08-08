---
name: agentic-development
description: Manual AEGIS workflow for full feature, fix, and change runs or proportional quick runs for genuinely small fixes and changes, with human-approved stages, validation, and evidence capture. Use when the user asks to implement a feature, fix a defect, change behavior, add tests for a planned change, or continue an agentic development run.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Development

This Codex entry point defines no stage procedure. The payload-owned canonical
bootstrap is `AGENTS.md` -> `<workflow> run context --json` -> only the named
recovery command (including `stage prepare` only when named) -> only the named
`required_reads` -> the current stage's human approval boundary. Do not load all
stage references or read internal run files for ordinary recovery.

Read and follow these shared workflow rule sources:

- `AGENTS.md`
- `.agentic/skills/agentic-development/SKILL.md`

Codex invocation: `$agentic-development`.

The full, platform-neutral procedure lives in
`.agentic/skills/agentic-development/SKILL.md`. This file is only the Codex
adapter entry point.
