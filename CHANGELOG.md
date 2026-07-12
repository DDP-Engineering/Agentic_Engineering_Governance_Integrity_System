<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Scaffold the WAEGIS guided wizard as a new stdlib-only package under
  `05_Software/waegis/` (task T0.1): `pyproject.toml` (name `waegis`, version
  0.1.0, no runtime deps, `waegis` script, pytest config), the §12 module
  skeleton with compliant headers, `version.py` carrying the wizard version and
  the compatible AEGIS payload range `>=0.4.0,<1.0` (AD-11), a `waegis` CLI
  whose planned subcommands (`new`, `adopt`, `analyze`, `doctor`, `upgrade`,
  `version`, `self-update`, `gui`) are stubs that exit 2 "not implemented", a
  README stub, and smoke/version tests. WAEGIS is never copied into the AEGIS
  payload.
- Amend the root `AGENTS.md` repository and validation rules to name both the
  `05_Software/aegis/` and `05_Software/waegis/` packages, and update the root
  `README.md` layout and pointers to mention WAEGIS.
- Add `00_Planning/WAEGIS_Wizard_Implementation_Plan.md`, the task-by-task
  implementation plan for the WAEGIS guided configuration and deployment
  wizard (new-project and existing-project journeys, install manifest,
  `analyze`/`doctor`/`upgrade` lifecycle, self-contained packaging).
- Add first-class Intent Alignment support with an `alignment` CLI command,
  `[alignment]` workflow policy defaults, independent standard/adoption stages,
  graph and journal persistence, status/report visibility, and shared
  development/adoption skill instructions.
- Add a Qwen Code adapter under `template/.qwen/` with `settings.json` (native
  `PreToolUse`/`PostToolUse` command hooks mapping to the shared `.agentic/hooks/`
  guards, `context.fileName` pointing at `AGENTS.md`, and secret/delivery permission
  denies), thin skill wrappers, `/workflow-*` command prompts, a README, and a
  `template/QWEN.md` adapter note.
- Add Qwen Code adapter parity tests and a `guard_write_zone` case for Qwen's
  `WriteFile` tool name.
- Add an OpenCode `aegis` primary agent and make it the project
  default agent so OpenCode loads the shared workflow discipline before
  behavior-changing work.
- Add a Python `dev` dependency group for `pytest` and `ruff` so validation
  tooling is managed by the project instead of global installs.

### Changed

- Rebrand the project as **AEGIS** (Agentic Engineering Governance & Integrity
  System), forked from the `2026_AgenticDevelopmentWorkflowTemplate` codebase
  (history not carried over). The CLI command, Python package, and console
  entry point are now `aegis` (was `agentic-workflow` / `agentic_workflow`);
  the dev package directory is `05_Software/aegis/`. This is a breaking
  CLI-contract rename.
- Renumber the top-level repository layout to reserve `03_Hardware/` and
  `04_HardwareDocu/`: `04_Software/` -> `05_Software/` and
  `05_SoftwareDocu/` -> `06_SoftwareDocu/`. `02_Tools/create_project_from_template.py`
  and all documentation were updated to the new paths.
- Teach the shared `guard_write_zone` hook to recognize Qwen Code's `WriteFile`
  (and raw `write_file`/`replace`) tool names so the write-zone guard applies
  identically across the Codex, Claude Code, Pi, OpenCode, and Qwen Code adapters.
- Route OpenCode workflow command prompts through the `aegis` agent
  and document CLI command usage with `opencode run --command`.

## [0.4.0] - 2026-06-25

### Added

- Add an OpenCode adapter with `opencode.json`, native skill wrappers, command
  prompts, and a local plugin that maps OpenCode tool events to the shared
  `.agentic/hooks/` guard scripts.
- Add OpenCode adapter parity tests and Node unit tests for plugin hook
  decision parsing, protected-read blocking, and tool-event mapping.

## [0.3.0] - 2026-06-23

