# WAEGIS V2 — Architecture and Harvest Map

**Harvest source:** the exact WAEGIS 1 baseline commit recorded at Phase 1
start. It must include the 2026-08-07 fixes now present at HEAD. Harvest through
`git show <baseline>:<path>` after replacement begins; do not create a sibling
runtime package as a reference copy.

## 1. Package boundary

The runnable implementation remains:

```text
05_Software/waegis/
├── pyproject.toml          # project name and command: waegis
├── src/waegis/            # import package: waegis
├── tests/
├── packaging/
│   ├── build.py             # zipapp, inventory, release manifest
│   ├── runtime_bundle.py    # pinned CPython Windows/Linux bundles
│   └── runtime-lock.json    # exact sources, platforms, and SHA-256 values
└── README.md
```

V2 never imports V1 from another tree and never imports the deployed `aegis`
package at runtime. AEGIS is invoked only through the payload-local wrapper so
the exact copied implementation is the oracle.

## 2. Target modules and budgets

Budgets are guards, not implementation targets. A harvested file is trimmed to
the named behavior; it is not copied wholesale merely because the table names
it.

| Module | Origin | Budget | Responsibility |
|---|---|---:|---|
| `cli.py` | fresh | ~300 | argparse wiring, V2 commands/options, exit mapping, one-document JSON boundary |
| `install.py` | fresh | ~500 | shared new/adopt orchestration in the exact order from doc 01 |
| `configure.py` | fresh | ~275 | owned-field re-interview and validated publication |
| `check.py` | fresh | ~325 | manifest/drift, AEGIS-oracle, wrapper/hook/adapter findings |
| `repair.py` | fresh | ~150 | managed-file-only restoration through the shared apply path |
| `upgrade.py` | fresh shell | ~425 | V2 plan/consent/apply around the harvested classifier |
| `gitsafety.py` | fresh | ~250 | clean-tree/HEAD checks, exact recovery plan, automatic handled-failure rollback, one lock |
| `interview.py` | fresh | ~225 | conditional rendering over FieldSpecs and proposal provenance |
| `ownership.py` | fresh | ~150 | payload path disposition rules and project-owned preservation contract |
| `analyze.py` | harvest/trim `repo/analyze.py` | ~1,200 | evidence-backed language/root/gate proposals; remove V1 report/manifest coupling |
| `workflow_toml.py` | harvest/trim `repo/workflow_toml.py` | ~1,900 | schema-3 comment-preserving owned-field edits, quick policy, parse-back checks |
| `manifest.py` | harvest/redesign `payload/manifest.py` | ~650 | V2 schema 2, safe paths, one installed hash, drift, deterministic atomic JSON |
| `copier.py` | harvest/trim `payload/copier.py` | ~450 | inventory enumeration, staging, atomic copy, conflicts; no re-verification tier |
| `locate.py` | harvest/trim `payload/locate.py` | ~275 | explicit/bundled/checkout resolution and safe content-addressed extraction |
| `classify.py` | harvest from `commands/upgrade.py` | ~275 | pure three-way managed-file classifier and conflict decision normalization |
| `gitops.py` | small harvest subset | ~225 | status/HEAD/init/restore/clean only; no clone, branch, add, or commit |
| `prompts.py` | harvest/trim `io/prompts.py` | ~475 | FieldSpec, console/scripted askers, validators, conditional answer resolution |
| `answers.py` | harvest/trim `io/answers.py` | ~225 | closed V2 TOML/JSON answers schema and atomic optional answer export |
| `envelope.py` | harvest/trim `io/envelope.py` | ~125 | deterministic V2 result/error envelopes |
| `runner.py` | harvest `probes/runner.py` | ~250 | injectable argument-array subprocess seam |
| `toolchecks.py` | small harvest subset | ~100 | Python and Git prerequisite/version checks |
| `runtime.py` | harvest/trim | ~125 | select and atomically register the exact interpreter used by deployed AEGIS wrappers |
| `version.py` | harvest/redesign | ~100 | WAEGIS 3.0.0, manifest schema 2, and AEGIS `>=3.0.0,<4.0.0` |
| `__init__.py`, `__main__.py` | fresh | ~60 | stable package/version export and module entry point |
| `packaging/build.py` | fresh/trim | ~450 | zipapp, closed payload inventory, artifact/release manifests, SHA-256 publication |
| `packaging/runtime_bundle.py` | harvest/trim | ~500 | verify pinned runtimes and build Windows/Linux x64 bundles around the same payload-bearing zipapp |

