<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Software Documentation

Implementation notes, workflow contracts, and deeper technical documentation
for the AEGIS and WAEGIS packages belong here. Canonical runnable-workflow
documentation ships with the template:

- `05_Software/aegis/template/.agentic/documents/CLI_API_REFERENCE.md` - CLI
  commands, evidence lifecycle, requirement activation, audits, and delivery
  preflight.
- `05_Software/aegis/template/.agentic/documents/POLICY_CONFIGURATION.md` -
  intrinsic workflow contracts, repository-policy modes, external safety
  boundaries, and operator decisions.
- `05_Software/aegis/template/.agentic/documents/PROMPT_CHEATSHEET.md` -
  operator-ready prompts for each workflow gate.
- `05_Software/aegis/template/.agentic/documents/WORKFLOW_CONFIGURATION.md` -
  complete schema-version-2 structure, validation, modes, traceability, gates,
  and configured guardrails.

Presentation material maintained in this folder (WAEGIS 0.3.0):

- `WAEGIS_01_Setup_And_First_Adoption.pptx` - setup and first-adoption journey.
- `WAEGIS_02_Architecture_Portability_And_MultiLanguage.pptx` - architecture,
  portability, and multi-language overview.
- `WAEGIS_02_Safe_AEGIS_Upgrade.pptx` - moving an installed project to a new
  AEGIS payload version without overwriting local work.

Stakeholder architecture decks (split by scope, one shared visual system):

- `WAEGIS_Architecture_Presentation.pptx` - WAEGIS as the deployment wizard: the
  five-phase run, the configuration interview, `new` versus `adopt`, and the
  managed lifecycle.
- `AEGIS_Governance_Workflow_Presentation.pptx` - AEGIS as the governance
  workflow: the seven development stages (input, gate, and output for each), the
  enforcement layers, and the adoption track.
