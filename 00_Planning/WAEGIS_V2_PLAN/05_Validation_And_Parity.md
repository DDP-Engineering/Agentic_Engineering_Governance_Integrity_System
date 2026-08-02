# WAEGIS V2 — Validation, Parity, and V1 Retirement

## 1. Test strategy

Three tiers, all offline via the preserved seams (CommandRunner / Asker / streams):

1. **Ported unit tests** (Phase 1): the V1 tests covering harvested modules, moved with import fixes only — they pin that harvesting changed nothing.
2. **Fresh behavior tests** (Phases 2–4): per command, covering the doc 01 flows — dry-run writes nothing, consent gates every mutation, dirty-tree refusal, conflict decisions, owned-fields-only regeneration, exit codes, `--json` shapes, golden interview/consent transcripts.
3. **Parity and crash tests** (Phase 6): below.

Anti-regrowth structural tests run in every phase (line budget, forbidden imports, forbidden names, manifest fixture round-trip).

## 2. The parity harness (the go/no-go instrument)

A test-only driver that runs **V1 and V2 side by side** on identical fixture inputs and diffs the outcomes. Fixture matrix:

| Scenario | Compares |
|---|---|
| `new` into empty dir, all-defaults answers | full repo tree byte-diff (excluding `.git` internals), manifest, workflow.toml |
| `adopt` into a JS fixture repo (package.json scripts, existing CLAUDE.md conflict → each of keep/take/sidecar) | tree, manifest, conflict outcomes, proposals JSON |
| `adopt` into a Python fixture (pyproject, Makefile, CI file) | proposals JSON, generated workflow.toml |
| `configure` changing two gates on a V1-installed repo | workflow.toml byte-diff (owned fields only), manifest configuration block |
| `analyze --json` on all fixtures | envelope deep-equality |
| `check`/`doctor --json` on healthy / drifted / broken fixtures | findings parity (minus journal group), exit codes |
| `repair` after deleting a managed file | tree, manifest |
| `upgrade` V1-installed → newer payload, with one of each classifier row represented | tree, manifest, per-file actions, exit codes |

Rules: file *contents* must be byte-identical; human console text may differ (V2's messages are its own); `--json` payloads must be shape-compatible and value-equal except documented additive/removed fields (doctor's journal group). Every intentional divergence is listed in the parity report with a rationale.

## 3. Crash matrix (proves the safety model)

For each mutating command, a test kills the process (hard, via subprocess) at: (a) mid-payload-copy, (b) after config write / before manifest, (c) mid-upgrade-apply. Assertions: the repo is restorable **using exactly the git commands V2 printed** (the test executes them verbatim); after restore, a re-run of the same command completes and yields the same end state as an uninterrupted run (idempotence); no lockfile is left behind after restore + re-run.

Plus: `KeyboardInterrupt` at consent and mid-apply → clean exit / re-raise with restore guidance; two concurrent V2 invocations → second refuses via lockfile with the documented message.

## 4. Independent review gates

After Phases 2, 4, and 6: an adversarial review session (the Batch-13-style acceptance pattern) — trace the flows end to end, hunt for consent bypasses, writes outside `resolve_managed_path`, divergence between printed restore commands and actual damage, and parity-harness blind spots. Findings fixed before the next phase starts.

## 5. V1 retirement criteria (all must hold)

1. Parity report green across the full matrix, intentional divergences documented.
2. Crash matrix green.
3. V2 has performed one real `adopt` and one real `upgrade` on a production repo (candidate: one of the smaller adopted repos, not AudioMancer first) without manual intervention.
4. RepoWise decision resolved: Phase 7 done, or the Core-only stance accepted in writing.
5. Docs that name WAEGIS behaviors (aegis README, template documents, memory notes) updated to V2's safety model.

Until then V1 ships; after that, V1 is removed from the working tree (it remains in git history) and V2 drops the "2": package renamed at leisure or kept — cosmetic, owner's call.

## 6. Standing risks to keep visible

- **Byte-parity of `workflow.toml` is the most fragile promise** — it is why doc 02 forbids touching the harvested generator until the harness exists. Any "improvement" to it happens only after Phase 6, behind the parity gate.
- **The clean-tree precondition changes operator experience** on dirty repos (V1 allowed more). This is intentional and must be stated plainly in the V2 README — it is the price of deleting 1,500 lines of transaction machinery, and `--allow-dirty` exists for the exceptions.
- **Scope creep is the disease this project treats.** The forbidden list and the line-budget test are load-bearing; weakening either requires a written owner decision, not an agent's judgment call.
