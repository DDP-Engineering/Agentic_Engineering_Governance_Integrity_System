<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Configuring AEGIS

Every policy decision AEGIS enforces lives in one human-editable file:
`.agentic/workflow.toml`. Nothing here is a one-time install-time choice —
you can change any of it at any point, and the next run picks up the new
policy. This note walks through the decisions you actually have to make,
grouped by what they're for, rather than listing every field mechanically.

Inspect the current effective policy at any time:

```text
<workflow> config validate --json
<workflow> config show --json
```

`config validate` confirms the file is a well-formed, complete schema-3
document; `config show` prints the normalized policy actually in effect.

## The shipped defaults are deliberately open

A freshly installed workspace ships **unrestricted or disabled** on every
policy that can be turned off: no gate runs, no guardrail blocks anything,
alignment is on but unprotected. This is a deliberate choice — AEGIS does not
assume it knows your repository's risk profile better than you do. Every
restriction below is something you opt into, not something you opt out of.

## How work happens: the interface

```toml
[interface]
stage_form_retention = "latest"
check_execution = "external"
```

**`stage_form_retention`** controls what happens to a stage's *transient*
input forms after they're used — not the durable record (design, requirement
snapshots, graph state, evidence, journals, validation summaries, and
delivery reports are always kept regardless of this setting).

| Value | What happens |
| --- | --- |
| `discard` | The prepared form is deleted once no longer needed. Lowest disk footprint; nothing to review after the fact beyond the durable record. |
| `latest` (default) | The most recently prepared form stays in place, overwritten by the next `prepare`. This supports a fresh-session handoff without retaining superseded revisions. |
| `versioned` | Every closed revision is kept under the stage's `revisions/` folder. Choose this if you want a full paper trail of every draft, not just the final durable state. |

A retention change only affects the *next* prepared revision — it never
rewrites something already on disk.

**`check_execution`** decides who runs your check commands: `external`
(default) means you or your agent runs them and records the result through
`check prepare` / `check record`; `managed` means AEGIS runs the imported
commands itself via `check run`. Pick `managed` if you want one less manual
step and trust AEGIS's sandboxing of the command; pick `external` if your
checks need an environment, credentials, or a tool AEGIS shouldn't be
executing directly.

## The five quality gates

```toml
[gates.build]
mode = "disabled"
commands = []
# ...typecheck, lint, test, security follow the same shape
```

Each of the five gates is independent, with the same two-value mode:
`disabled` (default) or `enforce`. There is no in-between "advisory" gate —
either it runs and its failure blocks validation, or it doesn't run at all.
An enforced gate needs at least one explicit command; a disabled gate may
still keep its commands recorded for when you decide to turn it on later. All
five, when enforced, always run in the same fixed order during `verify run`:
build, typecheck, lint, test, security — every enabled one runs even if an
earlier one already failed, so you see the complete picture in one pass
rather than fixing issues one at a time across repeated runs.

The security gate deserves a specific caution: its result is evidence from
whatever tool you configured, not a general claim that the change is secure.
Configure a real tool (a dependency scanner, a static analyzer) rather than a
placeholder command — an empty or fake command undermines the entire point of
enforcing it.

Each gate group also accepts an optional `timeout` (seconds, applied per
command in that group):

```toml
[gates.test]
mode = "enforce"
commands = ["pytest -q"]
timeout = 2400
```

Omitted, it defaults to 1800 seconds (30 minutes). Raise it for a genuinely
slow suite rather than letting AEGIS report a false `fail` for a command that
was still running — the recorded evidence for a timed-out command is
indistinguishable from a real failure unless you already know to expect it,
so a too-short timeout on a slow gate quietly produces misleading history.

A reasonable adoption order: turn on `test` first (you likely already run
tests), then `build` and `typecheck` if your language has them, then `lint`,
and only add `security` once you've picked a real tool for it.

## Guardrails

Guardrails are narrower than gates — each protects one specific kind of
mistake rather than running a whole tool. Read their mode values carefully:
they are **not** all the same tri-state. Some are a strict on/off; only one
(`scope`) has a middle "advisory" setting.

