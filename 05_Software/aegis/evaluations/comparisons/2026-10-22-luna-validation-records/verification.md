<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Software verification

On 2026-10-22:

- `python -m py_compile 05_Software/aegis/tests/test_structure.py` passed.
- Focused structural suite: **58 passed in 3.06 seconds**.
- Final full suite: **551 passed, 2 skipped in 435.95 seconds** using
  `python -m pytest -q 05_Software/aegis/tests --tb=short --basetemp .tmp-codex/pytest-validation-records-final`.
  See [final output](software-tests-final.txt).
- The preceding full run found one overly broad guard that rejected the word
  Mermaid in a presentation instruction. The guard now checks actual drawing
  syntax outside the diagram guide. [Initial output](software-tests.txt) is
  preserved: 550 passed, 1 failed, 2 skipped. Prompt and model-evaluation inputs
  were not changed during this correction.
- The parser has the same hash as the control. Its read-only help command
  previously exited zero; [captured output](../2026-10-22-luna-prompt-corrections/cli-help.txt).

The full local suite overlaps part of core model collection; reported model
wall time does not isolate service latency. These offline software checks are
distinct from the 25 model scenario outcomes.

No own AEGIS workflow, journal, commit, publication or version bump was used.
AEGIS commands in disposable fixtures are the evaluation subject. The payload
stays 0.14.0.

Final `git diff --check` passed. Exact hashes for all ten evaluator/scenario/role
sources and all eighteen template/installed/frozen payload files matched; see
[final verification](final-verification.json). The selected capacity follow-up
has two completed reviewers and its original complete legal prologue.
