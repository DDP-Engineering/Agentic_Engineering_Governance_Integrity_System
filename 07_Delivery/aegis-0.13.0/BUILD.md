# AEGIS 0.13.0 delivery build - 2026-09-10

Built from the uncommitted master working tree with the assigned version 0.13.0.
Pending context and documentation changelog entries are included in this release.
The delivery contains 13 archives: two core packages, ten host-integration
packages and one documentation ZIP. No AEGIS task workflow, commit, remote
publication, model call or real host-profile installation was performed.

## Construction

1. Ran `python 02_Tools/build_aegis_release.py --version 0.13.0`. The builder
   verified the 17-file managed payload and ran the complete product suite.
2. Ran `node 02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>`
   to assemble five complete host packages using version 0.13.0.
3. Added the maintained installation-manual collection under each package's
   `docs/Plugin_Installation/`, with the project-context and agent-plugin guides
   under `docs/`. `INSTALLATION_GUIDE.md` links to that host's Markdown and PDF.
   Repository-wide source/build links in the full manuals refer to the AEGIS
   source checkout; no user profiles or runtime settings are included.
4. Archived each complete host directory under its `aegis-<host>` prefix as
   Windows ZIP and Linux tar.gz. Archived the complete `06_SoftwareDocu/` tree
   and license under `aegis-documentation-0.13.0/`.
5. Used fixed 1980-01-01 archive member timestamps and verified mode 0755 for
   Linux `install.sh` launchers. Recorded complete archive and source hashes.

## Verification

- Product suite: **435 passed, 2 skipped in 159.72 seconds** on Windows.
  The skips concern Windows symlink semantics.
- Canonical and installed core payloads compile. Packaged CLI help passes.
- All 13 archive inventories and file bytes match their assembled sources.
  SHA-256 values cover every archive; core records agree with the full manifest.
- All 74 packaged `.mjs` files pass JavaScript syntax checks, and all 81
  detected relative static imports resolve. Every host manifest reports 0.13.0
  and each complete package contains its shared bridge.
- The documentation package includes eight PowerPoint decks, six installation
  PDFs and current Markdown guides. These are unchanged from the preceding
  documentation refresh, which reviewed PDF rendering and PowerPoint consistency.
- Native host installation, Desktop GUI acceptance, model-driven workflows and
  Linux execution were not run for this build. Package checks do not establish
  those forms of acceptance.

`SHA256SUMS` and `release-manifest.json` describe the core pair.
`DELIVERY_SHA256SUMS` and `delivery-manifest.json` cover all 13 archives with paths
relative to `07_Delivery/dist/`. The full manifest records 145 source-file hashes
because the source working tree is uncommitted. Rebuilding does not install or
publish these packages.

## Superseded local delivery

The 0.12.0 core, host and documentation archives and their delivery-record
directory were removed from `07_Delivery/` after the replacement was verified.
They remain recoverable in a temporary backup outside the repository. The root
changelog retains release history. Current delivery links and checksums refer
to 0.13.0 only.
