# WAEGIS V2 — Architecture and Harvest Map

## 1. Target module layout (`05_Software/waegis2/src/waegis2/`)

| Module | Origin | Budget (lines) | Responsibility |
|---|---|---|---|
| `cli.py` | fresh | ~300 | argparse wiring, same commands/flags as V1; JSON-error envelope on parse failure |
| `install.py` | fresh | ~450 | the shared new/adopt flow: verify payload → analyze → interview → plan → consent → copy → generate config → manifest → commit → smoke |
| `configure.py` | fresh | ~250 | re-interview owned fields, regenerate, optional gate/smoke re-run |
| `check.py` | fresh | ~250 | doctor-lite findings + exit contract |
| `repair.py` | fresh | ~150 | copier in repair mode |
| `upgrade.py` | fresh shell + harvested core | ~400 | plan/consent/apply around the harvested classifier |
| `gitsafety.py` | fresh | ~150 | clean-tree check, restore-command builder, lockfile |
| `interview.py` | fresh | ~200 | consequence-style question renderer over harvested FieldSpecs (doc 03) |
| `analyze.py` | **harvest: `repo/analyze.py`** | ~1,550 | as-is; reviewed clean; only import-path fixes |
| `workflow_toml.py` | **harvest: `repo/workflow_toml.py`** | ~1,500 | as-is first (byte-compat generator is sacred); the triple-schema consolidation is a stretch task, only if parity stays byte-identical |
| `manifest.py` | **harvest: `payload/manifest.py`** | ~650 | as-is: path-traversal safety, hashing, drift, load/write — the compat contract lives here |
| `copier.py` | **harvest: `payload/copier.py`, trimmed** | ~450 | keep two-phase copy, conflict-hook contract, `resolve_managed_path` discipline; DROP re-verification passes and re-counting |
| `locate.py` | **harvest: `payload/locate.py`** | ~250 | payload resolution ladder + verified zipapp extraction |
| `classify.py` | **harvest: the `_classify` core + FileAction/decision types from `commands/upgrade.py`** | ~250 | the three-way merge classifier, extracted clean |
| `gitops.py` | **harvest subset of `repo/gitops.py`** | ~300 | init/add/commit/status/identity/branch + timeouts; drop clone if unused by the flows |
| `prompts.py` | **harvest: `io/prompts.py`** | ~450 | FieldSpec, askers, `default_value()`, answers precedence |
| `answers.py` | **harvest: `io/answers.py`** | ~250 | answers file load/save (V1-compatible) |
| `envelope.py` | **harvest: `io/envelope.py`** | ~115 | frozen `--json` contract |
| `runner.py` | **harvest: `probes/runner.py`** | ~200 | CommandRunner seam + subprocess impl |
| `toolchecks.py` | **harvest subset of `probes/tools.py`** | ~120 | python + git + identity checks only |
| `version.py` | **harvest** | ~90 | WIZARD_VERSION=2.0.0, payload range |
| `repowise.py` | **harvest (Phase 7, optional)** | (~1,200) | outside the 5k budget; only if D1 approved |
| `packaging/build.py` | fresh | ~200 | zipapp + SHA256SUMS |

Fresh total ≈ 1,750; harvested total ≈ 3,250 (trimmed). **Core budget ≤ 5,000** enforced by test.

## 2. What is dropped from V1, explicitly

| V1 component | Lines | Verdict and rationale |
|---|---|---|
| `transaction.py` | 1,530 | **DROP.** Sound but disproportionate (review verdict). Replaced by `gitsafety.py` (~150). |
| `engine/` (step, catalog, runner, journal) | ~1,625 | **DROP.** Detect/act/verify catalogs, topological ordering, resumable journals — replaced by sequential functions and idempotent re-run. |
| `commands/` + `_shared.py` | ~10,000 | **DROP as code; harvest knowledge.** The phase decomposition, consent semantics, exit-code mapping, and conflict vocabulary are re-expressed thinly; the classifier and FileAction types are harvested into `classify.py`. |
| `probes/network.py`, `probes/machine.py` | ~840 | **DROP.** Proxy/TLS/OS/disk probes out of scope. |
| `doctor.py` | 1,104 | **DROP as code**; findings list distilled into `check.py` (~250). |
| `packaging/build_release.py` | 2,451 | **DROP.** Replaced per D3; stays in git history if reproducibility is ever needed. |
| `lifecycle.py`, `runtime.py` | ~290 | **DROP.** Journal-resume discovery and packaged-runtime registration have no V2 counterpart. |
| Doxygen `@author/@date/@version` tags | — | Not carried over; V2 follows the post-sweep style rule from day one. |

## 3. Seams preserved for testability

The three injection seams that make V1's suite offline-capable are kept, because they cost almost nothing and buy everything: `CommandRunner` (subprocess), the `Asker` protocol (console/scripted), and stream injection for all output. No event-sink abstraction — commands write to their stream directly.

## 4. Dependency rules

- stdlib only, Python 3.11+ (unchanged).
- `waegis2` never imports `waegis` (V1) or `aegis`; harvested files are vendored copies with updated intra-package imports.
- One-direction layering: `cli` → command modules → (`install`/`upgrade` internals) → harvested libraries. No command imports another command; genuinely shared bits live in the library layer, not a `_shared` grab-bag.

## 5. Anti-regrowth guards (structural tests, written in Phase 1)

1. Total non-test source lines ≤ 5,000 (excluding optional `repowise.py`).
2. Forbidden-import test: `hmac`, `secrets`, `fcntl`/`msvcrt` (beyond the single lockfile helper), `ssl`, `winreg` must not appear in `waegis2`.
3. Forbidden-name grep: no `journal`, no `transaction`, no `StepSpec` identifiers.
4. Manifest schema round-trip test against a fixture generated by V1 1.1.0 (the compat contract, pinned forever).