The table leaves roughly 450 lines of core slack under the 9,500-line guard and
about 50 lines under the separate 1,000-line packaging/launcher guard. Phase
reports record actual totals for fresh, harvested, packaging, launcher, and test
code. RepoWise code is not hidden under either budget; any future lifecycle tool
requires a separate owner decision and budget.

### Distribution topology

Every release builds one payload-bearing `waegis.pyz`. It is published directly
for hosts with Python 3.11+ and is also copied byte-for-byte into:

- `waegis-windows-x64.zip`, with pinned CPython and a thin Windows launcher;
- `waegis-linux-x64.tar.gz`, with pinned CPython and a thin POSIX launcher.

The AEGIS payload occurs exactly once inside `waegis.pyz`. Native bundles do not
add V1's second loose payload tree; their only application payload is the exact
published zipapp.

The runtime lock has a closed schema and records the exact Python version,
platform, source filename/location, size, and SHA-256 for each runtime input.
An offline build consumes only already verified cached inputs; an approved
online build may fetch only the locked source. Runtime archives and final bundle
members reject traversal, links/special files, case collisions, duplicates, and
unexpected executables.

Each native launcher passes the bundled interpreter through
`WAEGIS_PACKAGED_RUNTIME`. Before a mutating install flow, V2 selects a valid
interpreter in this order: explicit `AEGIS_PYTHON`, packaged runtime, then the
compatible interpreter executing the zipapp. It atomically writes that exact
path to the established per-user `WAEGIS_HOME/runtime-python` pointer before
install/smoke. This lets deployed AEGIS shell, PowerShell, and Node wrappers use
the same interpreter; the native case works with no system Python. Moving or
deleting an unpacked bundle invalidates that pointer; read-only `check` reports
the condition and running a mutating command through the launcher from its new
persistent location repairs it. `version`, `analyze`, dry-run, and failed
precondition paths do not write the pointer. The zipapp neither creates a fake
runtime nor claims Pythonless support.

The three artifacts share WAEGIS version 3.0.0, payload version/range
`3.0.0`/`>=3.0.0,<4.0.0`, payload digest, payload inventory, and zipapp digest
in one release manifest. V2 requires deterministic membership and hashes, but
it does not restore V1's edition, SBOM, or byte-for-byte reproducibility
framework unless separately approved.

## 3. Manifest schema 2

The manifest is a deterministic JSON receipt at
`.agentic/install-manifest.json`. It is written atomically only after AEGIS
validation and smoke succeed.

Required top-level fields:

| Field | Contract |
|---|---|
| `manifest_version` | Integer `2`; distinguishes V2 from V1 |
| `product` | Exact string `aegis` |
| `payload_version` | Version read from the deployed payload |
| `payload_digest` | Digest of the verified build-time payload inventory |
| `installed_at` | UTC timestamp |
| `installed_by` | Exact WAEGIS version |
| `mode` | `new`, `adopt`, `repair`, or `upgrade` |
| `files` | Canonical path map of file records, sorted bytewise |
| `configuration` | Allowlisted normalized WAEGIS-owned answers, generator version, and generated workflow hash; never clone URLs, credentials, environment data, or arbitrary answers |

Each file record contains:

```json
{
  "sha256": "<lowercase hex>",
  "size": 123,
  "disposition": "managed"
}
```

Allowed dispositions:

- `managed`: WAEGIS may repair or three-way-upgrade the path;
- `generated`: WAEGIS created it from answers; only `configure` may rewrite it;
- `seeded`: created only when absent, then repository-owned;
- `kept-local`: an existing path the operator retained; WAEGIS never writes it;
- `sidecar`: payload content written to an explicit non-overwriting review path;
  it is reported but never silently promoted.

All file records keep the observed installed hash for audit and drift reporting,
but only `managed` disposition authorizes automatic maintenance. A path cannot
appear twice or collide by case. The manifest cannot list itself. Existing
symlink/reparse components, absolute/drive/UNC paths, `.`/`..`, repeated
separators, device-like names, or paths escaping the repository are rejected.

The golden manifest fixture pins field names, ordering, allowed dispositions,
normalization, and newline/indentation. It is not a substitute for explicit
schema validation tests.

## 4. Payload inventory and ownership

