<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS version 1 implementation

## Product boundaries

AEGIS is copied into `.agentic/aegis/` and owns that complete manifest-listed
payload. Every other `.agentic/` path is project-owned. WAEGIS is a separate
operator application and is never installed as part of the payload.

Both products keep domain and application policy inward of ports and concrete
filesystem, process, Git-observation, and presentation adapters. They copy the
small common machine-envelope contract locally so neither runtime imports the
other and no third runtime package is required.

## AEGIS state and publication

Run and Stage Markdown documents hold their own versioned metadata, current
sections, append-preserved events, evidence, findings, dispositions, decisions,
escapes, and attachment references. Requirements, Specifications, and
Components contain only current project knowledge. Deleting or replacing them
does not delete application source or tests; the owning Stage retains the
durable action evidence.

Mutations prepare exact before/after bytes below `.agentic/.runtime/`, validate
expected revisions under a working-copy lock, persist the commit decision, and
recover to a complete before-or-after state. Runtime material is transient and
never authoritative project data.

Configured commands execute as argument arrays with `shell=False`, isolated
process groups, concurrently drained output, explicit timeout/cancellation,
and the five exact outcomes. Unfavorable project outcomes remain successful
AEGIS protocol records with truthful engineering conclusions.

## WAEGIS lifecycle

Every mutation has a read-only `*-plan` operation and a separate `*-apply`.
Plans are operator-owned JSON outside the target, enumerate exact writes or
deletions and ownership, and are authorized by the SHA-256 of their exact
bytes. Apply revalidates both the digest and target fingerprint before its
first target write. Interrupted filesystem publication rolls the same
authorized plan forward from WAEGIS-local recovery data.

Installation creates complete detected/default configuration, preserves
existing project data, and adds only local context/runtime exclusions. Upgrade
and removal use the installed payload manifest as the sole ownership boundary.
Only `repository-init-apply` can run Git, and that adapter exposes only local
`git init`.

## Release tooling and validation boundary

The standalone `02_Tools/build_aegis_release.py` script builds stable ZIP member
order, timestamps, bytes, prerequisites, and exact archive inventories, and can
inspect those archives without extracting them. Dependency-excluding Windows
and Ubuntu archive shapes are buildable from source. Dependency-including builds
refuse until `02_Tools/runtime_inputs.toml` contains real local Python 3.12 and
Git archives with exact versions and SHA-256 digests.

The repository does not retain a separate automated test package for this
maintenance script. Compilation and explicit build/inspect smoke commands check
the local tool path; supported-host, Ubuntu, private-runtime, network-denied,
and downstream-repository acceptance remain part of the later IP-18 campaign.
