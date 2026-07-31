# WAEGIS V2 — Scope and Requirements

## 1. The safety model (replaces transactions)

The single biggest simplification. V2's rule set:

1. **Precondition, not recovery:** every mutating command on an existing repo requires a **clean git working tree** (no staged/unstaged changes). If dirty, refuse with the exact message: what is dirty, and that the operator should commit or stash first. Override: `--allow-dirty` (prints a one-line warning that git restore is then partial).
2. **Git is the undo:** on any failure mid-write, V2 prints the exact restore commands (`git checkout -- <paths>` / `git clean -fd <new paths>`) and, when the tree was clean at start, offers to run them itself. For `waegis new` (fresh directory) the undo is "delete the directory" — stated, offered.
3. **Idempotent re-run is the resume:** every command computes its plan from current on-disk state (manifest + drift), so running it again after an interruption naturally does only the remaining work. No journal needed.
4. **One trivial concurrency guard:** a `O_EXCL` lockfile under `.agentic/` per repo, deleted on exit, age-checked (stale after 1 h with a printed override hint). Nothing more.
5. **Payload integrity stays:** the shipped payload archive is still hash-verified on extraction (cheap, real supply-chain value), and copied files are hashed **once** — into the manifest — with no re-verification pass.

## 2. Commands (CLI-compatible surface)

### `waegis new TARGET` and `waegis adopt TARGET`
Thin aliases over one shared install flow; `new` additionally creates the directory and runs `git init` + initial commit; `adopt` additionally runs repo analysis to pre-fill the interview and applies conflict handling.

Flow: resolve+verify payload → (adopt) clean-tree check → (adopt) analyze repo, propose answers → interview ([03_Interview_UX.md](03_Interview_UX.md) style; `--answers` file and `--non-interactive` honored exactly as V1) → show plan (files to copy, conflicts and their decisions, config summary) → consent (`--yes` / `--dry-run` as V1) → copy payload (conflicts: keep-local / take-payload / write-new sidecar, asked per file or supplied via answers, exactly V1's vocabulary) → generate `workflow.toml` → write manifest → (new) initial commit / (adopt, optional per answer) commit → smoke check (`aegis run status` answers) → report.

### `waegis analyze --repo PATH`
Unchanged in behavior: read-only manifest state + drift + analysis proposals, human and frozen `--json`. Harvested nearly as-is.

### `waegis configure --repo PATH`
Re-interview of owned `workflow.toml` fields (stored answers → analysis proposals → defaults precedence, exactly V1), regenerate owned fields only (comment-preserving generator, harvested), optional gate/smoke re-run per answer, manifest configuration metadata updated last. Failure: git-restore guidance instead of transaction rollback.

### `waegis check --repo PATH` (alias: `doctor`, kept for compatibility)
The 80/20 of V1 doctor at ~15% of its size: manifest valid/absent/legacy, drift list, `workflow.toml` parses and roots exist, wrappers answer `--help`, hook files present + node resolvable (warn), last-install completeness *derived from manifest presence* (no journal). Same ok/warn/fail per finding, same 0/1/2 exit contract, same `--json` shape minus the journal group (additive-compatible).

### `waegis repair --repo PATH`
Restore missing/drifted **managed** files from the payload (never operator-owned conflict-kept files), regenerate generated files, rewrite manifest. Reuses the install flow's copier in "repair" mode; clean-tree precondition applies.

### `waegis upgrade --repo PATH`
The three-way classifier is harvested verbatim (installed-manifest vs on-disk vs new-payload → auto-apply / keep-local / conflict / delete / add), same per-file conflict decisions, same refusal of cross-major jumps and manifest-less repos, same manifest-written-last ordering, same optional branch-and-commit git modes. What changes: transaction → clean-tree precondition + git restore; journal → none; `run_upgrade` internals rebuilt thin.

### `waegis repowise …` — decision point D1 (see §4)

### `waegis version`
Unchanged.

## 3. Non-goals (V2 will not do)

- No resume of a half-finished wizard (re-run instead — it's idempotent).
- No machine probes beyond: python version, git present, git identity set. No disk/OS/proxy/TLS probes; a failed copy or clone reports its own OS error.
- No enforcement ambitions: V2 is an installer, full stop.
- No schema-2 or pre-manifest migration beyond what V1 supports today.
- No editions machinery in code — Complete vs Core is a packaging-time content difference only.

## 4. Decision points (owner must ratify before Phase 1)

| # | Question | Recommendation |
|---|---|---|
| D1 | RepoWise in V2? | **Phase 7, optional.** Harvest `repowise.py` mostly as-is (self-contained, reviewed); until then V2 ships Core-only and `waegis repowise` prints "use waegis 1.x for RepoWise management". If AudioMancer needs Complete on day one, keep using V1 there — V2 parity does not block the deployment. |
| D2 | Where does V2 live? | `05_Software/waegis2/` beside V1, own pyproject, package name `waegis2`, installed command still `waegis` (only one is installed at a time). V1 is deleted from the repo only after the retirement criteria in doc 05. |
| D3 | Packaging | Plain `zipapp` + a SHA256SUMS file (~200-line build script). Drop embedded-CPython runtimes and the reproducible-archive framework; require Python 3.11+ on the operator machine (already required for AEGIS itself, so this costs nothing in practice). If byte-reproducibility is ever needed again, V1's `build_release.py` remains in git history. |
| D4 | Version numbering | V2 ships as **WAEGIS 2.0.0** (the CLI surface is compatible but the safety model is a breaking change of behavior). Payload compatibility stays `>=2.0,<3.0`. |

## 5. Requirements checklist (acceptance-level)

- R1: A repo installed by V1 1.1.0 is fully manageable by V2 (analyze, check, configure, repair, upgrade) with no migration step.
- R2: For identical answers, V2 `new`/`adopt` produce a byte-identical `workflow.toml` and a manifest V1 accepts as valid.
- R3: All `--json` envelopes parse against V1's shapes; exit codes preserve 0/1/2/3 semantics.
- R4: Every interview question follows the consequence style of doc 03; `--answers` files written for V1 remain valid.
- R5: A `kill -9` at any point during any V2 command leaves the repo recoverable by the printed git commands, verified by the crash tests in doc 05.
- R6: Source budget ≤ 5,000 lines (enforced by a structural test that fails the suite if exceeded — the anti-regrowth guard).
- R7: The AEGIS payload and its template are not modified by this project at all.
