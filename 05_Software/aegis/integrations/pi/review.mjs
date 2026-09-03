#!/usr/bin/env node
// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { readSettings, discoverRuntime } from '../shared/runtime.mjs';
import { createAdapter } from '../shared/adapter.mjs';
import { taskSchema } from '../shared/operations.mjs';
import { resolveHost } from '../shared/host-setup.mjs';

export function reviewArguments({ role, task, promptFile, packet, model }) {
  if (!['spec', 'quality'].includes(role)) throw new Error('Review role must be spec or quality.');
  taskSchema.parse(task);
  if (!path.isAbsolute(promptFile)) throw new Error('Review instructions require an absolute path.');
  return ['--print', '--no-session', '--no-extensions', '--no-skills', '--no-prompt-templates',
    '--no-context-files', '--no-themes', '--tools', 'read,grep,find,ls', '--append-system-prompt', promptFile,
    ...(model ? ['--model', model] : []), '--',
    `Independently review ${task} for ${role === 'spec' ? 'specification compliance' : 'implementation quality'}. Read root AGENTS.md, .agentic/AGENTS.md, .agentic/tasks/${task}.md and the linked requirements/design, changed files and evidence.${packet ? ' Read the review packet at ' + JSON.stringify(packet) + '.' : ''} Return the required verdict and limitations; do not edit anything.`];
}

async function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!['--root', '--task', '--role', '--packet', '--model', '--host-cli'].includes(argv[i]) || !argv[i + 1]) throw new Error('Use --root, --task, --role, --packet and optionally --model or --host-cli.');
    options[argv[i].slice(2)] = argv[i + 1];
  }
  if (!options.root || !options.packet) throw new Error('Supply --root and a checkout-relative --packet containing the candidate digest and review scope.');
  const root = await fs.realpath(options.root);
  const packet = await fs.realpath(path.resolve(root, options.packet));
  const relative = path.relative(root, packet);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative) || !(await fs.stat(packet)).isFile()) throw new Error('Review packet must be a regular file inside the checkout.');
  const promptFile = path.join(path.dirname(fileURLToPath(import.meta.url)), 'review-prompts', `aegis-${options.role}-review.md`);
  const args = reviewArguments({ ...options, promptFile, packet: relative });
  const stored = await readSettings();
  const runtime = await discoverRuntime(stored);
  const adapter = createAdapter(runtime);
  await adapter.resume({ task: options.task }, { directory: root, worktree: root, sessionID: 'pi-review', agent: 'aegis-spec-review' });
  const cli = await resolveHost('pi', runtime.node, options['host-cli'] || stored.hostCliPath);
  const child = spawn(cli.command, [...cli.args, ...args], { cwd: root, shell: false, windowsHide: true, stdio: 'inherit' });
  const interrupt = () => child.kill('SIGTERM');
  process.once('SIGINT', interrupt); process.once('SIGTERM', interrupt);
  try {
    process.exitCode = await new Promise((resolve, reject) => {
      child.once('error', reject); child.once('exit', (code, signal) => resolve(signal ? 1 : code ?? 1));
    });
  } finally { process.removeListener('SIGINT', interrupt); process.removeListener('SIGTERM', interrupt); }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
