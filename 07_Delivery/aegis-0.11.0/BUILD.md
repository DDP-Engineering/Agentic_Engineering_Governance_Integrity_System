# AEGIS 0.11.0 delivery build - 2026-09-04

Built from the current working tree after assigning version 0.11.0. The
delivery contains 13 archives: two core packages, ten host-integration packages
and one documentation ZIP.

## Verification

- The standard core release builder completed the full product suite: **400
  passed, 2 skipped in 138.36 seconds**. The skips concern
  Windows symlink semantics.
- Verified every archive inventory and every packaged file byte against its
  assembled source, plus SHA-256 checksums for all 13 archives.
- Checked all 75 packaged JavaScript files for syntax and all
  82 detected relative imports. Every host includes `bridge.mjs`.
- Verified executable permissions on the Linux `install.sh` launchers.
- Regenerated and rendered all six release-specific installation PDFs.
- No model was invoked, no real host profile was modified, and no package was
  published. Desktop GUI, native host installation and model-driven workflows
  were not run.

`SHA256SUMS` and `release-manifest.json` describe the core pair.
`DELIVERY_SHA256SUMS` and `delivery-manifest.json` cover the complete delivery.
Checksum paths are relative to `07_Delivery/dist/`.
