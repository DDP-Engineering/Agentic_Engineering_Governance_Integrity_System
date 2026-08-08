<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# How To Start and Adapt a New Project with AEGIS 3.0

AEGIS is a file-first governance workflow installed inside a project. WAEGIS 3
is the separate deployment wizard; after deployment, use the project-local
AEGIS wrapper for governed work.

## 1. Install the payload

For an absent target:

```text
waegis new TARGET
```

For a clean existing Git repository:

```text
waegis adopt TARGET
```

Preview with `--dry-run`; supply a closed JSON/TOML answers-version-2 file for
repeatable non-interactive use; add `--yes` only after reviewing the complete
plan. WAEGIS initializes Git for `new` but never clones, creates a branch,
stages, or commits. Review and commit the result yourself.

WAEGIS 3 supports stable AEGIS `>=3.0.0,<4.0.0`. It re-adopts detected WAEGIS
1 installations without trusting their ownership data and rejects AEGIS 2 or
cross-major payloads before mutation. See `UPGRADING.md`.

## 2. Validate local policy

Run the copied wrapper from the repository root:

```text
./.agentic/tools/run.ps1 config validate --json
bash .agentic/tools/run.sh config validate --json
```

`workflow.toml` is mandatory schema 3. Correct invalid configuration instead
of inferring fallback policy. `config show --json` is for explicit diagnosis,
not the normal fresh-session context pack.

The shipped stage-form retention default is explicit:

```toml
stage_form_retention = "latest"
```

## 3. Choose the run profile

Use a full run for ordinary feature, fix, or change work:

```text
aegis run start feature
aegis run start fix
aegis run start change
```

Use `fix --quick` or `change --quick` only for genuinely small work. Quick runs
retain intake, implementation, validation, and delivery. They still create a
real check during implementation and require red-before-green evidence.

For an existing repository that has just been adopted:

```text
aegis run start adoption
```

Adoption describes and baselines existing behavior; it does not change
application behavior.

## 4. Work one stage at a time

Every stage follows the same human approval boundary:

```text
aegis stage prepare
# edit the generated form and referenced Markdown
aegis stage apply
aegis stage show
# obtain explicit human approval
aegis stage close
```

Full development order:

```text
intake -> alignment -> requirement -> design -> check -> implementation -> validation -> delivery
```

Adoption order:

```text
adoption-intake -> adoption-alignment -> repo-discovery -> component-map -> component-adoption -> baseline-review -> adoption-delivery
```

Requirements describe observable contracts. Design records the approved
solution. Checks cite requirements and establish real red evidence before
implementation. Validation runs configured deterministic gates and invariants;
delivery records handoff but never publishes, pushes, merges, or opens a PR.

## 5. Resume with bounded context

In a fresh agent session:

```text
1. Read AGENTS.md.
2. Run aegis run context --json.
3. Follow only any named recovery command.
4. Read only the required_reads paths.
5. Perform the reported current stage and stop for approval.
```

Do not load `graph.json`, `journal.jsonl`, configuration history, or all run
artifacts merely to resume. Use them only for explicit AEGIS diagnosis.

## 6. Configure evidence and gates

External check mode prepares a form, runs commands outside AEGIS, then records
the completed evidence. Managed mode uses `aegis check run`. Never fabricate
IDs or use manual evidence as a substitute for executable red/green results.

`aegis verify run` evaluates build, typecheck, lint, test, and security groups
in order, plus invariants, traceability, coverage, impact, and worktree review.
Disabled groups remain disabled, never passed. A requested command path that
launches nothing is `nothing-ran`, not success.

## 7. Optional external discovery

RepoWise is not a WAEGIS 3 capability. A repository operator or separately
managed external tool may enable the optional schema-1 integration and produce
its structural artifacts. AEGIS validates current hashes, schema, Git HEAD,
and worktree fingerprint during repo-discovery, preserves human-entered data,
and treats proposals as advisory unless policy explicitly requires them.
AEGIS never imports or executes RepoWise.

## 8. Finish without publishing

Closing delivery completes the AEGIS run and writes the final report. Review
the repository and use your normal Git/release process afterward. AEGIS and
WAEGIS do not infer permission to commit, push, publish, merge, or deploy.
