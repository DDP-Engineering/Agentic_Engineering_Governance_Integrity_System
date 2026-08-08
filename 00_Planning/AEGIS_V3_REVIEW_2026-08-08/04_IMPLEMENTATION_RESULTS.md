<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.0.0 Review Implementation Results - 2026-08-08

## Scope and baseline

The review was checked against the runnable AEGIS payload on branch `master`
at commit `8a72b5a4399f`. That is the implementation revision identified by the
review, so no baseline drift had to be reconciled. WAEGIS and AEGIS Light
remain outside this correction scope.

The implementation work preserves the successful user workflow, command
groups, stage sequence, and delivery outcome. Corrections close bypasses,
restore documented response and recovery contracts, make failure paths
bounded, and replace misleading documentation where expanding enforcement
would have changed policy behavior.

## Review disposition

### Corrected findings

The implementation corrects V3-01 through V3-14, V3-17 through V3-50 except
V3-34, and V3-52 through V3-60. The main tangible results are:

- UTF-8 is pinned at the CLI and hook boundaries, malformed state stays inside
  typed recovery paths, and run listing/abandonment remain available when
  workflow configuration or a run journal is damaged.
- Shell/write/secret/delivery guards now cover attached and noclobber
  redirects, target-directory copy/move forms, patch moves, notebook writes,
  nested replaced text, nested workflow lookalikes, and Git executable flags.
- Stage context, stage routing, evidence finality, waiver staleness, coverage
  reporting, response scalars, exact next commands, schema hints, and copied
  CLI/invariant documentation now agree with their runtime contracts.
- Repeated managed checks retain immutable logs, disabled gates retain an
  exact waiver target, legal repeated argv tokens remain legal, and complete
  gate/check process trees are terminated on timeout.
- Working-tree status is read with strict UTF-8, a 30-second bound, and
  NUL-delimited rename records; atomic publication no longer changes the
  process-wide umask; interrupted run temporaries are ignored by Git; and the
  local-model pilot reports a failed verification diagnostic instead of
  losing its accumulated result to `KeyError`.
- Component-map forms name and protect the configured manifest, RepoWise input
  shapes and paths are bounded at their trust boundary, reports are published
  atomically, bracket-bearing paths remain traceable/protectable, and Windows
  source-extension matching follows Windows case behavior.

V3-08 was confirmed as a coverage gap, but wiring protected-read policy into
arbitrary shell commands would expand enforcement and change user-visible
policy outcomes. The maintained contract now states accurately that protected
reads cover dedicated read/search tools, not shell reads.

V3-17 was also confirmed. The `[alignment]` table remains accepted compatibility
metadata so existing workspaces do not break, while the starter configuration
and operator documentation now say explicitly that it does not control routing,
closure, or path enforcement.

V3-56 is corrected at the repository-integrity boundary: a hard-kill may still
leave a harmless sibling temporary, but the template now excludes those files
from Git so they cannot become durable workflow evidence or ship accidentally.

### Valid findings deliberately not changed

V3-15, V3-16, and V3-34 are valid. The review itself places them in the
owner-decision batch because changing the repository root and shared glob
semantics changes which paths are evaluated and blocked. They were therefore
not implemented under the requirement to preserve the current user-visible
functionality and outcome.

### Statement not confirmed

V3-51 is not accurate for this baseline. RepoWise status and warnings are
generated during `repo-discovery` preparation, but `stage apply` does not call
the merge routine and does not overwrite edited values. The fields have no
runtime consumer after import, so no corrective behavior change was made.

### Simplification proposals

The deletion batch was not applied. Removing RepoWise, the local-model pilot,
alignment compatibility keys, or other shipped surfaces requires the explicit
owner decision named by the remediation plan and could change supported usage.
The behavior-preserving S12 duplicate component-manifest parse was removed;
the retained RepoWise and pilot surfaces received the applicable defect fixes.

## Validation evidence

- `uv run --group dev ruff check template/.agentic/cli/src/aegis template/.agentic/hooks tools tests`: passed.
- `python -m py_compile` over all 46 changed Python files: passed.
- `uv run --group dev python -m pytest -q tests`: 669 passed, 3 skipped in
  96.40 seconds.
- `uv run --group dev python -B -m aegis --help`: passed and retained the same
  top-level command groups.
- `git diff --check`: passed; the remaining PowerShell line-ending message is
  Git's configured LF-to-CRLF conversion warning, not a whitespace error.

The three skipped tests are POSIX-only filename/mode cases on this Windows
host. Live execution inside every external adapter host was not repeated; the
adapter hook contracts were covered through the Python hook regression suite.
