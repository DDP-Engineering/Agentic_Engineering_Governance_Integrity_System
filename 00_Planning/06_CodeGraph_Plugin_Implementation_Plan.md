<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# CodeGraph plugin implementation plan

**Status:** Proposed design and implementation backlog; no CodeGraph functionality is implemented by this document.

**Product:** A reusable, optional AEGIS code-navigation plugin, independent of any downstream application.

**Planning basis:** AEGIS 0.13.0 source inspected on 2026-10-03. InfoShare is one possible evaluation repository, not the product or installation target of this plan.

**Revision 2026-10-03:** Revised after a three-round design review. Main changes:

- CodeGraph runs on the same Python 3.11+ interpreter as `aegis.py`. The frozen executable, bundled interpreter, and `{exe}` placeholder are removed.
- The plugin folder `.agentic/plugins/codegraph/` is committed with the repository, including its vendored native parser modules. Only the generated database is ignored.
- Local-model planning assumes a context window of at least 128k tokens.
- Host-triggered indexing runs as a separate maintenance job kind; a provider-side OS lock and a stdin liveness pipe cover every indexing caller.
- Ownership of ignore rules, installation, versioning, exit codes, symbol IDs, recovery, reviewer access, and host-visible output budgets is now explicit.
- The backlog adds protocol fixtures, installation, contract documentation, CI infrastructure, and this repository's own layout configuration.
- The writer lock, liveness pipe, and parser cancellation have explicit implementation rules and CG-00/CG-04 acceptance criteria.
- The database is confined to `.agentic/knowledge/codegraph/`; journal states come from SQLite, and rebuild checks ownership and journal pairing; the status vocabulary is split into separate fields; cancellation keeps the job supervisor alive; CI separates test tooling from the clean runtime; Python support is a tested matrix rather than a promise about future releases.
- The plugin runs with `-B` so no bytecode is written; indexing refuses unless Git confirms the database folder is ignored and untracked; ownership is checked before every read-write open; manifests outside the selected trees are discovered and hashed; add-on updates require a quiescent checkout; the provider runs in a new process session on Ubuntu; database names follow `NAME.sqlite`; snapshot IDs never repeat and page tokens are bound to their request; acceptance criteria moved into per-deliverable subsections and open items moved before the backlog.
- Precondition order is explicit and the Git check precedes any filesystem change; plugin changes during indexing are detected by content, not version; install validates the release and refuses ownership conflicts; uninstall refuses unexpected files and removes the lock file only as final teardown.

## 1. Goal and recommended decision

Help an agent following AEGIS find and understand relevant source code with fewer searches, smaller responses, and explicit evidence about relationships. Preserve AEGIS's small, offline-first, advisory nature. These productivity benefits are the intended outcome; the plan measures navigation accuracy and output bounds, not agent productivity.

Deliver one optional CodeGraph plugin, written in Python and run by the same Python interpreter as AEGIS, as a committed folder under `.agentic/plugins/codegraph/` with its native parser modules vendored inside it. Keep one derived SQLite database per checkout. Keep `aegis.py` a single standard-library file. Add a thin command dispatcher to AEGIS; keep ingestion, extraction, database ownership, graph queries, and result ranking in CodeGraph.

**Resolved deployment constraint:** third-party packages are allowed inside the plugin folder. The recipient must not need to install Python packages, language parsers, Node, .NET, or a database server, and must not run `pip`, compile code, or download anything to use CodeGraph. AEGIS's existing Python 3.11+ requirement is the only runtime. There is no bundled interpreter or frozen executable.

The normal agent interaction should be:

```text
find a symbol -> inspect its small neighborhood -> read selected source -> make the change
```

The agent does not write SQL, select parsers, administer a database, or ingest the repository on every turn.

**Context baseline:** local-model support assumes a context window of at least 128k tokens. That window is available capacity, not a target to fill; output budgets stay byte-based and compact.

### Requirements stated by the user

- CodeGraph is an add-on to AEGIS, reusable across repositories.
- CodeGraph runs on the same Python interpreter as AEGIS and lives inside the same `.agentic/` folder.
- The plugin folder is committed with the repository.
- AEGIS configuration identifies the plugin settings, database, and existing source scope.
- The plugin and database are self-contained and small.
- CodeGraph and the AEGIS dispatch integration must work natively on both Windows and Ubuntu.
- Third-party packages may be vendored inside the plugin folder; recipients install nothing beyond AEGIS's Python.
- Keep AEGIS itself one small Python application where possible.
- Make stored information easy for coding agents to retrieve without complexity.
- Support local-model use with a context window of at least 128k tokens, and bounded context consumption, without binding the implementation or acceptance criteria to a particular model or provider.

### Parser and packaging decision

Use Python for the engine, the standard-library `sqlite3` module of the user's Python for storage, and Tree-sitter bindings plus pinned Python, C#, TypeScript/TSX, and JavaScript grammars vendored as prebuilt native modules. These are real syntax parsers and avoid maintaining handwritten language parsers.

The read path (status, check, find, file, symbol, callers, refs) imports only the standard library. Native parser modules load only during indexing. A machine whose Python has no matching vendored binaries can still query an existing index; status reports `indexing_supported: false`.

The plugin folder carries the natives for both Windows x64 and Ubuntu x64 side by side and selects the matching set at runtime by platform, architecture, and Python ABI. Support is a published, tested matrix of CPython versions and operating systems, not a promise about future releases:

- Stable-ABI (abi3) wheels can reduce the number of binary sets, because one build can serve several CPython versions. Each wheel still has a minimum Python version, applies to one implementation, architecture, and OS baseline, and depends on its own transitive requirements. CG-00 establishes which pinned packages ship abi3 wheels and what that covers.
- Without abi3 wheels, the folder carries one binary set per tested Python minor version per operating system.
- A CPython version in the tested matrix is supported. A newer CPython for which a compatible abi3 set exists may index, but status labels it `python_support: untested` until it is added to the matrix. Any other Python reports `indexing_supported: false`.

Native modules come from pinned published wheels at build time. Nothing is compiled, regenerated, or downloaded on a recipient's machine.

Tree-sitter builds syntax trees; it does not automatically provide compiler type checking or complete cross-file symbol binding. Add a small explicit resolver for supported lexical bindings, imports, and declared types. Label uncertain targets. Exact overload resolution, runtime dispatch, reflection, and dependency injection remain outside the base edition's guarantees.

Roslyn/TypeScript-compiler-backed enrichment would add runtime, build-context, and project-reference requirements. Defer it until measured navigation failures justify it. Do not recreate a compiler inside the base engine.

## 2. Observed AEGIS integration points

These are current source facts, not proposed capabilities:

| Existing source | Observed behavior | Consequence for CodeGraph |
|---|---|---|
| [Core CLI](../05_Software/aegis/template/.agentic/aegis.py), `AGENTIC`, `ROOT`, `load_config` | Root is the parent of the installed `.agentic` directory, located from `__file__`; configuration is `.agentic/aegis.toml`. | Use the same root and TOML file, independent of caller working directory. |
| Core `match_path` / `match_any` | Directory prefixes and case-sensitive `fnmatchcase` patterns classify repository-relative paths. | Match these semantics exactly; do not introduce a second glob dialect. |
| Core `CONFIG_SHAPE` / `check_config` | Shapes are checked per known table; unknown tables are ignored. | Older cores silently ignore `[codegraph]`. Add one narrowly scoped table, not a plugin framework. |
| Core test `test_generated_config_documents_every_validated_key` | Every key in `CONFIG_SHAPE` must appear, live or commented, in the config `init` writes. | Keep core-validated CodeGraph keys few; the provider validates the rest. |
| Core `visible_repo_paths` / `fingerprint` | Anchors list Git-visible files and skip the whole installed `.agentic/` tree. | Anchors are unaffected by the plugin folder and database. Do not couple graph freshness to task anchors. |
| Core `collect_diff` / `untracked_files` | Untracked large or binary files are reported as "added lines not scanned" under `secret-in-diff`. | The database folder must be git-ignored. |
| Core `write_ignore_block` / `check_fingerprints` | `init` rewrites one managed `.gitignore` block with fixed content and removes it when `[records] commit_fingerprints = true`. | CodeGraph owns a separate block with completely distinct markers. |
| Core `run_git`, `run_command`, `kill_tree` | Git output is captured without a size cap; configured commands capture to a temporary file and keep a 4 KiB tail; `kill_tree` kills a process tree on Windows and POSIX. | A new bounded stdout reader is needed for provider JSON. Reuse `kill_tree`. |
| Core `build_parser` / `main` | Flat argparse subcommands. Argparse usage errors exit 2, although `CLI.md` describes usage errors as exit 1. | The new commands document exit 2 for usage errors. Adapters never parse argparse error text. |
| Core test `test_payload_ships_a_complete_cli_reference` | Every parser command needs its own `## \`command\`` section in `CLI.md`. | Eight concise sections sharing one common explanation. |
| Core `brief`, `summary`, `components`, `explain`, `diagram` | Bounded workflow views, component catalogue (top-level `knowledge/*.md` only), requirement traceability, and coverage diagrams. | Preserve these commands and their output contracts; a code graph is a separate navigation capability. |
| [Shared operations](../05_Software/aegis/integrations/shared/operations.mjs) | Eleven host operations defined once; Pi and the MCP server enumerate them. | Add one read-only operation and one maintenance operation. |
| [Adapter](../05_Software/aegis/integrations/shared/adapter.mjs) `cli` | Runs `python aegis.py` with a 60-second timeout and a 16 MiB buffer; abort kills only the direct Python child. Validates `schema == 1`. | Queries stay bounded direct calls. Indexing cannot use this path. |
| Adapter `fingerprint` (`candidate`) | Hashes every Git-visible file except `.agentic/tasks/` and Python bytecode. | The committed plugin folder is part of the reviewed candidate. An unignored database would change the digest on every index. |
| [Worker](../05_Software/aegis/integrations/shared/worker.mjs) and process-tree helper | Detached worker, tree kill on cancel, candidate fingerprints before and after, one verification lock per checkout. | Reuse for a maintenance job kind with its own reservation and no fingerprints. |
| [MCP server](../05_Software/aegis/integrations/shared/mcp.mjs) | Static `tools/list`; every call runs as `agent: 'aegis'`; results are pretty-printed JSON. | The role label is not identity. Budget the model-visible content in the adapter. |
| OpenCode `plugin.mjs` / `lib/config.mjs` | Registers its 11 tools by hand, not from `operations.mjs`; reviewers have an explicit tool allowlist. | Separate OpenCode registration and allowlist edits. |
| [Codex bridge](../05_Software/aegis/integrations/shared/bridge.mjs) | Fixed operation, value, and flag lists; `--role reviewer` refuses mutating operations. | Add the operations and `target`/budget options; reviewers refuse indexing. |
| Pi `review.mjs`; Claude and Qwen reviewer agents | Pi reviewers run with `--no-extensions` and read tools only; Claude and Qwen reviewers list native read tools only. | Graph access for reviewers is new wiring per host. |
| Shared `install.mjs` | Update and removal are refused while any `*.lock` file exists in the job cache, with a message about verification. | The message must name any active or uncertain AEGIS job. |
| Shared `runtime.mjs` | `AEGIS_PYTHON` and the recorded `runtime.json` select the Python interpreter for desktop hosts. | CodeGraph inherits AEGIS's interpreter selection; no separate executable path is needed. |
| `host-setup.mjs`, `claude/setup.mjs`, skills, READMEs, integration tests | Report or assert "11" tools or "eleven operations". | Derive reported counts from registrations; update text and tests. |
| [Release builder](../02_Tools/build_aegis_release.py) | Strict 17-file core payload inventory. | The plugin ships outside the core payload with its own builder. |
| [Host integration guide](../06_SoftwareDocu/Agent_Plugins.md) | OpenCode, Codex, Pi, Qwen Code, and Claude integrations already exist; their packages use Node and host-specific resources. | Reuse those optional adapters. CodeGraph must not require those integrations, Node, or a new MCP server. |

