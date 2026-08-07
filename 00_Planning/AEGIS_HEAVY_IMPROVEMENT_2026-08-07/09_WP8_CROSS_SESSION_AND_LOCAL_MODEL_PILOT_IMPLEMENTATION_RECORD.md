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
