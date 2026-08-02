<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# WAEGIS Complete / RepoWise Delivery

WAEGIS Complete adds RepoWise 0.37.0 as a separate, optional AGPL sidecar. It
does not link RepoWise into AEGIS or WAEGIS and does not give RepoWise authority
over AEGIS state.

A Complete artifact produces the `offline-bundled-runtime` deployment
portability state (see `05_Software/waegis/README.md`'s "Deployment
Self-Containment" section and the template's `REPOWISE_INTEGRATION.md`): the
installed runtime beneath `.agentic/tools/repowise/0.37.0/<platform>/` is
gitignored, so a downstream Git clone alone does not restore it — only the
delivered working directory or a fresh Complete installer run does. Every
Complete artifact therefore carries the RepoWise license, its exact
corresponding source, third-party notices, SBOM, provenance, and hashes, as
listed below, so the runtime can be reconstructed and reviewed independently
of Git history. The RepoWise source checkout used as build input (for example
`D:\Source\repowise` above) stays outside `05_Software`; it is a clean tagged
checkout consumed only by the release builder and is never vendored into the
tracked AEGIS/WAEGIS source tree.

## Native Release Build

Use a clean checkout exactly at RepoWise tag `v0.37.0`:

```powershell
python 05_Software/waegis/packaging/build_release.py `
  --repowise-source D:\Source\repowise `
  --complete-target windows-x64
```

```bash
python 05_Software/waegis/packaging/build_release.py \
  --repowise-source /src/repowise \
  --complete-target linux-x64
```

The Complete target must match the build host. Build and smoke-test Windows x64
on Windows x64 and Linux x64 on Linux x64, then combine the two fixed-name
artifacts with the Core files and regenerate/verify publication checksums.
Target projects never compile native dependencies.

Set the same valid `SOURCE_DATE_EPOCH` on both native hosts. The builder
normalizes the generated SBOM timestamp and removes its random serial number;
the corresponding-source ZIP is rebuilt from committed blobs with the same
canonical ZIP metadata. With identical RepoWise commit, `uv.lock`, cached
wheels, runtime assets, Python patch, `uv`, zlib, and compression
implementation, each same-target Complete artifact is expected to be
byte-identical. Windows and Linux Complete archives contain different native
inputs and are not expected to equal each other. Builds made by different
Python/uv/zlib implementations are outside the byte-identity guarantee.

When the second native build reuses the first platform's fixed-name artifact,
the builder verifies that both bundle manifests identify the same RepoWise tag
and commit. A stale cross-platform companion is rejected.

The source must identify as project `repowise` version `0.37.0`, be at the exact
tag, and have no tracked or untracked changes. Release production may download
only pinned inputs. Use `--offline` once the runtime and wheel caches are fully
populated.

Both runtime locks are closed-schema documents. Targets must be exactly
`windows-x64` and `linux-x64`; assets are safe unique basenames; SHA-256 values
are exact hexadecimal digests; optional sizes are positive integers. Offline
cache hits perform no network call. Downloads use an exclusive unique sibling,
stream and fsync content, validate size/digest, and atomically publish without
removing an earlier cache object on failure.

## Required Complete Contents

Each Complete artifact contains:

- normal WAEGIS 1.1 and AEGIS 2.1 payloads;
- a separate native RepoWise 0.37.0 Python 3.12.13 runtime;
- locked, native-wheel-only dependencies;
- exact tracked RepoWise source ZIP, tag, commit, and SHA-256;
- RepoWise AGPL license and generated third-party notices;
- CycloneDX 1.5 SBOM;
- strict per-file bundle manifest, tree digest, and unpacked-size metadata.

The project-local installation is
`.agentic/tools/repowise/0.37.0/<platform>/`. A sidecar manifest and tree digest
verify it. Normal AEGIS payload manifests do not enumerate its runtime files.
The sidecar runtime is pinned separately from WAEGIS Core's Python 3.13
runtime because RepoWise locks NumPy 1.26.4, which has no Python 3.13 wheel.
The corresponding-source ZIP is generated from the pinned Git commit rather
than worktree bytes, so Windows and Linux packages carry byte-identical source.

## Offline and Security Checks

Before publication, verify:

- clean exact-tag source refusal;
- archive path traversal rejection;
- duplicate/case-colliding, undeclared, encrypted, linked, and special archive
  member rejection;
- exact internal manifest schema, target, membership, regular-file type, and
  per-file digest verification;
- disk-space failure before copy;
- native launcher/import and `--version`;
- install and deterministic indexing with non-loopback network denied;
- loopback-only Ollama behavior and deterministic fallback;
- hash, HEAD, and worktree-staleness detection;
- Core-to-Complete and Complete-to-Core policy transitions.

Bundled managed runtime denies non-loopback socket connections and disables
telemetry, editor/agent setup, update checks, package resolution, and cloud
provider discovery. External RepoWise remains operator-managed.

## Licensing Review

RepoWise declares AGPL-3.0-or-later. Before public or commercial combined
distribution, obtain legal review of the delivery arrangement and satisfy all
applicable source, notice, offer, modification, and network-use obligations.
Keep exact corresponding source and notices beside every Complete binary.

The generated SBOM and third-party notices are build evidence, not a substitute
for license or vulnerability review.

The full epoch, archive, cache, link-materialization, and two-build reproduction
contract is maintained in
`../06_SoftwareDocu/WAEGIS_RELEASE_REPRODUCIBILITY.md`.