`[layout].source`, `[layout].tests`, and `[layout].docs` already provide useful scope. They are classification patterns, not always literal folders. For example, a documentation area can contain maintenance scripts; parser selection must remain distinct from workflow classification.

## 3. Architecture and ownership

```text
Application repository                          CodeGraph plugin (same Python)
  .agentic/aegis.toml --------------------------> scope/configuration
  source + tests + project manifests ----------> inventory + extraction
                                                     |
                                                     v
                                              codegraph.sqlite
                                                     ^
                                                     | read-only
Agent -> AEGIS know_graph_* -> python -I codegraph.py -> bounded query result
  |                                                        |
  +---------------- read cited source locations <----------+
```

### Two components, one optional cache

| Component | Owns | Does not own |
|---|---|---|
| AEGIS core | Configuration entry point, root resolution, database-path validation, bounded process dispatch, advisory availability, CLI interface. | Parsers, SQLite schema, graph traversal, indexing schedule. |
| CodeGraph plugin | Scope discovery, extractors, index creation/update, writer lock, recovery, schema compatibility, search/traversal, compact presentation, installation helper, ignore diagnostics. | AEGIS stages, task status, requirements, reviews, test outcomes. |
| Host adapter | Exposes the read operation and the maintenance job using the host's existing transport, and enforces the model-visible output budget. | Another graph database or parser implementation. |

Proposed source and delivery locations:

```text
AEGIS source repository:
  05_Software/aegis/plugins/codegraph/codegraph.py        # entry point
  05_Software/aegis/plugins/codegraph/codegraph/          # engine modules (scope, extraction, storage, queries, cli)
  05_Software/aegis/plugins/codegraph/queries/            # versioned extraction queries
  05_Software/aegis/plugins/codegraph/requirements.lock   # pinned wheels for vendoring
  05_Software/aegis/plugins/codegraph/README.md
  05_Software/aegis/plugins/codegraph/tests/              # engine tests
  05_Software/aegis/plugins/codegraph/tests/fixtures/     # small authored fixtures
  05_Software/aegis/tests/test_codegraph_bridge.py        # core tests with stub provider
  02_Tools/build_codegraph_release.py                     # assembles the plugin folder with vendored natives

Downstream repository, when installed:
  .agentic/aegis.py                                       # existing core, thin addition
  .agentic/aegis.toml                                     # project-owned configuration
  .agentic/plugins/codegraph/                             # add-on payload, committed
    codegraph.py
    codegraph/                                            # engine modules
    queries/
    vendor/<platform>-<abi>/                              # e.g. win_amd64-abi3, linux_x86_64-abi3
    MANIFEST.json                                         # plugin version, protocol, pinned versions, hashes
    NOTICES.txt                                           # third-party licenses
  .agentic/knowledge/                                     # shared parent for knowledge
    api-host.md                                           # example tracked component page
    codegraph/                                            # generated, ignored by Git
      codegraph.sqlite
      codegraph.lock
```

Keep the source organized into a few responsibility-based modules. Continue to distribute AEGIS core as one standard-library Python file.

The add-on is separately installable; ordinary AEGIS installation remains sufficient for all existing behavior. Installation and updates go through the plugin's installer (section 7), which copies the complete plugin folder into a quiescent checkout; enabling it is a separate, explicit configuration step. No recipient-side package resolution, plugin marketplace, background service, network access, or automatic application build is needed. Because the folder is committed, every clone and worktree has the plugin; each checkout keeps its own database.

Use one ordinary SQLite file at rest, plus a small lock file. SQLite may create a transient journal during writes; temporary files during a rebuild are also acceptable. Do not promise that one file is the only filesystem object at every instant.

Ignore `.agentic/knowledge/codegraph/`, including the lock, journals, and rebuild temporaries, but keep `.agentic/knowledge/*.md` tracked. The existing `components` command selects only top-level Markdown pages, so the generated subfolder does not become a component page. The database remains checkout-local and disposable; it is not merged between branches or distributed by cloning. Refresh it after a merge or branch switch; a new clone or worktree needs initial ingestion.

### Folder placement and ownership

| Location in a downstream checkout | Purpose | Git treatment |
|---|---|---|
| `.agentic/aegis.py` | Installed AEGIS companion CLI. | Track through the existing payload process. |
| `.agentic/aegis.toml` | Shared indexing scope and CodeGraph settings. | Project-owned, tracked. No machine-specific paths are needed. |
| `.agentic/plugins/codegraph/` | Add-on payload: engine source, queries, vendored natives, manifest, notices. | Tracked. Replaced wholesale on add-on upgrade; do not edit in place. |
| `.agentic/knowledge/*.md` | Human/agent-maintained component knowledge. | Tracked and reviewed with the source. |
| `.agentic/knowledge/codegraph/` | Generated SQLite index, its lock, and transient update/rebuild files. | Ignored through the CodeGraph ignore block; one local index per checkout/worktree. |

The default database belongs under `knowledge/codegraph/`, not under a separate `.agentic/cache/` tree. Keep the plugin separate from the database so upgrading or removing the plugin does not remove knowledge files. The indexer excludes the installed root `.agentic/` from ingestion, including the plugin and its own database; it does not recursively ingest its output.

`.agentic/AGENTS.md` lists every `.agentic/` location by owner. It must gain `.agentic/plugins/` as add-on payload and `.agentic/knowledge/codegraph/` as generated local data, and the upgrade instructions must say that a core upgrade keeps `.agentic/plugins/`.

### Invocation

AEGIS runs the plugin with its own interpreter and a fixed entry point:

```text
[sys.executable, "-I", "-B", "-X", "utf8", "<root>/.agentic/plugins/codegraph/codegraph.py", <operation>, ...]
```

- `shell=False`; no shell or environment expansion.
- `-I` (isolated mode) stops user site-packages, `PYTHONPATH`, and other `PYTHON*` variables from shadowing the vendored packages. Isolated mode also leaves the script directory off `sys.path`, so `codegraph.py` inserts its own folder and the matching `vendor/<platform>-<abi>/` folder at the front of `sys.path` itself.
- `-B` stops Python writing bytecode (`__pycache__`) into the committed plugin folder when it imports the engine modules; otherwise even a read-only query would write files. Isolated mode ignores `PYTHONDONTWRITEBYTECODE`, so the flag must be explicit. When the plugin is run directly, `codegraph.py` sets `sys.dont_write_bytecode = True` before importing any of its own modules. Spawned extraction workers inherit `-B` from the interpreter flags, and in standalone mode set it again when they re-run the entry module. Compiling the engine on every launch costs some startup time; CG-00 measures it.
- `-X utf8` sets UTF-8 mode explicitly, because isolated mode ignores the `PYTHONUTF8` variable the adapters pass.
- The interpreter is whatever runs `aegis.py`. Desktop hosts already select it through `AEGIS_PYTHON` or the recorded `runtime.json`, so CodeGraph needs no separate executable path.
- The plugin location is fixed. AEGIS never runs a configured program for graph knowledge.

A future document-retrieval plugin could place its derived database under `.agentic/knowledge/documents/`, while its original documents remain in the repository's configured documentation folders. This is a naming/placement convention only: do not create the folder, add its ignore rule, or introduce document ingestion until that plugin is implemented.

### Distribution and vendoring

- `02_Tools/build_codegraph_release.py` assembles the plugin folder: engine source, queries, and native modules unpacked from the wheels pinned in `requirements.lock`, for every supported platform and ABI. The build machine may download or cache wheels; recipients never do.
- Record plugin version, protocol version, pinned dependency versions, file hashes, and licenses in `MANIFEST.json` and `NOTICES.txt`.
- Target Windows x64 and Ubuntu x64 in one folder, so a team on mixed operating systems shares one committed copy. Other architectures are later targets. Use manylinux wheels whose glibc baseline covers the oldest supported Ubuntu release.
- Keep natives lazy-loaded and limited to the initial language set. Do not ship an all-language SDK, compiler, UI toolkit, model, or database service.
- Committed native binaries add repository history on each upgrade; keep native upgrades deliberate. Measure the folder size in CG-00 against the footprint target before committing it to downstream repositories.
- The plugin has no executable file of its own; it is always started through Python, so archive file modes carry no meaning.
- The database stays outside the plugin folder. A plugin upgrade preserves the repository cache, configuration, and workflow records.

### Windows and Ubuntu support contract

Both platforms are first-release requirements for scope discovery, ingestion, updates, SQLite queries, AEGIS dispatch, and installation. Windows runs natively, without requiring WSL, Bash, or Docker.

| Target | Delivered as | Invocation / platform checks |
|---|---|---|
| Windows x64 | The plugin folder with `vendor/win_amd64-*` natives. | PowerShell 5.1/7; `python` and `py -3` interpreters; spaces and Unicode in paths; drive-letter paths; termination of the indexer and its extraction workers; `msvcrt` locking; file replacement while readers are open. |
| Ubuntu x64 | The same folder with `vendor/linux_x86_64-*` natives. | `python3`; case-sensitive paths; symlinks; termination of the indexer and its extraction workers; `fcntl` locking; file replacement. |

CG-00 publishes the tested support matrix (CPython minor versions, the minimum Windows release, and the tested Ubuntu LTS releases) and records it in the manifest. Free-threaded Python builds are unsupported for indexing unless matching natives exist; they report `indexing_supported: false`.

Use the same CLI arguments, configuration schema, query protocol, and extraction rules on both platforms. Normalize indexed paths to repository-relative `/` form while retaining original filename case; convert to native paths at filesystem boundaries. Test LF/CRLF handling and Unicode source offsets so citations remain correct. Keep databases checkout-local and rebuild on relocation rather than sharing a live database between operating systems.

This repository has no CI today. Provision Windows and Ubuntu runners (CG-12) with three distinct environments:

- **Assembly:** builds the plugin folder from the pinned wheels when the natives are not already committed. Only this step may use the network or a wheel cache.
- **Test:** the existing development setup (a supported Python with `pytest`, Node.js 22+ for the host integration tests, and Git) runs the core suite, the plugin suite, the dispatch tests, and the integration tests against the assembled folder, offline.
- **Clean runtime:** a machine with only a supported Python and Git, and no extra packages, exercises dispatch, indexing, and queries through `aegis.py` against the assembled folder, offline. It includes a check that a separately installed `tree_sitter` does not shadow the vendored copy.

