<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Planning

Planning notes, requirements, architecture sketches, and future workflow design
records for the standalone AEGIS project belong here.

- `Agentic_Development_Architecture/` - the agentic development stack
  architecture document, including the current feature/fix and
  existing-project adoption execution models.
- `Agentic_Development_Architecture_Examples/` - worked feature and bug-fix
  examples of the workflow, including Intent Alignment before requirement work.
- Pi adapter behavior is documented by the stack architecture and the copied
  template assets under `05_Software/aegis/template/.pi/`.
- WAEGIS implementation behavior is documented by
  `05_Software/waegis/README.md` and the source-local module documentation.
- OpenCode adapter behavior is documented in the stack architecture and the
  copied template assets under `05_Software/aegis/template/.opencode/` and
  `05_Software/aegis/template/opencode.json`.
- Qwen Code adapter behavior is documented in the stack architecture and the
  copied template assets under `05_Software/aegis/template/.qwen/` and
  `05_Software/aegis/template/QWEN.md`.
- `Agentic_Flow_Artifact_Map.svg` maps the workflow stages to the `.agentic`
  files, commands, hooks, and skills that create or update persisted workflow
  information.
- `Aegis_Artifact_Flow.svg` - stage-by-stage map of which skills,
  commands, scripts, and hooks create or update `.agentic` workflow artifacts.
- `Aegis_Artifact_Flow_ro.svg` - Romanian version of the `.agentic`
  workflow artifact flow map.
- `Aegis_Architecture_Presentation.pptx` - slide deck overview of the
  AEGIS architecture.
- `PROMPT_CHEATSHEET.md` - planning reference copy of the operator prompt cheat
  sheet; the canonical copy ships at
  `05_Software/aegis/template/.agentic/documents/PROMPT_CHEATSHEET.md`.
