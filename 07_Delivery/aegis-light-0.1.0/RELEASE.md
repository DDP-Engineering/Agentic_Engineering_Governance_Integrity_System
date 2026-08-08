<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light 0.1.0 Delivery Package

- **AEGIS Light version**: 0.1.0 (first release)
- **Built**: 2026-08-02 (rebuilt after the first pilot; see *Pilot
  findings* below — the earlier local build of this version was never
  published and is superseded)
- **Runtime requirement**: Python 3.11 or newer, standard library only
- **Bundled runtime**: none — there is nothing to embed
- **Platform**: Windows and Linux, identical content
- **Status**: not published; local delivery only

AEGIS Light is a *companion* governance system for agent-driven
development: a staged workflow with requirements, specs, tests,
traceability and an audit trail that never blocks the agent. There are
no hooks, no gates and no waivers. The workflow lives in plain
instructions the agent reads; a single standard-library CLI scaffolds
artifacts and reports heuristic findings the agent self-corrects
against. The only hard gate is `check --strict`, and only if a team
wires it into CI.

It is a separate product from AEGIS 2.x, not an upgrade path: same
ideas, none of the machinery.

## Artifacts

| File | Bytes | Contents |
|---|---|---|
| `aegis-light-0.1.0.zip` | see `SHA256SUMS` | payload + docs, identical tree |
| `aegis-light-0.1.0.tar.gz` | see `SHA256SUMS` | the same tree, tar format |

Both archives hold byte-identical content and are **not**
platform-specific; the two formats exist only for local ergonomics.
Archive member timestamps are normalized, so rebuilding the same sources
reproduces the same checksums.

Archive layout:

```text
aegis-light-0.1.0/
  .agentic/        the payload - copy this folder into your repository
  INSTALL.md       three steps
  README.md        the product page
  LICENSE.txt
  docs/            the eight user guides (markdown)
```

## Install

Copy `.agentic/` into a repository, run `python .agentic/aegis.py init`,
point three keys in `.agentic/aegis.toml` at the project, review the
diff, commit. Nothing is installed outside the repository; uninstalling
is deleting `.agentic/` and the marked pointer blocks.

## What ships

- Five-stage workflow (frame, specify, design, build, deliver) plus a
  three-stage quick path and a three-phase adoption flow, defined in
  `AGENTS.md` and one step file per stage.
- Requirements as one TOML file each (eight categories, collision-safe
  8-hex ids), optional specs, per-component knowledge pages, and task
  journals that are the only run state.
- `aegis.py`: `init`, `task new`, `req new`, `status`, `check`, `test`,
  `report`. Advisory by default — `check` always exits 0; `--strict` is
  the CI gate.
- A 15-check heuristic catalog: five error-level and ten warning-level,
  with `[check] strict_promote` as the team's governance dial.
- Focused regression via `aegis test --impacted`.
- Machine-readable `--json` on `check` and `status`, versioned by a
  `schema` integer.

## Pilot findings folded into this build

AEGIS Light was migrated onto a real 500-requirement project before this
package was cut. Four changes came out of that, all included here:

- **`uncovered-source` ignored deleted files.** A deleted file stays in
  the diff, but no requirement can cover a file that no longer exists —
  the finding was unactionable. Now skipped.
- **`ticket-ref` flagged standards as tickets.** `UTF-8`, `SHA-256`,
  `RFC-2119` and friends share the JIRA shape. A technical-prefix
  exclusion list removes that whole class of false positives.
- **`outside-layout` flagged the pointer files `init` creates.** A fresh
  install greeted the user with three warnings caused by AEGIS itself.
  `AGENTS.md`, `CLAUDE.md` and `QWEN.md` are now exempt.
- **The payload never told agents not to edit it.** The ownership rule
  lived only in the user documentation, so an agent that found a bug
  patched `aegis.py` in place — where the next upgrade would have
  silently discarded it. `AGENTS.md` now carries a "Do not edit the
  payload" section telling the agent to report instead.

Also added: **EARS** as the recommended requirement shape (all five
patterns in the requirement template and the specify step), with the
rules that two "shall" clauses means two requirements and that prose
should never be contorted to fit a pattern. Guidance only — nothing
validates it.

## Verification

- 137 tests pass on Windows and on Linux (WSL2, Ubuntu 24.04); one test
  is POSIX-only and skips on Windows.
- `ruff check --select E,F,W` is clean.
- The build refuses to package unless the suite passes and the payload
  inventory matches the expected file list exactly.
- The archives were installed into a throwaway repository and driven
  through `init`, `check`, `test --impacted` and `report`.

## Known limitations

Stated plainly rather than worked around:

- A very large tracked diff is held in memory for the duration of one
  `git diff`; there is no in-tool mitigation.
- Captured command output goes to a temporary file, so a pathologically
  noisy command can consume temp-volume space until its timeout.
- On Windows hosts that refuse `taskkill`, a timed-out command's
  descendants may survive; the run says so instead of claiming a clean
  kill.
- Tracked filenames containing quotes or backslashes fall back to a
  per-file diff; beyond 25 such files the rest are reported as
  unscanned rather than silently skipped.

## Next

The pilot (adopting AEGIS Light in a real repository and driving a build
stage with a local small model) is the remaining planned phase.

## Publication

Not published. This record documents a local build only; no tag was
pushed and no release was created.