The "no extra packages" claim applies to the runtime, not to the test tooling. OS support for the engine does not prove that every third-party host desktop application supports that OS; verify supported host integrations separately.

## 4. Configuration and ingestion scope

### Proposed optional configuration

The following is a **new proposed contract**, not syntax implemented in AEGIS today:

```toml
[codegraph]
enabled = true
database = ".agentic/knowledge/codegraph/codegraph.sqlite"   # must stay in this folder

# Defaults; normally omitted.
include = []                 # extra paths beyond layout.source/tests
exclude = []                 # additional exclusions; takes precedence over include
include_untracked = true     # non-ignored untracked files when using Git
index_tests = true
python_import_roots = []     # only when import-root inference is wrong
max_file_bytes = 1048576
parse_timeout_seconds = 10   # per file, during indexing
max_results = 20
max_output_bytes = 8192
timeout_seconds = 5          # read queries only, not indexing
check_timeout_seconds = 30   # explicit whole-scope freshness check
index_timeout_seconds = 0    # explicit ingestion; 0 means no elapsed-time limit
```

- Absent `[codegraph]` or `enabled = false` means no provider process and no database access by normal AEGIS commands.
- The plugin entry point is fixed at `.agentic/plugins/codegraph/codegraph.py`; there is no `command` setting.
- `database` must name a file directly inside `.agentic/knowledge/codegraph/` whose name has the form `NAME.sqlite`, where `NAME` uses only letters, digits, `_`, and `-`. That rule keeps a configured name from colliding with SQLite's sidecars (such as `codegraph.sqlite-journal`), rebuild temporaries, or `codegraph.lock`. That folder is the one the ignore block covers and the writer lock protects, so a database anywhere else could be committed, change the reviewed candidate, or overwrite a source file on rebuild. The core resolves the path, including symlinks and junctions, and rejects anything else before dispatching. The provider enforces the same rule independently because it can be invoked directly. Reject graph input paths escaping the root.
- Default source scope is the union of `layout.source`, `layout.tests` when `index_tests` is enabled, and CodeGraph `include`. Documentation is not indexed; document knowledge belongs to a future `know_docs_*` plugin.
- Missing/empty source and test layout does not trigger an unrestricted disk scan. `scope` reports `scope_missing` and suggests configuring `[layout]` or `include` once.
- Keep `[check].ignore` and `[commands].workdir` independent: neither defines graph scope. Do not put indexing in `[commands]`, because `check --run` executes eligible entries there.
- The core validates enablement, database path, output bounds, and separate positive read/check timeouts plus a nonnegative indexing timeout (0 means no elapsed-time limit). Keep this set small, because the default config must document every key the core validates. The provider validates indexing settings and applies the layout matcher. Both read the same TOML; a matching-contract fixture suite prevents duplicated matcher behavior from drifting.
- A configuration digest covers only ingestion-relevant settings, built-in exclusions, extractor revisions, and inventory mode. Changes to test commands, review mode, or result limits do not require re-indexing.

### Discovery algorithm

1. Use the root supplied by AEGIS. Standalone invocation requires an explicit `--root` and defaults to that root's `.agentic/aegis.toml`.
2. In a Git repository, enumerate `git ls-files --cached --others --exclude-standard -z`, with untracked inclusion configurable. Inspect worktree bytes, including uncommitted edits; omit currently deleted files. Do not initialize Git or recurse into submodules.
3. When Git is not installed or the root is not a Git repository, walk only the explicitly scoped tree with `os.scandir`, pruning known output/dependency directories, and state `inventory=filesystem`. This fallback does not claim complete Git ignore semantics. When the root is a Git repository but listing fails, report the error instead of silently widening scope.
4. Apply layout selection and exclusions to normalized repository-relative POSIX paths. De-duplicate overlapping patterns. Apply size/type checks before reading large files.
5. Classify files separately from choosing their language. Explicit test paths and recognized test filenames receive the test role. Distinguish source, tests, manifests, migrations, generated files, documentation, and unsupported assets.
6. Select a vendored grammar and extractor by extension and content markers: `.py`/`.pyi` for Python; `.cs` for C#; `.ts`/`.mts`/`.cts` for TypeScript and `.tsx` for TSX; `.js`/`.mjs`/`.cjs` for JavaScript and `.jsx` for JSX.
7. Discover project metadata separately from source selection. Import roots and project ownership often depend on manifests outside the selected patterns, such as a root-level `pyproject.toml`, `package.json`, `tsconfig.json`, or `.sln`. Read the recognized manifest names (section 5) found in the selected source and test trees and in their ancestor directories up to the repository root, never above it and never inside excluded paths. Python import roots are inferred from these manifests and documented `src` layouts, with `python_import_roots` as an override; repository code is never executed to discover them. Manifests are recorded with their hashes in the indexed input manifest, so a changed manifest makes the index stale, but they add no source symbols.
8. Record skipped, failed, partial, and unsupported files with reasons. Counts by language and role make coverage visible.

Default exclusions cover installed root `.agentic` state (including the plugin folder and database), `.git`, dependency caches, `node_modules`, build outputs, generated/minified assets, binary archives, and vendored trees. Generated source such as `.Designer.cs` is classified and skipped by default, with its omission visible. Keep migrations as a separate searchable role rather than deleting their semantic history. Bulk SQL seed contents and document/media assets are not source-symbol input.

**Important for indexing AEGIS itself:** exclude the installed root `.agentic/`, not every directory named `.agentic`. The canonical source under `05_Software/aegis/template/.agentic/` is valid configured input.

`scope` previews selected patterns, file/byte totals, role/language counts, and skip reasons without creating the database. Ordinary repositories should need only enablement; `include`/`exclude` are exceptions, not a second repository map.

## 5. Extraction strategy and truthful graph semantics

### Initial language capabilities

| Input | Extraction strategy | Useful output | Important limits |
|---|---|---|---|
| Python | Tree-sitter Python grammar and scope-aware queries; never import repository modules. Import roots inferred from manifests and `src` layouts. | Modules, classes, functions/methods, parameters, assignment bindings, import expressions, call sites, name occurrences, enclosing scopes. | Syntax parsing is not runtime type resolution; monkey-patching, star imports, dynamic loading (for example `importlib.util.spec_from_file_location`), dynamic calls, and grammar-version gaps remain visible as unresolved. |
| C# | Tree-sitter C# grammar plus declaration/reference extraction and a conservative resolver. | Namespaces, class/interface/enum declarations, method/property/field signatures, parameter bindings, written base-type names, call/name occurrences. | No Roslyn/MSBuild execution, complete overload binding, generic type inference, preprocessor evaluation, or DI resolution. Partial declarations stay separate and are grouped by a candidate logical key. Razor files are unsupported. |
| TypeScript / JavaScript | Tree-sitter TypeScript/TSX and JavaScript grammars plus module/scope extraction, for the extensions listed in section 4. | Classes, interfaces where applicable, functions, methods/arrow functions, variables/parameters, imports/exports, calls and syntactic JSX references where supported. | Grammar support does not imply compiler type checking or resolution of aliases, callbacks, computed properties, decorators, or framework injection. |
| `.sln`, `.csproj`, selected package/TS config files | Line records, `xml.etree.ElementTree`, `json`, and a narrowly tested JSONC reader where necessary. | Project membership hints, declared project/package dependencies, literal import-resolution hints. | MSBuild conditions, globs/imported props, package exports, and bundler aliases may require evaluation unavailable here; label partial/conditional data. |
| Documentation / HTML / other languages | File inventory only. | Locations to read with ordinary tools. | No claim of code relationships; HTML-to-component and HTTP-client-to-server links are deferred. Markdown heading lookup belongs to `know_docs_*`. |

Extraction queries and resolver rules are versioned alongside pinned grammars. Syntax-tree node spans supply positions and keep comments/string content distinct from declarations. Normalize byte offsets to the documented line/column representation, including non-ASCII input. Detect Tree-sitter error/missing nodes; return safe unaffected facts with partial status, or mark the file failed when safe extraction is impossible. Do not interpret a recoverable syntax tree as proof that the program compiles.

Extraction support is narrower than grammar support and must be documented/tested. Unsupported forms remain inventory or unresolved occurrences. Missing vendored grammars indicate a packaging/compatibility problem; never silently substitute a regex parser or download a parser.

### Per-file parse budget

Indexing has no overall time limit by default, so one pathological file must not hang it. Each file gets `parse_timeout_seconds`. The same mechanism carries cancellation requests from the parent-liveness monitor and the optional deadline (section 6).

- Use Tree-sitter's own cooperative cancellation. As checked during the design review, the upstream Python binding exposes a progress callback for parsing, with the read-callback form of `parse`, and progress callbacks for query execution. If progress support exists only for the read-callback form, the extractor parses through a read callback rather than a byte buffer. CG-00 verifies this against the exact pinned binding and grammar versions.
- Cancellation must interrupt parsing promptly, stop expensive extraction queries, and leave the parser reusable or reset it before the next file.
- A cancelled or timed-out file is never published as successfully indexed. A file that exceeds its budget is recorded as `failed` with reason `parse-timeout`; its earlier facts are removed from the new generation.
- Callbacks are cooperative: they do not protect against a native crash or a hang outside the callback points. If the pinned implementation cannot meet these requirements, run extraction in a small pool of long-lived worker processes that the controller can terminate and replace. Start them with the `spawn` method (see "Writer lock" in section 6), and do not start one process per file.

### Facts and relationships

- Nodes: file, project, namespace/module, class/interface/type, callable, property/field, parameter, and supported variable binding.
- Definition evidence: path, start/end line, column, enclosing scope, short signature, language, file role, grammar version, and extractor revision.
- Relations: containment, declared import/project reference, written inheritance/interface reference, syntactic call, and identifier use. A reference can have **no resolved target**.
- Keep declared target spelling and source location even when linking fails. Store bounded candidate targets separately from direct links; do not fan every common name out to every declaration.
- Use resolution labels such as `direct-syntax`, `lexical-binding`, `candidate`, `unresolved`, and `external`. Do not invent numeric confidence probabilities.
- Candidate call targets are never displayed as confirmed runtime callers, even when a name has only one match in the index.
- Local variable identities include enclosing scope to handle shadowing. Start with definitions/parameters and supported lexical reads/writes; comprehensive data-flow and alias analysis are deferred.
- Related tests mean tests with observed/candidate references, not test coverage. Never create a `TESTS` proof edge from a name match.
- External package/module references are leaf records; the indexer does not fetch or ingest their implementations.

Prioritize declaration and location precision over recall. Ambiguity and missing relationships are acceptable when visible. Falsely confident relationships defeat the purpose of the plugin.

## 6. SQLite model, updates, and freshness

### Minimal logical schema

