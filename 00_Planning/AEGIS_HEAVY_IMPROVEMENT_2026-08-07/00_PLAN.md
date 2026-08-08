# AEGIS Heavy Improvement Plan

**Date:** 2026-08-07
**Plan status:** implementation-ready
**Product decision:** evolve Heavy; do not create a fourth AEGIS variant
**Minimum model context:** 32K tokens
**Normal model context:** 128K tokens
**Pilot repository:** `F:\2026_VoiceWeaver` in an isolated local worktree; never push
**Inspection-only repository:** `F:\2026_AudioMancer`; do not modify it

## 1. Executive decision

AEGIS Heavy remains the single forward product. It supplies the controls that
have demonstrated engineering effect: file-first requirements, traceability,
recorded red-before-green evidence, deterministic validation, write-zone hooks,
and delivery checks. AEGIS Light contributes its procedural writing style,
compact task orientation, impact-focused loop, and explicit handling of an
execution that ran nothing. The old AEGIS remains a field benchmark and a source
of proven invariants; it is not a new implementation base.

This plan does not create another runtime. The target is one Heavy payload with:

1. independently restartable stages;
2. a bounded context pack that works at 32K and stays compact at 128K;
3. deterministic controls on full and quick paths;
4. procedural prompts that a 27B local model can follow;
5. a measured path from implementation to pilot and soak.

WAEGIS is removed from the daily agent workflow, but it is not archived yet.
It remains the supported offline installer, doctor, and upgrader until another
tested mechanism provides all three capabilities without losing project-owned
data. This supersedes the earlier proposal to retire it immediately.

## 2. Non-negotiable product requirements

### 2.1 Stage independence

Every stage in `STAGES` and `ADOPTION_STAGES` must be startable in a fresh
agentic session. A new session receives no chat summary from the previous
session. It must be able to recover the current work from repository artifacts
and bounded CLI output.

The approved bootstrap sequence is:

```text
1. read the repository AGENTS.md
2. run `aegis run context --json`
3. run `aegis stage prepare`
4. read only the skill/reference paths named by `run context`
5. read the prepared current form and the named previous-stage final form(s)
6. execute only the current stage
7. stop after the human approval boundary
```

The session must not need `graph.json`, `journal.jsonl`, the full configuration,
all stage references, or a prose handoff written by the previous agent.

### 2.2 Context budgets

The 32K profile is the hard compatibility floor. The 128K profile is the normal
operating target, not permission for instructions to grow.

The bootstrap pack is defined as the UTF-8 concatenation of:

- repository `AGENTS.md`;
- the active skill router;
- the current stage reference;
- `aegis run context --json` output;
- the prepared current-stage primary form;
- the retained final form from the immediately preceding stage, when one exists.

Automated acceptance uses both a byte proxy and model-specific pilot telemetry:

- `run context --json`: at most 4 KiB, including a run with 1,000 evidence rows;
- complete bootstrap pack: at most 30 KiB of UTF-8;
- measured Qwen3.6-27B input: at most 8K workflow tokens;
- at least 24K tokens remain for code, diff, commands, and outputs at the 32K
  floor;
- the same workflow pack remains at most 8K tokens in the 128K profile.

The byte limit is the offline, deterministic regression gate. The Qwen token
measurement is the empirical acceptance gate because tokenization is
model-specific. Do not introduce an online tokenizer dependency into AEGIS.

### 2.3 Deterministic effect

- A quick run must not turn red-before-green into `not-applicable`.
- A request to execute verification that executes no command must return a
  distinct `nothing-ran` failure.
- Impact execution must fail safe to the full test gate when the focused set is
  incomplete or unsafe.
- A bypass, disabled policy, waiver, pass, failure, and nothing-ran result remain
  distinct states in CLI output, evidence, reports, and tests.
- Existing historical runs remain readable and keep their original meaning.

### 2.4 One source of truth

The generated form checklist is rendered from a declarative stage contract in
the CLI package. Stage reference Markdown mirrors that contract and is checked
for parity by tests. An implementation must not maintain two independently
authored `Done when` lists.

### 2.5 Offline-first and cross-host parity

Core workflow behavior must not require a network service, hosted tokenizer, or
host-specific adapter. `.codex`, `.claude`, `.pi`, and `.opencode` remain thin
adapters to the same payload-owned skills and commands.

## 3. Evidence baseline

The decision is based on observed repository state, not feature count alone.

| Variant | Useful evidence | Main limitation |
|---|---|---|
| Old AEGIS | 170 runs, 665 checks, 568 green results, zero green results missing red evidence, 2,067 evidence records | large shared Markdown registers, a recorded branch collision, roughly 17K workflow tokens before task source |
| AEGIS Light | 137 tests pass and 1 skips; AudioMancer has 526 active per-file requirements with linked tests | advisory-only; no hooks or deterministic state boundary; 5 completed journals still contain unticked work |
| AEGIS Heavy | file-first forms, per-file requirements, hooks, deterministic stage closure | only two complete VoiceWeaver runs; quick path currently drops INV-3; current P0/P1 changes are uncommitted |

Measured workflow loads from the comparison:

- Heavy static largest-stage pack: 21,887 bytes before forms;
- Heavy VoiceWeaver `config show`: 5,991 characters;
- Heavy VoiceWeaver `run status`: 1,069 characters in the measured small run;
- Light AudioMancer delivery hot set: 31,154 bytes plus 2,480-byte status;
- Old static pack: 63,208 bytes plus 4,380-byte status.

