<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS Implementation Plan — Guided Configuration & Deployment Wizard for AEGIS

> Status: **core lifecycle and packaging implemented; stabilization complete,
> live release verification still open.**
> Date: 2026-07-11.
> Inputs: `2026_AgenticDeliveryOrchestrator/00_Planning/Onboarding_Wizards_Analysis_And_Proposal.md`
> (the WAEGIS/WADORE analysis), `2026_AgenticDeliveryOrchestrator/00_Planning/TODO.md`,
> and this repository (AEGIS 0.4.0).
>
> This plan is written to be executed **task by task with Claude Code**. Each
> task states its goal, deliverables, acceptance criteria, dependencies, the
> recommended Claude model, and the recommended reasoning (extended-thinking)
> level. Section 12 contains the standing instruction block to paste into every
> Claude Code session.

---

## 0. Implementation amendment (2026-07-16)

- Implemented commands: `new`, `adopt`, `analyze`, `configure`, `doctor`,
  `repair`, `upgrade`, and `version`.
- The common JSON envelope, strict path confinement, payload compatibility,
  fingerprinted re-detection, persistent rollback transactions, current
  manifest/configuration metadata, and payload-bundled packaging are in place.
- Manifest and journal remain version `1` because WAEGIS is unreleased. Their
  current fields are mandatory; earlier partial layouts are rejected. There is
  no migration, restamp, or compatibility reader.
- M4 remains open only for Ubuntu 22.04/remote-clone verification. The Windows
  lifecycle journey is recorded in
  `06_SoftwareDocu/WAEGIS_Lifecycle_Live_Verification.md`; M6 remains open for
  Ubuntu and clean-machine repetition. T7.1/T7.2 are implemented and locally
  archive-verified on Windows, while clean-machine Windows/Ubuntu execution is
  still required; see
  `06_SoftwareDocu/WAEGIS_Packaged_Distribution_Verification.md`.
- T7.3 network self-update is deferred until authenticated release signatures
  are designed. Archives are distributed side-by-side manually. M8 GUI and M9
  AI remain deferred and are not exposed in CLI help.
- In all later sections, this amendment supersedes references to blind journal
  skipping, manifestless upgrade/restamping, stubs, and checksum-only
  self-update.

---

## 1. Scope

### 1.1 In scope (this repository)

**WAEGIS** — the guided wizard that configures and deploys the AEGIS platform
(the `05_Software/aegis/template/` payload) into a target repository, in a way
a person with **no repo-setup knowledge** can follow.

- Two journeys: **`waegis new`** (new project) and **`waegis adopt`**
  (existing project).
- Lifecycle commands: **`waegis analyze`**, **`waegis configure`**,
  **`waegis doctor`**, **`waegis repair`**, **`waegis version`**, and
  **`waegis upgrade`** — the "support updates" requirement.
- Self-contained distribution: zero third-party Python dependencies from day
  one; embedded-CPython app directory as the final packaging stage (no Python,
  no admin rights, no manual installs on the operator machine).
- Console frontend first (mandatory baseline, scriptable via answers files);
  local-web GUI as a later optional milestone; optional AI advisor last.

### 1.2 Out of scope (owned by the ADORE repository)

- WADORE (host/orchestrator wizard), forge label creation, container image
  scaffolding, ADORE profile generation, synthetic-ticket supervised run,
  service install (phases P5–P8 of the analysis document).
- **But:** every WAEGIS surface is designed so a future WADORE can delegate to
  it non-interactively — `--answers FILE`, `--json` output, meaningful exit
  codes, and the install manifest are the integration contract.

### 1.3 Requirements restated (from the user + analysis doc)

| # | Requirement | Where satisfied |
|---|---|---|
| R1 | Guided, very human-accessible configuration + deployment | Step engine §4, novice `why` text on every step, plan preview |
| R2 | Self-contained wizard | Stdlib-only package (§3, AD-3), embedded-runtime packaging (M7) |
| R3 | Supports updates | Install manifest §6, `analyze`/`doctor`/`upgrade` (M3, M6) |
| R4 | Two modes: new project / existing project | `waegis new` (M4), `waegis adopt` (M5) |
| R5 | Verify after every step | `verify()` is a required part of the step contract §4 |
| R6 | Safe to abort/re-run | detect→skip, checkpoint journal, resume §4 |
| R7 | Corporate restriction detection with IT-forwardable reports | Probe layer + report generator (M2) |

---

## 2. Grounding: what exists today in this repository

Assets the wizard **reuses and must not reimplement**:

- `02_Tools/create_project_from_template.py` — safe copy semantics
  (`--dry-run`, `--force`, `--existing-repo`, never-overwrite default,
  exclusion rules). The wizard absorbs these semantics into a manifest-aware
  copier; the script becomes a thin wrapper (T3.2).
- `05_Software/aegis/template/` — the versioned payload: `.agentic/` (CLI,
  hooks, skills, tools, knowledge, requirements, registry, reports,
  `workflow.toml`, `components.toml`), agent adapters (`.claude/`, `.codex/`,
  `.pi/`, `.opencode/`, `.qwen/`), `AGENTS.md`, `CLAUDE.md`, `QWEN.md`,
  `opencode.json`, starter `CHANGELOG.md`.
- `template/.agentic/workflow.toml` — the **single configuration surface** the
  new-project wizard must generate. The documented gotcha (keeping
  `[write_zones]` aligned with `[source].roots`/`[tests].roots` and
  `[traceability].coverable_roots`) becomes a generator invariant (§7).
- `template/.agentic/tools/run.ps1|run.sh|install.ps1|install.sh` — the smoke
  targets every deployment verifies against.