| Table | Contents |
|---|---|
| `meta` | Database schema (also stamped in the SQLite header as a fixed CodeGraph `application_id`), query protocol, plugin version, snapshot ID (random, never reused), generation counter, parser/grammar/extractor revisions, vendor platform/ABI tag, Python and SQLite versions, FTS5 availability, normalized checkout identity, configuration digest, completed build time, indexed content-manifest digest, optional Git HEAD. |
| `files` | Relative path, role, language, content hash, size/mtime, extraction status and concise reason. |
| `symbols` | Full ID, file, parent/scope ID, kind, simple/qualified name, compact signature, location. |
| `references` | Source file/scope/location, occurrence kind, target spelling, qualifier/arity when known, resolution status, optional target ID. |
| `edges` | Linked endpoints/relation plus the supporting reference or declaration location and resolution basis. |

Use ordinary indexes on names, qualified names, file IDs, relation kinds, and edge endpoints. Split identifier words for name search. SQLite comes from the user's Python, so FTS5 availability varies by build: basic lookup must work without FTS5, the plugin detects FTS5 at runtime and records it in `meta`, and full-text indexing remains an optional optimization. No embeddings, stored full source bodies, or generated LLM summaries in the base index.

Store extracted facts, not serialized full syntax trees. Initially reparse only changed files; Tree-sitter's in-memory incremental editing does not require a persistent process or AST cache here. Grammar/extractor upgrades invalidate the affected languages even when source bytes are unchanged.

### Symbol identifiers

- A symbol's full ID is a 128-bit digest of its stable key: path, scope, kind, name, normalized signature, and a disambiguator for duplicates. Line shifts should not normally change keys; renames can.
- JSON results carry the full ID. Text output displays the shortest unique prefix, at least 10 hex characters.
- Commands accept a prefix and resolve it against the whole current index, not only the displayed page. An ambiguous prefix returns a selection result; the plugin never guesses. A prefix that was unique can become ambiguous after re-indexing, which is acceptable.
- Collisions of full IDs are detected at index time and reported as an index failure.

### Index lifecycle

- `index` enumerates selected files and hashes eligible contents; reuse extraction for unchanged content and parser/grammar/extractor revisions. Hashing is cheaper than reparsing and catches equal-size edits that timestamps alone can miss.
- Add new files, remove deleted/now-excluded facts, and replace facts for changed files. Parse failure removes the old facts from the current generation and records failure; old successful facts must not masquerade as current.
- Initially re-resolve candidate relationships against the complete symbol inventory after a change batch. This is simpler and safer than reverse-invalidation logic. Optimize only after benchmarks justify it.
- Every published generation gets a random 128-bit snapshot ID that is never reused, including after the database is deleted, recreated, or rebuilt; a counter alone would restart and make old identifiers look valid. Every result carries the snapshot ID.
- A page token is bound to its snapshot ID and to its request: action, target, filters, ordering, and limit. A token from an earlier snapshot returns `expired`; a token reused with a different request is a malformed request (`status: error`), so it can never silently skip records in another query.
- One cache per checkout/worktree. Root identity mismatch is reported, never silently shared across projects. Cache databases are rebuilt after relocation or schema incompatibility.

### Write preconditions

Every indexing run (incremental update, recovery, or rebuild) checks these in order. Steps 1 and 2 write nothing, so a refusal leaves the filesystem untouched:

1. **Paths and configuration.** Validate the configuration and the database path and name (section 4).
2. **Git state.** In a Git checkout, the provider asks Git whether the database folder is ignored and whether anything in it is tracked, checking the database, lock, and temporary-file names. If the folder is not ignored or holds tracked files, indexing refuses before any filesystem change, including creating the database folder or the lock file: `status: error` with reason `destination_not_ignored` or `destination_tracked`, exit 1, and the remedy (run `codegraph install`, or untrack with the printed `git rm --cached` command). This is what makes "indexing never changes a candidate" true rather than assumed. Without Git (filesystem inventory) there is no candidate to protect and the check is skipped.
3. **Writer lock.** Taken as described below; this is the first step that may create anything.
4. **Ownership.** Before opening an existing database read-write, for any purpose, the provider reads the `application_id` in its file header. A file without the CodeGraph ID is never opened read-write: indexing refuses and reports it, so a foreign SQLite database or any other file is never recovered, migrated, or replaced. A missing target is created fresh, with the ID set before any other write. Readers report a foreign file as `index: incompatible`.

Only after these four steps does the provider recover, update, or rebuild.

### Writer lock

SQLite's own lock covers one transaction, not the whole "build a temporary database, validate it, then replace" procedure, and a host job reservation does not see a terminal invocation. CodeGraph therefore owns the writer lock:

- Before recovery, incremental update, or rebuild, the provider takes an exclusive OS lock on `.agentic/knowledge/codegraph/codegraph.lock` (`msvcrt.locking` on Windows, `fcntl.flock` on Ubuntu) and holds it for the whole operation, including replacement.
- The operating system releases the lock when the process exits, even when it is killed, so no lock can go stale and nothing is deleted because it is old. A lock file left on disk after a crash is not locked.
- The lock file path is stable. The lock file is never deleted, renamed, or recreated, including after unlocking and during rebuild replacement. On Ubuntu, a process holding a lock on the old file and a newcomer locking a fresh one would both believe they are the only writer. The only exception is the final teardown step of `uninstall` (section 7), after all provider activity has stopped and the plugin folder is gone.
- Extraction workers never hold the lock. With `fcntl.flock`, the lock belongs to the open file description, and a child created by `fork` shares it, so workers that outlived a killed indexer would keep the database locked. Python's multiprocessing uses `fork` on Linux before Python 3.14, so CodeGraph selects the `spawn` start method explicitly. On Windows, Python file descriptors are not inherited by default.
- Releasing the lock does not repair an interrupted SQLite transaction; that case remains `needs_recovery`.
- A second writer reports `index: busy` immediately.
- The database folder must be on a local filesystem; network drives are unsupported in the first edition because their lock semantics are unreliable.

| Lock | Protects |
|---|---|
| Host maintenance reservation (section 8) | Duplicate host job submission and job tracking. |
| CodeGraph writer lock | Every indexing caller, including terminal invocations, throughout ingestion, recovery, rebuild, and replacement. |

### Publication and recovery

- A single writer publishes one transactional generation. Short read transactions see a consistent completed generation.
- Use SQLite's rollback journal in its default `DELETE` mode, so no journal remains after a committed transaction. Do not require WAL sidecars or a daemon.
- **Let SQLite classify the database state; never infer it from files on disk.** A `-journal` file can belong to an active write or be a harmless leftover, and only SQLite can tell whether it is hot. Most of an indexing run does not block reads at all: while the indexer parses, builds a temporary database, or holds SQLite's RESERVED lock, readers keep serving the last completed generation. Readers use a short busy timeout so a brief commit does not surface as `busy`; a reader that still gets `SQLITE_BUSY` reports `busy`. A read-only connection that gets `SQLITE_READONLY_ROLLBACK` (exposed by Python 3.11+ as `sqlite_errorname`) has found a hot journal from an interrupted write and reports `needs_recovery`. A journal SQLite does not treat as hot does not affect reads.
- **Recovery** happens only in an explicit `index`, after the write preconditions: the provider opens the existing database read-write and lets SQLite roll the hot journal back itself. Readers never repair, and nothing deletes a journal by hand.
- **Rebuild** (incompatible schema, relocation, or `--rebuild`), after the write preconditions:
  1. The ownership check applies to an existing target. The `application_id` sits in the file header, so it stays readable even when the rest of a damaged CodeGraph database is not; any other file is refused.
  2. Recover the existing database first, if it is recoverable, so no hot journal is left beside it.
  3. Build the new database under a temporary name in the same folder, commit, close it so it has no journal, and validate it.
  4. Replace the target, with bounded Windows sharing-conflict handling while readers hold it open. If the old database could not be recovered and is being discarded, remove its journal together with it, before the new file takes the name. A journal must never be left beside a database it does not belong to; SQLite would apply it to the wrong file.
  5. On any failure, keep the previous usable database.
- Check file metadata around reads and retry boundedly if source changes. If inputs change during publication checks, report a non-current snapshot rather than claim a consistent live tree.

### Parent liveness

- When AEGIS launches indexing, it passes `--watch-stdin` and gives the provider a stdin pipe it never writes to. AEGIS keeps the write end open until indexing completes, and no other child process inherits it; an inherited copy would keep the pipe open after AEGIS died.
- A monitor thread in CodeGraph turns end-of-file into a cancellation request. Cancellation stops parsing, extraction, resolution, and publication, stops extraction workers, and leaves the last published generation intact.
- If AEGIS dies for any reason, including a host shell-tool timeout, the pipe closes and indexing stops. This works when `index_timeout_seconds = 0`, needs no process-ID polling, and is unaffected by PID reuse.
- The pipe does not cover a host that disappears while `aegis.py` keeps running; host job cancellation and the optional deadline cover that case. At worst the indexer finishes normally and releases its lock.
- A person running the plugin directly in a terminal does not pass the flag.
- An optional `--deadline` passed by AEGIS is enforced by the provider itself, through the same cancellation path, in addition to AEGIS's own timeout.

### Freshness without a full scan for every question

Separate **snapshot identity**, **source freshness**, and **extraction completeness**:

1. Every query returns snapshot ID, generation, indexed timestamp, configuration compatibility, and coverage limitations.
2. By default, hash-check the bounded set of source files cited in the response. Suppress invalid current-location claims when those files changed. This is `cited-files-checked`, not a guarantee about the entire repository.
3. Incoming references can be missing from newly added or changed files outside that result. Thus every ordinary query also states `scope-freshness=not-fully-checked`. An empty result means no matches in the indexed scope, never no usages anywhere.
4. `know_graph_check` explicitly inventories/hashes the selected scope read-only and compares it with the recorded manifest. It reports additions, changes, deletions, failures, project-metadata changes, and configuration drift. It does not repair the index or store a new freshness timestamp.
5. Run `know_graph_index` explicitly when the check reports missing/stale data and cache-write authority permits it. Avoid per-edit hooks, per-turn indexing, and repeated status polling. Final code verification remains the existing AEGIS process.

Changing HEAD alone neither proves staleness nor proves freshness: worktree content and scope matter. Refreshing the graph never changes task anchors, recorded review evidence, requirements, or test selection.

### Selected policy: strictly read-only queries, explicit maintenance

Navigation, status, and freshness checks never create, refresh, migrate, repair, or write the database. They create no cache directories, logs, or journal records. Missing, stale, incompatible, busy, or unrecoverable data yields an explicit result and an ordinary-search fallback. No cache-maintaining query mode is included in the first edition.

Every response reports four separate things, so that an empty successful search is never confused with an unavailable index. CG-02 freezes the exact JSON envelope; the vocabulary is:

| Field | Values | Meaning |
|---|---|---|
| `status` | `ok`, `ambiguous`, `not_found`, `expired`, `unavailable`, `disabled`, `error` | The outcome of this request. `ok` includes an empty result list. `ambiguous` returns choices instead of picking one (a name or ID prefix with several matches). `not_found` covers an unknown symbol ID, a prefix with no match, and an unindexed file path. `expired` covers a page token from an earlier snapshot. `unavailable` means the index cannot serve the request (see `index`). `disabled` is produced by the core without starting the plugin. `error` covers a check that cannot start (for example, Git listing fails), corruption, protocol mismatch, a page token reused with a different request, and a refused write precondition. |
| `index` | `ready`, `missing`, `incompatible`, `busy`, `needs_recovery` | The database state. `incompatible` means an unsupported schema or extractor revision, or a file that is not a CodeGraph database. `busy` means a reader still got `SQLITE_BUSY` after its short busy timeout or, for an indexing request, another indexer holds the writer lock. `needs_recovery` comes from SQLite as described under "Publication and recovery". |
| `freshness` | `current`, `stale`, `unknown`, `not_fully_checked` | `current`, `stale`, and `unknown` come only from `know_graph_check`; an interrupted or timed-out check is `unknown`, never `current`. Ordinary queries report `not_fully_checked`. |
| `indexing_supported` | `true`, `false` | Whether this Python has matching vendored natives. When `true`, `python_support` is `tested` or `untested`. |

A current but partially extracted snapshot remains incomplete. A successful check describes the inspected snapshot, not future edits. Normal queries identify their own narrower cited-file checks and never inherit a global-current claim automatically.

The development agent manages this at useful boundaries:

1. At task start/resume, when graph navigation is needed, run `know_graph_check` once.
2. For missing/stale/needs-recovery data, run `know_graph_index` as a separate permitted write operation; otherwise ask the developer or use ordinary search. Initial ingestion creates the local database; subsequent runs update it incrementally.
3. After checkout/pull/merge or a meaningful batch of edits, invalidate the earlier check and repeat before relying on cross-file relationships. An identical new branch does not require full re-ingestion.
4. Read the cited source before editing or forming behavior claims. Report unresolved/partial data without retrying the same graph command repeatedly.
5. Before reviewer handoff, the coordinator can refresh the index. Reviewers may check/query it but cannot index; if stale, they use source search or request coordinator maintenance.

This is a short agent instruction, not a new AEGIS stage, watcher, automatic Git hook, or responsibility placed on the developer after each keystroke. Refreshing derived cache data grants no source-edit, test, or publication authority.

## 7. Minimal access contract for agents

### Proposed read-only AEGIS CLI

Use flat top-level commands with positional targets, matching AEGIS's existing flat parser structure. `know_` identifies repository knowledge and `graph` identifies its source. CodeGraph remains the plugin/product name and `[codegraph]` remains its configuration table.

```text
python .agentic/aegis.py know_graph
python .agentic/aegis.py know_graph_check
python .agentic/aegis.py know_graph_find "OrderRepository"
python .agentic/aegis.py know_graph_file "src/OrderRepository.cs"
python .agentic/aegis.py know_graph_symbol 3f9a1c07be
python .agentic/aegis.py know_graph_callers 3f9a1c07be
python .agentic/aegis.py know_graph_refs 3f9a1c07be
```

The initial read-only CLI contains seven commands:

| Command | Result |
|---|---|
| `know_graph` | Availability, generation, scope/coverage counts, recorded freshness metadata, supported languages, ignore/tracking diagnostics for the database folder, and whether this Python can index. No positional argument or whole-scope scan. |
| `know_graph_check` | Explicit whole-scope content-hash comparison against the saved manifest; read-only, with no positional argument. Returns freshness and bounded differences without repairing them. |
| `know_graph_find <name>` | Ranked symbols with IDs, signatures, roles, and source locations. Ambiguous names return choices instead of silently selecting a symbol. |
| `know_graph_file <path>` | Bounded symbol outline of one indexed file. The target is a repository path, normalized with the core's existing `repo_path_arg`. |
| `know_graph_symbol <id>` | One symbol's signature, containing scope, definition, and small callers/callees/references neighborhood. |
| `know_graph_callers <id>` | Incoming syntactic call references and candidate callers, with resolution labels and locations. |
| `know_graph_refs <id>` | Identifier references to the symbol, with reference kinds, resolution labels, and locations. |

Normal use requires no flags or nested subcommands. Use the ID or unique prefix returned by `know_graph_find` for symbol-specific commands, so overloads and duplicate names are not guessed. An ID that is no longer valid returns `not_found`, and an ambiguous prefix returns `ambiguous`.

All seven read registrations set an operation constant and route to one shared dispatcher. Configuration loading, database-path validation, bounded process execution, and response handling are implemented once. The read operations are `status`, `check`, `find`, `file`, `symbol`, `callers`, and `refs`; CodeGraph can share internal traversal code between them. A separate eighth command, `know_graph_index`, uses the same transport with explicitly mutating semantics.

Each of the eight commands needs its own `CLI.md` section, because the existing structure test requires one per parser command. Keep each section short and point to one shared explanation of budgets, statuses, and fallback, so an agent does not need the whole reference to run a query.

Optional `--json`, `--limit`, `--max-bytes`, and a request-bound page token (section 6) support adapters and exceptional larger results; defaults come from configuration. `find` may also accept optional path/kind/role filters. These options do not change the flat command structure. Default to one-hop neighborhoods and bounded traversal work; additional relationship-specific commands are deferred until needed.

Reserve `know_docs_*` as a future naming convention for document knowledge, for example `know_docs_search` and `know_docs_show`. Do not register placeholder commands or implement RAG in this change. That prefix describes the source, allowing a future document provider to use full-text search, vector retrieval, or both without exposing its storage engine in the command names. Avoid a generic cross-provider framework until another provider actually exists.

### Separate producer commands

Expose maintenance as a flat AEGIS command so a developer or authorized development agent does not need to locate the plugin:

```text
python .agentic/aegis.py know_graph_index
python .agentic/aegis.py know_graph_index --rebuild
```

Ordinary invocation creates a missing index, recovers a hot journal, or incrementally updates the existing compatible index. `--rebuild` explicitly replaces an incompatible/relocated database through the transactional rebuild procedure. This command writes only inside `.agentic/knowledge/codegraph/`: the configured index, its lock, and its temporary files. It does not change application files, configuration, component Markdown, or AEGIS records. Keep its indexing timeout separate from the short query timeout, with visible progress on stderr and clean cancellation; an index failure returns nonzero. From the CLI it runs synchronously. Standalone equivalents remain available:

```text
python .agentic/plugins/codegraph/codegraph.py scope --root .
python .agentic/plugins/codegraph/codegraph.py index --root .
python .agentic/plugins/codegraph/codegraph.py index --root . --rebuild
```

On Ubuntu use `python3` when that is the installed interpreter command. When running these by hand, prefer the same `-I -B -X utf8` flags AEGIS uses: the entry point already disables bytecode writing and puts its own folders first on `sys.path`, but only `-I` also keeps user site-packages and `PYTHON*` variables out.

These are deliberate maintenance operations. A query never installs the add-on, creates an empty database, runs ingestion, modifies source, or updates a journal. The plugin runs independently of AEGIS and consumes the shared configuration contract.

### Installation, update, and removal

```text
python -I -B -X utf8 <extracted-release>/codegraph.py install --root <checkout>
python -I -B -X utf8 .agentic/plugins/codegraph/codegraph.py uninstall --root .
```

The installer lives in the plugin, not in AEGIS core. Install and update run from an extracted release, so the new version installs itself rather than relying on the old installed copy. Both commands use the same interpreter flags as AEGIS dispatch. Install and update:

- Require a quiescent checkout. The installer tries the writer lock without waiting and refuses while any indexer holds it, whether a host job or a terminal started that indexer. Host job reservations do not see terminal invocations, so they are not this check.
- Validate the release's own files against its `MANIFEST.json` before touching the checkout.
- Compare an existing plugin folder with the hashes its own `MANIFEST.json` recorded. Locally modified or unknown files are an ownership conflict: the installer refuses and lists them instead of overwriting them. Python bytecode caches are generated files, not conflicts.
- Stage the new files, replace the plugin folder, and restore the previous files if any replacement fails, for example when Windows keeps a native module loaded.
- Never edit `aegis.toml` or anything outside the plugin folder and the owned ignore block.
- Write a CodeGraph-owned `.gitignore` block covering `.agentic/knowledge/codegraph/`, preserving all other content and the file's newline style.
- Use markers that share no text with AEGIS's own `# AEGIS:BEGIN (managed by .agentic/aegis.py init)` and `# AEGIS:END` markers, for example `# CODEGRAPH:BEGIN (managed by codegraph install)` and `# CODEGRAPH:END`. Tests cover both blocks together, including `init` removing its block when `commit_fingerprints = true`.
- Print the `[codegraph]` snippet for the developer to add. It does not rewrite `aegis.toml`; Python's standard library cannot write TOML, and AEGIS core gains no TOML-writing dependency.
- Report, without changing anything, whether the database folder is correctly ignored and untracked, not ignored, or already tracked despite the ignore rule. Adding an ignore rule does not untrack a file; the plugin never removes files from Git and prints the command for a human to run. Indexing refuses to write until a not-ignored or tracked state is resolved (section 6, "Write preconditions").

`uninstall` deletes generated data, so it is explicit and stricter:

- It takes the writer lock without waiting, holds it for the whole removal, and refuses while any provider holds it.
- Before deleting anything, it lists both owned folders and refuses if either holds a file it does not own. In the database folder it owns the lock file, `NAME.sqlite` files carrying the CodeGraph `application_id`, their SQLite sidecars, and rebuild temporaries. In the plugin folder it owns the files listed in `MANIFEST.json`, unmodified, plus Python bytecode caches.
- It deletes the database files first, then the plugin folder, so no provider from this checkout can start again. Only then, as final teardown, it releases the lock and deletes the lock file and the empty database folder. Last, it removes the CodeGraph ignore block.
- It touches nothing else: `.agentic/knowledge/*.md`, `aegis.toml`, and all unrelated content stay. It prints the `[codegraph]` table to remove from `aegis.toml`, and the documentation states plainly that uninstall deletes the local index.

**Plugin changes during indexing.** Because the plugin folder is committed, updates also arrive through Git, and a branch switch or an uncommitted edit can change engine code or extraction queries without changing the release version. The instructions say not to pull, switch branches, or update the plugin while it is indexing. As a publication safeguard, the indexer computes a plugin-content identity from the actual files in the plugin folder (paths and contents, not the hashes listed in `MANIFEST.json`) when it starts, and again immediately before publication. If they differ, it discards the unpublished work, keeps the last completed generation, and returns `status: error` with reason `plugin_changed`. This protects what gets published; it does not make replacing code mid-run safe.

The same diagnostics appear in `know_graph` status output.

### Process and response contract

