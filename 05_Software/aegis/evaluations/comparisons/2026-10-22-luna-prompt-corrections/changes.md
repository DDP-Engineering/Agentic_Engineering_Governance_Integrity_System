<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Frozen prompt changes

The previous current payload is the control. The exact candidate diff is
[saved separately](prompt-changes.diff); [protocol hashes](protocol.json) bind
all eighteen payload files. Template and installed copies match. This collection
changes eight prompt files, with no parser or scenario changes.

| Confirmed issue | Prompt correction | Existing scenarios |
|---|---|---|
| Deliver recognizes stale proof without saving a return | Save header/checklist/Handoff/report, preserve round, show actual summary | `deliver_changed_after_proof`, `deliver_requires_approval` |
| Malformed transition report abandoned after summary error | Physical-line example, reread/repair/rerun, bounded transition versus pending decision | `autopilot_design_transition`, all journal cases |
| Empty diagram types treated as defaults; display or explicit-stop artifacts omitted | Apply gates before file/link generation, preserve Design stop, show checkpoint blocks | All six diagram/autopilot cases |
| Unchanged reused node marked changed due to a new incoming edge | Classify proposed node and edge changes independently | Enabled diagram/autopilot cases |
| Reviews demand final proof before the phase that runs it, or assume no test diff means no coverage | Define evidence due at review, inspect existing assertions and observed runs, bind before/after inspection | Enabled review cases, `build_existing_contract` |
| Normative interface and observed implementation can be conflated | Preserve active contract, label normative versus implemented behavior, journal the mismatch | `adopt_existing_component`, Frame/resume cases |
| Independently verifiable responses grouped without explanation | Split normal/error outcomes or justify inseparable grouping with distinct oracles | `specify_exact_serialization` |

Frame and Build step bytes remain unchanged. Native role definitions remain
unchanged and receive the same transport instructions. Their reading and use
of shared payload guidance must be established from actual tool observations.
No new approval gate or Git authority is introduced. Payload version is 0.14.0.

The complete candidate was frozen before the first execution. No prompt was
changed after observing a result, and no semantic failure was retried.
