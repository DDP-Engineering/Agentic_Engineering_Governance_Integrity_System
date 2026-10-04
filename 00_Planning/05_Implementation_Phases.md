<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 05 - Current implementation

The assigned source version is **AEGIS 0.14.0**. This page describes current
capabilities, source ownership and verification methods. Release history is in
the [changelog](../CHANGELOG.md); dated build evidence is retained under
`07_Delivery/` and implementation evidence in task records.

## Implemented capabilities

| Area | Current behavior |
|---|---|
| Workflow | Six ordinary stages, a quick path for eligible repairs, and a separate component-by-component adoption flow. |
| Interaction | Stage checkpoints by default, optional project-configured autopilot, explicit publication authority, and immediate material deviation notices. |
| Project context | Project-owned `context/project.md` and `context/environment.md`, scaffolded independently by `init` when absent and preserved byte-for-byte when present. |
| Current documentation | Positive actual responsibilities and behavior in project/component documents and active contracts, with proposals in draft/task records and history in journals/Git. |
| Durable artifacts | Frame cards, atomic requirement coverage, task designs, TOML requirements, Markdown specs and knowledge, append-only Log/Rulings, replaceable Handoff/Stage report, and anchor/evolution evidence. |
| Companion CLI | Offline-first standard-library Python scaffolding, component discovery, traceability, configured execution and bounded reporting. |
| Verification | A 21-check advisory catalog, optional strict CI, focused/impacted test selection, dry-run previews, fallback refusal, timeouts, and complete saved evidence with optional compact presentation. |
| Coordination | Presence-only context pointers in `brief`, stage reporting through `summary`, one-level child tasks, independent review verdicts and bounded correction rounds. |
| Integrations | OpenCode, Codex, Pi, Qwen Code and Claude Code entry points backed by eleven shared adapter operations. |
| Host lifecycle | Complete package assembly, runtime discovery, owned installation/update/removal, verification jobs, duplicate prevention, cancellation and recovery. |

## Source ownership

```text
05_Software/aegis/
  template/.agentic/       canonical managed core
    templates/            six generic artifact templates
    steps/                six ordinary stages plus adoption
    aegis.py              Python CLI
  integrations/           five host adapters and shared runtime
    tests/                JavaScript behavior tests
  tests/                  Python product suite and integration wrappers
  README.md               package overview

.agentic/
  context/                this project's current profile and environment
  knowledge/              this project's component orientation
  requirements/           this project's behavior contracts
  tasks/                  this project's progress and evidence

02_Tools/
  build_aegis_release.py  core archive and build-record builder
  build_agent_plugins.mjs complete host-package builder
```

The managed core contains 17 files. Downstream projects own their context,
configuration and records. Update the canonical template and installed mirror
together, then replace only managed files during upgrades. Each missing context
file is scaffolded independently by `init`; existing project data keeps its bytes.
The downstream starter changelog remains empty.

## Project context lifecycle

Read the profile at frame/resume and relevant environment sections before setup,
build or verification. Select component, requirement, source and test references
instead of preloading the repository. Brief lists the two paths with `present`
or `not recorded`; their contents and accuracy require direct review.

Populate confirmed purpose, implementation and setup facts during frame or
adoption. New projects add responsibilities as they are implemented. Build
updates affected facts as changes become real; validate reconciles current
context, component pages and active contracts against the candidate and
authorized intent. Preserve unrelated sections and established requirements.
Missing or partial context is compatible with ordinary work.

Current documents contain one positive description of each actual behavior,
including meaningful error, security and compatibility responses. Draft
requirements/specs hold agreed proposals. Journals, Git and the changelog carry
past decisions and changes. Suspected defects remain task findings pending
clarification rather than becoming assumed active contracts.

## Verification methods and evidence

Use repository `AGENTS.md` for the validation obligations and
`.agentic/aegis.toml` for canonical commands and layout. The product suite covers
isolated CLI/scaffolding behavior, context preservation and optional brief
pointers, traceability, configured execution, packaging and host integration
behavior. Focused tests precede the full product suite for executable changes.

Host verification has separate scopes:

- Package checks inspect resources, runtime discovery and owned lifecycle.
- Backend checks inspect native registration, tool discovery and protocol calls.
- Desktop acceptance inspects the visible resources in the selected environment.
- Model-led acceptance exercises the workflow and independent reviews with the
  user's authorized provider and chosen model.

A result supports only its recorded candidate and environment. Package/backend
checks alone establish neither Desktop nor model-led acceptance. Small-context
operation is supported by selective reading and compact records; model compliance
requires its own measured evaluation. Consult [agent package guidance](../06_SoftwareDocu/Agent_Plugins.md)
for verification routes and links to recorded evidence.

## Builders and distribution

| Builder | Output |
|---|---|
| `python 02_Tools/build_aegis_release.py --version <x.y.z>` | Core Windows/Linux archives, checksums and build records under `07_Delivery/aegis-<version>/`, with matching source/changelog version. |
| `node 02_Tools/build_agent_plugins.mjs --output <fresh-output-directory>` | Five complete host-package directories, including shared libraries and launchers, using the existing core version. |

Distribute a complete assembled directory or an archive of it. Each recipient
installs into their own host profile and authenticates independently. Source
version assignment, local package construction, host installation and external
publication have separate outcomes and authority.

## Maintenance

1. Keep managed templates generic and project facts in project-owned files.
2. Preserve the assigned version unless a version change is requested.
3. Update current planning, user guides and affected generated companions with
   workflow, command, configuration or artifact changes.
4. Use behavior tests for executable changes and direct semantic/link/layout
   review for documentation-only changes.
5. Keep documentation-only maintenance and release operations outside AEGIS
   task governance.
6. Preserve the user's dirty work and require applicable authority for Git and
   external actions.
7. Keep dated verification evidence in task/build records and current guidance
   in these documents.
