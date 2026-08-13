<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Design — an unfakeable red witness that stays honestly skippable

**Answers finding:** `F-01`
**Touches:** `F-03` (Delivery must report what actually happened), `F-06` (skip
records what it discards)

## 1. The problem, stated exactly

The product's reason to exist is that an agent must not be able to make tests pass
by editing them. The defence is detection, not prevention: fingerprint the tests
when they are red, compare at green, and report any test whose bytes moved.

Both halves of that defence are currently supplied by the caller.

`_append_entry` copies the caller's input verbatim:

```
workflow_operations.py:1603    entry = dict(inputs)
workflow_operations.py:1604    entry.pop("expected_revision", None)
```

`_validate_automated_evidence` (`workflow_operations.py:191`) checks `command`,
`selector`, `working_directory`, `outcome`, `exit_status`, `observed_result` and
`tests`. It never mentions `red_witness` or `fingerprints`. So both survive.

`_valid_red_witness` (`stage_expectations.py:139`) then accepts any entry carrying
`red_witness is True`, a non-empty `fingerprints` dict, and a `time` earlier than
the Implementation start.

### Reproduced

On a fresh install, with no process ever launched:

```bash
printf 'import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n' > tests/test_calc.py
```

Then one `evidence-add` carrying `"red_witness": true` and a `fingerprints` map
whose digest is the **already-gutted** file. Check completed with no
`check_red_witness_missing` finding. Implementation then ran the real suite, passed,
and raised **no integrity finding at all**. A test rewritten to assert nothing was
delivered clean.

## 2. The principle

> Faking must be impossible. Skipping must be cheap, obvious, and honest.

Today it is the reverse. Faking takes one documented operation. Skipping requires
knowing an undocumented `decision.add` payload that appears in no help output and
no shipped guidance.

Fixing only the first half would turn AEGIS into a trap: an agent that genuinely
cannot produce red evidence would have no way forward. Both halves move together.

## 3. The fix is one strip loop

`red_witness` and `fingerprints` are written in exactly one place in the entire
runtime:

```
execution_operations.py:194   evidence["fingerprints"] = _fingerprints(context, workspace)
execution_operations.py:195   evidence["red_witness"] = True
```

That branch runs only when AEGIS itself launched the process. So the moment those two
keys can no longer arrive from a caller, they can only mean "AEGIS executed this and
observed a failure". The flag already *is* the provenance marker; it was simply
forgeable.

### The required change

In `workflow_operations.py`, immediately after `entry = dict(inputs)` at line 1603:

```python
for reserved in ("red_witness", "fingerprints", "red_fingerprint_comparison"):
    entry.pop(reserved, None)
```

That is the whole security fix. `_valid_red_witness` (`stage_expectations.py:139`)
needs no change — its existing conjunction becomes sound the moment its inputs can
only originate from a real execution.

Strip silently rather than raising. The caller is not doing anything forbidden by
sending extra keys, and an error here would be a gate. What matters is only that the
value cannot originate outside AEGIS.

Nothing else changes about what callers may record. `evidence.add` remains fully
available, including for automated results produced outside AEGIS. Such evidence is
simply never a witness. AEGIS does not refuse the claim; it declines to treat an
unverified claim as proof.

### Optional, and only if F-03 needs it

If the Delivery report has to distinguish "AEGIS ran this" from "someone told AEGIS
this" for **green** evidence as well, add a `provenance` field of `executed` or
`reported` alongside the strip, and include it in the strip list. Do not do this as
part of the security fix. Decide it while implementing F-03, where the need would
actually appear, and skip it if the Delivery text reads well without it.

### No compatibility shim

Version 1 has not passed release acceptance and nothing is deployed. Runs created
before this change keep whatever they recorded; there is no migration to write and no
treat-legacy-as-executed exception to carry.

## 4. The three honest ways to not have a red witness

All three already exist. None is discoverable. The work is surfacing them.

### 4.1 Red-before-green does not apply — record the exception

The sanctioned path, already implemented at `workflow_operations.py:1623-1636` and
validated at `stage_expectations.py:153-170`. It requires a decision whose `target`
is `red_before_green` and whose `value` is `exception_approved`, carrying a non-empty
`reason` and a non-empty `alternative_confirmation`. Check then records an
informational `not_applicable` finding instead of a failure, and Implementation stops
demanding green evidence.

This is the right design and needs no behavioral change. It needs to be findable:

- The `check_red_witness_missing` finding must state the exception path in its
  observation text, including the operation name and the two mandatory fields. The
  finding text is the only carrier that reaches every host today, because
  `next_actions` is empty everywhere (see `F-08`). Where the Stage holds failed
  automated test evidence that is not a witness, the same text should also name
  `execution-run` — that is the developer who ran the suite elsewhere, and they need
  to be told which of the two problems they have.
- `workflows/check.toml` already mentions "an exception-approved reason and
  alternative confirmation". Extend the instruction with the literal operation and
  its required fields, so a small model can act without guessing a payload shape.
- When `F-08` lands, the same two findings gain a `decision.add` next action.

Legitimate uses, worth naming in the instruction: a pure documentation change; a
dependency bump with existing coverage; a defect that only reproduces against a
resource the developer cannot run locally; a change whose confirmation is genuinely
manual.

### 4.2 The whole Check Stage does not apply — skip it

Already works. Verified: Check is one of the six skippable Stages
(`workflow_operations.py:1472-1487`). A skip records actor, reason, and time, and
sets a `skipped` status distinct from `passed`.

Two things must follow, and today neither does:

- Skipping a Check that already holds a recorded red witness or execution silently
  discards that context. The skip should record what it discarded — see `F-06`.
- Delivery must state that Check was skipped. Today it can claim the opposite — see
  `F-03`.

Implementation must still report missing green evidence when Check was skipped. A
skipped Check is not an approved exception, and conflating them would let a skip
launder a missing result. Keep the two paths distinct in
`stage_expectations.py`.

### 4.3 The tests ran, but not through AEGIS — report them

`evidence.add` with `kind` of `automated` or `imported` remains fully available after
Step 2. The entry keeps its command, outcome, exit status, observed result and
covered tests. It is simply not a witness, because it carries no `red_witness` flag.

This is the honest landing place for "I ran the suite in my IDE". Combined with 4.1
it covers every real case: record what happened, then record the decision that
red-before-green does not apply here and why.

## 5. What Delivery must then say

Truthfulness is what makes the escape hatches safe. Delivery already owns a
`test_integrity` section and a `skips_waivers_and_omitted_stages` section, and both
are currently free text that can contradict the Run (`F-03`). Once `F-03` recomputes
them at completion, the four cases must read distinctly:

| Situation | Delivery must state |
|---|---|
| Executed witness, no test changed | Red before green held; no test changed between red and green |
| Executed witness, tests changed | Red before green held; names every changed test |
| Exception approved | Red before green did not apply; the reason and the alternative confirmation |
| Check skipped, or witness only reported | No red evidence was established; why, and by whom |

## 6. Tests to add

In `05_Software/aegis/tests/test_execution_integrity.py`:

- `test_reported_evidence_cannot_become_a_red_witness` — `evidence.add` carrying
  `red_witness` and `fingerprints`; assert the stored entry has neither, and that
  Check completion still emits `check_red_witness_missing`. This is the regression
  test for the whole finding.
- `test_executed_failure_is_a_red_witness` — a real `execution.run` failure at Check;
  assert the entry carries `red_witness` and a non-empty `fingerprints` map, and that
  Check completion emits no red-witness finding.

In `05_Software/aegis/tests/test_stage_completion_expectations.py`:

- `test_skipped_check_still_reports_missing_green_evidence` — skip Check, reach
  Implementation, assert the missing-green finding is present and that no
  `not_applicable` exception finding appears.
- `test_red_exception_finding_names_the_decision_operation` — assert the
  missing-witness finding text names `decision-add`, `red_before_green`,
  `exception_approved`, `reason`, and `alternative_confirmation`.

## 7. Explicitly out of scope

- **Do not add a gate.** Nothing here may refuse a `stage.complete`. Every case
  resolves to a finding.
- **Do not make Check un-skippable** after evidence exists. Record what the skip
  discards; do not prevent it. Widening `work_applied` to cover evidence would
  convert an escape hatch into a trap, against the standing constraint.
- **Do not add per-Requirement or per-test witness granularity.** The Stage-level
  witness is what the plan specifies.
- **Do not attempt to verify that a reported result is true.** AEGIS cannot, and
  claiming otherwise would be the same category of error as the current defect.
  Making the witness unforgeable is the entire remedy.
- **Do not add a `provenance` field as part of this change.** An earlier draft made
  it the centrepiece; it turned out to be redundant, because `red_witness` already
  carries the same meaning once it cannot be forged.
