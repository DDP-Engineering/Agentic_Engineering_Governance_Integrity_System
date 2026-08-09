<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light 0.2.0 Delivery Package

- **AEGIS Light version**: 0.2.0
- **Previous release**: 0.1.0
- **Built**: 2026-08-09
- **Runtime**: none embedded — requires Python 3.11 or newer on the target
- **Platform**: none — the two archives hold byte-identical trees and
  differ only in container format
- **Dependencies**: standard library only

This release completes the heuristic catalog at seventeen checks. Both
additions are advisory, in keeping with the product's rule that nothing
blocks the agent mid-flight; both are reported by `check` and neither
stops an edit.

**`stage-zone` (check 17, warning).** Each stage has a write zone beyond
`.agentic/`, which every stage may always write. The documentation stages
`frame`, `specify` and `design` write nothing else — they come before the
code is agreed — as do adoption's `survey` and `close`; adoption's
`components` phase may also write tests, because characterizing an
untested behavior is part of adopting it. `build` and `deliver` are
unconstrained. Source edited under a constrained stage is reported with
the file and the stage that owns it. In practice most hits mean the
journal's `stage:` line is stale rather than that the edit was wrong,
which is itself worth surfacing, because a stale stage breaks resume.
Zones are overridable per stage in a new optional `[zones]` table in
`aegis.toml`; an unrecognised zone name is reported by check 14 rather
than silently narrowing the stage. The check is diff-based, so without
git or a merge base it degrades to a single NOTE like its five peers.

**`manual-verification` (check 16, note).** A `verification` field that
begins `Manual:` or `Inspection:` **and names a method** records the
requirement as verified by hand instead of counting it among the tests
still owed. This closes a gap where `verification` was a required field
that no check consulted, and where a genuinely unautomatable requirement
— a look-and-see judgement, an install on clean hardware — had no way to
say so. It is emitted at NOTE level, and promotion applies only to
warnings, so such a requirement can never fail `check --strict` even when
`manual-verification` is listed in `[check] strict_promote`. That is
deliberate: it lets a team promote `no-linked-tests` hard without the
unautomatable requirements making the gate unpassable. The finding stays
printed and counted in every report, so the claims remain visible and
countable; whether a `Manual:` claim is honest is a review question, not
a CI one. A bare prefix naming no method buys nothing and still warns.

Existing installations need no configuration change: both defaults live
in the payload, and `init` never overwrites an existing `aegis.toml`.
Upgrading is the usual payload copy — `AGENTS.md`, `steps/`, `templates/`,
`aegis.py`, `LICENSE.txt` — and a review of the diff.

## Artifacts

| File | Bytes | Edition | Target |
| --- | ---: | --- | --- |
| `aegis-light-0.2.0.zip` | 74,220 | Payload | Any OS with Python 3.11+ |
| `aegis-light-0.2.0.tar.gz` | 56,891 | Payload | Any OS with Python 3.11+ |

Each archive holds the 13-file `.agentic/` payload, `INSTALL.md`, the
product `README.md`, `LICENSE.txt`, and the nine user guides under
`docs/`. The two formats are ergonomic, not different builds.

## Checksums

```text
69b2100f7b1511c2a529a93d8abbfa3e4b62835145e1e6aa9f6f7e0b23d9a550  aegis-light-0.2.0.zip
ddbbb1b4832e1889d27f44a5c29cffa290c64699755fea80cb09564e1e94cc7f  aegis-light-0.2.0.tar.gz
```

The binaries remain Git-ignored in `07_Delivery/dist/`. This tracked
record identifies the locally built release.

## Reproducibility

These digests are reproducible: the builder normalizes archive member
timestamps, ownership and modes, and writes the gzip container with a
fixed header MTIME and no embedded filename. Three consecutive builds
from the same sources produced identical checksums before this record was
written.

That last part is new in this release. Through 0.1.0 the builder created
the tar via `tarfile.open(..., "w:gz")`, which stamps the build clock
into the gzip header even though the tar members are normalized — so the
archive was reproducible in *content* while its *digest* changed on every
rebuild, which is the only form of reproducibility a release record can
cite. The 0.1.0 archives are therefore not byte-reproducible from source;
their recorded digests identify the artifacts as built on 2026-08-03.

## Verify

From the repository root:

```
python 02_Tools/build_aegis_light_release.py
```

The version defaults to the payload's own `VERSION`, so the archive label
cannot silently disagree with the CLI inside it. The builder verifies the
payload inventory against the expected 13-file set, runs the product test
suite (150 passed, 1 skipped) and refuses to package a red tree, then
rewrites `dist/` and this record. Compare the resulting `SHA256SUMS`
against the block above.

## Validation performed for this release

- Product suite: 150 passed, 1 skipped, on Python 3.12.10 / Windows 11.
- Payload inventory verified at 13 files; no adapter, policy or hook
  files present.
- Structural guards hold: no forbidden identifiers in `aegis.py`,
  standard-library imports only, `check` still exits 0 without `--strict`.
- Both new checks exercised end-to-end **from the extracted archive**, not
  only from the source tree: `stage-zone` fires on source edited during
  `specify` and is silent during `build`; `manual-verification` replaces
  the missing-test warning and survives `--strict` with both slugs
  promoted, while a requirement with no manual method still fails the
  promoted gate.
- Archive digests confirmed stable across three consecutive builds.
