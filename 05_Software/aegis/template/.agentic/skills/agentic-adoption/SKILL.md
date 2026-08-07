---
name: agentic-adoption
description: File-first AEGIS adoption workflow for repository discovery, component mapping, baseline establishment, and safe handoff without application behavior changes.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Adoption

Adoption uses the same file-first lifecycle as standard work:

```text
<workflow> config validate --json
<workflow> config show --json
<workflow> run start adoption
<workflow> run resume
<workflow> stage prepare
<workflow> stage apply
<workflow> stage close
```

Open and edit the returned artifact. Do not put scope, access, routing, or
decisions in flags. The human explicitly approves every `stage close`.

## Fresh Stage Sessions

Read `AGENTS.md`, run `<workflow> run context --json`, then read only its
`required_reads`: named skill, reference, current form, and retained previous
form. If
`unavailable_current_artifact` is present, run only its recovery command;
never prepare an already applied stage. Do not recover ordinary adoption work
by reading `graph.json` or `journal.jsonl`; use `run
status` only for detailed diagnosis.

The required order is:

`adoption-intake → adoption-alignment → repo-discovery → component-map → component-adoption → baseline-review → adoption-delivery`

Load only the reference for the current stage:

| Stage | Reference |
| --- | --- |
| adoption-intake | `reference/adoption-intake.md` |
| adoption-alignment | `reference/adoption-alignment.md` |
| repo-discovery | `reference/repo-discovery.md` |
| component-map | `reference/component-map.md` |
| component-adoption | `reference/component-adoption.md` |
| baseline-review | `reference/baseline-review.md` |
| adoption-delivery | `reference/adoption-delivery.md` |

Ground rules:

- Adoption may update workflow configuration, maps, requirements,
  documentation, test inventory, and baseline records.
- It must not change runtime product behavior. Start a standard AEGIS run when
  behavior changes are needed.
- Prefer one component. Use a named bundle only with explicit approval and a
  rationale captured in the form.
- Establish local scope before change: component paths, tests, documentation,
  requirements, ownership, and risks must be explicit.
- Keep discovered behavior separate from desired behavior.
- Stop for map approval and for unclear scope, ownership, or risk.
- Use `<workflow> adoption component-status`, `scope-check`, and `baseline` for
  read-only inspection after a run is selected. `scope-check` reports
  `enforcement` beside its issues; `not-enforced` means only its advisory
  findings apply.
- Record discovered behavior as requirements with `<workflow> stage add` at the
  `component-adoption` stage. That stage is the only place an adoption run can
  create them.
- Route earlier and request access changes only through the stage control form.

At each stop, report the stage, artifact, imported revision, component scope,
behavior-change check, baseline status, blockers, and exact next command.
