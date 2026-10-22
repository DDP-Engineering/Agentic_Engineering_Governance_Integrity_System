<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Software verification

`python -m py_compile` passed for the three new capability/subscription tools,
the capability tests and the changed CLI structure test. The unchanged core
harness had already been compiled and exercised by its offline tests.

`python -m pytest -q 05_Software/aegis/tests --tb=short --basetemp .tmp-codex/pytest-review-transport-final`
completed with **551 passed, 2 skipped in 389.59 seconds** on Python 3.13.5,
Windows. See [the saved output](software-tests.txt). The two omitted cases are
platform-dependent symlink checks. Processes needed unrestricted local Git/Python
execution; the first sandboxed suite was stopped after access-related failures.

The first unrestricted suite found one existing test depending on the real
checkout's Git HEAD. The test now fixes its own HEAD value and verifies all
five intended template substitutions. Its focused rerun and the preceding
550-test suite passed. Neither evaluated payload nor the frozen model scorer was
changed for this repair.

The internal review adapter then gained task-reference normalization: the
declared text argument accepts a task ID with an optional descriptive suffix,
selects only the canonical journal and rejects other task IDs or stale digests.
Its targeted offline test passed; the final 551-test suite above includes it.
The visible tool schema and coordinator instructions retain identical hashes.
The complete three-case review subgroup is recollected symmetrically, while
the other cases never reach this repaired enabled-review branch.

The new fixture tests cover all five newly added stage cases, denied reviewer
mutations, candidate identity, independent snapshot visibility, false authored
verdicts, diagram configuration branches, real artifact observations, context
preservation/fresh proof, autopilot boundaries, executable injection rejection,
actual Build red/green execution and bounded requirement scaffolding. Synthetic
backends in offline tests are not counted as live reviewer activation.

`git diff --check` passed. It emitted existing CRLF normalization notices for
the previously modified Frame/Validate/task files. All eighteen installed
payload files match the frozen current template byte for byte; the original
and current CLI/parser bytes are identical.
The read-only `python template/.agentic/aegis.py --help` check also exited0;
its output is retained in `cli-help.txt`. No development workflow was opened.

Live model collection and semantic review are recorded separately. Mermaid
syntax/rendering, installed plugin discovery and actual publication remain
outside this verification.
