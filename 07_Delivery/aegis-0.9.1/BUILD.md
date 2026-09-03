# AEGIS 0.9.1 delivery refresh - 2026-09-03

Rebuilt from the current working tree, including uncommitted implementation and documentation changes. The core version remains 0.9.1, dated 2026-09-02 in the changelog; the five host integrations remain Unreleased. This operation did not publish a release, change installed host profiles or modify product code.

The set contains 13 archives: two core payloads, ten host plugin archives (Windows and Linux for OpenCode, Codex, Pi, Qwen Code and Claude Code), and one documentation ZIP with 19 Markdown guides, eight PowerPoint decks, six installation PDFs and 11 figures. See the [delivery index](../README.md) for downloads and installation.

## Verification

- The standard core release builder ran the complete product suite: **387 passed, 2 skipped in 163.00 seconds**. The skips concern Windows symlink semantics and unavailable symlink creation.
- Verified all archive inventories and bytes against the assembled packages/current sources, and generated SHA-256 checksums for all 13 archives. Each host archive now carries its matching illustrated Markdown/PDF guide.
- Checked all 74 packaged JavaScript files for syntax, checked relative static imports, and matched every bundled shared library to its source. Every host includes `bridge.mjs`. No installed `runtime.json`, author-specific user path, local model or credentials were packaged.
- Extracted the core ZIP on Windows and core tar.gz on Ubuntu 24.04 under WSL; fresh temporary checkout initialization and JSON status passed on both.
- All five bridges from extracted Windows plugin ZIPs successfully read status from the temporary checkout.
- All five Linux plugin tarballs extracted successfully; POSIX launcher syntax and execute permissions passed. Linux bridge execution was not repeated: Node.js 22+ was absent from this WSL environment PATH.
- No local or remote models were called. Desktop GUI acceptance and model-driven end-to-end workflows were not run. This refresh does not extend earlier native host verification claims.

## Records

`SHA256SUMS` and `release-manifest.json` describe the core pair. `DELIVERY_SHA256SUMS` and `delivery-manifest.json` cover all 13 archives. Checksum paths are relative to `07_Delivery/dist/`. The complete manifest records the Git HEAD plus source-file hashes because HEAD alone does not represent the working tree.

The eleven obsolete build/probe folders were backed up before removal. A local cleanup record is kept outside the repository; old test-proof files were preserved in that backup. Fresh expanded plugin staging directories were removed after archive verification, leaving only distributable files in `dist/`.

## Installation-guide refresh

The 2026-09-03 documentation refresh used isolated Windows profiles to install and run `doctor` for OpenCode 1.18.18, Codex CLI 0.153.0, Pi 0.84.4 and Qwen Code 0.23.0. Claude Code was unavailable, so that guide shows current package inventory and JavaScript syntax evidence without claiming a new native install. No models or real host profiles were used. All 31 PDF pages were rendered and visually reviewed.
