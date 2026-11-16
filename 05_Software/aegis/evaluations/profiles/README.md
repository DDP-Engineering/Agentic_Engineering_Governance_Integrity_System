# Evaluation input profiles

Input profiles describe the startup instructions and fixed model configuration
for controlled AEGIS prompt experiments. The product prompts are the intended
experimental variable. Model/server calibration and host-entry configuration
are recorded separately, before evaluating prompt revisions.

`installed-entry.json` supplies the existing parser's `POINTER_DIGEST` in initial
host context, reflecting instruction text delivered by an installed root
instruction file. The digest and its source are hashed. Full workflow contract,
active stage and required templates remain discoverable files; actual reads
are measured. Profile selection must not add per-scenario answer hints.

The native subscription runner supplies this digest in its effective startup
instructions for both profiles. The core profile retains the original five
tools and scorer. The separate capability profile adds bounded delegation
and stage capabilities; its differences are recorded in each manifest.
Historical calibration records were removed at the owner's request. Fresh
paired runs are described in the parent evaluation guide.

For prompt comparisons, retain the same profile, host tools, model settings,
budgets, scenario suite and full requirement/rubric review. Run a fresh complete
control under that entry configuration and vary only the selected AEGIS prompt
files. Bare-host historical scores do not isolate prompt changes under a new
entry profile. Distinguish supplied instructions, actual reads, execution
completion, automatic predicates and semantic compliance in reports.

This is a constrained synthetic environment. The core profile supplies the
digest without creating a root instruction file. Capability fixtures also
write that digest to `AGENTS.md` for actual reviewer discovery. Neither profile
establishes complete installed-host equivalence. The unchanged profile JSON is
hashed in each manifest.
