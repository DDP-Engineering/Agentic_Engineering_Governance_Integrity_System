<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-8c12ef28 - Ship the CodeGraph plugin with the AEGIS release

stage: specify
type: feature
path: full
interaction: autopilot
requirements:
parent:
branch: ddp/codegraph-plugin-plan
base: 1aee86b4d4220e834f19ddedea42fa3f0a36e207
opened: 2026-10-04

## Done checklist (current stage)

- [ ] every in-scope behavior has exactly one requirement
- [ ] behavior inventory covers positive, boundary, failure, and recovery cases
- [ ] required fields filled and prose is self-contained
- [ ] independently variable or verifiable responses are split; inseparable
      atomic outcomes remain together
- [ ] each final requirement normally uses one "shall", in an EARS shape
      where one fits
- [ ] verification names setup, trigger, action, observable oracle, and a
      relevant boundary or failure
- [ ] `affected_paths` set to the best current guess
- [ ] specs written for exact contracts that the requirement cannot carry alone
- [ ] Requirement coverage maps every Frame outcome without overlap or gaps
- [ ] semantic conflicts, assumptions, and unknowns resolved or recorded
- [ ] journal `requirements:` line lists every ID
- [ ] `check` reports no format errors
- [ ] `stage: design`

## Frame

Problem: the AEGIS release does not deliver the CodeGraph plugin. The 0.14.0
Windows archive holds 34 files and no plugin (OBSERVED by listing
`07_Delivery/dist/aegis-0.14.0-windows.zip`), while the delivered
`docs/01_Install_and_Setup.md` says the commands need the plugin in
`.agentic/plugins/codegraph/` and that "its README covers installation" - a
README the archive does not contain. The builder also runs only
`05_Software/aegis/tests` before packaging (OBSERVED, `run_tests`), never the
plugin suite in `05_Software/aegis/plugins/codegraph/tests/`. (STATED finding
from the ADORE deployment, where the plugin had to be copied from source.)
Desired outcome: each release delivers the plugin as an optional add-on whose
own suite passed before packaging and whose archives are listed with SHA-256
in the publication record.
Actors: the maintainer who builds a release; a user installing AEGIS from the
delivered archives; agents in the user's repository.
Primary scenario: the maintainer runs `python 02_Tools/build_aegis_release.py
--version X` -> the builder validates both inventories, runs the product suite
and the plugin suite -> writes the core archives and the plugin package with
checksums and manifest entries -> a user extracts the plugin into
`.agentic/plugins/codegraph/` per its README and `know_graph_index` works.
Examples: the ADORE deployment (plugin copied from
`05_Software/aegis/plugins/codegraph/` without `tests/` and `ruff.toml`).
Counterexamples: a user who never enables CodeGraph should not have to carry
its parsers (9.9 MB of natives, OBSERVED) in their repository.
In scope: `02_Tools/build_aegis_release.py` (inventory, staging, suite gate,
archives, checksums, manifest, RELEASE.md rows, INSTALL text);
`05_Software/aegis/tests/test_release_builder.py`; requirements for shipping
the add-on and for the suite gate (REQ-REL-858e8cac, REQ-REL-59983fe5 cover
the core today); `06_SoftwareDocu/01_Install_and_Setup.md`,
`02_Tools/README.md`; the release-builder knowledge page, which has no
`## Routing` section (legacy) and needs reconciliation.
Out of scope: building or publishing a release (a repository operation);
`07_Delivery/README.md` and earlier publication records; the host integration
packages built by `02_Tools/build_agent_plugins.mjs`; refreshing vendored
parsers.
Constraints: archives stay deterministic (REQ-REL-59983fe5); the core
`.agentic/` payload stays standard-library only (REQ-PLAT-e675406e), so the
natives cannot go inside it; plugin files are copied byte for byte, because a
changed plugin file invalidates an index (plugin identity, CodeGraph spec);
Linux `.so` files keep usable modes in tar; Windows and Linux builds.
Success signals: a release build produces the plugin package with exactly the
canonical plugin files minus tests and lint config (automated); a failing
plugin suite stops the build (automated); extracting the package into a
fresh repository and running `know_graph_index` succeeds (automated with a
temporary repository, or manual).
Evidence: STATED - the request. OBSERVED - archive listing; `stage_tree`,
`EXPECTED_PAYLOAD`, `run_tests` in the builder; requirement texts; plugin
`vendor/` sizes (Windows `.pyd` about 1.4 MB, Linux `.so` about 8.8 MB); the
plugin README install steps. INFERRED - a repository is often shared by
Windows and Linux machines, so a package must carry both platforms' natives.
UNKNOWN - plugin suite duration inside the release gate.
Assumptions: one plugin package serves both platforms (both natives), shipped
in both the ZIP and tar.gz formats like the core.
Unknowns: whether host integration packages should later carry the plugin.
Decision-blocking questions: (1) packaging form - answered: separate add-on
archives (RULING-002). Options were: separate add-on archives
next to the core ones (recommended: core stays small, no conflict with
REQ-PLAT-e675406e); an optional `plugins/codegraph/` folder inside the core
archives (one download, but every core download grows by several MB); or
inside the core `.agentic/` payload (not recommended: conflicts with
REQ-PLAT-e675406e and installs natives into every repository).
Proposed behaviors: the builder verifies the plugin inventory, runs the plugin
suite, writes the plugin package in the chosen form with deterministic
contents, and records it in SHA256SUMS, release-manifest.json and RELEASE.md;
INSTALL text and the setup guide say how to install it.
Path and reason: full - new delivery output and gate, no requirement covers
shipping the add-on.

| criterion | yes | no | evidence |
|---|---|---|---|
| no new externally observable behavior | | no | new release package |
| no new interface or data format | | no | new archives and manifest entries |
| no new dependency | yes | | none |
| an existing requirement covers the behavior | | no | release requirements cover the core payload only |
| no security- or data-handling change | yes | | packaging only |

## Requirement coverage


## Design


## Log

- 2026-10-04 frame: full path (new delivery package and suite gate); packaging form and scope awaiting the user.
- 2026-10-04 frame: scope accepted by the user with separate add-on archives (RULING-002); queued third; interaction autopilot up to delivery (RULING-001); full path.

## Rulings

- RULING-001 | date=2026-10-04 | decision=interaction autopilot up to delivery; stop only for delivery approval | reason=user choice when accepting the three CodeGraph follow-up frames | source=user | supersedes=none
- RULING-002 | date=2026-10-04 | decision=ship the plugin as separate add-on archives (ZIP and tar.gz) next to the core archives, with their own checksums; the core payload is unchanged | reason=user answer to frame question 1 | source=user | supersedes=none

## Handoff


current: specify
status: ready
next: After TASK-2bb6095f reaches delivery: write the release requirements (specify).
must_read: 02_Tools/build_aegis_release.py, .agentic/requirements/reliability/REQ-REL-858e8cac.toml
blockers: none

## Stage report


stage: frame
result: completed
current: specify
changed: journal frame card only
evidence: ADORE trial transcripts and repository inspection (no tests run at frame)
issues: none
next: specify - write the requirements
needs_user: no (autopilot, RULING-001)
spec_compliance:
implementation_quality:
review_round:
