<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS - FAQ

## What if the agent ignores the workflow?

The core is advisory. Its heuristics can expose inconsistent artifacts and
diffs, but cannot prove that an agent followed every instruction, performed
honest red testing, or created a journal for every task. Review the actual
records and candidate. Opt-in strict CI can reject errors/promoted warnings;
host integrations also apply their own bounded tool permissions and guards.

## What is AEGIS's operating model?

The 0.14.0 source combines staged instructions, evidence-led idea capture,
requirements, linked tests, journals, repository evolution, review policy and
a Python CLI. Its five host integrations add native entry points and shared
verification jobs. Core records live in Git; installed host resources and job
caches also have local state outside the repository.

## Which agents and models work?

The core needs an agent that can read files and execute the configured commands.
Native packages exist for OpenCode, Codex, Pi, Qwen Code and Claude Code. They
do not distribute credentials or select a model for another user. Bounded
stages and `brief` reduce context load; they do not guarantee compliance by a
particular model or at a specific context limit.

## Can I stop and resume elsewhere?

Yes. Transfer committed records using separately authorized Git operations.
Find the task with `status` if necessary, then run `brief TASK-<id>`. Confirm
the branch, read the current step, Handoff paths and required full journal,
and continue the first unticked action. Missing/stale/shortened state means
read more. A `summary` is recorded information, not fresh proof or approval.
Local verification jobs and uncommitted files do not travel with Git.

## What belongs in the task Log?

Project and component documents hold current positive behavior and actual setup.
Populate `context/project.md` and `context/environment.md` at frame/adoption,
update affected facts when implementation or setup changes, and reconcile at
validate. Draft/task records hold proposals; journals and Git retain history.
See [project context](Project_Context.md) for examples and ownership.

Only durable progress and evidence: stage transitions, material changes or
decisions, consolidated test results, blockers, approvals, deviations, and the
delivery outcome. Frame, Requirement coverage, Design, Rulings, Handoff, and
Stage report own their detailed information; the Log does not duplicate them.
Routine searches, edits, tool mechanics, corrected retries, and repeated test
attempts stay out. During build, retain one expected red and one final green per
meaningful behavior increment.

## Does it work without Git?

The core can install and inspect artifacts without Git, with degraded
diff-related functionality. Anchors, evolution and impacted selection need
Git. The host adapters require a Git checkout. A remote is not required:
local branches can supply the comparison base and a local commit can be the
explicitly agreed delivery outcome.

## Does it need the network?

The standard-library Python core makes no network requests. Configured project
commands, host initialization and the chosen provider may use the network.
Integration packages can be assembled/copied without model requests; their
installed resources and job caches live outside the repository.

## Windows, Linux, CLI and Desktop?

The core and five integration packages support Windows/Linux execution.
CLI and Desktop share registration when they use the same backend and user
profile. Remote or WSL CLI environments need their own install. Claude Desktop
WSL plugin sessions are currently unsupported; Linux Desktop is beta on
supported Ubuntu/Debian distributions. Recorded backend checks do not prove
GUI discovery or an end-to-end model-led workflow. See [Agent_Plugins.md](Agent_Plugins.md).

## What does `check` actually check?

The current catalog has 22 checks, including artifact/link integrity, scope and
layout, secrets in added diff lines, repository evolution, enabled review state,
stage zones, command failures/timeouts and the case where no command ran.
`check --help` lists the installed catalog; the [CLI reference](09_CLI_Reference.md)
describes the output and configuration.

Ordinary findings leave the advisory command successful; `--strict` fails on
errors and promoted warnings. Notes cannot be promoted. Invalid invocation or
an operational error is separate from an advisory finding.

Human output shows the first 40 findings unless `--full` is used; `--strict`
implies the full list. JSON output is complete. A `DEVIATION` is the agent's
spoken explanation of an accepted limitation or departure, not a tool finding
or delivery approval.

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

If nothing covers the path, it says so - and calls that a finding when the
file sits inside your configured `source` or `tests` globs. Ungoverned code
in a governed area is worth knowing about, and it is exactly the kind of gap
that is invisible until you ask.

