<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Software and artifact verification

- Changed structural guard file compiled with `python -m py_compile`.
- Focused existing structural checks: **58 passed**. The first run reported
  57 passed and one literal-wording guard failure after the Deliver rewrite.
  That guard now checks the explicit current return/save instruction; the
  model scorer and its predicates were never changed.
- Full `python -m pytest -q 05_Software/aegis/tests`: **551 passed, 2 skipped**
  in 549.17 seconds. See software-tests.txt for captured output.
- `python 05_Software/aegis/template/.agentic/aegis.py --help`: exit 0.
- `git diff --check`: exit 0; existing CRLF normalization notices only.
- Current host adapters reference the installed contract and step files rather
  than duplicating these revised instructions. No host adapter contract changed.

Only the existing prompt structural guards were adjusted to follow the revised
wording/presentation order. No executable product behavior or CLI parser changed.
No documentation-prose inventory tests were added. Model evaluation source hashes
and installed/template/frozen payload identity are checked again in the final
comparison audit. The software suite ran concurrently with early core model cases;
that is a timing confound, not an isolated prompt-speed measurement.

No own AEGIS task, stages, commit, push or release were performed. Disposable
model fixture sessions exercise AEGIS as the subject of evaluation.

Final artifact audit verified all 50 canonical rows against raw results, baseline
integrity, both candidate archive CRCs, all 18 mirrored payload files and all ten
frozen evaluator/scenario/profile/role sources. Four distinct fresh reviewer
sessions completed with two digest reads each and immutable snapshots; all four
read the complete shared contract. There were no externally failed attempts.
The initial local audit script mistakenly applied len() to the integer digest
read count; the corrected audit verified the recorded count directly. This
analysis-script error did not affect model runs or scores.
