<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Upgrading a Deployed AEGIS Payload

AEGIS does not install or upgrade its own payload. Use a trusted external
deployment tool or a reviewed manual copy procedure, and follow that tool's
current compatibility guidance. This document defines only the AEGIS-owned
state and validation boundary.

Never assume that an older configuration, graph, or active run is compatible
with a newer payload. AEGIS 3.0 accepts schema-3 workflow configuration and
refuses unsupported schemas instead of migrating them silently.
The shipped interface default is `stage_form_retention = "latest"`; preserve a
project's explicit value only when the new payload validates it.

## Ownership Boundary

Treat the deployment tool's authenticated install manifest as the authority
when one exists. In its absence, use this conservative split:

| Payload-owned material to replace from the new distribution | Project-owned material to preserve and review |
| --- | --- |
| `.agentic/cli/`, `.agentic/tools/`, `.agentic/hooks/`, `.agentic/documents/`, and `.agentic/skills/` | `.agentic/workflow.toml` and `.agentic/integrations/repowise.toml` |
| Shipped host-adapter files under `.claude/`, `.codex/`, `.opencode/`, `.pi/`, and `.qwen/` | `.agentic/requirements/`, `.agentic/specs/`, and `.agentic/knowledge/` |
| Payload license and starter templates | `.agentic/components.toml`, `.agentic/reports/`, and `.agentic/runs/` |

Root adapter instructions such as `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, and
`opencode.json` can contain both payload and project customization. Resolve
their ownership through the install manifest or an explicit review; never
overwrite them blindly.

Runtime caches, generated provider artifacts, worktree-local selection state,
and lock files are neither portable project history nor payload source. Rebuild
them only through the owning tool.

## Before Replacing the Payload

1. Record the current AEGIS version, configuration schema, Git state, and
   deployment-tool receipt or manifest.
2. Back up every project-owned path and any intentionally customized adapter
   file.
3. Finish or explicitly abandon active runs unless compatibility with the new
   payload is documented and verified.
4. Review the new release notes for schema, CLI, hook, adapter, and ownership
   changes.
5. Preview the exact replacement set and resolve conflicts explicitly.

Do not edit durable graph, journal, evidence, requirement, or receipt files to
make an upgrade appear compatible.

## After Replacing the Payload

From the governed repository, use its project-local wrapper:

```text
<workflow> --help
<workflow> config validate --json
<workflow> config show --json
<workflow> requirement list --json
<workflow> run status --json
```

`<workflow>` means `.\.agentic\tools\run.ps1` on Windows or
`bash .agentic/tools/run.sh` on POSIX. Correct invalid configuration through a
reviewed policy change; do not infer fallback values. Confirm that required
hooks and adapter trust are active, and inspect any current run before resuming
it.

An upgrade is not a release, push, merge, or publication action. Those remain
separate explicit operations.
