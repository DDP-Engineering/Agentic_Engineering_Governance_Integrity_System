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
  architecture document and future workflow-mode specifications, including
  existing-project adoption mode and its implementation plan.
- `Agentic_Development_Architecture_Examples/` - worked feature and bug-fix
  examples of the workflow, including Intent Alignment before requirement work.
- `Pi_Integration_Plan.md` - plan for the Pi (pi.dev) adapter under
  `template/.pi/`.
- `WAEGIS_Wizard_Implementation_Plan.md` - exhaustive, task-by-task
  implementation plan for the WAEGIS guided configuration and deployment
  wizard (`waegis new` / `waegis adopt` plus `analyze`/`doctor`/`upgrade`),
  written for execution with Claude Code.
- OpenCode adapter behavior is documented in the stack architecture and the
  copied template assets under `template/.opencode/` and `template/opencode.json`.
- Qwen Code adapter behavior is documented in the stack architecture and the
  copied template assets under `template/.qwen/` and `template/QWEN.md`.
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
- `Full_Workflow_Demo.mp4` - screen recording walking through a full workflow run.
