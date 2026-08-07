<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# QWEN.md

Qwen Code should treat `AGENTS.md` as the authoritative workflow contract for
this repository. Read `AGENTS.md` first, then use this file only as the Qwen Code
adapter note.

If this file and `AGENTS.md` disagree, follow `AGENTS.md`.

For a fresh stage session, use only the payload-owned route: `AGENTS.md`,
`aegis run context --json`, its named recovery command (`stage prepare` only
when named), and its `required_reads`. Do not load all stage references or read
`graph.json`/`journal.jsonl` for ordinary recovery. `run context` validates the
workflow before it responds; use `config validate` after a configuration repair
and `config show` only for explicit policy diagnosis. Obey both AEGIS policy and
Qwen Code host safety controls.

Shared workflow skills are model-invoked and also available from the `/skills`
picker (for example `agentic-development`). Existing Codex-style references such
as `$documentation-audit` mean the matching Qwen Code skill under `.qwen/skills/`,
for example the `documentation-audit` skill.

Project-local settings, skills, and commands under `.qwen/` load only after the
workspace is trusted; see `.qwen/README.md`.
