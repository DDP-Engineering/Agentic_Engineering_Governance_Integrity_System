# AEGIS 0.16.0 delivery build - 2026-11-16

Local build from `master` commit `835ce7215edb74d8dc98a82373e09529fc4e6e12`,
plus the uncommitted source changes listed in delivery-manifest.json and
preserved in source-preparation.diff. Those changes were then committed
unchanged as `18f556b`, whose tree is the packaged source: its 149 file diffs
against `835ce72` match the recorded ones byte for byte. The source version is
0.16.0 and its CHANGELOG.md release date is 2026-11-16.
Packaging is a repository operation, so no AEGIS task journal was used.
Maintainer planning stays outside the delivery archives; its hashes are in the
manifest.

source-preparation.diff covers every listed change except the replaced
evaluation baselines under `05_Software/aegis/evaluations/baselines/`. They
are development records outside every archive, and each baseline carries its
own integrity.json. The diff also holds the six record files of this folder
that existed when it was written.

## Construction

1. `py -3.12 02_Tools/build_aegis_release.py --version 0.16.0` verified the
   18-file payload, ran the complete product suite and wrote the core pair with
   SHA256SUMS, release-manifest.json and RELEASE.md.
2. `node 02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>`
   assembled the five host packages. Each received the plugin installation
   collection, Agent_Plugins.md, Project_Context.md and a host-specific
   INSTALLATION_GUIDE.md linking its Markdown and PDF guide.
3. Host trees are archived with their aegis-<host> prefixes, fixed 1980-01-01
   timestamps and executable install.sh launchers, as one Windows ZIP and one
   Linux tar.gz per host. The documentation ZIP contains the 06_SoftwareDocu
   guide tree plus the license.
4. SHA-256 covers all 13 archives; archive-inventories.json records every
   member hash.

## Verification

- Product suite, run by the official builder: **521 passed, 2 skipped in
  201.32s**. The two skips are symlink cases that Windows does not support.
  BUILD_TESTS.txt retains the complete builder output.
- Core: 18 managed payload files and 35 members in each archive, every payload
  and guide member byte-identical to the current sources. The packaged CLI
  compiles, and `--help` and `--version` succeed at 0.16.0.
- Host inventories: OpenCode 48, Codex 50, Pi 48, Qwen Code 52, Claude Code 57,
  every member byte-identical to staging. All five host manifests report
  0.16.0 and each package carries the shared bridge.
- 75 packaged JavaScript files pass `node --check`; their 82 relative static
  imports all resolve.
- Documentation ZIP: 40 files, including eight PowerPoint decks and six
  installation PDFs. The 99 local Markdown links inside the delivered tree
  resolve; 12 more point to the source checkout, as the installation guides
  state. The slide XML of the eight decks has no quick-path, Handoff, Stage
  report or earlier-version terms.
- Every archive member path is relative and stays under its prefix. Linux
  install.sh is 0755 in both the ZIP and the tar.gz archives.
- No model calls, real host-profile changes, remote publication or
  installation during the build. Native host installation, Desktop GUI
  acceptance, model-driven workflows and Linux execution were not run.

The prompt evaluation of this payload is stored separately in
`05_Software/aegis/evaluations/baselines/`: subscription `gpt-6-luna` core
10/10 and capabilities 10/15 at medium reasoning, with the three new medium
failures passing on a high-reasoning rerun. No local-model evaluation of this
payload exists yet.

SHA256SUMS and release-manifest.json cover the core pair. DELIVERY_SHA256SUMS
and delivery-manifest.json cover all 13 archives, relative to ../dist/. All
build artifacts remain local; dist/ is ignored by Git. The 0.15.0
dist/SHA256SUMS it replaced was copied to the ignored
dist/.previous-builds/before-0.16.0-20261116T160200Z/ folder.