The current Heavy worktree also has an integration defect that must be treated
as the first implementation gate:

- `tests/test_documentation_workflow.py` has 1 failure because the rewritten
  requirement reference removed the protected phrase
  `one independently observable contract`;
- the focused stage/quick/gate/traceability set has 116 passing tests;
- P0/P1/P6 edits are present but uncommitted;
- unrelated user changes must be preserved.

## 4. Scope and non-goals

In scope:

- finish and integrate the current retention and procedural-reference changes;
- cover all 15 standard and adoption stages with a restartable contract;
- generate bounded stage context and check it automatically;
- retain red-before-green on new quick runs;
- add honest nothing-ran execution outcomes;
- add safe impact execution;
- keep host adapters and documentation synchronized;
- run 32K, 128K, cross-session, and soak acceptance.

Not in scope:

- a fourth AEGIS implementation;
- replacing the requirement-per-file store;
- replacing the graph/journal persistence engine;
- using Light's hand-edited `stage: done` convention;
- claiming that prompts are a security boundary against the agent itself;
- modifying AudioMancer;
- pushing VoiceWeaver or AEGIS branches;
- archiving WAEGIS before its three distribution duties have a tested successor.

## 5. Work-package status and mapping

The older P0-P7 list is replaced by the work packages below.

| New package | Incorporates | State on 2026-08-07 |
|---|---|---|
| WP0 - stabilize current patch | old P0, P1, P6 | initial commit `ad33af3`; review corrections green, pending independent re-review and commit |
| WP1 - canonical stage contracts | old P1, P3, P6 | standard prose partly present; adoption coverage open |
| WP2 - bounded cross-session context | stage-independence requirement | open |
| WP3 - quick red-before-green | old P2 | open |
| WP4 - honest nothing-ran | old P5, corrected scope | open |
| WP5 - impact execution | old P4 | open |
| WP6 - WAEGIS continuity boundary | old P7, amended decision | open |
| WP7 - adapter and documentation parity | completion obligation | open |
| WP8 - cross-session and local-model pilot | acceptance obligation | open |
| WP9 - soak, release, and retirement decision | stability obligation | open |

No package after WP0 may begin from a failing AEGIS suite. WP1-WP5 each finish
at an independently reviewable commit boundary. Do not batch them into one
implementation session.

## 6. Agent and model execution policy

### 6.1 Supported implementation models

Use one of the following columns; it is not necessary to run both providers for
every package. The independent acceptance review should use a fresh session and,
where practical, the other provider.

| Work class | Codex | Claude Code | Reason |
|---|---|---|---|
| state-machine design, persistence compatibility, invariants, command safety | `gpt-5.6-sol`, `xhigh` reasoning | `claude-opus-5`, `xhigh` effort | highest judgement requirement |
| normal Python implementation and targeted tests | `gpt-5.6-sol`, `high` reasoning | `claude-sonnet-5`, `high` effort | quality/cost balance |
| documentation, adapter parity, fixtures, mechanical test updates | `gpt-5.6-terra`, `medium` reasoning | `claude-sonnet-5`, `medium` effort | bounded and well-specified |
| independent final review of a package | `gpt-5.6-sol`, `xhigh` reasoning | `claude-opus-5`, `xhigh` effort | adversarial contract review |

Model IDs are pinned for reproducibility of this dated plan. If they become
unavailable, use the current `sol`-class Codex model or Claude Code `opus` alias
for hard reasoning, and the current `terra`-class Codex model or `sonnet` alias
for routine implementation. Record the exact resolved model in the package log.

Claude Code launch examples:

```powershell
claude --model claude-opus-5 --effort xhigh
claude --model claude-sonnet-5 --effort high
claude --model claude-sonnet-5 --effort medium
```

For Codex, select the exact model and reasoning level in the active Codex client
or its supported configuration surface and record the pair in the package log.

`max`, Codex `ultra`, and Claude Code `ultracode` are escalation settings, not
defaults. Use them only after a high/xhigh session has produced a concrete,
reproducible blocker and a new session is justified. They must not replace
decomposition, tests, or an independent review.

The model assignments use the current Codex host capability list and current
Claude Code model configuration documented at
`https://code.claude.com/docs/en/model-config` on 2026-08-07.

### 6.2 Session isolation

For every work package:

1. implementation occurs in one bounded session;
2. tests and the implementation log are completed in that session;
3. review occurs in a new session that receives the plan, diff, and test output,
   but not the implementer's hidden reasoning;
4. review findings are fixed in another bounded session if necessary;
5. the human approves any commit or stage-close operation required by the live
   workflow.

The implementer and reviewer must not edit the same files concurrently.

### 6.3 Common implementation prompt

Prepend this to the package-specific prompt in each work package:

```text
Implement exactly one work package from
00_Planning/AEGIS_HEAVY_IMPROVEMENT_2026-08-07/00_PLAN.md.

Read the repository AGENTS.md and 01_Documentation/Code_Style.md completely.
Inspect git status and the existing diff before editing. Preserve all unrelated
and pre-existing user changes. Do not start a second work package. Use the
existing package style and apply changes incrementally. Update behavior tests,
payload documentation, and all affected host adapters in the same package.

Before changing code, restate the package invariants and list the files you
expect to touch. Write or update the focused failing test first. After the fix,
run focused tests, then the full applicable suite and CLI help. Report exact
commands, results, remaining risks, and the proposed commit boundary. Do not
push. Do not modify F:\2026_AudioMancer.
```

