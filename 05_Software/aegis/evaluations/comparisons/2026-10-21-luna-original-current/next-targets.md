<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Proposed prompt improvements

The original ten cases improve from 6/10 to 10/10 strict passes. Concrete gains
include Frame requirement IDs/license prologues, coherent paused resume records
and clearing stale approvals without inventing new verdicts. One point is only
alignment with a conservative missing-evidence predicate. The broader sample
remains mixed. One repeat does not isolate the effect of individual files;
Specify, Design, Build, Deliver, Adopt and Diagrams themselves were unchanged.

Preserve the useful Frame/Validate/task behavior and address these bounded
contracts before rerunning the same 25 cases:

1. **Persist stage returns.** In `6_deliver.md` and shared journal guidance,
   make a stale-proof return a concrete operation on header, current checklist,
   Handoff and Stage report, followed by the actual summary. Both variants
   recognized stale proof but failed to save the return to Validate.

2. **Repair record writes before reporting completion.** Current autopilot
   advanced the header to Build but left a malformed Stage report and stopped
   after summary failed. Simplify `templates/task.md` around a positive multiline
   example and an explicit read/repair/check sequence within existing authority.
   Preserve license/history. Add no approval gate. A checkpoint and a bounded
   autopilot transition with no missing human decision need different pause fields.

3. **Clarify diagram gating, markers and presentation.** Distinguish missing
   types from `types=[]`; the latter creates neither file nor link. Use the
   proposed Design for change markers and leave reused unchanged nodes unstyled.
   Show blocks after summary and before choices at checkpoints. Autopilot still
   saves/reports artifacts while suppressing display. Current samples ignored
   the empty list, omitted checkpoint display, marked the unchanged normalizer
   changed and omitted enabled diagrams at an explicit stop.

4. **Define evidence required at review time.** Fresh roles repeatedly demand
   final strict proof before approval, while Validate schedules it afterward.
   Separate available pre-review proof from the later final proof. Read actual
   assertions and executed scope; an existing test can cover a restoration
   without a new test-file diff. Retain explicit before/after candidate binding;
   some roles made one explicit digest call. Extra scope findings include
   fixture-provided configuration/knowledge changes, whose ownership cannot
   automatically be attributed to the model's implementation.

5. **Separate contract, implementation and proposal.** In shared AGENTS and
   Adopt guidance, preserve an active requirement when source disagrees; record
   the mismatch in the journal. Label a normative interface as a contract rather
   than verified runtime behavior. Do not legitimize the defect by rewriting the
   requirement. In Specify, justify deliberate grouping of independently testable
   responses: the current serialization draft has two shall clauses without an
   atomicity rationale. Normal/error boundaries need judgment, not a mechanical
   shall counter. Design may propose internal technical choices within accepted
   scope while leaving unresolved public policy explicit.

Do not change AEGIS wording merely to force `approve` instead of `authorize`, or
`trim` instead of `remove surrounding whitespace`: these are scorer limitations.
The repaired task-reference adapter is a transport correction, not a prompt gain.

Use the fixed current payload as the next control, change a small related prompt
set, retain Luna/medium/131072/runtime conditions and check all 25 for regressions.
Native role prompt changes, if selected, also need old/new instruction snapshots
as experimental inputs. No AEGIS prompt changed during this collection; the
payload version remains 0.14.0.
