# WAEGIS V2 ("lite") — Plan Overview

**Date:** 2026-07-31
**Status:** PLANNED — not started. Independent of the AudioMancer deployment and of the AEGIS 2.1.0 release; V1 remains the shipping installer until V2 reaches parity (see [05_Validation_And_Parity.md](05_Validation_And_Parity.md)).

## Why a V2

Every review of WAEGIS 1.x reached the same conclusion: the tool works, is correct, and is roughly **2–3x larger than its behavior requires** (~24.7k source lines + ~2.4k packaging + ~22k tests). The surplus is defensive machinery — HMAC-signed transactions guarding a folder copy into a repo that git already protects, resumable journals for a 30-second operation, a corporate-network probe fleet, double and triple verification layers — built for threats the tool has never actually met. The cost is real: every change pays a navigation tax, and reviews found genuine bugs in the guidance path while the failsafe tier was being polished.

**The V2 thesis:** an installer for a git-based workflow tool may treat **git as the transaction layer**. Copy files, ask well-explained questions, write a manifest — and if anything goes wrong, the repository's own version control is the undo. Intelligence stays (analysis proposals, per-file conflict handling, three-way upgrade merge); armor goes.

## Target shape

| | WAEGIS 1.x | WAEGIS V2 target |
|---|---|---|
| Source lines | ~24,700 + 2,400 packaging | **≤ 5,000 + ~300 packaging** |
| Test lines | ~22,000 | ~6,000 (ported + parity) |
| Commands | new, adopt, analyze, configure, doctor, repair, repowise, upgrade, version | same names, same flags (CLI-compatible) |
| Crash safety | HMAC transactions, ownership records, locks, journal resume | clean-tree precondition + git restore; idempotent re-run |
| Machine probes | OS, disk, python, git, node, identity, proxy, TLS interception | python, git, git identity only |
| Verification | hash on extract + hash on copy + re-hash on verify + byte-compare | hash on payload extract; hash once into the manifest |
| Wizard engine | StepSpec catalog / topological runner / journal / event sinks | plain sequential functions |
| Packaging | reproducible tar/zip framework, embedded CPython, SBOM | zipapp + sha256 sums (decision point D3) |

## The decision: fresh or from current?

**Hybrid — fresh skeleton, harvested organs.** Neither extreme survives scrutiny:

- *Pure fresh* re-litigates genuinely hard, already-solved, already-reviewed problems: path-traversal safety in `manifest.py`, the comment-preserving `workflow.toml` generator with its parse-back invariants, the analysis heuristics, the three-way upgrade classifier ("textbook-clean" per review). Rewriting those would reintroduce the bug classes the 2026-07-31 review spent fifteen batches removing.
- *Pure evolution* cannot shed the architecture: the command layer is wired through transactions, journals, consent plumbing, and the step engine at every seam. Deleting the armor from inside V1 is more work, and more regression risk, than building a thin body and transplanting the proven organs.

So: a **new source tree** (`05_Software/waegis2/`) whose modules are either freshly written thin shells (~1.5k lines total) or **vendored copies of specific V1 files** taken essentially as-is (~3.5k lines), each listed with a keep/trim/drop verdict in [02_Architecture.md](02_Architecture.md). V1 is never imported — V2 is standalone — and V1 stays untouched in the repo until retirement.

## Frozen compatibility contracts (non-negotiable)

V2 must be a drop-in replacement for the repos V1 already installed:

1. **`install-manifest.json`** — byte-level schema compatibility, both read and write. V2 must manage a repo installed by V1 and vice versa.
2. **`workflow.toml` output** — schema-3, byte-identical generation for identical answers (same generator, harvested).
3. **`--json` envelopes and exit codes** — same shapes, same 0/1/2/3 meanings.
4. **CLI surface** — same command names and flags; `new`/`adopt` become thin aliases over one shared install flow, so every template document and skill referencing them stays true.
5. **Payload compatibility range** — same `>=2.0,<3.0` semantics.

## Explicitly forbidden in V2 (anti-regrowth list)

No HMAC/signed state. No ownership records. No journal-based resume. No cross-process lock machinery beyond one trivial lockfile. No network probes. No byte-compare-after-atomic-write. No double hashing of the same content in one flow. No step-engine/catalog abstraction. No editions beyond Core/Complete. Any future proposal to add one of these requires a written justification against a failure that actually occurred.

## Documents

| File | Contents |
|---|---|
| [01_Scope_And_Requirements.md](01_Scope_And_Requirements.md) | Command-by-command behavior spec, safety model, non-goals, decision points D1–D4 |
| [02_Architecture.md](02_Architecture.md) | Module map with line budgets; per-V1-file harvest verdicts (keep / trim / drop) |
| [03_Interview_UX.md](03_Interview_UX.md) | The consequence-style question catalog — every interview question drafted |
| [04_Implementation_Phases.md](04_Implementation_Phases.md) | Seven agent-ready phases with prompts, acceptance criteria, and model guidance |
| [05_Validation_And_Parity.md](05_Validation_And_Parity.md) | Test strategy, the V1↔V2 parity harness, and the retirement criteria for V1 |
