<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Example: Existing Repository Adoption

1. WAEGIS 1.1 analyzes explicit scripts, tool configuration, Make targets, and
   CI commands and proposes build/typecheck/lint/test/security gates. It never
   invents a security command.
2. The operator selects discovery: disabled; a validated external RepoWise
   0.37.x command; or the Complete edition's pinned RepoWise 0.37.0 sidecar.
   New-project indexing defaults to No; adoption defaults to Yes. `--yes` never
   silently opts into indexing.
3. WAEGIS configures AEGIS and RepoWise as separate transactions. A failed
   index leaves AEGIS and the sidecar configured, records its log, and reports
   `waegis repowise sync --repo "<project>"`. When the adoption commit was
   accepted, the selected RepoWise policy is recorded in a second narrow
   configuration commit; an adoption left uncommitted keeps it with the other
   pending changes.
4. The operator reviews schema-3 interface policy, every gate group, and the
   separate schema-1 RepoWise integration, then deploys AEGIS 2.1.
5. `aegis run start adoption` prepares adoption intake.
6. The specialized adoption stages use the same prepare/apply/close lifecycle:
   alignment, repository discovery, component map, component adoption,
   baseline review, adoption delivery.
7. At `repo-discovery`, AEGIS validates RepoWise version, receipt, graph/state
   schemas, hashes, Git HEAD, and worktree fingerprint. Current data can
   pre-populate empty source-root, component, dependency, entry-point, and test
   fields, with provenance in a durable run-local snapshot.
8. Human-entered discovery remains authoritative. Advisory RepoWise failures
   warn; only an explicitly required integration blocks the stage.
9. Delivery closure records completion without publishing.

An AEGIS 1.x install is not upgraded in place. Preserve intended project-owned
artifacts and deploy a fresh AEGIS 2.x payload.
