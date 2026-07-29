---
name: agentic-development
description: File-first AEGIS workflow for features, fixes, and changes across intake, alignment, requirement, design, check, implementation, validation, and delivery.
---

<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Agentic Development

Use AEGIS as an eight-stage, file-first lifecycle:

`intake → alignment → requirement → design → check → implementation → validation → delivery`

The human approves every transition. Host plan mode may support discussion but
does not replace the imported design or `stage close` approval journal.

## Bootstrap

1. Run `<workflow> config validate --json`.
2. Run `<workflow> config show --json`.
3. Start or resume:

   ```text
   <workflow> run start <feature|fix|change>
   <workflow> run resume
   ```

4. Open the returned artifact. Do not encode statements, paths, decisions, or
   evidence in CLI flags.

## Stage Lifecycle

For every stage:

```text
<workflow> stage prepare
# edit the generated TOML/Markdown
<workflow> stage apply
# show the imported state and request explicit human approval
<workflow> stage close
```

Use `stage add` for another atomic requirement or check. `stage apply` imports
the complete collection only after every file validates. Access changes and
human-approved earlier routing belong in the generated control section.

Load only the current reference:

| Stage | Reference |
| --- | --- |
| intake | `reference/intake.md` |
| alignment | `reference/alignment.md` |
| requirement | `reference/requirement.md` |
| design | `reference/design.md` |
| check | `reference/check.md` |
| implementation | `reference/implementation.md` |
| validation | `reference/validation.md` |
| delivery | `$agentic-delivery` |

## Non-Negotiable Rules

- Requirements define observable contracts; design owns internal structures,
  boundaries, algorithms, compatibility choices, and implementation sequence.
- A fix needs a reproducing red check before implementation.
- Record red and green check evidence through the configured external or managed
  path. Never invent IDs; AEGIS generates them.
- Do not edit check artifacts during implementation. Route back through a stage
  control form when the contract or check is wrong.
- Run deterministic verification before interpretive diff review.
- `stage close` at delivery completes AEGIS state only. It does not push,
  publish, merge, or create a pull request.

## Stop Format

```text
Stage: <stage>
Artifact: <path>
Imported revision: <number>
Evidence: <ids and results>
Blockers: <none or exact blockers>
Needs human: approve close, revise artifact, route earlier, or abort
Next command: <exact command>
```
