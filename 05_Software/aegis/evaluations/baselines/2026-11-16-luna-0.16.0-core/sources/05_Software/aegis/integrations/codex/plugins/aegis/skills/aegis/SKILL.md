---
name: aegis
description: Follow an installed AEGIS software-development workflow, resume its task journal, arrange independent reviews, and track verification. Use in repositories with .agentic/aegis.py for changes that add or change a durable product rule (logic, data, security, performance, integrations, product-wide UI), or when AEGIS is requested. Not for bug fixes that restore intended behavior, local UI adjustments, refactors, or packaging, release, deployment and repository-maintenance-only work.
---

# AEGIS software workflow

Use the current Git checkout's `AGENTS.md`, `.agentic/AGENTS.md`, installed step files and task journal. They define the workflow. User instructions and existing authorization remain authoritative. The installed contract's Scope decides which changes AEGIS governs; make the others directly. The plugin supplies a local bridge; it does not replace those records or initialize missing governance.

Locate this plugin's `scripts/aegis.mjs` from the loaded skill path: it is `../../scripts/aegis.mjs` relative to this skill directory. Resolve it to an absolute path before running it; do not assume the current working directory is the plugin directory. Run with Node.js 22 or later. The bridge discovers Python 3.11 or later and Git; the installer pins runtime paths for Desktop.

Examples below use `<bridge>` for that absolute script path and `<repo>` for the actual checkout:

```text
node <bridge> status --root <repo>
node <bridge> resume --root <repo> --task TASK-<id>
node <bridge> read --root <repo> --task TASK-<id> --document step
node <bridge> check --root <repo> --task TASK-<id>
node <bridge> journal --root <repo> --task TASK-<id> --action pause --next "Accept the framed scope?"
node <bridge> run --root <repo> --task TASK-<id> --kind validate
node <bridge> job --root <repo> --id <returned-job-id>
```

Use argument arrays or proper shell quoting for paths and user text. Each invocation is stateless; provide `--task` wherever task context is required. Read [bridge operations](references/operations.md) when choosing other commands.

1. Inspect dirty changes and open tasks before writing. Resume an existing matching task; read its journal and verify branch alignment. Resolve checkpoint or autopilot from the journal and `[interaction]` configuration, defaulting missing or invalid autopilot to off. In checkpoint mode stop after every stage and present the installed choices. A request to continue never grants Git publication authority; AEGIS ends when validate closes the task, and commits, pushes and pull requests follow the repository's procedures and the user's instructions.
2. Edit Frame, Requirement coverage and Design natively and tick the Done checklist; write everything else through the bridge `journal` operation: `--action advance` finishes a stage, `pause` stops for the user, `log` and `ruling` record events and decisions, `verdict` records explicit review results. On compaction or a new session, reread the durable journal; never use a remembered summary as proof.
3. Implement and verify according to the installed workflow. Static `check` is not a test suite. Use `run --kind test --command <configured-name>` for configured verification and `run --kind validate` for final strict proof after candidate-changing work and review are complete.
4. Read `[review]` in `.agentic/aegis.toml`. When enabled, **delegate two independent reviews**: specification compliance and implementation quality. Prefer the installed `aegis-spec-review` and `aegis-quality-review` custom roles when exposed by the host. Otherwise spawn separate fresh agents with the corresponding prompt from [review instructions](references/review.md), explicitly requesting read-only work. Use the same task, scope and candidate digest for both; do not share verdicts until both reviews finish. Record their evidence and honor the installed correction-round limit.
5. The coordinator alone maintains records and starts/cancels verification. Reviewer use of the bridge must include `--role reviewer`. This flag is a cooperative guard, not authenticated identity. Custom roles request a read-only sandbox; live host overrides still govern actual permissions. Never claim a reviewer was isolated when its host did not enforce it.
6. A verification run returns immediately with a job ID. Inspect `job` before starting another run, including after context loss. Poll the existing job; preserve full log paths, executed commands, exit status, findings and `candidate_unchanged`. Missing proof, cancelled/interrupted work or changed candidates cannot count as a pass. Deliberate cancellation requires `job --action cancel --id <id>`. Never clear an uncertain lock without checking the recorded processes and output.
7. `journal --action advance` and `--action pause` print the summary; show it before details. State actual validation scope and unresolved limitations. If GUI behavior or a model-driven workflow was not exercised, say so.

If a required runtime, host feature or review agent is unavailable, report that limitation and follow the installed workflow; never fabricate a second verdict. Respect the user's model restrictions. The bridge and installer themselves make no model requests.

## Current project context

Read the installed contract's current-context guidance. At frame/resume, open
`.agentic/context/project.md` and relevant `.agentic/context/environment.md` sections
when present, then follow selected component and source/test references.
Older payloads may omit these files. Keep project/component documents and
active requirements/specs about current positive behavior. Draft/task records
hold proposals; journals and Git retain history. Preserve established contracts.
Update implementation and setup instructions as needed during build. Reconcile
component knowledge during validate before final review and proof; update
relevant facts earlier when another agent needs them for a handoff.
`.agentic/aegis.toml` remains canonical for configured commands and layout.

## Efficient verification

Use the repository's documented setup/readiness checks before testing in a new
checkout; do not repeatedly start full suites to diagnose missing tools or services.
Use focused native commands during build. On a payload whose `test --help` exposes
these options, preview with `python .agentic/aegis.py test --impacted --base HEAD --dry-run`, then request impacted testing with `no_fallback: true`
(or bridge `--impacted --no-fallback`). The project runner must actually honor
selectors; AEGIS does not translate test-framework syntax or guarantee a narrow run.
An unavailable selection requires a focused project command or deferred full proof,
not a claim that tests passed. Start full validation after candidate edits and
review; do not run a separate full suite immediately beforehand. Preserve the
installed final-proof contract and rerun when the final candidate changes.
For evolution, `compact: true` (bridge `--compact`) omits hashes from the response
while preserving complete saved evidence. These options are opt-in; with an older
payload, use native focused commands and its supported evidence format.
Reuse unchanged instructions in an intact session, keep State fields short, and
poll the existing job at useful intervals instead of launching duplicate suites.
