# AEGIS - FAQ

## What if the agent ignores the workflow?

The core is advisory. Its heuristics can expose inconsistent artifacts and
diffs, but cannot prove that an agent followed every instruction, performed
honest red testing, or created a journal for every task. Review the actual
records and candidate. Opt-in strict CI can reject errors/promoted warnings;
host integrations also apply their own bounded tool permissions and guards.

## What is AEGIS's operating model?

The current source combines five stage instructions (frame, specify, design,
build, validate), evidence-led idea capture, requirements, linked tests,
journals whose state the CLI writes, repository evolution, review policy and
a Python CLI. It guides and never blocks: `check` is an advisory report. It
covers software implementation; commits, pushes, pull requests, merges,
tickets, releases and packaging follow the repository's own procedures. Its
five host integrations add native entry points and shared verification jobs.
Core records live in Git; installed host resources and job caches also have
local state outside the repository.

## Which agents and models work?

The core needs an agent that can read files and execute the configured commands.
Native packages exist for OpenCode, Codex, Pi, Qwen Code and Claude Code. They
do not distribute credentials or select a model for another user. Bounded
stages and `brief` reduce context load; they do not guarantee compliance by a
particular model or at a specific context limit.

## Can I stop and resume elsewhere?

Yes. Transfer committed records using separately authorized Git operations.
Find the task with `status` if necessary, then run `brief TASK-<id>`. Confirm
the branch, read what its `Read next` line names - the current step file, then
the State `must_read` paths - and the full journal where the stage requires
it, and continue the first unticked action. Missing/stale/shortened state means
read more. A `summary` is recorded information, not fresh proof or approval.
Local verification jobs and uncommitted files do not travel with Git.

## What belongs in the task Log?

Only durable progress and evidence: stage transitions, material changes or
decisions, consolidated test results, blockers, approvals, deviations, and the
final validation result. `advance` writes the transitions, `test --task` a test
result, and `log` any other durable event. Frame, Requirement coverage, Design,
Rulings and State own their detailed information; the Log does not duplicate
them. Routine searches, edits, tool mechanics, corrected retries, and repeated
test attempts stay out. During build, retain one expected red and one final
green per meaningful behavior increment.

Project and component documents hold current positive behavior and actual setup.
Populate `context/project.md` and `context/environment.md` at frame/adoption,
update affected facts when implementation or setup changes, and reconcile at
validate. Draft/task records hold proposals; journals and Git retain history.
See [project context](Project_Context.md) for examples and ownership.

## Does it work without Git?

The core can install and inspect artifacts without Git, with degraded
diff-related functionality. Anchors, evolution and impacted selection need
Git. The host adapters require a Git checkout. A remote is not required:
local branches can supply the comparison base, and what you do with the
finished work - a local commit, a push, a pull request - is your own procedure.

## Does it need the network?

The standard-library Python core makes no network requests. Configured project
commands, host initialization and the chosen provider may use the network.
Integration packages can be assembled/copied without model requests; their
installed resources and job caches live outside the repository.

## Windows, Linux, CLI and Desktop?

The core and five integration packages support Windows/Linux execution.
CLI and Desktop share registration when they use the same backend and user
profile. Remote or WSL CLI environments need their own install. Desktop plugin
availability depends on the host's support for that backend and environment;
a successful CLI installation does not establish Desktop support. Recorded
backend checks do not prove GUI discovery or an end-to-end model-led workflow. See [Agent_Plugins.md](Agent_Plugins.md).

## What does `check` actually check?

The current catalog has 24 checks, including artifact/link integrity, scope and
layout, secrets in added diff lines, repository evolution, enabled review state,
stage zones, context page size and repeated headings, command failures/timeouts
and the case where no command ran.
`check --help` lists the installed catalog; the [CLI reference](09_CLI_Reference.md)
describes the output and configuration.

Ordinary findings leave the advisory command successful; `--strict` fails on
errors and promoted warnings. Notes cannot be promoted. Invalid invocation or
an operational error is separate from an advisory finding.