### 6.4 Common independent-review prompt

```text
Review one completed AEGIS work package against its section in 00_PLAN.md.
Do not assume the implementation is correct. Inspect the diff, implementation
tests, backward compatibility, CLI output states, documentation, adapter parity,
and context impact. Run the focused tests and at least one negative-path test.
Report findings by severity with exact files and lines. If there are no findings,
state which acceptance criteria were independently verified. Do not edit unless
the user explicitly changes this review task into a fix task. Do not push.
```

## 7. Definition of done for every code package

A package is complete only when all applicable items hold:

- its focused test was observed failing for the intended reason before the
  implementation was accepted;
- focused tests pass;
- `uv run --group dev python -m pytest -q tests` passes under
  `05_Software/aegis/`;
- every changed Python file passes `python -m py_compile <file>`;
- `uv run --group dev python -B -m aegis --help` passes for CLI changes;
- WAEGIS changes pass `uv run --group dev python -m pytest -q tests` and
  `uv run --group dev python -B -m waegis --help` under `05_Software/waegis/`;
- copied payload documentation and `.codex`, `.claude`, `.pi`, `.opencode`
  adapters agree with the implemented command contract;
- root `CHANGELOG.md` has an Unreleased entry for behavior changes;
- `template/CHANGELOG.md` remains empty;
- no generated cache, report, run, or temporary file is accidentally included;
- an independent fresh-session review has no unresolved blocking finding.

Planning-only changes do not require a changelog entry or the Python suites.

## 8. WP0 - Stabilize and integrate the current patch

### Objective

Turn the present P0/P1/P6 worktree into a green, reviewable baseline before new
behavior is added.

### Required implementation

1. Inspect all current changes under the seven development references,
   `template/AGENTS.md`, `template/.agentic/workflow.toml`, and the WAEGIS
   workflow-TOML generator/tests.
2. Preserve the stronger old contract phrase in the requirement guidance:
   every requirement is `one independently observable contract`. The new
   one-behavior explanation may remain, but it must not weaken that semantic
   rule or merely delete its regression test.
3. Confirm the shipped default and the WAEGIS-generated default both use
   `stage_form_retention = "latest"`.
4. Confirm the comments do not claim a fixed graph size or another
   project-specific measurement in copied template material. Template prose
   must remain generic.
5. Check all seven rewritten references for actual CLI syntax. Replace the
   `<workflow>` placeholder only where the adapter contract defines it; do not
   invent direct commands that the package does not expose.
6. Update focused documentation tests to protect structure and behavior rather
   than accidental paragraph layout.
7. Run the AEGIS and WAEGIS suites and record a clean baseline.

### Likely files

- `05_Software/aegis/template/.agentic/skills/agentic-development/reference/*.md`
- `05_Software/aegis/template/.agentic/workflow.toml`
- `05_Software/aegis/template/AGENTS.md`
- `05_Software/aegis/tests/test_documentation_workflow.py`
- `05_Software/waegis/src/waegis/repo/workflow_toml.py`
- `05_Software/waegis/tests/test_repo_workflow_toml.py`
- `05_Software/waegis/tests/test_waegis_v1.py`

### Acceptance tests

```powershell
Set-Location 05_Software/aegis
uv run --group dev python -m pytest -q tests/test_documentation_workflow.py
uv run --group dev python -m pytest -q tests/test_stage_form_lifecycle.py tests/test_quick_runs.py tests/test_gates.py tests/test_requirements_traceability.py
uv run --group dev python -m pytest -q tests
uv run --group dev python -B -m aegis --help

Set-Location ../waegis
uv run --group dev python -m pytest -q tests
uv run --group dev python -B -m waegis --help
```

### Model assignment

- implementation: Codex `gpt-5.6-terra`, medium, or Claude Code
  `claude-sonnet-5`, medium;
- review: Codex `gpt-5.6-sol`, high, or Claude Code `claude-opus-5`, high.

### Package prompt

```text
Implement WP0. Resolve the current documentation regression without weakening
the atomic-requirement contract. Audit the existing uncommitted P0/P1/P6 diff,
make template prose generic, confirm retention-default parity with WAEGIS, and
produce a completely green AEGIS/WAEGIS baseline. Do not add later work-package
behavior.
```

### Stop condition

Stop if the full suite is not green. WP1 must not absorb a WP0 failure.

## 9. WP1 - Canonical contracts and generated completion checklists

### Objective

Give every standard and adoption stage one procedural contract, and render its
completion criteria inside the form the stage session is already editing.

### Design

Add a small immutable checklist model in `stage_schema.py`, for example:

```python
@dataclass(frozen=True)
class StageChecklistItem:
    text: str
    command: str = ""
    human: bool = False

STAGE_DONE_WHEN: dict[Stage, tuple[StageChecklistItem, ...]] = {...}
```

The exact symbol name may follow package style, but these properties are
required:

- every value in `ALL_STAGES` has a non-empty checklist;
- each item names a machine command or is explicitly marked human;
- the mapping is the canonical executable source;
- generated TOML comments do not become parsed payload fields;
- collection stages render the checklist once in `stage.toml`, not in every
  requirement/check item;
