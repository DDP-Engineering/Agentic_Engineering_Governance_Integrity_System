<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 2.1 Human Explanations

> Historical archive: these guides describe the AEGIS 2.1 deployment model.
> They are preserved as versioned background material and are not the current
> AEGIS 3.0 workflow or deployment contract.

These guides explain the former AEGIS 2.1 deployment in plain language. They
are organized by the lifecycle and purpose of an artifact, rather than by the
order in which the files were inspected.

Every guide answers the same four questions:

1. What does this file or folder represent?
2. What type of data does it hold?
3. Who creates or updates it?
4. Why does AEGIS keep it?

## Guide map

| Guide | Domain | Status |
| --- | --- | --- |
| [01_Installation_Payload_And_Configuration.md](01_Installation_Payload_And_Configuration.md) | The installed payload, installation receipt, configuration, local CLI, and shipped reference material. | Available |
| [02_Agent_Adapters_Hooks_Integrations_And_Skills.md](02_Agent_Adapters_Hooks_Integrations_And_Skills.md) | Adapter configuration for supported agent tools, hooks, launchers, integrations, and skills. | Available |
| [03_Durable_Governance_State.md](03_Durable_Governance_State.md) | Components, requirements, specifications, knowledge, coverage waivers, and the durable adoption-report archive. | Available |
| [04_Workflow_Run_Records.md](04_Workflow_Run_Records.md) | Run folders, graphs, journals, stage forms, evidence, reports, and validation summaries. | Available |
| [05_Maintenance_Upgrade_Transactions_And_Legacy_History.md](05_Maintenance_Upgrade_Transactions_And_Legacy_History.md) | Payload upgrades, transactions, repair, legacy records, and safe operational maintenance. | Available |

For current operator behavior, use the documentation shipped under
`05_Software/aegis/template/.agentic/documents/` and the maintained AEGIS guides
in the parent `06_SoftwareDocu/` folder. Deployment-tool claims in this archive
are historical and do not establish current WAEGIS compatibility.
