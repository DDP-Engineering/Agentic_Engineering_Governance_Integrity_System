# Prompt evaluations

These development-only evaluations measure AEGIS prompt behavior in disposable
Git repositories. They are outside the downstream template. The objective is
to improve prompts through controlled comparisons, with real tool observations
and a separate semantic review. Developing this harness does not use the AEGIS
workflow; the fixture sessions exercise that workflow as their subject.

## Stored records

This folder keeps only baselines on the 0.16.0 payload, all collected on
2026-11-16. Each manifest pins the payload by file hash.

The subscription baselines ran with 131,072 configured tokens and Codex CLI
0.169.0. The `gpt-6-luna` medium and high baselines ran on the 0.16.0 payload
before its final `page_kb` change, whose `aegis.py` and `CLI.md` differ from
the delivered files; the `gpt-6-luna` xhigh and `gpt-6.1-sol` baselines ran on
the delivered payload.

| Baseline | Profile | Model, reasoning | Strict passes |
|---|---|---|---|
| [`2026-11-16-luna-0.16.0-core`](baselines/2026-11-16-luna-0.16.0-core/) | core | `gpt-6-luna`, medium | 10/10 |
| [`2026-11-16-luna-0.16.0-capabilities`](baselines/2026-11-16-luna-0.16.0-capabilities/) | capabilities | `gpt-6-luna`, medium | 10/15 |
| [`2026-11-16-luna-high-0.16.0-rerun`](baselines/2026-11-16-luna-high-0.16.0-rerun/) | capabilities, three cases | `gpt-6-luna`, high | 3/3 |
| [`2026-11-16-luna-xhigh-0.16.0-core`](baselines/2026-11-16-luna-xhigh-0.16.0-core/) | core | `gpt-6-luna`, xhigh | 10/10 |
| [`2026-11-16-luna-xhigh-0.16.0-capabilities`](baselines/2026-11-16-luna-xhigh-0.16.0-capabilities/) | capabilities | `gpt-6-luna`, xhigh | 11/15 |
| [`2026-11-16-sol-0.16.0-core`](baselines/2026-11-16-sol-0.16.0-core/) | core | `gpt-6.1-sol`, medium | 10/10 |
| [`2026-11-16-sol-0.16.0-capabilities`](baselines/2026-11-16-sol-0.16.0-capabilities/) | capabilities | `gpt-6.1-sol`, medium | 13/15 |

With luna at medium, `review_detects_missing_behavior`,
`diagrams_enabled_types`, `validate_stale_context` and both autopilot cases
failed. The high rerun repeats the first three once and passes them; the two
autopilot cases failed the same checks on the 0.15.0 payload at high.

At xhigh, luna passed those first three but failed four cases. Both autopilot
cases saved their diagrams without naming the file in the State block. In
`review_enabled_current` the spec reviewer appended its verdict to the task ID
in its response, so the runner rejected that review as an identity mismatch
and every reviewer check failed with it. In `deliver_requires_approval` the
final answer cited the recorded strict check and its candidate digest, but
not the literal `verify.py` or `--strict` the check looks for. At xhigh luna
also questioned the fixtures' own `aegis.toml` changes as outside the task.

With Sol at medium, `diagrams_skipped_design` recorded the skip but advanced
the journal to build instead of stopping at the design checkpoint, and
`autopilot_design_transition` saved its diagrams without naming the file in
the State block.

The local baselines ran `qwen/qwen3.8-27b` (Q4_K_M) on LM Studio with a
65,536-token loaded window, on the delivered 0.16.0 payload. Without reasoning
they used sampling 0.7/0.8/20 and 16,384 output tokens per response; with
`xhigh` reasoning, 0.6/0.95/20 and 32,768:

| Baseline | Profile | Reasoning | Strict passes |
|---|---|---|---|
| [`2026-11-16-qwen-nothink-0.16.0-core`](baselines/2026-11-16-qwen-nothink-0.16.0-core/) | core | off | 10/10 |
| [`2026-11-16-qwen-nothink-0.16.0-capabilities`](baselines/2026-11-16-qwen-nothink-0.16.0-capabilities/) | capabilities | off | 13/15 |
| [`2026-11-16-qwen-nothink-0.16.0-holdout`](baselines/2026-11-16-qwen-nothink-0.16.0-holdout/) | holdout | off | 6/6 |
| [`2026-11-16-qwen-xhigh-0.16.0-core`](baselines/2026-11-16-qwen-xhigh-0.16.0-core/) | core | xhigh | 10/10 |
| [`2026-11-16-qwen-xhigh-0.16.0-capabilities`](baselines/2026-11-16-qwen-xhigh-0.16.0-capabilities/) | capabilities | xhigh | 15/15 |
| [`2026-11-16-qwen-xhigh-0.16.0-holdout`](baselines/2026-11-16-qwen-xhigh-0.16.0-holdout/) | holdout | xhigh | 6/6 |