- single-form stages render the checklist at the top of their primary form;
- re-preparation renders the same checklist deterministically.

Use the same six-section procedural skeleton for every stage reference:

```text
Purpose
Read first
Steps
Outputs
Done when
Skip when
```

The seven current development references are the starting point, not the full
scope. Also update all seven references in
`agentic-adoption/reference/` and the standard delivery skill/reference path.
Forward work comes before recovery. Recovery and waivers remain available but
appear after the ordinary path.

The Markdown `Done when` list is a checked projection of the canonical mapping.
Add a test that extracts the checkboxes from each mapped reference and compares
their normalized text and human/machine classification with the mapping. A
documentation edit that drifts from the generated form must fail the suite.

### Likely files

- `05_Software/aegis/template/.agentic/cli/src/aegis/stage_schema.py`
- `05_Software/aegis/template/.agentic/cli/src/aegis/stage_forms.py`
- `05_Software/aegis/template/.agentic/skills/agentic-development/reference/`
- `05_Software/aegis/template/.agentic/skills/agentic-adoption/reference/`
- `05_Software/aegis/template/.agentic/skills/agentic-delivery/SKILL.md`
- `05_Software/aegis/tests/test_stage_form_lifecycle.py`
- `05_Software/aegis/tests/test_documentation_workflow.py`

### Required tests

- all 15 stages are present exactly once in the contract mapping;
- an empty checklist or unclassified item is rejected by a test;
- single-stage form comments render in stable order;
- collection-stage control comments render once;
- comments do not alter imported payload/digest behavior;
- rehydrated forms retain the checklist;
- all mapped Markdown checklists match the canonical list;
- every reference remains no larger than 5 KiB unless a measured exception is
  justified in the implementation log.

### Model assignment

- contract design: Codex `gpt-5.6-sol`, xhigh, or Claude Code
  `claude-opus-5`, xhigh;
- prose/mechanical completion: Codex `gpt-5.6-terra`, medium, or Claude Code
  `claude-sonnet-5`, medium;
- review: the other provider's hard-reasoning model at xhigh.

### Package prompt

```text
Implement WP1. Create one declarative Done-when contract for all 15 lifecycle
stages, render it as comments in generated stage forms, and make every standard,
adoption, and delivery reference follow the six-section procedural skeleton.
Add exact parity tests so form and Markdown checklists cannot drift. Preserve
TOML payload and digest semantics.
```

### Stop condition

Do not add a context command or change quick-run semantics in this package.

## 10. WP2 - Bounded cross-session context

### Objective

Make stage independence a deterministic CLI contract and prevent status/evidence
growth from consuming a small model's context.

### CLI contract

Add the read-only command:

```text
aegis run context [--json]
```

Its JSON response has its own versioned, bounded shape:

```json
{
  "context_schema_version": 1,
  "run_id": "...",
  "kind": "fix",
  "profile": "full",
  "stage": "implementation",
  "reference": ".agentic/skills/.../reference/implementation.md",
  "skill": ".agentic/skills/agentic-development/SKILL.md",
  "artifact": ".agentic/runs/.../stages/implementation/implementation.toml",
  "previous_stage_artifacts": ["..."],
  "required_reads": ["..."],
  "next_commands": ["aegis stage prepare", "aegis stage apply", "aegis stage close"],
  "human_gate": "stage close"
}
```

The exact serialization must follow existing payload conventions, but it must:

- derive all paths from the authoritative graph, stage schema, and retention
  policy;
- name only the current skill/reference, not every stage file;
- identify the immediately previous retained final form(s);
- state explicitly when a retained form is unavailable and name the recovery
  command;
- omit evidence rows, journal rows, requirement indexes, complete configuration,
  and report content;
- remain stable in size when evidence history grows;
- perform no stage mutation;
- work for standard, quick, and adoption stages;
- return the same resolution errors as other run-scoped commands.

Keep `run status` as the detailed diagnostic surface. Document `run context` as
the normal first command of a fresh agent session.

### Automated context test

Add `tests/test_stage_context_budget.py` or an equivalently durable name. Build
representative full, quick, and adoption runs, including a graph with 1,000
evidence records. Measure UTF-8 bytes for each component and the complete pack.
Print the component breakdown on failure.

Hard assertions:

```text
run context JSON <= 4 KiB
complete bootstrap pack <= 30 KiB
size with 1,000 evidence records == size without those rows, except IDs/paths
no graph.json or journal.jsonl in required_reads
```

The test must use payload files in the installable template, not repository-only
copies.

### Documentation and adapters

Update template `AGENTS.md`, the development/adoption/delivery routers,
`PROMPT_CHEATSHEET.md`, and each host adapter with the exact fresh-session
recipe. No adapter may inject its own longer handoff format.

### Model assignment

- implementation: Codex `gpt-5.6-sol`, xhigh, or Claude Code
  `claude-opus-5`, xhigh;
- review: other provider, xhigh.

### Package prompt

```text
Implement WP2. Add a read-only, versioned `aegis run context` response for fresh
stage sessions. Bound it to 4 KiB and the complete template bootstrap pack to
30 KiB, including a 1,000-evidence regression fixture. Cover all standard,
quick, and adoption stages. Keep detailed `run status` behavior intact.
```

### Stop condition

