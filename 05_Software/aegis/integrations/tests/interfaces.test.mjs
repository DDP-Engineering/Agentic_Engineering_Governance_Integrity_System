// Copyright (c) 2026 DDP Engineering
// Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
// SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { spawnSync, execFileSync } from 'node:child_process';
import plugin from '../opencode/plugin.mjs';
import { discoverRuntime } from '../shared/runtime.mjs';
import { runBridge } from '../shared/bridge.mjs';

test('opencode: register native agents/commands/tools without changing existing profiles', async () => {
  const hooks = await plugin({ directory: process.cwd() });
  const config = { model: 'kept/model', agent: { build: { permission: { edit: 'ask' }, prompt: 'kept' } }, command: { mine: { template: 'kept' } } };
  const before = structuredClone(config);
  await hooks.config(config);
  assert.equal(config.agent.aegis.mode, 'primary');
  assert.equal(config.agent.aegis.model, undefined);
  assert.deepEqual(config.agent.build, before.agent.build);
  assert.deepEqual(config.command.mine, before.command.mine);
  assert.equal(config.model, before.model);
  assert.equal(Object.keys(hooks.tool).length, 11);
  assert.equal(Object.keys(config.command).length, 6);
  await hooks.config(config); // Same-object repeat is idempotent.
  await assert.rejects(hooks.config({ agent: { aegis: {} } }), /conflict/);
});

test('review: read-only permissions and bridge deny reviewer mutation', async () => {
  const hooks = await plugin({ directory: process.cwd() }); const config = {}; await hooks.config(config);
  for (const name of ['aegis-spec-review', 'aegis-quality-review']) {
    assert.equal(config.agent[name].mode, 'subagent');
    assert.equal(config.agent[name].permission['*'], 'deny');
    assert.equal(config.agent[name].permission.aegis_read, 'allow');
  }
  await assert.rejects(runBridge(['run', '--kind', 'validate', '--role', 'reviewer']), /Reviewers/);
  await assert.rejects(runBridge(['job', '--id', 'anything', '--action', 'cancel', '--role', 'reviewer']), /Reviewers/);
});

test('runtime: resolve real executables and reject an invalid pinned Python', async () => {
  const found = await discoverRuntime({ python: process.env.AEGIS_PYTHON || (process.platform === 'win32' ? 'python' : 'python3') });
  assert.ok(path.isAbsolute(found.python)); assert.ok(path.isAbsolute(found.node));
  await assert.rejects(discoverRuntime({ python: path.join(os.tmpdir(), 'aegis-no-such-python') }), /Python/);
});

test('codex: assembled bridge reads actual checkout state and rejects missing governance', async () => {
  const base = await fs.mkdtemp(path.join(os.tmpdir(), 'aegis-codex-bridge-'));
  const root = path.join(base, 'repo'); await fs.mkdir(root);
  execFileSync('git', ['init', '-q'], { cwd: root });
  const script = path.join(process.env.AEGIS_TEST_PACKAGES, 'aegis-codex/plugins/aegis/scripts/aegis.mjs');
  let result = spawnSync(process.execPath, [script, 'status', '--root', root], { encoding: 'utf8' });
  assert.equal(result.status, 1); assert.match(result.stderr, /AEGIS is not installed/);
  await fs.cp(process.env.AEGIS_TEST_PAYLOAD, path.join(root, '.agentic'), { recursive: true });
  const python = process.env.AEGIS_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
  execFileSync(python, [path.join(root, '.agentic/aegis.py'), 'init'], { cwd: root });
  result = spawnSync(process.execPath, [script, 'status', '--root', root], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).result.schema, 1);
});
