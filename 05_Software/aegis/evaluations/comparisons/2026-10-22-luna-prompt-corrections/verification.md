<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Software verification

On 2026-10-22, Windows/Python:

- `python -m py_compile 05_Software/aegis/tests/test_structure.py` passed.
- Focused structural guards: **58 passed** after updating one literal assertion
  to the equivalent clarified enabled-value sentence. The initial failure was
  an obsolete wording expectation, not a changed Boolean gate.
- `python -m pytest -q 05_Software/aegis/tests --tb=short --basetemp .tmp-codex/pytest-prompt-corrections-full`:
  **551 passed, 2 skipped in 469.77 seconds**. See [captured output](software-tests.txt).
  These are local software tests, separate from the model evaluation outcomes.
- `python 05_Software/aegis/template/.agentic/aegis.py --help` exited zero;
  [captured help](cli-help.txt). This read-only CLI check starts no workflow.

The full software suite ran concurrently with part of the core model collection;
model wall-time observations therefore do not isolate service latency.
No AEGIS workflow was used for this development work. The controlled fixture
sessions exercise AEGIS as the evaluation subject.
