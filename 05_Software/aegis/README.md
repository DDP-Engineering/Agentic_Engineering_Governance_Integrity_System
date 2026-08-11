<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS package

This package develops and tests the exact AEGIS version 1 runtime delivered at
`template/.agentic/aegis/cli/src/aegis/`. There is no second runtime copy.

The central operation registry owns all 48 AEGIS command names, input schemas,
help, examples, availability, and dispatch. Human output and one-line JSON use
the same presentation-neutral result and the version 1
`aegis.machine.response` envelope.

Implemented behavior includes:

- canonical configuration/artifact codecs, safe repository paths, exact
  payload verification, and cohesive recoverable publication;
- multiple durable Runs with one local selected context and eight self-owned
  Stage documents for full and short profiles;
- Stage evidence, findings, dispositions, decisions, exceptions, attachments,
  skips, revisits, scope changes, Delivery, and abandonment;
- current-only Requirements, Specifications, Components, trace validation,
  and impacted-test selection;
- configured shell-free tests, lints, and audits with pass, fail, timeout,
  cancellation, launch-error, large-output, red-fingerprint, and Git integrity
  evidence; and
- bounded Adoption journals and thin shared host-adapter resources for direct
  CLI, Claude Code, Codex, Qwen Code, OpenCode, and Pi use.

Default policy is advisory and non-blocking. Findings never manufacture a pass
and never perform developer-owned outward Git actions.

## Development

```powershell
uv run --group dev python -m pytest -q tests
uv run --group dev ruff check template/.agentic/aegis/cli/src tests
uv run --group dev python -B -m aegis --help
uv run --group dev python -B -m aegis --format json version-show
```

Runtime dependencies are limited to the Python standard library. The package
supports Python 3.11 or later.

## Invocation

Global options precede the flat command:

```text
aegis --repo C:\path\to\installed-project --format json stage-show
aegis --repo C:\path\to\installed-project run-create --input ticket.json
aegis --repo C:\path\to\installed-project execution-run --category tests --name project
```

Structured input files and stdin use `aegis.machine.input` schema version 1.
No operator-producible input or repository state is emitted as a traceback.