Do not accept a context-budget test that omits `AGENTS.md`, the active router,
the current reference, or the current and previous forms.

## 11. WP3 - Red-before-green on new quick runs

### Objective

Keep the proportional lifecycle but remove the quick path's evidence loophole.
New quick runs bypass requirement, design, and the check collection stage; they
do not bypass a reproducing check and its red/green evidence.

### Compatibility design

Persist a run-local red/green policy with two meanings:

- `legacy-not-applicable`: historical quick graphs created before this change;
- `required`: all new full and quick development runs.

The loader must default an older schema-3 quick graph that lacks the field to
`legacy-not-applicable`; a newly started quick graph writes `required`. Do not
reinterpret completed historical quick reports.

### File-first quick check registration

Add a bounded quick-only definition flow while the run is at implementation:

```text
aegis check create
# fill the generated check definition; ID is minted by AEGIS
aegis check register
aegis check prepare / aegis check record
# or: aegis check run <check-id>
```

Required behavior:

- `check create` writes a strict TOML definition under the current run's
  implementation working directory;
- the definition contains an AEGIS-minted ID, command, optional path, variants,
  and concerns;
- requirement/spec citations are explicitly empty/not-applicable on quick runs;
- `check register` validates and atomically journals the check before source is
  changed;
- repeated create/register may add more than one check;
- the commands refuse full runs and non-implementation stages so they cannot
  bypass the normal check collection stage;
- managed and external execution reuse the existing evidence recorder;
- manual evidence cannot satisfy `linked_check_evidence` for a new quick run;
- implementation close requires at least one registered check, every active
  check green, and a prior red record for every green check;
- INV-3 is evaluated for new quick runs; only legacy quick runs report it N/A;
- reports distinguish legacy N/A from current evaluated pass/fail.

Do not add a new lifecycle stage solely for this feature. The proportional path
remains intake, implementation, validation, delivery.

### Required red tests before implementation

- a new quick implementation with no registered check cannot apply/close;
- a manual evidence ID does not satisfy the quick check contract;
- green without prior red is blocked;
- red followed by green closes;
- a non-zero command cannot be recorded as green;
- a legacy quick fixture remains readable and reports INV-3 N/A;
- a full run cannot call the quick check registration commands;
- evidence and journal writes roll back on persistence conflict;
- waiver targeting remains digest-pinned and explicit.

### Likely files

- `models.py`, `store.py`, `cli.py`, `stage_forms.py`, `stage_schema.py`
- `check_execution.py`, `invariants.py`, `verification.py`, `report.py`
- `tests/test_quick_runs.py`, `tests/test_quick_run_reporting_boundaries.py`
- `tests/test_check_execution.py`, `tests/test_invariants.py`
- workflow skill/reference and CLI documentation

### Model assignment

- implementation: Codex `gpt-5.6-sol`, xhigh, or Claude Code
  `claude-opus-5`, xhigh;
- review: other provider, xhigh;
- use `max` only if compatibility/persistence tests expose a concrete unresolved
  state transition after the first review.

### Package prompt

```text
Implement WP3. Preserve the four-stage quick lifecycle but add a file-first,
quick-only check create/register flow. Persist a compatibility policy so old
quick graphs retain N/A while every new quick run must record a real red result
before green. Reuse existing check evidence and waiver machinery; do not accept
manual evidence as the reproducing check.
```

### Stop condition

Stop if backward compatibility requires silently rewriting old graphs or if a
new quick run can close implementation without an evaluated INV-3.

## 12. WP4 - Honest `nothing-ran` execution outcome

### Objective

Prevent a user or model from reading an execution request that launched no
command as successful verification.

### Correct scope

`nothing-ran` means zero commands were launched by an explicit execution
request. It does not mean that AEGIS guessed from arbitrary tool stdout that a
test framework collected zero tests. Frameworks must be configured to return a
non-zero status for their own zero-collection condition.

Apply the outcome to:

- `aegis verify gates` when no selected configured command executes;
- `aegis verify impact --run` when neither a focused command nor a full fallback
  command executes;
- any managed check execution request whose resolved check set is empty.

Do not relabel these states:

- a disabled gate in a general `verify run` remains `not-enforced`;
- an audit that inspected data and found no issue is still a successful audit;
- a bypass remains `bypassed`;
- a command that ran and exited zero remains pass, even if its framework emits
  unfamiliar prose.

### Output contract

Machine output includes:

```json
{
  "execution_status": "nothing-ran",
  "executed_count": 0,
  "reason": "..."
}
```

The command exits non-zero, writes no pass evidence, and journals the explicit
outcome where the command normally journals execution. Plain output includes
`NOTHING RAN` and the reason.

### Required tests

- all gates disabled plus explicit `verify gates` is non-zero nothing-ran;
- selecting a disabled gate is non-zero nothing-ran;
- `verify run` with all gates disabled still reports gates as not-enforced and
  does not claim that deterministic audits ran nothing;
- an empty managed check ID set is nothing-ran;
- one passing command is pass, not nothing-ran;
- one failing command is fail, not nothing-ran;
- JSON and plain output agree;
- no pass evidence is persisted for nothing-ran.

### Model assignment

- implementation: Codex `gpt-5.6-sol`, high, or Claude Code
  `claude-sonnet-5`, high;
- review: hard-reasoning model at xhigh.

### Package prompt

