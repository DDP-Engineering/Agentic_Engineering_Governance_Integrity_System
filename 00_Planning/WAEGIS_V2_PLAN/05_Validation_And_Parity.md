# WAEGIS V2 — Validation, AEGIS Acceptance, and V1 Retirement

V2 has no V1 output-parity requirement. V1 is used only as the recorded source
of selected proven algorithms, a producer of migration fixtures, and the
shipping fallback until retirement. The bundled AEGIS payload, V2's explicit
schemas, ownership rules, and Git recovery contract are the acceptance oracles.

## 1. Test strategy

1. **Pure contract tests:** paths, inventory, ownership, manifest schema,
   classifier, answer validation, recovery plan, lock, and exit mapping.
2. **Ported algorithm tests:** V1 tests for harvested behavior, adapted only
   where the V2 contract deliberately differs and accompanied by a rationale.
3. **Fresh command tests:** dry-run/consent, conditional interview, JSON
   boundary, exact conflicts, clean-tree refusal, AEGIS validation, manifest
   last, and ownership-limited maintenance.
4. **Crash and acceptance tests:** real subprocess termination, exact Git
   restore, immediate rerun convergence, real payload wrapper, packaging, and
   cross-platform execution.

All ordinary tests are offline through injectable `CommandRunner`, `Asker`,
clock/lock metadata, home/cache path, and output streams. The full integration
matrix disables networking at the process/environment boundary.

## 2. AEGIS acceptance matrix

Every generated install invokes the actual copied wrapper. `config validate
--json` must return 0 and the stable configuration envelope. `run status
--json` is healthy when it returns either an active-run envelope or the expected
fresh-install `RUN-POINTER-MISSING` error. V2 never creates a fake run to make
smoke pass.

| Scenario | Required assertions |
|---|---|
| `new` into an absent target, all defaults | WAEGIS alone created the directory; Git initialized; no commit/index mutation; payload inventory exact; config validate and coherent-status smoke pass; manifest schema 2 written last |
| `adopt` into clean Python and JavaScript repos | Evidence-backed proposals; dry-run writes nothing; all adapter payload paths are classified; config validates; no pre-existing unrelated byte changes |
| Adopt conflicts for managed, generated, seeded, and root adapter files | keep-local/take-payload/sidecar outcomes exact; no global overwrite default; sidecar never collides; manifest dispositions match decisions |
| Adopt over a V1-installed fixture | Minimal V1 detector and explicit migration warning; V1 manifest data not trusted; every differing path uses normal conflict rules; V1 manifest recoverable through Git until V2 manifest is published last |
| Dirty adopt/configure/repair/upgrade | Staged, unstaged, untracked, nested, renamed, and ignored managed-destination cases refuse before consent or lock; no dirty bypass exists |
| Configure two ordinary fields and quick policy add/remove | Only explicitly owned bytes change; comments, advanced keys, gate timeout, `impacted_command`, and non-owned values remain byte-identical; AEGIS validates after each change |
| Analyze/check JSON on absent, healthy, warning, drifted, invalid, and V1 fixtures | V2 golden envelopes; read-only byte identity; check codes 0/1/2; version readback and guidance exact |
| Repair missing/drifted managed files | Approved managed paths restored; generated, seeded, kept-local, sidecar, requirements, components, knowledge, reports, runs, and workspace state untouched |
| Upgrade with every classifier/ownership row | Exact per-file action; project-owned trees preserved; V2 manifest last; config/smoke pass; payload and WAEGIS version readback correct; V1/invalid/incompatible cases refuse before mutation |
| Zipapp with fresh profile and networking disabled | Internal inventory and published digest verify; payload resolves/extracts; install/check/upgrade work with Python 3.11+; absence or incompatibility fails before mutation with exact guidance |
| Windows x64 runtime bundle with system Python unavailable | Locked CPython verifies; launcher runs the identical payload-bearing zipapp with no duplicate payload tree; runtime pointer is atomically registered; installed AEGIS wrappers, install/check/upgrade, and pointer repair after bundle relocation behave as documented |
| Native Linux x64 runtime bundle with system Python unavailable | Same runtime, install/check/dry-run-upgrade/real-upgrade, recovery, pointer, and preservation results as Windows, allowing only documented path/launcher text differences |

Golden files pin schemas and stable text where text is a contract. They do not
replace semantic assertions. A golden update must be in the same change as the
documented contract change and explain why.

## 3. Crash and recovery matrix

The test harness starts from a clean committed repository, captures the complete
pre-operation tree and Git metadata, then terminates the WAEGIS subprocess after
each publication boundary:

- after lock acquisition and before the first payload write;
- mid-copy after at least one tracked overwrite and one exact new file;
- after `workflow.toml` publication but before AEGIS validation;
- after successful validation but before manifest publication;
- during upgrade additions, replacements, and removals;
- during atomic manifest replacement;
- immediately after manifest publication but before normal lock cleanup.

For each kill point:

1. recovery commands must already be present in flushed captured output (the
   structured stderr recovery record for JSON mode); no post-crash inference is
   accepted;
