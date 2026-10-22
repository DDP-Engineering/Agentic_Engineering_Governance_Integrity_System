<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Verification

Prompt material only changed: five payload guides and ten host reviewer prompts.
The two Codex TOML developer-instruction strings were parsed successfully. No
Python product/test code or executable adapter code changed in this iteration.

Existing focused structural and host-integration checks: **70 passed in 55.07s**
(focused-tests.txt). Initial complete software run: **550 passed, 1 failed,
2 skipped in 411.42s** (software-tests.txt). The failure was the unchanged
asynchronous runner polling test: job state still running instead of completed
at adapter.test.mjs:114. A focused rerun without code/test changes passed:
**1 passed in 59.34s** (adapter-recheck.txt). The initial failure is retained;
a clean all-green full rerun was not performed. This is a timing-sensitive
observation, not proof of a diagnosed root cause or an AEGIS prompt-score failure.

The software tests ran concurrently with early model cases, so observed timings
are not isolated prompt-speed measurements. No model semantic failure is retried.
Model-provider/transport errors are tracked separately from controlled fixture
failures and from local software test verification.

Native live review exercises only the two Codex role prompts. Other host prompt
copies receive structural/integration checks, not live model comparisons. No
own AEGIS workflow, task journal, commit, publication or version bump is used.

The follow-up changes only prompt instructions. Final focused structural and
host integration results are recorded in focused-tests.txt. The earlier full
suite and isolated rerun are copied as preceding-software-tests.txt and
preceding-adapter-recheck.txt; they are not a full-suite rerun of this candidate.

Final candidate focused structural/integration run: **70 passed in 55.99s**.
All existing checks pass in that focused run; no software tests were changed.

Final audit: 50 canonical rows match raw results; control integrity and both
raw candidate archive CRCs verified. Eighteen payload mirrors and eight fixed
non-role evaluator inputs match; ten role copies match their frozen candidate
sources. Four distinct roles completed with explicit first/last digest calls
and complete shared-contract reads. No post-proof candidate writes, no duplicate
journals and no external model failures. Full legal prologues are verbatim in
22/25 cases; three gain the word file in the reference line, with notice and
SPDX retained. Exact differences are saved separately. CLI help and diff checks
exit 0. No own task journal, commit, publication or version bump.

Both complete candidate cohorts preserve the original 21/25 control. First
candidate20/25 and final19/25 are not a per-case composite. No model semantic
failures were individually retried; external-only recovery launched no extra
case because neither cohort had provider/transport interruptions. Model/scorer
raw statuses and every failed predicate remain unchanged.
