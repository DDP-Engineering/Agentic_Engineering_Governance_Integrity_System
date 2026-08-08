<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Software Documentation

Deeper implementation and operating guidance for AEGIS 3 and WAEGIS 3 lives
here. Canonical runnable-workflow documents remain in the copied AEGIS
template so downstream repositories receive references matching their CLI.

## Operator path

- `01_Getting_Started_Install_And_Adopt.md` - WAEGIS 3 entry points,
  prerequisites, distribution choices, consent, ownership, and recovery.
- `02_Everyday_Work_Full_Runs.md` - complete AEGIS development lifecycle.
- `03_Quick_Runs_And_Bypassing_AEGIS.md` - proportional quick-run contract.
- `04_Configuring_AEGIS.md` - schema-3 project policy.
- `05_Reading_AEGIS_Metadata.md` - durable workflow state and evidence.
- `06_AEGIS_Adapter_And_Context_Conformance.md` - host adapters and bounded
  context contract.
- `AEGIS_3_0_HumanExplanations/` - installation, adapters, durable state, run
  records, and WAEGIS 3 maintenance/recovery explained by domain.

## Canonical copied references

- `05_Software/aegis/template/.agentic/documents/CLI_API_REFERENCE.md`
- `05_Software/aegis/template/.agentic/documents/ADAPTER_CONFORMANCE.md`
- `05_Software/aegis/template/.agentic/documents/POLICY_CONFIGURATION.md`
- `05_Software/aegis/template/.agentic/documents/PROMPT_CHEATSHEET.md`
- `05_Software/aegis/template/.agentic/documents/WORKFLOW_CONFIGURATION.md`
- `05_Software/aegis/template/.agentic/documents/REPOWISE_INTEGRATION.md`

## Presentations

Existing PPTX files are retained as historical presentation material. Their
AEGIS 2.x/WAEGIS 1.x screenshots and Core/Complete or RepoWise lifecycle claims
are not current WAEGIS 3 operating documentation. Current behavior is defined
by the Markdown references above and `05_Software/waegis/README.md`.
