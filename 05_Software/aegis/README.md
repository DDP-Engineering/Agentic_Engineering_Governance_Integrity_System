<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 0.8.0

AEGIS is an advisory governance workflow for agent-driven software development.
It keeps requirements, specifications, task journals, and component knowledge
as plain files in the target repository. The workflow is intentionally
non-blocking: agents read the instructions, record their work, and use the
heuristic check to find issues that need correction.

## Install

Copy `template/.agentic/` into the target repository, then run:

```bash
python .agentic/aegis.py init
```

`init` creates missing data folders, a default `aegis.toml` when absent, and
managed guidance blocks in `AGENTS.md`, `CLAUDE.md`, and `QWEN.md`. It also
reports Git availability. When Git is installed but the target is not yet a
repository, `init --git` creates one explicitly.

## Use

```text
using aegis workflow, implement feature X
```

The stages are frame, specify, design, build, validate, and deliver. Small
changes may follow the quick path: frame, build, validate, deliver.

During build, record the repository immediately after the expected red test
and compare it again after implementation:

```text
python .agentic/aegis.py anchor --task TASK-<id>
python .agentic/aegis.py evolution --task TASK-<id>
```

These commands are advisory. They record added, modified, and removed
Git-visible files without blocking development or claiming tamper-proof
evidence. Git-ignored files and generated Python bytecode caches are excluded.

Two commands read the register back rather than adding to it:

```text
python .agentic/aegis.py diagram --out docs/coverage.mmd
python .agentic/aegis.py explain src/some/file.py
```

`diagram` draws every requirement as a Mermaid flowchart coloured by how the
behavior is verified; `explain` names the requirements and journals that
already govern a path. Both read only files already in the repository.

See `template/.agentic/CLI.md` for the complete command contract.

## Documentation layout

In `.agentic/aegis.toml`, set optional `[layout] docs` globs for project
documentation, such as `docs = ["docs/", "README.md", "CHANGELOG.md"]`.
Declared documentation no longer produces `outside-layout` warnings, while
remaining in secret scanning. It does not count as source or test coverage
and does not change stage write zones. Overlapping source/tests globs retain
their existing checks; an omitted or empty docs list preserves prior behavior.

## Compact stage reporting

```text
python .agentic/aegis.py summary TASK-<id>
```

The agent records one fixed report at stage completion or pause, then copies
this read-only command's output into chat before detailed explanation.
Reported stage/result and current journal stage are separate. Missing evidence
stays `not recorded`; stale or shortened records require journal review.
No new approval stops, dependencies, or model calls are introduced.

For local models with limited context, start with the summary, current stage
instructions, checklist, and relevant log/evidence rather than loading the
whole register. Required full validation and delivery reads still apply.
The payload's prompt cheatsheet includes explicit one-stage sessions; actual
model compliance and 64K-context performance require separate model runs.
See `template/.agentic/CLI.md` for the optional journal record and output limits.

## Development

```bash
python -m pytest -q tests
python template/.agentic/aegis.py --help
```

## License

PolyForm Noncommercial 1.0.0. See `template/.agentic/LICENSE.txt`.
