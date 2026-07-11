<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Intent Alignment

Intent Alignment is a first-class workflow stage after `intake` and
`adoption-intake`. It records what the agent believes the work is before
requirement/spec work or adoption discovery proceeds.

The command is:

```text
aegis alignment --source "<ref>" --understanding "<text>" --scope "<scope>" --acceptance "<criterion>" --risk low|medium|high --decision proceed|pause --reason "<reason>"
```

The command stores the latest record in the active run `graph.json` under
`alignment` and appends every record to `journal.jsonl` as
`alignment.recorded`.
`status` and `report` expose the current record for review.

Policy is configured in `.agentic/workflow.toml` under `[alignment]`.
Open questions, risk at or above the configured threshold, or planned paths that
match protected scope patterns require `decision pause`. When automated
continuation is acceptable, each open question can have a recommended response
that states the answer the agent will assume. `enabled = false` skips
`alignment` and `adoption-alignment` during `next` routing. The command never
advances the workflow stage by itself.

The core workflow is independent of Jira, GitHub, GitLab, or any other tracker.
It does not post comments, wait on timers, or schedule automatic continuation.

The shared `.agentic/skills/agentic-development` and
`.agentic/skills/agentic-adoption` procedures are the adapter contract.
Codex, Claude Code, Pi, OpenCode, and Qwen inherit Intent Alignment behavior
through their existing thin skill wrappers.