- AEGIS maps the selected `know_graph` / `know_graph_*` command to its validated operation and launches `sys.executable -I -B -X utf8 .agentic/plugins/codegraph/codegraph.py` with absolute root, config, and database paths, the protocol version it expects, bounded query arguments, and the target after `--`, so a target beginning with `-` is never read as an option. It launches only for explicit graph-knowledge calls and never imports plugin code into its own process.
- The provider supports a compact text response and one JSON document on stdout with `schema = 1`, `provider = "codegraph"`, a separate integer `protocol`, and the plugin version. JSON fields include action, status, snapshot ID, generation, freshness, coverage, results, truncation, and next-page information.
- Keep JSON compatible with the current adapter's outer `schema == 1` check. The core validates the CodeGraph protocol in every response; adapters validate the AEGIS envelope. Human progress goes to stderr only; queries write nothing to stderr on success. Do not return the same result as both long text and JSON to the model.
- Text and JSON enforce result and byte budgets, including metadata. Reserve room for warnings/truncation. Truncate at record boundaries so JSON stays valid. Report `has_more` rather than running expensive full counts.
- Bound process time, stdout/stderr collection, query length, file reads, and SQL traversal work. A process output cap must be enforced while collecting, not after an unlimited capture; on Windows this needs reader threads. On Ubuntu, start the provider with `start_new_session=True`, as `run_command` already does: `kill_tree` kills the child's whole process group there, and without a new session that group would include AEGIS itself and whatever launched it. Kill and reap a timed-out reader with `kill_tree` and leave its cache untouched. Whole-scope checks use a separately documented check budget and return `unknown` if interrupted; indexing uses the maintenance budget and the stdin liveness pipe.
- Readers open SQLite using a correctly escaped read-only URI and `query_only`; never use a normal connection that creates a missing file. SQL values are parameterized; there is no arbitrary SQL or shell-query interface.
- Exit codes: responses with `status` `ok`, `ambiguous`, `not_found`, `expired`, `unavailable`, or `disabled` exit 0, the non-`ok` ones with a concise fallback instruction. `status: error`, malformed requests detected by the dispatcher, process failures, and indexing failures exit 1. Argparse usage errors exit 2, as they do for every AEGIS command today, and the new `CLI.md` sections say so. Empty successful results are distinct from failure. Do not alter other AEGIS commands' exit policies.

### Versioning and compatibility

- CodeGraph has its own release version, recorded in `MANIFEST.json`.
- The query protocol has a separate integer version. AEGIS passes the protocol it expects; the provider answers in that protocol or returns `status: error` with reason `protocol`, which the core reports as a protocol failure.
- Adapters identify supporting AEGIS releases from `python .agentic/aegis.py --version` and a documented compatibility table, cached per checkout. On an older core they report the capability as unavailable without invoking anything else, and never parse argparse error text.
- The compatibility table lists AEGIS core versions, protocol versions, and CodeGraph versions that work together.

Illustrative compact output, with fictitious symbols and locations:

```text
CodeGraph | generation=42 | cited-files=checked | scope=not-fully-checked | parser=tree-sitter
OrderRepository.Save(Order) | src/OrderRepository.cs:80-105 | symbol=3f9a1c07be
Candidate callers: OrderService.Save | src/OrderService.cs:42
Declared interface: IOrderRepository | src/IOrderRepository.cs:8
Related test reference: SaveTests | tests/SaveTests.cs:31 (not coverage)
Read: src/OrderRepository.cs:80-105; src/OrderService.cs:35-48
Shown=3 | more=no | unresolved calls remain; verify source before editing.
```

## 8. Small-model interaction and host integration

### One capability, a few actions

Expose one `aegis_know_graph` read-only tool in host integrations, with `action` in `status`, `check`, `find`, `file`, `symbol`, `callers`, or `refs`, and a `target` required for every action except `status` and `check`. Validate action/target combinations and retain optional bounded output controls. Add `know_graph` to the Codex bridge with the same action/target contract. The adapter maps each operation to the corresponding flat AEGIS CLI command; the bridge syntax is a host interface, not another core command hierarchy. Queries and checks are bounded direct calls.

Expose `aegis_know_graph_index` separately as a cache-writing coordinator operation (or explicit CLI maintenance where host registration is unavailable). It accepts only indexing/rebuild inputs, never arbitrary shell text; the Codex bridge has a separate `know_graph_index` operation. Do not add `index` to the read-only tool's action enum or silently convert a query to indexing. Existing host permissions still govern access; coordinator role labels are cooperative guards, not OS authentication.

Use existing transports: native tools in OpenCode/Pi, existing local MCP in Qwen Code/Claude, and the Codex plugin bridge. No new server is necessary.

### Host-triggered indexing as a maintenance job

The adapter's direct call has a 60-second timeout and on abort kills only the Python child, so host-triggered indexing runs as a job:

- Reuse the existing detached worker and process-tree termination, with a new job kind `codegraph_index`.
- Indexing takes its own checkout-scoped reservation, separate from the verification lock, so it neither blocks nor is mistaken for validation.
- Maintenance jobs record no candidate fingerprints, test results, or verification verdicts.
- Exact job IDs identify either job kind. `aegis_job` without an ID keeps its existing verification behavior; maintenance status is selected explicitly by ID or kind.
- Cancellation keeps the worker alive as the job's supervisor, as the existing worker already does for verification jobs. It terminates the execution subtree below the worker (`aegis.py`, the provider, and its extraction workers). The worker then observes completion, records `cancelled`, closes its output handles, and releases its reservation.
- A worker that dies itself is the exceptional case: the job reads as interrupted, and its reservation is not cleared automatically, matching existing behavior. That reservation recovery is separate from the provider's writer lock, which the OS releases when the provider exits. The stdin liveness pipe stops a provider whose `aegis.py` was killed.
- Installer update/removal messages say "active or uncertain AEGIS job" instead of "verification", because either kind can block an update of the host integration. These host-side checks see host jobs only; the CodeGraph installer's writer-lock check is what covers indexing started from anywhere.

### Output budgets reach the model, not just the provider

Hosts wrap adapter results and several pretty-print them, so a provider limit is not the model-visible limit. The adapter therefore:

- Requests a provider budget below the host budget, reserving room for wrapper metadata and error notices.
- Serializes graph results compactly and returns either the provider's compact text or its JSON, never both.
- Enforces the final model-visible content budget; when a result is too large, it requests or renders fewer complete records. It never cuts serialized JSON in the middle.

Tool schemas: Pi, MCP, and OpenCode register tools statically, so the two CodeGraph tools stay listed when the feature is disabled and answer with a short availability result; agents are told not to retry an unavailable capability in the same session. The Codex bridge adds no tool schema, only skill text. Measure and minimize the added schema size; do not promise it disappears when disabled.

### Host wiring

| Host or file | Change |
|---|---|
| `shared/operations.mjs` | Add the read operation and the maintenance operation. Pi and MCP pick them up from here. |
| `shared/adapter.mjs` | Command mapping, budgets, compact serialization, AEGIS version gating, maintenance job submission. |
| `shared/worker.mjs` | Maintenance kind without fingerprints or verdicts. |
| `shared/bridge.mjs` | Add both operations and the `target`, `limit`, `max-bytes`, and page options; `--role reviewer` refuses indexing. |
| OpenCode `plugin.mjs` | Register both tools by hand, matching the shared definitions. |
| OpenCode `lib/config.mjs` | Coordinator keeps `aegis_*`; reviewer allowlist gains only the read tool. |
| Claude and Qwen reviewer agents | Add only the read tool to their tool lists. |
| Codex reviewer agents | Mention the read operation with `--role reviewer`. |
| Pi reviewers | Keep no AEGIS tools; they use ordinary source reading. |
| `shared/host-setup.mjs`, `claude/setup.mjs` | Derive reported tool counts from registrations instead of hard-coding them. |
| Skills, READMEs, integration tests | Replace "eleven operations" and the asserted counts. |
| `shared/install.mjs` | Message names any active or uncertain AEGIS job. |

### Reviewer access and trust

- The plugin is committed Python source in the checkout, reviewed with the candidate, and run by the same interpreter as `.agentic/aegis.py`, which reviewer operations already execute. It has the same trust level as the core: no more, no less. No configured programs are run.
- The read tool's description states that it runs the checkout's plugin code.
- Maintenance is unavailable through reviewer tool configuration. The MCP server reports every call as `agent: 'aegis'`, so the role label cannot identify a reviewer; reviewer tool lists are the control.
- Reviewers without graph access, such as Pi reviewers, read cited source with their existing read tools.

### Short agent instruction to add

> When CodeGraph is enabled and needed, run `know_graph_check` at task start/resume and after branch/pull/merge or meaningful edits. If missing, stale, or needing recovery, use the separate `know_graph_index` operation only with cache-write authority; otherwise use ordinary search. Find the symbol, inspect its compact context, then read cited source. Queries never refresh the database. Reviewers check/query only. Treat candidate links and related tests as hints, not proof; graph results do not change AEGIS verification.

Keep this guidance in one place in the installed workflow contract and reference it from host skills. Do not paste the database schema or extractor manual into the system prompt. Preserve existing `brief` and `summary` output; provide discoverability through the small capability description, not repository maps on every resume.

### Retrieval and context budgets

- Default `know_graph_find`: at most 20 entries and 8 KiB of provider output, about 2-2.5K tokens or roughly 2% of the 128k baseline; typical targeted answers should be smaller.
- Default `know_graph_symbol`: compact signature, source range, and a limited neighborhood within the same budget, so ordinary navigation takes roughly two graph calls.
- Default output does not include function bodies. Use the host's read tool for selected ranges; do not duplicate whole files in graph replies.
- Cap an explicitly enlarged response at 32 KiB in the first edition; prefer paging/refinement over broad dumps.
- Rank exact qualified names first, then exact simple names, prefixes/identifier terms, and paths; use deterministic tie-breaking. Keep test/migration roles visible and selectable.
- Byte limits are real limits, not claimed token counts. Use deterministic output-size checks; no tokenizer package or model-specific evaluation is required by the plugin.
- Store important discovered paths in the existing Handoff when relevant. Do not copy result pages or create a second task-memory store. Reuse results only for the same generation and selected source snapshot.

The plugin remains model-independent and makes no model requests itself. Its interface stays small through short action names, explicit ambiguity/freshness metadata, and source locations rather than large context dumps.

## 9. Required AEGIS changes

All implementation edits belong in canonical source first, followed by the normal payload/integration update process. Do not patch downstream installed copies as the primary implementation.

| Area | Planned change | Compatibility boundary |
|---|---|---|
| `template/.agentic/aegis.py` | Commented, default-disabled `[codegraph]` guidance; shape validation for the few core keys; database-path validation; seven read-only flat registrations plus `know_graph_index`; one dispatcher that runs `sys.executable -I -B -X utf8` on the fixed entry point, in a new process session on Ubuntu, with a bounded reader, separate read/check/index budgets, `kill_tree` on timeout, the stdin liveness pipe for indexing (write end held until completion and not inherited by other children), and protocol validation. | Remains one stdlib file; no SQLite/parsers in core; disabled projects retain current command output/behavior. |
| `template/.agentic/CLI.md` | Eight short command sections sharing one explanation of budgets, statuses, fallback, and exit 2 for usage errors. | Existing sections unchanged. |
| `template/.agentic/AGENTS.md` | Ownership table entries for `.agentic/plugins/` (add-on payload) and `.agentic/knowledge/codegraph/` (generated, ignored); upgrade instructions keep `.agentic/plugins/`; the short navigation instruction. | No new stage, mandatory graph gate, or replacement of required reads/tests. |
| `integrations/shared/*`, host files | Changes listed under "Host wiring" in section 8. | Existing operation schemas stay unchanged; no detached verification job for a query; index maintenance is not verification evidence; no new Node dependency; reviewer access remains read-only. |
| Plugin installation | `codegraph install` installs or updates the committed plugin folder in a quiescent checkout, writes the CodeGraph ignore block, and prints the config snippet; `uninstall` reverses it. | Existing AEGIS core packages need not bundle CodeGraph; preserve user edits and other plugins. |
| This repository's `.agentic/aegis.toml` | Add `05_Software/aegis/plugins/` to `[layout].source` and its tests folder to `[layout].tests`; add a `[commands]` entry for the plugin suite. | Without this, plugin edits raise `outside-layout`/`uncovered-source`, and validation never runs the plugin suite. |
| Tests/docs/install copies | Compatibility tests; package guides, configuration guide, small-model guidance, and maintained mirrors. | No assertion of desktop/model behavior from backend-only tests. |

