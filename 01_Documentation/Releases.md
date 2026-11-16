# Versions and changelog

Assigning a version and building a release are repository operations, not
AEGIS work: open no task journal for them. The implementation a release
carries is journaled; the release itself is not.

## Versions

- Semantic Versioning. Below `1.0.0`, MINOR covers new capabilities and any
  breaking workflow-contract, CLI, hook-protocol or `.agentic/` layout change;
  PATCH covers fixes with no contract change. From `1.0.0`, breaking changes
  take MAJOR.
- The version has one source: the `VERSION` literal in
  `05_Software/aegis/template/.agentic/aegis.py`. `python .agentic/aegis.py
  --version` prints it, `02_Tools/build_aegis_release.py` parses it, and
  `02_Tools/build_agent_plugins.mjs` writes it into every built host package.
- Guides, planning documents, slide decks and PDFs do not state the current
  version; they point to `--version` and the changelog. Only the delivery
  records under `07_Delivery/` name the versions they hold.

## CHANGELOG.md

- Keep a Changelog: `## [Unreleased]`, then the version in progress or the
  latest release. Sections `Added`, `Changed`, `Fixed`, `Removed`, only those
  with entries.
- While a version is assigned but not yet delivered, entries go under its
  section and `[Unreleased]` stays empty. Otherwise they go under
  `[Unreleased]`.
- One or two lines per entry: what changed, and why only when it is not
  obvious. Rationale and design belong in task journals and knowledge pages.
- Older releases live in `CHANGELOG-archive.md`; when a new version is
  assigned, move the previous release section there.
- `05_Software/aegis/template/CHANGELOG.md`, when present, is a downstream
  starter and stays empty.

## Assigning a version

In one change:

1. Turn `## [Unreleased]` into a new `## [x.y.z] - YYYY-MM-DD` section with an
   empty `[Unreleased]` above it, and move the previous release section to
   `CHANGELOG-archive.md`.
2. Set `VERSION = "x.y.z"` in `template/.agentic/aegis.py`.
3. Set `"version"` in the four source manifests:
   `integrations/claude/plugins/aegis/.claude-plugin/plugin.json`,
   `integrations/codex/plugins/aegis/.codex-plugin/plugin.json`,
   `integrations/pi/package.json` and `integrations/qwen/qwen-extension.json`.
4. Run `python -m pytest -q 05_Software/aegis/tests`.

A release refuses to build unless `CHANGELOG.md` carries a dated section for
`VERSION`. Build and publish the delivery as `02_Tools/README.md` describes.
