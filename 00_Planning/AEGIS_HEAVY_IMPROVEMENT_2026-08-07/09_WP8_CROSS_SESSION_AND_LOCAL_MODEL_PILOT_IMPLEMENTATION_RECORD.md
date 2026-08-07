<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WP8 cross-session and local-model pilot implementation record

- Date: 2026-08-07
- Starting commit: `1c1c69c`
- Starting tracked state: clean
- Scope: AEGIS only. The user override excludes WAEGIS, VoiceWeaver,
  AudioMancer, frontier-model references, release/soak work, and all other
  projects. The pilot therefore uses disposable local copies of the generic
  AEGIS payload rather than the plan's superseded VoiceWeaver worktree.

## Endpoint and model confirmation

The only network request used for discovery was:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:1234/v1/models
```

It returned `prism-ml/bonsai-27b`. The live pilot used exactly that model via
the same loopback `http://127.0.0.1:1234/v1` OpenAI-compatible API. The model
listing exposes neither a model-build identifier nor tokenizer details, so the
machine result records those fields as not exposed rather than inferring them.
The supplied local context is 131,072; trials used the plan's 32,768 hard-floor
profile and the supplied 131,072 profile. Thinking was enabled, temperature was
zero, and seed support was not asserted because the runner did not expose it.

## Harness and safety boundary

Added `05_Software/aegis/tools/local_model_pilot.py` and focused regression
coverage. The harness copies `template/` into an operating-system temporary
directory for every full-change and quick-fix trial. Every stage session makes
a new API call with one initial user message and a UUID session ID; no previous
conversation messages or prose summaries are reused between sessions.

The model receives only repository path, run ID, context profile, and the
instruction to follow `AGENTS.md`. It has one zero-argument tool:
`run_bounded_aegis_bootstrap`. Model output is never parsed as a shell command.
Only the harness can launch `run start`, `run context`, `stage prepare`, or the
recovery command `stage show`; all commands use `shell = false` subprocess argv.
The harness reads only paths in `run context.required_reads` and rejects any
attempt by AEGIS context to name `graph.json` or `journal.jsonl`.

The test is intentionally bootstrap-only. It does not fill forms, apply or
close stages, create evidence, execute checks, grant waivers, or simulate a
human approval. Those omissions are recorded as non-passed WP8 acceptance
criteria, not inferred successes.

## Commands executed

```powershell
python -B -m py_compile tools/local_model_pilot.py tests/test_local_model_pilot.py
uv run --group dev python -m pytest -q tests/test_local_model_pilot.py
uv run --group dev ruff check tools/local_model_pilot.py tests/test_local_model_pilot.py
uv run --group dev python -B tools/local_model_pilot.py --endpoint http://127.0.0.1:1234/v1 --model prism-ml/bonsai-27b --context-profile 32768 --context-profile 131072 --thinking enabled --temperature 0 --output ..\..\00_Planning\AEGIS_HEAVY_IMPROVEMENT_2026-08-07\09_WP8_LOCAL_MODEL_PILOT_RESULTS.json
```

The final focused harness validation passed: `8 passed`; changed-file Ruff and
Python compilation passed.

`uv run --group dev python -B -m aegis --help` passed. The broad AEGIS-only
suite passed with `578 passed, 3 skipped` after excluding exactly
`test_opencode_adapter.py`, `test_pi_adapter.py`, `test_qwen_adapter.py`,
`test_release_hygiene.py`, and `test_scaffold.py`: each directly imports
WAEGIS, which the user scope override prohibits reading or validating. This is
not a claim that the full cross-package AEGIS suite passed. `git diff --check`,
empty downstream starter-changelog, copied-template cache, generic-template,
trailing-whitespace, and changed-path WAEGIS-scope checks all passed.

## Durable pilot evidence and results

The final raw result is
`09_WP8_LOCAL_MODEL_PILOT_RESULTS.json`; it preserves model responses, runner
usage, response/output byte sizes, wall time, command argv and output,
bootstrap bytes, exact required files read, recovery findings, and per-session
correctness scores. `09_WP8_LOCAL_MODEL_PILOT_ATTEMPT_02.json` is the preceding
recorded attempt, retained to show the retry.

