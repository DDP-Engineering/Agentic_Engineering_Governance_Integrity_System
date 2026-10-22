<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Verification

Prompt material only changed: three payload guides and ten host reviewer prompts.
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