| Guardrail | Modes | What it protects against |
| --- | --- | --- |
| `guardrails.secrets` | `disabled` / `enforce` | Configured regex patterns matching likely credentials or private keys in changed content. |
| `guardrails.protected_paths` | `disabled` / `enforce` | Specific paths and operations (e.g. "never delete", "never write") you've marked off-limits. |
| `guardrails.working_tree` | `unrestricted` / `restricted` | Paths that must not change at all while a restriction is active — useful for protecting generated files or vendored code from accidental edits. |
| `guardrails.write_access` | `unrestricted` / `stage_restricted` | Which paths each individual stage is allowed to write to. `stage_restricted` requires an explicit `[guardrails.write_access.stages]` table naming every stage's allowed globs — there is no partial configuration. |
| `guardrails.scope` | `unrestricted` / `advisory` / `enforce` | Whether a run's changes stay inside its declared allowed roots. `advisory` warns without blocking; `enforce` blocks. This is the one guardrail with a genuine middle ground. |
| `guardrails.delivery` | `disabled` / `enforce` | Specific command patterns that require delivery-stage control before they can run. |

Each `enforce`-or-equivalent mode requires the guardrail's actual rule data
(patterns, roots, or the stage table) to be non-empty — you cannot enforce a
guardrail with nothing configured for it to check.

## Alignment

```toml
[alignment]
enabled = true
pause_on_open_questions = true
risk_threshold = "medium"
allow_recommended_responses = true

[alignment.protected_scope]
mode = "disabled"
patterns = []
```

Alignment is on by default for full runs (quick runs never reach it — see
the note on quick runs and bypassing AEGIS). `risk_threshold` is `low`,
`medium`, or `high`: it's the minimum assessed risk level at which
alignment's controls actually engage, so a genuinely low-risk change doesn't
get held up by process built for riskier ones. `pause_on_open_questions`
determines whether an unresolved question in the alignment form actually
stops the stage from closing, or is just recorded. `protected_scope` is a
narrower guardrail inside alignment specifically: `enforce` mode with
patterns blocks a run from touching paths you've marked as needing extra
scrutiny before alignment can close.

## Traceability and coverage

```toml
[traceability]
language = "python"
source_extensions = [".py"]
test_file_patterns = ["test_*.py", "*_test.py"]

[traceability.coverage]
mode = "disabled"
coverable_roots = []
exclude = []
```

`language` drives which file-naming conventions AEGIS uses to connect source
files to their tests. `traceability.coverage.mode` is `disabled` or
`enforce`: enforced, AEGIS checks that source under `coverable_roots` (minus
anything in `exclude`) actually has linked test coverage per your
requirements, not just that tests exist somewhere.

## Component baseline guard and adoption

```toml
[components.baseline_guard]
mode = "disabled"

[adoption]
allow_component_bundles = true
max_bundle_components = 5

[adoption.source_changes]
mode = "unrestricted"
```

`components.baseline_guard.mode` (`disabled` / `enforce`) governs whether
work is blocked on a component whose adoption status hasn't reached a usable
baseline yet — enforce this once your component map is mature enough that
"not yet baselined" should actually stop work rather than just being visible.
`adoption.source_changes.mode` (`unrestricted` / `blocked`) is specifically
about adoption runs: `blocked` prevents adoption work itself from touching
application source, keeping adoption strictly about discovery and
documentation until you're ready to let it change code too.

## Quick-run proportionality

```toml
[quick.changed_paths]
mode = "advise"
max_paths = 10
```

This table is commented out in the shipped starter file — omission is
equivalent to `mode = "disabled"` with `max_paths = 10`. Modes are `disabled`
and `advise` only; there is no `enforce` here by design, since this is meant
as a nudge toward starting a full run, not a hard block. See the note on
quick runs and bypassing AEGIS for what the advisory actually does.

## Repository locations

```toml
[source]
roots = ["src", "app", "lib"]

[tests]
roots = ["tests", "test"]

[requirements]
roots = [".agentic/requirements"]

[documentation]
roots = [".agentic/knowledge/components"]
component_template = ".agentic/knowledge/components/component_template.md"

[components]
manifest = ".agentic/components.toml"

[knowledge]
roots = [".agentic/knowledge"]

[reports]
adoption_root = ".agentic/reports/adoption"
```

These are the paths AEGIS actually looks in for your source, your tests, and
its own durable records. Get `source.roots` and `tests.roots` right for your
repository's real layout early — traceability, coverage, and impact analysis
all depend on them.

## RepoWise (optional, separate file)

RepoWise's own configuration deliberately lives outside `workflow.toml`, in
a separate strict schema-1 file at `.agentic/integrations/repowise.toml`. Its
absence means RepoWise is disabled; `config validate`/`config show` inspects
it alongside the main configuration but it does not change schema 3 in any
way. This separation exists so RepoWise stays genuinely optional discovery
tooling, never part of AEGIS's own required policy surface.
