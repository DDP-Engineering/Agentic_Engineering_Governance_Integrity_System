<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Adapter and Context Conformance

## One Workflow Contract

Codex, Claude Code, Pi, OpenCode, Qwen Code, and direct CLI users route into
the copied AEGIS payload. `AGENTS.md` owns the bootstrap boundary, the shared
`.agentic/skills/` directories own stage procedures, and the CLI owns command
and execution semantics. Host adapters only bind host skills, prompt commands,
and tool events to those sources.

The canonical fresh-session sequence is:

```text
AGENTS.md
-> aegis run context --json
-> only the named recovery command (stage prepare only when named)
-> only the named required_reads
-> the current stage's human approval boundary
```

`run context` is intentionally small: it names the selected router and
reference, current primary form, and at most the retained immediately preceding
form. It excludes evidence history, full configuration, requirements, reports,
`graph.json`, and `journal.jsonl`. Recovery and metadata documentation remain
available for diagnosis, but they are outside the ordinary forward context
pack. `run context` validates the workflow configuration before it responds.
`config validate` is the explicit confirmation after a configuration repair;
`config show` is policy diagnosis only. Neither belongs in the fresh-session
sequence. The copied `ADAPTER_CONFORMANCE.md` inventories every supported host
entry point and its payload-owned source.

## Compatibility Policy

Host adapters must not reimplement stage lists, completion conditions, quick
rules, CLI fallback logic, or another bootstrap sequence. Each same-named host
skill delegates to its same-named payload skill. Pi reuses `.agentic/skills`
directly through its package manifest. Adapter tests cover every mapped
Markdown entry point and wrapper, reject local configuration bootstrap,
references to all stage modules at once, and ordinary-recovery instructions to
read internal graph or journal files.

The canonical completion contract is declared in the CLI package. Generated
form checklists and stage-reference `Done when` lists are tested projections of
that contract; hosts never provide an alternate checklist.

## Context and Execution Outcomes

The deterministic bootstrap budget remains at most 4 KiB for public `run
context --json` output and at most 30 KiB for the complete UTF-8 bootstrap
pack. Historical evidence does not enlarge the response. Model-token telemetry
is an operational measurement rather than an adapter-specific instruction.

New quick runs register their run-local checks before source changes and retain
real red-before-green evidence. Explicit `check run`, `verify gates`, and
impact execution requests that launch zero commands return non-zero
`nothing-ran` results with an execution status, count, and reason. Disabled
gates in aggregate `verify run` remain `not-enforced`. `verify impact --run`
uses a shell-free argv prefix only for safe, complete impacted selectors and
otherwise records and executes the full-test fallback.
