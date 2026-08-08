# WAEGIS V2 — Current Contract Audit and Plan Corrections

## 1. Audited baseline

This audit was performed on 2026-08-08 against the working tree on branch
`AEGIS_V2`, whose current commit at audit time was `be77ead`. The planning files
already contained uncommitted owner edits; those edits were treated as the
proposal baseline and corrected in place. Unrelated deleted review folders were
not touched.

### AEGIS

- The runnable development source is the exact copied payload package under
  `05_Software/aegis/template/.agentic/cli/src/aegis/`; there is no separate
  `05_Software/aegis/src/` implementation.
- At initial audit time, development metadata and embedded declarations said
  AEGIS `2.1.0`, and WP9 required a MAJOR release without assigning it. Later
  on 2026-08-08 the owner assigned AEGIS `3.0.0`; the current in-tree version
  declarations now reflect that decision. WAEGIS 3 therefore pins AEGIS
  compatibility to `>=3.0.0,<4.0.0`.
- `workflow.toml` schema version is 3 and the parser is closed/strict.
- `[quick.changed_paths]` is optional. Absence means disabled with retained
  `max_paths = 10`; an active table accepts `mode = "disabled"|"advise"` and a
  positive integer threshold.
- `[gates.test].impacted_command` is an optional argv prefix. It is not a shell
  command template and should remain advanced/operator-owned in WAEGIS.
- `aegis config validate --json` exists and returns the stable
  `status`/`stage`/`artifact`/`next` envelope plus schema versions. It is the
  correct install-time configuration oracle.
- A new install normally has no selected run. `aegis run status --json` then
  reports `RUN-POINTER-MISSING`; the current V1 smoke verifier intentionally
  accepts that outcome. Requiring a status envelope for every fresh install was
  incorrect.
- Payload wrappers resolve explicit `AEGIS_PYTHON`, then a V1
  `WAEGIS_HOME/runtime-python` registration, then system Python. The current
  native WAEGIS Core artifacts bundle and register CPython, so a Python-required
  zipapp is a real support-boundary change.
- The AEGIS template currently contains 155 payload files and all supported
  adapter trees. WAEGIS copies them as one payload rather than selecting a
  subset.
- Five AEGIS test modules import `waegis`: OpenCode, Pi, Qwen, scaffold, and
  release-hygiene coverage. Keeping the `waegis` package path avoids an
  unnecessary import migration, though behavior assertions must change for V2.

### WAEGIS 1

- Current size is 26,226 Python source lines, 2,448 packaging lines, and 18,495
  Python test lines.
- Public commands are `new`, `adopt`, `analyze`, `configure`, `doctor`,
  `repair`, `repowise`, `upgrade`, and `version`.
- The current package/import/command name is `waegis`; repository instructions
  require it to remain under `05_Software/waegis/` unless the owner explicitly
  requests a rename.
- V1's smoke order and transaction rollback can tolerate conditions that the
  proposed Git-only design cannot. The V2 order must therefore validate before
  manifest publication and must not commit before smoke.
- V1's manifest records copied, generated, and skipped paths, but V2 needs a
  clearer per-file disposition because repair/upgrade authority is the core
  project-owned-data boundary.
- V1's strict adapter check is deliberately narrow: the known fail-open format
  is `.codex/hooks.json`, whose accepted top-level keys are `description` and
  `hooks`. The plan must not claim equivalent host parsers that do not exist.
- V1's release system provides Pythonless native archives and reproducibility,
  while the standalone `waegis.pyz` requires Python. These are different
  product capabilities.

## 2. Corrections applied to the plan

