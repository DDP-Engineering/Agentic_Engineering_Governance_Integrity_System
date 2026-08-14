<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 0.4.0

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
managed guidance blocks in `AGENTS.md`, `CLAUDE.md`, and `QWEN.md`.

## Use

```text
using aegis workflow, implement feature X
```

The stages are frame, specify, design, build, validate, and deliver. Small
changes may follow the quick path: frame, build, validate, deliver.

## Development

```bash
python -m pytest -q tests
python template/.agentic/aegis.py --help
```

## License

PolyForm Noncommercial 1.0.0. See `template/.agentic/LICENSE.txt`.
