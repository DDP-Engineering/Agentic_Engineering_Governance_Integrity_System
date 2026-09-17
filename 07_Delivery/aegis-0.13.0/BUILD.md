# AEGIS 0.13.0 delivery build - 2026-09-17

Rebuilt in place from the uncommitted working tree with the unchanged version
0.13.0: the three affected archives replace their predecessors under the same
names, and the version was deliberately not incremented. The delivery still
contains 13 archives: two core packages, ten host-integration packages and one
documentation ZIP. No AEGIS task workflow, commit, remote publication, model
call or real host-profile installation was performed.

The rebuild carries two payload changes and the documentation that describes
them. `[review] max_fix_cycles` now accepts 0 through 255 instead of 0 through
5, so a repository may configure up to 256 total review rounds; the default
stays 2. A new `[records] commit_fingerprints` setting, `false` by default,
makes `init` maintain a managed block in the root `.gitignore` that keeps the
`TASK-<id>.anchor.json` and `TASK-<id>.evolution.json` sidecars out of Git, and
a new `fingerprints-tracked` check reports a repository whose tracked state
contradicts that setting. The advisory catalog is therefore 22 checks rather
than 21. AEGIS still performs no Git write: `init` prints the `git rm --cached`
command for a human to run.

## Construction

1. Ran `python 02_Tools/build_aegis_release.py --version 0.13.0`. The builder
   verified the 17-file managed payload, ran the complete product suite, and
   replaced the two core archives and the core publication record.
2. Rebuilt `AEGIS-Documentation-0.13.0.zip` from the delivered `06_SoftwareDocu/`
   tree and the repository license under `aegis-documentation-0.13.0/`, using the
   builder's own deterministic archive settings. The archive holds 46 members, as
   the previous build did.
3. Carried the ten host-integration archives forward untouched. None of their
   inputs changed: they embed no payload, and the only documentation they bundle
   is `Agent_Plugins.md`, `Project_Context.md` and `Plugin_Installation/`, none of
   which this change edits. Each was re-verified byte-for-byte against its
   recorded SHA-256 rather than rebuilt.
4. Used fixed 1980-01-01 archive member timestamps throughout. Recorded complete
   archive and source hashes, and rewrote both checksum files and the full
   manifest.

## Repository-only guide-tree file

`06_SoftwareDocu/10_Workflow_Overhead_Analysis.html` is a maintainer study of
workflow cost measured across three repositories. It lives in the guide tree but
is deliberately **not delivered**: it is absent from the documentation ZIP and
from the manifest's source-file set, and `00_Index.md` does not list it, so no
shipped document links to a file the recipient does not have. The documentation
package is therefore the delivered guide tree plus the license, not every file
present under `06_SoftwareDocu/`.

## Verification

- Product suite: **449 passed, 2 skipped in 171.02 seconds** on Windows, run by
  the builder before packaging. The skips concern Windows symlink semantics. The
  count rose from the previous build's 436 because this change added 13 tests
  covering the new setting, the managed ignore block and the new check.
- The canonical payload verified at 17 files. Core archive inventories matched
  the staged tree at 34 members each, and the Linux tar.gz carries byte-identical
  content to the Windows ZIP.
- The rebuilt core archives were opened and confirmed to contain the new
  `commit_fingerprints` setting, the `MAX_FIX_CYCLES_LIMIT = 255` bound, the
  `fingerprints-tracked` check and the `write_ignore_block` helper in
  `.agentic/aegis.py`, plus the updated guides under `docs/`, which still number
  13 Markdown files.
- The documentation ZIP holds 46 files, eight PowerPoint decks and six
  installation PDFs. Its packaged FAQ states the 22-check catalog, and neither its
  index nor the core archive's copy references the undelivered analysis page.
- Rebuilding the documentation ZIP from an unchanged tree reproduced identical
  bytes, confirming the deterministic archive settings.
- The three updated decks were verified by inspecting their slide XML - package
  integrity, well-formed slides, table row count and unchanged total table
  height - not by rendering them. Visual rendering was not performed for this
  build. The two settings tables each gained a `[records]` row while keeping
  their original 4,500,000 EMU height, so no table grew into the slide-number
  placeholder.
- SHA-256 values cover every archive. All 13 were verified against the files on
  disk, the core record agrees with the full manifest, and the ten unchanged host
  archives matched their recorded hashes.
- Packaged JavaScript syntax, relative imports, host manifests and Linux launcher
  execute bits were not re-checked, because those archives were not rebuilt; the
  0.13.0 build of 2026-09-10 recorded them as passing.
- Native host installation, Desktop GUI acceptance, model-driven workflows and
  Linux execution were not run for this build. Package checks do not establish
  those forms of acceptance.

`SHA256SUMS` and `release-manifest.json` describe the core pair.
`DELIVERY_SHA256SUMS` and `delivery-manifest.json` cover all 13 archives with paths
relative to `07_Delivery/dist/`. The full manifest records 145 source-file hashes
because the source working tree is uncommitted; that set covers the delivered
sources and the JavaScript test harness, not the Python product suite and not the
repository-only guide-tree file above. Rebuilding does not install or publish
these packages.

## Superseded local delivery

The three archives replaced by this rebuild carry the same names as the ones they
overwrote, so earlier copies are distinguishable only by their recorded SHA-256
values. The replaced 2026-09-16 artifacts were:

| Artifact | Superseded SHA-256 |
|---|---|
| `AEGIS-Documentation-0.13.0.zip` | `a87fd666507916837445c939ef221a7f9d4445328ce3acf8113fb5471207b497` |
| `aegis-0.13.0-linux.tar.gz` | `f8aacd41f98691ca994df1a46a87bad157852a2c46e397e817c2d8bea32a9942` |
| `aegis-0.13.0-windows.zip` | `b2b861740f4373a1e93be48d9ac7a4274151d34bb1ca0412af6df944539d1502` |

An intermediate set built earlier the same day included the analysis page in the
documentation ZIP and its index. That set was replaced within the same session
and was never recorded as a delivery; the values above remain the last
superseded state committed to this record.

The 0.12.0 core, host and documentation archives and their delivery-record
directory were removed from `07_Delivery/` after the 0.13.0 replacement was
verified. They remain recoverable in a temporary backup outside the repository.
The root changelog retains release history. Current delivery links and checksums
refer to 0.13.0 only.