| Proposed assumption | Correction |
|---|---|
| Build V2 beside V1 as `05_Software/waegis2/`, import `waegis2` | Replace the implementation on a dedicated branch under `05_Software/waegis/`; preserve `waegis` package/import/command; keep V1 through Git baseline/history |
| Hard break means no V1 bytes are ever read | Permit a minimal top-level V1 detector for safe guidance; never load or trust V1 ownership/configuration data |
| `--allow-dirty` is an acceptable warning-only override | Remove it; it invalidates exact Git rollback and project-owned-data preservation |
| Generic `git checkout`/`git clean` guidance is sufficient | Emit exact `git restore` and path-scoped `git clean -fdx --` commands before mutation and test them verbatim |
| A one-hour-old lock is stale | Time alone cannot prove a dead owner; require visible metadata and explicit dead-owner `--break-lock` |
| Commit, then smoke | Validate wrapper/config/status first, publish manifest last, and do not automate branches/commits |
| Fresh `run status --json` must return the normal envelope | Accept the expected `RUN-POINTER-MISSING` fresh state; use `config validate --json` as the primary install oracle |
| "Full schema-3 owned surface" | The payload template supplies complete schema 3; WAEGIS edits an explicit subset and preserves advanced/operator-owned fields byte-for-byte |
| Repair may regenerate generated files | Repair only managed payload files; route configuration to `configure` |
| A V2 golden manifest alone defines the schema | Define manifest version 2, closed top-level fields, per-file dispositions, path rules, and semantic adversarial tests; use the golden only for stable serialization |
| Existing `files/generated/skipped` ownership is enough | Add managed/generated/seeded/kept-local/sidecar dispositions and a template-derived ownership classification test |
| Adjacent SHA-256 gives supply-chain integrity | Treat it as corruption detection unless verified through a trusted publication channel; separately verify a closed internal payload inventory |
| Dropping embedded CPython costs nothing | Final D3 retains both the Python-required zipapp and Pythonless Windows/Linux runtime bundles; keep only the focused runtime lock, launchers, registration, and tests |
| Create a WAEGIS-local changelog | Use root `CHANGELOG.md` as the canonical record and keep `template/CHANGELOG.md` empty |
| Optional RepoWise Phase 7 can finish the plan | Make Phase 7 mandatory cross-platform integration/retirement evidence; handle any future RepoWise work separately |
| AEGIS payload/tests are never modified by the project | Keep them reference-only during core work, then update behavior-coupled tests and documentation in the explicit integration phase |

## 3. Improvements beyond factual corrections

- The interview becomes conditional, so disabled gates and guardrails do not
  ask for unused commands or patterns.
- `new` requires an absent target and clone support is dropped; clone first and
  use `adopt`.
- Git history automation is removed. This makes the safety proof worktree-only
  and eliminates Git identity, branch validation, staging, and commit failure
  paths.
- The manifest becomes a success marker written after real AEGIS validation,
  rather than state that can claim installation before smoke finishes.
- The retirement matrix now contains every AEGIS heavy-improvement continuity
  gate: clean offline install, idempotent check/doctor, dry-run and real upgrade,
  recovery, adapter coverage, version readback, two representative repositories,
  and Windows plus native POSIX evidence.
- Project-owned preservation has explicit sentinel coverage for workflow,
  requirements/specifications, components, knowledge, reports, runs, workspace
  state, adapter conflicts, and unrelated ignored paths.

## 4. Final owner decisions (2026-08-08)

1. **D1 — RepoWise:** excluded from V2 core and the retirement critical path;
   use external/manual configuration, with any future lifecycle automation
   designed as a separate tool.
2. **D3 — Distribution:** ship both the Python 3.11+-required payload zipapp and
   Pythonless Windows/Linux x64 bundles. Native bundles contain the identical
   payload-bearing zipapp plus pinned CPython and register that runtime for
   deployed AEGIS wrappers. The payload is not duplicated as a loose tree; the
   bundles are artifact forms, not editions.
3. **D4/D6 — Versions:** the V2 architecture ships as WAEGIS `3.0.0`, aligned
   with AEGIS `3.0.0`, and supports AEGIS `>=3.0.0,<4.0.0` only. “V2” remains
   the planning/architecture name.
4. **D7 — Git history automation:** removed. WAEGIS may run `git init` for a new
   absent target, but only reports review/commit guidance; it never creates
   branches, stages files, or commits.

The package location/import decision is not open: it follows the current
repository instructions unless the owner explicitly changes those instructions.

## 5. Audit commands and evidence

The following read-only checks informed the audit:

```powershell
git status --short
git branch --show-current
git log -1 --oneline
uv run --group dev python -B -m aegis --help
uv run --group dev python -B -m aegis config --help
uv run --group dev python -B -m aegis run status --help
uv run --group dev python -B -m waegis --help
uv run --group dev python -B -m waegis <command> --help
```

Source/test/packaging counts were measured from current non-cache Python and
packaging files. A first parallel suite attempt exceeded the runner's two-minute
combined timeout and was inconclusive. Serial reruns with adequate timeouts then
established the current baseline:

```text
AEGIS:  638 passed, 3 skipped in 64.49s
WAEGIS: 700 passed, 8 skipped in 106.66s
```

Those full-suite baselines preceded the same-day AEGIS 3.0.0 version assignment.
After the assignment, the current package read back `3.0.0` and the targeted
release-hygiene suite passed (`6 passed in 6.86s`). Phase 7 still reruns the full
AEGIS suite against the completed WAEGIS 3 implementation.

The skips are the current suites' platform/optional-case skips; this plan does
not treat them as future retirement evidence. Phase 7 still requires the full
relevant Windows/POSIX V2 and AEGIS integration paths without WAEGIS-importing
scope exclusions.
