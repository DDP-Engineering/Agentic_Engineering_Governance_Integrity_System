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
- The stakeholder architecture decks (`WAEGIS_Architecture_Presentation.pptx`
  and `AEGIS_Governance_Workflow_Presentation.pptx`) live under
  `06_SoftwareDocu/`.
- `PROMPT_CHEATSHEET.md` - planning reference copy of the operator prompt cheat
  sheet; it leads with a stage-by-stage spine of the prompts a human gives the
  agent to drive one change from intake through delivery. The canonical copy
  ships at `05_Software/aegis/template/.agentic/documents/PROMPT_CHEATSHEET.md`
  and is kept identical to this one.
- `AEGIS_Hard_Break_Modernization_Master_Plan_2026-07-22.md` - coordinated
  execution order and shared acceptance criteria for the requirement, workspace
  state, and policy-neutral configuration hard break.
- `AEGIS_Requirement_Snapshot_Traceability_Plan_2026-07-22.md` - UUIDv4
  requirement records, in-memory traceability, and registry removal plan.
- `AEGIS_Worktree_Local_Run_State_Plan_2026-07-22.md` - per-worktree active-run
  pointer and explicit run selection plan.
- `AEGIS_Policy_Neutral_Configuration_Plan_2026-07-22.md` - strict
  `workflow.toml` policy model and shared CLI/hook/adapter consumption plan.
