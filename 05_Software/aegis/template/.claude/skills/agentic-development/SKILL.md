---
name: agentic-development
description: Use for feature, bug fix, or behavior-change work that should follow the shared agentic development workflow gates, including the proportional --quick profile for genuinely small fixes and changes.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Development

This Claude Code entry point defines no stage procedure. The payload-owned
canonical bootstrap is `AGENTS.md` -> `<workflow> run context --json` -> only
the named recovery command (including `stage prepare` only when named) -> only
the named `required_reads` -> the current stage's human approval boundary. Do
not load all stage references or read internal run files for ordinary recovery.

Read and follow these shared workflow rule sources:

- `AGENTS.md`
- `.agentic/skills/agentic-development/SKILL.md`

Claude Code invocation: `/agentic-development`.

Interpret any Codex-style `$write-component-documentation`,
`$documentation-audit`, or `$python-codestyle-audit` reference as the matching
Claude Code skill under `.claude/skills/`.
