<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Documentation Audit Ledger

## Dispositions

- **Current**: matches the AEGIS 3.0 implementation and needs no content change.
- **Updated**: was stale and is corrected by this audit.
- **Historical**: intentionally records an earlier implementation or decision.
- **Deferred**: materially depends on WAEGIS and must be refreshed with that
  separate package rather than during this AEGIS-only audit.

The group rules below are exhaustive for the 125-artifact inventory. Exceptions
are named explicitly, so every artifact receives one unambiguous disposition.

| Inventory group | Count | Disposition | Audit result |
| --- | ---: | --- | --- |
| Root `AGENTS.md`, `CHANGELOG.md`, and `README.md`; `01_Documentation/Code_Style.md`; `02_Tools/README.md` | 5 | Current or updated | Root AEGIS branding and the tools guide were updated. Governing instructions remain current; the changelog records this refresh. WAEGIS-specific root instructions remain outside the semantic audit. |
| `02_Tools/generate_start_guide_pdf.py` | 1 | Updated | Branding now matches AEGIS 3.0, default output is ignored build material outside the copied template, and stale docstring version metadata was removed. |
| `05_Software/aegis/README.md` | 1 | Updated | The package identifies AEGIS 3.0 and no longer asserts an incompatible WAEGIS range. |
| Every tracked `.md` or `.txt` file under `05_Software/aegis/template/` | 89 | Current or updated | All 89 files passed link, command-structure, adapter-route, legal-header, genericity, and template-hygiene checks. Current branding is AEGIS 3.0. The start, configuration, prompt, RepoWise, upgrade, hook, and Codex guides now describe the AEGIS-owned boundary without pinning volatile WAEGIS commands or compatibility ranges. Supporting policy comments and source docstrings were aligned. The downstream `CHANGELOG.md` remains empty. |
| `06_SoftwareDocu/README.md` plus `02_Everyday_Work_Full_Runs.md` through `06_AEGIS_Adapter_And_Context_Conformance.md` | 6 | Current or updated | The five numbered AEGIS guides match current contracts. The catalog was rebuilt from files that actually exist and now labels historical/deferred sets. |
| `06_SoftwareDocu/01_Getting_Started_Install_And_Adopt.md` and companion `.pptx` | 2 | Deferred | These artifacts are WAEGIS-oriented installation material. No compatibility refresh is claimed while WAEGIS is being redesigned. |
| Every file under `06_SoftwareDocu/AEGIS_2_1_HumanExplanations/` | 6 | Historical | Five explanation guides remain unchanged as AEGIS 2.1 provenance. The folder README now prevents them from being mistaken for AEGIS 3.0 guidance. |
| Every Markdown record under `00_Planning/AEGIS_HEAVY_IMPROVEMENT_2026-08-07/` | 11 | Historical, with one updated follow-up | The records remain audit evidence. The final WP9 disposition now records the later owner-assigned 3.0.0 release without rewriting its audit-time NO-GO. JSON pilot evidence was excluded and untouched. |
| `00_Planning/Agentic_Development_Architecture/Agentic_Development_Stack_Architecture.md` | 1 | Deferred historical architecture | The dated AEGIS 2.1/WAEGIS 1.1 architecture is preserved until the WAEGIS redesign establishes its replacement boundary. |
| Feature and bug-fix examples under `00_Planning/Agentic_Development_Architecture_Examples/` | 2 | Current, with bug-fix correction | Commands remain real AEGIS contracts. The quick-run example now says to restart a full run instead of implying routing into bypassed stages. |
| Existing-repository adoption example under `00_Planning/Agentic_Development_Architecture_Examples/` | 1 | Deferred | Its operational sequence is WAEGIS-owned and is not treated as current AEGIS 3.0 installation guidance. |
| **Total** | **125** |  | Every in-scope artifact is covered exactly once. |

## Audit Evidence

- The initial focused documentation/stage/quick/context suite passed 94 tests.
- All 123 Markdown link targets checked before editing resolved successfully.
- The seven rewritten development-stage references expose the required
  operational structure, and their documented invocations parse through the
  real AEGIS CLI parser.
- The requirement-stage reference retains the rule that each requirement is
  "one independently observable contract".
- Template scans found no VoiceWeaver, AudioMancer, or fixed graph-size claims.
- Shipped `stage_form_retention` remains `latest`.

Final validation results are recorded in `02_FINAL_DISPOSITION.md` after the
post-edit validation pass.