## Why isn't the architecture diagram generated from my code?
Because generating it would break two promises. A parser that reads code
has to be written per language - free for Python, absent for C, Java, C#
and everything else - so a derived diagram would work in some of your
repositories and not others. And derivation can only ever draw what
already exists, which makes the interesting half impossible: the shape a
change is *going to* produce. So the `## Architecture` diagram in each
knowledge page is written by hand at adoption and kept as current-state
knowledge. When a design changes structure, its proposed diagram lives in the
task journal. At `validate`, after the implementation exists, the agent
reconciles the canonical knowledge page with built code. The cost is honest:
a hand-drawn diagram can go stale, and `check` cannot detect semantic drift.

## Can it stop the agent writing code before the scope is agreed?
The core has no write interceptor. It can report stage-zone findings. Each stage has a write
zone: `frame`, `specify` and `design` write only under `.agentic/`, while
`build`, `validate`, and `deliver` are mechanically unrestricted. Source edited under a documentation
stage shows up as a `stage-zone` warning naming the file and the stage.
Most hits mean the journal's `stage:` line is stale rather than that the
edit was wrong - which is itself worth knowing, because a stale stage
breaks resume. `deliver` is publish-only by instruction and returns to
`validate` if the candidate changes, but it deliberately has no default zone:
the merge-base diff cannot determine which stage introduced an edit. Adjust
the zones per stage in `[zones]` in `aegis.toml` only when that limitation is
acceptable for your workflow.

## Do I have to write requirements for everything?
No. Adopt incrementally (doc 05), or not at all for areas you never
touch. The `uncovered-source` warning tells you when a change lands in
an area with no requirement - that's a signal to add one, not a
punishment.

## What are the pauses? Can I turn them off?
By default, the workflow stops after every stage and presents concrete choices
to continue, revise or return, or pause. Set `[interaction] autopilot = true`
in `.agentic/aegis.toml`, or explicitly request autopilot for one task, to flow
between intermediate stages. Missing or invalid settings mean autopilot is off.
The pre-publication stop always remains. These pauses are conversational
instructions, not mechanisms; your agent CLI's permission system is unchanged.
Autopilot suppresses intermediate stops, not the agent's voice: deviation
notices still arrive mid-run, and delivery still presents every one of
them in full.

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
its requirements, branch/base, tests, validation, and delivery independently.
Do not split small or tightly coupled work. Children are opt-in and limited to
one level. Parent integration sees only children visible in its checkout.

## What is the difference between `brief` and `summary`?

`brief` is the first bounded re-entry view: task identity, checklist, bound
report, review policy, active rulings, handoff, and visible children. `summary`
projects only the latest bound Stage report. Neither is approval or a substitute
for the full journal and current step sources.

## What happens when the review fix limit is reached?

Total rounds are `1 + max_fix_cycles`. If either verdict still requires changes
on the final round, delivery is blocked with `needs_user: yes`. Only an explicit
human ruling that changes scope or policy can reset the counter.

## How does a new agent resume safely?

Run `brief TASK-<id>`, read the current step and Handoff `must_read` paths,
confirm the branch matches the journal, then read the full journal wherever the
stage requires it. Missing, stale, or omitted state means read more; it never
means approval.

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

## Can I remove handoffs and saved metadata to save tokens?

Keep the required handoffs and evidence. New records omit marked template-only
notes, and stage files refer to shared instructions. Record consolidated outcomes
instead of tool transcripts; keep handoffs short and refresh them at boundaries,
pauses, blockers and session ends. `evolution --compact --json` reduces response
text while keeping full saved fingerprints. Existing journals are not compacted,
and actual end-to-end token savings have not been measured.

## Does AEGIS configure the test environment for any project?

No. The project owns its toolchain, readiness checks and runner commands. AEGIS
neither installs dependencies nor translates framework-specific selectors.
Configure and verify focused routing during [setup](01_Install_and_Setup.md#verify-focused-routing-before-using-it).

## Does every edit require AEGIS?

No. This repository uses AEGIS for software-development work. Documentation-only
updates, packaging, release, deployment and repository-maintenance-only work
are outside that scope unless explicitly requested. This documentation refresh
does not require a task journal, development test suite or a model call.
