<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS Release Reproducibility and Archive Integrity

## Byte-Reproducibility Contract

For identical declared inputs and the supported build toolchain, WAEGIS expects
the following generated files to be byte-identical:

- `waegis.pyz`;
- Core Windows x64 ZIP and Linux x64 tar.gz application archives;
- Complete Windows x64 ZIP and Linux x64 tar.gz application archives;
- the RepoWise corresponding-source ZIP embedded in Complete;
- internal application and RepoWise bundle manifests, normalized SBOM, package
  metadata, launchers, notices, `release-manifest.json`, and `SHA256SUMS`.

The inputs are the repository and template file bytes, both runtime locks and
their pinned archives, the selected target/edition, the clean exact RepoWise
commit and `uv.lock`, the resolved locked wheels, and the canonical build
epoch. The supported toolchain must also be identical: Python patch version,
standard-library ZIP/tar/gzip behavior, `uv` version for Complete, zlib version
and compression implementation, and relevant target platform. A different
Python, `uv`, zlib, compression implementation, runtime asset, or wheel set is
outside the byte-identity promise even if it produces a functionally equivalent
archive.

With that constraint, Core target artifacts are intended to reproduce on a
Windows or Linux builder: the archive target, not the builder host, determines
names and modes. Each Complete target must still be built and smoke-tested
natively because it contains native wheels. A Windows Complete archive is not
expected to equal a Linux Complete archive; each same-target artifact is
expected to reproduce with the same native toolchain. The RepoWise source ZIP
is generated from committed Git blobs and is expected to match across both
native builds.

The generated release manifest and checksum file are deterministic binary
release assets. Gitea comments, publication times, signatures, HTTP headers,
and historical tracked publication records are outside the binary
reproducibility contract. Historical records are not rewritten.

## Canonical Build Epoch

The builder selects one epoch once and uses it for ZIP members, tar members,
the gzip header, normalized Complete SBOM metadata, and the release manifest:

1. `SOURCE_DATE_EPOCH`, when present;
2. the current source commit timestamp when the source is a Git checkout;
3. `1980-01-01T00:00:00Z` for an exported source tree without Git metadata.

An explicit value must contain only a non-negative base-10 integer. Malformed,
negative, non-integer, and values above `4294967294` fail with
`PackagingError`; explicit invalid input never falls back. Values before the
ZIP minimum are clamped to the 1980 epoch. The selected value is rounded down
to ZIP's two-second precision. The normalized value is then shared by every
archive format, including gzip, rather than using wall-clock or staging-file
times.

## Deterministic Archive Construction

ZIP and zipapp members are regular files sorted by canonical POSIX name.
Directory entries are omitted. Every member uses the same UTC timestamp,
Unix creator system, mode `0644` or explicitly derived executable mode `0755`,
deflate compression, and compression level 9.

The Linux artifact is an explicit GNU tar stream inside a gzip stream with an
empty header filename, compression level 9, and the canonical epoch. Root,
directory, and regular-file entries are sorted; uid/gid are zero; uname/gname
are empty; modes are `0755` for directories and declared executables and
`0644` otherwise. Links and special staging objects are not emitted. The
upstream standalone runtime's `python/share/terminfo/` database is omitted:
it contains case-colliding names that cannot be represented faithfully during
a Windows-hosted Linux cross-build, while the Linux target supplies its system
terminfo database.

Names use portable POSIX spelling. Empty, dot, traversal, absolute,
drive-qualified, UNC/device-like, control-character, backslash, duplicate, and
Windows-case-colliding names fail before publication. Generated manifests and
digests sort by those names rather than host-dependent `Path` ordering.

## Runtime Locks and Downloads

Both runtime locks use schema 1 and are closed. Required top-level fields are
`schema_version`, `provider`, `release`, `python_version`, and `targets`;
`reason` is the sole optional field. Targets must be exactly
`windows-x64` and `linux-x64`. Each target accepts only `asset`, `sha256`, and
optional `size`. Assets are unique safe basenames, digests are 64 hexadecimal
characters normalized to lowercase, and optional sizes are positive integers
(booleans are not integers for this contract). Lock data cannot add URL path or
query components.

A verified cache hit is returned without network access. `--offline` never
calls the transport and fails a missing or invalid cache entry. Online misses
stream into an exclusively created unique sibling, flush and fsync it, verify
size when declared and SHA-256 always, then atomically replace the cache path.
Network, write, timeout, validation, digest, interrupt, and exit failures remove
only that unique temporary and preserve the previous cache object.

## Exact Internal Verification and Publication

An application ZIP or tar contains exactly one
`<single-root>/archive-manifest.json`. The schema is exactly
`schema_version`, `target`, and non-empty `files`. The manifest is the only
regular member omitted from its own file table. Safe directory entries may be
present and are ignored after validation. Every other regular file must be
declared with a valid SHA-256 and every declared file must exist with matching
bytes. Undeclared files, duplicates, case collisions, encrypted ZIP entries,
links, devices, FIFOs, and unsupported types fail with `PackagingError`.

Runtime extraction validates the complete member and link graph before writing.
Safe relative `..` components may resolve within the extraction root because
the pinned runtimes use them; escaping traversal, absolute targets, unresolved
links, link parents, and cycles fail. Forward, backward, multi-hop file, and
multi-hop directory links are materialized as regular files/directories in a
deterministic order with executable metadata propagated.

Every output archive is written to an exclusive unique sibling and verified
there. `os.replace` publishes it only after verification, so failure leaves the
previous final artifact intact and removes the temporary. Release metadata uses
the same exclusive atomic publication pattern.

## Reproduction Procedure

Use one explicit epoch for all native builders:

```powershell
$env:SOURCE_DATE_EPOCH = "1785425602"
uv run python packaging/build_release.py --offline --output first

@'
import os
from pathlib import Path
for root in (Path("src/waegis"), Path("../aegis/template")):
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (946684801, 946684801))
'@ | python -

uv run python packaging/build_release.py --offline --output second
Get-ChildItem first -File | ForEach-Object {
    $name = $_.Name
    (Get-FileHash "first/$name").Hash -eq (Get-FileHash "second/$name").Hash
}
```

Run the command from `05_Software/waegis`. Cache paths may be supplied with
`--runtime-cache`. Complete builds additionally supply the same exact RepoWise
checkout, target, and `SOURCE_DATE_EPOCH` on each native host. The sidecar
manifest records that epoch, and a companion built with a different epoch is
rejected. After combining native companions, run:

```powershell
uv run python packaging/build_release.py --output second --verify-only
```

Hash equality across materially different Python/uv/zlib toolchains is an
informative comparison, not a supported guarantee.
