<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Adapter Conformance

Every host is a thin route to the same project-local AEGIS payload. Host
configuration may translate host events to payload hooks, but it must not add
stage rules, command semantics, or a second recovery procedure.

## Canonical Bootstrap

For a fresh stage session, every host follows one sequence:

```text
AGENTS.md
-> <workflow> run context --json
-> only the named recovery command (stage prepare only when named)
-> only the named required_reads
-> the current stage's human approval boundary
```

`run context` supplies one router, one current-stage reference, the current
primary form, and at most the retained preceding form. Do not inject all stage
references. Do not read `graph.json` or `journal.jsonl` for ordinary recovery;
use the recovery command named by `run context`. The CLI API reference and
metadata guide remain discoverable diagnostic material outside this forward
context pack.

## Entry-Point Map

| Consumer | Host entry points | Payload-owned source |
| --- | --- | --- |
| Direct CLI | `.agentic/tools/run.ps1`, `.agentic/tools/run.sh` | `AGENTS.md`, this document, and `CLI_API_REFERENCE.md` |
| Codex | `.codex/config.toml`, `.codex/hooks.json`, and `.codex/skills/<name>/SKILL.md` | `.agentic/hooks/` and `.agentic/skills/<name>/SKILL.md` |
| Claude Code | `CLAUDE.md`, `.claude/settings.json`, and `.claude/skills/<name>/SKILL.md` | `AGENTS.md`, `.agentic/hooks/`, and `.agentic/skills/<name>/SKILL.md` |
| Pi | `.pi/package.json`, `.pi/settings.json`, and `.pi/extensions/agentic-guard/` | `AGENTS.md`, `.agentic/hooks/`, and the `pi.skills` path `../.agentic/skills` |
| OpenCode | `opencode.json`, `.opencode/agents/aegis.md`, `.opencode/commands/`, `.opencode/plugins/`, and `.opencode/skills/<name>/SKILL.md` | `AGENTS.md`, `.agentic/tools/run_aegis.py`, `.agentic/hooks/`, and `.agentic/skills/<name>/SKILL.md` |
| Qwen Code | `QWEN.md`, `.qwen/settings.json`, `.qwen/commands/`, and `.qwen/skills/<name>/SKILL.md` | `AGENTS.md`, `.agentic/tools/run_aegis.py`, `.agentic/hooks/`, and `.agentic/skills/<name>/SKILL.md` |

`<name>` is one of `agentic-adoption`, `agentic-development`,
`agentic-delivery`, `regression-traceability`, `documentation-audit`,
`python-codestyle-audit`, or `write-component-documentation`. The corresponding
payload skill is the sole procedure for that name.

## Public Execution Outcomes

All hosts surface the same CLI contracts. New quick runs create and register
their run-local checks before source changes, then retain truthful red and
green evidence. Explicit managed-check and gate requests that launch no
command are non-zero `nothing-ran` outcomes; aggregate `verify run` continues
to report disabled gates as `not-enforced`. `verify impact --run` uses the
configured argv prefix only when impact coverage is safe and complete;
otherwise it runs the configured full-test fallback.
