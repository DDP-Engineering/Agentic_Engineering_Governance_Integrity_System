# Project context and current-state documentation

AEGIS keeps shared project knowledge as a compact description of the current
checkout. Task journals, Git, and the changelog carry decisions and history;
context files and component pages carry current facts and routes to evidence.

## Files and ownership

| File under `.agentic/` | Format and contents | Owner |
|---|---|---|
| `context/project.md` | Markdown: purpose/users, responsibilities, supported operation, established constraints, implementation orientation, authoritative references | Project |
| `context/environment.md` | Markdown: toolchain, setup, configuration/services, readiness checks, build/run, verification, platform details, authoritative references | Project |
| `knowledge/<component>.md` | Markdown: current component routing, responsibilities, interfaces, invariants, behaviors, files | Project |
| `requirements/<category>/<id>.toml` | Structured behavior contract, status, verification and source/test links | Project |
| `specs/<id>.md` | Detailed behavior following the linked requirement's status | Project |
| `templates/project.md`, `templates/environment.md` | Generic authoring guidance and stable headings used by `init` | AEGIS payload |

Context uses ordinary UTF-8 Markdown. The CLI checks file presence for `brief`,
not a metadata schema. Stable headings make selective reading straightforward.
There is no per-task timestamp, version ledger, or history section to maintain.
Empty sections are valid when evidence is not yet available.

`init` scaffolds each absent context file independently and strips the payload
license header and marked authoring notes. Existing bytes, including an empty
file, are preserved.
Upgrades replace managed templates and leave project context owned by the team.
Only generic templates ship to downstream projects; this repository's populated
context stays in its installed `.agentic/context/`.

## Creation and update lifecycle

| Point in the work | Context action |
|---|---|
| Installation | Create absent files with headings; supply no inferred project facts. |
| Frame / adoption survey | Read existing context and canonical sources; populate confirmed purpose, current implementation and reproducible setup within scope. |
| Specify / design | Keep proposed behavior in task records and draft requirements/specs; use current context to identify existing constraints. |
| Build | Update affected facts when implementation or setup actually changes. |
| Validate / adoption close | Reconcile affected context, component pages, and active contracts against the candidate and authorized intent before final proof. |
| Pause / resume | Keep progress in the journal; `pause` records the next action in its State. On resume, read the profile and relevant environment sections against the current checkout. |
| After another branch is integrated | Recheck affected claims against the combined tree; another branch's plans are not facts in this checkout. |

For a new project, start with confirmed purpose and available setup, and add
implemented responsibilities incrementally. For an existing project, inspect
the relevant source, tests, configuration and established documentation first.
Partial adoption is useful: missing context adds no gate or automated warning
that requires inventing content to proceed.

Each branch updates only the facts its implementation changes, section by
section, within its task's scope. Ordinary review and merge handle these shared
files alongside code. After integrating branches, recheck affected claims
against the combined tree. Avoid rewriting whole files or touching unchanged
sections merely to record that they were read.

## Writing current positive facts

An active requirement can say:

> The admin page shall display the project logo in its top-right corner.

Its component page can say:

> The admin header renders the project logo in its top-right corner.

Record the actual outcome once. Keep rejected alternatives, removed features,
before/after explanations, investigation notes, and superseded decisions in
task history. Express component boundaries as positive ownership assignments,
such as "The identity component authenticates sessions; the admin component
renders the authenticated workspace."

Positive wording preserves security, failure, privacy, and compatibility
semantics: "The endpoint returns 403 to callers without the required role" is
a current behavior, as is "Exports contain authorized records only." Tests
continue to exercise error and boundary cases. Semantic review, rather than a
ban on particular words, keeps these contracts meaningful.

Draft requirements/specs describe agreed proposed behavior explicitly as draft.
Activate them when implemented and verified; resolve open spec decisions and
keep their decision trail in the task journal. Retired requirement records
remain available for traceability and are excluded from current behavior
summaries. Existing historical records are preserved; reconcile relevant stale
prose when its area is touched.

An observed bug is evidence, not automatic permission to redefine an established
requirement. Adoption records suspected defects and evidence in the journal and
asks for clarification before activating a disputed new contract. Authorized
behavior changes update the current statement; Git retains the prior text.

## Evidence and bounded reading

Keep the project profile short. Link the selected component pages and relevant
requirements instead of embedding the complete register. Link existing README,
setup docs, manifests and scripts instead of creating parallel copies.
`aegis.toml` remains authoritative for configured commands, working directory,
timeouts and layout. The environment guide explains where to find and how to
use those definitions.

Describe required configuration names and provisioning routes; credentials
stay in approved secret stores. Portable setup belongs in the guide, while
machine-local paths, failed runs and verification outcomes belong in task evidence.
A documented setup step remains subject to the user's installation and network
authorization.

`brief` lists the two context paths with `present` or `not recorded` and reads
neither body. Presence means the file exists, not that its claims were verified.
Read the profile, then relevant environment sections and selected component,
requirement, source and test links. This keeps retrieval bounded and offline
without imposing a specific model or guaranteeing a context-window size.
