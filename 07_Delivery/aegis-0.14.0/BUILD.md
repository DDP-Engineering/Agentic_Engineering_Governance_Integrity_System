# AEGIS 0.14.0 delivery build - 2026-10-20

Built from the uncommitted `ddp/optional-diagrams` working tree, cut from
master `52e0772`, with the assigned version 0.14.0. The delivery contains 13
archives: two core packages, ten host-integration packages and one
documentation ZIP. No commit, remote publication, model call or real
host-profile installation was performed.

The release carries the optional `[diagrams]` setting. It is off by default and
off when missing. When enabled, design draws Mermaid diagrams of the proposed
implementation into `.agentic/tasks/diagram_TASK-<id>.md` for the human,
following the new `steps/diagrams.md` guide, and the design checkpoint shows
them. No stage, review or `check` finding depends on them, and no renderer is
bundled. The design `### Proposed architecture` diagram and the component-page
`## Architecture` diagram are no longer required. The managed payload therefore
has 18 files instead of 17.

This 0.14.0 is unrelated to the 0.14.0 archives built earlier on the CodeGraph
evaluation branch. Those archives were replaced here and kept in a backup
outside the repository.

## Construction

1. Ran `python 02_Tools/build_aegis_release.py --version 0.14.0`. The builder
   verified the 18-file managed payload, ran the complete product suite, and
   wrote the core archives and the core publication record.
2. Ran `node 02_Tools/build_agent_plugins.mjs --output <fresh-staging-directory>`
   to assemble the five host packages at version 0.14.0.
3. Added the maintained installation-manual collection under each package's
   `docs/Plugin_Installation/`, with the project-context and agent-plugin guides
   under `docs/`. Each `INSTALLATION_GUIDE.md` links to that host's Markdown and
   PDF.
4. Archived each host directory under its `aegis-<host>` prefix as a Windows ZIP
   and a Linux tar.gz. Archived the delivered `06_SoftwareDocu/` tree and the
   license under `aegis-documentation-0.14.0/`.
5. Used fixed 1980-01-01 member timestamps, and mode 0755 for Linux `install.sh`
   launchers. Recorded complete archive and source hashes.

## Repository-only guide-tree file

`06_SoftwareDocu/10_Workflow_Overhead_Analysis.html` is a maintainer study. It
is not delivered: it is absent from the documentation ZIP and from the
manifest's source-file set, and `00_Index.md` does not list it.

## Verification

- Product suite: **463 passed, 2 skipped in 220.28 seconds** on Windows, run by
  the builder before packaging. The skips concern Windows symlink semantics.
- The canonical payload verified at 18 files. Both core archives hold 35 members,
  including `.agentic/steps/diagrams.md`. The packaged CLI compiles and reports
  `aegis 0.14.0`, and its help works.
- Host-package inventories match the 0.13.0 layout file for file: OpenCode 54,
  Codex 56, Pi 54, Qwen Code 58 and Claude Code 63. Every manifest reports
  0.14.0, and each package contains its shared bridge.
- All 74 packaged `.mjs` files pass `node --check`, and all 81 relative static
  imports resolve. Linux `install.sh` launchers carry mode 0755 in both archive
  formats.
- The documentation ZIP holds 46 files, with eight PowerPoint decks and six
  installation PDFs, matching the 0.13.0 member set.
- Every deck and installation PDF reads 0.14.0.
  - The decks were edited and verified in their slide XML, not rendered.
  - In the PDFs, the version text was replaced inside the content streams and
    the cross-reference table was rebuilt. The digits share one Helvetica
    width, so the layout is unchanged. The PDFs were not visually rendered.
- SHA-256 values cover every archive. All 13 were verified against the files on
  disk, and the core record agrees with the full manifest.
- Native host installation, Desktop GUI acceptance, model-driven workflows and
  Linux execution were not run for this build.

`SHA256SUMS` and `release-manifest.json` describe the core pair.
`DELIVERY_SHA256SUMS` and `delivery-manifest.json` cover all 13 archives, with
paths relative to `07_Delivery/dist/`. The full manifest records 146 source-file
hashes because the source working tree is uncommitted. Rebuilding does not
install or publish these packages.

## Superseded local delivery

The 0.13.0 core, host and documentation archives and their delivery-record
directory were removed from `07_Delivery/` after the 0.14.0 replacement was
verified. They remain recoverable in a temporary backup outside the repository.
The root changelog retains release history. Current delivery links and checksums
refer to 0.14.0 only.
