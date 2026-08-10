<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Release Scope

**Status:** Working draft  
**Product version:** 1  
**Last updated:** 2026-08-10  
**Source:** `AEGIS_PRODUCT_REQUIREMENTS.md`

## 1. Purpose

This document presents the release-oriented view of the priorities owned by
the Product Requirements Register. It explains what blocks the first usable
release and what may be delivered later without changing the product's central
promise.

The Product Requirements Register remains authoritative for requirement
meaning, priority, and status. This document does not assign, weaken, rewrite,
or replace any requirement.

## 2. Release thesis

The first usable release must prove the complete forward workflow:

> A developer installs AEGIS, pastes ticket text, and a human or AI agent can
> carry the work through Intake, Alignment, Requirement, Design, Check,
> Implementation, Validation, and Delivery with durable handoffs, truthful test
> evidence, impacted validation, and a clear outcome.

That workflow must be useful without configuration, remain non-blocking, work
offline, preserve repository ownership, and operate through both human-readable
artifacts and a stable machine interface. It must support Python 3.12 projects
using `pytest` or `unittest` on Windows 11 and Ubuntu 22.04 x86-64.

Adoption, upgrade execution, post-integration trace validation, and the
complete named host-adapter set remain part of the product direction. They do
not block the first usable forward-workflow release.

## 3. Priority rules

### Must

A `Must` requirement is a release condition. The initial release shall not be
declared complete while a `Must` requirement is absent, knowingly contradicted,
or lacks its required acceptance evidence.

`Must` includes:

- the ticket-to-Delivery workflow and truthful state model;
- non-blocking defaults, escape hatches, and developer control;
- durable snapshots, run isolation, scope evolution, and change attribution;
- requirement, test, file, and evidence traceability;
- red-before-green evidence and changed-test detection;
- offline operation, no data transmission, and non-invasive installation;
- the initial operating-system, architecture, Python, test-framework, and
  delivery-package commitments; and
- protocol, encoding, interruption safety, payload ownership, and product
  boundaries required for trustworthy everyday use.

### Should

A `Should` requirement is intended product functionality, but its absence does
not invalidate the core first release. A deferred `Should` shall be named in the
release record with its reason and intended follow-up; it shall never be
represented as delivered.

`Should` is used for the reverse adoption workflow, the complete named host-
adapter matrix, upgrade execution, post-integration trace validation,
optional specification authoring, and end-to-end air-gapped operation involving
separately selected third-party tools.

### Could

A `Could` requirement is optional expansion and is not part of the initial
release commitment. It may be implemented only after the `Must` release path is
coherent and usable. If present, it must still obey all applicable `Must`
requirements.

`Could` is limited initially to WAEGIS diagnosis and repair, opt-in preventive
write zones, and optional strict CI integration.

### Interpretation

- Priority applies to the complete requirement, including its exceptions and
  boundaries.
- A product boundary marked `Must` is a release condition even when it states
  something AEGIS shall not do.
- `Should` and `Could` mean deferred capability, not reduced truthfulness.
- A missing lower-priority capability shall be reported as unavailable or
  deferred, never simulated through invented evidence.
- Priority does not define implementation order. A small vertical slice may
  prove part of the `Must` set before the complete release gate is satisfied.

## 4. Requirement classification

The table reproduces all 226 priorities declared in the Product Requirements
Register. Each row supplies the common identifier prefix. Numeric entries are
the three-digit suffixes under that prefix; for example, `001-003` in the
`PR-ROLE` row means `PR-ROLE-001`, `PR-ROLE-002`, and `PR-ROLE-003`.