### Added

- Add existing-project adoption run kind and adoption-specific workflow stages.
- Add component manifest support for adopted component and bundle status.
- Add adoption CLI commands for baseline summaries, local scope checks, and
  component status reporting.
- Add the `agentic-adoption` shared skill plus Codex, Claude Code, and Pi
  adapter documentation for existing-project adoption mode.
- Add a worked planning example for adopting an existing repository without
  application behavior changes.
- Add explicit existing-repository and dry-run options to the template creation
  helper script.
- Add adoption delivery preflight blocking for application source changes unless
  adoption behavior changes are explicitly enabled.
- Validate component manifests in adoption commands, registry checks, and
  delivery preflight so invalid adoption baselines cannot appear clean.

### Changed

- Move workflow-owned component documentation defaults from `06_SoftwareDocu/`
  to `.agentic/knowledge/components/`.
- Sync the delivered and planning prompt cheatsheets with adoption-mode prompts.
- Refresh planning artifact-flow diagrams to show adoption artifacts, component
  maps, local scope checks, and `.agentic/knowledge/` documentation.
- Document existing-repository adoption usage for the template creation helper.
- Update the root README with adoption artifacts, worked examples, and
  existing-repository scaffold usage.

## [0.2.0] - 2026-06-21

### Added

- Add a Pi (pi.dev) adapter under `template/.pi/` as a third agent adapter
  alongside `.codex/` and `.claude/`. A TypeScript bridge extension maps Pi
  tool events onto the shared `.agentic/hooks/` guard scripts (reused
  byte-for-byte), and the Pi package manifest reuses `.agentic/skills/` through
  `pi.skills` with no skill duplication. Includes vitest specs and Python
  parity tests.

### Changed

- Relicense the project from AGPL-3.0 + Non-Commercial to the PolyForm
  Noncommercial License 1.0.0 (SPDX `LicenseRef-PolyForm-Noncommercial-1.0.0`).
  Replace `LICENSE.txt`, remove the now-redundant `LICENSE_NC.txt`, and update
  the legal headers across sources, documents, and configs. Commercial use
  requires a separate commercial license from DDP Engineering.
- Relocate the operator references (`PROMPT_CHEATSHEET.md`,
  `CLI_API_REFERENCE.md`, `How_To_Start_A_New_Project.md`,
  `WORKFLOW_CHEATSHEET.svg`) from the template root into `.agentic/documents/`.
- Exclude the `.pi/` adapter's install-on-demand `node_modules/` from the
  template scaffolder.
- Document Pi as the third adapter across the stack architecture and worked
  examples, and add versioning/changelog rules to the root `AGENTS.md`.

### Removed

- Remove the `.agentic/specs/` directory; run spec items are recorded in the
  run `graph.json`.

### Fixed

- Point the template hygiene tests (`test_scaffold`,
  `test_documentation_workflow`) at the relocated `.agentic/documents/`
  cheatsheet paths.

## [0.1.0] - 2026-06-17

### Added

- Bootstrap standalone `aegis` project structure.
- Add copyable AEGIS payload with `.agentic/` CLI, tools, hooks,
  requirements, policy, and workflow configuration.
- Add Codex adapter under `.codex/` with bundled workflow skills and hook
  bindings.
- Add Claude Code adapter under `.claude/` plus `CLAUDE.md`, using thin skill
  wrappers that reference the shared workflow instructions.
- Add component documentation convention under `06_SoftwareDocu/`, including
  template, documentation audit, and write-component-documentation support.
- Add requirement traceability, coverage, impact, invariant, delivery preflight,
  and report support in the Python CLI.
- Add repository scaffold helper under `02_Tools/`.
- Add planning architecture documents, worked examples, delivery prompt cheat
  sheet, and visual workflow cheat sheet SVG.
- Add DDP Engineering AGPL-3.0 plus Non-Commercial license files and legal
  headers.
