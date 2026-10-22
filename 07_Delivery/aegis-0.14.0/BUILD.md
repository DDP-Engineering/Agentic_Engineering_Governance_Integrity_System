# AEGIS 0.14.0 delivery build - 2026-10-22

Local rebuild from `master` commit `9e3d870cd1fe834a93e785008c69506bda954359`,
plus the delivery-preparation changes listed in delivery-manifest.json. The
source version remains 0.14.0 and its assigned release date remains 2026-10-20.
This build includes current Unreleased source changes; no version is assigned.
source-preparation.diff preserves the local documentation and test changes.
The build contains the current experimental prompt revisions. No own AEGIS
workflow was used. Maintainer planning is recorded in source-preparation.diff
and manifest hashes, and remains outside the downstream delivery archives.

## Construction

1. Verify that all packaged source hashes, the locally changed test hashes and
   HEAD still match the preceding tested build. Preserve all 13 previous archives
   and their records in the ignored backup named by the manifest's rebuild block.
   Use stage_tree, write_zip and write_tar from build_aegis_release.py to build
   the 18-file payload and current guides into a fresh core pair at 0.14.0.
2. `node 02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>`
   assembles the five host packages. Each receives the existing installation
   manual collection, Project_Context.md, Agent_Plugins.md and a host-specific
   INSTALLATION_GUIDE.md linking its Markdown and PDF.
3. Host trees are archived with their aegis-<host> prefixes, fixed 1980-01-01
   timestamps and executable install.sh launchers. The documentation ZIP contains
   the guide tree plus the license; the maintainer-only overhead study and
   evaluation harness are excluded. The delivered index omits the harness link.
4. SHA-256 covers all 13 archives; every archived file is compared with staging
   or current core sources. archive-inventories.json records every member hash.
5. This rebuild retains the successful software-suite result after the source
   identity checks above. The official full builder runs that suite for a normal
   release build; it was not invoked to repeat the unchanged suite in this rebuild.

## Verification

- Final official builder suite: **548 passed, 2 skipped in 420.54s**.
  This is the prior build result, retained for this identical-source rebuild;
  no software or test sources changed after that run.
- Initial suite: 3 failed, 548 passed, 2 skipped. Those tests assumed an AEGIS
  deployment in this repository, deliberately removed before the build. The user
  requested deleting those checks. The Claude protocol case and its Python
  wrapper, plus the two parametrized installed-CLI/reference cases, were removed.
  An intermediate run was interrupted for that requested change. The final full
  suite was run again; no failing test is silently excluded from its invocation.
  BUILD_TESTS_INITIAL.txt and BUILD_TESTS.txt retain both complete results.
- Core: 18 managed payload files, 35 members in each archive; packaged
  Python compiles and --help/--version succeed at 0.14.0.
- Host inventories: OpenCode 54, Codex 56, Pi 54, Qwen Code 58, Claude Code 63.
  Their manifests report 0.14.0 and the shared bridge is present in each package.
- 74 packaged JavaScript files pass node --check;
  81 actual static relative imports resolve, parsed without executing modules.
- Documentation: 46 files, eight PowerPoint decks and six installation PDFs.
  The preceding documentation refresh updated seven decks and rendered/inspected
  all ten changed slides. Package structure, reference fonts, slide counts and
  layout passed then. Their source hashes are unchanged; that QA is retained,
  without another render in this rebuild. Other PPTX entries remain byte-identical.
  Six unchanged PDFs and their unchanged installation sources remain current;
  all PDF pages have readable text. All 108 local Markdown links resolve.
- All 13 rebuilt archives preserve the preceding member inventories and bytes;
  12 archive hashes are identical. The documentation ZIP uses the archive helper
  metadata with unchanged content. All current SHA-256 checks pass. Linux install.sh
  permission bits are verified in both ZIP and tar.gz files.
- No model calls, real host-profile changes, remote publication or installation.
  Native Desktop acceptance, Linux execution and model-led workflows were not run.

SHA256SUMS and release-manifest.json cover the core pair. DELIVERY_SHA256SUMS
and delivery-manifest.json cover all 13 archives, relative to ../dist/.
All build artifacts remain local; dist/ is ignored by Git. Prior tracked build
records and all 13 archives were copied into an ignored backup before replacement;
the location is retained in the manifest's rebuild block. Earlier documentation
QA retains its own original backup reference separately.