| Requirement area | Must | Should | Could |
|---|---|---|---|
| `PR-ROLE` | `001-007` | — | — |
| `PR-WORKFLOW` | `001-008` | — | — |
| `PR-RUN` | `001-007` | — | — |
| `PR-EVOL` | `001-005` | — | — |
| `PR-SNAPSHOT` | `001-004` | — | — |
| `PR-REPORT` | `001-003` | — | — |
| `PR-DELIVERY` | `001-004` | — | — |
| `PR-ART` | `001-004` | — | — |
| `PR-REQ` | `001, 003-004, 007-009` | `002, 005-006` | — |
| `PR-ADOPT` | — | `001-006` | — |
| `PR-DEFAULT` | `001-006` | — | — |
| `PR-POSTURE` | `001-006` | — | — |
| `PR-ESCAPE` | `001-010` | — | — |
| `PR-SUCCESS` | `001-005` | `006` | — |
| `PR-WAEGIS` | `001-002, 005-007` | `004` | `003` |
| `PR-SCOPE` | `001-009` | — | — |
| `PR-CONFIG` | `001-013` | — | — |
| `PR-PLAT` | `001-004` | — | — |
| `PR-RUNTIME` | `001-007` | — | — |
| `PR-OFF` | `001-006, 008-009` | `007` | — |
| `PR-MODEL` | `001-005` | — | — |
| `PR-PKG` | `001-009` | — | — |
| `PR-COMP` | `001-004` | — | — |
| `PR-TRACE` | `001-016` | — | — |
| `PR-RED` | `001-005` | — | — |
| `PR-INT` | `001-006` | — | `007` |
| `PR-ZONE` | `001-007` | — | — |
| `PR-COLLAB` | `001-008, 011` | `009-010` | — |
| `PR-PROTO` | `001-006` | — | — |
| `PR-ENC` | `001-004` | — | — |
| `PR-STATE` | `001-003` | — | — |
| `PR-HOST` | `003-004` | `001-002` | — |
| `PR-PAYLOAD` | `001-002, 004-005` | `003` | — |
| `PR-BOUND` | `001, 003-006` | — | `002` |

### Classification totals

| Priority | Requirement count |
|---|---:|
| Must | 206 |
| Should | 17 |
| Could | 3 |
| **Total** | **226** |

## 5. Deferred capability groups

### 5.1 Adoption — Should

The first release may govern new work in an existing repository without first
deriving the repository's complete current requirement and coverage model.
The structured Adoption workflow remains a later product increment for
progressively bringing pre-existing behavior under full traceability.

Covered requirements: `PR-ADOPT-001` through `PR-ADOPT-006`.

### 5.2 Upgrade execution — Should

The first release must establish payload and project-data ownership boundaries
that make later upgrades safe. Performing the upgrade is not itself required to
prove the first installation and forward workflow.

Covered requirements: `PR-WAEGIS-004`, `PR-PAYLOAD-003`, and the broader
lifecycle success measure `PR-SUCCESS-006`.

### 5.3 Host-adapter completion — Should

The machine protocol and adapter semantic rules are release conditions. The
complete adapter set for Claude Code, Codex, Qwen Code, OpenCode, and Pi may be
completed incrementally after the host-independent workflow is proven.

Covered requirements: `PR-HOST-001` and `PR-HOST-002`. The invariants in
`PR-HOST-003` and `PR-HOST-004` remain `Must` for every adapter that exists.

### 5.4 Post-integration trace validation — Should

The artifact design must avoid artificial cross-branch conflicts and must never
silently conceal genuine conflicts. Post-integration duplicate, link,
membership, and coverage checks in `trace-validate` may follow after branch-safe
artifact creation is working.

Covered requirements: `PR-COLLAB-009` and `PR-COLLAB-010`.

### 5.5 Optional hardening and operations — Could

The initial release deliberately excludes capabilities that add enforcement or
secondary operator functions:

- `PR-WAEGIS-003`: installation diagnosis and repair;
- `PR-INT-007`: preventive stage-scoped write zones; and
- `PR-BOUND-002`: strict AEGIS checks integrated into CI.

These capabilities shall remain disabled unless deliberately implemented and
selected by the team.

## 6. Initial release gate

The initial release is ready only when:

1. every `Must` requirement has an implementation or an applicable, explicitly
   documented non-software fulfillment;
2. every `Must` requirement has automated acceptance evidence or an explicit
   manual verification method appropriate to the behavior;
3. the complete ticket-to-Delivery path has been demonstrated on Windows 11 and
   Ubuntu 22.04 x86-64 with Python 3.12 projects using both `pytest` and
   `unittest`;
4. the dependency-including and dependency-excluding AEGIS and WAEGIS packages
   have been exercised offline;
5. interruption, unfavorable evidence, skips, waivers, scope revisions, dirty
   working trees, multiple recorded runs, and changed tests retain truthful
   outcomes; and
6. every deferred `Should` and `Could` requirement is listed accurately in the
   release record and is not represented as present.

Passing the release gate means the first release is a usable, truthful AEGIS
product. It does not mean that every future capability in the product direction
has been implemented.