```text
Implement WP4. Introduce a distinct non-zero `nothing-ran` outcome only when an
explicit execution request launches zero commands. Preserve disabled,
not-enforced, bypassed, pass, and fail semantics. Do not parse framework output
to guess zero test collection.
```

### Stop condition

Stop if the implementation cannot distinguish an explicit execution request
from a general audit with disabled gates. Do not make disabled-by-policy gates
fail ordinary `verify run` merely to satisfy this package.

## 13. WP5 - Safe `verify impact --run`

### Objective

Execute the focused tests already resolved by impact analysis while failing safe
to the configured full test gate.

### Configuration contract

Add one optional argv-style field under `[gates.test]`:

```toml
[gates.test]
mode = "enforce"
commands = ["python -m pytest -q"]
impacted_command = ["python", "-m", "pytest", "-q"]
```

`impacted_command` is an argv prefix, not a shell template. Append each resolved
test selector as one argv element and execute with `shell = false`. Omission
preserves existing schema-3 files; WAEGIS validation/generation and configuration
documentation must be updated in the same package.

### Execution algorithm

1. Resolve changed paths using the existing `impact()` function.
2. Build the union of linked test selectors in deterministic sorted order.
3. Reject a focused run and choose the full fallback when any changed source:
   - is uncovered;
   - maps to a requirement with no linked tests;
   - contains a selector that escapes the repository, starts with an option, or
     contains NUL/newline content;
   - cannot be represented as one safe argv element;
   - produces an empty selector set.
4. If safe and complete, append the selectors to `impacted_command` and execute
   it with the configured test timeout.
5. If unsafe/incomplete or no impacted command is configured, print the exact
   fallback reason and execute every configured `[gates.test].commands` entry.
6. If no focused or fallback command can execute, return WP4's nothing-ran.
7. Persist ordinary test-gate evidence plus a journal event that records mode
   (`focused` or `full-fallback`), selectors, and fallback reason.
8. Return the actual command exit status subject to existing waiver rules. Never
   turn fallback or a failing focused set into success.

### CLI contract

```text
aegis verify impact [paths_file] --run
aegis verify impact [paths_file] --run --json
```

Without `--run`, existing reporting behavior and output remain unchanged.

### Required tests

- exact path, directory, glob, and rename impact cases execute expected tests;
- duplicate selectors execute once in stable order;
- selectors are passed as argv, not interpolated through a shell;
- uncovered changed source falls back to full tests with a reason;
- covered source with no linked test falls back;
- leading-option, newline, NUL, and repository-escape selectors fall back;
- missing `impacted_command` falls back;
- missing both focused and full commands returns nothing-ran;
- timeout and unlaunchable-command evidence match normal gate behavior;
- reporting-only `verify impact` remains byte-for-byte compatible where already
  covered by snapshots/contracts;
- Windows argv execution is tested without relying on POSIX quoting.

### Model assignment

- command-safety design and implementation: Codex `gpt-5.6-sol`, xhigh, or
  Claude Code `claude-opus-5`, xhigh;
- review: other provider, xhigh.

### Package prompt

```text
Implement WP5. Add `verify impact --run` using an argv-style impacted test
prefix, deterministic selector union, and fail-safe full-test fallback. Never
shell-interpolate selectors. Reuse gate timeout/evidence/waiver behavior and the
WP4 nothing-ran state. Preserve reporting-only output without --run.
```

### Stop condition

Stop if any selector reaches a shell-interpolated command, if incomplete impact
coverage can skip the full fallback, or if the no-command path can return zero.

## 14. WP6 - WAEGIS continuity boundary

### Objective

Remove WAEGIS from ordinary development-stage instructions while retaining it
as the tested distribution and maintenance boundary.

### Supported responsibility split

AEGIS owns:

- workflow state, requirements, checks, evidence, hooks, reports, and adapters;
- commands used by an agent after the payload is installed;
- template defaults and configuration validation.

WAEGIS owns only:

- install/deploy of the payload and selected adapters;
- `doctor` diagnostics;
- upgrade of payload-owned files while preserving project-owned data.

Daily AEGIS skills must not instruct an implementation agent to invoke WAEGIS.
Installation, repair, and upgrade documentation may and should invoke it.

### Required implementation

1. Audit every payload WAEGIS reference and classify it as install, doctor,
   upgrade, or improper daily-workflow coupling.
2. Remove only the improper coupling.
3. Document the manual offline recovery path using the existing install scripts,
   but do not call it the supported upgrader until it has ownership-aware tests.
4. Define payload-owned and project-owned trees in one WAEGIS source and test
   that upgrades preserve at least requirements, specs, knowledge, reports,
   run history, component data, and project workflow configuration.
5. Add an install/doctor/upgrade smoke test against a temporary repository.
6. Keep WAEGIS outside `template/`; it remains a separate stdlib package.

### Retirement gate

WAEGIS may be archived only after a replacement passes all of these tests on two
repositories:

- clean offline install;
- idempotent doctor with actionable failures;
- dry-run upgrade plan;
- real upgrade preserving every project-owned tree;
- rollback or recoverable backup;
- adapter selection parity;
- version readback after upgrade.

Until then, retirement is not part of this release.

### Model assignment

- implementation: Codex `gpt-5.6-sol`, high, or Claude Code
  `claude-sonnet-5`, high;