Without reasoning, `autopilot_design_transition` drew no diagrams, and
`deliver_changed_after_proof` rejected the changed candidate correctly but
never read `5_validate.md`. With `xhigh`, every case of the three profiles
passed, both autopilot cases included, at about five times the duration; peak
prompts stayed below 30,000 tokens, under half the window, in both settings. Local baselines keep the runner's own `report.md` and
`evidence.sha256.json` in place of `integrity.json`.

The 0.14.0 baselines (core 6/10, capabilities 6/15 at medium) were replaced on
2026-11-16, and older transcripts and the 0.14.0 paired comparisons were
removed earlier, all at the owner's request; Git history keeps them. Other
local and subscription measurements keep their raw evidence in the ignored
`.tmp-codex-eval/` folder.

## Reports

[`report_aegis_evaluations.py`](../../../02_Tools/report_aegis_evaluations.py)
turns stored baselines and local run folders into one HTML page, for one run,
one AEGIS version or every run given. The page explains the test and its
measures, then gives one results row per run, a case-by-case matrix, each
failed case with its request, failed checks, tool calls and final answer, the
run settings grouped where they match, and the limits of the evidence. A run
still collecting is marked partial. The page is generated, so keep it beside
the runs, for example under `.tmp-codex-eval/reports/`, rather than in this
folder.

## Profiles and coverage

The original ten cases in `scenarios.json`, five tools, core fixture setup and
automatic scorer remain unchanged. Their runner is
[`evaluate_aegis_prompts.py`](../../../02_Tools/evaluate_aegis_prompts.py).
This profile covers Frame, Validate and task-record resume behavior, including
stale handoffs, rulings, missing evidence, failed verification and review exhaustion.

The separate `capability-scenarios.json` adds fifteen cases. Its fixture and
scoring modules are `evaluate_aegis_capabilities.py` and
`evaluate_aegis_stages.py` under `02_Tools/`. It does not retroactively change
the meaning of the original ten scores. Both profiles run through the
subscription runner and through the local runner described below. A third,
local-only `holdout` profile adds a second domain and a chained lifecycle,
described under "Hold-out domain and chained lifecycle".

| Prompt or behavior | Observed coverage | Boundary |
|---|---|---|
| `.agentic/AGENTS.md` | Common contract in every original/current fixture; observed reads retained | Changed together with Frame, Validate and task; its individual effect is not isolated |
| `1_frame.md` | Three original Frame cases | Small existing fix, ambiguous retention and new interface |
| `2_specify.md` | Exact serialization requirement and format specification | No implementation; semantic coverage reviewed separately |
| `3_design.md` | Proposed asynchronous jobs, skipped design and interaction settings | Design only; component knowledge stays current |
| `4_build.md` | Actual red test, anchor, source edit, green test and evolution | One existing pure-function regression; existing tests are immutable |
| `5_validate.md` | Original four cases, fresh review enabled/disabled (`review.md` where the payload has it), missing behavior, stale context | Synthetic verification command; no external CI |
| Closing a validated task | Presentation for the user's decision and rejection of a candidate changed after proof, at `deliver` in a payload that still has that stage and at the end of validate otherwise | Stops before commit/publication |
| `adopt.md` | One agreed component, source/tests, knowledge and suspected contract mismatch | Survey, adoption close and publication are not covered |
| `diagrams.md` | Enabled structure/sequence/state, disabled, empty types and skipped design | Artifact/link/display checks; no automatic Mermaid rendering certification |
| Autopilot | Design-to-Build transition, explicit stage stop and blocking review | Not a complete unattended project lifecycle |
| Context | Both project/environment files reconciled, unrelated notes retained | Stale known facts in a bounded fixture |
| Hold-out pricing domain | Frame, specify and design intents with different vocabulary | Local runner only; never used to write prompt rules |
| Chained lifecycle | Five fresh stage sessions handing off through the journal | One feature; code limited to two files and a restricted Python subset |

This is representative behavioral coverage of all eight step prompts, not
exhaustive coverage of every instruction, adapter or configuration combination.
The task template is also exercised. A file being read alone does not count as
successful behavioral coverage.

## Subscription collection

