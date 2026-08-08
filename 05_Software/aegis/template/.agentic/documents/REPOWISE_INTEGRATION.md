<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Optional RepoWise Integration

RepoWise is an optional, process-isolated repository-discovery provider. AEGIS
only validates and reads its structural artifacts. RepoWise never becomes
authoritative AEGIS workflow state and never replaces human-entered discovery.

## Policy

The optional strict file is `.agentic/integrations/repowise.toml`:

```toml
schema_version = 1
provider = "repowise"
mode = "disabled"                 # disabled | advisory | required
source = "none"                   # none | bundled | external
version_spec = ">=0.37.0,<0.38.0"
artifact = ".repowise/knowledge-graph.json"
state = ".repowise/state.json"
require_head_match = true
require_worktree_match = true
```

Absence means disabled. This file is separate from schema-3
`.agentic/workflow.toml`; enabling it does not migrate or alter workflow or
run-graph schema.

Provider installation, configuration, status inspection, and synchronization
have no AEGIS command. Use the selected external deployment tool's current
documentation for those operations. AEGIS does not validate that tool's own
version or compatibility claims.

Do not hand-edit generated runtime metadata or receipts. No credentials belong
in the AEGIS policy or receipt. `.repowise/`, project-local provider runtimes,
and execution metadata are reproducible local state and should remain excluded
from Git. The validated run-local discovery snapshot is the durable AEGIS
record.

## Freshness and Authority

A successful provider synchronization supplies
`.agentic/integrations/repowise-receipt.json` with:

- receipt schema and provider/source identity;
- RepoWise version, profile, completion state, and timestamp;
- Git HEAD and a worktree fingerprint;
- knowledge-graph and state paths and SHA-256 digests.

At `repo-discovery`, AEGIS validates the strict policy, receipt, the supported
RepoWise 0.37.0 release line, graph/state JSON schemas, hashes, HEAD, and
worktree fingerprint. It then writes normalized proposals and provenance to:

```text
.agentic/runs/<run-id>/discovery/repowise.json
```

Current data may pre-populate otherwise empty source-root, component,
dependency, entry-point, and existing-test fields. Existing human content is
preserved. `advisory` mode warns when evidence is unavailable or stale;
`required` mode blocks repository-discovery closure until it is current.

AEGIS never imports RepoWise Python code, runs a RepoWise command, registers its
MCP server, or treats generated prose as evidence. AEGIS consumes only the
validated structural graph data.

## Portability and Offline Boundary

The `source` field records one of three deployment states:

- `none` - integration is disabled and no provider runtime is required;
- `external` - the deployment links a machine-level provider that must be
  re-established on another machine;
- `bundled` - an external deployment tool provisioned a project-local runtime
  that is not part of normal Git history.

AEGIS reads this state but does not provision, restore, update, or execute the
runtime. A copied Git repository is self-contained only when the integration is
disabled; otherwise the selected deployment tool must restore the provider and
produce fresh validated artifacts.

RepoWise is licensed separately under AGPL-3.0-or-later. Any distribution that
bundles it must preserve the required source, notices, provenance, and hashes
and review the applicable obligations before delivery.