2. the test handles the dead-owner lock exactly as documented;
3. it executes the emitted Git commands verbatim, with no test-only cleanup;
4. tracked bytes/index and exact new-file absence match the pre-operation state;
5. an immediate rerun reaches the same tree and manifest as an uninterrupted
   run;
6. no branch or commit was created and no unrelated ignored file was removed.

Handled `OSError`, AEGIS validation failure, subprocess timeout, manifest-write
failure, and `KeyboardInterrupt` cases additionally assert automatic scoped
rollback and truthful reporting of rollback success/failure.

Concurrency tests cover two simultaneous V2 mutators, a live lock older than
the former one-hour threshold (must not auto-break), a dead-owner lock, invalid
lock metadata, and explicit `--break-lock`. Read-only commands never break or
mutate a lock.

## 4. Ownership-preservation matrix

The retirement gate is specifically about not losing project-owned state. Each
install and upgrade fixture contains unique sentinel bytes in:

- `.agentic/workflow.toml` advanced/operator-owned fields and comments;
- `.agentic/requirements/` and specification files;
- `.agentic/components.toml` and component knowledge;
- `.agentic/knowledge/` outside immutable payload documentation;
- `.agentic/reports/` and adoption reports;
- `.agentic/runs/` and `.agentic/.workspace/` state;
- existing adapter/root instruction files resolved as keep-local;
- unrelated tracked, untracked, and ignored repository paths.

Tests assert those bytes before and after repair, upgrade, failed operations,
recovery, and rerun. New payload files under a project-owned tree must have an
explicit ownership rule; an unclassified path fails the build and plan.

## 5. Independent review gates

After install, upgrade, and final integration phases, an adversarial review
traces the actual flow end to end and hunts for:

- writes before consent, lock, or clean-tree revalidation;
- incomplete write/recovery sets;
- unsafe pathspecs or broad `git clean` behavior;
- a manifest published before validation/smoke;
- trust in V1 ownership or stale answers;
- generated/seeded/kept paths entering managed repair/upgrade;
- archive inventory/extraction mismatches;
- JSON prompting or mixed stdout;
- Windows/POSIX divergence and acceptance blind spots.

Findings are resolved before the next phase or final go/no-go.

## 6. V1 retirement criteria

All criteria are mandatory:

1. Complete WAEGIS tests, structural guards, AEGIS acceptance matrix, crash
   matrix, and artifact verification are green on Windows.
2. Complete WAEGIS tests plus clean offline install, idempotent check, dry-run
   upgrade, real upgrade, recovery, adapter coverage, and version readback are
   green on one native POSIX runner.
3. The full AEGIS suite is green with the five WAEGIS-importing modules included
   and still importing the preserved `waegis` package path.
4. Two representative real repositories pass the replacement gate: clean
   install/adopt, idempotent actionable check, dry-run upgrade, real upgrade,
   exact project-owned preservation, recovery, every shipped adapter present or
   explicitly kept, and version readback. One is a V1-to-V2 adoption and one is
   a later V2-to-V2 upgrade.
5. The final D1, D3, D6, and D7 decisions are implemented: no RepoWise core or
   Git history automation exists; WAEGIS is 3.0.0 with AEGIS range
   `>=3.0.0,<4.0.0`; and the zipapp plus both Pythonless runtime bundles pass
   criteria 1, 2, and 4.
6. Root/WAEGIS/AEGIS/deeper documentation is updated to V2 behavior; copied
   template material is generic; V1 transaction/runtime guidance and ignore
   rules are removed only with active V2 integration; downstream
   `template/CHANGELOG.md` is empty.
7. Root changelog/version handling follows the repository's explicit release
   process, and the owner signs the V2 go/no-go record.

Until all seven hold, V1 remains the supported release-line installer. After
they hold, the V2 implementation is already the canonical `waegis` package;
there is no later package rename or sibling-tree cleanup.

## 7. Standing risks

- **Git recovery depends on the absolute clean-tree rule.** Any future dirty
  bypass invalidates the safety proof and requires a different backup design.
- **Hard-break migration cannot infer V1 ownership.** V1 adoption is deliberately
  more interactive; convenience must not become implicit overwrite authority.
- **The AEGIS range is major-bound.** Recheck schema fields, adapters,
  launchers, and ownership inventory for every bundled AEGIS 3.x update and
  boundary-test `>=3.0.0,<4.0.0`; never infer cross-major compatibility.
- **Three artifact forms can drift.** Build native bundles around the exact
  already-built payload-bearing zipapp, forbid a second payload tree, pin the
  digests in one release manifest, and run equivalent offline acceptance paths
  for all three.
- **Pythonless operation depends on a persistent bundle path.** The runtime
  pointer must be diagnosed and repaired after bundle relocation or deletion;
  installation documentation must tell operators to unpack native bundles to a
  stable location.
- **A checksum is not a signature.** Artifact authenticity depends on the
  publication channel unless a separate signing decision is made.
- **Copied configuration is strict.** WAEGIS must preserve advanced values but
  let the real AEGIS parser reject unsupported combinations before publication.
- **Scope regrowth remains likely.** The package boundary, ownership matrix,
  forbidden list, line guard, and mandatory integration phase are load-bearing.
