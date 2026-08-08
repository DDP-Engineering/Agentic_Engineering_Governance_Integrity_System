# WAEGIS 3 Technical Acceptance Report

Date: 2026-08-08
Branch: `ddp/waegis-v3-implementation`
Technical result: **PASS**
Retirement status: **pending owner go/no-go signature**

## Accepted product

- WAEGIS `3.0.0`, one stdlib-only package and command: `waegis`.
- Bundled AEGIS `3.0.0`; supported range `>=3.0.0,<4.0.0`.
- Manifest schema 2 with explicit managed/generated/seeded/kept-local/sidecar
  ownership.
- One payload-bearing zipapp plus Pythonless Windows x64 and Linux x64 bundles.
- No WAEGIS RepoWise lifecycle and no Git branch/stage/commit automation.

## Gate summary

| Gate | Result | Evidence |
|---|---|---|
| WAEGIS suite | PASS | 139 passed, 2 conditional skips, Ruff/compile/help clean |
| AEGIS suite | PASS | 638 passed, 3 conditional skips; five WAEGIS-importing modules included |
| Crash/recovery | PASS | Six install hard-kill points plus one real-payload upgrade point |
| Artifact integrity | PASS | Full build repeated byte-identically; closed manifest and checksums verified |
| Independent review remediation | PASS | F-01-F-13 scoped cleanup plus F-16/F-20-F-22; high-churn optional consolidation deferred |
| Windows native | PASS | No host Python; new/check/dry+real upgrade/check all green |
| Linux native | PASS | Ubuntu 24.04, no host Python; same path green with Node 24.18.0 |
| V1 representative replay | PASS | Untrusted V1 ownership ignored; 155-record schema-2 adoption; 3.1 upgrade; sentinel preserved |
| V2 representative replay | PASS | Dry/real 3.1 upgrade; project/workflow sentinels and all adapters preserved |
| Documentation/hygiene | PASS | AEGIS 3/WAEGIS 3 docs aligned; active transaction ignore removed; template changelog empty |
| D1/D3/D6/D7 | PASS | All four final owner decisions implemented and exercised |

The conditional skips are platform/filesystem tests guarded by explicit host
capability checks. They do not waive a retirement path: the corresponding
Linux, native-bundle, and cross-platform behavior passed separately.

## Independent review remediation

The 2026-08-08 adversarial review was triaged rather than applied wholesale.
The implementation includes F-01 through F-13 where applicable, plus F-16,
F-20, F-21, and F-22. F-14, F-15, F-17, and F-18 were deferred because their
cosmetic or safety-boundary churn did not correct an observed failure. F-19 and
F-23 through F-27 remain intentional or accepted limitations.

Four sequential Codex sessions produced one commit per batch. Independent
integration validation then passed 139 WAEGIS tests, all six install crash
boundaries, 638 AEGIS tests, Ruff, compilation, both CLI help surfaces, line
guards, the release verifier, and two byte-identical release builds. The native
and representative-repository scenarios were not repeated because the scoped
review did not change native launchers, the runtime lock, AEGIS payload bytes, or
migration classification; their original acceptance evidence remains recorded.

## Recovery proof

Each hard-kill subprocess had already flushed the exact path-scoped Git
recovery record. The acceptance harness executed those commands verbatim,
restored the exact original tree and clean index, required explicit breaking of
the proven-dead owner lock, and immediately reran successfully. Production code
contains no fault-injection hook. Handled failures and `KeyboardInterrupt`
continue to roll back automatically.

## Artifact identity

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `waegis.pyz` | 436,825 | `7301619a8ecdbea960b6704d798eaee8fc638a03d8a88befe90e16ba75719d0c` |
| `waegis-windows-x64.zip` | 23,403,980 | `2c48cc8a7e2b718e5e6382667e5d5cdb6244ba542afd2824de5f40e5e726c852` |
| `waegis-linux-x64.tar.gz` | 68,435,992 | `3021d9e3c5770faffa94216689e090474e56bf22bd572be56c909b69f9c8e627` |

The zipapp embedded by both native bundles is the published zipapp above. The
payload digest is
`c89a8d5b417c6a6152c24ce25b6ca4d94eb4c2cf2be5160a9ee37d858a846a83`.

## Structural result

- Core source: 26 files / 5,571 lines (limit 9,500).
- Packaging builder: 2 files / 579 lines (limit 1,000).
- Copied `template/CHANGELOG.md`: 0 bytes.
- Active `.agentic/.waegis-transactions/` ignore rule: absent.
- WAEGIS RepoWise core and Git history automation: absent.

## Conclusion

All technical retirement criteria are satisfied. The engineering recommendation
is **GO**. Criterion 7 remains formally open until the owner signs
`GO_NO_GO.md`. Until then, no release promotion or V1 retirement is claimed.

The complete machine-readable evidence is in `ACCEPTANCE_REPORT.json`.