Keep ingestion outside `check --run`, `test`, `brief`, `summary`, and `init`. `init` may advertise optional settings but must not install or execute the plugin. Static config checking can report malformed core-validated CodeGraph settings without opening its database. Cache absence/staleness does not become a new strict-validation failure or reduce the existing full verification scope.

The committed plugin folder is part of every candidate fingerprint and diff, like the rest of the tracked tree. The database is confined to `.agentic/knowledge/codegraph/`, and indexing refuses to write unless Git confirms that folder is ignored and untracked, so indexing never changes a candidate. Index freshness checks the plugin's recorded parser/protocol versions rather than repeatedly hashing its files.

## 10. Implementation backlog and acceptance criteria

Work items are implementation-sized slices, not new AEGIS stages. Implementation runs as AEGIS tasks with requirement records, grouped by coherent deliverables rather than automatically one task per row. Complete each slice with focused behavior tests. Do not create all host extensions before the standalone query path proves useful.

### Open items before implementation

- Which pinned packages ship abi3 wheels, and the resulting support matrix (CG-00). This decides how many native sets the folder carries; Python versions outside the tested matrix stay unverified either way.
- Whether canonical source also commits the vendored natives or only assembled plugin folders do. This decides whether CI needs an assembly step before tests and where the plugin suite finds its natives. The AEGIS repository's own install under `.agentic/plugins/codegraph/` is committed either way.
- The measured folder size against the 30 MiB target.

### Backlog

| ID | Deliverable | Depends on |
|---|---|---|
| CG-00 | Vendored-parser feasibility slice | None |
| CG-01 | Config, layout matching, metadata discovery, and read-only scope preview | None |
| CG-02 | Protocol specification, fixtures, and stub provider | None |
| CG-03 | SQLite storage and Python grammar vertical slice | CG-00, CG-01, CG-02 |
| CG-04 | Incremental publication, write preconditions, locking, recovery, and freshness | CG-03 |
| CG-05 | Strict read-only query API | CG-03, CG-04 |
| CG-06 | Thin AEGIS core integration and instructions | CG-02 |
| CG-07 | C# extraction and .NET manifest reader | CG-03, CG-05 |
| CG-08 | TypeScript/JavaScript extraction and module metadata | CG-03, CG-05 |
| CG-09 | Installer: install, update, removal, ignore block, and diagnostics | CG-01 |
| CG-10 | Existing host adapter integration, Codex/OpenCode first | CG-02, CG-06 |
| CG-11 | Distribution, documentation, and rollback | CG-05 to CG-10 |
| CG-12 | Windows and Ubuntu CI infrastructure | None |
| CG-13 | Representative repository navigation benchmarks | CG-07 to CG-11 |

Start with CG-00 so native parser compatibility and folder size are established before investing in the whole engine; CG-01, CG-02, and CG-12 can run alongside it. First usable milestone: CG-00 through CG-06, exercising CodeGraph's own source through the direct CLI. Cross-language pilot: CG-07 and CG-08 before evaluating a .NET/Angular application. Host integration builds against the frozen protocol rather than defining it.

### Acceptance criteria

#### CG-00 Vendored-parser feasibility slice

- Publish the tested support matrix of CPython versions and operating systems, and pin the bindings, grammars, Python versions, and OS baselines.
- Establish which pinned packages ship abi3 wheels and how far that reduces the binary sets.
- Vendored natives load under `-I -B` on every Python in the matrix on clean Windows and Ubuntu machines with no extra packages, and a separately installed `tree_sitter` does not shadow them.
- With the exact pinned binding and grammar versions, cancellation interrupts parsing promptly, stops expensive queries, leaves the parser reusable or reset, and publishes no partly processed file.
- Measure folder size against the footprint target, detect FTS5 on the tested Pythons, and time query startup, including compiling the engine without a bytecode cache.

#### CG-01 Config, layout matching, metadata discovery, and read-only scope preview

- Reuses source/tests patterns without duplication; deterministic path selection on Windows and Ubuntu.
- Git and filesystem inventory modes are explicit, including a non-repository root.
- Extension mapping covers `.py`, `.pyi`, `.cs`, `.ts`, `.tsx`, `.mts`, `.cts`, `.js`, `.jsx`, `.mjs`, `.cjs`.
- Project metadata is discovered in the selected trees and their repository-contained ancestors, hashed into the input manifest, and adds no source symbols; Python import roots are inferred, with an override.
- Installed `.agentic` is excluded while canonical template code remains discoverable.
- Preview creates no project or cache files and writes no bytecode.
- This repository's layout and plugin-suite command are configured.

#### CG-02 Protocol specification, fixtures, and stub provider

- Versioned JSON envelope and compact text format written down, with the `status`, `index`, `freshness`, and `indexing_supported` fields from section 6.
- Exact responses for an empty successful search, ambiguity, unknown or expired IDs, expired pages, page tokens reused with a different request, unindexed paths, an unavailable index, a refused write precondition, a check that cannot start, and an interrupted check.
- Snapshot IDs never repeat after deletion, recreation, or rebuild; page tokens are bound to snapshot, action, target, filters, ordering, and limit.
- Fixture responses for every value and action, and a stub provider the core and adapter suites use without parser dependencies.

#### CG-03 SQLite storage and Python grammar vertical slice

- Index CodeGraph's own multi-module source and synthetic fixtures through vendored Tree-sitter, with AEGIS's single-file source as a secondary pilot.
- Find classes, functions, parameters, and supported bindings; cite exact ranges; 128-bit IDs with prefix resolution; distinguish dynamic and unresolved calls.
- Clean read-only missing-database handling; no repository imports or runtime downloads.

#### CG-04 Incremental publication, write preconditions, locking, recovery, and freshness

- Add, edit, delete, rename, exclude, config-change, manifest-change, parse-failure, and parse-timeout cases handled.
- Preconditions run in order (paths and configuration, Git state, writer lock, ownership). In a Git checkout, indexing refuses before any filesystem change, including creating the database folder or the lock file, when the database folder is not ignored or contains tracked files.
- The ownership check precedes every read-write open: a file without the CodeGraph `application_id` is never recovered, updated, or replaced.
- The OS writer lock blocks a second writer and is released when the holder is killed, even while extraction workers still run; the lock file is never deleted or recreated.
- Readers keep serving the last completed generation while an indexer parses, builds a temporary database, or holds SQLite's RESERVED lock; only an actual `SQLITE_BUSY` after the short busy timeout reads as `busy`.
- A genuinely interrupted transaction reads as `needs_recovery` and is recovered only by the next index; a harmless journal file does not affect reads; rebuild never leaves a journal beside the wrong database.
- Stdin liveness stops indexing when the parent dies, including with no elapsed limit, and no other child inherits the pipe.
- An indexer whose plugin content changed during the run, through an update, a branch switch, or an uncommitted edit that leaves the release version unchanged, discards its unpublished work and keeps the last completed generation (`plugin_changed`).
- Interrupted writes preserve a valid generation; worktrees stay separate; queries do not mutate the cache; an explicit check detects equal-size edits and new callers.

#### CG-05 Strict read-only query API

- Status, check, find, file, symbol, callers, and refs match the CG-02 protocol.
- Result bytes, work, and time are bounded.
- Read-only database and filesystem behavior, including missing, stale, corrupt, foreign, busy, and needs-recovery cases, with no bytecode written.
- Check never saves state; disambiguation and paging work; no-results and unavailable stay distinct.

#### CG-06 Thin AEGIS core integration and instructions

- Built against the stub provider.
- Seven read commands plus `know_graph_index` share one transport; positional targets suffice for navigation.
- The fixed entry point runs with `-I -B -X utf8`, in a new process session on Ubuntu; a timeout or cancellation kills the provider's tree and leaves AEGIS and its caller alive.
- The database path is confined to `.agentic/knowledge/codegraph/` with a `NAME.sqlite` filename.
- Read, check, and index budgets are separate; the reader is bounded; exit codes are as specified.
- Eight concise `CLI.md` sections and the `AGENTS.md` ownership and instruction updates.
- No automatic refresh, no plugin process when disabled, and no graph access during normal governance commands.

#### CG-07 C# extraction and .NET manifest reader

- Tested declaration subset and locations: namespaces, interfaces, properties, fields, and methods.
- Comments, generics, attributes, and partial classes covered or explicitly marked partial.
- Never claims complete overload or DI resolution.

#### CG-08 TypeScript/JavaScript extraction and module metadata

- Classes, functions, arrow functions, variables, and import forms tested across all mapped extensions.
- Duplicate names, scope and shadowing, JSX, templates, and regex literals tested.
- Relative import candidates are source-linked; no installed Node compiler is required.

#### CG-09 Installer: install, update, removal, ignore block, and diagnostics

- `install`, run from an extracted release with `-I -B -X utf8`, installs or updates the plugin folder. It refuses while the writer lock is held, validates the release against its manifest, refuses and lists locally modified or unknown files in an existing plugin folder, stages the new files, restores the previous files if any replacement fails, and never edits `aegis.toml`.
- `uninstall` holds the writer lock throughout, refuses if either owned folder holds a file it does not own, deletes the database files and then the plugin folder, deletes the lock file and database folder only as final teardown, then removes the ignore block. Component Markdown, `aegis.toml`, and unrelated content are untouched.
- The ignore block uses distinct markers, preserves content and newline style, and coexists with the AEGIS block, including `commit_fingerprints = true`.
- Prints the config snippet without editing TOML; reports ignored, not-ignored, and tracked states without changing Git state.

#### CG-10 Existing host adapter integration, Codex/OpenCode first

- Built against the stub provider: one read tool/bridge operation plus a maintenance job kind with its own reservation and no fingerprints.
- Cancellation stops the execution subtree while the worker records `cancelled` and releases its reservation.
- Model-visible budget enforced with compact serialization; AEGIS version gating.
- Reviewers cannot index; tool counts are derived from registrations; the installer message is updated.
- No new server or dependency; backend tests and Codex/OpenCode registration/dispatch checks; other hosts extended through shared code.

#### CG-11 Distribution, documentation, and rollback

- The release builder assembles the plugin folder from pinned wheels for both platforms, with manifest and notices.
- Explicit enable and disable; an add-on upgrade preserves core, config, and records, and a core upgrade preserves the plugin.
- A schema mismatch produces an actionable fallback.
- Install, update, disable, and recovery instructions.

#### CG-12 Windows and Ubuntu CI infrastructure

