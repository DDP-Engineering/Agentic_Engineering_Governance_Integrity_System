// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import path from 'node:path';
import { createAdapter } from './adapter.mjs';
import { discoverRuntime, readSettings } from './runtime.mjs';

const operations = new Set(['status', 'resume', 'read', 'summary', 'check', 'scaffold', 'evidence', 'candidate', 'diff', 'run', 'job']);
const values = new Set(['root', 'task', 'document', 'kind', 'title', 'type', 'category', 'parent', 'action', 'base', 'path', 'command', 'id', 'role']);
const flags = new Set(['all', 'strict', 'impacted', 'no-fallback', 'compact']);

/** Argument-array bridge for Codex skill scripts; role is a guard, not identity authentication. */
export async function runBridge(argv) {
  const [operation, ...rest] = argv;
  if (!operations.has(operation)) throw new Error(`Choose an operation: ${[...operations].join(', ')}`);
  const args = {};
  for (let i = 0; i < rest.length; i++) {
    const key = rest[i].replace(/^--/, '');
    if (flags.has(key)) args[key.replaceAll('-', '_')] = true;
    else if (values.has(key) && rest[i + 1] !== undefined) args[key] = rest[++i];
    else throw new Error(`Unknown or incomplete option: ${rest[i]}`);
  }
  if (args.role && !['coordinator', 'reviewer'].includes(args.role)) throw new Error('Role must be coordinator or reviewer');
  const root = path.resolve(args.root || process.cwd());
  const reviewer = args.role === 'reviewer';
  if (reviewer && (['scaffold', 'evidence', 'run'].includes(operation) || operation === 'job' && args.action === 'cancel')) throw new Error('Reviewers can only read workflow evidence.');
  delete args.root; delete args.role;
  const runtime = await discoverRuntime(await readSettings());
  const adapter = createAdapter(runtime);
  return adapter[operation](args, { directory: root, worktree: root, sessionID: 'codex-cli',
    agent: reviewer ? 'aegis-spec-review' : 'aegis', abort: new AbortController().signal });
}
