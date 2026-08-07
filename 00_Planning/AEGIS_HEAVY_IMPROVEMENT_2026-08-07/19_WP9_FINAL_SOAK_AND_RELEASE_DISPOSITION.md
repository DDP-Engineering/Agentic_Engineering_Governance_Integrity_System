<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WP9 final soak and release disposition

- Date: 2026-08-07
- Agent host: Codex
- Exact model: current task model; not exposed in the task record
- Reasoning/effort: current task setting; not exposed in the task record
- Starting commit: `2a090db8ec04b8ae1aac73e1cc9ec1bc2f220bb1`
- Starting tracked state: clean
- Scope restated: perform the AEGIS-only WP9 release-readiness audit, repeated
  AEGIS validation, template/version/evidence checks, and final disposition.
  WAEGIS, external repositories, and `F:\2026_AudioMancer` are excluded by user
  instruction. The five AEGIS test modules that import WAEGIS are scope
  exclusions, never reported as passing tests.

## Red observation

### Full Ruff audit

```powershell
Set-Location 05_Software/aegis
uv run --group dev ruff check template/.agentic/cli/src/aegis tools/local_model_pilot.py tests
```

Observed failure:

```text
F401 `.paths.RepositoryPathError` imported but unused
template/.agentic/cli/src/aegis/requirement_store.py:35
```

### WP8 evidence-chain verification

The accepted `18_WP8_BONSAI_ONLY_CONTROLLED_ATTEMPT_11.json` records ten
predecessor paths and SHA-256 values. Those values exactly authenticate the raw
CRLF bytes in the source worktree used for attempt 11. This checkout and the
committed Git blobs use `eol=lf`; their bytes exactly match the source records
after CRLF-to-LF normalization. A direct raw-byte comparison therefore reports
ten expected mismatches, not post-hash mutation or evidence tampering.

The evidence remains immutable and accepted. Its portability limitation is the
recorded hash basis: a verifier outside the original CRLF source worktree must
either retain those raw bytes or normalize the same way before comparison.

## Changes

- Removed the unused `RepositoryPathError` import from
  `template/.agentic/cli/src/aegis/requirement_store.py`. This is a lint-only
  correction; it changes no public CLI or workflow behavior.
- Removed the UTF-8 byte-order mark from the repository-root `.gitattributes`
  so Git recognizes its first line as a comment and applies the declared text
  attributes without a parse warning.
- Added this durable AEGIS-only WP9 audit and disposition record.
- Did not modify WAEGIS, external repositories, WP8 raw pilot evidence,
  versions, release artifacts, or `template/CHANGELOG.md`.

## Validation

### Targeted and repeated AEGIS-only tests

```powershell
Set-Location 05_Software/aegis
uv run --group dev python -m pytest -q tests/test_stage_context_budget.py::test_missing_prepared_form_stage_show_reports_state_without_recreating_it tests/test_local_model_pilot.py tests/test_quick_runs.py tests/test_execution_outcomes.py tests/test_impact_execution.py tests/test_documentation_workflow.py
```

Result: `94 passed in 28.26s`.

```powershell
uv run --group dev python -m pytest -q tests --ignore=tests/test_opencode_adapter.py --ignore=tests/test_pi_adapter.py --ignore=tests/test_qwen_adapter.py --ignore=tests/test_release_hygiene.py --ignore=tests/test_scaffold.py
```

Results from three independent executions: `586 passed, 3 skipped` in
`68.48s`, `70.41s`, and `71.49s`. The last run followed the lint correction.
The exactly five ignored modules directly import WAEGIS:

- `test_opencode_adapter.py`
- `test_pi_adapter.py`
- `test_qwen_adapter.py`
- `test_release_hygiene.py`
- `test_scaffold.py`

They remain unvalidated scope exclusions, not passing AEGIS results.

```powershell
python -B -m py_compile template/.agentic/cli/src/aegis/requirement_store.py
uv run --group dev ruff check template/.agentic/cli/src/aegis tools/local_model_pilot.py tests
uv run --group dev python -m pytest -q tests/test_requirements_traceability.py tests/test_stage_context_budget.py::test_missing_prepared_form_stage_show_reports_state_without_recreating_it
```

Compilation and Ruff passed; the targeted result was `53 passed in 1.33s`.
The compilation-created copied-template bytecode was removed and the final
template cache check was clean.

### Public CLI and recovery contracts

All of these commands passed:

```powershell
uv run --group dev python -B -m aegis --help
uv run --group dev python -B -m aegis run --help
uv run --group dev python -B -m aegis run context --help
uv run --group dev python -B -m aegis stage show --help
uv run --group dev python -B -m aegis verify gates --help
uv run --group dev python -B -m aegis verify impact --help
```

The public missing-prepared-form regression passed. It confirms the current
`stage show` response reports the unavailable prepared state without mutating
the graph or recreating a form; the WP8-recorded duplicate-`artifact` crash is
not present in the current AEGIS source.

### POSIX validation follow-up

The same AEGIS-only suite was run under Ubuntu 24.04 on WSL2 with CPython
3.12.3, uv 0.11.32, and native Linux Node 24.18.0. The Node archive was kept
outside the repository and verified against the official Node.js
`SHASUMS256.txt` before use.

```bash
uv run --frozen --group dev python -B -m pytest -q -rs tests \
  --ignore=tests/test_opencode_adapter.py \
  --ignore=tests/test_pi_adapter.py \
  --ignore=tests/test_qwen_adapter.py \
  --ignore=tests/test_release_hygiene.py \
  --ignore=tests/test_scaffold.py
```

