# AEGIS 0.16.1 delivery build - 2026-11-17

Local build from `master` commit `166a0b9`, plus the uncommitted source
changes listed in delivery-manifest.json and preserved in
source-preparation.diff. The source version is 0.16.1 and its CHANGELOG.md
release date is 2026-11-17. Packaging is a repository operation, so no AEGIS
task journal was used.

The changes are not committed and nothing is tagged or published. Once they
are committed unchanged, that commit's tree is the packaged source.

## Construction

1. `python 02_Tools/build_aegis_release.py --version 0.16.1` verified the
   18-file payload, ran the complete product suite and wrote the core pair
   with SHA256SUMS, release-manifest.json and RELEASE.md.
2. `python 02_Tools/build_aegis_delivery.py --version 0.16.1` assembled the
   five host packages with `build_agent_plugins.mjs`, added the plugin
   installation collection, Agent_Plugins.md, Project_Context.md and a
   host-specific INSTALLATION_GUIDE.md to each, and archived every host as one
   Windows ZIP and one Linux tar.gz with fixed 1980-01-01 timestamps and an
   executable install.sh. It also wrote the documentation ZIP (the
   06_SoftwareDocu tree plus the license), dist/SHA256SUMS and the delivery
   records of this folder.

## Verification

- Product suite, run by the core builder: **529 passed, 2 skipped**. The two
  skips are symlink cases that Windows does not support. BUILD_TESTS.txt
  retains the builder output.
- All 13 archives pass `sha256sum -c` against dist/SHA256SUMS.
- Core: 36 members in each archive. The packaged CLI reports 0.16.1. The
  suite's archive test confirms that every relative link in the packaged
  README, changelogs and guides resolves inside the archive.
- Host inventories: OpenCode 48, Codex 50, Pi 48, Qwen Code 52, Claude Code 57.
  All five host manifests report 0.16.1.
- 75 packaged JavaScript files pass `node --check`. No packaged text file has
  CRLF line endings; the delivery builder refuses one.
- Linux install.sh is 0755 in both the ZIP and the tar.gz archives.
- Documentation ZIP: 40 files.

Not run: native host installation, Desktop GUI acceptance, model-driven
workflows, Linux execution, and a prompt evaluation of this payload. The
tracked evaluation baselines are for 0.16.0. Relative static imports of the
packaged JavaScript and the links inside the documentation ZIP were not
re-checked for this build.

SHA256SUMS and release-manifest.json cover the core pair. DELIVERY_SHA256SUMS
and delivery-manifest.json cover all 13 archives, relative to ../dist/. All
build artifacts remain local; dist/ is ignored by Git. The 0.16.0
dist/SHA256SUMS this build replaced was copied to the ignored
dist/.previous-builds/before-0.16.1-20261117/ folder.