- ownership/upgrade review: hard-reasoning model at xhigh.

### Package prompt

```text
Implement WP6. Make WAEGIS a narrow install/doctor/upgrade boundary, remove it
from daily stage instructions, and add ownership-preservation smoke tests. Do
not copy WAEGIS into the payload and do not archive it. Document the exact gate
that a future replacement must pass.
```

### Stop condition

Stop on any upgrade test that removes or overwrites a project-owned file. Do not
replace that failure with a documentation warning or proceed with retirement.

## 15. WP7 - Adapter and documentation conformance

### Objective

Ensure Codex, Claude Code, Pi, OpenCode, direct CLI users, and local models see
the same workflow contract without duplicated logic.

### Required implementation

- inventory every adapter entry point and map it to its payload-owned skill;
- remove adapter-local copies of stage instructions;
- update command examples for `run context`, quick check registration,
  nothing-ran, and impact execution;
- add documentation tests that every adapter names the canonical bootstrap
  sequence and does not tell the agent to read `graph.json`/`journal.jsonl`;
- verify adapter prompts do not inject all stage references at once;
- keep recovery instructions discoverable but outside the ordinary forward
  context pack;
- update `06_SoftwareDocu/` for the stage contract, compatibility policy,
  context budgets, and execution outcomes;
- update `05_Software/aegis/README.md` for public CLI/config changes.

### Model assignment

- implementation: Codex `gpt-5.6-terra`, medium, or Claude Code
  `claude-sonnet-5`, medium;
- review: Codex `gpt-5.6-sol`, high, or Claude Code `claude-opus-5`, high.

### Package prompt

```text
Implement WP7 as a parity pass. Make every host adapter a thin route into the
same payload-owned workflow, update all public command/config documentation,
and add tests that prevent adapter-local stage logic or oversized bootstrap
injection. Do not change core behavior unless a documented mismatch proves the
prior package incomplete.
```

### Stop condition

If parity work exposes a core behavior defect, stop and reopen the work package
that owns that behavior. Do not hide a CLI mismatch in adapter-specific prose.

## 16. WP8 - Cross-session and local-model pilot

### Objective

Prove the workflow on the target local model and prove that each stage really is
independent of chat history.

### Safety and repository setup

- Use a new local branch/worktree derived from `F:\2026_VoiceWeaver`.
- Do not push.
- Do not use or modify `F:\2026_AudioMancer`.
- Record the starting commit, dirty state, AEGIS payload version, model build,
  runner, tokenizer, context size, sampling settings, and tool permissions.
- Keep the 32K and 128K trials on equivalent starting states.

### Session protocol

For each stage:

1. end the previous agentic session completely;
2. open a fresh session with no transcript or prose summary;
3. provide only repository path, run ID, model/context profile, and the common
   instruction to follow repository `AGENTS.md`;
4. require the model to run `aegis run context --json` and `stage prepare`;
5. log every file read and command issued;
6. reject a trial that reads `graph.json`, `journal.jsonl`, all references, or a
   hidden human handoff;
7. let the human perform only the documented approval gate;
8. end the session after stage close.

### Model matrix

| Trial | Model | Context | Reasoning | Required workload |
|---|---|---|---|---|
| A | Qwen3.6-27B | 32K | runner-native thinking enabled; record exact setting | one complete real full `change` run, one fresh session per stage |
| B | Qwen3.6-27B | 32K | same as A | one complete real quick `fix`, including red then green |
| C | Qwen3.6-27B | 128K | same prompt/sampling policy | repeat the full change on equivalent state |
| D | Qwen3.6-27B | 128K | same prompt/sampling policy | repeat the quick fix |
| E | Codex `gpt-5.6-sol` | client default >=128K | high | reference full run, one fresh session per stage |
| F | Claude Code `claude-sonnet-5` | client default >=128K | high | reference full run, one fresh session per stage |

Use temperature zero or the runner's lowest deterministic setting. Fix a seed
where supported. Do not claim cross-run determinism when the runner/model does
not support it.

### Telemetry per stage

Record in a machine-readable pilot result:

- run/stage/session IDs;
- model, context, effort/thinking, sampling, seed;
- bootstrap bytes and tokenizer-reported input tokens;
- total input/output tokens;
- files read and commands run;
- invalid command count;
- stage apply attempts and close attempts;
- route-backs, waivers, and recovery reads;
- human interventions other than approval;
- wall time;
- final evidence and invariant states.

### Pilot acceptance

- both 32K trials complete without a frontier model editing or explaining the
  work to Qwen;
- no stage exceeds 8K workflow tokens;
- every stage begins in a fresh session and uses only the allowed bootstrap;
- every new quick/full green check has prior red evidence;
- no execution request that ran nothing is reported as pass;
- context size does not grow with run evidence history;
- 128K improves working headroom but does not receive a larger workflow pack;
- every intervention and stall is logged; a failed first attempt is a finding,
  not something to hide with an unrecorded retry.

### Model assignment for harness work

- pilot harness/telemetry implementation: Codex `gpt-5.6-sol`, high, or Claude
  Code `claude-sonnet-5`, high;
- pilot result analysis: Codex `gpt-5.6-sol`, xhigh, or Claude Code
  `claude-opus-5`, xhigh.

### Package prompt