[`evaluate_aegis_subscription.py`](../../../02_Tools/evaluate_aegis_subscription.py)
uses an explicitly supplied native Codex executable and its existing ChatGPT
login. It does not provision API keys or change global configuration. Supply
new, disjoint output and working directories; overwrites are rejected.

```powershell
python 02_Tools/evaluate_aegis_subscription.py run --cli C:/path/to/codex.exe --model gpt-6-luna --reasoning medium --context 131072 --profile core --payload .tmp-codex/paired-capabilities-source/original --output 05_Software/aegis/evaluations/baselines/example-original-core --work-dir .tmp-codex/example-original-core
python 02_Tools/evaluate_aegis_subscription.py run --cli C:/path/to/codex.exe --model gpt-6-luna --reasoning medium --context 131072 --profile capabilities --payload .tmp-codex/paired-capabilities-source/original --output 05_Software/aegis/evaluations/baselines/example-original-capabilities --work-dir .tmp-codex/example-original-capabilities
```

Repeat both profiles for a frozen current payload under new candidate paths.
Keep model, reasoning, context, runtime, profiles and rubrics fixed. No prompt
edits or semantic-failure retries occur during collection. Each native session
is preceded by 30 seconds. Returned generic HTTP429 errors permit bounded
60/120/240-second backoff; quota/billing errors and semantic failures do not.
Native internal per-request pacing is not exposed. A non-completed case stops
that profile; incomplete profiles must not be reported as complete comparisons.

Each case preserves the request, effective instructions, process/session
identity, native events, tool observations, final response, usage and timing.
Manifests retain source/runtime/payload hashes, requested model and reasoning,
configured context and output-limit availability. Evidence archives include
the fixture and integrity hashes. Coordinator wall time includes nested review
sessions; do not add their wall times again. Report actual output tokens from
native usage; reasoning token counts are unavailable unless explicitly supplied
by the service. A 16,000-token tool-output allowance is not a model output cap.
The configured context is a client setting, not independent proof of server allocation.

## Actual reviewer activation

The coordinator must call `delegate_review` for each existing native role;
writing approved verdicts alone fails. Each role runs in a fresh native CLI
session with its unchanged adapter developer instructions, read-only tools and
the same immutable snapshot including Git history. The second role receives
neither coordinator edits nor the first verdict. Observed reads, candidate
digest reads, distinct session IDs and unchanged snapshots are checked.

Review criteria are model-produced. Missing accepted None/ValueError behavior
must be identified by fresh reviewers. Zero fix cycles and autopilot do not
permit continuation past a changes-required verdict. Disabled review launches
no session and retains ordinary validation. This tests the adapter's fresh-agent
fallback through a controlled launcher; it does not test installed plugin
discovery or native host custom-role routing.
The task reference accepts its journal ID with an optional descriptive suffix.
Only the canonical ID selects the review snapshot; the brief is not forwarded
as authority or coordinator conversation. Other task IDs and stale digests
are rejected separately.

## Execution limits and interpretation

Only project-owned Markdown/TOML records are normally writable. Git is read-only.
The Build case additionally allows `src/normalize.py` writes only when its AST
matches the original lowercase function or its pure `strip().lower()` correction.
Every execution rechecks this condition and the trusted verifier/configuration.
No other source, tests, payload or verifier can be changed. These capabilities
bound execution in a synthetic repository; they are not an operating-system sandbox.

Automatic scores check observable state and evidence; they do not prove prose
quality or design correctness. Review saved requirements, diagrams, facts,
review findings and final answers against each rubric. Distinguish prompt
defects, model errors, infrastructure failures and overly narrow automatic
predicates. One repeat is a measured sample, not a reliability estimate.

## Local runs

`evaluate_aegis_prompts.py run` drives a local Chat Completions server such as
LM Studio. `--profile core` runs the ten original cases; `--profile
capabilities` runs the fifteen capability cases with the same fixtures, hosts
and scorer as the subscription runner. There, each `delegate_review` call starts
a fresh local session for its role, with the unchanged Codex role prompt, the
read-only reviewer tools and one immutable snapshot. Neither role sees the
coordinator conversation or the other verdict; a changed candidate consumes the
round, and a verdict bound to another task or candidate is not a review.

```powershell
python 02_Tools/evaluate_aegis_prompts.py run --profile capabilities --base-url http://localhost:1234/v1 --model qwen/qwen3.8-27b --temperature 0.7 --top-p 0.8 --top-k 20 --repeats 3 --output <new-output-dir> --work-dir <new-work-dir>
```