Human output shows the first 40 findings unless `--full` is used; `--strict`
implies the full list. JSON output is complete. A `DEVIATION` is the agent's
spoken explanation of an accepted limitation or departure, not a tool finding
or an approval.

## What about a requirement no test can verify?
Say so in the requirement. Start its `verification` with `Manual:` or
`Inspection:` and name the method ("Manual: install on a clean laptop and
read the splash screen"), and `check` classifies it as a named manual method
instead of listing it among missing automated tests. The label does not prove
that the method was performed; record its action and observed result separately. It stays a NOTE -
printed and counted on every run, but never promotable to a `--strict`
failure, so review of the method remains necessary. The honesty is on you: a
test you have not written yet is not a manual method, and writing
`Manual:` with nothing after it buys nothing. And it is no longer only on
you: when a manual method stands in for a test that could have been
automated, the agent says so out loud as a `DEVIATION` line at the moment
it happens.

## Where do I see coverage at a glance instead of one requirement at a time?
`python .agentic/aegis.py diagram`. It draws the register as a Mermaid
flowchart - every requirement grouped under the component whose knowledge
page claims it, with separate coverage states for linked tests, manual methods, uncovered
active requirements, drafts, retired requirements and broken records. Requirements no page claims are grouped apart rather than
dropped, so a behavior nobody has filed under a component is visible
instead of absent. Narrow it with `--component` or `--task` before the
register outgrows one screen, and use `--out` to write a file, because a
console under a legacy code page will mangle the characters on the way
out. Everything drawn is read from files already in the repository - no
model, no network, no renderer. The colour reports that a linked test
*exists*, not that it is any good: this is a coverage map, not a quality
judgement.

## I'm reading a file I didn't write. What is it for?
`python .agentic/aegis.py explain <path>`. It lists every requirement whose
`affected_paths` cover that file, grouped under the component that claims
each one, with how it is verified - then the task journals that delivered
them, so you can read the reasoning as well as the rule. A directory in
`affected_paths` covers the files beneath it, and you can paste an absolute
path straight from your shell.

If nothing covers the path, it says so plainly. That is not a finding: code
that only direct changes touched has no requirement. It is still worth
knowing, and it is exactly the kind of gap that is invisible until you ask.

## Can I see the proposed change as a diagram before code is written?
Yes, when you ask for it. Set `[diagrams] enabled = true` in
`.agentic/aegis.toml` and design ends by drawing the proposed implementation
as Mermaid diagrams - `structure`, `sequence` or `state`, as listed in
`[diagrams] types` - into `.agentic/tasks/diagram_TASK-<id>.md`. In checkpoint
mode the response copies every saved heading and complete Mermaid block after
the summary and before choices. Autopilot saves the artifacts and reports their
path without displaying the blocks or adding a stop. An explicit Design stop
still generates applicable artifacts and leaves the header at Design.

Enablement requires the TOML Boolean `true`. Missing/non-list types default to
structure; `types = []` creates no file or link, and unknown names are ignored.
A skipped Design draws nothing. Structure node classes follow
the proposed node edits independently of edges: a new connection does not turn
an unchanged reused node into a changed node.

The drawing
comes from the design, not from a code parser, so it works for every language
and can show a shape that does not exist yet. It only illustrates the design:
no stage, review or `check` finding depends on it, and the Design text wins
where the two disagree. AEGIS bundles no renderer; GitHub, GitLab and many
Markdown previews draw Mermaid, and a terminal shows its text.

## Can it stop the agent writing code before the scope is agreed?
The core has no write interceptor; AEGIS guides and never blocks. It can
report stage-zone findings. Each stage has a write
zone: `frame`, `specify` and `design` write only under `.agentic/`, while
`build` and `validate` are mechanically unrestricted. Source edited under a documentation
stage shows up as a `stage-zone` warning naming the file and the stage.
Most hits mean the journal's `stage:` line is stale rather than that the
edit was wrong - which is itself worth knowing, because a stale stage
breaks resume. `advance` keeps that line current at each transition. Adjust
the zones per stage in `[zones]` in `aegis.toml` when your workflow needs a
different boundary; a zone stays advisory either way.

## Do I have to write requirements for everything?
No. Only changes that add or change a durable product rule go through
AEGIS; bug fixes, local UI adjustments and refactors are made directly and
leave no requirement (doc 04). Adopt existing behavior incrementally (doc
05), or not at all for areas you never touch. `uncovered-source` looks only
at an AEGIS task's own diff (`check --task`): it says the task changed code
its requirements do not cover.

## What are the pauses? Can I turn them off?
By default, the workflow stops after every stage and presents concrete choices
to continue, revise or return, or pause; the agent records each stop with
`pause` and each continuation with `advance`. Set `[interaction] autopilot = true`
in `.agentic/aegis.toml`, or explicitly request autopilot for one task, to flow
between stages through validate. Missing or invalid settings mean autopilot is off.
A decision-blocking question still stops autopilot (`pause --blocked`), and
AEGIS never commits or publishes in either mode. These pauses are conversational
instructions, not mechanisms; your agent CLI's permission system is unchanged.
Autopilot suppresses intermediate stops, not the agent's voice: deviation
notices still arrive mid-run, and the validate close presents every one of
them again in full.

## What is a `DEVIATION` line?
A one-line notification the agent speaks the moment it records a
deviation, in the shape `DEVIATION <stage>: <what> - <why accepted, or
what it costs>`. It is not a stop: the agent says it and carries on,
never waiting for a reply. You get one only when the candidate, agreed scope,
design or contract, or confidence in required verification materially differs
from the plan: for example, when a relevant limitation is accepted,
verification is skipped or weakened, a requirement is retired, unexpected
candidate files are retained, or review finds unrequested work that remains.
Corrected quoting mistakes, failed searches, rejected atomic patches, mistyped
paths, transient command failures, expected red tests, and unrelated findings
are not deviations because they do not change the candidate or its evidence.
The journal line is still written
- the notice is its twin, not its replacement, because a journal is read
afterwards and by then you have already paid for not knowing.

## Can another tool consume this?
Yes: `check --json`, `status --json`, `anchor --json`, and
`evolution --json` print one JSON document on
stdout - always complete (the human-facing finding cap never applies),
with a `schema` integer so your integration fails loudly on a contract
change instead of misparsing. Exit codes are identical to text mode, and
`--run` progress goes to stderr so stdout stays parseable. Parse that
rather than scraping the human output.

## Does repository evolution prove the tests were honest?
No. `anchor` and `evolution` make the changed file set visible and durable,
but both records live in the working tree, are kept out of git by default,
and can be replaced. They help a human
or agent notice that tests, source, tools, or documentation changed; they are
not signatures, attestations, or tamper-proof evidence.

## Is my data locked in?
Core records are Markdown, TOML and task JSON sidecars. Preserve the records
you need before removing `.agentic/` and its marked root pointer blocks.
Uninstall optional host packages separately with their installer. Job logs are
retained in the cache; removal does not erase that evidence automatically.

## When should I create a child task?

Use one only when a large parent contains a non-overlapping scope that can own
its requirements, branch/base, tests and validation independently.
Do not split small or tightly coupled work. Children are opt-in and limited to
one level. Parent integration sees only children visible in its checkout.

## What is the difference between `brief` and `summary`?

`brief` is the first bounded re-entry view: task identity, stage,
branch and base, parent, requirements, context presence, checklist, State,
outcome, interaction mode, review policy, the computed diagram decision, active
rulings, visible children, and a `Read next` line naming what to read. `summary`
prints only the recorded State as a short block - the same block `advance` and
`pause` print after writing. Neither is approval or a substitute for the full
journal and current step sources.

## What happens when the review fix limit is reached?

Total rounds are `1 + max_fix_cycles`. If either verdict still requires changes
on the final round, the agent pauses the task as blocked (`pause --blocked`),
so `summary` shows Needs user: yes. Only a decision by the user, recorded with
`ruling --source user`, changes the scope or the bound. Invalidating stale
verdicts does not reset consumed rounds or erase historical findings. The
protocol is in `.agentic/steps/review.md`, read only when review is enabled.

Reviewers inspect current linked files, including untracked files, and focused
proof due at that phase. Final full strict verification follows their approvals;
its pending checklist is not itself missing review evidence. Existing executed
tests may verify a fix, while a fresh run cannot recreate historical red or
anchor evidence that was never recorded.

## How does a new agent resume safely?

Run `brief TASK-<id>`, read what its `Read next` line names - the current step
file, then the State `must_read` paths - confirm the branch matches the
journal, then read the full journal wherever the stage requires it. Missing,
stale, or omitted state means read more; it never means approval.

## My journal was written by an earlier version. What happens to it?

It stays readable without migration. A journal with `## Handoff` and
`## Stage report` sections keeps them until the first `advance` or `pause`
replaces both with one `## State` block. The former deliver stage is folded
into validate, so a journal left at `stage: deliver` closes through validate:
confirm that its recorded proof still describes the checkout, then run
`advance TASK-<id>` to reach `done`. Its license header and older Log lines
stay as written.

## Where do I report a gap between these docs and the behavior?
The behavior is defined by the payload (`AGENTS.md`, the step files,
`aegis.py --help`); these docs are the guided tour. If they disagree,
the payload wins - and the doc gets fixed.

## Should I see Review in OpenCode's Build selector?

After the complete OpenCode package is installed and its backend restarted,
**Aegis** is the primary agent. The two review agents are subagents, not extra
primary Build modes. Codex exposes the `aegis:aegis` skill instead of an
OpenCode-style primary-agent selector. Other hosts have their own commands.

## What if `lib/bridge.mjs` is missing?

Use a complete built package and its installer; a raw integration source folder
does not include the copied shared runtime. Codex and Claude packages place
that runtime under `plugins/aegis/lib/`. Run `doctor`, inspect ownership
conflicts and update from a complete package. Do not copy one missing file
into an owned installation or treat a fallback to the core CLI as a successful
plugin repair.

## Does a package reuse the author's subscription or sign-in?

No. Every recipient uses their own host authentication, available provider,
model and permissions. The package configures workflow resources and executable
paths; it neither transfers subscriptions nor establishes third-party access
rights. Authentication support belongs to the host/provider.

## A verification run was interrupted. Should I run it again?

First inspect the existing shared `job`, logs and process state. Detached jobs
can survive a session restart; adapters using the same cache prevent a second
job in the same checkout. External suites are outside that protection. Do not
erase an uncertain reservation merely to retry. A changed candidate invalidates
final-proof use even when the recorded command exited zero.

## Can I avoid running the full suite after every edit?

Yes. Use project-native focused tests during build, then full strict verification
after final edits and review. `test --impacted --base HEAD --dry-run` previews
selection without executing it. Add `--no-fallback` to an impacted run to refuse
unavailable selection; without it, the full command remains the fallback. The
runner must honor the selected references. A preview, refusal or cancelled job
is not passing evidence, and later candidate changes still require fresh proof.

## Can I remove the State and saved metadata to save tokens?

Keep the State and evidence. New records omit the payload license header and
marked template-only notes.
Record consolidated outcomes instead of tool transcripts; keep the one-line
State values short - `advance` and `pause` refresh them at boundaries, pauses,
blockers and session ends. `evolution --compact --json` reduces response
text while keeping full saved fingerprints. Existing journals are not compacted,
and actual end-to-end token savings have not been measured.

## Does AEGIS configure the test environment for any project?

No. The project owns its toolchain, readiness checks and runner commands. AEGIS
neither installs dependencies nor translates framework-specific selectors.
Configure and verify focused routing during [setup](01_Install_and_Setup.md#verify-focused-routing-before-using-it).

## Does every edit require AEGIS?

No. This repository uses AEGIS for software-development work. Documentation-only
updates, packaging, release, deployment and repository-maintenance-only work
are outside that scope unless explicitly requested. Commits, pushes, pull
requests and merges follow the repository's own procedures in every case. This
documentation refresh does not require a task journal, development test suite
or a model call.
