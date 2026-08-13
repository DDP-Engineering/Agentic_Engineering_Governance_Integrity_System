<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS command runtime

This standard-library-only package supplies the repository-local AEGIS command
protocol. It supports Python 3.12.

Use the flat help and version commands through the package or installed script:

```text
python -m aegis help-show
python -m aegis help-show --operation run.create
python -m aegis version-show
python -m aegis --format json version-show
```

Human output is the default. `--format json` emits one compact version 1 machine
response followed by LF. Operations declared by the catalog but unavailable in
the installed runtime return a structured `capability_unavailable` response
after their registry-declared inputs validate. Malformed inputs return
structured `invalid_input`; they are not discarded. Exact-operation help is
also registry-owned and includes purpose, required and optional arguments,
result, and one minimal example.

The runtime does not launch project tests, lints, audits, or other configured
commands. `execution-list` returns read-only argument-array and working-directory
guidance; callers execute through normal host tooling and record the observed
outcome through `evidence-add`.

`run-create` defaults `interaction_mode` to `checkpoint`. A `continuous` Run
also requires a non-empty `execution_instruction`, which is stored in `run.md`;
the runtime never infers delegation from arbitrary prose. After an included
Stage handoff, machine and human output expose `data.checkpoint` with the Stage
summary and Continue, Review, Revise, and Park choices. Delivery substitutes
Approve and close. Review and Park do not mutate workflow state, while Continue
and Revise route through the existing Stage operations. Agent-recorded Delivery
approval uses `approval_source = "continuous_delegation"` only for a continuous
Run; a checkpoint approval records `developer` after the developer chooses it.

AEGIS discovers an installation by walking upward to a Git worktree containing
`.agentic/config.toml`. It does not consult user-home configuration or cross a
nested Git worktree boundary. An explicit global `--repo <path>` is always
validated. Without `--repo`, package-level help and version remain available
before a project installation exists.
