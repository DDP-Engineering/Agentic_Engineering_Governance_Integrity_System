# Code style

Only the rules no tool checks. Write code that a reader, human or agent, can
follow in as few lines as possible.

## All code

- Simple, direct code; no speculative abstraction, wrapper layers or options
  nobody uses. Preserve public interfaces unless a change is requested.
- One responsibility per file. The payload CLI stays one standard-library file,
  `template/.agentic/aegis.py`; elsewhere, split a file that grows past about
  400 lines.
- Explicit names over comments. A comment says why, never what; no
  commented-out code.
- No file banners, license headers, section markers or end-of-file markers.
  Licensing is in `REUSE.toml`; only payload files under
  `05_Software/aegis/template/.agentic/` carry the short SPDX tag.
- No authorship, date or version tags in comments or docstrings.
- Fail closed at trust boundaries (command arguments, files, configuration,
  host tool input, subprocess output): validate, report a clear error, never
  guess or continue with partial data.
- Deterministic local paths and configuration; no host-specific assumptions in
  shared code.
- English for identifiers, comments, messages and test names.

## Python

- Python 3.11 or newer; the payload uses the standard library only.
- A one-line module docstring. A one-line docstring on public functions and
  classes whose purpose the name does not make obvious; a longer one, in plain
  sentences, only for a non-obvious contract. No `@` tags.
- Type hints on function signatures.
- Read and write text as UTF-8 with LF line endings.

## JavaScript (integrations)

- ES modules (`.mjs`) for Node.js 22 or newer, using built-in modules, plus the
  bundled files under `integrations/shared/vendor/`.
- A one-line `/** ... */` on exported functions whose purpose the name does not
  make obvious.
- Pass child-process arguments as arrays, never as shell text.

## Tests

- Name a test after the behavior it proves; cover the clear path and the
  failure cases at each trust boundary.
- Mention the governing requirement ID in the test docstring when one exists.
