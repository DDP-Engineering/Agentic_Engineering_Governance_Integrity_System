# AEGIS 0.13.0 delivery build - 2026-09-16

Rebuilt in place from the uncommitted working tree with the unchanged version
0.13.0: the three affected archives replace their predecessors under the same
names, and the version was deliberately not incremented. The delivery still
contains 13 archives: two core packages, ten host-integration packages and one
documentation ZIP. No AEGIS task workflow, commit, remote publication, model
call or real host-profile installation was performed.

The rebuild carries the configuration-documentation change: the packaged CLI now
names `[layout] default_branch` in the configuration it generates, the
installation guide gained a settings reference covering every key and its
default, the Folders & Files configuration table gained two keys, the CLI
reference states how the default branch resolves, and both affected decks were
updated to match.

## Construction

1. Ran `python 02_Tools/build_aegis_release.py --version 0.13.0`. The builder
   verified the 17-file managed payload, ran the complete product suite, and
   replaced the two core archives and the core publication record.
2. Rebuilt `AEGIS-Documentation-0.13.0.zip` from the complete `06_SoftwareDocu/`
   tree and the repository license under `aegis-documentation-0.13.0/`, using the
   builder's own deterministic archive settings.
3. Carried the ten host-integration archives forward untouched. None of their
   inputs changed: they embed no payload, and the only documentation they bundle
   is `Agent_Plugins.md`, `Project_Context.md` and `Plugin_Installation/`, none of
   which this change edits. Each was re-verified byte-for-byte against its
   recorded SHA-256 rather than rebuilt.
4. Used fixed 1980-01-01 archive member timestamps throughout. Recorded complete
   archive and source hashes, and rewrote both checksum files and the full
   manifest.

## Verification

- Product suite: **436 passed, 2 skipped in 167.32 seconds** on Windows, run by
  the builder before packaging. The skips concern Windows symlink semantics.
- The canonical payload verified at 17 files. Core archive inventories matched
  the staged tree, and the Linux tar.gz carries byte-identical content to the
  Windows ZIP.
- The rebuilt core archives contain the new `default_branch` default in
  `.agentic/aegis.py` and the updated guides under `docs/`. The documentation ZIP
  holds 46 files, eight PowerPoint decks and six installation PDFs, matching the
  previous inventory.
- The two updated decks were verified by inspecting their slide XML - package
  integrity, slide count, order, numbering and table geometry - not by rendering
  them. Visual rendering was not performed for this build.
- SHA-256 values cover every archive; the core record agrees with the full
  manifest, and the ten unchanged host archives matched their recorded hashes.
- Packaged JavaScript syntax, relative imports, host manifests and Linux launcher
  execute bits were not re-checked, because those archives were not rebuilt; the
  0.13.0 build of 2026-09-10 recorded them as passing.
- Native host installation, Desktop GUI acceptance, model-driven workflows and
  Linux execution were not run for this build. Package checks do not establish
  those forms of acceptance.

`SHA256SUMS` and `release-manifest.json` describe the core pair.
`DELIVERY_SHA256SUMS` and `delivery-manifest.json` cover all 13 archives with paths
relative to `07_Delivery/dist/`. The full manifest records 145 source-file hashes
because the source working tree is uncommitted; that set covers the shipping
sources and the JavaScript test harness, not the Python product suite.
Rebuilding does not install or publish these packages.

## Superseded local delivery

The 0.12.0 core, host and documentation archives and their delivery-record
directory were removed from `07_Delivery/` after the replacement was verified.
They remain recoverable in a temporary backup outside the repository. The root
changelog retains release history. Current delivery links and checksums refer
to 0.13.0 only. The three archives replaced by this rebuild carry the same names
as the ones they overwrote, so earlier copies are distinguishable only by their
recorded SHA-256 values.
