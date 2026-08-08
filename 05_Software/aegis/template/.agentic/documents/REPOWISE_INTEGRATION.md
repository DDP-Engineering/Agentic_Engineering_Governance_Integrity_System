<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Optional External RepoWise Integration

RepoWise is optional process-isolated repository-discovery input. AEGIS can
validate and normalize its structural artifacts during adoption discovery but
never imports RepoWise code or executes its CLI. WAEGIS 3 does not install,
configure, synchronize, inspect, or distribute RepoWise.

The optional adapter contract shipped with AEGIS 3 is validated against
RepoWise 0.37.0. The repository operator remains responsible for installing
and maintaining that external tool.

## Policy

The optional closed policy file is `.agentic/integrations/repowise.toml`:

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

Absence means disabled. The file is separate from `workflow.toml` schema 3.
The repository operator or a separately managed external tool owns any change.
The `source` value describes where externally managed evidence came from; it
does not make AEGIS or WAEGIS install a runtime.

## Freshness and authority

At `repo-discovery`, AEGIS validates the strict policy, supported version,
graph/state schemas, recorded hashes, Git HEAD, and worktree fingerprint. It
normalizes accepted structural proposals into the run-local discovery record.
Current proposals may fill otherwise empty discovery fields but never replace
human-entered content. Advisory unavailability warns; required unavailability
blocks repo-discovery closure.

External integration state is reproducible local data and should not be
mistaken for durable AEGIS evidence. The normalized run snapshot, provenance,
and human decisions are the AEGIS record.

## Operating boundary

- Configure and refresh RepoWise only through an explicit operator process
  separate from WAEGIS.
- Do not ask AEGIS to run the integration; no such command exists.
- Do not treat generated prose, MCP setup, editor files, or model output as
  authoritative workflow state.
- Review RepoWise's separate license and distribution obligations wherever the
  external tool is obtained or delivered.

Disabling or removing the integration does not disable AEGIS. RepoWise
lifecycle automation remains outside the WAEGIS 3 product and release.