```text
Execute WP8 exactly as a controlled experiment. Use an isolated VoiceWeaver
worktree and never push. Start a genuinely fresh session for every stage. Run
Qwen3.6-27B at both the 32K hard floor and 128K normal target, plus one Codex and
one Claude Code reference run. Capture the prescribed telemetry and report all
stalls; do not repair a local-model trial invisibly with a frontier model.
```

### Stop condition

Stop immediately if the test is not running in an isolated VoiceWeaver
worktree, if any command would push, or if AudioMancer would be modified. A Qwen
stall ends that trial as a recorded finding; it does not authorize a frontier
model to continue the same stage.

## 17. WP9 - Soak, release, and final variant disposition

### Objective

Replace “it passed a demo” with enough field evidence to call the workflow
stable for daily development.

### Soak requirement

Complete at least 20 real tasks over at least two approved repositories. Do not
count AudioMancer unless the owner later grants write permission. The set must
include:

- at least 5 quick runs;
- at least 10 full feature/fix/change runs;
- at least 2 adoption or clean-install exercises;
- at least 5 deliberate fresh-session handoffs;
- at least 3 genuine route-back/recovery cases;
- at least 3 branch merge/rebase cases that exercise per-file requirements;
- both 32K and 128K local-model runs.

The categories may overlap. Record failed and abandoned runs; do not count only
successful ones.

### Release gates

- zero green checks without prior red evidence on new runs;
- zero silent nothing-ran passes;
- zero lost project-owned files across tested upgrades;
- 100% of sampled fresh sessions recover without graph/journal reads;
- all automated context packs remain within the 30 KiB/8K-token limits;
- at least 90% of stages apply successfully on the first correctly filled form;
- no unresolved severity-1 or severity-2 review finding;
- AEGIS and WAEGIS suites are green on supported Windows and one POSIX runner;
- install, doctor, and upgrade paths are documented and replayed from a clean
  repository;
- owner signs the go/no-go record.

### Version and changelog

Changing quick-run evidence semantics and adding public CLI/config contracts is
a workflow-contract change. Under repository policy, the eventual release is a
MAJOR version, not a patch. Do not assign the version until the soak gate passes.
When assigned, update in one change:

- root `CHANGELOG.md`, rolling Unreleased into the dated release;
- every template version declaration required by repository instructions;
- WAEGIS compatibility declarations if affected;
- leave `template/CHANGELOG.md` empty.

### Variant disposition after release

- Heavy becomes the only actively developed AEGIS workflow.
- Light is retained as a prompt/UX reference and comparison fixture; no new
  governance behavior is implemented there.
- Old AEGIS is retained as historical efficacy and migration evidence; no new
  product features are implemented there.
- WAEGIS remains the maintenance boundary until its retirement gate passes.

### Model assignment

- telemetry aggregation and mechanical reporting: Codex `gpt-5.6-terra`,
  medium, or Claude Code `claude-sonnet-5`, medium;
- go/no-go analysis and release review: Codex `gpt-5.6-sol`, xhigh, or Claude
  Code `claude-opus-5`, xhigh;
- the owner, not an agent, makes the final release and WAEGIS-retirement
  decisions.

### Package prompt

```text
Execute WP9 from recorded field evidence. Aggregate at least 20 real tasks over
two approved repositories, evaluate every numeric and zero-tolerance release
gate, and write a go/no-go recommendation with failures included. Do not assign
a version, archive a variant, push, or declare stability when any mandatory gate
is missing or failed.
```

### Stop condition

A failed or unmeasured mandatory release gate is a no-go. Do not convert it to a
warning, average it away, or reduce the sample after observing the result.

## 18. Implementation order

```text
WP0 baseline green
  -> WP1 canonical contracts
  -> WP2 bounded stage context
  -> WP3 quick red/green
  -> WP4 nothing-ran
  -> WP5 impact execution
  -> WP6 WAEGIS boundary
  -> WP7 parity pass
  -> WP8 local-model pilot
  -> fix only measured pilot findings
  -> WP9 soak and release decision
```

WP3 and WP4 precede impact execution because WP5 depends on their evidence and
nothing-ran semantics. WP8 starts only after the core suite is green and adapter
parity is complete. Pilot findings become explicit follow-up work packages; they
must not be folded into an unbounded “polish” session.

## 19. Implementation log template

Create one entry per package in this planning directory:

```markdown
# <package> implementation record

- Date:
- Agent host: Codex | Claude Code
- Exact model:
- Reasoning/effort:
- Starting commit:
- Starting dirty paths:
- Scope restated:

## Red observation

- Test command:
- Expected failure:
- Observed failure:

## Changes

- Files:
- Contract decisions:
- Compatibility behavior:

## Validation

- Focused commands and results:
- Full commands and results:
- CLI/manual checks:

## Context effect

- Before bytes/tokens:
- After bytes/tokens:

## Review

- Reviewer host/model/effort:
- Findings:
- Resolution:

## Remaining risk

- Unverified behavior:
- Next allowed package:
```

## 20. Final go/no-go question

The release question is not “is Heavy more sophisticated than Light?” It is:

> Can a fresh 27B-model session, at the 32K hard floor, recover one stage from
> bounded repository artifacts, perform it correctly, and leave deterministic
> evidence that another fresh session can trust?

If the 32K full and quick trials fail, the release is no-go regardless of the
frontier-model result. Fix the measured stall in Heavy; do not answer it by
creating another AEGIS variant.