The build creates a closed internal inventory for every payload file after the
same exclusions used by installation. Each record has canonical path, byte
size, hash, and initial disposition. Runtime extraction rejects undeclared,
missing, duplicate, case-colliding, linked, special-type, or hash-mismatched
entries.

Ownership is explicit and tested:

- executable AEGIS CLI, shared hooks, adapters, shared skills, payload
  documents, and launch tools normally begin as `managed`;
- `workflow.toml` begins as `generated`;
- downstream `CHANGELOG.md`, component data, requirement records, coverage
  waivers, knowledge indexes/content, adoption reports, run history, and
  `.agentic/.workspace/` state are repository-owned or seeded and never
  silently replaced;
- an adopt conflict overrides the default: keep-local and sidecar decisions
  remain non-managed in the install manifest.

The exact path/pattern table lives in `ownership.py` and is covered by a test
derived from the real AEGIS template inventory. Any new payload path without a
classification fails packaging and installation tests.

## 5. Publication and recovery flow

All mutating commands reuse one library flow:

```text
validate target and clean HEAD
  → verify payload inventory
  → compute ownership/conflicts/write set/recovery set
  → preview and consent
  → acquire lock and revalidate clean HEAD
  → flush exact recovery record (stderr in JSON mode)
  → stage bytes outside repository
  → atomically publish exact files
  → invoke bundled AEGIS validation and smoke
  → atomically publish manifest last
  → release lock and report operator commit guidance
```

No file publication occurs during analysis, answers validation, dry-run, or
consent collection. A manifest from an earlier successful operation remains
the baseline until the new manifest is published.

## 6. What is dropped from V1

| V1 component | HEAD lines | Verdict |
|---|---:|---|
| `transaction.py` | 1,507 | Drop; clean Git + exact recovery plan replaces it |
| `engine/` | about 1,705 | Drop; plain sequential functions and rerun convergence replace it |
| V1 command implementations and `_shared.py` | about 10,700 | Drop as code; retain only domain rules explicitly named in this plan |
| network and machine probes | about 940 | Drop; direct command prerequisite failures are sufficient |
| `commands/doctor.py` | 1,180 | Drop as code; V2 `check.py` uses the narrower finding set and the AEGIS CLI oracle |
| `repowise.py` and command lifecycle | about 2,104 | Drop from core per final D1 decision |
| `packaging/build_release.py` plus runtime locks | 2,448 | Replace with the two focused builders and a small closed runtime lock; retain no edition/RepoWise/SBOM framework |
| lifecycle/runtime registration and repeated verification | about 490 | Retain only atomic runtime-pointer registration required by native bundles; drop generic lifecycle and repeated verification |
| clone, branch, stage, and commit Git helpers | subset of 659 | Drop per D7 |
| author/date/version docstring tags | n/a | Do not carry forward; follow current code style |

## 7. Dependency and testability rules

- Standard library only at runtime. Source and zipapp execution require Python
  3.11+; native bundles supply their pinned interpreter. Release-build inputs
  are limited to the locked runtime archives and approved build tooling.
- One-direction layering: `cli` → command orchestrators → shared apply/safety
  libraries → pure harvested helpers.
- Command modules do not import each other.
- `CommandRunner`, `Asker`, clock/lock metadata, and output streams are
  injectable. There is no event-sink framework.
- Runtime code never imports `aegis`, V1, tests, or repository planning files.
- All subprocess calls are argument arrays with `shell=False` and explicit
  timeouts.

## 8. Anti-regrowth tests

1. Core non-test Python source is at most 9,500 lines; the threshold may only
   decrease without owner approval.
2. Imports/names for HMAC, transaction, journal, step engine, network probes,
   clone, branch, stage, or commit automation are rejected.
3. `--allow-dirty`, `waegis2`, and runtime imports from `aegis` or V1 are
   rejected.
4. The manifest schema and golden fixture round-trip deterministically and
   reject unknown fields, unsafe paths, collisions, and invalid dispositions.
5. Every current AEGIS payload path has exactly one initial ownership class.
6. The built internal payload inventory exactly matches the staged payload and
   rejects a one-byte mutation, undeclared entry, missing entry, link, and case
   collision.
7. The recovery-plan generator accepts only the exact precomputed write set and
   always inserts `--` before pathspecs.
8. Packaging/launcher source is at most 1,000 lines; all artifact forms use the
   identical payload-bearing zipapp with no second payload tree, and
   runtime-bundle smoke tests pass with system Python deliberately unavailable.
