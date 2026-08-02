<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Planning

Planning notes, requirements, architecture sketches, and future workflow design
records for the standalone AEGIS project belong here.

- `Agentic_Development_Architecture/` - the AEGIS 2.1/WAEGIS 1.2 stack:
  eight-stage file-first lifecycle (plus the proportional `--quick` profile for
  small `fix`/`change` runs), schema 3, design approval, per-step waivers,
  check evidence, deterministic verification, deployment boundary, and
  optional RepoWise 0.37.0 discovery sidecar.
- `Agentic_Development_Architecture_Examples/` - worked feature, bug-fix, and
  existing-repository adoption examples using prepare/apply/close.
- `AEGIS_LIGHT_PLAN/` - the design record for the lightweight, heuristic,
  agent-oriented AEGIS: workflow defined in `AGENTS.md` plus per-stage step
  files instead of hooks and blocking gates, five condensed stages with a
  quick path, one-file artifacts (requirement TOML, task journals) with git
  as the state and collaboration layer, an advisory single-file companion
  CLI (`aegis check` never blocks; `--strict` is CI-only), and explicit
  context budgets for small local models (32k+). No backward compatibility
  with the 2.x payload. **Built and hardened**: the product lives at
  `05_Software/aegis-light/` (0.1.0, phases P1-P5 done; the pilot is the
  remaining phase) with user documentation at `06_SoftwareDocu/AEGIS-Light/`.
  Where the plan and the payload disagree, the payload is authoritative.
- `WAEGIS_V2_PLAN/` - the proposed WAEGIS "lite" rewrite: a git-as-transaction
  safety model replacing the current transaction/journal machinery, a
  harvested-module architecture budgeted under 5,000 lines, and the
  consequence-style interview question catalog (already applied to the
  current WAEGIS 1.2 interview; the plan is the starting point for a
  from-scratch V2 tree, not yet started).
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
- The operator prompt cheat sheet for the eight-stage workflow and optional
  adoption discovery ships downstream at
  `05_Software/aegis/template/.agentic/documents/PROMPT_CHEATSHEET.md`; no
  separate planning-side copy is kept here.

Superseded planning documents (the AEGIS hard-break modernization plan, the
requirement-snapshot traceability plan, the worktree-local run-state plan,
and the policy-neutral configuration plan, all dated 2026-07-22) have been
removed after their work completed; the resulting behavior is what
`Agentic_Development_Architecture/` and the source-local module documentation
describe today.