Result: `589 passed in 45.65s`, with zero skips. The complete Ruff audit and
the public `aegis`, `run`, `stage show`, `verify gates`, and `verify impact`
help commands also passed in Ubuntu. The ignored modules remain the same five
WAEGIS-importing scope exclusions used for the Windows runs.

### Template, version, and cumulative-diff checks

- `git diff --check` passed.
- `git check-attr` recognizes the root `.gitattributes` and copied workflow
  configuration as `text` with `eol=lf`, without the former BOM parse warning.
- The copied template has zero `__pycache__`, `.pyc`, and `.pyo` artifacts.
- `template/CHANGELOG.md` is exactly zero bytes.
- AEGIS version declarations are all `2.1.0`: the embedded package, embedded
  CLI `pyproject.toml`, Pi adapter manifest, and development package
  `pyproject.toml`.
- The copied-template scan found zero references to this repository's planning
  directory, workspace path, or external repository paths.
- The largest copied template file is the existing `stage_forms.py` at
  106,163 bytes; no new oversized artifact was added.
- The WP8 attempt manifest declares a Bonsai-only override with four
  disposable-fixture trials. Its ten predecessor SHA-256 values authenticate
  raw CRLF source bytes; the audited LF files and Git blobs match the normalized
  source bytes as described above.

## Soak and release gates

| Gate | Disposition | Evidence / limitation |
| --- | --- | --- |
| 20 real tasks across two approved repositories | **No-go** | No qualifying field-soak record exists in scope. The four WP8 disposable-fixture trials do not count as real tasks or a second approved repository. |
| At least 5 quick and 10 full runs | **No-go** | Zero qualifying field runs are recorded. |
| Adoption/clean-install, route-back/recovery, and merge/rebase minimums | **No-go** | No qualifying field evidence is recorded. |
| Both local-model profiles | Observed only | The accepted Bonsai-only fixture control exercised labelled 32K and 128K profiles, but it is not a qualifying field soak and does not prove server-enforced context. |
| Zero green checks without prior red evidence | Unmeasured for soak | WP8 fixture controls and current regressions support the contract; no qualifying field population exists to evaluate. |
| Zero silent `nothing-ran` passes | Unmeasured for soak | Current execution-outcome regressions pass; no qualifying field population exists to evaluate. |
| 100% fresh-session recovery without graph/journal reads | Unmeasured for soak | WP8 fixture requests are bounded, but the formal field sample is zero. |
| Context limits | Pass for automated/fixture evidence | Current tests and accepted fixture evidence remain within the 4 KiB/30 KiB and observed 8K-token boundaries. |
| At least 90% first correctly filled forms | Unmeasured for soak | The controlled harness owns form edits; it cannot provide the required field-session rate. |
| No unresolved severity-1 or severity-2 AEGIS source finding | Pass for current source audit | The current `stage show` recovery regression, full Ruff audit, repeated AEGIS-only suites, CLI checks, and whitespace audit are green. |
| AEGIS suite on Windows and POSIX | Pass | Repeated Windows AEGIS-only validation is green; the Ubuntu 24.04 WSL2 run passed all 589 in-scope tests with native Linux Node and no skips. |
| Installer/doctor/upgrade replay and project-owned-file preservation | Scope exclusion / **No-go** | These are WAEGIS-owned paths and are prohibited by the user scope override. They were not run and are not claimed. |
| Owner go/no-go signature | **No-go** | No owner signature has been supplied. |

## Variant and adapter disposition

- **AEGIS Heavy:** remains the only actively developed AEGIS workflow. It is
  not release-ready or stable-for-daily-development under WP9 because mandatory
  soak and release gates are missing or failed.
- **AEGIS Light:** retained only as a prompt/UX reference and comparison
  fixture. No new governance behavior is approved there.
- **Old AEGIS:** retained only as historical efficacy and migration evidence.
  No new product features are approved there.
- **Direct CLI:** current public command surface and recovery contract are
  validated in the AEGIS-only runs above; this does not substitute for field
  soak.
- **Codex and Claude adapters:** payload-owned structural route is covered by
  the AEGIS documentation/conformance tests; no host-specific field soak is
  claimed.
- **Pi, OpenCode, and Qwen adapters:** their structural payload guidance is
  covered by the AEGIS documentation pass, but their runtime adapter test
  modules import WAEGIS and were excluded. They are not release-certified.
- **Superseded provider matrix:** the reviewed Bonsai-only disposable-fixture
  matrix is accepted WP8 input only. It is explicitly not equivalent to the
  original Qwen/Codex/Claude provider matrix and cannot be used to satisfy WP9
  field-soak or provider-coverage requirements.
- **WAEGIS:** deliberately outside this WP9 execution. No continuity,
  retirement, version, release-readiness, installer, doctor, or upgrade claim
  is made.

## Version and release decision

No release version is assigned. The planned quick-evidence and public
CLI/configuration changes require a MAJOR version only after the soak gate
passes; that condition is not met. AEGIS remains at `2.1.0`, root
`CHANGELOG.md` remains under `Unreleased`, and the downstream starter
`template/CHANGELOG.md` remains empty. No WAEGIS declaration was read or
changed for this decision.

## Final disposition

**NO-GO: do not release, version, archive a variant, or claim daily-development
stability.** The AEGIS source and AEGIS-only repeated validation are green after
the lint correction, and the Ubuntu POSIX suite is green. The mandatory field
soak is absent, WAEGIS-owned release gates are intentionally excluded, and
owner approval is absent.

## Remaining risk

- Preserve the raw-CRLF evidence basis, or provide a documented normalization
  verifier, when the WP8 hashes must be checked from another checkout.
- Collect the complete 20-task field soak across two owner-approved
  repositories, including all required task categories and failed/abandoned
  runs.
- Have the owner separately decide and sign the final go/no-go after all
  mandatory gates have evidence.