- The in-repo adoption workflow
  (`adoption-intake → adoption-alignment → repo-discovery → component-map →
  component-adoption → baseline-review → adoption-delivery`) and the
  `agentic-adoption` skill — Wizard E hands off to this; it does not re-do it.
- Repo conventions: stdlib-only, offline-first, Python ≥ 3.11, doxygen-style
  docstrings per `01_Documentation/Code_Style.md`, SemVer + root
  `CHANGELOG.md`, validation commands in `AGENTS.md`.

Proven designs to **port** from the ADORE repository (do not import across
repos; re-implement the small primitives in `waegis` following the same
shape):

- `ador/wizard.py` — `FieldSpec` + `ask()` (description, example, detected
  default, validate, re-prompt), `ConsoleAsker`/`ScriptedAsker`, answers-file
  seam, never-save-invalid guard.
- `ador/doctor.py` — injectable `CommandRunner`, offline-testable probes,
  curated OS-keyed guidance text.

---

## 3. Ratified architecture decisions

| ID | Decision | Rationale |
|---|---|---|
| AD-1 | WAEGIS is a **separate package** at `05_Software/waegis/` in this repository — not part of the copied payload, not an `aegis` CLI subcommand | The payload must stay lean (AGENTS.md rule); the wizard runs *before* the payload exists in the target; matches analysis §6 option 3 |
| AD-2 | Two entry points (`new`, `adopt`) over **one shared step engine**; steps are data executed by one runner | Analysis §2.1; keeps scope creep in check (new needs = new steps, not new mechanisms) |
| AD-3 | **Stdlib-only**, Python ≥ 3.11, offline-first, injectable runners everywhere | Repo rule; makes the zipapp/embedded packaging trivial; tests stay offline |
| AD-4 | Frontends: **console first** (mandatory), local-web GUI later, **no TUI framework** | Analysis §3.1 recommendation |
| AD-5 | **Deterministic core; AI advisor optional and last** — AI proposes, deterministic code validates, human confirms; fully functional with AI disabled | Analysis §3.2 |
| AD-6 | The **install manifest** (`.agentic/install-manifest.json`) is written by every wizard copy and is the enabler for `analyze`/`doctor`/`upgrade` | Analysis §2.5 — highest-leverage structural change; closes decision D6 |
| AD-7 | Packaging in two stages: (a) run-from-checkout + `waegis.pyz` zipapp interim; (b) app directory with embedded CPython (python-build-standalone; Ubuntu 22 = glibc ≤ 2.35) with staged side-by-side self-update | Analysis §3.3–3.4 |
| AD-8 | Every step: `detect() → act() → verify()`, verify **required**, results journaled, re-run = detect-and-skip | User requirement R5/R6 |
| AD-9 | Non-interactive seam: `--answers FILE` + `--json` on every command | WADORE integration contract; also the test harness |
| AD-10 | Secrets: WAEGIS never stores, echoes, or journals secret values; it does not need any today (forge tokens are WADORE scope) | Keeps D9 out of this repo's blast radius |
| AD-11 | WAEGIS is versioned independently (starts 0.1.0) and pins a **compatible payload version range** (initially `aegis >= 0.4.0, < 1.0`) recorded in `waegis/version.py` | Closes D7 for the repo side |

---

## 4. The step engine (core contract)

Both journeys are an ordered catalog of steps executed by one engine. Every
step implements:

```text
StepSpec
  id             stable key, e.g. "repo.payload-copy" (never renamed once released)
  title          one line, novice-readable
  why            2–4 sentences: what this is and why the workflow needs it
  phase          P0-machine | P1-prereq | P2-network | P3-repo | P4-deploy | P5-handoff
  automation     auto      — wizard acts, no confirmation
                 assisted  — wizard acts after human confirms
                 manual    — human acts, wizard guides then verifies
  preconditions  list of step ids that must be green first
  applies(ctx)   bool — lets one catalog serve both modes and optional branches
  detect(ctx)    already satisfied? idempotent, strictly read-only
  act(ctx)       perform or guide the step; may prompt via the Asker
  verify(ctx)    machine-checkable postcondition — REQUIRED, never trusts "the
                 human said so"
  on_fail(ctx)   novice-readable diagnosis + remediation + copyable "ask IT"
                 text where relevant
```

Engine behaviors (all are hard requirements, all get dedicated tests):

1. **detect → skip**: green steps render ✓ and are skipped; this alone gives
   resume-after-abort, idempotent re-run, and "adopt a half-configured repo".
2. **verify after every act** — a step is green only when its probe passed.
3. **Checkpoint journal** — one JSON file per wizard run under the WAEGIS home
   (`%APPDATA%\waegis` / `~/.config/waegis` / `WAEGIS_HOME`), recording for
   each step: timestamps, detect/act/verify outcomes, chosen answers
   (secrets excluded by construction), and artifacts created (paths, commits).
   The journal is the input for `doctor` and for resume.
4. **Plan preview** ("terraform plan" style): before any mutation, render the
   full ordered step list with what each will change; operator approves the
   plan once, then confirms `assisted` steps individually. `--dry-run` stops
   after the preview.
5. **Prompt shape**: every question uses `FieldSpec` — description, example,
   detected default, validator, re-prompt on invalid. Novice mode (default)
   prints the `why`; `--terse` suppresses it.
6. **Answers file**: `--answers FILE` (TOML or JSON) pre-supplies answers;
   missing answers still prompt unless `--non-interactive`, which fails
   loudly listing the missing keys.

---

## 5. Product surface (CLI contract)

```text
waegis new TARGET [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis adopt TARGET [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis analyze --repo PATH [--json]
waegis configure --repo PATH [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis doctor --repo PATH [--json]
waegis repair --repo PATH [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis upgrade --repo PATH [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis version [--json]
```