All eight initial fresh sessions requested exactly the sole allowed tool with
zero arguments. No session read graph or journal state, no invalid model command
was executed, and the bounded packs were 24,471–25,127 UTF-8 bytes. Reported
initial request totals were 581–863 tokens; successful continuations reported
730–990 total tokens. Thus every observed workflow exchange is below 8,000
tokens. The 131,072 profile did not receive a larger bootstrap pack than the
32,768 profile; equivalent full/quick startup packs are byte-identical across
profiles.

| Profile | Trial | Startup result | Recovery result |
|---|---|---|---|
| 32,768 | full change | pass, 6,401 ms | fail: `stage show` exit 1, 4,274 ms |
| 32,768 | quick fix | pass, 7,915 ms | fail: `stage show` exit 1, 5,791 ms |
| 131,072 | full change | pass, 6,306 ms | fail: `stage show` exit 1, 4,306 ms |
| 131,072 | quick fix | pass, 11,039 ms | fail: `stage show` exit 1, 3,782 ms |

The four recovery failures are the same validated finding. With a deliberately
unavailable prepared current form, `run context` correctly names `aegis stage
show`, but that command crashes with `TypeError: _payload() got multiple values
for argument 'artifact'`. The final evidence includes bounded stderr excerpts.
This is an AEGIS core recovery defect owned by its prior work-package contract;
it was not repaired during WP8.

An earlier live attempt exposed a second harness finding: continuations could
time out while the local model reasoned about an open-ended post-tool response.
The harness now sends a bounded acknowledgement prompt and caps that response
at 512 tokens. One first-attempt result file was inadvertently overwritten
after a failed relative-path move; the terminal-observed failures are excluded
from acceptance analysis because their raw record is not durable. The harness
now refuses to overwrite an existing output path, and the two later attempts
are retained. This recording failure is itself a pilot-process limitation.

## WP8 acceptance disposition

- Disposable/local AEGIS fixtures only: passed.
- Exact local model and loopback endpoint confirmation: passed.
- Fresh full and quick bootstrap sessions at both profiles: passed for the
  tested intake startup/recovery sessions; no frontier model participated.
- Bounded context/history independence and no graph/journal recovery reads:
  passed for all observed sessions.
- 8K workflow-token limit and equal workflow pack across profiles: passed for
  observed exchanges; runner tokenizer metadata remains unavailable.
- Fresh-session recovery sequence: failed because the named `stage show`
  command crashes in all four recovery trials.
- Full multi-stage change and red-then-green quick fix with human approvals,
  final evidence, and invariants: not executed by this bootstrap-only harness;
  therefore not accepted.
- Complete original plan matrix: not executed, because the user scope override
  replaced VoiceWeaver/Qwen/Codex/Claude trials with the single specified local
  model and prohibited external-project access.

## Remaining risk and follow-up boundary

Do not begin WP9. The `stage show` duplicate-`artifact` crash requires a
separate, measured core-recovery follow-up before this pilot can be extended to
a human-approved, multi-stage full/quick run. The pilot also cannot claim
tokenizer-native tokenization or true cross-run determinism because LM Studio's
reported API fields did not expose either capability.

## Corrective Bonsai-only controlled experiment

This correction supersedes the preceding bootstrap-only disposition for this
user-authorized run. It is a **Bonsai-only user override**, not equivalent
provider coverage for the original Qwen/Codex/Claude matrix. WAEGIS remains out
of scope; no WAEGIS source, test, or documentation was accessed.

`18_WP8_BONSAI_ONLY_CONTROLLED_ATTEMPT_11.json` is the final append-only result.
It retains the raw loopback `/v1/models` discovery response, every initial
OpenAI-compatible request payload/options, responses, reasoning-token evidence
when supplied by LM Studio, command output, fixed approval gates, and SHA-256
links to all durable prior attempts. Attempt 01 remains unavailable because it
was overwritten before the overwrite guard existed; the record does not invent
it. Attempts 02 through 08 remain preserved, including the measured failed
configuration attempts.

The final attempt completed a real full eight-stage `change` and a real quick
four-stage `fix` at both profiles. Each stage sent one fresh model request with
exactly one user message and `prior_transcript_messages = 0`; UUIDs are only
labels, not the evidence of transcript isolation. The model emitted only the
zero-argument bounded bootstrap tool request. The harness owned every command,
form edit, Git fixture setup, approval, and managed check invocation; no model
text became shell input.

