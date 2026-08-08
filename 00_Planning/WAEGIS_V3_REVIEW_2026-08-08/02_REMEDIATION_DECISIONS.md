# WAEGIS 3 Review Remediation Decisions

Date: 2026-08-08
Branch: `ddp/waegis-v3-implementation`
Status: approved implementation scope

## Decision principles

- Correctness and misleading diagnostics are fixed before owner GO/NO-GO.
- Interactive robustness is fixed without weakening answers-file strictness.
- Dead code and stale text are removed when the change is mechanically clear.
- Optional consolidation is accepted only when it fixes an observable problem or
  removes a small behavioral inconsistency.
- Publication and recovery code is not restructured solely to reduce line count.

## Implement

| Findings | Decision |
| --- | --- |
| F-01, F-02, F-04 | Implement as the first correctness batch with focused regression tests. |
| F-03, F-05 | Implement as the runtime/interview batch. Preserve publication ordering and scripted-answer failure behavior. |
| F-06, F-07, F-09, F-10, F-11, F-12 | Apply the mechanically safe source cleanup. F-11 is folded into F-02. |
| F-08 | Remove only the duplicate UNC test. Retain the drive-letter check because it provides a more precise diagnostic than the later colon rule. |
| F-13 | Remove the ignored V1 bytecode residue from the implementation worktree after validation. It is disk-only cleanup. |
| F-16 | Use one reparse-point implementation and propagate `OSError`, matching the write-path safety behavior. |
| F-20 | Resolve the payload only when configure must reconstruct the workflow. Add a no-payload healthy-repository regression test. |
| F-21, F-22 | Document re-adopt as the recovery route and improve the configure authority refusal while configure is already being changed. |

## Do not implement now

| Findings | Decision |
| --- | --- |
| F-14 | Defer. It restructures the most sensitive mutation/rollback boundary without correcting an observed failure. F-03 can be fixed consistently in both callers with a small diff. |
| F-15, F-17, F-18 | Defer cosmetic duplicate extraction. The extra module coupling and churn do not improve current behavior. |
| F-19 | Keep the deliberate pre-lock and post-lock clean checks. |
| F-23 | Accept the harmless answers asymmetry until answers handling otherwise changes. |
| F-24, F-25, F-26, F-27 | Retain as accepted limitations documented by the review. |

## Execution model

Implementation uses one Codex session per batch, sequentially. Each session starts
from the latest integrated commit, changes only its assigned scope, runs the full
WAEGIS suite, Ruff, and line guards, and produces one reviewable commit. The main
session integrates each commit into `ddp/waegis-v3-implementation` before starting
the next session.

The final integration pass runs the full WAEGIS and AEGIS suites, the crash matrix,
and the packaging verifier. Owner GO/NO-GO remains pending until those results are
recorded.