- `--payload PATH` overrides payload resolution (default: bundled snapshot in
  a packaged install; `05_Software/aegis/template/` when running from the
  repo checkout).
- `--json` is non-interactive and emits exactly one common envelope.
- Exit codes: 0 success, 1 warning/approval or decisions required, 2 validation
  or verification failure, 3 operational/internal failure.

---

## 6. Install manifest specification (v1)

Written to `TARGET/.agentic/install-manifest.json` by every wizard copy:

```json
{
  "manifest_version": 1,
  "product": "aegis",
  "payload_version": "0.4.0",
  "installed_at": "2026-07-11T12:00:00Z",
  "installed_by": "waegis 0.1.0",
  "mode": "new",
  "files": {
    ".agentic/cli/src/aegis/cli.py": { "sha256": "…", "size": 12345 },
    "AGENTS.md": { "sha256": "…", "size": 2345 }
  },
  "generated": [ ".agentic/workflow.toml" ],
  "skipped": [ "CLAUDE.md" ],
  "payload_digest": "<sha256 of the payload inventory>",
  "configuration": {
    "answers": { "language": "python" },
    "generator_version": "0.1.0",
    "generated_files": {
      ".agentic/workflow.toml": { "sha256": "<generated file hash>" }
    }
  }
}
```

Semantics:

- `files` — every payload file copied verbatim, keyed by repo-relative POSIX
  path, with the **original** (as-shipped) sha256. This is what makes
  `upgrade` three-way aware (shipped-original / current-local / new-template).
- `generated` — files the wizard *created or rewrote from answers*
  (`workflow.toml` always; possibly `.gitattributes`). Upgrade never
  overwrites these; doctor validates them against the new payload's schema
  instead.
- `skipped` — payload files the operator chose to keep local during adoption
  conflicts. Upgrade re-offers them.
- Absence, corruption, or an earlier partial layout remains visible to
  `analyze`, but `configure`, `repair`, and `upgrade` reject it. There is no
  compatibility migration or conservative restamp path.
- Every managed path is canonical and repository-relative. Traversal,
  absolute/drive/UNC paths, normalization/case collisions, and source/target
  symlink or reparse-point escapes are rejected.
- The manifest lists itself under neither key and is excluded from hashing.
- Line endings: hash the byte stream exactly as shipped; the copier must copy
  bytes verbatim (no newline translation) so hashes are stable across
  Windows/Linux checkouts. Document interaction with `.gitattributes`.

---

## 7. `workflow.toml` generation rules

One generator serves both modes; only the answer source differs (interview in
`new`, analysis proposals in `adopt`).

Inputs (each a `FieldSpec` with detected default):

| Answer | Example | Feeds |
|---|---|---|
| `source_roots` | `["src"]` | `[source].roots`, `[traceability].coverable_roots`, `[write_zones].implementation` |
| `test_roots` | `["tests"]` | `[tests].roots`, `[write_zones].check`, `[write_zones].component-adoption` |
| `language` | `"python"` | `[traceability].language`, `source_extensions`, `test_file_patterns` |
| `gate_test_cmds` | `[["uv","run","pytest","-q"]]` | `[gates].test` |
| `gate_lint_cmds` | `[["ruff","check","."]]` | `[gates].lint` |
| `alignment_enabled` | `true` | `[alignment].enabled` |

Hard invariants the generator enforces (unit-tested as properties, so the
documented "one gotcha" becomes impossible):

1. Every entry of `[source].roots` appears as `<root>/**` in
   `[write_zones].implementation` and verbatim in
   `[traceability].coverable_roots`.
2. Every entry of `[tests].roots` appears as `<root>/**` in
   `[write_zones].check` and in `[write_zones].component-adoption`.
3. `[write_zones].implementation` always also contains
   `.agentic/knowledge/components/**`.
4. All other sections keep the template defaults unless an answer explicitly
   changes them.
5. Output is parsed back with `tomllib` and the invariants re-checked before
   the file is written (never-save-invalid guard).
6. Language presets ship for at least: `python`, `typescript/javascript`,
   `java`, `csharp`, `go`, `rust`, `cpp`, plus `other` (operator supplies
   extensions/patterns). Presets set `source_extensions` and
   `test_file_patterns`.

