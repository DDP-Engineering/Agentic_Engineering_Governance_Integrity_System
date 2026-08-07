---
name: agentic-delivery
description: Use when preparing delivery, reports, commits, PRs, pushes, merges, or final preflight for an agentic workflow run.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Delivery

This Claude Code entry point defines no stage procedure. The payload-owned
canonical bootstrap is `AGENTS.md` -> `<workflow> run context --json` -> only
the named recovery command (including `stage prepare` only when named) -> only
the named `required_reads` -> the current stage's human approval boundary. Do
not load all stage references or read internal run files for ordinary recovery.

Read and follow these shared workflow rule sources:

- `AGENTS.md`
- `.agentic/skills/agentic-delivery/SKILL.md`

Claude Code invocation: `/agentic-delivery`.

Do not commit, push, create a PR, merge, or publish until delivery preflight
passes and the human explicitly approves the action.
