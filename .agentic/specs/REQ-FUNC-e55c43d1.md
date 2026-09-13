<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-e55c43d1 - Render a deterministic bounded task brief

## Behavior

`brief TASK-<id>` renders a richer resume view than `summary` using only the
workspace configuration, durable task journals and context-file presence. It writes nothing and does
not call Git, subprocesses, configured commands, a model, or the network.
Repeated runs against unchanged files are byte-identical.

The fixed section order is `AEGIS brief`, Task, Stage, Branch/base, Parent,
Requirements, Context, Checklist, Stage report, Interaction, Review, Active rulings, Handoff,
Visible children, Details. Legacy omissions render as `not recorded`,
`none recorded`, or `none visible`; approval and success are never inferred.
Stale stage-report or handoff bindings are explicitly marked.

Context lists `.agentic/context/project.md` and `.agentic/context/environment.md`
with `present` or `not recorded`. This is a bounded presence-only route to
project-owned files; callers read their bodies separately and verify relevant
claims against the checkout. Missing files remain compatible with brief.

## Data / interface

```python
BRIEF_VALUE_LIMIT = 240
BRIEF_RULING_LIMIT = 8
BRIEF_CHILD_LIMIT = 20

def brief_lines(path: Path, journal: dict, text: str, cfg: dict) -> list[str]: ...
def cmd_brief(args: argparse.Namespace) -> int: ...
```

Scalar values use the same printable control-character and whitespace
normalization as `summary` and are limited to 240 characters. At most eight
active rulings retain journal order and at most twenty visible children use
task-ID order. Every truncated collection ends with
`...[N omitted; read journal]`. No wall-clock or live Git value is emitted.
Unknown tasks produce one bounded error line and a nonzero exit.

## Acceptance

- A representative exact-output snapshot has the required fixed order.
- Two unchanged invocations produce identical bytes and no writes or command
  execution.
- All scalar and collection bounds visibly report omissions.
- `summary`, status text, and status JSON retain their existing contracts.
