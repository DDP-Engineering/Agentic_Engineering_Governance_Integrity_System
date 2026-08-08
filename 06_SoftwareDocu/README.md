<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Software Documentation

Implementation notes, workflow contracts, and deeper technical documentation
for AEGIS belong here. Canonical runnable-workflow documentation ships with the
template:

- `05_Software/aegis/template/.agentic/documents/CLI_API_REFERENCE.md` - CLI
  command groups, stage-form lifecycle, evidence modes, verification, and
  delivery handoff.
- `05_Software/aegis/template/.agentic/documents/ADAPTER_CONFORMANCE.md` -
  direct CLI and host-adapter entry points, payload-owned routing, bounded
  bootstrap, and shared execution-outcome contracts.
- `05_Software/aegis/template/.agentic/documents/POLICY_CONFIGURATION.md` -
  intrinsic workflow contracts, repository-policy modes, external safety
  boundaries, and operator decisions.
- `05_Software/aegis/template/.agentic/documents/PROMPT_CHEATSHEET.md` -
  operator-ready prompts for each workflow gate.
- `05_Software/aegis/template/.agentic/documents/WORKFLOW_CONFIGURATION.md` -
  complete schema-3 structure, captured interface policy, five independent
  optional deterministic gates, traceability, and guardrails.
- `05_Software/aegis/template/.agentic/documents/REPOWISE_INTEGRATION.md` -
  optional schema-1 RepoWise discovery policy, evidence freshness, offline
  boundary, and authority model.

## Maintained AEGIS Guides

- `02_Everyday_Work_Full_Runs.md` - full feature, fix, and change runs.
- `03_Quick_Runs_And_Bypassing_AEGIS.md` - proportional quick runs and their
  explicit bypass semantics.
- `04_Configuring_AEGIS.md` - schema-3 workflow policy and optional schema-1
  RepoWise integration.
- `05_Reading_AEGIS_Metadata.md` - durable and transient AEGIS state.
- `06_AEGIS_Adapter_And_Context_Conformance.md` - adapter compatibility,
  canonical bootstrap ownership, bounded context, and public execution
  outcomes.

## Deferred Installation Material

`01_Getting_Started_Install_And_Adopt.md` and its companion `.pptx` describe
installation and adoption through WAEGIS. They are retained but are not current
AEGIS 3.0 compatibility guidance; their refresh is deferred to the separate
WAEGIS redesign. Consult the WAEGIS package documentation before using those
instructions.

## Historical Material

`AEGIS_2_1_HumanExplanations/` is an explicitly historical explanation set for
AEGIS 2.1. It is preserved for provenance and must not be treated as the
current AEGIS 3.0 contract.
