<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS - user documentation

Guides for the assigned **AEGIS 0.14.0** source, including the OpenCode,
Codex, Pi, Qwen Code and Claude Code integrations. Existing delivery archives
and their build records are under `07_Delivery/`. Assigning a source version
does not build or publish those packages.

Start with installation and folders, then choose the relevant worked example.
Examples illustrate the workflow; sample output is not evidence of a test run.
For 0.14.0 verification setup, start with
[focused routing](01_Install_and_Setup.md#verify-focused-routing-before-using-it).
The folder guide explains lean records and saved evidence; the FAQ and prompt
cheatsheet cover focused tests, final proof and minimal handoffs.

| Guide | Read when | Slides |
|---|---|---|
| [01 - Install and setup](01_Install_and_Setup.md) | Installing the repository core and an optional host package. | [PPTX](01_Install_and_Setup.pptx) |
| [02 - Folders and files](02_Folders_and_Files.md) | Understanding durable records, configuration and local integration state. | [PPTX](02_Folders_and_Files.pptx) |
| [03 - Feature](03_Example_Feature.md) | Taking new behavior through the full workflow. | [PPTX](03_Example_Feature.pptx) |
| [04 - Quick fix](04_Example_Quick_Fix.md) | Restoring an existing requirement with a small, eligible fix. | [PPTX](04_Example_Quick_Fix.pptx) |
| [05 - Adoption](05_Example_Adoption.md) | Bringing existing behavior under governance, component by component. | [PPTX](05_Example_Adoption.pptx) |
| [06 - Team setup](06_Team_Setup.md) | Sharing records, configuring CI and reviewing combined work. | [PPTX](06_Team_Setup.pptx) |
| [07 - FAQ](07_FAQ.md) | Understanding capabilities and limits. | [PPTX](07_FAQ.pptx) |
| [08 - Prompt cheatsheet](08_Prompt_Cheatsheet.md) | Starting, resuming and handing over work. | [PPTX](08_Prompt_Cheatsheet.pptx) |
| [09 - CLI reference](09_CLI_Reference.md) | Looking up core command syntax, options and exit behavior. | - |
| [Project context](Project_Context.md) | Maintaining current project/environment facts and positive behavior documentation. | - |
| [Agent plugins](Agent_Plugins.md) | Building, distributing, installing and operating all five integrations. | - |
| [Plugin installation manual](Plugin_Installation/README.md) | Step-by-step, illustrated installation for OpenCode, Codex, Pi, Qwen Code and Claude Code. | [Combined PDF](Plugin_Installation/pdf/00_AEGIS_Plugin_Installation_Manual.pdf) |

The decks are condensed companions. The Markdown guides contain the detailed
commands and limitations. The plugin installation folder also provides five
standalone PDFs, a combined manual and installation illustrations.
The manuals describe current procedures; release and verification history stays
in linked task/build records rather than their setup instructions.
The installed `.agentic/AGENTS.md`, stage files and CLI define the repository
workflow; integration source and package READMEs define host-specific behavior.
A host plugin does not replace the core payload.

This repository excludes documentation-only updates from AEGIS task governance.
Edit and review documentation directly; use AEGIS for software-development work.
Backend registration checks do not establish Desktop GUI or model-led workflow
acceptance; see the plugin guide for the recorded verification boundary.
