---
name: agentic-adoption
description: Codex adapter for adopting an existing project into the shared agentic workflow before feature, fix, or behavior-change work.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Adoption

This Codex entry point defines no stage procedure. The payload-owned canonical
bootstrap is `AGENTS.md` -> `<workflow> run context --json` -> only the named
recovery command (including `stage prepare` only when named) -> only the named
`required_reads` -> the current stage's human approval boundary. Do not load all
stage references or read internal run files for ordinary recovery.

Read and follow this shared workflow rule source:

- `.agentic/skills/agentic-adoption/SKILL.md`

Codex invocation: `$agentic-adoption`.

The full, platform-neutral procedure lives in
`.agentic/skills/agentic-adoption/SKILL.md`. This file is only the Codex
adapter entry point.