Each result records first, peak and total prompt tokens, completion tokens and
the token cost of each file read. A request's prompt growth is shared among the
tool results appended before it by character length, so per-read costs are
estimates while their sum is measured. The manifest keeps the loaded context
window reported by LM Studio, or `--context-window`, and the report flags runs
above 50% and 75% of it. LM Studio may unload an idle model and load it again
on the next request, so the runner reads the window after every case and marks
a manifest whose window varied. `compare` ignores the server's load state and
adds median peak and total prompt tokens.

Defaults suit a local 27B model: 2,400 seconds per case and 900 per request or
reviewer session. `--top-p`, `--top-k` and `--presence-penalty` are sent only
when set; prefer the model's recommended sampling, since greedy decoding can
repeat endlessly. Six identical consecutive tool calls, or two alternating ones,
end a session as `loop`, as does a response cut at the output limit inside
repeated text. A response that repeats one short unit over 1,000 or more
characters but still finishes is counted as degenerate in the report; its
content is still graded. A `read_file` on a directory is an unavailable capability, not a
forbidden action, on every platform. The local core system text is the shared
core instruction text with the installed root digest, which the subscription
core profile also uses before its MCP routing note. The default response budget
is 16,384 tokens, unlike the native runner's unexposed output cap. Changing
transport, profile, sampling, budgets or window requires fresh paired controls.

Paired payloads differ only in what a payload itself supplies. Each payload
gives its own root digest, as `init` installs it; manifests record it as
`entry_sha256`, and `compare` checks the host contract with the digest replaced
by a placeholder. Fixture journals carry the resume state in the payload's own
format, a `## State` block or the older Handoff and Stage report, and scoring
reads either. The host runs the allowed CLI commands that the fixture's own
parser defines, recorded as `aegis_commands`, and the `run_command`
description names them; the compared contract keeps a generic description.
`advance`, `pause` and `verdict` print the summary as `summary` does, and
results count the journal-writer commands a session used.

A tool name passed as a `run_command` program, a CLI command the payload
does not have, a `req` scaffold without exactly one category and one title, or
`git` repeated as its own first argument is an unavailable capability like a
directory read: a wrong tool choice, not a forbidden action; `req --help`
runs. The evaluated CLI, not the host, decides which `req` categories exist,
so its aliases work and an unknown one returns the CLI's own error. An existing
command outside the allowed set, a `req` category with path characters, a
shell program or a Git write, repeated program name or not, stays forbidden.
`read_file` reads whole lines: `offset` is the first line, 1-based, `limit` a
number of lines, and each result gives `total_lines`, `eof` and the
`next_offset` to continue from, within 40,000 characters. Missing-evidence reports
may lead with a label, as in `unavailable: no tests run` or
`not recorded - no checks run`.

## Hold-out domain and chained lifecycle

`holdout-scenarios.json` uses a pricing module (`apply_discount` in integer
cents) whose vocabulary differs from `normalize_name`. Its frame, specify and
design cases mirror the intents of the original ones: an existing-contract
fix, an undecided data policy, a new data format, an exact text format with an
error response, and a three-module design. **Hold-out results gate prompt
changes and are never used to write prompt rules or examples;** a rule tuned to
a hold-out case turns that case into training data and voids its purpose.

`holdout_chain_percent_validation` runs frame, specify, design, build and
validate as five fresh sessions on one repository. Each session receives only
its stage request; the files and journal left by earlier sessions are the whole
handoff, and the first session's journal ID fills `{task}` in later requests. A
session that does not complete ends the chain. The chain is graded on the
integrated result: every session completed, records at validate, an active
requirement for the error response linked to existing tests, the original
contract still active, a harness-owned acceptance check, red, anchor, edit,
green and evolution in that order, and a final strict proof of the final
candidate. Only the Build session may write `src/pricing.py` and
`tests/test_pricing.py`, and only within a restricted Python subset: no imports
beyond `unittest` and the pricing module, no names or attributes starting with
an underscore, no file, process or dynamic-code builtins, no exponentiation and
no classes other than unittest cases. Every command re-checks both files before
anything executes. This bounds accidental damage in a synthetic repository; it
is not a security sandbox.

## Semantic checks and pass rates

`semantic-checks.json` configures deterministic predicates per scenario: open
questions present in the Frame's unknowns, no invented quantities in its
normative fields, captured contract terms, one requirement per independently
failing response, and Design coverage and size. They are reported as
`semantic_checks` beside the strict checks, never change a strict pass and do
not replace the reviewed rubric. The report lists strict and semantic pass
rates per case across repeats, and `compare` adds them for both runs. Use at
least three repeats before accepting a prompt change, and require it to keep or
improve the hold-out rates.
