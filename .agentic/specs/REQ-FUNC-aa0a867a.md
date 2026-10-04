<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-aa0a867a - Extract Python definitions with exact source ranges

This spec defines Python extraction, module naming, resolution labels and
symbol identity. It is also referenced by REQ-FUNC-c7ece57c,
REQ-FUNC-0c82c3c6, REQ-FUNC-7432a8a2, REQ-FUNC-45ed74a5, REQ-REL-1162622e,
REQ-DATA-9004cf27 and REQ-PLAT-3430c1f3.

## Behavior

Extraction parses each selected Python file with the vendored Tree-sitter
Python grammar. It never imports or executes repository code.

### Decoding and positions

- Files decode as UTF-8 (a leading BOM is ignored). A file that does not
  decode is `failed` with reason `encoding`.
- Lines are 1-based. Columns are 1-based Unicode code-point offsets within the
  line, converted from Tree-sitter byte offsets. CRLF and LF files give the
  same line numbers; a `\r` before `\n` is not part of any range.
- A range ends at the last character of the node; a module's range ends at
  the last character of its last non-empty line.

### Definitions

| Construct | Kind | Name | Signature |
|---|---|---|---|
| the file | `module` | module name | empty |
| `class` statement | `class` | class name | `class Name(bases)`; `class Name` without bases |
| `def`/`async def` at module level or nested in a function | `function` | function name | `def name(params) -> annotation`, `async def` kept |
| `def`/`async def` directly in a class body | `method` | method name | as for functions |
| function parameters, including `*args`, `**kwargs`, keyword-only and positional-only | `parameter` | parameter name | annotation text when present |
| a simple-name assignment target (`x = ...`, `x: T = ...`, augmented, `for x in`, `with ... as x`) at module, class or function level | `variable` | target name | annotation text when present |

A simple name's first binding in a scope defines its variable; later
bindings of the same name in that scope - assignment, augmented assignment,
`for`, `with ... as`, `:=` and `del` targets - are `write` references to it.
Each plain name in a tuple, list or starred target binds the same way.
Comprehension, `except ... as` and `with ... as` targets bind variables of the
enclosing scope. A name declared `global` resolves in the module scope and a
`nonlocal` name in the enclosing functions; neither defines a local variable.
Decorators are included in the definition's range. Signatures collapse
whitespace runs to one space and drop comments. An attribute target
(`self.x = ...`, `mod.attr = ...`) produces a `write` reference spelled as the
chain, resolved like an attribute read, not a variable. A lambda's parameters
bind only inside its body and are not recorded; the references in its body
and defaults are. Definitions inside comments or string literals do not exist for
the grammar and therefore produce nothing.

Qualified names join the module name and the enclosing definition names with
`.`, for example `pkg.mod.Outer.method` and `pkg.mod.func.inner`.

### Module names and import roots

1. When `[codegraph] python_import_roots` is non-empty, those folders are the
   roots.
2. Otherwise each folder holding a recognized manifest (`pyproject.toml`,
   `setup.cfg`) is a root, and so is its `src/` child folder when that exists.
3. When neither applies, the repository root is the root.

A file's module name is its path relative to the deepest root containing it,
without the suffix, with `/` replaced by `.`; `pkg/__init__.py` names `pkg`.
A file under no root uses its path from the repository root. Manifests are read
as text with `tomllib` or `configparser`; `setup.py` is never executed.

### References and resolution labels

| Reference | Kind |
|---|---|
| call expression with a name or attribute callee; an attribute on any other receiver (`super().save()`) is spelled as the attribute name | `call` |
| `import a.b`, `from a.b import c` | `import` |
| identifier read in an expression; an attribute chain only when its first name is bound by an import (`os.sep`) | `read` |
| assignment, augmented assignment or deletion target | `write` |

Labels, first matching rule wins:

1. `direct-syntax`: an import whose module path names an indexed module, or a
   `from` import naming a symbol defined at the top level of an indexed module.
2. `lexical-binding`: a name resolved through the scope chain (current
   function, enclosing functions, module, then names bound by imports) to a
   definition in the same file or to the target of a `direct-syntax` import.
   Class bodies - including every enclosing class of a nested class - are not
   part of a method's scope chain.
3. `external`: a module path or imported name outside the index, and Python
   built-in names; the spelling is kept, there is no target.
4. `candidate`: no binding path, but symbols with the same simple name exist
   elsewhere; up to 5 candidates are stored, ranked same module, same package,
   then path order. `self.name` and `cls.name` calls resolve this way against
   the enclosing class first.
5. `unresolved`: anything else, including star imports and relative imports
   that climb above the package. Calls such as `getattr(...)` are built-in
   calls (rule 3); the attribute they reach is never resolved.

Only `direct-syntax` and `lexical-binding` set `target`. Candidates are stored
separately and are never shown as confirmed. No relation expresses test
coverage.

### Syntax errors and time limits

- A parse tree containing error or missing nodes keeps the definitions and
  references of top-level statements that contain none, and marks the file
  `partial` with reason `syntax`. With no such statement the file is `failed`
  with reason `syntax`.
- Each file is parsed and extracted in a worker process started with the
  `spawn` method. When one file exceeds `parse_timeout_seconds`, the indexer
  terminates that worker, records the file as `failed` with reason
  `parse-timeout`, starts a replacement worker and continues; the file
  contributes no facts. Tree-sitter progress callbacks are not used.
- A failed or partial file's facts from earlier generations are replaced by
  the new result in the same publication.

### Symbol identity

`id = sha256("\x1f".join([path, scope_qualified_name, kind, name, signature, str(n)]))[:32]`,
where `scope_qualified_name` is the enclosing definition's qualified name (the
module name at top level) and `n` is the 0-based ordinal among definitions in
the same file with all other key fields equal, in source order. Line positions
are not part of the key.

## Data / interface

Extractor revision `python-1` is recorded per file; changing the extraction
rules increments it and invalidates every Python file on the next index.

## Examples

```python
# pkg/src/shop/orders.py, root pkg/src
class OrderRepository(Base):       # class shop.orders.OrderRepository, lines 2-5
    def save(self, order):         # method shop.orders.OrderRepository.save
        audit(order)               # call audit -> candidate when audit exists elsewhere
        return self.store(order)   # call self.store -> candidate on OrderRepository first
```

## Acceptance

- Golden fixtures cover every construct row, every label rule, CRLF and
  non-ASCII files, syntax errors and an undecodable file, and match on Windows
  and Ubuntu.
- Re-indexing unchanged content gives identical IDs; inserting blank lines
  above a definition keeps them.

## Assumptions and open decisions

- The pinned tree-sitter 0.26.0 binding crashes Python 3.11 and 3.12 when a
  progress callback is supplied, so per-file time limits rely on terminating
  worker processes.