- Runners for both platforms with the three environments in section 3: assembly (the only step with network or wheel-cache access); test (Python with `pytest`, Node.js 22+, Git) running all suites offline against the assembled folder; and clean runtime (Python and Git only) exercising dispatch, indexing, and queries offline.
- A documented owner.

#### CG-13 Representative repository navigation benchmarks

- Reproducible extraction and query accuracy, latency, size, and source-location results against hand-checked fixtures.
- Measured limitations published; no model-specific trial required.

## 11. Verification strategy and measurable targets

### Required behavior tests

Use small synthetic source fixtures and the repository's existing Python test runner for engine behavior. Once the plugin folder is assembled (or its natives are committed), the plugin suite runs on any Python in the support matrix with only `pytest` installed. Core dispatch tests use the CG-02 stub provider so the existing core suite does not depend on parsers. Run the plugin suite through its `[commands]` entry and in CI. Existing host integration tests remain in their current tooling.

- Scope: overlapping globs, empty scope, case-sensitive matching, Unicode/spaces, deleted/untracked files, ignored outputs, large seeds, linked/outside-root paths, nested repository boundaries, non-repository roots, and the no-Git fallback; manifests outside the selected trees (a root `pyproject.toml`, `package.json`, or `tsconfig.json`) are read and hashed but add no symbols, and changing one makes the index stale.
- Extractors: fake declarations inside comments/strings, multiline signatures, nested scopes, duplicate names, variable shadowing, ambiguous overloads, malformed/in-progress source, unsupported syntax, encoding failures, parse timeouts, and cancellation (prompt interruption, query stop, parser reuse, no partial publication).
- Index integrity: dangling edges after deletions, re-resolution after rename, unchanged-file reuse, parser/config invalidation, read/write concurrency, writer-lock contention including a killed holder with live workers, lock-file stability across rebuilds, interruption, parent death during indexing, schema mismatch, relocation, and rebuild recovery.
- Write preconditions: in a Git checkout, a not-ignored or tracked database folder makes indexing refuse before any file is created; an existing foreign SQLite database, with or without a hot journal, is never opened read-write.
- Journals and rebuild: reads keep working while an indexer parses, builds a temporary database, or holds SQLite's RESERVED lock; an actual `SQLITE_BUSY` after the busy timeout reads as `busy`; a genuinely interrupted transaction (`needs_recovery`, then recovered by the next index), and a harmless leftover journal file (reads unaffected); rebuild over a recoverable old database, over an unrecoverable one, and over a non-CodeGraph file (refused); no journal left beside a database it does not belong to.
- Queries: every `status` value from section 6, with an empty successful search distinct from an unavailable index; deterministic ranking, scoped identities, prefix resolution and ambiguity, cycles/high fan-out, missing/partial data, exact location hashes, explicit stale citations, paging (a token from before a rebuild returns `expired`; a token reused with a different request is rejected), valid bounded JSON, and SQL argument escaping.
- Read-only boundary: compare database hashes and directory inventories before/after status/check/navigation, including missing/stale/incompatible/busy/needs-recovery cases; query/check create no index, directories, logs, migrations, saved timestamps, or bytecode. Start from a fresh plugin folder with no `__pycache__` directories, through AEGIS and standalone, including extraction-worker startup. Exercise a readable database in a non-writable knowledge directory and verify a cancelled full check never reports current.
- AEGIS: legacy config and command snapshots unchanged; database paths outside `.agentic/knowledge/codegraph/` rejected by both the core and the provider, including symlink and junction escapes and names outside `NAME.sqlite` (such as `codegraph.sqlite-journal` or the lock filename); targets after `--`; on Ubuntu, a timeout or cancellation kills the provider's tree while AEGIS and its caller stay alive; no auto-execution/indexing; bounded subprocess capture; exit/status mapping including exit 2 for usage errors; existing candidate/anchor/test behavior unaffected.
- Isolation: a user-installed `tree_sitter` and a `PYTHONPATH` entry do not change which natives load; an unmatched Python reports `indexing_supported: false` while queries still work; a newer Python using an abi3 set reports `python_support: untested`.
- Installation: ignore-block creation and refresh, coexistence with the AEGIS block in both `commit_fingerprints` settings, newline preservation, and tracked-database diagnostics; install, update, and uninstall refused while an indexer holds the writer lock, including one started from a terminal; install refuses locally modified or unknown plugin files; a failed replacement restores the previous files; uninstall refuses unexpected files in either owned folder and leaves component Markdown and `aegis.toml` untouched; an indexer whose plugin content changed mid-run, including an edit that keeps the release version, does not publish.
- Naming/storage: flat `know_graph_*` CLI reads and the read tool produce equivalent results; maintenance alone writes the ignored `.agentic/knowledge/codegraph/` subfolder; component Markdown remains discoverable and tracked.
- Host behavior: model-visible content stays within budget including wrappers; read and maintenance tools have truthful separate annotations; maintenance jobs record no fingerprints, and cancellation stops the execution subtree while the worker records `cancelled` and releases its reservation; unsupported older cores degrade through version gating; reviewers gain no mutation route; source reads still occur.
- Platform parity: run the same fixtures and CLI/protocol tests on native Windows and Ubuntu; compare normalized results, verify LF/CRLF and Unicode line/column mapping, and test each platform's process termination, locks, and replacement behavior.

Review documentation directly; do not add tests asserting planning prose or inventories. During implementation run the existing core suite and affected integration tests plus the plugin suite, following the repository's validation rules: `python -m pytest -q 05_Software/aegis/tests` and `python -m pytest -q 05_Software/aegis/plugins/codegraph/tests`. These are future implementation checks, not commands executed for this planning-only change.

### Initial engineering budgets (targets, not measured claims)

Record OS, Python version, SQLite version, Tree-sitter and grammar versions, CPU/storage, cold/warm state, index scope, and output policy with every benchmark.

| Metric | Initial target / decision criterion |
|---|---|
| Recipient-installed dependencies | None beyond AEGIS's Python 3.11+ and the supported OS. Git improves inventory but is optional for the standalone plugin. |
| Core growth | Aim for at most 300 additional production lines in `aegis.py`. This is a review target, not a reason to compress code or weaken process handling. |
| Plugin footprint | Initial goal <=30 MiB for the committed folder with both platforms' natives and the initial language set; measure in CG-00 and review the vendored set before committing it to downstream repositories if materially exceeded. |
| Core-only overhead | No provider process, index scan, or database open when the feature is disabled. Static host tool registrations remain; measure and minimize their size. |
| Response budget | 20 results / 8 KiB default provider output; <=32 KiB explicitly enlarged; the adapter keeps model-visible content within its budget including wrappers; all truncation visible. |
| Context baseline | Local models with at least 128k context; defaults use a small fraction of it. |
| Query latency | On a ~100k-line first-party code fixture and SSD, target p95 <=1 second including both Python process launches and bounded cited-file checks. Explicit whole-scope verification measured separately. |
| Indexing latency | Same fixture: initial index <=30 seconds, typical small edit-batch update <=5 seconds. Measure before promising; no background polling to conceal cost. |
| Database/memory | Initially target database <=100 MiB and peak indexer RSS <=256 MiB for that fixture; disclose collection method and missed targets. |
| Extraction usefulness | Hand-labeled pilot sample: >=95% precision and >=80% recall for the advertised declaration subset; report unsupported constructs separately and do not generalize to compiler-level reference accuracy. |
| Relationship honesty | Every displayed target has evidence/resolution labels; zero known ambiguous relationships promoted to proven semantic targets in the regression corpus. |

### Repository navigation benchmarks

Use fixed repository snapshots and hand-checked expected results for symbol discovery, callers/implementations, duplicate names, variable shadowing, architecture boundary lookup, test-reference discovery, and a deliberately stale index. Exercise at least 20 queries across small Python and upper-medium C#/TypeScript fixtures directly through the CLI/API.

Measure matching declarations/references, missed locations, incorrect resolution claims, source citations, result bytes, and elapsed time including refresh cost. These tests assess the plugin's navigation data and output bounds without requiring an LLM or making claims about a particular model's accuracy or token savings. Agent productivity benefits remain intended and unmeasured; a small generic agent comparison can be added later as an optional study. Simple single-file edits remain free to use ordinary search directly.

An optional InfoShare evaluation can reuse the earlier observed shape (nine C# projects, Angular/mobile clients, substantial migrations and bulk seed SQL). Re-measure before benchmarking, obtain access as needed, and do not hard-code its folder names into the reusable plugin. CodeGraph's own source is the initial dogfood target, with AEGIS's source as a secondary pilot.

## 12. Deferred capabilities and completion definition

Defer GUI graph visualization, natural-language query translation, embeddings/RAG, document and Markdown indexing (future `know_docs_*`), persistent servers, watchers, multi-repository federation, arbitrary plugins inside CodeGraph, automatic code edits, automatic test-suite reduction, exhaustive data-flow analysis, and compiler/LSP integrations. The first edition should earn those additions through demonstrated use.

Completion requires:

- A committed plugin folder that runs on AEGIS's Python 3.11+ with vendored parsers, from AEGIS configuration, with no per-folder parser setup or recipient package installation.
- Native parser support on Windows x64 and Ubuntu x64, with passing core, plugin, and dispatch tests on both platforms and a documented supported-version matrix (Python versions, OS releases).
- A rebuildable checkout-local SQLite database, protected by the provider writer lock, with truthful coverage/freshness metadata and explicit recovery.
- Useful source-linked queries through a thin AEGIS command and the selected existing host adapters, with model-visible budgets enforced.
- Existing AEGIS behavior preserved when CodeGraph is absent, disabled, or unavailable.
- Status, freshness checks, and navigation remain strictly read-only; explicit authorized indexing handles first ingestion, recovery, and refreshes, with reviewer maintenance prohibited.
- Indexing stops cleanly when cancelled or when its parent dies, from the CLI and from host jobs.
- Measured parser/navigation performance and verified host tool registration/dispatch, with unverified host combinations clearly identified.
- Install, update, disable, and recovery instructions that do not make database maintenance part of every agent turn.

**Recommended implementation start:** prove the vendored natives on every supported Python and platform, write the protocol and stub, then build the Python vertical slice and compact query contract, followed by C#/TypeScript/JavaScript extraction.

## 13. External technical references

- [Tree-sitter introduction and language parsers](https://tree-sitter.github.io/tree-sitter/): embeddable syntax parsing, language bindings, and upstream grammars. Parsing does not by itself implement semantic symbol resolution.
- [Python command-line options](https://docs.python.org/3/using/cmdline.html): isolated mode (`-I`) and UTF-8 mode (`-X utf8`).
- [Python stable ABI](https://docs.python.org/3/c-api/stable.html): the abi3 limited API that decides whether one native build serves several Python versions.
- [SQLite URI filenames](https://www.sqlite.org/uri.html) and [SQLite locking and hot journals](https://www.sqlite.org/lockingv3.html): read-only connections and rollback-journal recovery.

The Tree-sitter reference was checked during the original planning. The other references were added in the 2026-10-03 revision and should be confirmed during CG-00. Exact dependency versions, folder size, supported platform baselines, and performance remain implementation/evaluation results to establish.