Empty gates are permitted but produce a **loud, recorded warning** in the
step result and in `doctor` ("gates are configured empty and will pass
without checking anything").

---

## 8. Step catalogs

### 8.1 Wizard N — `waegis new TARGET`

| ID | Phase | Automation | detect / act / verify (summary) |
|---|---|---|---|
| `home.init` | P0 | auto | WAEGIS home + journal exist / create / write-read probe |
| `machine.os` | P0 | auto | OS + version in support matrix (Win 11, Ubuntu 22+) / n.a. / report; warn-not-block outside matrix |
| `machine.disk` | P0 | auto | free space at TARGET drive ≥ 1 GB / n.a. / report |
| `prereq.python` | P1 | assisted | `python3.11+` or launcher found (probe `python`, `py -3`, `python3`) / guide install (winget/apt command shown, run on confirm) or use embedded runtime when packaged / re-probe reports version ≥ 3.11 |
| `prereq.git` | P1 | assisted | `git --version` ≥ 2.30 / guide install / re-probe |
| `prereq.git-identity` | P1 | manual | `git config user.name`/`user.email` set (global or will be set repo-local) / guide exact commands / re-probe |
| `net.proxy` | P2 | auto | applies only when a remote clone is requested; env + OS proxy settings + connect test / n.a. / reachability report, IT text on block |
| `repo.target-path` | P3 | assisted | TARGET valid: creatable or empty dir, not nested inside another git work tree (unless operator confirms) / create dir / dir exists + writable |
| `repo.init-or-clone` | P3 | assisted | TARGET is a git repo / `git init -b main` **or** `git clone URL` per answer / `git rev-parse --is-inside-work-tree` |
| `deploy.payload-copy` | P4 | assisted | manifest present + hashes match bundled payload / manifest-aware copy / re-hash every copied file against manifest; file count matches |
| `deploy.workflow-toml` | P4 | assisted | valid `workflow.toml` satisfying §7 invariants / interview → generate / parse + invariant check + roots exist (create empty roots with `.gitkeep` on confirm) |
| `deploy.gates` | P4 | assisted | gates non-empty / capture commands; offer to run each once in TARGET / commands exit 0, or operator explicitly accepts a deferred/red gate (recorded) |
| `verify.cli-smoke` | P4 | auto | n.a. / run `.agentic/tools/run.ps1\|.sh --help` / exit 0 |
| `verify.workflow-smoke` | P4 | auto | n.a. / run wrapper `status` (and `gates run` when configured) in TARGET / exit 0, output parseable |
| `verify.hooks-present` | P4 | auto | all four hook files + chosen agent adapter dirs present / n.a. / listed ✓ |
| `repo.initial-commit` | P4 | assisted | working tree clean with payload committed / `git add` + commit (message templated) / `git status --porcelain` empty; commit exists |
| `handoff.summary` | P5 | auto | n.a. / print + journal: what was installed (versions), where, the first operator prompt to try (from `PROMPT_CHEATSHEET.md`), how to run `doctor`, pointer to orchestrator onboarding (WADORE) as a separate product / journal written |

### 8.2 Wizard E — `waegis adopt TARGET`

Reuses `home.init` through `net.proxy` unchanged, then:

| ID | Phase | Automation | detect / act / verify (summary) |
|---|---|---|---|
| `repo.validate-existing` | P3 | auto | TARGET is a git work tree; record branch, dirty files (warn), submodules, LFS / n.a. / report confirmed by operator |
| `repo.prior-install` | P3 | auto | `.agentic/` present? manifest present? version? drift summary / n.a. / routes: none → continue; manifest current → suggest `doctor`; manifest older → suggest `upgrade`; `.agentic` without manifest → conservative adoption path |
| `analyze.repo` | P4 | auto | analysis report exists for this HEAD / run heuristics §9, write report JSON + human summary / operator confirms the proposals field by field |
| `deploy.adoption-copy` | P4 | assisted | manifest present / never-overwrite copy with conflict report; per-file keep/replace decisions; write manifest incl. `skipped` / hashes verified; conflict decisions journaled |
| `deploy.workflow-toml` | P4 | assisted | same as Wizard N, seeded from analysis proposals instead of blank questions |
| `deploy.gates` | P4 | assisted | same as Wizard N, seeded from detected build/CI commands |
| `verify.cli-smoke` / `verify.workflow-smoke` / `verify.hooks-present` | P4 | auto | identical to Wizard N |
| `repo.adoption-commit` | P4 | assisted | adoption branch (default `chore/aegis-adoption`) created + payload committed / branch + add + commit / clean tree on the branch |
| `handoff.adoption` | P5 | auto | n.a. / print + journal the exact operator prompt that starts the in-repo adoption workflow (`adoption-intake` with the `agentic-adoption` skill, agent of the operator's choice) — WAEGIS's job ends here / journal written |

---

## 9. Repo analysis heuristics (`analyze.repo`, also `waegis analyze`)

Deterministic, read-only, ranked-proposal output (never a silent decision):

- **File inventory**: `git ls-files` (fallback: filesystem walk honoring
  `.gitignore` top-level patterns); extension histogram weighted by file count
  and total bytes → language ranking.
- **Build systems**: presence of `pyproject.toml`/`setup.py`/`setup.cfg`,
  `package.json` (+ lockfiles), `pom.xml`, `build.gradle(.kts)`,
  `CMakeLists.txt`, `Cargo.toml`, `go.mod`, `*.csproj`/`*.sln`, `Makefile`,
  `Dockerfile`.
- **Source roots**: conventional dirs (`src`, `app`, `lib`, package dirs with
  `__init__.py`, `cmd`/`pkg`/`internal` for Go, `Sources` for Swift), else the
  minimal set of top-level dirs covering ≥ 90 % of code files.
- **Test roots**: `tests`, `test`, `spec`, `src/test/java`, `__tests__`;
  detect **colocated tests** (e.g. `*_test.go`, `*.spec.ts` beside sources)
  and flag that write-zone patterns must then be file-pattern based.
- **Gate command candidates**: `package.json` `scripts.test`/`scripts.lint`;
  pytest/ruff config in `pyproject.toml`; `Makefile` targets `test`/`lint`;
  CI files (`.gitlab-ci.yml`, `.github/workflows/*.yml`) script lines —
  extracted as *candidates with provenance*, never auto-trusted.
- **Adoption risk flags**: submodules (`.gitmodules`), LFS
  (`.gitattributes` `filter=lfs`), monorepo signals (multiple lockfiles /
  `packages/*`), very large repos (> 10k files → warn analysis is heuristic),
  existing `.agentic/` or agent adapter dirs (conflict preview),
  pre-existing `AGENTS.md`/`CLAUDE.md` (**guaranteed conflict** — per-file
  decision with a merge hint, never overwrite).
- Output: `analysis.json` (machine) + human summary table; both journaled.

---

## 10. Doctor checks and the upgrade algorithm

### 10.1 `waegis doctor --repo PATH` check catalog

| Group | Checks (each: novice-readable fix-it + machine result) |
|---|---|
| Machine | P0/P1 probes re-run (python, git versions) |
| Manifest | present, parses, `manifest_version` known; payload version vs bundled payload → "update available" |
| Drift | current file hashes vs manifest originals → modified/missing/extra lists (counts in human view, full lists in `--json`) |
| workflow.toml | parses; §7 invariants hold; every configured root exists on disk; write_zones aligned; gates non-empty (warn); `[components].manifest` path exists |
| Runnability | wrapper scripts present; `run.ps1|.sh --help` exits 0; hook files present; chosen adapters present |
| Journal | last wizard run for this repo completed or names the step it stopped at |

Exit codes: 0 = healthy, 1 = warnings only, 2 = at least one failure.
`waegis analyze` = the read-only subset (inventory + manifest + drift), no
health verdicts.

### 10.2 `waegis upgrade --repo PATH` (three-way, manifest-driven)

For each file, compare O = original hash (manifest), L = current local hash,
N = new payload hash:

| Case | Action |
|---|---|
| L = O, N = O | unchanged — skip |
| L = O, N ≠ O | auto-apply new version |
| L ≠ O, N = O | keep local (upstream unchanged) |
| L ≠ O, N ≠ O, L = N | already matches new — re-stamp manifest |
| L ≠ O, N ≠ O, L ≠ N | **conflict** — per-file choice: keep local / take new / write `<file>.new` beside it |
| in new payload, not in manifest | new upstream file — add (conflict flow if a local file exists) |
| in manifest, not in new payload | removed upstream — delete if unmodified, keep + report if modified |

Rules: `generated` files are never touched (doctor re-validates them against
the new payload's template instead); plan preview + `--dry-run` first;
journal every decision; run `verify.cli-smoke` + `verify.workflow-smoke`
after applying; only then rewrite the manifest with the new
`payload_version` and new original hashes. Upgrade requires the single current
manifest layout; absent, incomplete, or unknown layouts are rejected and must
be handled as a fresh `adopt` after explicit operator review.

---

## 11. Packaging and self-update

### Stage A (implemented): run from checkout + payload-bundled zipapp

- `uv run waegis …` / `python -m waegis` from `05_Software/waegis/`.
- `05_Software/waegis/packaging/build_release.py --zipapp-only` builds a
  stdlib `zipapp` that bundles a snapshot of the template payload. The zipapp
  remains the host-Python distribution.

### Stage B (implemented; clean-machine release verification open)

> Current implementation: `packaging/build_release.py` emits
> `waegis-X.Y.Z-windows-x64.zip`, `waegis-X.Y.Z-linux-x64.tar.gz`, and the
> zipapp, with a pinned runtime lock, internal archive manifests, an external
> release manifest, and `SHA256SUMS`. The original layout sketch below is kept
> as design provenance; its filenames and tool locations are superseded.

- Layout: `waegis-x.y.z/ {bin launcher (waegis.cmd / waegis sh), runtime/
  (embedded CPython from python-build-standalone; Linux build targeting
  glibc ≤ 2.35 for Ubuntu 22.04), app/ (waegis package), payload/
  aegis-template-x.y.z/, VERSION, RELEASE-MANIFEST.json (sha256 of every
  file)}`.
- Build script `02_Tools/package_waegis.ps1|.sh` produces
  `07_Delivery/waegis-x.y.z-win64.zip` and `waegis-x.y.z-linux-x64.tar.gz`;
  verifies contents against the release manifest; **no secrets, no
  project-specific config in the package** (same properties as the existing
  packaging TODO).
- Runtime downloads happen at **build machine** packaging time only, never on
  the operator machine.

### Self-update (deferred)

> The design bullets below are retained only as future design history. There
> is no `self-update` command in the released CLI; application archives are
> distributed side-by-side manually until authenticated signatures exist.

- `waegis self-update --check-only` reads a small release manifest (versions +
  sha256; signature field reserved, see risk D4') from a configured URL or
  file-share path (corporate offline mirror path).
- Staged update: download side-by-side dir → run its self-test
  (`waegis version` + engine smoke) → atomic junction/symlink swap → keep the
  previous version for rollback. Never patch in place.
- Payload updates are never auto-applied to repos: a newer bundled payload
  only makes `waegis upgrade --repo` available and makes `doctor` say
  "update available".

---

## 12. Standing instructions for every Claude Code task

Paste this block (adapted with the task text) at the start of each session:

```text
You are implementing one task of 00_Planning/WAEGIS_Wizard_Implementation_Plan.md
in D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System.
Read that plan section and AGENTS.md first. Non-negotiable constraints:
- Python >= 3.11, stdlib only, offline-first; all subprocess/network access
  behind injectable runner interfaces so tests run offline.
- Follow 01_Documentation/Code_Style.md: file headers with the PolyForm
  license block and @file/@brief/@author/@date/@version; every function/class
  documented with @brief/@param/@return/@exception/@version; bump local
  @version tags on change.
- The wizard lives in 05_Software/waegis/ and is NEVER copied into the
  template payload; do not modify 05_Software/aegis/template/ except where the
  task explicitly says so.
- Add/extend tests under 05_Software/waegis/tests for every behavior; use
  ScriptedAsker + fake CommandRunner; no test may touch the network.
- Update CHANGELOG.md [Unreleased] and any affected README in the same change.
- Validate before finishing: python -m py_compile on changed files,
  uv run --group dev python -m pytest -q tests (in 05_Software/waegis),
  python -m waegis --help.
- Final summary: what changed, what was validated, what remains unverified.
```

Package skeleton (created in T0.1, referenced by all tasks):

```text
05_Software/waegis/
  pyproject.toml            # name waegis, version 0.1.0, deps [], scripts: waegis
  README.md
  conftest.py
  src/waegis/
    __init__.py  __main__.py  cli.py  version.py   # + payload compat range
    engine/   step.py  catalog.py  runner.py  journal.py  plan.py
    io/       prompts.py  answers.py  console.py  reports.py
    probes/   machine.py  tools.py  network.py
    payload/  manifest.py  copier.py  locate.py
    repo/     gitops.py  analyze.py  workflow_toml.py
    commands/ new.py  adopt.py  analyze.py  doctor.py  upgrade.py
  tests/
```

---

## 13. Task breakdown (execution order)

Legend — **Model**: recommended Claude Code model; **Reasoning**: extended
thinking level to request (`low` ≈ default, `medium` ≈ "think", `high` ≈
"think hard"/max thinking budget). **Size**: S ≤ half a session, M ≈ one
session, L ≈ one long or two sessions. General rule: architecture-bearing and
algorithm-heavy tasks get Opus 4.8 at high reasoning; well-specified
implementation gets Sonnet 5 at medium; docs/boilerplate get Sonnet 5 at low
(Haiku 4.5 acceptable). If Fable 5 is available on your plan, it may replace
Opus 4.8 on the `high` tasks.

### M0 — Scaffold and repo integration

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T0.1 Package scaffold** | Create `05_Software/waegis/` per §12 skeleton: pyproject (stdlib-only, `waegis` script, pytest config mirroring the aegis package), empty modules with compliant headers, `version.py` with wizard version + payload compatibility range (AD-11), README stub, smoke test asserting `python -m waegis --help` exits 0. Update root `README.md` + `AGENTS.md` repository-layout rules to mention `05_Software/waegis/` (the AGENTS.md "keep implementation under aegis/" rule must be amended to name both packages). Changelog entry. | Sonnet 5 / low / M |

*Acceptance:* pytest green in the new package; `--help` lists all planned
subcommands as stubs that exit 2 "not implemented"; AGENTS.md amended.

### M1 — Step engine foundation

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T1.1 Engine core** | `engine/step.py` (StepSpec, StepStatus, StepResult), `engine/catalog.py` (registration, ordering, precondition resolution, `applies()` filtering), `engine/runner.py` (plan build → preview gate → per-step detect/act/verify loop, failure stop with `on_fail` rendering, `--dry-run`), `engine/journal.py` (checkpoint JSON in WAEGIS home, resume: load journal → seed detect results). Property tests: precondition cycles rejected; verify always called after act; journal round-trip; resume skips green steps. | **Opus 4.8 / high / L** |
| **T1.2 Prompt + answers primitives** | Port the `FieldSpec`/`ask()` design: description, example, detected default, validator, re-prompt; `ConsoleAsker`, `ScriptedAsker`; answers-file load/save (TOML via tomllib, JSON) with unknown-key warnings; `--non-interactive` fails listing missing keys. Never-save-invalid guard helper. Tests with ScriptedAsker covering re-prompt, defaults, missing-answer failure. | Sonnet 5 / medium / M |
| **T1.3 Console renderer + reports** | `io/console.py`: plan preview table, live step status (✓ / ✗ / → / skipped), plain-ASCII fallback (Windows console safety — no reliance on ANSI or non-CP1252 glyphs unless detected); `io/reports.py`: environment report and the blocking-point report template (*attempted command, exact error, why needed, copyable IT request, alternatives*). `--json` emitters for plan and results. | Sonnet 5 / medium / M |

*Milestone acceptance:* a toy 3-step catalog (used only in tests) runs end to
end interactively and via answers file; abort mid-run + re-run resumes.

### M2 — Probes (machine, tools, network)

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T2.1 CommandRunner + machine/tool probes** | Injectable `CommandRunner` (mirrors the proven doctor design: run, capture, timeout, not-found handling). `probes/machine.py`: OS + version vs support matrix, arch, free disk at path. `probes/tools.py`: python (try `py -3`, `python3`, `python`; parse version; ≥ 3.11 verdict), git (≥ 2.30), uv (optional, informational). Each probe returns `ProbeResult{status, found_version, required, guidance}` with OS-keyed guidance text (winget/apt commands). Offline tests via fake runner for every OS/outcome combination. | Sonnet 5 / medium / L |
| **T2.2 Network/corporate probes** | `probes/network.py`: proxy detection (env vars + Windows registry/`gsettings` best effort), direct-vs-proxy HTTPS connect test to an operator-supplied host (only run when a remote operation is requested — offline-first default), TLS-interception heuristic (presented issuer vs known public CA list for the probe host), each producing the §12 blocking-point report. All socket use behind an injectable transport; tests use fakes only. | Sonnet 5 / medium / M |

*Milestone acceptance:* the machine/tool/network probes render a real
environment report (human + `--json`) when exercised directly on a real Win
11 machine (`waegis doctor` itself does not exist until T6.1/M6 — this
milestone proves the probe layer standalone); unit suite green offline.

### M3 — Install manifest + payload engine + analyze

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T3.1 Manifest module** | `payload/manifest.py`: schema v1 (§6), byte-exact sha256 hashing, read/write/validate, drift computation (modified/missing/extra) given a repo root. Golden-file tests; hash stability test across newline styles. | Sonnet 5 / medium / M |
| **T3.2 Manifest-aware copier** | `payload/copier.py`: absorb `create_project_from_template.py` semantics (exclusion rules, never-overwrite, `--force`, dry-run) + conflict report (exists-identical / exists-different with size+hash) + per-file decision hook (keep/replace/rename-`.new`) + manifest emission (`files`/`generated`/`skipped`). `payload/locate.py`: payload resolution order (`--payload` > bundled marker > repo checkout). Refactor `02_Tools/create_project_from_template.py` into a thin wrapper that calls the copier (public flags unchanged — it now also writes the manifest; document this). Tests: copy into empty dir, adoption with conflicts, byte-verbatim copy, manifest correctness. | **Opus 4.8 / high / L** |
| **T3.3 `waegis analyze`** | `commands/analyze.py`: manifest presence/version, drift lists, "which workflows installed" inventory, human + `--json`. Handles the no-manifest legacy case. | Sonnet 5 / low / S |

*Milestone acceptance:* copying the real template into a temp dir yields a
manifest whose hashes verify; deliberate edit → `analyze` reports exactly
that file.

### M4 — Wizard N (`waegis new`)

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T4.1 workflow.toml generator** | `repo/workflow_toml.py`: FieldSpecs of §7, language presets, generation from the real template file as base (read → modify → emit; comments may be regenerated — document), §7 invariants enforced + re-parse guard, root creation with `.gitkeep` on confirm. Property tests: for arbitrary root sets the invariants hold; golden tests per language preset. | **Opus 4.8 / high / L** |
| **T4.2 Git operations** | `repo/gitops.py` over CommandRunner: `is_work_tree`, `init -b main`, `clone`, identity get/set (repo-local offer), `status --porcelain`, `add`+`commit` with templated message, branch create. Windows/POSIX path safety. Fake-runner unit tests + a small marked integration test set using the real git in a tmp dir. | Sonnet 5 / medium / M |
| **T4.3 Wizard N catalog + command** | `commands/new.py`: register the §8.1 catalog over the engine; smoke steps run the real wrapper (`run.ps1` via `powershell -File` on Windows, `run.sh` via `bash`/`sh` on POSIX) inside TARGET; wire `--answers/--dry-run/--non-interactive/--json`. End-to-end test: ScriptedAsker + real payload + real git in tmp dir → green run, then re-run → all steps detect-skip. | **Opus 4.8 / high / L** |
| **T4.4 Live verification — new mode** | Interactive session: run `waegis new` on a real Windows 11 machine and on Ubuntu 22 (or WSL Ubuntu 22 if no VM), fix the small breakages this always finds (console encoding, launcher resolution, ps1 execution policy). Record a verification report under `06_SoftwareDocu/`. | Sonnet 5 / medium / M |

*Milestone acceptance (user-visible):* a novice-shaped transcript from empty
dir to committed, smoke-verified AEGIS repo with zero manual file editing.

### M5 — Wizard E (`waegis adopt`)

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T5.1 Repo analysis heuristics** | `repo/analyze.py` implementing §9 with ranked, provenance-tagged proposals; `analysis.json` schema; human summary. Fixture-based tests: mini repos for python-src, node-monorepo, java-maven, go-colocated-tests, repo-with-existing-CLAUDE.md, repo-with-partial-.agentic. | **Opus 4.8 / high / L** |
| **T5.2 Wizard E catalog + command** | `commands/adopt.py`: §8.2 catalog; prior-install routing (none / current / older / manifestless); adoption-copy conflict flow (per-file decisions journaled); workflow.toml + gates seeded from analysis; adoption branch + commit. End-to-end tests on the M5.1 fixtures. | **Opus 4.8 / high / L** |
| **T5.3 Hand-off + docs** — **absorbed into T5.2, no separate work needed.** T5.2's `commands/adopt.py` already sources the `handoff.adoption` prompt from the copied `PROMPT_CHEATSHEET.md` (`_adoption_operator_prompt`, regex-extracted from the target repo so it cannot drift), includes an informational agent-adapter chooser (`ADAPTER_DIR_NAMES`), and `05_Software/waegis/README.md` already documents both journeys. | Sonnet 5 / low / S |

### M6 — doctor + upgrade

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T6.1 `waegis doctor` - implemented** | Read-only catalog with typed repair/configure/upgrade actions and common JSON envelope. | Sonnet 5 / medium / M-L |
| **T6.2 lifecycle - implemented** | Adds transactional `configure`, `repair`, and `upgrade`: all decisions before approval, clean-Git policy, persistent backup/recovery, smoke verification, and manifest write last. A current valid manifest is mandatory. | **Opus 4.8 / high / L** |
| **T6.3 Live verification — update path** | Take a repo installed from payload 0.4.0, locally edit two payload files and workflow.toml, bump the template (scratch 0.4.1 with edits touching modified + unmodified files), run doctor → upgrade → doctor. Record report in `06_SoftwareDocu/`. | Sonnet 5 / medium / M |

### M7 - Self-contained packaging + self-update

> Current status: T7.1 and T7.2 are implemented in
> `05_Software/waegis/packaging/`; clean-machine verification remains. T7.3 is
> deferred and side-by-side manual distribution is the release policy.

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T7.1 Zipapp packaging** | `02_Tools/package_waegis.py`: build `waegis-x.y.z.pyz` bundling the payload snapshot + payload-version marker; contents verified against a generated manifest; output to `07_Delivery/`; version single-sourced from `pyproject.toml`. | Sonnet 5 / low–medium / M |
| **T7.2 Embedded-runtime app dir** | Stage-B layout (§11): fetch/pin python-build-standalone builds at package time (Windows x64; Linux x64 glibc ≤ 2.35), launchers, RELEASE-MANIFEST.json, `02_Tools/package_waegis.ps1|.sh`. Must verify on clean Win 11 and clean Ubuntu 22.04 (risk D10'). No secrets, no project config in package. | **Opus 4.8 / high / L** |
| **T7.3 self-update** | `commands/self_update.py`: `--check-only` against URL/file-share release manifest; staged side-by-side download → self-test → junction/symlink swap → rollback retention; opt-in config in WAEGIS home. Transport injectable; offline tests with fake transport + real-swap test on tmp dirs. | Opus 4.8 / high / M–L |

### M8 - Local-web GUI (optional, after M4-M6 are proven)

> Deferred and not exposed in CLI help.

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T8.1 Step API** | JSON API over the engine on `http.server` bound to `127.0.0.1` only: plan, step status stream (long-poll), answer submission, run control. Token-in-URL session guard so another local user cannot drive it. | Opus 4.8 / high / L |
| **T8.2 Single-page UI** | One self-contained HTML file (inline CSS/JS, zero external assets): step list with ✓/✗/current, `why` panels, copyable commands, answer forms mirroring FieldSpec validation, plan-preview approval. Shows the exact console command each step runs (teach, don't hide). | Sonnet 5 / medium / L |
| **T8.3 GUI parity tests + hardening** | Drive the API with stdlib http client in tests: full Wizard N journey headless; localhost-only + session-token tests; graceful port fallback. | Sonnet 5 / medium / M |

### M9 - AI advisor (optional, strictly last)

> Deferred and not exposed in CLI help.

| Task | Content | Model / Reasoning / Size |
|---|---|---|
| **T9.1 Advisor client + consent** | OpenAI-compatible HTTP client (stdlib), endpoint/model/key from WAEGIS home config; **explicit consent step before any repo content leaves the machine**, corporate default = off/local; secrets and `.env` content never sent; advisor output flows into the same validate-then-confirm path as human answers. | Opus 4.8 / high / M |
| **T9.2 Advisor integrations** | (a) Wizard E analysis prefill when heuristics are ambiguous; (b) failure-explanation enrichment of blocking-point reports; (c) "explain this step" free-form help. Each with a deterministic fallback and an off switch; fake-endpoint tests. | Sonnet 5 / medium / M |

### Cross-cutting release tasks (repeat at each milestone end)

- Roll `CHANGELOG.md` per the AGENTS.md versioning command when the user asks
  for a version; wizard MINOR bumps for each shipped milestone.
- Keep `waegis/version.py` payload-compatibility range in sync with the
  template version (T3.2 introduced the manifest — that is a
  backward-compatible **MINOR** template change: manifest added, no contract
  broken).
- Suggested version arc: M1–M3 → waegis 0.1.0 (engine+manifest+analyze),
  M4 → 0.2.0 (`new`), M5 → 0.3.0 (`adopt`), M6 → 0.4.0 (doctor/upgrade),
  M7 → 0.5.0 (self-contained), M8 → 0.6.0 (GUI), M9 → 0.7.0 (advisor).

---

## 14. Model & reasoning summary

| Work type | Model | Reasoning | Tasks |
|---|---|---|---|
| Architecture-bearing contracts, three-way merge, heuristics, packaging with OS edge cases, anything security-adjacent | Opus 4.8 (or Fable 5 if available) | high ("think hard" / max budget) | T1.1, T3.2, T4.1, T4.3, T5.1, T5.2, T6.2, T7.2, T7.3, T8.1, T9.1 |
| Well-specified implementation with a spec table in this plan | Sonnet 5 | medium ("think") | T1.2, T1.3, T2.1, T2.2, T3.1, T4.2, T4.4, T6.1, T6.3, T8.2, T8.3, T9.2 |
| Boilerplate, wrappers, docs, small commands | Sonnet 5 (Haiku 4.5 acceptable) | low | T0.1, T3.3, T5.3, T7.1, release tasks |

Practical notes for running these with Claude Code:

- One task = one session; start every session with the §12 standing block +
  the task row + the referenced plan sections. Do not batch two `high` tasks
  into one session.
- Use plan mode for the `high` tasks (review the proposed design against §4,
  §6, §7, §10 before any file is written).
- After each task, run `/code-review` (medium) on the diff before committing;
  for T3.2, T6.2, and T7.x run it at high effort — these three carry the
  data-loss risk (overwrites, deletes, self-replacement).

---

## 15. Risks and open decisions (repo-side residue of the analysis D-list)

| ID | Risk / decision | Disposition |
|---|---|---|
| D2' | GUI ratification | Console ships first regardless; GUI is M8 and skippable |
| D4' | Windows code signing for the packaged app dir | Open; RELEASE-MANIFEST sha256 ships from M7; signature field reserved in the release manifest |
| D6' | Manifest format ownership | Closed: defined here (§6), lives in this repo, MINOR template-side change |
| D8' | Step-catalog scope creep | Guardrail: new needs become new StepSpecs; engine mechanisms frozen after M1 without a plan amendment |
| D10' | Ubuntu 22 glibc floor for embedded CPython | Verify on a clean 22.04 VM inside T7.2, not after |
| D11' | `AGENTS.md`/`CLAUDE.md` collisions in adoption targets | Handled as guaranteed-conflict per-file decisions (§9); a real *merge* helper is deliberately out of scope for 0.x |
| D12 | Colocated-test repos need file-pattern write zones | Analysis flags it (§9); generator supports pattern-based zones; live fixture in T5.1 |
| D13 | WADORE integration contract drift | Frozen surfaces: CLI flags/exit codes (§5), manifest v1 (§6), `--json` schemas; breaking any of these is a wizard MAJOR bump |

---

## 16. Definition of done (acceptance vision, repo-scoped)

A person who has never set up a repository, on a fresh corporate Windows 11
laptop or Ubuntu 22 machine, can:

1. unzip one folder and start one program (after M7; before that: any machine
   with Python 3.11+ runs the `.pyz`);
2. answer plain-language questions and watch every step turn green with a
   verified check — for a brand-new project **or** an existing repository;
3. when blocked (no git, proxy, policy), receive a complete report they can
   forward to IT without understanding it themselves;
4. finish with a repo running the AEGIS workflow: payload installed and
   hash-verified, `workflow.toml` generated with the write-zone invariants
   guaranteed, gates captured (or loudly deferred), smoke tests green, changes
   committed, and — in adopt mode — the exact prompt to start the in-repo
   adoption workflow;
5. later, run `waegis doctor` to learn what drifted and `waegis upgrade` to
   move the repo to a newer AEGIS payload without losing local changes.