- **32,768** is a harness-enforced workflow-budget profile. LM Studio's
  OpenAI-compatible API exposed no per-request context setter, so this does not
  claim server enforcement.
- **131,072** is the user-configured loaded-server profile. It is likewise not
  API-verified by `/v1/models`.
- Thinking is user-configured as enabled. Response
  `completion_tokens_details.reasoning_tokens`, when present, is retained as
  observed evidence and is not labelled an API-verified setting.

Every request serializes the exact message, sole tool schema, and API options
with stable UTF-8 JSON. The harness uses the serialized byte count as a
conservative tokenizer-independent upper bound for input tokens, adds its
explicit `max_tokens = 1024` allowance, and rejects a combined total above the
selected context profile before the network call. This same deterministic guard
was applied to the 32,768 and 131,072 profiles. It does not claim native LM
Studio context enforcement or tokenizer precision. Attempt 11 records a
current `attempt_outcome_class = "success"`; its distinct lineage metadata says
`has_prior_attempts = true` and `follows_prior_failures = true`, rather than
mislabeling the successful current attempt as a retry.

Both full runs registered a requirement/check, recorded a managed red result,
changed the fixture, recorded a managed green result, performed validation,
activated the requirement at validation close, reran final verification, and
closed delivery. Both quick runs used `check create`/`check register`, recorded
managed red then green evidence, retained the declared not-applicable quick
invariants, performed final verification, and closed delivery. All 24 fresh
stage requests had valid constrained tool calls, zero invalid command requests,
and no graph/journal bootstrap reads. Bounded bootstrap packs ranged from
18,546 to 27,389 bytes and the response usage/latency fields are preserved in
the JSON evidence.

The amended Bonsai-only acceptance is met for the controlled disposable-fixture
experiment: full and quick workflows complete at both labelled profiles, with
fresh initial transcripts, fixed recorded human gates, real forms/evidence, and
final invariant verification. It does **not** establish the superseded original
multi-provider matrix, server-enforced 32K/131K request contexts, tokenizer
measurements, or autonomous model-authored engineering quality. No WP9 work has
started.

## Final bounded correction validation

Attempt 11 is an appended live measurement, not a modification of attempts 02
through 10. Its `/v1/models` response was 1,864 bytes with 42 ms observed
latency. The 32,768 full/quick requests serialized to 709/704 bytes and the
131,072 full/quick requests serialized to 711/706 bytes. Including the fixed
1,024-token output allowance, their conservative combined bounds were
1,733/1,728 and 1,735/1,730 respectively; every request was accepted by the
harness guard.
The recorded current outcome is success for both full and quick workflows at
both profiles; all 24 requests had a valid zero-argument tool call and a 4/4
correctness score. Historical
validation remains `19 passed` focused and `580 passed, 3 skipped` broad from
the preceding correction. The current corrected-code totals and commands are
recorded below after final validation.

The final corrected-code validation was run from `05_Software/aegis`:

```powershell
uv run --group dev python -m pytest -q tests/test_local_model_pilot.py tests/test_stage_context_budget.py
python -B -m py_compile tools/local_model_pilot.py tests/test_local_model_pilot.py template/.agentic/cli/src/aegis/cli.py tests/test_stage_context_budget.py
uv run --group dev ruff check tools/local_model_pilot.py tests/test_local_model_pilot.py template/.agentic/cli/src/aegis/cli.py tests/test_stage_context_budget.py
uv run --group dev python -B -m aegis --help
uv run --group dev python -m pytest -q tests --ignore=tests/test_opencode_adapter.py --ignore=tests/test_pi_adapter.py --ignore=tests/test_qwen_adapter.py --ignore=tests/test_release_hygiene.py --ignore=tests/test_scaffold.py
```

The focused result was `23 passed in 2.97s`; compilation, Ruff, and CLI help
passed. The final AEGIS-only broad result was `584 passed, 3 skipped in
56.09s`. The five explicit ignores are the only test files that directly import
the separate WAEGIS package and are excluded solely to preserve this AEGIS-only
scope. These are current corrected-code totals, distinct from the historical
`19 passed` focused and `580 passed, 3 skipped` broad totals stated above.
