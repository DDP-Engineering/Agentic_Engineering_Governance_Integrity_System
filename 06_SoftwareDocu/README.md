<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Software documentation

Start at [00_Index.md](00_Index.md) for the installation guide, worked examples,
team guidance, FAQ and prompt cheatsheet. Guides 01-08 each have a matching
PowerPoint deck; decks summarize the detailed Markdown rather than replace it.

These documents describe the assigned **AEGIS 0.10.0** project at
`05_Software/aegis/` and its five host integrations:
OpenCode, Codex, Pi, Qwen Code and Claude Code. See
[Agent_Plugins.md](Agent_Plugins.md) for distribution and installation and
[Plugin_Installation/README.md](Plugin_Installation/README.md) for illustrated,
host-by-host installation manuals in Markdown and PDF. See
[09_CLI_Reference.md](09_CLI_Reference.md) for the core command surface.

The core keeps durable workflow records in the repository. Optional packages
add native host resources, local runtime/ownership records and tracked jobs in
a separate cache. Each user retains their own authentication and model settings.
Backend verification is distinct from Desktop GUI or model-led acceptance.

The installed contract, stage files and CLI define core behavior; integration
source and package READMEs define host behavior. Examples are illustrative.
Documentation-only updates here are reviewed directly, without AEGIS task
journals or development test runs. Update Markdown and slide companions
together when their shared content changes.

The plugin installation PDFs are generated from their Markdown sources. Their
figures distinguish isolated command evidence from unavailable Desktop UI
acceptance; they do not turn a backend or package check into a GUI claim.
